"""
DP灰度扩展骨骼检测器
使用动态规划找到最佳灰度边界，目标是检测出23个骨骼关节

DP[i][j] = 在灰度范围 [i, j] 下能检测到的骨骼数量
DP[i][j] = max(DP[i+1][j], DP[i][j+1])

初始 i, j 从YOLO模型学到的灰度边界开始
通过扩展灰度范围，逐步增加检测数量，直到恰好23个
"""

import cv2
import numpy as np
from ultralytics import YOLO
from typing import List, Dict, Optional, Tuple
import os


class DPBoneDetector:
    """
    DP灰度扩展骨骼检测器
    """
    
    def __init__(self, model_path: str = None, conf: float = 0.5, imgsz: int = 1024):
        """初始化"""
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
        DP灰度扩展检测流程
        
        Args:
            image: 输入图像
            target_count: 目标检测数量（默认23）
        
        Returns:
            检测结果
        """
        if self.model is None:
            return {'success': False, 'error': '模型未加载', 'regions': []}
        
        try:
            orig_h, orig_w = image.shape[:2]
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image.copy()
            
            # Step 1: YOLO检测21个骨骼，获取灰度范围
            print("Step 1: YOLO检测并学习初始灰度范围...")
            yolo_results = self._yolo_detect(image)
            initial_gray_range = self._learn_initial_gray_range(gray, yolo_results['regions'])
            print(f"  初始灰度范围: [{initial_gray_range[0]}, {initial_gray_range[1]}]")
            
            # Step 2: DP灰度扩展
            print(f"Step 2: DP灰度扩展，目标是检测{target_count}个骨骼...")
            print(f"  使用DP算法: dp[i][j] = max(dp[i+1][j], dp[i][j+1])")
            
            best_gray_range, detection_history = self._dp_gray_expansion(
                gray, 
                initial_gray_range, 
                target_count
            )
            
            print(f"  最佳灰度范围: [{best_gray_range[0]}, {best_gray_range[1]}]")
            print(f"  最终检测数量: {detection_history[-1][2] if detection_history else 0}")
            
            # Step 3: 使用最佳灰度范围检测骨骼
            print("Step 3: 使用最佳灰度范围检测骨骼...")
            regions = self._detect_bones_with_gray_range(gray, best_gray_range)
            print(f"  检测到 {len(regions)} 个骨骼")
            
            # Step 4: 分类和标记
            print("Step 4: 骨骼分类...")
            classified_regions = self._classify_bones(regions, yolo_results['regions'])
            
            # 判断手性
            hand_side = self._detect_hand_side(classified_regions)
            
            return {
                'success': True,
                'hand_side': hand_side,
                'total_regions': len(classified_regions),
                'initial_gray_range': initial_gray_range,
                'best_gray_range': best_gray_range,
                'regions': classified_regions,
                'detection_history': detection_history,
                'yolo_regions': yolo_results['regions']
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e), 'regions': []}
    
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
            area = (x2_orig - x1_orig) * (y2_orig - y1_orig)
            
            regions.append({
                'label': cls_name,
                'label_cn': cls_name_cn,
                'centroid': (cx, cy),
                'bbox_coords': (x1_orig, y1_orig, x2_orig, y2_orig),
                'area': area,
                'confidence': float(box.conf[0])
            })
        
        return {'regions': regions, 'hand_side': self._detect_hand_side(regions)}
    
    def _learn_initial_gray_range(self, gray: np.ndarray, regions: List[Dict]) -> Tuple[int, int]:
        """学习YOLO检测骨骼的初始灰度范围"""
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
        
        # 以均值为中心，±1.5倍标准差作为初始范围
        low = max(0, int(bone_mean - 1.5 * bone_std))
        high = min(255, int(bone_mean + 1.5 * bone_std))
        
        return (low, high)
    
    def _dp_gray_expansion(self, gray: np.ndarray, 
                           initial_range: Tuple[int, int], 
                           target_count: int) -> Tuple[Tuple[int, int], List]:
        """
        DP灰度扩展算法
        
        DP[i][j] = 在灰度范围 [i, j] 下能检测到的骨骼数量
        DP[i][j] = max(DP[i+1][j], DP[i][j+1])
        
        Args:
            gray: 灰度图像
            initial_range: 初始灰度范围
            target_count: 目标检测数量
        
        Returns:
            (最佳灰度范围, 检测历史)
        """
        # DP表：dp[i][j] = 在灰度[i,j]范围内检测到的骨骼数量
        # 初始化为-1表示未计算
        dp = np.full((256, 256), -1, dtype=np.int32)
        
        # 初始化已知值：初始范围能检测到的骨骼数量
        init_low, init_high = initial_range
        
        def count_bones(low: int, high: int) -> int:
            """计算在灰度范围[low, high]内能检测到的骨骼数量"""
            if low < 0 or high > 255 or low > high:
                return 0
            
            # 创建骨骼掩码
            bone_mask = np.zeros_like(gray, dtype=np.uint8)
            bone_mask[(gray >= low) & (gray <= high)] = 255
            
            # 连通组件分析
            num_labels, _, stats, _ = cv2.connectedComponentsWithStats(bone_mask, connectivity=8)
            
            # 统计合理面积的区域数量
            count = 0
            for i in range(1, num_labels):
                area = stats[i, cv2.CC_STAT_AREA]
                # 骨骼区域面积通常在500-20000像素之间
                if 500 <= area <= 20000:
                    count += 1
            
            return count
        
        # DP递归计算
        def dp_recursive(low: int, high: int) -> int:
            """DP递归计算"""
            if low < 0 or high > 255 or low > high:
                return 0
            
            if low == high:
                # 单一灰度值，计算检测数量
                return count_bones(low, high)
            
            # 如果已经计算过，直接返回
            if dp[low, high] != -1:
                return dp[low, high]
            
            # DP状态转移
            # dp[i][j] = max(dp[i+1][j], dp[i][j+1])
            down = dp_recursive(low + 1, high)
            right = dp_recursive(low, high + 1)
            
            dp[low, high] = max(down, right)
            return dp[low, high]
        
        # 从初始范围开始DP计算
        print(f"  开始DP计算，从初始范围 [{init_low}, {init_high}] ...")
        
        # 先计算初始范围能检测到多少
        initial_count = count_bones(init_low, init_high)
        print(f"  初始范围检测数量: {initial_count}")
        
        # 记录检测历史
        detection_history = [(init_low, init_high, initial_count)]
        
        # DP计算初始范围
        dp_recursive(init_low, init_high)
        
        # 从初始范围向外扩展
        low, high = init_low, init_high
        max_expansion = 100  # 最大扩展步数
        expansion_step = 1
        
        for step in range(max_expansion):
            # 检查当前范围是否达到目标
            current_count = count_bones(low, high)
            
            if current_count >= target_count:
                print(f"  步骤 {step}: 达到目标 {current_count} >= {target_count}")
                detection_history.append((low, high, current_count))
                break
            
            # 选择扩展方向：优先扩展能增加更多骨骼的方向
            count_left = count_bones(low - expansion_step, high)
            count_right = count_bones(low, high + expansion_step)
            count_both = count_bones(low - expansion_step, high + expansion_step)
            
            if count_both > max(count_left, count_right):
                # 同时扩展两边
                low = max(0, low - expansion_step)
                high = min(255, high + expansion_step)
            elif count_left >= count_right:
                # 扩展左边
                low = max(0, low - expansion_step)
            else:
                # 扩展右边
                high = min(255, high + expansion_step)
            
            new_count = count_bones(low, high)
            detection_history.append((low, high, new_count))
            
            if step % 10 == 0:
                print(f"  步骤 {step}: 范围=[{low}, {high}], 检测数量={new_count}")
        
        # 找到最接近目标的范围
        best_range = init_low, init_high
        best_count = initial_count
        min_diff = abs(initial_count - target_count)
        
        for low_test in range(max(0, init_low - max_expansion), min(255, init_high + max_expansion)):
            for high_test in range(low_test, min(256, init_high + max_expansion)):
                count = count_bones(low_test, high_test)
                diff = abs(count - target_count)
                
                if diff < min_diff:
                    min_diff = diff
                    best_count = count
                    best_range = (low_test, high_test)
        
        return best_range, detection_history
    
    def _detect_bones_with_gray_range(self, gray: np.ndarray, 
                                      gray_range: Tuple[int, int]) -> List[Dict]:
        """使用灰度范围检测骨骼"""
        low, high = gray_range
        
        bone_mask = np.zeros_like(gray, dtype=np.uint8)
        bone_mask[(gray >= low) & (gray <= high)] = 255
        
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(bone_mask, connectivity=8)
        
        regions = []
        for i in range(1, num_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            
            if 500 <= area <= 20000:
                x = stats[i, cv2.CC_STAT_LEFT]
                y = stats[i, cv2.CC_STAT_TOP]
                w = stats[i, cv2.CC_STAT_WIDTH]
                h = stats[i, cv2.CC_STAT_HEIGHT]
                cx, cy = int(centroids[i][0]), int(centroids[i][1])
                
                regions.append({
                    'centroid': (cx, cy),
                    'bbox': (x, y, w, h),
                    'bbox_coords': (x, y, x + w, y + h),
                    'area': area
                })
        
        return regions
    
    def _classify_bones(self, regions: List[Dict], yolo_regions: List[Dict]) -> List[Dict]:
        """基于YOLO结果对检测到的骨骼进行分类"""
        # 使用YOLO的区域作为参考
        classified = []
        
        for region in regions:
            cx, cy = region['centroid']
            best_match = None
            min_dist = float('inf')
            
            # 找到最近的YOLO区域
            for yolo_region in yolo_regions:
                yolo_cx, yolo_cy = yolo_region['centroid']
                dist = np.sqrt((cx - yolo_cx)**2 + (cy - yolo_cy)**2)
                
                if dist < min_dist:
                    min_dist = dist
                    best_match = yolo_region
            
            if best_match and min_dist < 50:  # 距离阈值
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
                # 无法匹配到YOLO区域，标记为待分类
                classified.append({
                    'label': 'Unknown',
                    'label_cn': '待分类',
                    'centroid': region['centroid'],
                    'bbox': region['bbox'],
                    'bbox_coords': region['bbox_coords'],
                    'area': region['area'],
                    'confidence': 0.5,
                    'source': 'floodfill'
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
        
        # YOLO检测区域（绿色）
        yolo_color = (0, 255, 0)
        # DP检测区域（蓝色）
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
        
        if 'best_gray_range' in results:
            gray_range = results['best_gray_range']
            cv2.putText(vis, f"Gray: [{gray_range[0]}, {gray_range[1]}]", 
                       (10, panel_y + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        
        cv2.putText(vis, f"Total: {results['total_regions']}", 
                   (10, panel_y + 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        
        if 'detection_history' in results:
            history = results['detection_history']
            if history:
                last = history[-1]
                cv2.putText(vis, f"DP: [{last[0]}, {last[1]}] = {last[2]}", 
                           (10, panel_y + 75), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 0), 1)
        
        if output_path:
            cv2.imwrite(output_path, vis)
        
        return vis


def test_dp_detector():
    """测试DP灰度扩展检测器"""
    test_images = ["check_this_image.jpg"]
    
    print("\n" + "="*70)
    print("🔬 DP灰度扩展骨骼检测器测试")
    print("="*70)
    print("DP算法: dp[i][j] = max(dp[i+1][j], dp[i][j+1])")
    print("目标: 检测出23个骨骼关节")
    print("="*70)
    
    detector = DPBoneDetector(conf=0.5, imgsz=1024)
    
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
            print(f"✅ 总计: {results['total_regions']} 个骨骼")
            print(f"✅ 初始灰度范围: [{results['initial_gray_range'][0]}, {results['initial_gray_range'][1]}]")
            print(f"✅ 最佳灰度范围: [{results['best_gray_range'][0]}, {results['best_gray_range'][1]}]")
            
            print("\n检测历史:")
            for i, (low, high, count) in enumerate(results['detection_history']):
                if i % 10 == 0 or i == len(results['detection_history']) - 1:
                    print(f"  步骤 {i:>2}: 范围=[{low:>3}, {high:>3}], 检测={count}")
            
            print("\n所有检测到的骨骼:")
            for i, region in enumerate(results['regions'], 1):
                source_tag = "[YOLO]" if region['source'] == 'yolo' else "[DP]"
                print(f"{i:>2}. {source_tag} {region['label_cn']:>8} 位置:{region['centroid']} 面积:{region['area']:.0f}")
            
            # 可视化
            output_path = f"dp_result_{os.path.basename(img_path)}"
            detector.visualize(image, results, output_path)
            print(f"\n💾 结果已保存: {output_path}")
            
        else:
            print(f"❌ 检测失败: {results.get('error')}")
    
    print("\n" + "="*70)
    print("✅ 测试完成")
    print("="*70)


if __name__ == "__main__":
    test_dp_detector()
