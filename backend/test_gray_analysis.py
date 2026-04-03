"""
分析图像灰度分布
用于确定骨骼的真实灰度区间
"""

import cv2
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path


def analyze_gray_distribution(image_path):
    """分析图像灰度分布"""
    # 读取图像
    image = cv2.imread(image_path)
    if image is None:
        print(f"无法读取图像: {image_path}")
        return
    
    # 转换为灰度图
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    print(f"\n{'='*60}")
    print(f"图像分析: {Path(image_path).name}")
    print(f"{'='*60}")
    print(f"图像尺寸: {gray.shape}")
    
    # 基本统计
    print(f"\n灰度值统计:")
    print(f"  最小值: {gray.min()}")
    print(f"  最大值: {gray.max()}")
    print(f"  均值: {gray.mean():.2f}")
    print(f"  标准差: {gray.std():.2f}")
    
    # 计算直方图
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
    hist = hist.flatten()
    
    # 分析灰度分布
    print(f"\n灰度分布分析:")
    
    # 找出主要峰值
    peak_gray = np.argmax(hist)
    print(f"  主峰值位置: {peak_gray}")
    print(f"  主峰值计数: {hist[peak_gray]:.0f}")
    
    # 计算不同灰度区间的像素数
    ranges = [
        (0, 50, "暗区"),
        (50, 100, "次暗区"),
        (100, 150, "中灰区"),
        (150, 200, "次亮区"),
        (200, 256, "亮区")
    ]
    
    print(f"\n灰度区间分布:")
    total_pixels = gray.shape[0] * gray.shape[1]
    for low, high, name in ranges:
        count = np.sum((gray >= low) & (gray < high))
        percentage = count / total_pixels * 100
        print(f"  {name} [{low:>3}-{high:>3}]: {count:>8} 像素 ({percentage:>5.2f}%)")
    
    # 分析边缘区域（应该主要是背景）
    margin = 20
    edge_region = np.concatenate([
        gray[:margin, :].flatten(),
        gray[-margin:, :].flatten(),
        gray[:, :margin].flatten(),
        gray[:, -margin:].flatten()
    ])
    
    print(f"\n边缘区域分析（应该是背景）:")
    print(f"  边缘均值: {edge_region.mean():.2f}")
    print(f"  边缘标准差: {edge_region.std():.2f}")
    print(f"  边缘范围: [{edge_region.min()}, {edge_region.max()}]")
    
    # 判断背景类型
    bg_mean = edge_region.mean()
    if bg_mean > 127:
        bg_type = "亮背景"
        bone_range = (50, bg_mean)  # 骨骼在中间灰度
    else:
        bg_type = "暗背景"
        bone_range = (bg_mean, 200)  # 骨骼在较亮区域
    
    print(f"\n背景类型: {bg_type}")
    print(f"推测骨骼灰度范围: [{bone_range[0]:.0f}, {bone_range[1]:.0f}]")
    
    # 使用Otsu自动阈值
    _, otsu_thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if isinstance(otsu_thresh, np.ndarray):
        otsu_thresh_value = int(otsu_thresh[0, 0])
    else:
        otsu_thresh_value = int(otsu_thresh)
    print(f"\nOtsu自动阈值: {otsu_thresh_value}")
    
    # 尝试不同的阈值
    print(f"\n不同阈值的分割效果:")
    for thresh in [80, 100, 120, 140, otsu_thresh_value]:
        _, binary = cv2.threshold(gray, thresh, 255, cv2.THRESH_BINARY_INV)
        bone_pixels = np.sum(binary > 0)
        bone_percentage = bone_pixels / total_pixels * 100
        print(f"  阈值={thresh:>3}: 骨骼像素={bone_pixels:>7} ({bone_percentage:>5.2f}%)")
    
    # 建议的最佳阈值范围
    print(f"\n💡 建议:")
    print(f"  - 背景类型: {bg_type}")
    print(f"  - 骨骼灰度区间: {bone_range[0]:.0f} - {bone_range[1]:.0f}")
    print(f"  - 推荐阈值: {int((bone_range[0] + bone_range[1]) / 2)}")
    
    return {
        'gray': gray,
        'hist': hist,
        'bg_mean': bg_mean,
        'bg_type': bg_type,
        'bone_range': bone_range,
        'otsu_thresh': otsu_thresh
    }


def main():
    """主函数"""
    test_images = [
        "check_this_image.jpg",
        "../frontend/src/static/AI_logo.jpg"
    ]
    
    for img_path in test_images:
        if Path(img_path).exists():
            analyze_gray_distribution(img_path)
        else:
            print(f"\n图像不存在: {img_path}")


if __name__ == "__main__":
    main()
