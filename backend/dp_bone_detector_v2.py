"""
DP灰度扩展骨骼检测器 V2
使用BFS/并查集对灰度值进行聚类分块，然后DP扩展灰度

流程：
1. BFS聚类分块：将图像按灰度和空间连通性分成若干区域
2. 学习初始灰度范围：从YOLO检测结果中学习
3. DP灰度扩展：dp[i][j] = max(dp[i+1][j], dp[i][j+1])
4. 目标是检测出恰好23个骨骼关节
"""

import cv2
import numpy as np
from ultralytics import YOLO
from typing import List, Dict, Optional, Tuple
from collections import deque
import os


class DPV2BoneDetector:
    """
    DP灰度扩展骨骼检测器 V2
    先BFS聚类分块，再DP灰度扩展
    """
    
    def __init__(self, model_path: str = None, conf: float = 0.5, imgsz: int = 1024):
        if model_path is None:
            model_path = os.path.join(
                os.path.dirname(__file__), 
                "app", "models", "recognize", "best.pt"
            )
        
        self.model_path = model_path
        self.conf = conf
        self.imgsz = imgsz
        self.model = None
        
        if os.path.exists(model_path):
            self.model = YOLO(model_path)
            print(f"✅ YOLO模型加载成功: {model_path}")
        
        self.class_names_cn = {
            'DistalPhalanx': '远节指骨',
            'MCP': '掌指关节',
            'MCPFirst': '拇指掌指关节',
            'MiddlePhalanx': '中节指骨',
            'ProximalPhalanx': '近节指骨',
            'Radius': '桡骨',
            'Ulna': '尺骨'
        }
    
    def detect(self, image: np.ndarray, target_count: int = 23) -> Dict:
        """
        DP灰度扩展检测流程 V2
        """
        try:
            orig_h, orig_w = image.shape[:2]
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image.copy()
            
            # Step 1: BFS聚类分块
            print("\nStep 1: BFS聚类分块...")
            initial_blocks = self._bfs_clustering(gray)
            print(f"  初始分块数量: {len(initial_blocks)}")
            
            # Step 2: YOLO检测获取初始灰度范围
            print("Step 2: YOLO检测并学习初始灰度范围...")
            yolo_results = self._yolo_detect(image)
            print(f"  YOLO检测到 {len(yolo_results['regions'])} 个骨骼")
            
            initial_gray_range = self._learn_initial_gray_range(gray, yolo_results['regions'])
            print(f"  初始灰度范围: [{initial_gray_range[0]}, {initial_gray_range[1]}]")
            
            # Step 3: DP灰度扩展
            print(f"Step 3: DP灰度扩展，目标{target_count}个骨骼...")
            print(f"  DP算法: dp[i][j] = max(dp[i+1][j], dp[i][j+1])")
            
            best_gray_range, dp_history = self._dp_gray_expansion_v2(
                gray, 
                initial_blocks,
                initial_gray_range, 
                target_count
            )
            
            print(f"  最佳灰度范围: [{best_gray_range[0]}, {best_gray_range[1]}]")
            print(f"  最终检测数量: {dp_history[-1][2] if dp_history else 0}")
            
            # Step 4: 使用最佳灰度范围检测
            print("Step 4: 使用最佳灰度范围检测...")
            regions = self._detect_with_gray_range(gray, best_gray_range, initial_blocks)
            print(f"  检测到 {len(regions)} 个骨骼")
            
            # Step 5: 分类和合并
            print("Step 5: 骨骼分类...")
            classified = self._classify_and_merge(regions, yolo_results['regions'])
            
            hand_side = self._detect_hand_side(classified)
            
            return {
                'success': True,
                'hand_side': hand_side,
                'total_regions': len(classified),
                'initial_blocks': len(initial_blocks),
                'initial_gray_range': initial_gray_range,
                'best_gray_range': best_gray_range,
                'regions': classified,
                'dp_history': dp_history,
                'yolo_regions': yolo_results['regions']
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e), 'regions': []}
    
    def _bfs_clustering(self, gray: np.ndarray, gray_tolerance: int = 10) -> List[Dict]:
        """
        BFS聚类分块算法
        
        将图像按灰度相似性和空间连通性分成若干区域
        
        Args:
            gray: 灰度图像
            gray_tolerance: 灰度相似性容忍度
        
        Returns:
            分块列表，每个块包含：centroid, area, gray_mean, gray_std, bbox
        """
        h, w = gray.shape
        visited = np.zeros((h, w), dtype=bool)
        blocks = []
        
        def bfs_flood_fill(start_x: int, start_y: int) -> Tuple[List[Tuple[int, int]], float, float]:
            """
            BFS洪水填充，从起始点开始填充所有灰度相近的连通区域
            
            Returns:
                (像素列表, 灰度均值, 灰度标准差)
            """
            pixels = []
            queue = deque([(start_x, start_y)])
            visited[start_y, start_x] = True
            
            base_gray = gray[start_y, start_x]
            
            while queue:
                x, y = queue.popleft()
                pixels.append((x, y))
                
                # 4连通领域
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nx, ny = x + dx, y + dy
                    
                    if 0 <= nx < w and 0 <= ny < h:
                        if not visited[ny, nx]:
                            pixel_gray = gray[ny, nx]
                            # 灰度相似性检查
                            if abs(int(pixel_gray) - int(base_gray)) <= gray_tolerance:
                                visited[ny, nx] = True
                                queue.append((nx, ny))
            
            # 计算统计信息
            if pixels:
                pixel_values = [gray[y, x] for x, y in pixels]
                gray_mean = np.mean(pixel_values)
                gray_std = np.std(pixel_values)
            else:
                gray_mean = base_gray
                gray_std = 0
            
            return pixels, gray_mean, gray_std
        
        # 扫描所有像素
        for y in range(h):
            for x in range(w):
                if not visited[y, x]:
                    pixels, gray_mean, gray_std = bfs_flood_fill(x, y)
                    
                    if len(pixels) > 100:  # 只保留有意义的块
                        # 计算几何特征
                        xs, ys = zip(*pixels)
                        x_min, x_max = min(xs), max(xs)
                        y_min, y_max = min(ys), max(ys)
                        cx = (x_min + x_max) // 2
                        cy = (y_min + y_max) // 2
                        
                        blocks.append({
                            'pixels': pixels,
                            'centroid': (cx, cy),
                            'area': len(pixels),
                            'bbox': (x_min, y_min, x_max - x_min, y_max - y_min),
                            'bbox_coords': (x_min, y_min, x_max, y_max),
                            'gray_mean': gray_mean,
                            'gray_std': gray_std,
                            'gray_min': min([gray[y, x] for x, y in pixels]) if pixels else 0,
                            'gray_max': max([gray[y, x] for x, y in pixels]) if pixels else 255
                        })
        
        # 按面积降序排序
        blocks.sort(key=lambda b: b['area'], reverse=True)
        
        return blocks
    
    def _yolo_detect(self, image: np.ndarray) -> Dict:
        """YOLO检测"""
        orig_h, orig_w = image.shape[:2]
        resized_image = cv2.resize(image, (self.imgsz, self.imgsz), interpolation=cv2.INTER_LINEAR)
        
        results = self.model.predict(resized_image, imgsz=self.imgsz, conf=self.conf, verbose=False)
        
        if not results or len(results) == 0:
            return {'regions': [], 'hand_side': 'unknown'}
        
        result = results[0]
        boxes = result.boxes
        
        if boxes is None or len(boxes) == 0:
            return {'regions': [], 'hand_side': 'unknown'}
        
        regions = []
        scale_x = orig_w / self.imgsz
        scale_y = orig_h / self.imgsz
        
        for box in boxes:
            cls_id = int(box.cls[0])
            cls_name = result.names[cls_id]
            cls_name_cn = self.class_names_cn.get(cls_name, cls_name)
            
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            x1_orig = int(x1 * scale_x)
            y1_orig = int(y1 * scale_y)
            x2_orig = int(x2 * scale_x)
            y2_orig = int(y2 * scale_y)
            
            cx = (x1_orig + x2_orig) // 2
            cy = (y1_orig + y2_orig) // 2
            
            regions.append({
                'label': cls_name,
                'label_cn': cls_name_cn,
                'centroid': (cx, cy),
                'bbox_coords': (x1_orig, y1_orig, x2_orig, y2_orig),
                'area': (x2_orig - x1_orig) * (y2_orig - y1_orig),
                'confidence': float(box.conf[0])
            })
        
        return {'regions': regions, 'hand_side': self._detect_hand_side(regions)}
    
    def _learn_initial_gray_range(self, gray: np.ndarray, regions: List[Dict]) -> Tuple[int, int]:
        """学习初始灰度范围"""
        bone_pixels = []
        
        for region in regions:
            x1, y1, x2, y2 = region['bbox_coords']
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(gray.shape[1], x2), min(gray.shape[0], y2)
            
            roi = gray[y1:y2, x1:x2]
            
            if roi.size > 0:
                _, bone_mask = cv2.threshold(roi, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                bone_pixels_in_roi = roi[bone_mask > 0]
                
                if len(bone_pixels_in_roi) > 0:
                    bone_pixels.extend(bone_pixels_in_roi.tolist())
        
        if not bone_pixels:
            return (80, 180)
        
        bone_pixels = np.array(bone_pixels)
        bone_mean = np.mean(bone_pixels)
        bone_std = np.std(bone_pixels)
        
        low = max(0, int(bone_mean - 1.5 * bone_std))
        high = min(255, int(bone_mean + 1.5 * bone_std))
        
        return (low, high)
    
    def _dp_gray_expansion_v2(self, gray: np.ndarray, 
                              initial_blocks: List[Dict],
                              initial_range: Tuple[int, int], 
                              target_count: int) -> Tuple[Tuple[int, int], List]:
        """
        DP灰度扩展算法 V2
        
        基于初始分块，根据灰度范围筛选块
        dp[i][j] = max(dp[i+1][j], dp[i][j+1])
        
        Returns:
            (最佳灰度范围, DP历史)
        """
        init_low, init_high = initial_range
        
        def count_bones_with_blocks(gray_low: int, gray_high: int) -> int:
            """
            根据灰度范围筛选块并统计骨骼数量
            """
            count = 0
            for block in initial_blocks:
                block_gray_min = block['gray_min']
                block_gray_max = block['gray_max']
                
                # 检查块的灰度是否与目标范围重叠
                if block_gray_max >= gray_low and block_gray_min <= gray_high:
                    area = block['area']
                    # 骨骼块面积通常在500-20000像素
                    if 500 <= area <= 20000:
                        count += 1
            
            return count
        
        # DP历史
        dp_history = []
        
        # 初始计数
        initial_count = count_bones_with_blocks(init_low, init_high)
        dp_history.append((init_low, init_high, initial_count))
        print(f"  初始范围 [{init_low}, {init_high}]: {initial_count} 个骨骼")
        
        # 向外扩展灰度范围
        low, high = init_low, init_high
        max_expansion = 80
        step = 2
        
        for i in range(max_expansion // step):
            new_low = max(0, low - step)
            new_high = min(255, high + step)
            
            count = count_bones_with_blocks(new_low, new_high)
            dp_history.append((new_low, new_high, count))
            
            if count >= target_count:
                print(f"  步骤 {i}: 达到目标 {count} >= {target_count}")
                return (new_low, new_high), dp_history
            
            if i % 5 == 0:
                print(f"  步骤 {i}: [{new_low}, {new_high}] = {count}")
            
            low, high = new_low, new_high
        
        # 找到最接近目标的范围
        best_range = init_low, init_high
        best_count = initial_count
        min_diff = abs(initial_count - target_count)
        
        for l in range(max(0, init_low - max_expansion), min(256, init_high + max_expansion), step):
            for h in range(l, min(256, init_high + max_expansion), step):
                count = count_bones_with_blocks(l, h)
                diff = abs(count - target_count)
                
                if diff < min_diff:
                    min_diff = diff
                    best_count = count
                    best_range = (l, h)
        
        return best_range, dp_history
    
    def _detect_with_gray_range(self, gray: np.ndarray, 
                                gray_range: Tuple[int, int],
                                initial_blocks: List[Dict]) -> List[Dict]:
        """使用灰度范围从分块中检测骨骼"""
        low, high = gray_range
        
        regions = []
        for block in initial_blocks:
            block_gray_min = block['gray_min']
            block_gray_max = block['gray_max']
            
            # 检查块的灰度是否与目标范围重叠
            if block_gray_max >= low and block_gray_min <= high:
                area = block['area']
                
                if 500 <= area <= 20000:
                    regions.append({
                        'centroid': block['centroid'],
                        'bbox': block['bbox'],
                        'bbox_coords': block['bbox_coords'],
                        'area': block['area'],
                        'gray_mean': block['gray_mean'],
                        'gray_std': block['gray_std']
                    })
        
        return regions
    
    def _classify_and_merge(self, regions: List[Dict], yolo_regions: List[Dict]) -> List[Dict]:
        """基于YOLO结果对检测到的骨骼进行分类"""
        classified = []
        
        for region in regions:
            cx, cy = region['centroid']
            best_match = None
            min_dist = float('inf')
            
            for yolo_region in yolo_regions:
                yolo_cx, yolo_cy = yolo_region['centroid']
                dist = np.sqrt((cx - yolo_cx)**2 + (cy - yolo_cy)**2)
                
                if dist < min_dist:
                    min_dist = dist
                    best_match = yolo_region
            
            if best_match and min_dist < 50:
                classified.append({
                    'label': best_match['label'],
                    'label_cn': best_match['label_cn'],
                    'centroid': region['centroid'],
                    'bbox': region['bbox'],
                    'bbox_coords': region['bbox_coords'],
                    'area': region['area'],
                    'confidence': best_match['confidence'],
                    'source': 'yolo',
                    'match_distance': min_dist
                })
            else:
                classified.append({
                    'label': 'Unknown',
                    'label_cn': '待分类',
                    'centroid': region['centroid'],
                    'bbox': region['bbox'],
                    'bbox_coords': region['bbox_coords'],
                    'area': region['area'],
                    'confidence': 0.5,
                    'source': 'bfs_dp'
                })
        
        return classified
    
    def _detect_hand_side(self, regions: List[Dict]) -> str:
        """判断手性"""
        radius_regions = [r for r in regions if r['label'] == 'Radius']
        ulna_regions = [r for r in regions if r['label'] == 'Ulna']
        
        if not radius_regions or not ulna_regions:
            return 'unknown'
        
        radius_cx = radius_regions[0]['centroid'][0]
        ulna_cx = ulna_regions[0]['centroid'][0]
        
        return 'left' if ulna_cx < radius_cx else 'right'
    
    def visualize(self, image: np.ndarray, results: Dict, 
                 output_path: str = None) -> np.ndarray:
        """可视化"""
        if len(image.shape) == 2:
            vis = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        else:
            vis = image.copy()
        
        if not results['success']:
            cv2.putText(vis, "Detection Failed", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            return vis
        
        yolo_color = (0, 255, 0)
        dp_color = (255, 0, 0)
        
        for region in results['regions']:
            source = region.get('source', 'yolo')
            color = yolo_color if source == 'yolo' else dp_color
            
            x1, y1, x2, y2 = region['bbox_coords']
            cx, cy = region['centroid']
            
            cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2)
            cv2.circle(vis, (cx, cy), 5, color, -1)
            
            label_text = f"{region['label_cn']}"
            cv2.putText(vis, label_text, (x1, y1 - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        # 信息面板
        panel_y = 25
        cv2.putText(vis, f"Hand: {results['hand_side'].upper()}", 
                   (10, panel_y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        if 'initial_blocks' in results:
            cv2.putText(vis, f"BFS Blocks: {results['initial_blocks']}", 
                       (10, panel_y + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
        
        if 'best_gray_range' in results:
            gray_range = results['best_gray_range']
            cv2.putText(vis, f"Gray: [{gray_range[0]}, {gray_range[1]}]", 
                       (10, panel_y + 45), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)
        
        cv2.putText(vis, f"Total: {results['total_regions']}", 
                   (10, panel_y + 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        
        if output_path:
            cv2.imwrite(output_path, vis)
        
        return vis


def test_dp_v2_detector():
    """测试DP灰度扩展检测器 V2"""
    test_images = ["check_this_image.jpg"]
    
    print("\n" + "="*70)
    print("🔬 DP灰度扩展骨骼检测器 V2")
    print("="*70)
    print("算法流程:")
    print("1. BFS聚类分块")
    print("2. YOLO检测学习初始灰度")
    print("3. DP灰度扩展: dp[i][j] = max(dp[i+1][j], dp[i][j+1])")
    print("4. 目标: 23个骨骼关节")
    print("="*70)
    
    detector = DPV2BoneDetector(conf=0.5, imgsz=1024)
    
    for img_path in test_images:
        if not os.path.exists(img_path):
            print(f"⚠️ 图像不存在: {img_path}")
            continue
        
        print(f"\n{'='*70}")
        print(f"🖼️  测试图像: {img_path}")
        print('='*70)
        
        image = cv2.imread(img_path)
        if image is None:
            print("❌ 无法读取图像")
            continue
        
        print(f"图像尺寸: {image.shape}")
        
        # 执行DP检测
        results = detector.detect(image, target_count=23)
        
        print("\n" + "="*60)
        print("检测结果")
        print("="*60)
        
        if results['success']:
            print(f"✅ 手性: {results['hand_side']}")
            print(f"✅ BFS初始分块: {results['initial_blocks']}")
            print(f"✅ 总计: {results['total_regions']} 个骨骼")
            print(f"✅ 初始灰度范围: [{results['initial_gray_range'][0]}, {results['initial_gray_range'][1]}]")
            print(f"✅ 最佳灰度范围: [{results['best_gray_range'][0]}, {results['best_gray_range'][1]}]")
            
            print("\nDP扩展历史:")
            for i, (low, high, count) in enumerate(results['dp_history']):
                if i % 5 == 0 or i == len(results['dp_history']) - 1:
                    print(f"  步骤 {i:>2}: [{low:>3}, {high:>3}] = {count}")
            
            print("\n所有检测到的骨骼:")
            for i, region in enumerate(results['regions'], 1):
                source_tag = "[YOLO]" if region['source'] == 'yolo' else "[BFS]"
                print(f"{i:>2}. {source_tag} {region['label_cn']:>8} 位置:{region['centroid']} 面积:{region['area']:.0f}")
            
            # 可视化
            output_path = f"dp_v2_result_{os.path.basename(img_path)}"
            detector.visualize(image, results, output_path)
            print(f"\n💾 结果已保存: {output_path}")
            
        else:
            print(f"❌ 检测失败: {results.get('error')}")
    
    print("\n" + "="*70)
    print("✅ 测试完成")
    print("="*70)


if __name__ == "__main__":
    test_dp_v2_detector()
