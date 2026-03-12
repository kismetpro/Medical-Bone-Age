# #训练小关节识别模型

# import os
# import xml.etree.ElementTree as ET
# from glob import glob
# from tqdm import tqdm
# import shutil

# # --- 配置区 ---
# data_sources = [
#     {'name': 'set1', 'img': '/kaggle/input/xiaoguanjiefenji/VOC2007/JPEGImages', 'xml': '/kaggle/input/xiaoguanjiefenji/VOC2007/Annotations'},
#     {'name': 'set2', 'img': '/kaggle/input/13hhhhh/xml', 'xml': '/kaggle/input/13hhhhh/image'}
# ]

# save_path = '/kaggle/working/merged_data'
# classes = ['DistalPhalanx', 'MCP', 'MCPFirst', 'MiddlePhalanx', 'ProximalPhalanx', 'Radius', 'Ulna']

# # 清理旧目录并重建
# if os.path.exists(save_path):
#     shutil.rmtree(save_path)
# for p in ['images/train', 'labels/train']:
#     os.makedirs(os.path.join(save_path, p), exist_ok=True)

# def convert(size, box):
#     dw = 1. / size[0]
#     dh = 1. / size[1]
#     x = (box[0] + box[1]) / 2.0
#     y = (box[2] + box[3]) / 2.0
#     w = box[1] - box[0]
#     h = box[3] - box[2]
#     return (x * dw, y * dh, w * dw, h * dh)

# # --- 执行合并 ---
# print("开始合并数据集（已启用防覆盖逻辑）...")
# for source in data_sources:
#     prefix = source['name']
#     xml_files = glob(os.path.join(source['xml'], '*.xml'))

#     for xml_path in tqdm(xml_files, desc=f"处理 {prefix}"):
#         tree = ET.parse(xml_path)
#         root = tree.getroot()
#         file_id = os.path.splitext(os.path.basename(xml_path))[0]

#         # 新的文件名：前缀 + 原文件名
#         new_file_id = f"{prefix}_{file_id}"

#         # 1. 查找并复制图片
#         img_exts = ['.png', '.jpg', '.jpeg', '.PNG', '.JPG']
#         src_img = None
#         current_ext = ""
#         for ext in img_exts:
#             temp_path = os.path.join(source['img'], file_id + ext)
#             if os.path.exists(temp_path):
#                 src_img = temp_path
#                 current_ext = ext
#                 break

#         if src_img:
#             # 复制图片到新路径，使用新名字
#             shutil.copy(src_img, os.path.join(save_path, 'images/train', new_file_id + current_ext))

#             # 2. 解析 XML 并写入新名字的标签文件
#             width_node = root.find('size/width')
#             height_node = root.find('size/height')
#             if width_node is None or int(width_node.text) == 0:
#                 continue # 跳过无效标注

#             width = int(width_node.text)
#             height = int(height_node.text)

#             label_file = os.path.join(save_path, 'labels/train', new_file_id + '.txt')
#             with open(label_file, 'w') as f:
#                 for obj in root.iter('object'):
#                     cls_name = obj.find('name').text
#                     if cls_name not in classes: continue
#                     cls_id = classes.index(cls_name)
#                     xmlbox = obj.find('bndbox')
#                     b = (float(xmlbox.find('xmin').text), float(xmlbox.find('xmax').text),
#                          float(xmlbox.find('ymin').text), float(xmlbox.find('ymax').text))
#                     bb = convert((width, height), b)
#                     f.write(f"{cls_id} {' '.join([f'{a:.6f}' for a in bb])}\n")

# total_imgs = len(os.listdir(os.path.join(save_path, 'images/train')))
# total_labels = len(os.listdir(os.path.join(save_path, 'labels/train')))
# print(total_labels)
# print(f"\n✅ 合并完成！")
# print(f"总图片数: {total_imgs} (预期应为 881 + 119 = 1000)")
# print(f"总标签数: {total_labels}")
开始合并数据集（已启用防覆盖逻辑）...
处理
set1: 100 % |██████████ | 881 / 881[00:04 < 00:00, 206.70
it / s]
处理
set2: 100 % |██████████ | 119 / 119[00:00 < 00:00, 219.84
it / s]
1000

