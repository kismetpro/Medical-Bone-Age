"""
混合检测方案：YOLO + 传统CV
1. YOLO识别21个骨骼关节
2. 学习这21个骨骼的灰度特征
3. 排除这21个区域
4. 用扫描线和FloodFill找剩余的2个腕骨
"""

import cv2
import numpy as np
from ultralytics import YOLO
from typing import List, Dict, Optional, Tuple, Set
from collections import deque
import os


class HybridBoneDetector:
    """
    混合骨骼检测器
    结合YOLO的准确性和传统CV的补充能力
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
    
    def detect(self, image: np.ndarray) -> Dict:
        """
        混合检测流程
        """
        if self.model is None:
            return {'success': False, 'error': '模型未加载', 'regions': []}
        
        try:
            orig_h, orig_w = image.shape[:2]
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image.copy()
            
            # Step 1: YOLO检测21个骨骼
            print("Step 1: YOLO检测骨骼...")
            yolo_results = self._yolo_detect(image)
            print(f"  YOLO检测到 {len(yolo_results['regions'])} 个骨骼")
            
            # Step 2: 学习YOLO检测骨骼的灰度特征
            print("Step 2: 学习骨骼灰度特征...")
            bone_gray_info = self._learn_bone_gray_features(gray, yolo_results['regions'])
            print(f"  骨骼灰度范围: [{bone_gray_info['low']}, {bone_gray_info['high']}]")
            print(f"  骨骼灰度均值: {bone_gray_info['mean']:.2f}")
            print(f"  骨骼灰度标准差: {bone_gray_info['std']:.2f}")
            
            # Step 3: 排除YOLO检测区域
            print("Step 3: 排除已检测区域...")
            excluded_mask = self._create_exclusion_mask(gray, yolo_results['regions'])
            excluded_ratio = np.sum(excluded_mask > 0) / (gray.shape[0] * gray.shape[1]) * 100
            print(f"  排除区域比例: {excluded_ratio:.1f}%")
            
            # Step 4: 在剩余区域用FloodFill找腕骨
            print("Step 4: FloodFill检测剩余骨骼...")
            remaining_regions = self._floodfill_detect_remaining(gray, excluded_mask, bone_gray_info)
            print(f"  找到 {len(remaining_regions)} 个剩余骨骼")
            
            # Step 5: 合并结果
            print("Step 5: 合并检测结果...")
            all_regions = yolo_results['regions'] + remaining_regions
            
            # 判断手性
            hand_side = self._detect_hand_side(all_regions)
            
            return {
                'success': True,
                'hand_side': hand_side,
                'total_regions': len(all_regions),
                'yolo_regions': len(yolo_results['regions']),
                'remaining_regions': len(remaining_regions),
                'regions': all_regions,
                'bone_gray_info': bone_gray_info
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
            confidence = float(box.conf[0])
            
            regions.append({
                'label': cls_name,
                'label_cn': cls_name_cn,
                'centroid': (cx, cy),
                'bbox': (x1_orig, y1_orig, x2_orig - x1_orig, y2_orig - y1_orig),
                'bbox_coords': (x1_orig, y1_orig, x2_orig, y2_orig),
                'area': area,
                'confidence': confidence,
                'source': 'yolo'
            })
        
        hand_side = self._detect_hand_side(regions)
        return {'regions': regions, 'hand_side': hand_side}
    
    def _learn_bone_gray_features(self, gray: np.ndarray, regions: List[Dict]) -> Dict:
        """
        学习YOLO检测骨骼的灰度特征
        """
        bone_pixels = []
        
        for region in regions:
            x1, y1, x2, y2 = region['bbox_coords']
            
            # 确保坐标在有效范围内
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(gray.shape[1], x2)
            y2 = min(gray.shape[0], y2)
            
            # 提取ROI
            roi = gray[y1:y2, x1:x2]
            
            if roi.size > 0:
                # 使用Otsu阈值提取骨骼像素
                _, bone_mask = cv2.threshold(roi, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                bone_pixels_in_roi = roi[bone_mask > 0]
                
                if len(bone_pixels_in_roi) > 0:
                    bone_pixels.extend(bone_pixels_in_roi.tolist())
        
        if not bone_pixels:
            # 如果无法提取，使用默认范围
            return {'low': 100, 'high': 170, 'mean': 135, 'std': 20, 'min': 80, 'max': 200}
        
        bone_pixels = np.array(bone_pixels)
        bone_mean = np.mean(bone_pixels)
        bone_std = np.std(bone_pixels)
        bone_low = max(0, int(bone_mean - 1.5 * bone_std))
        bone_high = min(255, int(bone_mean + 1.5 * bone_std))
        
        return {
            'low': bone_low,
            'high': bone_high,
            'mean': bone_mean,
            'std': bone_std,
            'min': int(np.min(bone_pixels)),
            'max': int(np.max(bone_pixels))
        }
    
    def _create_exclusion_mask(self, gray: np.ndarray, regions: List[Dict]) -> np.ndarray:
        """
        创建排除掩码
        排除YOLO检测到的21个骨骼区域
        """
        h, w = gray.shape
        exclusion_mask = np.zeros((h, w), dtype=np.uint8)
        
        # 扩大排除区域（避免边界重叠）
        padding = 5
        
        for region in regions:
            x1, y1, x2, y2 = region['bbox_coords']
            
            x1 = max(0, x1 - padding)
            y1 = max(0, y1 - padding)
            x2 = min(w, x2 + padding)
            y2 = min(h, y2 + padding)
            
            exclusion_mask[y1:y2, x1:x2] = 255
        
        return exclusion_mask
    
    def _floodfill_detect_remaining(self, gray: np.ndarray, 
                                    exclusion_mask: np.ndarray,
                                    bone_gray_info: Dict) -> List[Dict]:
        """
        使用FloodFill在剩余区域检测腕骨
        """
        h, w = gray.shape
        bone_low = bone_gray_info['low']
        bone_high = bone_gray_info['high']
        
        remaining_regions = []
        
        # 在排除掩码的补集上寻找种子点
        search_mask = cv2.bitwise_not(exclusion_mask)
        
        # 找到所有满足灰度条件的连通区域
        bone_candidate = np.zeros((h, w), dtype=np.uint8)
        bone_candidate[(gray >= bone_low) & (gray <= bone_high)] = 255
        bone_candidate = cv2.bitwise_and(bone_candidate, search_mask)
        
        # 连通组件分析
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(bone_candidate, connectivity=8)
        
        # 选择合适的区域作为腕骨
        for i in range(1, num_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            
            # 腕骨通常面积适中（1000-15000像素）
            if 1000 <= area <= 15000:
                cx, cy = int(centroids[i][0]), int(centroids[i][1])
                
                # 检查是否在图像下半部分（腕骨位置）
                if cy > h * 0.7:
                    # 创建该区域的掩码
                    region_mask = (labels == i).astype(np.uint8) * 255
                    
                    # 计算边界框
                    ys, xs = np.where(region_mask > 0)
                    x1, y1 = np.min(xs), np.min(ys)
                    x2, y2 = np.max(xs), np.max(ys)
                    
                    remaining_regions.append({
                        'label': 'CarpalBone',
                        'label_cn': '腕骨',
                        'centroid': (cx, cy),
                        'bbox': (x2 - x1, y2 - y1, x2 - x1, y2 - y1),
                        'bbox_coords': (x1, y1, x2, y2),
                        'area': area,
                        'confidence': 0.5,
                        'source': 'floodfill'
                    })
        
        return remaining_regions
    
    def _detect_hand_side(self, regions: List[Dict]) -> str:
        """判断手性"""
        radius_regions = [r for r in regions if r['label'] == 'Radius']
        ulna_regions = [r for r in regions if r['label'] == 'Ulna']
        
        if not radius_regions or not ulna_regions:
            return 'unknown'
        
        radius_cx = radius_regions[0]['centroid'][0]
        ulna_cx = ulna_regions[0]['centroid'][0]
        
        if ulna_cx < radius_cx:
            return 'left'
        else:
            return 'right'
    
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
        
        # YOLO检测区域颜色（绿色系）
        yolo_color = (0, 255, 0)
        # FloodFill检测区域颜色（红色系）
        floodfill_color = (0, 0, 255)
        
        for region in results['regions']:
            source = region.get('source', 'yolo')
            color = yolo_color if source == 'yolo' else floodfill_color
            
            x1, y1, x2, y2 = region['bbox_coords']
            cx, cy = region['centroid']
            
            # 绘制边界框
            cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2)
            
            # 绘制中心点
            cv2.circle(vis, (cx, cy), 5, color, -1)
            
            # 绘制标签
            label_text = f"{region['label_cn']}"
            if source == 'floodfill':
                label_text += " (补检)"
            
            cv2.putText(vis, label_text, (x1, y1 - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        # 绘制信息面板
        panel_y = 25
        cv2.putText(vis, f"Hand: {results['hand_side'].upper()}", 
                   (10, panel_y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(vis, f"YOLO: {results['yolo_regions']}", 
                   (10, panel_y + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 0), 2)
        cv2.putText(vis, f"Remaining: {results['remaining_regions']}", 
                   (10, panel_y + 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 200), 2)
        cv2.putText(vis, f"Total: {results['total_regions']}", 
                   (10, panel_y + 75), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        
        if output_path:
            cv2.imwrite(output_path, vis)
        
        return vis


def test_hybrid_detector():
    """测试混合检测器"""
    test_images = ["check_this_image.jpg"]
    
    print("\n" + "="*70)
    print("🔬 混合检测器测试 (YOLO + FloodFill)")
    print("="*70)
    
    detector = HybridBoneDetector(conf=0.5, imgsz=1024)
    
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
        
        # 执行混合检测
        results = detector.detect(image)
        
        print("\n" + "="*60)
        print("检测结果")
        print("="*60)
        
        if results['success']:
            print(f"✅ 手性: {results['hand_side']}")
            print(f"✅ YOLO检测: {results['yolo_regions']} 个")
            print(f"✅ FloodFill补检: {results['remaining_regions']} 个")
            print(f"✅ 总计: {results['total_regions']} 个")
            
            if 'bone_gray_info' in results:
                info = results['bone_gray_info']
                print(f"\n骨骼灰度特征:")
                print(f"  灰度范围: [{info['low']}, {info['high']}]")
                print(f"  均值: {info['mean']:.2f}")
                print(f"  标准差: {info['std']:.2f}")
            
            print("\n所有检测到的骨骼:")
            print("-" * 70)
            for i, region in enumerate(results['regions'], 1):
                source_tag = "[YOLO]" if region['source'] == 'yolo' else "[补检]"
                print(f"{i:>2}. {source_tag} {region['label_cn']:>8} 位置:{region['centroid']} 面积:{region['area']:.0f}")
            
            # 可视化
            output_path = f"hybrid_result_{os.path.basename(img_path)}"
            detector.visualize(image, results, output_path)
            print(f"\n💾 结果已保存: {output_path}")
            
        else:
            print(f"❌ 检测失败: {results.get('error')}")
    
    print("\n" + "="*70)
    print("✅ 测试完成")
    print("="*70)


if __name__ == "__main__":
    test_hybrid_detector()
