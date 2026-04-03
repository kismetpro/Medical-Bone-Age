import cv2
import numpy as np
from traditional_cv_joint_detector import ImprovedJointDetector

image = cv2.imread('check_this_image.jpg')
detector = ImprovedJointDetector()

gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
dist_info = detector.analyze_gray_distribution(gray)

print('Adaptive Gray Analysis:')
print(f'  Background: mean={dist_info["bg_mean"]:.1f}, is_bright={dist_info["bg_is_bright"]}')
print(f'  Foreground: mean={dist_info["fg_mean"]:.1f}, std={dist_info["fg_std"]:.1f}')
print(f'  Clusters: {[f"{x:.0f}" for x in dist_info["cluster_centers"]]}')
print(f'  Bone threshold: {dist_info["bone_low"]}-{dist_info["bone_high"]}')
print(f'  Tissue threshold: {dist_info["tissue_low"]}-{dist_info["tissue_high"]}')