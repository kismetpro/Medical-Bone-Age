"""
测试DP V3手指分类功能
"""
import cv2
from dp_bone_detector_v3 import DPV3BoneDetector

detector = DPV3BoneDetector(conf=0.5, imgsz=1024)
image = cv2.imread('test/14717.png')
results = detector.detect(image, target_count=23)

hand_side = results.get('hand_side', 'unknown')

if hand_side == 'left':
    finger_order = ['First', 'Second', 'Third', 'Fourth', 'Fifth']
else:
    finger_order = ['Fifth', 'Fourth', 'Third', 'Second', 'First']

finger_cn = {
    'First': '拇指',
    'Second': '食指',
    'Third': '中指',
    'Fourth': '环指',
    'Fifth': '小指'
}

regions_by_finger = {f: [] for f in finger_order}
for region in results.get('regions', []):
    label = region.get('label', 'Unknown')
    finger_key = None

    if 'First' in label:
        finger_key = 'First'
    elif 'Second' in label:
        finger_key = 'Second'
    elif 'Third' in label:
        finger_key = 'Third'
    elif 'Fourth' in label:
        finger_key = 'Fourth'
    elif 'Fifth' in label:
        finger_key = 'Fifth'

    if finger_key:
        regions_by_finger[finger_key].append(region)

print("="*70)
print(f"DP V3 手指分类测试 - 手性: {hand_side}")
print("="*70)

joints = {}
ordered_joints = []
joint_index = 0

for finger in finger_order:
    finger_regions = regions_by_finger[finger]
    if not finger_regions:
        continue

    sorted_regions = sorted(
        finger_regions,
        key=lambda r: (r.get('centroid', (0, 0))[1], r.get('centroid', (0, 0))[0])
    )

    print(f"\n【{finger_cn[finger]}】({len(sorted_regions)}个)")
    print("-" * 70)

    for region in sorted_regions:
        label = region.get('label', 'Unknown')
        label_cn = region.get('label_cn', label)
        centroid = region.get('centroid', (0, 0))
        bbox = region.get('bbox_coords', [0, 0, 0, 0])

        joint_data = {
            "type": label_cn,
            "label": label,
            "finger": finger,
            "finger_cn": finger_cn[finger],
            "order": joint_index,
            "score": round(region.get('confidence', 0.5), 4),
            "bbox_xyxy": [round(float(bbox[0]), 2), round(float(bbox[1]), 2), round(float(bbox[2]), 2), round(float(bbox[3]), 2)],
            "source": region.get('source', 'unknown'),
            "centroid": centroid
        }

        if label in joints:
            idx = 1
            while f"{label}_{idx}" in joints:
                idx += 1
            joint_key = f"{label}_{idx}"
        else:
            joint_key = label

        joints[joint_key] = joint_data
        ordered_joints.append(joint_data)

        print(f"  {joint_index:2d}. {label:25} 位置:({centroid[0]:.0f}, {centroid[1]:.0f})")
        joint_index += 1

print("\n" + "="*70)
print(f"总计检测到 {len(joints)} 个关节")
print(f"手指顺序: {' → '.join([finger_cn[f] for f in finger_order])}")
print("="*70)