✅ 合并完成！
总图片数: 1000(预期应为
881 + 119 = 1000)
总标签数: 1000
# # # 安装 ultralytics 库
# !pip install ultralytics

# # # 然后再运行你的代码
# # from ultralytics import YOLO
# # import os

# # # ... 后续代码不变
Collecting
ultralytics
Downloading
ultralytics - 8.4
.12 - py3 - none - any.whl.metadata(38
kB)
Requirement
already
satisfied: numpy >= 1.23
.0 in / usr / local / lib / python3
.12 / dist - packages(
from ultralytics) (2.0.2)
Requirement
already
satisfied: matplotlib >= 3.3
.0 in / usr / local / lib / python3
.12 / dist - packages(
from ultralytics) (3.10.0)
Requirement
already
satisfied: opencv - python >= 4.6
.0 in / usr / local / lib / python3
.12 / dist - packages(
from ultralytics) (4.12.0.88)
Requirement
already
satisfied: pillow >= 7.1
.2 in / usr / local / lib / python3
.12 / dist - packages(
from ultralytics) (11.3.0)
Requirement
already
satisfied: pyyaml >= 5.3
.1 in / usr / local / lib / python3
.12 / dist - packages(
from ultralytics) (6.0.3)
Requirement
already
satisfied: requests >= 2.23
.0 in / usr / local / lib / python3
.12 / dist - packages(
from ultralytics) (2.32.5)
Requirement
already
satisfied: scipy >= 1.4
.1 in / usr / local / lib / python3
.12 / dist - packages(
from ultralytics) (1.15.3)
Requirement
already
satisfied: torch >= 1.8
.0 in / usr / local / lib / python3
.12 / dist - packages(
from ultralytics) (2.8.0+cu126)
Requirement
already
satisfied: torchvision >= 0.9
.0 in / usr / local / lib / python3
.12 / dist - packages(
from ultralytics) (0.23.0+cu126)
Requirement
already
satisfied: psutil >= 5.8
.0 in / usr / local / lib / python3
.12 / dist - packages(
from ultralytics) (5.9.5)
Requirement
already
satisfied: polars >= 0.20
.0 in / usr / local / lib / python3
.12 / dist - packages(
from ultralytics) (1.25.2)
Collecting
ultralytics - thop >= 2.0
.18(
from ultralytics)
Downloading
ultralytics_thop - 2.0
.18 - py3 - none - any.whl.metadata(14
kB)
Requirement
already
satisfied: contourpy >= 1.0
.1 in / usr / local / lib / python3
.12 / dist - packages(
from matplotlib >= 3.3
.0->ultralytics) (1.3.3)
Requirement
already
satisfied: cycler >= 0.10 in / usr / local / lib / python3
.12 / dist - packages(
from matplotlib >= 3.3
.0->ultralytics) (0.12.1)
Requirement
already
satisfied: fonttools >= 4.22
.0 in / usr / local / lib / python3
.12 / dist - packages(
from matplotlib >= 3.3
.0->ultralytics) (4.60.1)
Requirement
already
satisfied: kiwisolver >= 1.3
.1 in / usr / local / lib / python3
.12 / dist - packages(
from matplotlib >= 3.3
.0->ultralytics) (1.4.9)
Requirement
already
satisfied: packaging >= 20.0 in / usr / local / lib / python3
.12 / dist - packages(
from matplotlib >= 3.3
.0->ultralytics) (26.0rc2)
Requirement
already
satisfied: pyparsing >= 2.3
.1 in / usr / local / lib / python3
.12 / dist - packages(
from matplotlib >= 3.3
.0->ultralytics) (3.2.5)
Requirement
already
satisfied: python - dateutil >= 2.7 in / usr / local / lib / python3
.12 / dist - packages(
from matplotlib >= 3.3
.0->ultralytics) (2.9.0.post0)
Requirement
already
satisfied: charset_normalizer < 4, >= 2 in / usr / local / lib / python3
.12 / dist - packages(
from requests >= 2.23
.0->ultralytics) (3.4.4)
Requirement
already
satisfied: idna < 4, >= 2.5 in / usr / local / lib / python3
.12 / dist - packages(
from requests >= 2.23
.0->ultralytics) (3.11)
Requirement
already
satisfied: urllib3 < 3, >= 1.21
.1 in / usr / local / lib / python3
.12 / dist - packages(
from requests >= 2.23
.0->ultralytics) (2.6.3)
Requirement
already
satisfied: certifi >= 2017.4
.17 in / usr / local / lib / python3
.12 / dist - packages(
from requests >= 2.23
.0->ultralytics) (2026.1.4)
Requirement
already
satisfied: filelock in / usr / local / lib / python3
.12 / dist - packages(
from torch >= 1.8
.0->ultralytics) (3.20.3)
Requirement
already
satisfied: typing - extensions >= 4.10
.0 in / usr / local / lib / python3
.12 / dist - packages(
from torch >= 1.8
.0->ultralytics) (4.15.0)
Requirement
already
satisfied: setuptools in / usr / local / lib / python3
.12 / dist - packages(
from torch >= 1.8
.0->ultralytics) (75.2.0)
Requirement
already
satisfied: sympy >= 1.13
.3 in / usr / local / lib / python3
.12 / dist - packages(
from torch >= 1.8
.0->ultralytics) (1.13.3)
Requirement
already
satisfied: networkx in / usr / local / lib / python3
.12 / dist - packages(
from torch >= 1.8
.0->ultralytics) (3.5)
Requirement
already
satisfied: jinja2 in / usr / local / lib / python3
.12 / dist - packages(
from torch >= 1.8
.0->ultralytics) (3.1.6)
Requirement
already
satisfied: fsspec in / usr / local / lib / python3
.12 / dist - packages(
from torch >= 1.8
.0->ultralytics) (2025.10.0)
Requirement
already
satisfied: nvidia - cuda - nvrtc - cu12 == 12.6
.77 in / usr / local / lib / python3
.12 / dist - packages(
from torch >= 1.8
.0->ultralytics) (12.6.77)
Requirement
already
satisfied: nvidia - cuda - runtime - cu12 == 12.6
.77 in / usr / local / lib / python3
.12 / dist - packages(
from torch >= 1.8
.0->ultralytics) (12.6.77)
Requirement
already
satisfied: nvidia - cuda - cupti - cu12 == 12.6
.80 in / usr / local / lib / python3
.12 / dist - packages(
from torch >= 1.8
.0->ultralytics) (12.6.80)
Requirement
already
satisfied: nvidia - cudnn - cu12 == 9.10
.2
.21 in / usr / local / lib / python3
.12 / dist - packages(
from torch >= 1.8
.0->ultralytics) (9.10.2.21)
Requirement
already
satisfied: nvidia - cublas - cu12 == 12.6
.4
.1 in / usr / local / lib / python3
.12 / dist - packages(
from torch >= 1.8
.0->ultralytics) (12.6.4.1)
Requirement
already
satisfied: nvidia - cufft - cu12 == 11.3
.0
.4 in / usr / local / lib / python3
.12 / dist - packages(
from torch >= 1.8
.0->ultralytics) (11.3.0.4)
Requirement
already
satisfied: nvidia - curand - cu12 == 10.3
.7
.77 in / usr / local / lib / python3
.12 / dist - packages(
from torch >= 1.8
.0->ultralytics) (10.3.7.77)
Requirement
already
satisfied: nvidia - cusolver - cu12 == 11.7
.1
.2 in / usr / local / lib / python3
.12 / dist - packages(
from torch >= 1.8
.0->ultralytics) (11.7.1.2)
Requirement
already
satisfied: nvidia - cusparse - cu12 == 12.5
.4
.2 in / usr / local / lib / python3
.12 / dist - packages(
from torch >= 1.8
.0->ultralytics) (12.5.4.2)
Requirement
already
satisfied: nvidia - cusparselt - cu12 == 0.7
.1 in / usr / local / lib / python3
.12 / dist - packages(
from torch >= 1.8
.0->ultralytics) (0.7.1)
Requirement
already
satisfied: nvidia - nccl - cu12 == 2.27
.3 in / usr / local / lib / python3
.12 / dist - packages(
from torch >= 1.8
.0->ultralytics) (2.27.3)
Requirement
already
satisfied: nvidia - nvtx - cu12 == 12.6
.77 in / usr / local / lib / python3
.12 / dist - packages(
from torch >= 1.8
.0->ultralytics) (12.6.77)
Requirement
already
satisfied: nvidia - nvjitlink - cu12 == 12.6
.85 in / usr / local / lib / python3
.12 / dist - packages(
from torch >= 1.8
.0->ultralytics) (12.6.85)
Requirement
already
satisfied: nvidia - cufile - cu12 == 1.11
.1
.6 in / usr / local / lib / python3
.12 / dist - packages(
from torch >= 1.8
.0->ultralytics) (1.11.1.6)
Requirement
already
satisfied: triton == 3.4
.0 in / usr / local / lib / python3
.12 / dist - packages(
from torch >= 1.8
.0->ultralytics) (3.4.0)
Requirement
already
satisfied: six >= 1.5 in / usr / local / lib / python3
.12 / dist - packages(
from python

-dateutil >= 2.7->matplotlib >= 3.3
.0->ultralytics) (1.17.0)
Requirement
already
satisfied: mpmath < 1.4, >= 1.1
.0 in / usr / local / lib / python3
.12 / dist - packages(
from sympy >= 1.13
.3->torch >= 1.8
.0->ultralytics) (1.3.0)
Requirement
already
satisfied: MarkupSafe >= 2.0 in / usr / local / lib / python3
.12 / dist - packages(
from jinja2->torch >= 1.8
.0->ultralytics) (3.0.3)
Downloading
ultralytics - 8.4
.12 - py3 - none - any.whl(1.2
MB)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 1.2 / 1.2
MB
18.9
MB / s
eta
0: 00:00
a
0: 00:01
Downloading
ultralytics_thop - 2.0
.18 - py3 - none - any.whl(28
kB)
Installing
collected
packages: ultralytics - thop, ultralytics
Successfully
installed
ultralytics - 8.4
.12
ultralytics - thop - 2.0
.18
# import yaml

