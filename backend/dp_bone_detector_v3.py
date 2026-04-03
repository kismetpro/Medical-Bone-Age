"""
DP灰度扩展骨骼检测器 V3
使用BFS/并查集(Union-Find)对灰度值进行聚类分块，并去重合并重叠区域

关键改进：
1. BFS聚类分块
2. Union-Find合并重叠的分块（去重）
3. 基于YOLO区域进行遮罩（避免YOLO和BFS重叠）
4. DP灰度扩展找到恰好23个骨骼
"""

import cv2
import numpy as np
from ultralytics import YOLO
from typing import List, Dict, Optional, Tuple
from collections import deque
import os


class DPV3BoneDetector:
    """
    DP灰度扩展骨骼检测器 V3
    添加去重和遮罩机制
    """
    
    def __init__(self, model_path: str = None, conf: float = 0.5, imgsz: int = 1024):
        if model_path is None:
            model_path = os.path.join(
                os.path.dirname(__file__), 
                "app", "models", "recognize", 
                "best.pt"
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
        """DP灰度扩展检测流程 V3（带去重）"""
        try:
            orig_h, orig_w = image.shape[:2]
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image.copy()
            
            # Step 1: YOLO检测
            print("\nStep 1: YOLO检测...")
            yolo_results = self._yolo_detect(image)
            print(f"  YOLO检测到 {len(yolo_results['regions'])} 个骨骼")
            
            # 创建YOLO遮罩（用于排除已检测区域）
            yolo_mask = self._create_yolo_mask(gray, yolo_results['regions'])
            print(f"  YOLO遮罩已创建（排除 {np.sum(yolo_mask > 0) / (orig_h * orig_w) * 100:.1f}% 区域）")
            
            # Step 2: BFS聚类分块（仅在非YOLO区域）
            print("\nStep 2: BFS聚类分块（排除YOLO区域）...")
            initial_blocks = self._bfs_clustering_with_mask(gray, yolo_mask)
            print(f"  BFS初始分块（不含YOLO区域）: {len(initial_blocks)}")
            
            # Step 3: Union-Find去重合并重叠的分块
            print("\nStep 3: Union-Find去重合并重叠分块...")
            merged_blocks = self._union_find_merge(initial_blocks)
            print(f"  去重合并后: {len(merged_blocks)} 个独立骨骼")
            
            # Step 4: 学习初始灰度范围
            print("\nStep 4: 学习初始灰度范围...")
            initial_gray_range = self._learn_initial_gray_range(gray, yolo_results['regions'])
            print(f"  初始灰度范围: [{initial_gray_range[0]}, {initial_gray_range[1]}]")
            
            # Step 5: DP灰度扩展
            print(f"\nStep 5: DP灰度扩展，目标{target_count}个骨骼...")
            best_gray_range, dp_history = self._dp_gray_expansion_v3(
                gray, 
                merged_blocks,
                yolo_results['regions'],
                initial_gray_range, 
                target_count
            )
            print(f"  最佳灰度范围: [{best_gray_range[0]}, {best_gray_range[1]}]")
            print(f"  最终检测数量: {dp_history[-1][2] if dp_history else 0}")
            
            # Step 6: 使用最佳灰度范围检测
            print("\nStep 6: 使用最佳灰度范围检测...")
            regions = self._detect_with_gray_range(gray, best_gray_range, merged_blocks)
            print(f"  检测到 {len(regions)} 个骨骼")
            
            # Step 7: 合并YOLO和BFS结果
            print("\nStep 7: 合并YOLO和BFS检测结果...")
            all_regions = yolo_results['regions'] + regions
            hand_side = self._detect_hand_side(all_regions)
            
            return {
                'success': True,
                'hand_side': hand_side,
                'total_regions': len(all_regions),
                'yolo_count': len(yolo_results['regions']),
                'bfs_count': len(regions),
                'initial_gray_range': initial_gray_range,
                'best_gray_range': best_gray_range,
                'regions': all_regions,
                'dp_history': dp_history,
                'merged_blocks': len(merged_blocks)
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e), 'regions': []}
    
    def _create_yolo_mask(self, gray: np.ndarray, regions: List[Dict], padding: int = 5) -> np.ndarray:
        """创建YOLO遮罩，排除已检测区域"""
        h, w = gray.shape
        mask = np.zeros((h, w), dtype=np.uint8)
        
        for region in regions:
            x1, y1, x2, y2 = region['bbox_coords']
            
            # 扩大区域
            x1 = max(0, x1 - padding)
            y1 = max(0, y1 - padding)
            x2 = min(w, x2 + padding)
            y2 = min(h, y2 + padding)
            
            mask[y1:y2, x1:x2] = 255
        
        return mask
    
    def _bfs_clustering_with_mask(self, gray: np.ndarray, mask: np.ndarray, gray_tolerance: int = 10) -> List[Dict]:
        """BFS聚类分块（排除遮罩区域）"""
        h, w = gray.shape
        visited = np.zeros((h, w), dtype=bool)
        blocks = []
        
        def bfs_flood_fill(start_x: int, start_y: int) -> Tuple[List[Tuple[int, int]], float, float]:
            """BFS洪水填充"""
            pixels = []
            queue = deque([(start_x, start_y)])
            visited[start_y, start_x] = True
            
            base_gray = gray[start_y, start_x]
            
            while queue:
                x, y = queue.popleft()
                pixels.append((x, y))
                
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nx, ny = x + dx, y + dy
                    
                    if 0 <= nx < w and 0 <= ny < h:
                        if not visited[ny, nx] and mask[ny, nx] == 0:  # 排除遮罩区域
                            pixel_gray = gray[ny, nx]
                            if abs(int(pixel_gray) - int(base_gray)) <= gray_tolerance:
                                visited[ny, nx] = True
                                queue.append((nx, ny))
            
            if pixels:
                pixel_values = [gray[y, x] for x, y in pixels]
                gray_mean = np.mean(pixel_values)
                gray_std = np.std(pixel_values)
            else:
                gray_mean = base_gray
                gray_std = 0
            
            return pixels, gray_mean, gray_std
        
        # 扫描所有非遮罩像素
        for y in range(h):
            for x in range(w):
                if not visited[y, x] and mask[y, x] == 0:
                    pixels, gray_mean, gray_std = bfs_flood_fill(x, y)
                    
                    if len(pixels) > 100:
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
        
        blocks.sort(key=lambda b: b['area'], reverse=True)
        return blocks
    
    def _union_find_merge(self, blocks: List[Dict], overlap_threshold: float = 0.3) -> List[Dict]:
        """
        Union-Find去重合并重叠的分块
        
        Args:
            blocks: BFS分块列表
            overlap_threshold: 重叠阈值（如果两个块重叠面积超过较小块面积的30%，则合并）
        
        Returns:
            合并后的块列表
        """
        if not blocks:
            return []
        
        n = len(blocks)
        parent = list(range(n))
        rank = [0] * n
        
        def find(x: int) -> int:
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]
        
        def union(x: int, y: int):
            px, py = find(x), find(y)
            if px == py:
                return
            if rank[px] < rank[py]:
                px, py = py, px
            parent[py] = px
            if rank[px] == rank[py]:
                rank[px] += 1
        
        def boxes_overlap(box1: Tuple, box2: Tuple) -> float:
            """检查两个边界框是否重叠，并返回重叠比例"""
            x1_min, y1_min, x1_max, y1_max = box1
            x2_min, y2_min, x2_max, y2_max = box2
            
            # 计算重叠区域
            x_overlap = max(0, min(x1_max, x2_max) - max(x1_min, x2_min))
            y_overlap = max(0, min(y1_max, y2_max) - max(y1_min, y2_min))
            overlap_area = x_overlap * y_overlap
            
            if overlap_area == 0:
                return 0.0
            
            # 计算重叠比例
            area1 = (x1_max - x1_min) * (y1_max - y1_min)
            area2 = (x2_max - x2_min) * (y2_max - y2_min)
            min_area = min(area1, area2)
            
            return overlap_area / min_area if min_area > 0 else 0.0
        
        # 检查所有块对的重叠
        for i in range(n):
            for j in range(i + 1, n):
                overlap_ratio = boxes_overlap(blocks[i]['bbox_coords'], blocks[j]['bbox_coords'])
                if overlap_ratio > overlap_threshold:
                    union(i, j)
        
        # 合并同一集合的块
        merged_groups = {}
        for i in range(n):
            root = find(i)
            if root not in merged_groups:
                merged_groups[root] = []
            merged_groups[root].append(blocks[i])
        
        # 创建合并后的块
        merged_blocks = []
        for root, group in merged_groups.items():
            if len(group) == 1:
                merged_blocks.append(group[0])
            else:
                # 合并多个块
                all_pixels = []
                all_x, all_y = [], []
                gray_means = []
                
                for block in group:
                    all_pixels.extend(block['pixels'])
                    all_x.extend([p[0] for p in block['pixels']])
                    all_y.extend([p[1] for p in block['pixels']])
                    gray_means.append(block['gray_mean'])
                
                x_min, x_max = min(all_x), max(all_x)
                y_min, y_max = min(all_y), max(all_y)
                cx = (x_min + x_max) // 2
                cy = (y_min + y_max) // 2
                
                merged_blocks.append({
                    'pixels': all_pixels,
                    'centroid': (cx, cy),
                    'area': len(all_pixels),
                    'bbox': (x_min, y_min, x_max - x_min, y_max - y_min),
                    'bbox_coords': (x_min, y_min, x_max, y_max),
                    'gray_mean': np.mean(gray_means),
                    'gray_std': np.std(gray_means) if len(gray_means) > 1 else 0,
                    'gray_min': min([p[0] for p in all_pixels]) if all_pixels else 0,
                    'gray_max': max([p[0] for p in all_pixels]) if all_pixels else 255
                })
        
        merged_blocks.sort(key=lambda b: b['area'], reverse=True)
        return merged_blocks
    
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
    
    def _dp_gray_expansion_v3(self, gray: np.ndarray, 
                              merged_blocks: List[Dict],
                              yolo_regions: List[Dict],
                              initial_range: Tuple[int, int], 
                              target_count: int) -> Tuple[Tuple[int, int], List]:
        """
        DP灰度扩展算法 V3
        
        目标：YOLO(21) + BFS补充 = 恰好23个骨骼
        
        Returns:
            (最佳灰度范围, DP历史)
        """
        init_low, init_high = initial_range
        yolo_count = len(yolo_regions)
        target_bfs_count = target_count - yolo_count  # BFS需要补充的数量
        
        def count_bfs_bones(gray_low: int, gray_high: int) -> int:
            """统计BFS分块中符合条件的骨骼数量"""
            count = 0
            for block in merged_blocks:
                block_gray_min = block['gray_min']
                block_gray_max = block['gray_max']
                
                if block_gray_max >= gray_low and block_gray_min <= gray_high:
                    area = block['area']
                    if 500 <= area <= 20000:
                        count += 1
            
            return count
        
        # DP历史
        dp_history = []
        
        # 初始计数
        initial_bfs_count = count_bfs_bones(init_low, init_high)
        total_count = yolo_count + initial_bfs_count
        dp_history.append((init_low, init_high, initial_bfs_count, total_count))
        print(f"  初始: BFS={initial_bfs_count}, 总计={total_count}")
        
        # 向外扩展灰度范围
        low, high = init_low, init_high
        max_expansion = 80
        step = 2
        
        for i in range(max_expansion // step):
            new_low = max(0, low - step)
            new_high = min(255, high + step)
            
            bfs_count = count_bfs_bones(new_low, new_high)
            total = yolo_count + bfs_count
            dp_history.append((new_low, new_high, bfs_count, total))
            
            if total >= target_count:
                print(f"  步骤 {i}: BFS={bfs_count}, 总计={total} >= {target_count} ✅")
                return (new_low, new_high), dp_history
            
            if i % 5 == 0:
                print(f"  步骤 {i}: BFS={bfs_count}, 总计={total}")
            
            low, high = new_low, new_high
        
        # 找到最接近目标的范围
        best_range = init_low, init_high
        best_total = total_count
        min_diff = abs(total_count - target_count)
        
        for l in range(max(0, init_low - max_expansion), min(256, init_high + max_expansion), step):
            for h in range(l, min(256, init_high + max_expansion), step):
                bfs_count = count_bfs_bones(l, h)
                total = yolo_count + bfs_count
                diff = abs(total - target_count)
                
                if diff < min_diff:
                    min_diff = diff
                    best_total = total
                    best_range = (l, h)
        
        return best_range, dp_history
    
    def _detect_with_gray_range(self, gray: np.ndarray, gray_range: Tuple[int, int], merged_blocks: List[Dict]) -> List[Dict]:
        """使用灰度范围从合并后的分块中检测骨骼"""
        low, high = gray_range
        
        regions = []
        for block in merged_blocks:
            block_gray_min = block['gray_min']
            block_gray_max = block['gray_max']
            
            if block_gray_max >= low and block_gray_min <= high:
                area = block['area']
                
                if 500 <= area <= 20000:
                    regions.append({
                        'label': 'CarpalBone',
                        'label_cn': '腕骨',
                        'centroid': block['centroid'],
                        'bbox': block['bbox'],
                        'bbox_coords': block['bbox_coords'],
                        'area': block['area'],
                        'confidence': 0.5,
                        'source': 'bfs_dp'
                    })
        
        return regions
    
    def _detect_hand_side(self, regions: List[Dict]) -> str:
        """判断手性"""
        radius_regions = [r for r in regions if r.get('label') == 'Radius']
        ulna_regions = [r for r in regions if r.get('label') == 'Ulna']
        
        if not radius_regions or not ulna_regions:
            return 'unknown'
        
        radius_cx = radius_regions[0]['centroid'][0]
        ulna_cx = ulna_regions[0]['centroid'][0]
        
        return 'left' if ulna_cx < radius_cx else 'right'
    
    def visualize(self, image: np.ndarray, results: Dict, output_path: str = None) -> np.ndarray:
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
        bfs_color = (255, 0, 0)
        
        for region in results['regions']:
            source = region.get('source', 'yolo')
            color = yolo_color if source == 'yolo' else bfs_color
            
            x1, y1, x2, y2 = region['bbox_coords']
            cx, cy = region['centroid']
            
            cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2)
            cv2.circle(vis, (cx, cy), 5, color, -1)
            
            label_text = f"{region.get('label_cn', 'Unknown')}"
            cv2.putText(vis, label_text, (x1, y1 - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        # 信息面板
        panel_y = 25
        cv2.putText(vis, f"Hand: {results['hand_side'].upper()}", 
                   (10, panel_y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        if 'yolo_count' in results and 'bfs_count' in results:
            cv2.putText(vis, f"YOLO: {results['yolo_count']}", 
                       (10, panel_y + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 0), 1)
            cv2.putText(vis, f"BFS: {results['bfs_count']}", 
                       (10, panel_y + 45), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 0, 0), 1)
        
        if 'best_gray_range' in results:
            gray_range = results['best_gray_range']
            cv2.putText(vis, f"Gray: [{gray_range[0]}, {gray_range[1]}]", 
                       (10, panel_y + 65), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)
        
        cv2.putText(vis, f"Total: {results['total_regions']}", 
                   (10, panel_y + 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        
        if output_path:
            cv2.imwrite(output_path, vis)
        
        return vis


def test_dp_v3_detector():
    """测试DP灰度扩展检测器 V3"""
    test_images = ["check_this_image.jpg"]
    
    print("\n" + "="*70)
    print("🔬 DP灰度扩展骨骼检测器 V3（去重版）")
    print("="*70)
    print("算法流程:")
    print("1. YOLO检测21个骨骼")
    print("2. 创建YOLO遮罩排除已检测区域")
    print("3. BFS聚类分块（仅非遮罩区域）")
    print("4. Union-Find去重合并重叠分块")
    print("5. DP灰度扩展: YOLO(21) + BFS(补) = 23")
    print("="*70)
    
    detector = DPV3BoneDetector(conf=0.5, imgsz=1024)
    
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
        
        results = detector.detect(image, target_count=23)
        
        print("\n" + "="*60)
        print("检测结果")
        print("="*60)
        
        if results['success']:
            print(f"✅ 手性: {results['hand_side']}")
            print(f"✅ YOLO检测: {results['yolo_count']} 个")
            print(f"✅ BFS去重后: {results['bfs_count']} 个")
            print(f"✅ 合并后总计: {results['total_regions']} 个")
            print(f"✅ 初始灰度范围: [{results['initial_gray_range'][0]}, {results['initial_gray_range'][1]}]")
            print(f"✅ 最佳灰度范围: [{results['best_gray_range'][0]}, {results['best_gray_range'][1]}]")
            
            print("\nDP扩展历史:")
            for i, (low, high, bfs_cnt, total) in enumerate(results['dp_history']):
                if i % 5 == 0 or i == len(results['dp_history']) - 1:
                    print(f"  步骤 {i:>2}: [{low:>3}, {high:>3}] BFS={bfs_cnt:>2} Total={total:>2}")
            
            print("\n所有检测到的骨骼:")
            yolo_list = [r for r in results['regions'] if r.get('source') == 'yolo']
            bfs_list = [r for r in results['regions'] if r.get('source') != 'yolo']
            
            print(f"\n【YOLO检测 {len(yolo_list)} 个】")
            for i, region in enumerate(yolo_list, 1):
                print(f"  {i:>2}. {region['label_cn']:>10} 位置:{region['centroid']} 面积:{region['area']:.0f}")
            
            if bfs_list:
                print(f"\n【BFS补充 {len(bfs_list)} 个】")
                for i, region in enumerate(bfs_list, 1):
                    print(f"  {i:>2}. {region['label_cn']:>10} 位置:{region['centroid']} 面积:{region['area']:.0f}")
            
            output_path = f"dp_v3_result_{os.path.basename(img_path)}"
            detector.visualize(image, results, output_path)
            print(f"\n💾 结果已保存: {output_path}")
            
        else:
            print(f"❌ 检测失败: {results.get('error')}")
    
    print("\n" + "="*70)
    print("✅ 测试完成")
    print("="*70)


if __name__ == "__main__":
    test_dp_v3_detector()
