"""
调试DP V3返回的数据格式
"""
import cv2
import json
from dp_bone_detector_v3 import DPV3BoneDetector

detector = DPV3BoneDetector(conf=0.5, imgsz=1024)
image = cv2.imread('test/14717.png')
results = detector.detect(image, target_count=23)

print('=== DP V3 Return Format ===')
print('Success:', results.get('success'))
print('Total regions:', results.get('total_regions'))
print('Hand side:', results.get('hand_side'))
print()
print('=== First 3 Regions ===')
for i, region in enumerate(results.get('regions', [])[:3]):
    print(f"{i+1}. Label: {region.get('label')}")
    print(f"   Label CN: {region.get('label_cn')}")
    print(f"   Bbox coords: {region.get('bbox_coords')}")
    print(f"   Centroid: {region.get('centroid')}")
    print(f"   Score: {region.get('confidence')}")
    print()
    print(f"   Full region dict: {region}")
