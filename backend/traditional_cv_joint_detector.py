"""
传统CV方法小关节识别算法 V5 - 扫描旋转染色法 + YOLOv8混合方案
基于用户描述的几何规律和图像处理启发式算法
核心思路：
1. YOLOv8手性检测：使用best.pt准确识别尺骨和桡骨
2. 传统CV检测：扫描旋转染色法检测其他关节
3. 结果融合：整合YOLOv8与传统CV的检测结果
"""

import cv2
import numpy as np
import os
from typing import List, Tuple, Dict, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import time


class HandSide(Enum):
    LEFT = "left"
    RIGHT = "right"
    UNKNOWN = "unknown"


@dataclass
class BoneComponent:
    """骨骼组件数据结构"""
    label: str
    mask: np.ndarray
    centroid: Tuple[float, float]
    bbox: Tuple[int, int, int, int]
    area: float
    aspect_ratio: float
    circularity: float
    solidity: float
    order: int = 0


class ScanningRotationDyeingDetector:
    """
    扫描旋转染色法小关节检测器 V5
    
    核心算法步骤:
    1. YOLOv8手性检测: 使用best.pt准确识别尺骨和桡骨
    2. 传统CV检测: 扫描旋转染色法检测其他关节
    3. 结果融合: 整合YOLOv8与传统CV的检测结果
    """
    
    def __init__(self, 
                 min_area: int = 100,
                 max_area: int = 100000,
                 scan_step: int = 15,
                 use_yolo_for_hand_side: bool = True,
                 yolo_model_path: Optional[str] = None,
                 yolo_conf: float = 0.5,
                 dye_colors: Optional[List[Tuple[int, int, int]]] = None):
        """
        初始化检测器
        
        Args:
            min_area: 最小区域面积
            max_area: 最大区域面积
            scan_step: 旋转扫描角度步长(度)
            use_yolo_for_hand_side: 是否使用YOLOv8检测手性
            yolo_model_path: YOLOv8模型路径
            yolo_conf: YOLOv8置信度阈值
            dye_colors: 染色颜色列表
        """
        self.min_area = min_area
        self.max_area = max_area
        self.scan_step = scan_step
        self.use_yolo_for_hand_side = use_yolo_for_hand_side
        self.yolo_conf = yolo_conf
        
        # YOLOv8模型初始化
        self._yolo_model = None
        if use_yolo_for_hand_side:
            if yolo_model_path is None:
                yolo_model_path = os.path.join(
                    os.path.dirname(__file__), 
                    "app", "models", "recognize", "best.pt"
                )
            if os.path.exists(yolo_model_path):
                try:
                    from ultralytics import YOLO
                    self._yolo_model = YOLO(yolo_model_path)
                    print(f"✅ YOLOv8模型加载成功: {yolo_model_path}")
                except Exception as e:
                    print(f"⚠️ YOLOv8模型加载失败: {e}")
                    self._yolo_model = None
        
        # 预设染色颜色(用于区分不同关节)
        self.dye_colors = dye_colors or [
            (255, 0, 0),     # 红色
            (0, 255, 0),     # 绿色
            (0, 0, 255),     # 蓝色
            (255, 255, 0),   # 青色
            (255, 0, 255),   # 紫色
            (0, 255, 255),   # 黄色
            (128, 0, 0),     # 深红
            (0, 128, 0),     # 深绿
            (0, 0, 128),     # 深蓝
            (128, 128, 0),   # 橄榄色
            (128, 0, 128),   # 紫色
            (0, 128, 128),   # 青色
            (255, 128, 0),   # 橙色
        ]
        
        # 哈希集合记录已扫描位置
        self._scanned_positions: Set[int] = set()
        # 标记掩码
        self._dye_mask: Optional[np.ndarray] = None
        
        # 预计算角度缓存
        self._angle_cache: Dict[int, Tuple[float, float]] = {}
        for angle in range(0, 360, self.scan_step):
            rad = np.deg2rad(angle)
            self._angle_cache[angle] = (np.cos(rad), np.sin(rad))
    
    def detect_hand_side_with_yolo(self, image: np.ndarray) -> Optional[Tuple[Optional[HandSide], Optional[Dict]]]:
        """
        使用YOLOv8检测手性和骨骼灰度特征
        
        关键：先将图片resize成1024x1024再调用YOLOv8
        
        Returns:
            Tuple of (hand_side, bone_gray_info)
            - hand_side: 手性
            - bone_gray_info: {'low': int, 'high': int, 'mean': float, 'std': float}
        """
        if self._yolo_model is None:
            return None, None
        
        try:
            # 保存原始尺寸
            orig_h, orig_w = image.shape[:2]
            
            # 转换为灰度图
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image.copy()
            
            # 先将图片resize成1024x1024
            resized_image = cv2.resize(image, (1024, 1024), interpolation=cv2.INTER_LINEAR)
            
            # 推理
            results = self._yolo_model.predict(
                resized_image, 
                imgsz=1024, 
                conf=self.yolo_conf, 
                verbose=False
            )
            
            if not results or len(results) == 0:
                return None, None
            
            result = results[0]
            boxes = result.boxes
            
            if boxes is None or len(boxes) == 0:
                return None, None
            
            # 查找Radius和Ulna
            radius_box = None
            ulna_box = None
            
            for box in boxes:
                cls_id = int(box.cls[0])
                cls_name = result.names[cls_id]
                
                if cls_name == 'Radius':
                    radius_box = box.xyxy[0].cpu().numpy()
                elif cls_name == 'Ulna':
                    ulna_box = box.xyxy[0].cpu().numpy()
            
            # 保存YOLOv8检测到的骨骼区域中心点（用于区域生长）
            # 注意：这些坐标是在resize后的1024x1024图像上的，需要映射回原始尺寸
            self._yolo_bone_regions = []
            scale_x = orig_w / 1024.0
            scale_y = orig_h / 1024.0
            
            if radius_box is not None:
                x1, y1, x2, y2 = map(int, radius_box)
                # 映射回原始尺寸
                cx = int((x1 + x2) // 2 * scale_x)
                cy = int((y1 + y2) // 2 * scale_y)
                if 0 <= cx < orig_w and 0 <= cy < orig_h:
                    self._yolo_bone_regions.append((cx, cy))
            
            if ulna_box is not None:
                x1, y1, x2, y2 = map(int, ulna_box)
                # 映射回原始尺寸
                cx = int((x1 + x2) // 2 * scale_x)
                cy = int((y1 + y2) // 2 * scale_y)
                if 0 <= cx < orig_w and 0 <= cy < orig_h:
                    self._yolo_bone_regions.append((cx, cy))
            
            # 提取骨骼灰度特征
            bone_gray_info = None
            if radius_box is not None or ulna_box is not None:
                # 注意：gray是原始尺寸的图像
                bone_pixels = []
                for box_coords in [radius_box, ulna_box]:
                    if box_coords is not None:
                        x1, y1, x2, y2 = map(int, box_coords)
                        # 映射回原始尺寸
                        x1_orig = int(x1 * scale_x)
                        y1_orig = int(y1 * scale_y)
                        x2_orig = int(x2 * scale_x)
                        y2_orig = int(y2 * scale_y)
                        
                        # 确保坐标在有效范围内
                        x1_orig = max(0, min(x1_orig, orig_w - 1))
                        y1_orig = max(0, min(y1_orig, orig_h - 1))
                        x2_orig = max(0, min(x2_orig, orig_w))
                        y2_orig = max(0, min(y2_orig, orig_h))
                        
                        # 提取检测框内的骨骼像素
                        roi = gray[y1_orig:y2_orig, x1_orig:x2_orig]
                        if roi.size > 0:
                            # 使用Otsu阈值提取骨骼区域
                            _, bone_mask = cv2.threshold(roi, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                            bone_pixels_in_roi = roi[bone_mask > 0]
                            if len(bone_pixels_in_roi) > 0:
                                bone_pixels.extend(bone_pixels_in_roi.tolist())
                
                if bone_pixels:
                    bone_pixels = np.array(bone_pixels)
                    bone_mean = np.mean(bone_pixels)
                    bone_std = np.std(bone_pixels)
                    bone_low = max(0, int(bone_mean - 1.5 * bone_std))
                    bone_high = min(255, int(bone_mean + 1.5 * bone_std))
                    
                    bone_gray_info = {
                        'low': bone_low,
                        'high': bone_high,
                        'mean': bone_mean,
                        'std': bone_std,
                        'min': int(np.min(bone_pixels)),
                        'max': int(np.max(bone_pixels))
                    }
            
            # 根据位置关系判断手性
            hand_side = None
            if radius_box is not None and ulna_box is not None:
                radius_center_x = (radius_box[0] + radius_box[2]) / 2
                ulna_center_x = (ulna_box[0] + ulna_box[2]) / 2
                
                # 在标准PA位片中，尺骨在左，桡骨在右 -> 左手
                if ulna_center_x < radius_center_x:
                    hand_side = HandSide.LEFT
                else:
                    hand_side = HandSide.RIGHT
            
            return hand_side, bone_gray_info
            
        except Exception as e:
            print(f"YOLOv8手性检测失败: {e}")
            return None, None
    
    def _pos_to_hash(self, x: int, y: int) -> int:
        """坐标转哈希值"""
        return (x << 16) | y
    
    def _clear_scan_cache(self):
        """清空扫描缓存"""
        self._scanned_positions.clear()
        self._dye_mask = None
    
    def find_starting_point(self, binary: np.ndarray) -> Optional[Tuple[int, int]]:
        """
        步骤1: 从图像右侧向左扫描找起始点
        
        原理: 手部X光片中,远节指骨通常位于图像右侧
        """
        h, w = binary.shape
        
        # 从右向左扫描
        for x in range(w - 1, -1, -1):
            for y in range(h):
                if binary[y, x] > 0:
                    return (x, y)
        
        return None
    
    def flood_fill_region(self, binary: np.ndarray, seed: Tuple[int, int], 
                         label: int) -> Optional[np.ndarray]:
        """
        步骤2: 中心扩展染色法(Flood Fill)
        
        使用BFS从种子点向外扩展,标记整个连通区域
        """
        h, w = binary.shape
        seed_x, seed_y = seed
        
        if binary[seed_y, seed_x] == 0:
            return None
        
        # 创建区域掩码
        region_mask = np.zeros((h, w), dtype=np.uint8)
        
        # BFS区域生长
        queue = deque([(seed_x, seed_y)])
        visited = set()
        visited.add((seed_x, seed_y))
        
        while queue:
            x, y = queue.popleft()
            region_mask[y, x] = 255
            
            # 4连通领域
            neighbors = [(x+1, y), (x-1, y), (x, y+1), (x, y-1)]
            for nx, ny in neighbors:
                if 0 <= nx < w and 0 <= ny < h:
                    if (nx, ny) not in visited and binary[ny, nx] > 0:
                        visited.add((nx, ny))
                        queue.append((nx, ny))
        
        return region_mask
    
    def clockwise_rotate_scan(self, binary: np.ndarray, 
                             center: Tuple[int, int],
                             visited_mask: np.ndarray) -> Optional[Tuple[int, int]]:
        """
        步骤3: 顺时针旋转扫描找下一个未染色区域
        
        从0度开始顺时针旋转,在每个角度上从近到远扫描
        """
        h, w = binary.shape
        cx, cy = center
        
        max_radius = int(np.sqrt(h**2 + w**2) / 2)
        
        # 顺时针旋转扫描
        for angle in range(0, 360, self.scan_step):
            cos_a, sin_a = self._angle_cache[angle]
            
            # 从近到远扫描
            for radius in range(10, max_radius, 3):
                x = int(cx + radius * cos_a)
                y = int(cy + radius * sin_a)
                
                # 边界检查
                if not (0 <= x < w and 0 <= y < h):
                    continue
                
                # 标记为已扫描
                self._scanned_positions.add(self._pos_to_hash(x, y))
                
                # 检查是否为有效种子点且未被染色
                if binary[y, x] > 0 and visited_mask[y, x] == 0:
                    return (x, y)
        
        return None
    
    def scanning_rotation_dyeing(self, binary: np.ndarray, 
                                max_regions: int = 15) -> List[Tuple[int, np.ndarray]]:
        """
        扫描旋转染色法主流程
        
        Returns:
            List of (label_id, region_mask) tuples
        """
        regions = []
        
        # 初始化标记掩码
        visited_mask = np.zeros_like(binary)
        
        # 步骤1: 找起始点
        start_point = self.find_starting_point(binary)
        if start_point is None:
            return regions
        
        # 步骤2: 染色第一个区域(远节指骨)
        first_region = self.flood_fill_region(binary, start_point, 0)
        if first_region is not None:
            regions.append((0, first_region))
            visited_mask = cv2.bitwise_or(visited_mask, first_region)
        
        # 步骤3: 迭代寻找其他区域
        current_color_idx = 1
        max_iterations = max_regions
        
        for iteration in range(max_iterations):
            # 计算当前已染色区域的中心作为扫描中心
            if regions:
                combined_mask = np.zeros_like(binary)
                for _, region in regions:
                    combined_mask = cv2.bitwise_or(combined_mask, region)
                
                moments = cv2.moments(combined_mask)
                if moments['m00'] > 0:
                    cx = int(moments['m10'] / moments['m00'])
                    cy = int(moments['m01'] / moments['m00'])
                    scan_center = (cx, cy)
                else:
                    scan_center = start_point
            else:
                scan_center = start_point
            
            # 顺时针旋转扫描找下一个种子点
            seed_point = self.clockwise_rotate_scan(binary, scan_center, visited_mask)
            
            if seed_point is None:
                break
            
            # 区域生长染色
            region = self.flood_fill_region(binary, seed_point, current_color_idx)
            if region is not None:
                regions.append((current_color_idx, region))
                visited_mask = cv2.bitwise_or(visited_mask, region)
                current_color_idx += 1
        
        return regions
    
    def region_growing_from_yolo_bones(self, 
                                       image: np.ndarray,
                                       gray: np.ndarray,
                                       bone_low: int, 
                                       bone_high: int,
                                       target_regions: int = 23) -> np.ndarray:
        """
        使用中心扩展法从YOLOv8检测到的骨骼区域出发，找到所有骨骼
        
        核心思路：
        1. 从YOLOv8检测到的尺骨和桡骨区域作为种子点
        2. 使用区域生长算法扩展
        3. 直到找到23个独立的骨骼区域
        
        Returns:
            bone_mask: 所有骨骼的二值掩码
        """
        h, w = gray.shape
        bone_mask = np.zeros((h, w), dtype=np.uint8)
        
        # 从YOLOv8骨骼区域和所有满足灰度条件的区域中找种子点
        seed_points = []
        
        # 优先使用YOLOv8骨骼区域
        if hasattr(self, '_yolo_bone_regions') and self._yolo_bone_regions:
            seed_points.extend(self._yolo_bone_regions)
        
        # 额外：从整幅图像中找到所有满足灰度条件的连通区域
        temp_mask = np.zeros((h, w), dtype=np.uint8)
        temp_mask[(gray >= bone_low) & (gray <= bone_high)] = 255
        
        # 找到所有连通区域
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(temp_mask, connectivity=8)
        
        # 选择足够大的区域作为种子
        if num_labels > 1:
            for i in range(1, num_labels):
                area = stats[i, cv2.CC_STAT_AREA]
                if area > 300:  # 降低最小面积阈值
                    cx, cy = int(centroids[i][0]), int(centroids[i][1])
                    # 检查是否已经在种子点列表中
                    if not any(abs(cx - sx) < 10 and abs(cy - sy) < 10 for sx, sy in seed_points):
                        seed_points.append((cx, cy))
        
        # 从种子点进行区域生长
        visited = np.zeros((h, w), dtype=bool)
        regions = []
        
        for seed_x, seed_y in seed_points:
            if visited[seed_y, seed_x]:
                continue
            
            # BFS区域生长
            region_mask = np.zeros((h, w), dtype=np.uint8)
            queue = deque([(seed_x, seed_y)])
            visited[seed_y, seed_x] = True
            
            while queue:
                x, y = queue.popleft()
                
                # 检查灰度是否在范围内
                if not (bone_low <= gray[y, x] <= bone_high):
                    continue
                
                region_mask[y, x] = 255
                
                # 4连通领域
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h:
                        if not visited[ny, nx]:
                            if bone_low <= gray[ny, nx] <= bone_high:
                                visited[ny, nx] = True
                                queue.append((nx, ny))
            
            # 只保留足够大的区域
            if np.sum(region_mask > 0) > 100:
                regions.append(region_mask)
        
        # 合并所有区域
        for region in regions:
            bone_mask = cv2.bitwise_or(bone_mask, region)
        
        return bone_mask
    
    def kmeans_bone_detection(self, gray: np.ndarray, n_clusters: int = 3) -> Tuple[int, int]:
        """
        使用KMeans聚类自动识别骨骼灰度范围
        
        原理：
        1. 将图像灰度分成n_clusters个类别
        2. 通常分为3类：背景、骨骼、结缔组织
        3. 骨骼的灰度通常在中间值
        
        Args:
            gray: 灰度图像
            n_clusters: 聚类数量
        
        Returns:
            (bone_low, bone_high): 骨骼灰度范围
        """
        h, w = gray.shape
        
        # 准备数据：采样以加速
        # 只使用非边缘的像素（避免背景干扰）
        margin = 20
        roi = gray[margin:-margin, margin:-margin]
        
        # 展平为1D数组
        pixel_values = roi.reshape((-1, 1)).astype(np.float32)
        
        # KMeans聚类
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
        _, labels, centers = cv2.kmeans(
            pixel_values, 
            n_clusters, 
            None, 
            criteria, 
            10, 
            cv2.KMEANS_RANDOM_CENTERS
        )
        
        # 按灰度值排序中心点
        centers = sorted(centers.flatten())
        
        # 分析每个类别
        # 假设：背景灰度最高或最低，骨骼在中间
        bg_mean = np.mean(gray[:20, :])  # 边缘背景均值
        
        # 找到最接近背景灰度的聚类中心（排除背景）
        bg_cluster_idx = 0
        min_diff = float('inf')
        for i, center in enumerate(centers):
            diff = abs(center - bg_mean)
            if diff < min_diff:
                min_diff = diff
                bg_cluster_idx = i
        
        # 根据背景类型判断骨骼位置
        if bg_mean > 127:
            # 亮背景：骨骼灰度 < 背景灰度
            # 骨骼应该是低于背景但高于最暗区域的灰度
            # 聚类中心通常：[骨骼, 结缔组织, 背景]
            bone_cluster_idx = 0  # 使用最低的灰度聚类
        else:
            # 暗背景：骨骼灰度 > 背景灰度
            # 骨骼应该是高于背景但低于最亮区域的灰度
            bone_cluster_idx = len(centers) - 1  # 使用最高的灰度聚类
        
        bone_center = centers[bone_cluster_idx]
        
        # 根据聚类中心计算骨骼灰度范围
        # 使用均值±标准差作为范围
        # 获取属于骨骼类别的像素
        bone_pixels = pixel_values[labels.flatten() == bone_cluster_idx]
        
        if len(bone_pixels) > 0:
            bone_std = np.std(bone_pixels)
            bone_low = max(0, int(bone_center - 1.5 * bone_std))
            bone_high = min(255, int(bone_center + 1.5 * bone_std))
        else:
            # 如果无法获取，使用默认范围
            bone_low = max(0, int(bone_center - 30))
            bone_high = min(255, int(bone_center + 30))
        
        return bone_low, bone_high
    
    def preprocess(self, image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        图像预处理 - 改进版
        
        关键改进：
        1. 正确识别亮背景/暗背景
        2. 设置严格的骨骼灰度区间
        3. 使用形态学处理去除结缔组织
        4. 过滤太小的噪声区域
        """
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        h, w = gray.shape
        total_pixels = h * w
        
        # ===== 步骤1: 分析背景类型 =====
        margin = max(20, min(h, w) // 20)
        edge_region = np.concatenate([
            gray[:margin, :].flatten(),
            gray[-margin:, :].flatten(),
            gray[:, :margin].flatten(),
            gray[:, -margin:].flatten()
        ])
        bg_mean = np.mean(edge_region)
        bg_std = np.std(edge_region)
        
        # 判断背景类型
        if bg_mean > 127:
            bg_is_bright = True
        else:
            bg_is_bright = False
        
        # ===== 步骤2: 使用KMeans聚类 + YOLOv8骨骼灰度特征 =====
        # 方法1: 如果有YOLOv8信息，使用它
        if hasattr(self, '_bone_gray_from_yolo') and self._bone_gray_from_yolo:
            bone_gray_info = self._bone_gray_from_yolo
            bone_low = bone_gray_info['low']
            bone_high = bone_gray_info['high']
            best_region_count = 0
        
        # 方法2: 使用KMeans聚类自动识别骨骼
        else:
            # KMeans聚类：将灰度分成3类（背景、骨骼、结缔组织）
            bone_low, bone_high = self.kmeans_bone_detection(gray)
            best_region_count = 0
        
        # ===== 步骤3: 使用中心扩展法找到所有骨骼 =====
        # 从YOLOv8检测到的骨骼区域出发，使用区域生长算法找到所有23个骨骼
        bone_mask = self.region_growing_from_yolo_bones(image, gray, bone_low, bone_high)
        
        # ===== 步骤4: 形态学处理 =====
        kernel_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        kernel_medium = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        
        # 轻度闭运算填充骨骼内部小孔洞（减少迭代次数）
        bone_mask = cv2.morphologyEx(bone_mask, cv2.MORPH_CLOSE, kernel_small, iterations=1)
        
        # 轻度开运算去除细小噪声（减少迭代次数）
        bone_mask = cv2.morphologyEx(bone_mask, cv2.MORPH_OPEN, kernel_small, iterations=1)
        
        # ===== 步骤5: 连通组件分析过滤 =====
        # 过滤太小的区域（噪声），但保留小关节
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(bone_mask, connectivity=8)
        
        # 进一步减小最小面积阈值，以便捕获更多小关节
        min_area = max(30, total_pixels * 0.0001)  # 至少0.01%的图像面积
        max_area = total_pixels * 0.5  # 最多50%的图像面积
        
        filtered_mask = np.zeros_like(gray)
        for i in range(1, num_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            # 只保留合理面积的区域
            if min_area <= area <= max_area:
                filtered_mask[labels == i] = 255
        
        # ===== 步骤6: 轻度形态学处理 =====
        filtered_mask = cv2.morphologyEx(filtered_mask, cv2.MORPH_CLOSE, kernel_small, iterations=1)
        
        # 保存骨骼灰度信息用于调试
        self._bone_gray_range = (bone_low, bone_high)
        self._bg_info = {
            'type': 'bright' if bg_is_bright else 'dark',
            'mean': bg_mean,
            'std': bg_std,
            'initial_regions': best_region_count
        }
        
        return filtered_mask, gray
    
    def extract_components_from_regions(self, regions: List[Tuple[int, np.ndarray]]) -> List[BoneComponent]:
        """从染色区域提取骨骼组件"""
        components = []
        
        for label_id, region_mask in regions:
            # 连通组件分析
            num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(region_mask, connectivity=8)
            
            for i in range(1, num_labels):
                area = stats[i, cv2.CC_STAT_AREA]
                # 降低最小面积阈值，保留更多小关节
                if area < 50 or area > self.max_area:  # 从self.min_area=100降低到50
                    continue
                
                x = stats[i, cv2.CC_STAT_LEFT]
                y = stats[i, cv2.CC_STAT_TOP]
                w = stats[i, cv2.CC_STAT_WIDTH]
                h = stats[i, cv2.CC_STAT_HEIGHT]
                cx, cy = centroids[i]
                
                mask = (labels == i).astype(np.uint8) * 255
                
                # 计算几何特征
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if not contours:
                    continue
                
                contour = contours[0]
                perimeter = cv2.arcLength(contour, True)
                aspect_ratio = max(w, h) / (min(w, h) + 1)
                circularity = 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0
                
                hull = cv2.convexHull(contour)
                hull_area = cv2.contourArea(hull)
                solidity = area / hull_area if hull_area > 0 else 0
                
                components.append(BoneComponent(
                    label="",
                    mask=mask,
                    centroid=(cx, cy),
                    bbox=(x, y, w, h),
                    area=area,
                    aspect_ratio=aspect_ratio,
                    circularity=circularity,
                    solidity=solidity,
                    order=label_id
                ))
        
        return components
    
    def classify_by_position(self, components: List[BoneComponent]) -> List[BoneComponent]:
        """基于Y轴位置分类关节类型"""
        if not components:
            return components
        
        sorted_by_y = sorted(components, key=lambda c: c.centroid[1])
        y_values = [c.centroid[1] for c in sorted_by_y]
        y_min, y_max = min(y_values), max(y_values)
        y_range = y_max - y_min if y_max > y_min else 1
        
        for comp in sorted_by_y:
            y_ratio = (comp.centroid[1] - y_min) / y_range
            
            if y_ratio > 0.85:
                comp.label = "Wrist"
            elif y_ratio > 0.65:
                comp.label = "MCP"
            elif y_ratio > 0.45:
                comp.label = "PIP"
            elif y_ratio > 0.25:
                comp.label = "MIP"
            else:
                comp.label = "DIP"
        
        return sorted_by_y
    
    def detect_hand_side_auto(self, components: List[BoneComponent]) -> HandSide:
        """自动检测手性"""
        wrist_components = [c for c in components if c.label == "Wrist"]
        
        if len(wrist_components) >= 2:
            sorted_by_x = sorted(wrist_components, key=lambda c: c.centroid[0])
            
            # 在标准PA位片中,尺骨在左,桡骨在右 -> 左手
            # 但这里我们简单判断:最左边的作为Ulna
            leftmost = sorted_by_x[0]
            rightmost = sorted_by_x[-1]
            
            # 假设X轴左小右大
            if leftmost.centroid[0] < rightmost.centroid[0]:
                return HandSide.LEFT
            else:
                return HandSide.RIGHT
        
        return HandSide.UNKNOWN
    
    def assign_finger_labels(self, components: List[BoneComponent], 
                            hand_side: HandSide) -> List[BoneComponent]:
        """分配具体的指骨标签"""
        groups = {}
        for comp in components:
            if comp.label not in groups:
                groups[comp.label] = []
            groups[comp.label].append(comp)
        
        result = []
        for label, comps in groups.items():
            if label == "Wrist":
                sorted_by_x = sorted(comps, key=lambda c: c.centroid[0])
                if len(sorted_by_x) >= 2:
                    if hand_side == HandSide.LEFT:
                        sorted_by_x[0].label = "Radius"
                        sorted_by_x[1].label = "Ulna"
                    else:
                        sorted_by_x[0].label = "Ulna"
                        sorted_by_x[1].label = "Radius"
                elif len(sorted_by_x) == 1:
                    sorted_by_x[0].label = "Radius"
                result.extend(sorted_by_x)
            else:
                sorted_by_x = sorted(comps, key=lambda c: c.centroid[0])
                n = len(sorted_by_x)
                
                if n >= 1:
                    if hand_side == HandSide.LEFT:
                        if n >= 3:
                            sorted_by_x[0].label = f"{label}Fifth"
                            sorted_by_x[n//2].label = f"{label}Third"
                            sorted_by_x[-1].label = f"{label}First"
                        elif n == 2:
                            sorted_by_x[0].label = f"{label}Third"
                            sorted_by_x[1].label = f"{label}First"
                        else:
                            sorted_by_x[0].label = f"{label}Third"
                    else:
                        if n >= 3:
                            sorted_by_x[0].label = f"{label}First"
                            sorted_by_x[n//2].label = f"{label}Third"
                            sorted_by_x[-1].label = f"{label}Fifth"
                        elif n == 2:
                            sorted_by_x[0].label = f"{label}First"
                            sorted_by_x[1].label = f"{label}Third"
                        else:
                            sorted_by_x[0].label = f"{label}Third"
                
                result.extend(sorted_by_x)
        
        return result
    
    def detect_joints(self, image: np.ndarray, 
                     hand_side: Optional[HandSide] = None) -> Dict:
        """
        主检测流程 - 扫描旋转染色法
        """
        start_time = time.time()
        
        # 清空缓存
        self._clear_scan_cache()
        
        # 预处理
        binary, gray = self.preprocess(image)
        
        # 执行扫描旋转染色法
        regions = self.scanning_rotation_dyeing(binary, max_regions=20)
        
        if not regions:
            return {
                'success': False,
                'error': '扫描旋转染色法未检测到任何骨骼区域',
                'regions': [],
                'hand_side': 'unknown',
                'processing_time': time.time() - start_time
            }
        
        # 提取组件
        components = self.extract_components_from_regions(regions)
        
        if not components:
            return {
                'success': False,
                'error': '未提取到有效的骨骼组件',
                'regions': [],
                'hand_side': 'unknown',
                'processing_time': time.time() - start_time
            }
        
        # 位置分类
        classified = self.classify_by_position(components)
        
        # 自动手性判断和骨骼灰度提取
        bone_gray_info = None
        if hand_side is None:
            # 优先使用YOLOv8检测手性和骨骼灰度特征
            if self.use_yolo_for_hand_side:
                hand_side, bone_gray_info = self.detect_hand_side_with_yolo(image)
                
                # 如果获取到骨骼灰度信息，保存到detector
                if bone_gray_info:
                    self._bone_gray_from_yolo = bone_gray_info
            
            # 如果YOLOv8失败，使用传统方法
            if hand_side is None:
                hand_side = self.detect_hand_side_auto(classified)
        
        # 分配手指标签
        final_components = self.assign_finger_labels(classified, hand_side)
        
        # 整理结果
        results = {
            'success': True,
            'hand_side': hand_side.value if hand_side else 'unknown',
            'total_regions': len(final_components),
            'regions': [],
            'processing_time': time.time() - start_time,
            '染色区域数': len(regions)
        }
        
        for comp in final_components:
            results['regions'].append({
                'label': comp.label,
                'centroid': (int(comp.centroid[0]), int(comp.centroid[1])),
                'bbox': comp.bbox,
                'area': comp.area,
                'aspect_ratio': round(comp.aspect_ratio, 2),
                'circularity': round(comp.circularity, 3),
                'order': comp.order
            })
        
        return results
    
    def visualize(self, image: np.ndarray, results: Dict, 
                output_path: Optional[str] = None,
                round_num: int = 0) -> np.ndarray:
        """
        可视化检测结果 - 使用最长左右宽和最长上下高的矩形框
        
        关键改进：
        1. 使用最小外接矩形（带旋转）
        2. 用最长边作为矩形框的宽或高
        3. 标注关节名称、面积、顺序
        """
        if len(image.shape) == 2:
            vis = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        else:
            vis = image.copy()
        
        if not results['success']:
            cv2.putText(vis, "Detection Failed", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            return vis
        
        color_map = {
            'DIPFirst': (255, 0, 0), 'DIPThird': (0, 255, 0), 'DIPFifth': (0, 0, 255),
            'DIP': (128, 128, 0),
            'MIPFirst': (255, 255, 0), 'MIPThird': (255, 0, 255), 'MIPFifth': (0, 255, 255),
            'MIP': (128, 0, 128),
            'PIPFirst': (0, 255, 255), 'PIPThird': (128, 0, 0), 'PIPFifth': (0, 128, 0),
            'PIP': (0, 128, 128),
            'MCPFirst': (0, 0, 128), 'MCPThird': (128, 128, 0), 'MCPFifth': (128, 0, 128),
            'MCP': (200, 200, 200),
            'Radius': (0, 128, 128),
            'Ulna': (255, 128, 0),
            'Wrist': (128, 128, 128)
        }
        
        for region in results['regions']:
            label = region['label']
            color = color_map.get(label, (255, 255, 255))
            
            x, y, w, h = region['bbox']
            cx, cy = region['centroid']
            
            # 使用最小外接矩形（带旋转）
            if 'mask' in region and region['mask'] is not None:
                mask = region['mask']
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if contours:
                    contour = contours[0]
                    rect = cv2.minAreaRect(contour)
                    box = cv2.boxPoints(rect)
                    box = np.int0(box)
                    cv2.drawContours(vis, [box], 0, color, 2)
                    
                    # 获取矩形框的宽高
                    rect_w, rect_h = rect[1]
                    if rect_w > 0 and rect_h > 0:
                        # 使用最长边作为矩形框的主要尺寸
                        max_side = max(rect_w, rect_h)
                        min_side = min(rect_w, rect_h)
                        rect_center = (int(rect[0][0]), int(rect[0][1]))
                        
                        # 在框中心显示信息
                        info_text = f"{label}"
                        area_text = f"A:{region['area']:.0f}"
                        order_text = f"#{region.get('order', 0)}"
                        
                        # 绘制标签
                        cv2.putText(vis, info_text, 
                                   (rect_center[0] - 30, rect_center[1] - 10), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                        cv2.putText(vis, area_text, 
                                   (rect_center[0] - 30, rect_center[1] + 10), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                        cv2.putText(vis, order_text, 
                                   (rect_center[0] - 30, rect_center[1] + 25), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 0), 1)
            else:
                # 使用普通矩形框
                cv2.rectangle(vis, (x, y), (x + w, y + h), color, 2)
            
            # 绘制质心点
            cv2.circle(vis, (cx, cy), 5, color, -1)
        
        # 显示信息面板
        panel_y = 25
        cv2.putText(vis, f"Round {round_num}", (10, panel_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        cv2.putText(vis, f"Hand: {results['hand_side'].upper()}", (10, panel_y + 25), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.putText(vis, f"Regions: {results['total_regions']}", (10, panel_y + 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.putText(vis, f"Time: {results.get('processing_time', 0):.3f}s", (10, panel_y + 75), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        if output_path:
            cv2.imwrite(output_path, vis)
        
        return vis
    
    def visualize_dyeing_process(self, image: np.ndarray, regions: List[Tuple[int, np.ndarray]],
                                output_path: Optional[str] = None) -> np.ndarray:
        """可视化染色过程"""
        if len(image.shape) == 2:
            vis = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        else:
            vis = image.copy()
        
        for label_id, region_mask in regions:
            color = self.dye_colors[label_id % len(self.dye_colors)]
            
            # 在原图上叠加染色
            colored_region = np.zeros_like(vis)
            colored_region[region_mask > 0] = color
            
            vis = cv2.addWeighted(vis, 0.7, colored_region, 0.3, 0)
        
        if output_path:
            cv2.imwrite(output_path, vis)
        
        return vis


def test_detector(image_path: str):
    """测试检测器"""
    print(f"加载图像: {image_path}")
    image = cv2.imread(image_path)
    if image is None:
        print(f"错误: 无法读取图像 {image_path}")
        return
    
    print(f"图像尺寸: {image.shape}")
    
    # 创建检测器
    detector = ScanningRotationDyeingDetector(
        min_area=100,
        max_area=100000,
        scan_step=15
    )
    
    # 执行检测
    print("\n开始扫描旋转染色法检测...")
    results = detector.detect_joints(image)
    
    print("\n" + "=" * 60)
    print("扫描旋转染色法检测结果")
    print("=" * 60)
    print(f"成功: {results['success']}")
    print(f"手性: {results['hand_side']}")
    print(f"检测到区域数: {results.get('染色区域数', 0)}")
    print(f"有效关节数: {results['total_regions']}")
    print(f"处理时间: {results.get('processing_time', 0):.3f}秒")
    
    if results['success']:
        print("\n关节详情:")
        for i, region in enumerate(results['regions']):
            print(f"  {i+1}. {region['label']:12s} "
                  f"位置:{region['centroid']} "
                  f"面积:{region['area']:.0f}像素 "
                  f"顺序:{region['order']}")
    
    # 可视化结果
    output_path = f"scanning_rotation_result_{os.path.basename(image_path)}"
    detector.visualize(image, results, output_path)
    print(f"\n结果已保存: {output_path}")
    
    return results


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        test_detector(sys.argv[1])
    else:
        print("用法: python traditional_cv_joint_detector.py <image_path>")
        print("示例: python traditional_cv_joint_detector.py check_this_image.jpg")