# # # 定义类别（必须和你合并数据时用的列表完全一致）
# classes = ['DistalPhalanx', 'MCP', 'MCPFirst', 'MiddlePhalanx', 'ProximalPhalanx', 'Radius', 'Ulna']

# # 重新生成 hand.yaml
# config = {
#     'path': '/kaggle/working/merged_data', # 你的合并数据路径
#     'train': 'images/train',
#     'val': 'images/train',    # 暂时用训练集验证，跑通后再说
#     'names': {i: c for i, c in enumerate(classes)}
# }

# with open('/kaggle/working/hand.yaml', 'w') as f:
#     yaml.dump(config, f)

# # print("✅ hand.yaml 已重新生成！")

# # # 检查文件是否真的存在
# # import os
# # if os.path.exists('/kaggle/working/hand.yaml'):
# #     print("🚀 文件确认存在，可以开始训练了。")
# # else:
# #     print("❌ 文件依然没生成，请检查路径权限。")
# import cv2
# import matplotlib.pyplot as plt
# import random

# def plot_random_sample(data_path, classes):
#     img_files = glob(os.path.join(data_path, 'images/train/*'))
#     img_path = random.choice(img_files)
#     label_path = img_path.replace('images', 'labels').replace('.png', '.txt').replace('.jpg', '.txt')

