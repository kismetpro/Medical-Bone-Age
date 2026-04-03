"""
调试DP V3检测和手指分配
"""
import cv2
from dp_bone_detector_v3 import DPV3BoneDetector

detector = DPV3BoneDetector(conf=0.5, imgsz=1024)
image = cv2.imread('test/14717.png')
results = detector.detect(image, target_count=21)

print("="*70)
print("DP V3 检测结果")
print("="*70)
print(f"手性: {results.get('hand_side')}")
print(f"总骨骼数: {results.get('total_regions')}")
print()

print("="*70)
print("YOLO 检测到的骨骼")
print("="*70)

label_counts = {}
for region in results.get('regions', []):
    label = region.get('label', 'Unknown')
    centroid = region.get('centroid', (0, 0))
    label_counts[label] = label_counts.get(label, 0) + 1
    print(f"  {label:30} 位置:({centroid[0]:.0f}, {centroid[1]:.0f})")

print()
print("骨骼统计:")
for label, count in sorted(label_counts.items()):
    print(f"  {label:30}: {count}个")

print()
print("="*70)
print("手指分配测试")
print("="*70)

hand_side = results.get('hand_side', 'unknown')
img_height, img_width = image.shape[:2]

if hand_side == 'left':
    finger_order = ['First', 'Second', 'Third', 'Fourth', 'Fifth']
else:
    finger_order = ['Fifth', 'Fourth', 'Third', 'Second', 'First']

finger_regions_map = {f: [] for f in finger_order}
carpal_regions = []

for region in results.get('regions', []):
    label = region.get('label', 'Unknown')
    centroid = region.get('centroid', (0, 0))

    if 'First' in label:
        finger_regions_map['First'].append(region)
        print(f"✓ {label:30} -> First (拇指)")
    elif label in ['Radius', 'Ulna']:
        carpal_regions.append(region)
        print(f"✓ {label:30} -> 腕骨")
    else:
        print(f"? {label:30} -> 待分配")

non_finger_regions = []
for region in results.get('regions', []):
    label = region.get('label', 'Unknown')
    if 'First' not in label and label not in ['Radius', 'Ulna', 'CarpalBone']:
        non_finger_regions.append(region)

print()
print(f"拇指位置阈值: > {img_width * 0.85:.0f} (85%)")
thumb_positions = [r for r in non_finger_regions if r.get('centroid', (0, 0))[0] > img_width * 0.85]
other_fingers = [r for r in non_finger_regions if r not in thumb_positions]

print(f"拇指候选 (X > {img_width * 0.85:.0f}): {len(thumb_positions)}个")
for r in thumb_positions:
    print(f"  {r.get('label'):30} 位置:({r.get('centroid')[0]:.0f}, {r.get('centroid')[1]:.0f})")

print()
print(f"其他手指骨骼: {len(other_fingers)}个")

if thumb_positions:
    finger_regions_map['First'].extend(thumb_positions)

if hand_side == 'left':
    sorted_by_x = sorted(other_fingers, key=lambda r: r.get('centroid', (0, 0))[0], reverse=True)
else:
    sorted_by_x = sorted(other_fingers, key=lambda r: r.get('centroid', (0, 0))[0])

print(f"排序后 (手性={hand_side}):")
for i, r in enumerate(sorted_by_x):
    print(f"  {i+1}. {r.get('label'):30} 位置:({r.get('centroid')[0]:.0f}, {r.get('centroid')[1]:.0f})")

print()
step = len(sorted_by_x) / 4
finger_labels = ['Second', 'Third', 'Fourth', 'Fifth']
print(f"分配步长: {step:.2f}")

for i, finger in enumerate(finger_labels):
    start_idx = int(i * step)
    end_idx = int((i + 1) * step) if i < 3 else len(sorted_by_x)
    assigned = sorted_by_x[start_idx:end_idx]
    finger_regions_map[finger].extend(assigned)
    print(f"  {finger}: {len(assigned)}个骨骼")

print()
print("="*70)
print("最终手指分配结果")
print("="*70)

for finger in finger_order:
    regions = finger_regions_map[finger]
    if regions:
        print(f"\n{finger}: {len(regions)}个骨骼")
        for r in regions:
            print(f"  - {r.get('label'):30} 位置:({r.get('centroid')[0]:.0f}, {r.get('centroid')[1]:.0f})")
