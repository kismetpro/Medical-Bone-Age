"""
测试扫描旋转染色法小关节检测器
使用优化后的V4算法
"""

import cv2
import sys
import os
import time

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from traditional_cv_joint_detector import ScanningRotationDyeingDetector, HandSide


def print_results(results):
    """打印检测结果"""
    if not results['success']:
        print(f"❌ 检测失败: {results.get('error', '未知错误')}")
        return
    
    print(f"\n✅ 检测成功")
    print(f"   手性: {results['hand_side']}")
    print(f"   染色区域数: {results.get('染色区域数', 0)}")
    print(f"   有效关节数: {results['total_regions']}")
    print(f"   处理时间: {results.get('processing_time', 0):.3f}秒")
    
    if results['regions']:
        print(f"\n📋 关节详情:")
        print("-" * 70)
        print(f"{'序号':>4} {'标签':>12} {'质心位置':>20} {'面积':>10} {'顺序':>6}")
        print("-" * 70)
        for i, region in enumerate(results['regions'], 1):
            centroid_str = f"({region['centroid'][0]}, {region['centroid'][1]})"
            print(f"{i:>4} {region['label']:>12} {centroid_str:>20} {region['area']:>10.0f} {region['order']:>6}")
        print("-" * 70)


def main():
    """主测试函数"""
    # 只测试check_this_image.jpg
    test_images = [
        "check_this_image.jpg"
    ]
    
    print("\n" + "="*70)
    print("🔬 扫描旋转染色法小关节检测器测试")
    print("="*70)
    
    for img_path in test_images:
        if not os.path.exists(img_path):
            print(f"\n⚠️  跳过不存在的图像: {img_path}")
            continue
        
        print(f"\n{'='*70}")
        print(f"🖼️  测试图像: {img_path}")
        print('='*70)
        
        # 读取图像
        image = cv2.imread(img_path)
        if image is None:
            print(f"❌ 错误: 无法读取图像")
            continue
        
        print(f"📐 图像尺寸: {image.shape[1]}x{image.shape[0]}")
        
        # 创建检测器 (扫描旋转染色法)
        print("\n⚙️  初始化扫描旋转染色法检测器...")
        print("   启用YOLOv8手性检测...")
        detector = ScanningRotationDyeingDetector(
            min_area=100,
            max_area=100000,
            scan_step=15,  # 旋转扫描角度步长
            use_yolo_for_hand_side=True  # 使用YOLOv8检测手性
        )
        
        # 测试1: 自动判断手性
        print("\n" + "-"*70)
        print("📌 测试1: 自动判断手性")
        print("-"*70)
        start_time = time.time()
        results_auto = detector.detect_joints(image, hand_side=None)
        
        # 显示骨骼灰度信息
        if hasattr(detector, '_bone_gray_range') and hasattr(detector, '_bg_info'):
            print(f"\n🔬 骨骼灰度分析:")
            print(f"   背景类型: {detector._bg_info['type']}")
            print(f"   背景均值: {detector._bg_info['mean']:.2f}")
            print(f"   骨骼灰度区间: [{detector._bone_gray_range[0]}, {detector._bone_gray_range[1]}]")
        
        # 显示YOLOv8提取的骨骼灰度信息
        if hasattr(detector, '_bone_gray_from_yolo') and detector._bone_gray_from_yolo:
            yolo_info = detector._bone_gray_from_yolo
            print(f"\n🤖 YOLOv8骨骼灰度特征:")
            print(f"   骨骼灰度区间: [{yolo_info['low']}, {yolo_info['high']}]")
            print(f"   骨骼均值: {yolo_info['mean']:.2f}")
            print(f"   骨骼标准差: {yolo_info['std']:.2f}")
            print(f"   骨骼范围: [{yolo_info['min']}, {yolo_info['max']}]")
        
        print_results(results_auto)
        
        # 可视化并保存
        output_path = f"scanning_rotation_result_{os.path.basename(img_path)}"
        detector.visualize(image, results_auto, output_path)
        print(f"\n💾 结果可视化已保存: {output_path}")
        
        # 测试2: 指定左手
        print("\n" + "-"*70)
        print("📌 测试2: 指定左手")
        print("-"*70)
        results_left = detector.detect_joints(image, hand_side=HandSide.LEFT)
        print_results(results_left)
        
        # 测试3: 指定右手
        print("\n" + "-"*70)
        print("📌 测试3: 指定右手")
        print("-"*70)
        results_right = detector.detect_joints(image, hand_side=HandSide.RIGHT)
        print_results(results_right)
        
        # 输出总结
        print("\n" + "="*70)
        print("📊 测试总结")
        print("="*70)
        print(f"图像: {img_path}")
        print(f"自动检测手性: {results_auto['hand_side']}")
        print(f"检测到关节数: {results_auto['total_regions']}")
        print(f"处理时间: {time.time() - start_time:.3f}秒")
        print("="*70)


if __name__ == "__main__":
    main()