#     img = cv2.imread(img_path)
#     h, w, _ = img.shape

#     with open(label_path, 'r') as f:
#         for line in f:
#             cls, x, y, bw, bh = map(float, line.split())
#             # 还原坐标
#             x1 = int((x - bw/2) * w)
#             y1 = int((y - bh/2) * h)
#             x2 = int((x + bw/2) * w)
#             y2 = int((y + bh/2) * h)
#             cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 3)
#             cv2.putText(img, classes[int(cls)], (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

#     plt.figure(figsize=(10, 10))
#     plt.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
#     plt.title(f"Check: {os.path.basename(img_path)}")
#     plt.show()

# plot_random_sample('/kaggle/working/merged_data', classes)

# from ultralytics import YOLO
# import os

# # 1. 初始化模型 (yolov8s.pt 在精度和速度上平衡得最好)
# model = YOLO('yolov8s.pt')

# # 2. 开始训练
# results = model.train(
#     data='/kaggle/working/hand.yaml',
#     epochs=100,               # 1000张图，100轮足够模型收敛
#     imgsz=1024,               # 关键：保持高分辨率以识别细小指节
#     batch=16,                 # 如果 P100 显存报错(OOM)，请改为 8
#     device=0,                 # 使用 GPU
#     save=True,                # 自动保存最好的模型
#     close_mosaic=10,          # 最后10轮关闭马赛克增强，提升坐标精度
#     augment=True,             # 开启自动增强
#     project='hand_bone_age',  # 项目名称
#     name='joint_detect_v1',   # 运行名称
#     exist_ok=True             # 覆盖同名文件夹
# )
# Inspection the model  of small joint recognizing
# from ultralytics import YOLO

