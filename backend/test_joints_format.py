"""
测试DP V3返回的关节数据格式
"""

import cv2
import json
from dp_bone_detector_v3 import DPV3BoneDetector

detector = DPV3BoneDetector(conf=0.5, imgsz=1024)
image = cv2.imread('test/14717.png')
results = detector.detect(image, target_count=23)

print('=== DP V3 Results ===')
print('Total regions:', results.get('total_regions'))
print('Hand side:', results.get('hand_side'))
print()

joints = {}
label_counter = {}

for region in results.get('regions', []):
    label = region.get('label', 'Unknown')
    label_cn = region.get('label_cn', label)
    bbox_coords = region.get('bbox_coords', [0, 0, 0, 0])
    x1, y1, x2, y2 = bbox_coords

    if label in label_counter:
        label_counter[label] += 1
        joint_key = f"{label}_{label_counter[label]}"
    else:
        label_counter[label] = 0
        joint_key = label

    joints[joint_key] = {
        "type": label_cn,
        "score": round(region.get('confidence', 0.5), 4),
        "bbox_xyxy": [round(float(x1), 2), round(float(y1), 2), round(float(x2), 2), round(float(y2), 2)],
        "source": region.get('source', 'unknown'),
        "coord": [
            round(region['centroid'][0] / image.shape[1], 4),
            round(region['centroid'][1] / image.shape[0], 4),
            round((x2 - x1) / image.shape[1], 4),
            round((y2 - y1) / image.shape[0], 4)
        ]
    }

print('=== Formatted Joints ===')
print(f'Total joints: {len(joints)}')
print()

print('Joint keys and types:')
for i, (key, value) in enumerate(joints.items(), 1):
    print(f'{i:2}. {key:25} -> {value["type"]:15} bbox: {value["bbox_xyxy"]}')
