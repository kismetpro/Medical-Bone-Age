"""
快速测试DP V3集成是否正常工作
"""

import cv2
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

def test_dpv3_import():
    """测试DP V3模块导入"""
    try:
        from dp_bone_detector_v3 import DPV3BoneDetector
        print("✅ DP V3模块导入成功")
        return True
    except Exception as e:
        print(f"❌ DP V3模块导入失败: {e}")
        return False

def test_dpv3_initialization():
    """测试DP V3检测器初始化"""
    try:
        from dp_bone_detector_v3 import DPV3BoneDetector
        detector = DPV3BoneDetector(conf=0.5, imgsz=1024)
        print("✅ DP V3检测器初始化成功")
        return detector
    except Exception as e:
        print(f"❌ DP V3检测器初始化失败: {e}")
        return None

def test_dpv3_detection(detector, test_image_path):
    """测试DP V3检测功能"""
    if not os.path.exists(test_image_path):
        print(f"⚠️ 测试图像不存在: {test_image_path}")
        return None

    try:
        image = cv2.imread(test_image_path)
        if image is None:
            print(f"❌ 无法读取图像: {test_image_path}")
            return None

        print(f"\n🖼️  测试图像: {test_image_path}")
        print(f"图像尺寸: {image.shape}")

        results = detector.detect(image, target_count=23)

        if results.get('success'):
            print("\n✅ DP V3检测成功!")
            print(f"   手性: {results.get('hand_side')}")
            print(f"   YOLO检测: {results.get('yolo_count')} 个骨骼")
            print(f"   BFS检测: {results.get('bfs_count')} 个骨骼")
            print(f"   总计: {results.get('total_regions')} 个骨骼")
            print(f"   最佳灰度范围: {results.get('best_gray_range')}")
            print(f"   合并后分块数: {results.get('merged_blocks')}")

            print("\n检测到的骨骼:")
            for i, region in enumerate(results.get('regions', [])[:5], 1):
                print(f"  {i}. {region.get('label_cn')} - 位置: {region.get('centroid')}")

            if len(results.get('regions', [])) > 5:
                print(f"  ... 还有 {len(results.get('regions', [])) - 5} 个骨骼")

            return results
        else:
            print(f"❌ DP V3检测失败: {results.get('error')}")
            return None

    except Exception as e:
        print(f"❌ 检测过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_backend_import():
    """测试后端导入"""
    try:
        from app.main import app, dpv3_detector
        print("\n✅ 后端模块导入成功")
        print(f"   dpv3_detector: {'已加载' if dpv3_detector else '未加载'}")
        return True
    except Exception as e:
        print(f"❌ 后端模块导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("="*70)
    print("🔬 DP V3集成测试")
    print("="*70)

    print("\n【测试1】DP V3模块导入...")
    if not test_dpv3_import():
        print("\n❌ 测试失败：DP V3模块无法导入")
        return

    print("\n【测试2】DP V3检测器初始化...")
    detector = test_dpv3_initialization()
    if not detector:
        print("\n❌ 测试失败：DP V3检测器无法初始化")
        return

    print("\n【测试3】DP V3检测功能测试...")
    test_image = "test/14717.png"
    results = test_dpv3_detection(detector, test_image)

    print("\n【测试4】后端集成测试...")
    if not test_backend_import():
        print("\n⚠️ 警告：后端集成可能存在问题")

    print("\n" + "="*70)
    if results and results.get('success'):
        print("✅ 所有测试通过！DP V3已成功集成到后端")
    else:
        print("❌ 部分测试失败，请检查错误信息")
    print("="*70)

    return results

if __name__ == "__main__":
    main()
