"""
测试test文件夹下的图片
测试YOLO、DP V3和Hybrid混合检测算法
"""

import cv2
import numpy as np
import os
from yolo_bone_detector import YOLOBoneDetector
from dp_bone_detector_v3 import DPV3BoneDetector
from hybrid_yolo_cv_detector import HybridBoneDetector

test_folder = "test"
output_folder = "test_results"

def create_comparison_visualization(image, results_list, titles, output_path):
    """创建对比可视化"""
    if len(image.shape) == 2:
        vis = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    else:
        vis = image.copy()

    n = len(results_list)
    h, w = vis.shape[:2]

    total_width = w * n
    total_height = h + 100

    comparison = np.zeros((total_height, total_width, 3), dtype=np.uint8)

    for i, (results, title) in enumerate(zip(results_list, titles)):
        start_x = i * w

        if len(results['regions']) > 0:
            color_map = {
                'DistalPhalanx': (255, 0, 0),
                'MCP': (0, 255, 0),
                'MCPFirst': (0, 255, 255),
                'MiddlePhalanx': (255, 0, 255),
                'ProximalPhalanx': (0, 128, 255),
                'Radius': (128, 0, 255),
                'Ulna': (255, 128, 0),
                'CarpalBone': (128, 128, 255)
            }

            for region in results['regions']:
                label = region.get('label', 'Unknown')
                color = color_map.get(label, (255, 255, 255))

                x1, y1, x2, y2 = region['bbox_coords']

                cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2)
                cx, cy = region['centroid']
                cv2.circle(vis, (cx, cy), 5, color, -1)

                label_cn = region.get('label_cn', label)
                cv2.putText(vis, label_cn, (x1, y1 - 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        else:
            cv2.putText(vis, "No detection", (w//4, h//2),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        cv2.putText(vis, f"{title}: {results.get('total_regions', 0)} bones",
                   (10, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        comparison[0:h, start_x:start_x+w] = vis

    title_y = h + 30
    for i, title in enumerate(titles):
        x_pos = i * w + 10
        cv2.putText(comparison, title, (x_pos, title_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

    cv2.imwrite(output_path, comparison)
    print(f"✅ 对比图已保存: {output_path}")

def test_image(image_path, detector_yolo, detector_dpv3, detector_hybrid):
    """测试单张图片"""
    print(f"\n{'='*80}")
    print(f"🖼️  测试图像: {image_path}")
    print('='*80)

    image = cv2.imread(image_path)
    if image is None:
        print(f"❌ 无法读取图像: {image_path}")
        return

    print(f"图像尺寸: {image.shape}")

    results_yolo = detector_yolo.detect(image)
    print(f"\n1️⃣ YOLO检测结果:")
    if results_yolo['success']:
        print(f"   手性: {results_yolo['hand_side']}")
        print(f"   检测到 {results_yolo['total_regions']} 个骨骼")
    else:
        print(f"   检测失败: {results_yolo.get('error')}")

    results_dpv3 = detector_dpv3.detect(image, target_count=23)
    print(f"\n2️⃣ DP V3检测结果:")
    if results_dpv3['success']:
        print(f"   手性: {results_dpv3['hand_side']}")
        print(f"   YOLO检测: {results_dpv3['yolo_count']} 个")
        print(f"   BFS检测: {results_dpv3['bfs_count']} 个")
        print(f"   总计: {results_dpv3['total_regions']} 个")
        print(f"   最佳灰度范围: [{results_dpv3['best_gray_range'][0]}, {results_dpv3['best_gray_range'][1]}]")
    else:
        print(f"   检测失败: {results_dpv3.get('error')}")

    results_hybrid = detector_hybrid.detect(image)
    print(f"\n3️⃣ Hybrid混合检测结果:")
    if results_hybrid['success']:
        print(f"   手性: {results_hybrid['hand_side']}")
        print(f"   YOLO检测: {results_hybrid['yolo_regions']} 个")
        print(f"   补充检测: {results_hybrid['remaining_regions']} 个")
        print(f"   总计: {results_hybrid['total_regions']} 个")
    else:
        print(f"   检测失败: {results_hybrid.get('error')}")

    output_path = os.path.join(output_folder, f"comparison_{os.path.basename(image_path)}")
    create_comparison_visualization(
        image,
        [results_yolo, results_dpv3, results_hybrid],
        ['YOLO', 'DP V3', 'Hybrid'],
        output_path
    )

    print("\n骨骼详情:")
    print("-" * 80)

    all_results = [
        ('YOLO', results_yolo),
        ('DP V3', results_dpv3),
        ('Hybrid', results_hybrid)
    ]

    for name, results in all_results:
        if results['success'] and results['regions']:
            print(f"\n【{name}】检测到的骨骼:")
            for i, region in enumerate(results['regions'], 1):
                label = region.get('label_cn', 'Unknown')
                centroid = region['centroid']
                area = region.get('area', 0)
                print(f"  {i:>2}. {label:>15} 位置:{centroid} 面积:{area:.0f}")

    return results_yolo, results_dpv3, results_hybrid

def main():
    """主函数"""
    print("="*80)
    print("🔬 骨骼检测算法测试")
    print("="*80)
    print("测试test文件夹下的所有图片")
    print("使用三种检测器:")
    print("  1. YOLO检测器 - 纯YOLO模型检测")
    print("  2. DP V3检测器 - DP灰度扩展检测")
    print("  3. Hybrid检测器 - YOLO+传统CV混合检测")
    print("="*80)

    os.makedirs(output_folder, exist_ok=True)

    print("\n初始化检测器...")
    detector_yolo = YOLOBoneDetector(conf=0.5, imgsz=1024)
    detector_dpv3 = DPV3BoneDetector(conf=0.5, imgsz=1024)
    detector_hybrid = HybridBoneDetector(conf=0.5, imgsz=1024)

    test_images = [
        os.path.join(test_folder, "14717.png"),
        os.path.join(test_folder, "14729.png"),
        os.path.join(test_folder, "14735.png"),
        os.path.join(test_folder, "14750.png")
    ]

    for image_path in test_images:
        if os.path.exists(image_path):
            test_image(image_path, detector_yolo, detector_dpv3, detector_hybrid)
        else:
            print(f"\n⚠️ 图像不存在: {image_path}")

    print("\n" + "="*80)
    print("✅ 测试完成")
    print(f"结果保存在: {output_folder}")
    print("="*80)

if __name__ == "__main__":
    main()
