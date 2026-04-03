"""
使用YOLO模型直接识别所有手部骨骼关节
基于用户训练的best.pt模型
"""

import cv2
import numpy as np
from ultralytics import YOLO
from typing import List, Dict, Optional, Tuple
import os


class YOLOBoneDetector:
    """
    使用YOLO模型直接识别所有骨骼关节
    """
    
    def __init__(self, model_path: str = None, conf: float = 0.5, imgsz: int = 1024):
        """
        初始化YOLO骨骼检测器
        
        Args:
            model_path: 模型路径，默认使用best.pt
            conf: 置信度阈值
            imgsz: 输入图像尺寸
        """
        if model_path is None:
            model_path = os.path.join(
                os.path.dirname(__file__), 
                "app", "models", "recognize", "best.pt"
            )
        
        self.model_path = model_path
        self.conf = conf
        self.imgsz = imgsz
        
        # 加载模型
        if os.path.exists(model_path):
            self.model = YOLO(model_path)
            print(f"✅ YOLO模型加载成功: {model_path}")
        else:
            print(f"❌ 模型文件不存在: {model_path}")
            self.model = None
        
        # 骨骼类别名称映射（中英文）
        self.class_names_cn = {
            'DistalPhalanx': '远节指骨',
            'MCP': '掌指关节',
            'MCPFirst': '拇指掌指关节',
            'MiddlePhalanx': '中节指骨',
            'ProximalPhalanx': '近节指骨',
            'Radius': '桡骨',
            'Ulna': '尺骨'
        }
    
    def detect(self, image: np.ndarray, hand_side: Optional[str] = None) -> Dict:
        """
        使用YOLO检测所有骨骼关节
        
        Args:
            image: 输入图像
            hand_side: 手性（可选，'left' 或 'right'）
        
        Returns:
            检测结果字典
        """
        if self.model is None:
            return {
                'success': False,
                'error': '模型未加载',
                'regions': []
            }
        
        try:
            # 保存原始尺寸
            orig_h, orig_w = image.shape[:2]
            
            # resize到1024x1024
            resized_image = cv2.resize(image, (self.imgsz, self.imgsz), interpolation=cv2.INTER_LINEAR)
            
            # YOLO推理
            results = self.model.predict(
                resized_image, 
                imgsz=self.imgsz,
                conf=self.conf, 
                verbose=False
            )
            
            if not results or len(results) == 0:
                return {
                    'success': False,
                    'error': 'YOLO未检测到任何对象',
                    'regions': [],
                    'hand_side': hand_side or 'unknown'
                }
            
            result = results[0]
            boxes = result.boxes
            
            if boxes is None or len(boxes) == 0:
                return {
                    'success': False,
                    'error': 'YOLO未检测到任何对象',
                    'regions': [],
                    'hand_side': hand_side or 'unknown'
                }
            
            # 解析检测结果
            regions = []
            scale_x = orig_w / self.imgsz
            scale_y = orig_h / self.imgsz
            
            for box in boxes:
                # 获取类别
                cls_id = int(box.cls[0])
                cls_name = result.names[cls_id]
                cls_name_cn = self.class_names_cn.get(cls_name, cls_name)
                
                # 获取边界框坐标（归一化到1024x1024）
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                
                # 映射回原始尺寸
                x1_orig = int(x1 * scale_x)
                y1_orig = int(y1 * scale_y)
                x2_orig = int(x2 * scale_x)
                y2_orig = int(y2 * scale_y)
                
                # 计算中心点
                cx = (x1_orig + x2_orig) // 2
                cy = (y1_orig + y2_orig) // 2
                
                # 计算面积
                area = (x2_orig - x1_orig) * (y2_orig - y1_orig)
                
                # 获取置信度
                confidence = float(box.conf[0])
                
                regions.append({
                    'label': cls_name,
                    'label_cn': cls_name_cn,
                    'centroid': (cx, cy),
                    'bbox': (x1_orig, y1_orig, x2_orig - x1_orig, y2_orig - y1_orig),
                    'bbox_coords': (x1_orig, y1_orig, x2_orig, y2_orig),
                    'area': area,
                    'confidence': confidence,
                    'class_id': cls_id
                })
            
            # 自动判断手性（基于桡骨和尺骨位置）
            if hand_side is None:
                hand_side = self._detect_hand_side(regions)
            
            return {
                'success': True,
                'hand_side': hand_side,
                'total_regions': len(regions),
                'regions': regions
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'regions': []
            }
    
    def _detect_hand_side(self, regions: List[Dict]) -> str:
        """
        根据桡骨和尺骨位置判断手性
        """
        radius_regions = [r for r in regions if r['label'] == 'Radius']
        ulna_regions = [r for r in regions if r['label'] == 'Ulna']
        
        if not radius_regions or not ulna_regions:
            return 'unknown'
        
        # 计算中心点
        radius_cx = radius_regions[0]['centroid'][0]
        ulna_cx = ulna_regions[0]['centroid'][0]
        
        # 在标准PA位片中：
        # 左手：尺骨在左，桡骨在右
        # 右手：桡骨在左，尺骨在右
        if ulna_cx < radius_cx:
            return 'left'
        else:
            return 'right'
    
    def visualize(self, image: np.ndarray, results: Dict, 
                 output_path: str = None, show_labels: bool = True) -> np.ndarray:
        """
        可视化检测结果
        """
        if len(image.shape) == 2:
            vis = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        else:
            vis = image.copy()
        
        if not results['success']:
            cv2.putText(vis, "Detection Failed", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            return vis
        
        # 颜色映射
        color_map = {
            'DistalPhalanx': (255, 0, 0),      # 红色
            'MCP': (0, 255, 0),                # 绿色
            'MCPFirst': (0, 255, 255),         # 黄色
            'MiddlePhalanx': (255, 0, 255),    # 紫色
            'ProximalPhalanx': (0, 128, 255),  # 橙色
            'Radius': (128, 0, 255),            # 粉紫色
            'Ulna': (255, 128, 0)               # 橙色
        }
        
        # 绘制每个检测框
        for i, region in enumerate(results['regions']):
            label = region['label']
            color = color_map.get(label, (255, 255, 255))
            
            x1, y1, x2, y2 = region['bbox_coords']
            cx, cy = region['centroid']
            
            # 绘制边界框
            cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2)
            
            # 绘制中心点
            cv2.circle(vis, (cx, cy), 5, color, -1)
            
            # 绘制标签
            if show_labels:
                conf_text = f"{region['confidence']:.2f}"
                label_text = f"{region['label_cn']} {conf_text}"
                
                cv2.putText(vis, label_text, (x1, y1 - 5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        # 绘制信息面板
        panel_y = 25
        cv2.putText(vis, f"Hand: {results['hand_side'].upper()}", 
                   (10, panel_y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(vis, f"Regions: {results['total_regions']}", 
                   (10, panel_y + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # 绘制图例
        legend_y = panel_y + 60
        for label, color in list(color_map.items())[:7]:
            label_cn = self.class_names_cn.get(label, label)
            cv2.rectangle(vis, (10, legend_y), (30, legend_y + 15), color, -1)
            cv2.putText(vis, label_cn, (35, legend_y + 12), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
            legend_y += 20
        
        if output_path:
            cv2.imwrite(output_path, vis)
        
        return vis


def test_yolo_detector():
    """测试YOLO骨骼检测器"""
    import sys
    
    # 测试图像
    test_images = [
        "check_this_image.jpg",
    ]
    
    print("\n" + "="*70)
    print("🔬 YOLO骨骼关节检测器测试")
    print("="*70)
    
    # 创建检测器
    detector = YOLOBoneDetector(conf=0.5, imgsz=1024)
    
    for img_path in test_images:
        if not os.path.exists(img_path):
            print(f"\n⚠️ 图像不存在: {img_path}")
            continue
        
        print(f"\n{'='*70}")
        print(f"🖼️  测试图像: {img_path}")
        print('='*70)
        
        # 读取图像
        image = cv2.imread(img_path)
        if image is None:
            print(f"❌ 无法读取图像")
            continue
        
        print(f"图像尺寸: {image.shape}")
        
        # 执行检测
        print("\n🔍 执行YOLO检测...")
        results = detector.detect(image)
        
        print("\n" + "="*60)
        print("检测结果")
        print("="*60)
        
        if results['success']:
            print(f"✅ 手性: {results['hand_side']}")
            print(f"✅ 检测到 {results['total_regions']} 个骨骼关节")
            print("\n关节详情:")
            print("-" * 70)
            print(f"{'序号':>4} {'类别':>20} {'中心位置':>20} {'面积':>10} {'置信度':>8}")
            print("-" * 70)
            
            for i, region in enumerate(results['regions'], 1):
                print(f"{i:>4} {region['label_cn']:>20} {str(region['centroid']):>20} "
                      f"{region['area']:>10} {region['confidence']:>8.3f}")
            print("-" * 70)
            
            # 统计各类别数量
            class_counts = {}
            for region in results['regions']:
                label = region['label_cn']
                class_counts[label] = class_counts.get(label, 0) + 1
            
            print("\n各类别数量:")
            for label, count in sorted(class_counts.items()):
                print(f"  {label}: {count}")
            
            # 可视化
            output_path = f"yolo_result_{os.path.basename(img_path)}"
            detector.visualize(image, results, output_path)
            print(f"\n💾 结果已保存: {output_path}")
            
        else:
            print(f"❌ 检测失败: {results.get('error', '未知错误')}")
    
    print("\n" + "="*70)
    print("✅ 测试完成")
    print("="*70)


if __name__ == "__main__":
    test_yolo_detector()