# # 1. 指向你【训练好】的权重
# # 注意：如果你多次训练，请确认路径里的 'joint_detect_v1' 是你最新的文件夹
# best_model_path = '/kaggle/input/hhhhh/pytorch/default/1/best.pt'

# model = YOLO(best_model_path)

# # 2. 运行验证
# # 只要 data 指向你的 hand.yaml，类别就会正确显示为 DistalPhalanx 等
# metrics = model.val(
#     data='',
#     imgsz=1024,
#     split='val',  # 这里的 val 会读取 yaml 里定义的验证集路径
#     conf=0.25     # 置信度阈值
# )

# # 3. 打印核心分数
# print(f"✅ 全类平均精度 mAP50: {metrics.results_dict['metrics/mAP50(B)']:.4f}")
Ultralytics
8.4
.12 🚀 Python - 3.12
.12
torch - 2.8
.0 + cu126
CUDA: 0(Tesla
P100 - PCIE - 16
GB, 16269
MiB)
Model
summary(fused): 73
layers, 11, 128, 293
parameters, 0
gradients, 28.5
GFLOPs
---------------------------------------------------------------------------
FileNotFoundError
Traceback(most
recent
call
last)
/ tmp / ipykernel_55 / 53167702.
py in < cell
line: 0 > ()
9  # 2. 运行验证
10  # 只要 data 指向你的 hand.yaml，类别就会正确显示为 DistalPhalanx 等
---> 11
metrics = model.val(
    12
data = '',
13
imgsz = 1024,

/ usr / local / lib / python3
.12 / dist - packages / ultralytics / engine / model.py in val(self, validator, **kwargs)
610
611
validator = (validator or self._smart_load("validator"))(args=args, _callbacks=self.callbacks)
            --> 612
validator(model=self.model)
613
self.metrics = validator.metrics
614
return validator.metrics

/ usr / local / lib / python3
.12 / dist - packages / torch / utils / _contextlib.py in decorate_context(*args, **kwargs)
118


def decorate_context(*args, **kwargs):
    119
    with ctx_factory():


--> 120
return func(*args, **kwargs)
121
122
return decorate_context

/ usr / local / lib / python3
.12 / dist - packages / ultralytics / engine / validator.py in __call__(self, trainer, model)
182
self.data = check_cls_dataset(self.args.data, split=self.args.split)
183 else:
--> 184
raise FileNotFoundError(emojis(f"Dataset '{self.args.data}' for task={self.args.task} not found ❌"))
185
186
if self.device.type in {"cpu", "mps"}:

FileNotFoundError: Dataset
''
for task=detect not found ❌
# # !pip install ultralytics
# from ultralytics import YOLO

# # 1. 加载模型
# model = YOLO('/kaggle/input/hhhhh/pytorch/default/1/best.pt')

# # 2. 运行验证
# # split='val' 会自动去找 yaml 里指定的验证集图片
# # imgsz 必须保持训练时的 1024
# results = model.val(
#     data='/kaggle/working/hand.yaml',
#     split='val',
#     imgsz=1024,
#     batch=16,
#     conf=0.001,  # 验证时通常设得很低，以获取完整的 PR 曲线
#     iou=0.6      # NMS 阈值
# )

# # 3. 打印核心指标
# print(f"全类平均精度 (mAP50): {results.results_dict['metrics/mAP50(B)']:.4f}")
# print(f"高精度模式 (mAP50-95): {results.results_dict['metrics/mAP50-95(B)']:.4f}")
Ultralytics
8.4
.12 🚀 Python - 3.12
.12
torch - 2.8
.0 + cu126
CUDA: 0(Tesla
P100 - PCIE - 16
GB, 16269
MiB)
Model
summary(fused): 73
layers, 11, 128, 293
parameters, 0
gradients, 28.5
GFLOPs
val: Fast
image
access ✅ (ping: 0.0±0.0 ms, read: 2497.7±484.8 MB / s, size: 643.8 KB)
val: Scanning / kaggle / working / merged_data / labels / train...
1000
images, 0
backgrounds, 0
corrupt: 100 % ━━━━━━━━━━━━ 1000 / 1000
763.0
it / s
1.3
s1s
val: New
cache
created: / kaggle / working / merged_data / labels / train.cache
Class
Images
Instances
Box(P
R
mAP50
mAP50 - 95): 100 % ━━━━━━━━━━━━ 63 / 63
2.7
it / s
22.9
s0
.2
ss
all
1000
20991
0.995
0.995
0.994
0.734
DistalPhalanx
997
4988
0.997
0.999
0.995
0.729
MCP
994
3982
0.995
0.999
0.994
0.73
MCPFirst
992
997
0.987
0.991
0.992
0.699
MiddlePhalanx
998
4015
0.998
0.995
0.995
0.675
ProximalPhalanx
999
5003
0.998
0.999
0.995
0.745
Radius
998
1004
0.996
0.993
0.994
0.802
Ulna
997
1002
0.993
0.991
0.994
0.758
Speed: 3.1
ms
preprocess, 9.3
ms
inference, 0.0
ms
loss, 1.7
ms
postprocess
per
image
Results
saved
to / kaggle / working / runs / detect / val8
全类平均精度(mAP50): 0.9940
高精度模式(mAP50 - 95): 0.7340
# 检查手性
import cv2
import matplotlib.pyplot as plt
from ultralytics import YOLO

# 1. 加载模型
model = YOLO('/kaggle/input/hhhhh/pytorch/default/1/best.pt')


def check_hand_and_show(image_path):
    # 推理
    results = model.predict(source=image_path, imgsz=1024, conf=0.5, verbose=False)[0]

    # 转换为 RGB 供 plt 显示
    img = cv2.imread(image_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    radius_info = None
    ulna_info = None

    # 解析检测结果
    for box in results.boxes:
        cls_id = int(box.cls[0])
        label = results.names[cls_id]
        coords = box.xyxy[0].cpu().numpy()  # [x1, y1, x2, y2]
        center_x = (coords[0] + coords[2]) / 2

        if label == 'Radius':
            radius_info = {'x': center_x, 'box': coords}
        elif label == 'Ulna':
            ulna_info = {'x': center_x, 'box': coords}

    # 2. 判断手性逻辑
    hand_text = "Unknown"
    if radius_info and ulna_info:
        # 在 PA 正位片中：尺骨在左且桡骨在右 -> 左手
        if ulna_info['x'] < radius_info['x']:
            hand_text = "Detected: LEFT Hand (左手)"
            color = (0, 255, 0)  # 绿色
        else:
            hand_text = "Detected: RIGHT Hand (右手)"
            color = (255, 165, 0)  # 橙色
    else:
        hand_text = "Hand Side Error (无法判定)"
        color = (255, 0, 0)

    # 3. 可视化绘图
    plt.figure(figsize=(10, 12))
    plt.imshow(img)
    ax = plt.gca()

    # 绘制判定框
    for item, name in zip([radius_info, ulna_info], ['Radius', 'Ulna']):
        if item:
            b = item['box']
            rect = plt.Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1],
                                 fill=False, edgecolor='cyan', linewidth=2)
            ax.add_patch(rect)
            plt.text(b[0], b[1] - 10, name, color='cyan', fontsize=12, fontweight='bold')

    plt.title(hand_text, fontsize=20, color='white', backgroundcolor='blue')
    plt.axis('off')
    plt.show()


