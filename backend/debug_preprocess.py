import cv2
import numpy as np
from traditional_cv_joint_detector import ImprovedJointDetector

image = cv2.imread('check_this_image.jpg')
detector = ImprovedJointDetector()

# 灰度分析
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
dist_info = detector.analyze_gray_distribution(gray)

print("Gray Analysis:")
print(f"  bone_threshold: {dist_info['bone_threshold']}")
print(f"  bg_threshold: {dist_info['bg_threshold']}")
print(f"  bg_is_bright: {dist_info['bg_is_bright']}")

# 预处理
binary, tissue = detector.preprocess(image)
print(f"\nBinary mask nonzero pixels: {np.sum(binary > 0)}")
print(f"Tissue mask nonzero pixels: {np.sum(tissue > 0)}")

# 连通组件
num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(binary, connectivity=8)
print(f"\nConnected components: {num_labels - 1}")

for i in range(1, min(num_labels, 10)):
    area = stats[i, cv2.CC_STAT_AREA]
    print(f"  Component {i}: area={area}")