# 运行测试
test_img = "/kaggle/input/xiaoguanjiefenji/VOC2007/JPEGImages/14811.png"
check_hand_and_show(test_img)

import cv2
import matplotlib.pyplot as plt
from ultralytics import YOLO

# 加载模型
model = YOLO('/kaggle/input/hhhhh/pytorch/default/1/best.pt')


def get_13_joints_v2(image_path):
    # 降低 conf 到 0.2，确保边缘的第五指不被过滤
    results = model.predict(source=image_path, imgsz=1024, conf=0.2, verbose=False)[0]
    img = cv2.cvtColor(cv2.imread(image_path), cv2.COLOR_BGR2RGB)

    all_d = []
    r_x, u_x = None, None
    for box in results.boxes:
        c = box.xyxy[0].cpu().numpy()
        lbl = results.names[int(box.cls[0])]
        cx = (c[0] + c[2]) / 2
        all_d.append({'lbl': lbl, 'cx': cx, 'box': c})
        if lbl == 'Radius': r_x = cx
        if lbl == 'Ulna': u_x = cx

    # 判定手性
    is_left = u_x < r_x if (u_x and r_x) else True

    final_13 = {}

    # 核心逻辑：按 X 坐标对每类关节进行全局排序
    # 这样可以准确区分出哪些属于大拇指 (First), 中指 (Third), 小指 (Fifth)
    def map_finger_logic(yolo_lbl, target_prefix, finger_indices=[0, 2, 4],
                         target_suffixes=['First', 'Third', 'Fifth']):
        subset = sorted([d for d in all_d if d['lbl'] == yolo_lbl],
                        key=lambda x: x['cx'], reverse=not is_left)

        for idx, suffix in zip(finger_indices, target_suffixes):
            if len(subset) > idx:
                final_13[f"{target_prefix}{suffix}"] = subset[idx]

    # --- 开始精准映射 13 个点 ---
    # 1. 腕部 (2个)
    if 'Radius' in [d['lbl'] for d in all_d]:
        final_13['Radius'] = next(d for d in all_d if d['lbl'] == 'Radius')
    if 'Ulna' in [d['lbl'] for d in all_d]:
        final_13['Ulna'] = next(d for d in all_d if d['lbl'] == 'Ulna')

    # 2. 映射指骨 (11个)
    map_finger_logic('MCP', 'MCP')  # MCP First, Third, Fifth
    map_finger_logic('ProximalPhalanx', 'PIP')  # PIP First, Third, Fifth
    map_finger_logic('MiddlePhalanx', 'MIP', [1, 2], ['Third', 'Fifth'])  # MIP Third, Fifth (大拇指没MIP)
    map_finger_logic('DistalPhalanx', 'DIP')  # DIP First, Third, Fifth

    # 可视化
    plt.figure(figsize=(12, 16))
    plt.imshow(img)
    for name, info in final_13.items():
        b = info['box']
        rect = plt.Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1], fill=False, edgecolor='red', linewidth=2)
        plt.gca().add_patch(rect)
        plt.text(b[0], b[1] - 5, name, color='white', fontsize=9, backgroundcolor='red')

    plt.title(f"Target 13 | Found {len(final_13)} | Hand: {'Left' if is_left else 'Right'}", fontsize=15)
    plt.axis('off')
    plt.show()
    return final_13


# 运行测试
joints_data = get_13_joints_v2('/kaggle/input/xiaoguanjiefenji/VOC2007/JPEGImages/14787.png')
