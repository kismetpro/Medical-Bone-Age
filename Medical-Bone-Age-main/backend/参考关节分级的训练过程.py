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
# # # 安装 ultralytics 库
# !pip install ultralytics

# # # 然后再运行你的代码
# # from ultralytics import YOLO
# # import os

# # # ... 后续代码不变
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
# #检查手性
# import cv2
# import matplotlib.pyplot as plt
# from ultralytics import YOLO

# # 1. 加载模型
# model = YOLO('/kaggle/input/hhhhh/pytorch/default/1/best.pt')

# def check_hand_and_show(image_path):
#     # 推理
#     results = model.predict(source=image_path, imgsz=1024, conf=0.5, verbose=False)[0]

#     # 转换为 RGB 供 plt 显示
#     img = cv2.imread(image_path)
#     img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

#     radius_info = None
#     ulna_info = None

#     # 解析检测结果
#     for box in results.boxes:
#         cls_id = int(box.cls[0])
#         label = results.names[cls_id]
#         coords = box.xyxy[0].cpu().numpy() # [x1, y1, x2, y2]
#         center_x = (coords[0] + coords[2]) / 2

#         if label == 'Radius':
#             radius_info = {'x': center_x, 'box': coords}
#         elif label == 'Ulna':
#             ulna_info = {'x': center_x, 'box': coords}

#     # 2. 判断手性逻辑
#     hand_text = "Unknown"
#     if radius_info and ulna_info:
#         # 在 PA 正位片中：尺骨在左且桡骨在右 -> 左手
#         if ulna_info['x'] < radius_info['x']:
#             hand_text = "Detected: LEFT Hand (左手)"
#             color = (0, 255, 0) # 绿色
#         else:
#             hand_text = "Detected: RIGHT Hand (右手)"
#             color = (255, 165, 0) # 橙色
#     else:
#         hand_text = "Hand Side Error (无法判定)"
#         color = (255, 0, 0)

#     # 3. 可视化绘图
#     plt.figure(figsize=(10, 12))
#     plt.imshow(img)
#     ax = plt.gca()

#     # 绘制判定框
#     for item, name in zip([radius_info, ulna_info], ['Radius', 'Ulna']):
#         if item:
#             b = item['box']
#             rect = plt.Rectangle((b[0], b[1]), b[2]-b[0], b[3]-b[1],
#                                  fill=False, edgecolor='cyan', linewidth=2)
#             ax.add_patch(rect)
#             plt.text(b[0], b[1]-10, name, color='cyan', fontsize=12, fontweight='bold')

#     plt.title(hand_text, fontsize=20, color='white', backgroundcolor='blue')
#     plt.axis('off')
#     plt.show()

# # 运行测试
# test_img = "/kaggle/input/xiaoguanjiefenji/VOC2007/JPEGImages/14811.png"
# check_hand_and_show(test_img)
# import cv2
# import matplotlib.pyplot as plt
# from ultralytics import YOLO

# # 加载模型
# model = YOLO('/kaggle/input/hhhhh/pytorch/default/1/best.pt')

# def get_13_joints_v2(image_path):
#     # 降低 conf 到 0.2，确保边缘的第五指不被过滤
#     results = model.predict(source=image_path, imgsz=1024, conf=0.2, verbose=False)[0]
#     img = cv2.cvtColor(cv2.imread(image_path), cv2.COLOR_BGR2RGB)

#     all_d = []
#     r_x, u_x = None, None
#     for box in results.boxes:
#         c = box.xyxy[0].cpu().numpy()
#         lbl = results.names[int(box.cls[0])]
#         cx = (c[0] + c[2]) / 2
#         all_d.append({'lbl': lbl, 'cx': cx, 'box': c})
#         if lbl == 'Radius': r_x = cx
#         if lbl == 'Ulna': u_x = cx

#     # 判定手性
#     is_left = u_x < r_x if (u_x and r_x) else True

#     final_13 = {}

#     # 核心逻辑：按 X 坐标对每类关节进行全局排序
#     # 这样可以准确区分出哪些属于大拇指 (First), 中指 (Third), 小指 (Fifth)
#     def map_finger_logic(yolo_lbl, target_prefix, finger_indices=[0, 2, 4], target_suffixes=['First', 'Third', 'Fifth']):
#         subset = sorted([d for d in all_d if d['lbl'] == yolo_lbl],
#                         key=lambda x: x['cx'], reverse=not is_left)

#         for idx, suffix in zip(finger_indices, target_suffixes):
#             if len(subset) > idx:
#                 final_13[f"{target_prefix}{suffix}"] = subset[idx]

#     # --- 开始精准映射 13 个点 ---
#     # 1. 腕部 (2个)
#     if 'Radius' in [d['lbl'] for d in all_d]:
#         final_13['Radius'] = next(d for d in all_d if d['lbl'] == 'Radius')
#     if 'Ulna' in [d['lbl'] for d in all_d]:
#         final_13['Ulna'] = next(d for d in all_d if d['lbl'] == 'Ulna')

#     # 2. 映射指骨 (11个)
#     map_finger_logic('MCP', 'MCP') # MCP First, Third, Fifth
#     map_finger_logic('ProximalPhalanx', 'PIP') # PIP First, Third, Fifth
#     map_finger_logic('MiddlePhalanx', 'MIP', [1, 2], ['Third', 'Fifth']) # MIP Third, Fifth (大拇指没MIP)
#     map_finger_logic('DistalPhalanx', 'DIP') # DIP First, Third, Fifth

#     # 可视化
#     plt.figure(figsize=(12, 16))
#     plt.imshow(img)
#     for name, info in final_13.items():
#         b = info['box']
#         rect = plt.Rectangle((b[0], b[1]), b[2]-b[0], b[3]-b[1], fill=False, edgecolor='red', linewidth=2)
#         plt.gca().add_patch(rect)
#         plt.text(b[0], b[1]-5, name, color='white', fontsize=9, backgroundcolor='red')

#     plt.title(f"Target 13 | Found {len(final_13)} | Hand: {'Left' if is_left else 'Right'}", fontsize=15)
#     plt.axis('off')
#     plt.show()
#     return final_13

# # 运行测试
# joints_data = get_13_joints_v2('/kaggle/input/xiaoguanjiefenji/VOC2007/JPEGImages/14787.png')
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import pandas as pd
from PIL import Image
import torchvision.transforms as T
import torchvision.models as models


# 1. 定义数据集加载
class RSNAMetacarpalDataset(Dataset):
    def __init__(self, csv_file, img_dir, transform=None):
        self.df = pd.read_csv(csv_file)
        self.img_dir = img_dir
        self.transform = transform

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx):
        row = self.df.iloc[idx]
        img_id = str(row['id'])
        # 假设你已经预处理切好了掌骨图，存储在 img_dir 下
        img_path = f"{self.img_dir}/{img_id}.png"
        image = Image.open(img_path).convert('RGB')

        # 骨龄标签 (RSNA 默认是 months)
        age = float(row['boneage'])
        # 性别标签 (Male: True/False)
        gender = 1.0 if row['male'] else 0.0

        if self.transform:
            image = self.transform(image)

        return image, torch.tensor([gender], dtype=torch.float32), torch.tensor([age], dtype=torch.float32)


# 2. 构建模型 (Backbone 预训练)
class BoneAgeBackbone(nn.Module):
    def __init__(self):
        super().__init__()
        # 使用 ResNet50 作为特征提取器
        self.resnet = models.resnet50(pretrained=True)
        num_ftrs = self.resnet.fc.in_features
        self.resnet.fc = nn.Identity()  # 移除分类层，只留特征

        # 骨龄回归头 (加上性别信息，因为 CHN 标准分男女)
        self.regressor = nn.Sequential(
            nn.Linear(num_ftrs + 1, 512),
            nn.ReLU(),
            nn.Linear(512, 1)
        )

    def forward(self, x, gender):
        features = self.resnet(x)
        # 拼接性别信息
        combined = torch.cat((features, gender), dim=1)
        age_pred = self.regressor(combined)
        return age_pred, features  # 同时输出特征，方便后续对齐


# import cv2
# import matplotlib.pyplot as plt
# from PIL import Image
# import os

# def analyze_bone_image(img_path):
#     # 1. 检查文件是否存在
#     if not os.path.exists(img_path):
#         print(f"Error: 找不到路径 {img_path}")
#         return

#     # 2. 读取原始图片
#     # RSNA 的图通常是单通道的灰度图
#     img = cv2.imread(img_path)
#     h, w, _ = img.shape

#     print(f"--- 图像基础属性分析 ---")
#     print(f"原始分辨率: {w} (宽) x {h} (高)")
#     print(f"长宽比 (W/H): {w/h:.2f}")

#     # 3. 模拟 YOLO 裁剪逻辑（假设你使用的是之前的 YOLO 检测模型）
#     # 这里我们演示如何获取并衡量“掌骨区域”
#     # 注意：实际训练时，我们需要的是裁剪后的尺寸，而不是缩放后的尺寸
#     plt.figure(figsize=(10, 10))
#     plt.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
#     plt.title(f"Original RSNA Image: {w}x{h}")
#     plt.axis('off')
#     plt.show()

#     # 4. 给出建议的训练尺寸
#     # 如果你的小关节数据是 256x256，而掌骨是 512x256
#     # 那么我们应该选择一个能包容两者的统一尺寸，例如 448x224
#     if w > h:
#         print("建议：该图为横向拍摄，可能需要旋转 90 度以符合手指纵向生长的解剖学方向。")

#     return w, h

# # 执行衡量
# img_path = "/kaggle/input/rsna-bone-age/boneage-training-dataset/boneage-training-dataset/10000.png"
# width, height = analyze_bone_image(img_path)
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from PIL import Image
import os
from tqdm import tqdm


def analyze_dataset_uncertainty(csv_path, img_dir):
    df = pd.read_csv(csv_path)

    print("--- 1. 标签分布分析 (寻找稀缺样本) ---")
    # 骨龄分布直方图
    plt.figure(figsize=(10, 5))
    sns.histplot(df['boneage'], bins=50, kde=True, color='blue')
    plt.title('Bone Age Distribution')
    plt.xlabel('Age (months)')
    plt.show()

    # 找出样本量少于一定阈值的年龄段（模型在这里最拿不准）
    age_counts = df['boneage'].value_counts().sort_index()
    rare_ages = age_counts[age_counts < 5]
    print(f"样本极少的年龄点个数: {len(rare_ages)}")

    print("\n--- 2. 图像尺寸波动分析 (寻找尺度偏差) ---")
    widths = []
    heights = []
    # 抽样分析前1000张，全量跑太慢
    sample_size = min(1000, len(df))
    for i in tqdm(range(sample_size)):
        img_id = df.iloc[i]['id']
        path = os.path.join(img_dir, f"{img_id}.png")
        with Image.open(path) as img:
            w, h = img.size
            widths.append(w)
            heights.append(h)

    df_size = pd.DataFrame({'width': widths, 'height': heights})
    print(f"宽度范围: {df_size.width.min()} - {df_size.width.max()}")
    print(f"高度范围: {df_size.height.min()} - {df_size.height.max()}")

    # 异常尺寸检测：找出分辨率过低或长宽比极端的图
    df_size['aspect_ratio'] = df_size['width'] / df_size['height']
    extreme_aspect = df_size[(df_size.aspect_ratio < 0.5) | (df_size.aspect_ratio > 1.5)]
    print(f"长宽比畸形的样本比例: {len(extreme_aspect) / sample_size:.2%}")

    print("\n--- 3. 性别偏移分析 ---")
    gender_dist = df['male'].value_counts(normalize=True)
    print(f"男性占比: {gender_dist[True]:.2%}, 女性占比: {gender_dist[False]:.2%}")


# 执行分析
analyze_dataset_uncertainty("/kaggle/input/rsna-bone-age/boneage-training-dataset.csv",
                            "/kaggle/input/rsna-bone-age/boneage-training-dataset/boneage-training-dataset")
--- 1.
标签分布分析(寻找稀缺样本) - --

样本极少的年龄点个数: 87

--- 2.
图像尺寸波动分析(寻找尺度偏差) - --
100 % |██████████ | 1000 / 1000[00:11 < 00:00, 90.44
it / s]
宽度范围: 556 - 2970
高度范围: 742 - 2970
长宽比畸形的样本比例: 0.10 %

--- 3.
性别偏移分析 - --
男性占比: 54.18 %, 女性占比: 45.82 %


# 5. 定义模型架构 (必须先运行此单元格)
class BoneAgeModel(nn.Module):
    def __init__(self):
        super(BoneAgeModel, self).__init__()
        # 使用 resnet50 作为 Backbone
        self.backbone = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V1)

        # 提取特征维度
        n_features = self.backbone.fc.in_features
        self.backbone.fc = nn.Identity()  # 移除原有全连接层，保留特征提取能力

        # 回归头：接收 (特征 + 1维性别)
        self.regressor = nn.Sequential(
            nn.Linear(n_features + 1, 512),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(512, 1)  # 输出归一化后的年龄
        )

    def forward(self, x, gender):
        # 1. 提取图像特征 [batch, 2048]
        feat = self.backbone(x)
        # 2. 拼接性别信息 [batch, 2049]
        combined = torch.cat((feat, gender), dim=1)
        # 3. 回归预测
        age_out = self.regressor(combined)
        return age_out


import pandas as pd
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader, Subset
from torchvision import transforms, models
from sklearn.model_selection import KFold
from PIL import Image
import os
from tqdm import tqdm
from torch.cuda.amp import GradScaler, autocast
from sklearn.model_selection import train_test_split, KFold
import pandas as pd

# --- 配置 ---
CSV_PATH = '/kaggle/input/rsna-bone-age/boneage-training-dataset.csv'
IMG_DIR = '/kaggle/input/rsna-bone-age/boneage-training-dataset/boneage-training-dataset/'
K_FOLDS = 5
BATCH_SIZE = 32
EPOCHS_PER_FOLD = 5  # K折下每个Fold不需要跑太久，主要为了找稳健特征
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# 集成到验证循环中的“错题本”逻辑
def analyze_hard_cases(val_df, preds, targets, dataset):
    # 1. 计算每个样本的绝对误差
    val_df['abs_error'] = np.abs(preds - targets) * (dataset.age_max - dataset.age_min)

    # 2. 找出误差最大的 Top 50 (模型最拿不准的)
    hard_cases = val_df.sort_values(by='abs_error', ascending=False).head(50)

    # 3. 检查这些样本是否属于样本极少的年龄点
    age_counts = val_df['boneage'].value_counts()
    hard_cases['is_rare_age'] = hard_cases['boneage'].apply(lambda x: age_counts.get(x, 0) < 5)

    print(f"--- 错题本分析 ---")
    print(f"Top 50 差生中，属于稀缺年龄段的比例: {hard_cases['is_rare_age'].mean():.2%}")

    return hard_cases


# --- 数据集定义 (保持你的逻辑) ---
class RSNADataset(Dataset):
    def __init__(self, df, img_dir, transform=None):
        self.data = df
        self.img_dir = img_dir
        self.transform = transform
        self.age_max = 228.0  # RSNA大概范围，建议固定以统一多折标准
        self.age_min = 1.0

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        row = self.data.iloc[idx]
        img_path = os.path.join(self.img_dir, f"{row['id']}.png")
        image = Image.open(img_path).convert('RGB')
        age = (row['boneage'] - self.age_min) / (self.age_max - self.age_min)
        gender = 1.0 if row['male'] else 0.0
        if self.transform:
            image = self.transform(image)
        return image, torch.tensor([gender], dtype=torch.float32), torch.tensor([age], dtype=torch.float32)


# --- 训练逻辑 ---
full_df = pd.read_csv(CSV_PATH)
# 1. 在 K 折之前，先切出 10% 作为终极测试集

# 预留 10% 数据作为盲测集，确保无泄露
dev_df, test_df = train_test_split(full_df, test_size=0.1, random_state=42, stratify=pd.cut(full_df['boneage'], 5))
kfold = KFold(n_splits=K_FOLDS, shuffle=True, random_state=42)
# 图像增强
data_transforms = transforms.Compose([
    transforms.Resize((256, 256)),
    transforms.RandomHorizontalFlip(),
    transforms.ColorJitter(0.15, 0.15),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

# 下载与预训练的掌骨识别模型
import os
import json

# --- 步骤 1: 配置 API 凭证 (手动填入你的 ID 和 Key) ---
kaggle_config = {
    "username": "lihaohao111",
    "key": "KGAT_c3e2ffc2dcad971db5c650b684a20013"
}

# 注意是 --version 而不是 -v
!kaggle - v
lihaohao111 / notebook0dae0b1317
18
Traceback(most
recent
call
last):
File
"/usr/local/bin/kaggle", line
4, in < module >
from kaggle.cli import main

File
"/usr/local/lib/python3.12/dist-packages/kaggle/__init__.py", line
6, in < module >
api.authenticate()
File
"/usr/local/lib/python3.12/dist-packages/kaggle/api/kaggle_api_extended.py", line
434, in authenticate
raise IOError('Could not find {}. Make sure it\'s located in'
OSError: Could
not find
kaggle.json.Make
sure
it
's located in /root/.config/kaggle. Or use the environment method. See setup instructions at https://github.com/Kaggle/kaggle-api/
# f = open("/kaggle/working/model_outputs/notebook0dae0b1317.log","r")
# print(f.read())
import math

# RUS-CHN Scoring Standard
SCORE_TABLE = {
    'female': {
        'Radius': [0, 10, 15, 22, 25, 40, 59, 91, 125, 138, 178, 192, 199, 203, 210],
        'Ulna': [0, 27, 31, 36, 50, 73, 95, 120, 157, 168, 176, 182, 189],
        'MCPFirst': [0, 5, 7, 10, 16, 23, 28, 34, 41, 47, 53, 66],
        'MCPThird': [0, 3, 5, 6, 9, 14, 21, 32, 40, 47, 51],
        'MCPFifth': [0, 4, 5, 7, 10, 15, 22, 33, 43, 47, 51],
        'PIPFirst': [0, 6, 7, 8, 11, 17, 26, 32, 38, 45, 53, 60, 67],
        'PIPThird': [0, 3, 5, 7, 9, 15, 20, 25, 29, 35, 41, 46, 51],
        'PIPFifth': [0, 4, 5, 7, 11, 18, 21, 25, 29, 34, 40, 45, 50],
        'MIPThird': [0, 4, 5, 7, 10, 16, 21, 25, 29, 35, 43, 46, 51],
        'MIPFifth': [0, 3, 5, 7, 12, 19, 23, 27, 32, 35, 39, 43, 49],
        'DIPFirst': [0, 5, 6, 8, 10, 20, 31, 38, 44, 45, 52, 67],
        'DIPThird': [0, 3, 5, 7, 10, 16, 24, 30, 33, 36, 39, 49],
        'DIPFifth': [0, 5, 6, 7, 11, 18, 25, 29, 33, 35, 39, 49]
    },
    'male': {
        'Radius': [0, 8, 11, 15, 18, 31, 46, 76, 118, 135, 171, 188, 197, 201, 209],
        'Ulna': [0, 25, 30, 35, 43, 61, 80, 116, 157, 168, 180, 187, 194],
        'MCPFirst': [0, 4, 5, 8, 16, 22, 26, 34, 39, 45, 52, 66],
        'MCPThird': [0, 3, 4, 5, 8, 13, 19, 30, 38, 44, 51],
        'MCPFifth': [0, 3, 4, 6, 9, 14, 19, 31, 41, 46, 50],
        'PIPFirst': [0, 4, 5, 7, 11, 17, 23, 29, 36, 44, 52, 59, 66],
        'PIPThird': [0, 3, 4, 5, 8, 14, 19, 23, 28, 34, 40, 45, 50],
        'PIPFifth': [0, 3, 4, 6, 10, 16, 19, 24, 28, 33, 40, 44, 50],
        'MIPThird': [0, 3, 4, 5, 9, 14, 18, 23, 28, 35, 42, 45, 50],
        'MIPFifth': [0, 3, 4, 6, 11, 17, 21, 26, 31, 36, 40, 43, 49],
        'DIPFirst': [0, 4, 5, 6, 9, 19, 28, 36, 43, 46, 51, 67],
        'DIPThird': [0, 3, 4, 5, 9, 15, 23, 29, 33, 37, 40, 49],
        'DIPFifth': [0, 3, 4, 6, 11, 17, 23, 29, 32, 36, 40, 49]
    }
}

BONE_NAMES_CN = {
    'Radius': '桡骨 (Radius)',
    'Ulna': '尺骨 (Ulna)',
    'MCPFirst': '第一掌骨 (MCP1)',
    'MCPThird': '第三掌骨 (MCP3)',
    'MCPFifth': '第五掌骨 (MCP5)',
    'PIPFirst': '第一近节 (PIP1)',
    'PIPThird': '第三近节 (PIP3)',
    'PIPFifth': '第五近节 (PIP5)',
    'MIPThird': '第三中节 (MIP3)',
    'MIPFifth': '第五中节 (MIP5)',
    'DIPFirst': '第一远节 (DIP1)',
    'DIPThird': '第三远节 (DIP3)',
    'DIPFifth': '第五远节 (DIP5)'
}


def calc_bone_age_from_score(score, gender):
    """
    Calculate bone age (years) from total RUS-CHN score.
    Ref: Pyqt5-and-BoneAge-main/utils.py
    """
    # Formula is valid for score roughly 0-1000
    if gender == 'male':
        boneAge = 2.01790023656577 + (-0.0931820870747269) * score + math.pow(score, 2) * 0.00334709095418796 + \
                  math.pow(score, 3) * (-3.32988302362153E-05) + math.pow(score, 4) * (1.75712910819776E-07) + \
                  math.pow(score, 5) * (-5.59998691223273E-10) + math.pow(score, 6) * (1.1296711294933E-12) + \
                  math.pow(score, 7) * (-1.45218037113138e-15) + math.pow(score, 8) * (1.15333377080353e-18) + \
                  math.pow(score, 9) * (-5.15887481551927e-22) + math.pow(score, 10) * (9.94098428102335e-26)
    else:  # female
        boneAge = 5.81191794824917 + (-0.271546561737745) * score + \
                  math.pow(score, 2) * 0.00526301486340724 + math.pow(score, 3) * (-4.37797717401925E-05) + \
                  math.pow(score, 4) * (2.0858722025667E-07) + math.pow(score, 5) * (-6.21879866563429E-10) + \
                  math.pow(score, 6) * (1.19909931745368E-12) + math.pow(score, 7) * (-1.49462900826936E-15) + \
                  math.pow(score, 8) * (1.162435538672E-18) + math.pow(score, 9) * (-5.12713017846218E-22) + \
                  math.pow(score, 10) * (9.78989966891478E-26)

    return max(0, boneAge)


class BoneAgeMultiTaskDataset(Dataset):
    def __init__(self, df, img_dir, arthrosis_base_path, transform=None):
        self.data = df
        self.img_dir = img_dir
        self.transform = transform
        # 建立图像 ID 与分级的映射映射（假设你已经预处理了一个映射表）
        self.arthrosis_map = self._load_arthrosis_labels(arthrosis_base_path)

    def _load_arthrosis_labels(self, path):
        # 逻辑：遍历 DIP 下的 1-11 文件夹，记录每个 ID 对应的等级
        # 返回字典 {id: grade}
        mapping = {}
        for grade in range(1, 12):
            folder = os.path.join(path, 'DIP', str(grade))
            if os.path.exists(folder):
                for fname in os.listdir(folder):
                    img_id = fname.split('.')[0]
                    mapping[img_id] = grade - 1  # 转为 0-10 索引
        return mapping

    def __getitem__(self, idx):
        row = self.data.iloc[idx]
        img_id = str(row['id'])
        row = self.data.iloc[idx]
        img_path = os.path.join(self.img_dir, f"{row['id']}.png")
        image = Image.open(img_path).convert('RGB')
        age = (row['boneage'] - self.age_min) / (self.age_max - self.age_min)
        gender = 1.0 if row['male'] else 0.0
        if self.transform:
            image = self.transform(image)

        # 获取分级标签，如果没有标注则设为 -100（PyTorch CrossEntropy 会忽略此值）
        dip_grade = self.arthrosis_map.get(img_id, -100)

        return image, gender, age, torch.tensor(dip_grade, dtype=torch.long)


class MultiTaskBoneModel(nn.Module):
    def __init__(self, backbone, score_table):
        super().__init__()
        self.backbone = backbone
        n_feat = 2048

        # 核心：根据 SCORE_TABLE 动态生成分类头
        self.heads = nn.ModuleDict()
        for bone_name in score_table['male'].keys():
            # 获取该骨骼对应的等级总数
            num_classes = len(score_table['male'][bone_name])
            self.heads[bone_name] = nn.Sequential(
                nn.Linear(n_feat, 256),
                nn.ReLU(),
                nn.Linear(256, num_classes)  # 每个部位的分类维度不同
            )

    def forward(self, x):
        feat = self.backbone(x)
        results = {}
        for bone_name, head in self.heads.items():
            results[bone_name] = head(feat)  # 输出 13 个不同的分级概率
        return results


def map_index_to_medical_stage(idx, bone_name, score_table, gender='male'):
    """
    将文件夹 1-11 的索引转换为医学标准的实际等级
    """
    max_medical_stage = len(score_table[gender][bone_name]) - 1
    # 简单的线性映射 (如果你的 11 个文件夹覆盖了全生命周期)
    # 实际医学分级 = round(当前索引 * (最高医学等级 / 10))
    medical_stage = round(idx * (max_medical_stage / 10.0))
    return medical_stage


class FormulaConstraintLoss(nn.Module):
    def __init__(self, score_table, gender='male'):
        super().__init__()
        self.gender = gender
        # 将 score_table 转化为张量并填充到统一长度，方便矩阵运算
        self.score_tensors = self._prepare_tensors(score_table[gender])

    def forward(self, pred_probs_dict, target_age):
        total_score = 0
        for bone_name, probs in pred_probs_dict.items():
            # 这里的 probs 是分类头的 Softmax 输出 [Batch, 11]
            # 我们通过期望值（Expected Value）计算平滑的得分，使其可微
            # 得分 = \sum_{i=0}^{10} (P(Level_i) * Score(Mapped_Level_i))
            mapped_scores = self._get_mapped_scores(bone_name)  # 获取映射后的分值张量
            bone_score = torch.sum(probs * mapped_scores, dim=1)
            total_score += bone_score

        # 代入你的 10 次多项式公式 (使用 torch.pow 保持梯度)
        pred_age = self.calc_torch_age(total_score)

        # 约束：公式算出的年龄 vs 医生给的总年龄
        constraint_loss = nn.L1Loss()(pred_age, target_age)
        return constraint_loss


class FinalPaperModel(nn.Module):
    def __init__(self, backbone, score_table):
        super().__init__()
        self.backbone = backbone  # 你已经练好的 ResNet50

        # 13 个分类头
        self.bone_names = list(SCORE_TABLE['male'].keys())
        self.heads = nn.ModuleDict({
            name: nn.Linear(2048, 11) for name in self.bone_names
        })

        # 公式约束层
        self.formula_layer = BoneAgeFormulaLayer(score_table)

    def forward(self, x, gender_is_male):
        feat = self.backbone(x)  # [Batch, 2048]

        # 分类预测
        logits_dict = {name: self.heads[name](feat) for name in self.bone_names}

        # 公式推导年龄
        formula_age = self.formula_layer(logits_dict, gender_is_male)

        return logits_dict, formula_age


class BoneAgeFormulaLayer(nn.Module):
    def __init__(self, score_table, levels_map):

        super().__init__()

        # --- 修复 1: 定义物理文件夹到医学关节的映射表 ---
        # 必须先定义映射，因为 _build_dynamic_matrix 会用到它
        self.mapping = {
            'Radius': ['Radius'],
            'Ulna': ['Ulna'],
            'MCPFirst': ['MCPFirst'],
            'MCP': ['MCPThird', 'MCPFifth'],
            'PIP': ['PIPThird', 'PIPFifth'],
            'DIP': ['DIPThird', 'DIPFifth'],
            'MIP': ['MIPThird', 'MIPFifth']
        }

        # --- 修复 2: 移除 register_buffer，直接赋值 ParameterDict ---
        # nn.ParameterDict 本身就是一种 Module 容器，会自动处理设备(GPU/CPU)转移
        self.male_score_tensors = self._build_dynamic_matrix(score_table, 'male', levels_map)
        self.female_score_tensors = self._build_dynamic_matrix(score_table, 'female', levels_map)

    def _build_dynamic_matrix(self, table, gender, levels_map):
        matrices = {}
        # 此时 self.mapping 已经在 __init__ 中定义
        for phy_name, num_f in levels_map.items():
            if num_f == 0: continue

            target_joints = self.mapping.get(phy_name, [phy_name])

            for joint in target_joints:
                med_scores = table[gender][joint]
                max_m = len(med_scores) - 1

                bone_vec = torch.zeros(num_f)
                for i in range(num_f):
                    m_idx = i * (max_m / max(1, num_f - 1))
                    low, weight = int(m_idx), m_idx - int(m_idx)
                    up = min(low + 1, max_m)
                    bone_vec[i] = (1 - weight) * med_scores[low] + weight * med_scores[up]
                matrices[joint] = bone_vec

        # 返回 ParameterDict，PyTorch 会将其中的 Parameter 自动注册
        return nn.ParameterDict({k: nn.Parameter(v, requires_grad=False) for k, v in matrices.items()})

    def forward(self, logits_dict, is_male_mask):
        total_score_m, total_score_f = 0, 0
        is_male_mask = is_male_mask.view(-1).bool()

        # 修正逻辑：遍历物理输出，分发给 13 个医学逻辑点
        for phy_name, logits in logits_dict.items():
            probs = torch.softmax(logits, dim=1)

            # 获取对应的医学关节列表（实现 7 转 13）
            target_joints = self.mapping.get(phy_name, [phy_name])

            for joint in target_joints:
                # 累加每个医学关节的期望得分
                total_score_m += torch.sum(probs * self.male_score_tensors[joint], dim=1)
                total_score_f += torch.sum(probs * self.female_score_tensors[joint], dim=1)

        # 代入 10 次多项式
        age_m = self._calc_poly(total_score_m, 'male')
        age_f = self._calc_poly(total_score_f, 'female')

        final_age_years = torch.where(is_male_mask, age_m, age_f)
        return torch.clamp(final_age_years * 12.0, min=0)  # 统一转为月龄


def get_bone_levels(base_path):
    bone_names = ['Radius', 'Ulna', 'MCPFirst', 'MCPThird', 'MCPFifth',
                  'PIPFirst', 'PIPThird', 'PIPFifth', 'MIPThird', 'MIPFifth',
                  'DIPFirst', 'DIPThird', 'DIPFifth']
    level_counts = {}
    for bone in bone_names:
        bone_dir = os.path.join(base_path, bone)
        if os.path.exists(bone_dir):
            # 计算该骨骼下有多少个分级文件夹
            folders = [f for f in os.listdir(bone_dir) if os.path.isdir(os.path.join(bone_dir, f))]
            level_counts[bone] = len(folders)
        else:
            level_counts[bone] = 0
    return level_counts


# 假设结果是 {'Radius': 11, 'DIPFirst': 6, ...}
BONE_LEVEL_MAP = get_bone_levels('/kaggle/input/arthrosis1/arthrosis')


class FinalPaperModel(nn.Module):
    def __init__(self, backbone, level_map):
        super().__init__()
        self.backbone = backbone
        self.heads = nn.ModuleDict()

        for bone_name, num_levels in level_map.items():
            if num_levels > 0:
                # 每个关节根据实际文件夹数量定义输出维度
                self.heads[bone_name] = nn.Linear(2048, num_levels)

        # 公式层也要传入这个 map，以便进行正确的分值映射
        self.formula_layer = BoneAgeFormulaLayer(SCORE_TABLE, level_map)


def _prepare_score_matrix(self, table, gender, level_map):
    # 此时矩阵不再是统一的 [13, 11]，而是一个列表或 padding 后的张量
    # 建议为每个关节动态生成映射向量
    matrices = {}
    for bone, max_folder_num in level_map.items():
        medical_scores = table[gender][bone]
        max_med_idx = len(medical_scores) - 1

        # 动态生成该关节的得分向量 [max_folder_num]
        bone_vec = torch.zeros(max_folder_num)
        for f_idx in range(max_folder_num):
            # 核心映射：folder_idx / (总文件夹数-1) * (医学最高级)
            m_idx = f_idx * (max_med_idx / max(1, max_folder_num - 1))
            low, w = int(m_idx), m_idx - int(m_idx)
            up = min(low + 1, max_med_idx)
            bone_vec[f_idx] = (1 - w) * medical_scores[low] + w * medical_scores[up]
        matrices[bone] = bone_vec
    return matrices


def get_actual_levels(base_path):
    bone_names = ['Radius', 'Ulna', 'MCPFirst', 'MCPThird', 'MCPFifth',
                  'PIPFirst', 'PIPThird', 'PIPFifth', 'MIPThird', 'MIPFifth',
                  'DIPFirst', 'DIPThird', 'DIPFifth']
    levels_map = {}
    for bone in bone_names:
        bone_path = os.path.join(base_path, bone)
        if os.path.exists(bone_path):
            # 统计目录下数字文件夹的数量
            folders = [d for d in os.listdir(bone_path) if d.isdigit()]
            levels_map[bone] = len(folders)
        else:
            levels_map[bone] = 0
    return levels_map


# 得到的可能是 {'Radius': 11, 'DIPFirst': 6, ...}
actual_levels = get_actual_levels('arthrosis/')


class FinalAdaptiveModel(nn.Module):
    def __init__(self, backbone, levels_map, score_table):
        self.score_table = score_table
        super().__init__()
        self.backbone = backbone
        self.heads = nn.ModuleDict({
            name: nn.Linear(2048, num) for name, num in levels_map.items() if num > 0
        })
        # 公式层也要传入这个 map
        self.formula_layer = BoneAgeFormulaLayer(score_table, levels_map)

    def forward(self, x, is_male_mask):
        feat = self.backbone(x)
        logits_dict = {name: head(feat) for name, head in self.heads.items()}
        # 传入 logits 字典进行公式计算
        formula_age = self.formula_layer(logits_dict, is_male_mask)
        return logits_dict, formula_age


def _prepare_score_matrix(self, table, gender, levels_map):
    # 注意：这里我们不再用一个单一 Tensor，因为各骨骼维度不同
    # 我们用 Padding 或者在一个循环里根据当前 bone 的实际 level 数动态映射
    matrices = nn.ParameterDict()  # 或者简单的字典
    for bone, num_folders in levels_map.items():
        if num_folders == 0: continue

        medical_scores = table[gender][bone]
        max_med_idx = len(medical_scores) - 1

        # 创建该骨骼专属的映射向量 [num_folders]
        bone_vec = torch.zeros(num_folders)
        for f_idx in range(num_folders):
            # 比例映射：将当前文件夹索引映射到医学分级索引
            m_idx = f_idx * (max_med_idx / max(1, num_folders - 1))
            low, weight = int(m_idx), m_idx - int(m_idx)
            up = min(low + 1, max_med_idx)
            bone_vec[f_idx] = (1 - weight) * medical_scores[low] + weight * medical_scores[up]

        matrices[bone] = nn.Parameter(bone_vec, requires_grad=False)
    return matrices


import torch
import torch.nn as nn
import torch.nn.functional as F


class BoneNet_v2(nn.Module):
    def __init__(self, backbone, levels_map, score_table):
        super().__init__()
        self.backbone = backbone  # 建议用你之前练好的 ResNet50
        self.levels_map = levels_map  # 传入探测到的各关节等级数

        # 1. 异构分类头：根据每个关节实际存在的文件夹数量定义输出
        self.heads = nn.ModuleDict({
            name: nn.Linear(2048, num_levels)
            for name, num_levels in levels_map.items() if num_levels > 0
        })

        # 2. 嵌入式公式约束层
        self.formula_layer = BoneAgeFormulaLayer(score_table, levels_map)

    def forward(self, x, is_male_mask):
        # 提取全局特征
        features = self.backbone(x)  # [Batch, 2048]

        # 得到 13 个关节的分类 Logits
        logits_dict = {name: self.heads[name](features) for name in self.heads}

        # 通过公式计算逻辑年龄
        formula_age = self.formula_layer(logits_dict, is_male_mask)

        return logits_dict, formula_age


class AdaptiveMultiTaskLoss(nn.Module):
    def __init__(self, lambda_formula=1.5):
        super().__init__()
        self.lambda_f = lambda_formula
        # ignore_index=-100 会自动跳过那些没在文件夹里出现的关节
        self.ce = nn.CrossEntropyLoss(ignore_index=-100)
        self.mae = nn.L1Loss()

    def forward(self, logits_dict, pred_age, target_grades, target_age):
        # 1. 分类损失 (只针对有标注的关节)
        loss_cls = 0
        count = 0
        for name, logits in logits_dict.items():
            loss_cls += self.ce(logits, target_grades[name])
            count += 1

        # 2. 公式约束损失 (所有图片都有总年龄标签)
        loss_formula = self.mae(pred_age, target_age)

        return (loss_cls / count) + self.lambda_f * loss_formula


# --- 1. 新增：超图一致性损失函数 ---
def get_hyper_loss(logits_dict, device):
    h_loss = 0
    for edge, joints in HYPER_EDGES.items():
        group_grades = []
        for j in joints:
            if j in logits_dict:
                # 使用 Softmax 期望值实现可微的等级估算
                probs = F.softmax(logits_dict[j], dim=1)
                expected_grade = torch.sum(probs * torch.arange(probs.size(1)).to(device), dim=1)
                group_grades.append(expected_grade)
        if len(group_grades) > 1:
            # 约束：同一超边内的发育进度方差不应过大（解剖学一致性）
            h_loss += torch.var(torch.stack(group_grades), dim=0).mean()
    return h_loss


# --- 2. 训练循环重写 ---
def train_one_epoch(model, loader, optimizer, criterion, device):
    model.train()
    for imgs, genders, target_ages, joint_labels in loader:
        # 新逻辑：多任务学习 + 超图约束 + 物理公式       logits_dict, formula_age = model(imgs, genders)

        # A. 分类损失：确保每个小关节分级准确
        loss_cls = sum([F.cross_entropy(logits_dict[j], joint_labels[j]) for j in joint_labels])

        # B. 超图一致性损失：利用解剖学先验纠偏
        loss_hyper = get_hyper_loss(logits_dict, device)

        # C. 公式回归损失：10次幂公式输出与真实年龄对齐
        loss_reg = F.mse_loss(formula_age, target_ages)

        # 综合 Loss (领域自适应的关键：强先验约束)
        total_loss = 0.5 * loss_cls + 0.2 * loss_hyper + 1.0 * loss_reg

        optimizer.zero_grad()

        total_loss.backward()
        optimizer.step()


import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import time


class TrainingLogger:
    def __init__(self, save_path='./training_logs'):
        self.save_path = save_path
        os.makedirs(save_path, exist_ok=True)
        self.history = {
            'epoch': [], 'total_loss': [], 'cls_loss': [],
            'formula_loss': [], 'formula_mae': []
        }

    def update(self, epoch, total_loss, cls_loss, formula_loss, formula_mae):
        self.history['epoch'].append(epoch)
        self.history['total_loss'].append(total_loss)
        self.history['cls_loss'].append(cls_loss)
        self.history['formula_loss'].append(formula_loss)
        self.history['formula_mae'].append(formula_mae)

        # 实时保存 CSV 数据
        pd.DataFrame(self.history).to_csv(f"{self.save_path}/history.csv", index=False)

    def draw_plots(self):
        """生成答辩用的专业图表"""
        plt.figure(figsize=(15, 5))

        # 1. Loss 曲线 (分类 vs 公式)
        plt.subplot(1, 2, 1)
        plt.plot(self.history['epoch'], self.history['cls_loss'], label='Classification Loss')
        plt.plot(self.history['epoch'], self.history['formula_loss'], label='Formula Constraint Loss')
        plt.title('Multi-Task Loss Convergence')
        plt.xlabel('Epoch')
        plt.ylabel('Loss')
        plt.legend()

        # 2. MAE 曲线 (最终精度)
        plt.subplot(1, 2, 2)
        plt.plot(self.history['epoch'], self.history['formula_mae'], color='red', label='Bone Age MAE (Months)')
        plt.axhline(y=7.5, color='gray', linestyle='--', label='SOTA Target (7.5m)')
        plt.title('Bone Age Prediction Accuracy')
        plt.xlabel('Epoch')
        plt.ylabel('MAE (Months)')
        plt.legend()

        plt.tight_layout()
        plt.savefig(f"{self.save_path}/performance_curves.png")
        plt.show()

    def draw_regression_plot(self, true_ages, pred_ages):
        """生成预测值与真实值的对比散点图（答辩必杀技）"""
        plt.figure(figsize=(8, 8))
        plt.scatter(true_ages, pred_ages, alpha=0.5, c='blue', s=10)
        # 画出理想对角线
        max_age = max(true_ages.max(), pred_ages.max())
        plt.plot([0, max_age], [0, max_age], 'r--', lw=2)

        plt.xlabel('Ground Truth Bone Age (Months)')
        plt.ylabel('Formula Predicted Age (Months)')
        plt.title('Accuracy Distribution: Ground Truth vs. Prediction')
        plt.grid(True)
        plt.savefig(f"{self.save_path}/regression_analysis.png")
        plt.show()


# --- 增加：仿射变换对齐函数 ---
def align_joint_affine(img):
    """
    通过仿射变换将关节调整到正中央，并纠正倾斜
    """
    # 1. 简单的重心对齐与旋转校正（示例逻辑）
    rows, cols = img.shape[:2]
    # 假设我们通过计算二阶矩得到主轴方向
    # 在实际工程中，可以利用 YOLO 的旋转框或 5 个关键点来确定 M 矩阵
    center = (cols / 2, rows / 2)
    # 示例：自动旋转 10 度并缩放 0.9 倍的变换矩阵
    M = cv2.getRotationMatrix2D(center, angle=0, scale=1.0)

    # 2. 执行仿射变换
    aligned_img = cv2.warpAffine(img, M, (cols, rows), borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    return aligned_img


# --- 定义超图解剖关联 (Hyper-Edges) ---
HYPER_EDGES = {
    'finger_3': ['DIPThird', 'MIPThird', 'PIPThird', 'MCPThird'],  # 第三手指发育链
    'finger_5': ['DIPFifth', 'MIPFifth', 'PIPFifth', 'MCPFifth'],  # 第五手指发育链
    'forearm': ['Radius', 'Ulna'],  # 前臂骨对
}
import os
import xml.etree.ElementTree as ET
import pandas as pd
from sklearn.model_selection import StratifiedKFold, train_test_split

# 定义 13 个小关节的官方顺序
import pandas as pd
import re
from sklearn.model_selection import StratifiedKFold, train_test_split

# 定义 13 个小关节的官方顺序
JOINT_ORDER = [
    'Radius', 'Ulna', 'MCPFirst', 'MCPThird', 'MCPFifth',
    'PIPFirst', 'PIPThird', 'PIPFifth', 'MIPThird', 'MIPFifth',
    'DIPFirst', 'DIPThird', 'DIPFifth'
]


def scan_boneage_by_filenames(img_dir):
    data_list = []
    img_files = [f for f in os.listdir(img_dir)]
    print(img_dir)
    print(img_files)
    for img_file in img_files:

        for grade in os.listdir(os.path.join(img_dir, img_file)):
            for img_name in os.listdir(os.path.join(img_dir, img_file, grade)):
                # print(img_name)

                row = {}

                row['path'] = os.path.join(img_dir, img_file, grade, img_name)

                row['grade'] = grade  # 计算总分用于分层
                data_list.append(row)

    return pd.DataFrame(data_list)


def split_and_mark_folds(df):
    # 额外的保险：确保列类型为数字
    df['grade'] = pd.to_numeric(df['grade'])

    # 1. 构造分层依据
    # 注意：如果等级种类很少，duplicates='drop' 是必须的
    df['grade_bin'] = pd.qcut(df['grade'], q=5, labels=False, duplicates='drop')

    # 2. 划分独立测试集
    train_val_df, test_df = train_test_split(
        df, test_size=0.1, random_state=42, stratify=df['grade_bin']
    )

    # 3. 5折交叉验证标记
    train_val_df = train_val_df.reset_index(drop=True)
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    train_val_df['fold'] = -1
    for fold, (train_idx, val_idx) in enumerate(skf.split(train_val_df, train_val_df['grade_bin'])):
        train_val_df.loc[val_idx, 'fold'] = fold

    return train_val_df, test_df


# --- 执行流程 ---
df = scan_boneage_by_filenames("/kaggle/input/arthrosis1/arthrosis")
print(df.describe())
train_val_df, test_df = split_and_mark_folds(df)
print(train_val_df.describe())
print(test_df.describe())
/ kaggle / input / arthrosis1 / arthrosis
['PIPFirst', 'MCP', 'MCPFirst', 'MIP', 'Radius', 'PIP', 'Ulna', 'DIPFirst', 'DIP']
path
grade
count
8210
8210
unique
8210
14
top / kaggle / input / arthrosis1 / arthrosis / DIP / 11 / DIP_...
4
freq
1
1278
grade
grade_bin
fold
count
7389.000000
7389.000000
7389.000000
mean
6.325348
1.674516
1.999729
std
3.223406
1.487641
1.414214
min
1.000000
0.000000
0.000000
25 % 4.000000
0.000000
1.000000
50 % 6.000000
2.000000
2.000000
75 % 9.000000
3.000000
3.000000
max
14.000000
4.000000
4.000000
grade
grade_bin
count
821.000000
821.000000
mean
6.306943
1.673569
std
3.256260
1.488376
min
1.000000
0.000000
25 % 4.000000
0.000000
50 % 6.000000
2.000000
75 % 9.000000
3.000000
max
14.000000
4.000000


def train_one_epoch(model, loader, optimizer, device, joint_order):
    model.train()

    ce = nn.CrossEntropyLoss()
    epoch_loss = 0.0
    total_correct = 0
    total_count = 0

    for imgs, joint_labels in tqdm(loader, desc="Training"):
        imgs = imgs.to(device)

        joint_labels = joint_labels.to(device)

        out = model(imgs)  # 推荐改成只吃imgs
        if isinstance(out, tuple):
            logits_dict, _ = out
        else:
            logits_dict = out

        total_loss = 0.0
        valid_joints = 0
        for j, name in enumerate(joint_order):
            if name not in logits_dict:
                continue
            logits = logits_dict[name]  # [B,C]
            labels = joint_labels[:, j].long()  # [B]
            loss_j = ce(logits, labels)
            total_loss = total_loss + loss_j
            valid_joints += 1

            preds = torch.argmax(logits, dim=1)
            total_correct += (preds == labels).sum().item()
            total_count += labels.numel()

        total_loss = total_loss / max(valid_joints, 1)

        epoch_loss += float(total_loss.item())

    acc = total_correct / max(total_count, 1)
    return epoch_loss / max(len(loader), 1), acc


print(test_df[:10])
path
grade
grade_bin
6327 / kaggle / input / arthrosis1 / arthrosis / DIPFirst / 7 / ...
7
2
5207 / kaggle / input / arthrosis1 / arthrosis / PIP / 4 / PIP_6...
4
0
6006 / kaggle / input / arthrosis1 / arthrosis / Ulna / 1 / Ulna...
1
0
6516 / kaggle / input / arthrosis1 / arthrosis / DIPFirst / 5 / ...
5
1
470 / kaggle / input / arthrosis1 / arthrosis / PIPFirst / 4 / ...
4
0
1854 / kaggle / input / arthrosis1 / arthrosis / MCP / 6 / MCP_5...
6
2
2415 / kaggle / input / arthrosis1 / arthrosis / MCPFirst / 11...
11
4
7641 / kaggle / input / arthrosis1 / arthrosis / DIP / 4 / DIP_5...
4
0
1715 / kaggle / input / arthrosis1 / arthrosis / MCP / 9 / MCP_6...
9
3
1132 / kaggle / input / arthrosis1 / arthrosis / MCP / 8 / MCP_2...
8
3


class SingleJointDataset(Dataset):
    def __init__(self, df, transform=None, return_label=True):
        self.df = df.reset_index(drop=True)
        self.transform = transform
        self.return_label = return_label

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx):
        row = self.df.iloc[idx]
        img_path = row["path"]
        image = Image.open(img_path).convert("RGB")

        if self.transform:
            image = self.transform(image)

        if not self.return_label:
            return image

        label = int(row["grade"]) - 1
        return image, label


import os
import math
import torch
import torch.nn as nn
import torch.nn.functional as F
from tqdm import tqdm


# =========================================================
# 1) GRL + Domain Classifier (DANN)
# =========================================================
class GradReverse(torch.autograd.Function):
    @staticmethod
    def forward(ctx, x, lambd):
        ctx.lambd = lambd
        return x.view_as(x)

    @staticmethod
    def backward(ctx, grad_output):
        return -ctx.lambd * grad_output, None


def grad_reverse(x, lambd=1.0):
    return GradReverse.apply(x, lambd)


class DomainClassifier(nn.Module):
    def __init__(self, in_dim, hidden=256):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden, 2)  # 0: source, 1: target
        )

    def forward(self, feat, grl_lambda=1.0):
        feat = grad_reverse(feat, grl_lambda)
        return self.net(feat)


# =========================================================
# 2) 示例学生模型接口（需与你现有模型对齐）
#    forward 返回:
#      logits_dict: {joint_name: [B,14]}
#      formula_age: [B]
#      feat:        [B,D]   <- 给域分类器
# =========================================================
class StudentWrapper(nn.Module):
    def __init__(self, backbone, head, feat_dim):
        super().__init__()
        self.backbone = backbone
        self.head = head
        self.domain_clf = DomainClassifier(feat_dim)

    def forward(self, x, grl_lambda=0.0, need_domain=False):
        feat = self.backbone(x)  # [B,D]
        logits_dict, formula_age = self.head(feat)

        domain_logits = None
        if need_domain:
            domain_logits = self.domain_clf(feat, grl_lambda=grl_lambda)

        return logits_dict, formula_age, feat, domain_logits


# =========================================================
# 3) 加载五折 teacher
# =========================================================
def load_teacher_ensemble(teacher_model_ctor, ckpt_paths, device):
    teachers = []
    for p in ckpt_paths:
        m = teacher_model_ctor().to(device)
        ckpt = torch.load(p, map_location=device)
        if isinstance(ckpt, dict) and "state_dict" in ckpt:
            ckpt = ckpt["state_dict"]
        m.load_state_dict(ckpt, strict=False)
        m.eval()
        for t in m.parameters():
            t.requires_grad = False
        teachers.append(m)
        print(f"[Teacher] loaded: {p}")
    return teachers


# =========================================================
# 4) 损失函数
# =========================================================
def kd_kl(student_logits, teacher_logits, T=2.0):
    s = F.log_softmax(student_logits / T, dim=1)
    t = F.softmax(teacher_logits / T, dim=1)
    return F.kl_div(s, t, reduction="batchmean") * (T * T)


def compute_cls_age_from_logits(logits_dict, score_table):
    # logits_dict[j]: [B,14]
    device = next(iter(logits_dict.values())).device
    B = next(iter(logits_dict.values())).shape[0]
    cls_age = torch.zeros(B, device=device)
    for j, logits in logits_dict.items():
        pred = torch.argmax(logits, dim=1)  # 0..13
        for b in range(B):
            cls_age[b] += float(score_table[j][int(pred[b].item())])
    return cls_age


# =========================================================
# 5) 单轮训练：source有标签 + target无标签（领域自适应）
# loader_source batch:
#   {"image":..., "labels":{joint:...}, "bone_age":...}
# loader_target batch:
#   {"image":...}  或 (image,)
# =========================================================
def train_one_epoch_da(
        student,
        teachers,  # list of 5 fold models
        loader_source,
        loader_target,
        optimizer,
        device,
        score_table,
        epoch,
        max_epoch,
        w_cls=1.0,
        w_age=0.4,
        w_kd=0.5,
        w_domain=0.2,
        T=2.0
):
    student.train()
    for t in teachers:
        t.eval()

    ce_joint = nn.CrossEntropyLoss()
    ce_domain = nn.CrossEntropyLoss()
    l1 = nn.L1Loss()

    total_loss = 0.0
    n_sample = 0

    target_iter = iter(loader_target)

    for src_batch in tqdm(loader_source, desc=f"Train DA E{epoch}", leave=False):
        try:
            tgt_batch = next(target_iter)
        except StopIteration:
            target_iter = iter(loader_target)
            tgt_batch = next(target_iter)

        src_img = src_batch["image"].to(device)
        src_labels = {k: v.to(device) for k, v in src_batch["labels"].items()}
        src_age = src_batch["bone_age"].float().to(device)

        if isinstance(tgt_batch, dict):
            tgt_img = tgt_batch["image"].to(device)
        elif isinstance(tgt_batch, (list, tuple)):
            tgt_img = tgt_batch[0].to(device)
        else:
            tgt_img = tgt_batch.to(device)

        p = float(epoch - 1) / float(max_epoch)
        grl_lambda = 2.0 / (1.0 + math.exp(-10 * p)) - 1.0

        optimizer.zero_grad()

        # ---- student forward
        s_logits_dict, s_formula_age, s_feat_src, s_domain_src = student(
            src_img, grl_lambda=grl_lambda, need_domain=True
        )
        _, _, s_feat_tgt, s_domain_tgt = student(
            tgt_img, grl_lambda=grl_lambda, need_domain=True
        )

        # ---- 1) source 监督分类
        loss_cls = 0.0
        nj = 0
        for j, logits in s_logits_dict.items():
            if j in src_labels:
                loss_cls += ce_joint(logits, src_labels[j])
                nj += 1
        loss_cls = loss_cls / max(1, nj)

        # ---- 2) 骨龄损失（分类映射年龄 + 超图公式年龄）
        s_cls_age = compute_cls_age_from_logits(s_logits_dict, score_table)
        loss_age = l1(s_cls_age, src_age) + l1(s_formula_age, src_age)

        # ---- 3) 五折 teacher ensemble 蒸馏
        with torch.no_grad():
            tea_logits_all = []
            for t in teachers:
                out = t(src_img)
                if isinstance(out, tuple):
                    t_logits_dict = out[0]
                else:
                    t_logits_dict = out
                tea_logits_all.append(t_logits_dict)

        loss_kd = 0.0
        kd_n = 0
        for j in s_logits_dict.keys():
            valid = [d[j] for d in tea_logits_all if j in d]
            if len(valid) == 0:
                continue
            t_avg = torch.stack(valid, dim=0).mean(dim=0)
            loss_kd += kd_kl(s_logits_dict[j], t_avg, T=T)
            kd_n += 1
        loss_kd = loss_kd / max(1, kd_n)

        # ---- 4) 域对抗损失（source=0, target=1）
        y_src_dom = torch.zeros(s_domain_src.size(0), dtype=torch.long, device=device)
        y_tgt_dom = torch.ones(s_domain_tgt.size(0), dtype=torch.long, device=device)

        loss_dom = ce_domain(s_domain_src, y_src_dom) + ce_domain(s_domain_tgt, y_tgt_dom)

        loss = w_cls * loss_cls + w_age * loss_age + w_kd * loss_kd + w_domain * loss_dom
        loss.backward()
        optimizer.step()

        bs = src_img.size(0)
        total_loss += loss.item() * bs
        n_sample += bs

    return total_loss / max(1, n_sample)


# =========================================================
# 6) 验证 / 测试（单模型）
# =========================================================
@torch.no_grad()
def evaluate_student(model, loader, device, score_table, alpha=0.7, beta=0.3):
    model.eval()
    pred_age = []

    for batch in tqdm(loader, desc="Eval/Test", leave=False):
        if isinstance(batch, dict):
            img = batch["image"].to(device)
        elif isinstance(batch, (list, tuple)):
            img = batch[0].to(device)
        else:
            img = batch.to(device)

        logits_dict, formula_age, _, _ = model(img, need_domain=False)
        cls_age = compute_cls_age_from_logits(logits_dict, score_table)
        final_age = alpha * cls_age + beta * formula_age
        pred_age.extend(final_age.cpu().tolist())

    return pred_age


# =========================================================
# 7) 集成测试（多个 student）
# =========================================================
@torch.no_grad()
def ensemble_test_students(models, loader, device, score_table, alpha=0.7, beta=0.3):
    for m in models:
        m.eval()

    all_age = []
    for batch in tqdm(loader, desc="Ensemble Test"):
        if isinstance(batch, dict):
            img = batch["image"].to(device)
        elif isinstance(batch, (list, tuple)):
            img = batch[0].to(device)
        else:
            img = batch.to(device)

        logits_list = []
        formula_list = []
        for m in models:
            logits_dict, formula_age, _, _ = m(img, need_domain=False)
            logits_list.append(logits_dict)
            formula_list.append(formula_age)

        joint_names = logits_list[0].keys()
        avg_logits_dict = {}
        for j in joint_names:
            avg_logits_dict[j] = torch.stack([d[j] for d in logits_list], dim=0).mean(dim=0)

        avg_formula = torch.stack(formula_list, dim=0).mean(dim=0)
        cls_age = compute_cls_age_from_logits(avg_logits_dict, score_table)
        final_age = alpha * cls_age + beta * avg_formula
        all_age.extend(final_age.cpu().tolist())

    return all_age


import os
import glob
import random
from typing import List, Dict, Tuple

import torch
from torch.utils.data import Dataset, DataLoader
from PIL import Image
from torchvision import transforms

# 你的数据根目录
# arthrosis/
#   DIP/1/*.png ...
#   PIP/1/*.png ...
DATA_ROOT = "/kaggle/input/arthrosis1/arthrosis"

IMG_EXTS = ("*.png", "*.jpg", "*.jpeg", "*.bmp", "*.tif", "*.tiff")


def list_class_dirs(joint_dir: str):
    # 只保留数字类别目录
    cls_dirs = []
    for name in os.listdir(joint_dir):
        p = os.path.join(joint_dir, name)
        if os.path.isdir(p) and name.isdigit():
            cls_dirs.append(name)
    cls_dirs = sorted(cls_dirs, key=lambda x: int(x))
    return cls_dirs


def build_single_joint_samples(data_root: str, joint_name: str) -> Tuple[List[Dict], Dict[int, int]]:
    """
    返回:
    - samples: [{"image_path":..., "label":int}]
    - class_to_idx: {原始类别号: 连续idx}
    """
    joint_dir = os.path.join(data_root, joint_name)
    if not os.path.isdir(joint_dir):
        raise FileNotFoundError(f"joint目录不存在: {joint_dir}")

    cls_names = list_class_dirs(joint_dir)
    if len(cls_names) == 0:
        raise ValueError(f"{joint_name} 下没找到数字类别子目录")

    raw_classes = [int(c) for c in cls_names]
    class_to_idx = {c: i for i, c in enumerate(sorted(raw_classes))}

    samples = []
    for c in raw_classes:
        c_dir = os.path.join(joint_dir, str(c))
        files = []
        for ext in IMG_EXTS:
            files.extend(glob.glob(os.path.join(c_dir, ext)))
        for fp in files:
            samples.append({"image_path": fp, "label": class_to_idx[c]})

    if len(samples) == 0:
        raise ValueError(f"{joint_name} 样本为空，请检查图片后缀或目录")
    return samples, class_to_idx


def split_train_val(samples: List[Dict], val_ratio: float = 0.2, seed: int = 42):
    random.Random(seed).shuffle(samples)
    n_val = int(len(samples) * val_ratio)
    val = samples[:n_val]
    train = samples[n_val:]
    if len(train) == 0 or len(val) == 0:
        raise ValueError(f"划分后为空: train={len(train)} val={len(val)}，请增大数据量或调整val_ratio")
    return train, val


class SingleJointDataset(Dataset):
    def __init__(self, samples, img_size=224, train=True):
        self.samples = samples
        if train:
            self.tf = transforms.Compose([
                transforms.Resize((img_size, img_size)),
                transforms.RandomRotation(10),
                transforms.ToTensor(),
                transforms.Normalize([0.485, 0.456, 0.406],
                                     [0.229, 0.224, 0.225]),
            ])
        else:
            self.tf = transforms.Compose([
                transforms.Resize((img_size, img_size)),
                transforms.ToTensor(),
                transforms.Normalize([0.485, 0.456, 0.406],
                                     [0.229, 0.224, 0.225]),
            ])

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, i):
        s = self.samples[i]
        img = Image.open(s["image_path"]).convert("RGB")
        img = self.tf(img)
        y = torch.tensor(s["label"], dtype=torch.long)
        return img, y


# ===== 示例：先只训练 DIP =====
joint_name = "DIP"
samples, class_to_idx = build_single_joint_samples(DATA_ROOT, joint_name)
train_samples, val_samples = split_train_val(samples, val_ratio=0.2, seed=42)

train_ds = SingleJointDataset(train_samples, img_size=224, train=True)
val_ds = SingleJointDataset(val_samples, img_size=224, train=False)

print(f"{joint_name}: total={len(samples)} train={len(train_ds)} val={len(val_ds)} classes={len(class_to_idx)}")

train_loader = DataLoader(train_ds, batch_size=16, shuffle=True, num_workers=0, pin_memory=True)
val_loader = DataLoader(val_ds, batch_size=16, shuffle=False, num_workers=0, pin_memory=True)
DIP: total = 1262
train = 1010
val = 252
classes = 11
import os
import glob
import math
import random
from collections import Counter, OrderedDict
from typing import List, Dict

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from PIL import Image
from torchvision import transforms, models

# =========================
# Config
# =========================
SEED = 42
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

SOURCE_ROOT = "/kaggle/input/arthrosis1/arthrosis"  # source domain
TARGET_ROOT = "/kaggle/input/arthrosis1/arthrosis"  # target domain (替换成真实目标域更合理)
JOINTS = ["DIP", "DIPFirst", "PIP", "PIPFirst", "MCP", "MCPFirst", "MIP", "Radius", "Ulna"]

CKPT_FOLDS = [
    "/kaggle/input/models/lihaohao111/yuxunlianmoxing/pytorch/default/1/model_fold_0 (1).pth",
    "/kaggle/input/models/lihaohao111/yuxunlianmoxing/pytorch/default/1/model_fold_1 (1).pth",
    "/kaggle/input/models/lihaohao111/yuxunlianmoxing/pytorch/default/1/model_fold_2 (1).pth",
    "/kaggle/input/models/lihaohao111/yuxunlianmoxing/pytorch/default/1/model_fold_3.pth",
    "/kaggle/input/models/lihaohao111/yuxunlianmoxing/pytorch/default/1/model_fold_4.pth",
]

OUT_DIR = "/kaggle/working/rewrite_da_hyper"
os.makedirs(OUT_DIR, exist_ok=True)

IMG_SIZE = 224
BATCH_SIZE = 16
NUM_WORKERS = 2
EPOCHS = 12
LR = 1e-4
WEIGHT_DECAY = 1e-4
VAL_RATIO = 0.2

LAMBDA_DOMAIN = 0.2
LAMBDA_HYPER = 0.2

IMG_EXTS = ("*.png", "*.jpg", "*.jpeg", "*.bmp", "*.tif", "*.tiff")


# =========================
# Utils
# =========================
def seed_everything(seed=42):
    random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def list_images(folder):
    files = []
    for e in IMG_EXTS:
        files.extend(glob.glob(os.path.join(folder, e)))
    return sorted(files)


def list_cls_dirs(joint_dir):
    d = []
    for n in os.listdir(joint_dir):
        p = os.path.join(joint_dir, n)
        if os.path.isdir(p) and n.isdigit():
            d.append(n)
    return sorted(d, key=lambda x: int(x))


def split_train_val(samples, val_ratio=0.2, seed=42):
    samples = samples.copy()
    random.Random(seed).shuffle(samples)
    n_val = int(len(samples) * val_ratio)
    val = samples[:n_val]
    train = samples[n_val:]
    if len(train) == 0 or len(val) == 0:
        raise ValueError("split empty")
    return train, val


def extract_state_dict(ckpt_obj):
    if isinstance(ckpt_obj, dict):
        for k in ["model", "state_dict", "model_state"]:
            if k in ckpt_obj and isinstance(ckpt_obj[k], dict):
                return ckpt_obj[k]
    return ckpt_obj


# =========================
# 5-fold average weights
# =========================
def average_checkpoints(paths):
    avg = None
    n = 0
    for p in paths:
        sd = extract_state_dict(torch.load(p, map_location="cpu"))
        clean = OrderedDict()
        for k, v in sd.items():
            kk = k[7:] if k.startswith("module.") else k
            clean[kk] = v

        if avg is None:
            avg = OrderedDict()
            for k, v in clean.items():
                avg[k] = v.clone().float() if torch.is_floating_point(v) else v.clone()
            n = 1
        else:
            n += 1
            for k, v in clean.items():
                if k in avg and torch.is_floating_point(v) and torch.is_floating_point(avg[k]):
                    avg[k] += v.float()

    for k in avg.keys():
        if torch.is_floating_point(avg[k]):
            avg[k] /= float(n)
    return avg


# =========================
# Data build (single joint)
# =========================
def build_source_samples(root, joint):
    jdir = os.path.join(root, joint)
    if not os.path.isdir(jdir):
        raise FileNotFoundError(jdir)

    cls_dirs = list_cls_dirs(jdir)
    raw_cls = [int(c) for c in cls_dirs]
    class_to_idx = {c: i for i, c in enumerate(sorted(raw_cls))}

    samples = []
    for c in raw_cls:
        cdir = os.path.join(jdir, str(c))
        for fp in list_images(cdir):
            samples.append({"image_path": fp, "label": class_to_idx[c]})
    return samples, class_to_idx


def build_target_samples(root, joint):
    jdir = os.path.join(root, joint)
    if not os.path.isdir(jdir):
        raise FileNotFoundError(jdir)

    samples = []
    cls_dirs = list_cls_dirs(jdir)
    if len(cls_dirs) > 0:
        for c in cls_dirs:
            for fp in list_images(os.path.join(jdir, c)):
                samples.append({"image_path": fp})
    else:
        for fp in list_images(jdir):
            samples.append({"image_path": fp})
    return samples


class SrcDataset(Dataset):
    def __init__(self, samples, train=True):
        self.samples = samples
        if train:
            self.tf = transforms.Compose([
                transforms.Resize((IMG_SIZE, IMG_SIZE)),
                transforms.RandomHorizontalFlip(0.5),
                transforms.RandomRotation(10),
                transforms.ToTensor(),
                transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
            ])
        else:
            self.tf = transforms.Compose([
                transforms.Resize((IMG_SIZE, IMG_SIZE)),
                transforms.ToTensor(),
                transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
            ])

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        s = self.samples[idx]
        x = Image.open(s["image_path"]).convert("RGB")
        x = self.tf(x)
        y = torch.tensor(s["label"], dtype=torch.long)
        return x, y


class TgtDataset(Dataset):
    def __init__(self, samples):
        self.samples = samples
        self.tf = transforms.Compose([
            transforms.Resize((IMG_SIZE, IMG_SIZE)),
            transforms.RandomHorizontalFlip(0.5),
            transforms.RandomRotation(10),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])

    def __len__(self): return len(self.samples)

    def __getitem__(self, idx):
        s = self.samples[idx]
        x = Image.open(s["image_path"]).convert("RGB")
        x = self.tf(x)
        return x


# =========================
# DANN + Hyper
# =========================
class GRL(torch.autograd.Function):
    @staticmethod
    def forward(ctx, x, lambd):
        ctx.lambd = lambd
        return x.view_as(x)

    @staticmethod
    def backward(ctx, grad_out):
        return -ctx.lambd * grad_out, None


def grad_reverse(x, lambd):
    return GRL.apply(x, lambd)


class DANNHyperModel(nn.Module):
    def __init__(self, num_classes):
        super().__init__()
        base = models.resnet50(weights=None)
        feat_dim = base.fc.in_features
        base.fc = nn.Identity()
        self.backbone = base

        self.classifier = nn.Linear(feat_dim, num_classes)
        self.domain_clf = nn.Sequential(
            nn.Linear(feat_dim, 256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, 2)
        )

        # “超图一致性”简化为同批特征局部关系约束
        self.hyper_proj = nn.Linear(feat_dim, 128)

    def forward(self, x, lambda_grl=0.0):
        f = self.backbone(x)  # [B,2048]
        cls = self.classifier(f)  # [B,C]
        dom = self.domain_clf(grad_reverse(f, lambda_grl))
        h = self.hyper_proj(f)  # [B,128]
        return cls, dom, h


def hyper_consistency_loss(h_feat, cls_logits):
    # 用预测概率相近样本的特征距离做轻量约束
    p = F.softmax(cls_logits, dim=1)
    sim = p @ p.t()  # [B,B]
    dist = torch.cdist(h_feat, h_feat)  # [B,B]
    loss = (sim * dist).mean()
    return loss


def load_avg_backbone(model, avg_sd):
    model_sd = model.state_dict()
    loadable = OrderedDict()

    for k, v in avg_sd.items():
        if k.startswith("backbone."):
            tk = k
        elif k.startswith("resnet."):
            tk = "backbone." + k[len("resnet."):]
        elif k.startswith("conv1") or k.startswith("bn1") or k.startswith("layer"):
            tk = "backbone." + k
        else:
            continue
        if tk in model_sd and model_sd[tk].shape == v.shape:
            loadable[tk] = v

    msg = model.load_state_dict(loadable, strict=False)
    print(f"[AvgLoad] loaded={len(loadable)} missing={len(msg.missing_keys)} unexpected={len(msg.unexpected_keys)}")


@torch.no_grad()
def evaluate(model, loader, criterion, device):
    model.eval()
    total_loss, total_correct, total = 0.0, 0, 0
    for x, y in loader:
        x, y = x.to(device), y.to(device)
        cls, _, _ = model(x, lambda_grl=0.0)
        loss = criterion(cls, y)
        pred = cls.argmax(1)
        total_loss += loss.item()
        total_correct += (pred == y).sum().item()
        total += y.size(0)
    return total_loss / max(1, len(loader)), total_correct / max(1, total)


def train_joint(joint_name, avg_sd):
    src_samples, class_to_idx = build_source_samples(SOURCE_ROOT, joint_name)
    src_train, src_val = split_train_val(src_samples, VAL_RATIO, SEED)
    tgt_samples = build_target_samples(TARGET_ROOT, joint_name)

    num_classes = len(class_to_idx)
    print(
        f"[{joint_name}] src={len(src_samples)} train={len(src_train)} val={len(src_val)} tgt={len(tgt_samples)} classes={num_classes}")

    src_train_loader = DataLoader(SrcDataset(src_train, train=True), batch_size=BATCH_SIZE, shuffle=True,
                                  num_workers=NUM_WORKERS, drop_last=True)
    src_val_loader = DataLoader(SrcDataset(src_val, train=False), batch_size=BATCH_SIZE, shuffle=False,
                                num_workers=NUM_WORKERS)
    tgt_loader = DataLoader(TgtDataset(tgt_samples), batch_size=BATCH_SIZE, shuffle=True, num_workers=NUM_WORKERS,
                            drop_last=True)

    model = DANNHyperModel(num_classes).to(DEVICE)
    load_avg_backbone(model, avg_sd)

    class_counts = Counter([s["label"] for s in src_train])
    w = []
    for c in range(num_classes):
        w.append(len(src_train) / (num_classes * max(1, class_counts.get(c, 1))))
    cls_criterion = nn.CrossEntropyLoss(weight=torch.tensor(w, dtype=torch.float32, device=DEVICE))
    dom_criterion = nn.CrossEntropyLoss()

    optimizer = optim.AdamW(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)

    best_acc = -1.0
    best_epoch = -1
    joint_dir = os.path.join(OUT_DIR, joint_name)
    os.makedirs(joint_dir, exist_ok=True)

    tgt_iter = iter(tgt_loader)

    for epoch in range(1, EPOCHS + 1):
        model.train()
        total_loss, total_cls, total_dom, total_hyp, total_acc, steps = 0, 0, 0, 0, 0, 0
        n_steps = max(len(src_train_loader), len(tgt_loader))

        src_iter = iter(src_train_loader)
        for step in range(n_steps):
            try:
                xs, ys = next(src_iter)
            except StopIteration:
                src_iter = iter(src_train_loader)
                xs, ys = next(src_iter)

            try:
                xt = next(tgt_iter)
            except StopIteration:
                tgt_iter = iter(tgt_loader)
                xt = next(tgt_iter)

            xs, ys, xt = xs.to(DEVICE), ys.to(DEVICE), xt.to(DEVICE)

            p = ((epoch - 1) * n_steps + step) / float(EPOCHS * n_steps)
            lambda_grl = 2. / (1. + math.exp(-10 * p)) - 1.

            optimizer.zero_grad()

            cls_s, dom_s, h_s = model(xs, lambda_grl=lambda_grl)
            _, dom_t, _ = model(xt, lambda_grl=lambda_grl)

            loss_cls = cls_criterion(cls_s, ys)

            y_dom_s = torch.zeros(dom_s.size(0), dtype=torch.long, device=DEVICE)
            y_dom_t = torch.ones(dom_t.size(0), dtype=torch.long, device=DEVICE)
            loss_dom = dom_criterion(dom_s, y_dom_s) + dom_criterion(dom_t, y_dom_t)

            loss_hyp = hyper_consistency_loss(h_s, cls_s)

            loss = loss_cls + LAMBDA_DOMAIN * loss_dom + LAMBDA_HYPER * loss_hyp
            loss.backward()
            optimizer.step()

            pred = cls_s.argmax(1)
            acc = (pred == ys).float().mean().item()

            total_loss += loss.item()
            total_cls += loss_cls.item()
            total_dom += loss_dom.item()
            total_hyp += loss_hyp.item()
            total_acc += acc
            steps += 1

        scheduler.step()

        val_loss, val_acc = evaluate(model, src_val_loader, cls_criterion, DEVICE)

        print(
            f"[{joint_name}] E{epoch:02d}/{EPOCHS} "
            f"train_loss={total_loss / steps:.4f} cls={total_cls / steps:.4f} "
            f"dom={total_dom / steps:.4f} hyp={total_hyp / steps:.4f} acc={total_acc / steps:.4f} | "
            f"val_loss={val_loss:.4f} val_acc={val_acc:.4f}"
        )

        if val_acc > best_acc:
            best_acc = val_acc
            best_epoch = epoch
            torch.save({
                "model_state": model.state_dict(),
                "class_to_idx": class_to_idx,
                "joint_name": joint_name,
                "best_val_acc": best_acc,
                "best_epoch": best_epoch
            }, os.path.join(joint_dir, f"best_{joint_name}.pth"))

    return {"joint": joint_name, "best_val_acc": best_acc, "best_epoch": best_epoch}


def main():
    seed_everything(SEED)
    print("Device:", DEVICE)

    avg_sd = average_checkpoints(CKPT_FOLDS)

    results = []
    for j in JOINTS:
        try:
            r = train_joint(j, avg_sd)
            results.append(r)
        except Exception as e:
            print(f"[{j}] FAILED: {e}")
            results.append({"joint": j, "best_val_acc": -1.0, "best_epoch": -1})

    summary_path = os.path.join(OUT_DIR, "summary.csv")
    with open(summary_path, "w") as f:
        f.write("joint,best_val_acc,best_epoch\n")
        for r in results:
            f.write(f"{r['joint']},{r['best_val_acc']:.6f},{r['best_epoch']}\n")

    print("\n==== DONE ====")
    print("summary:", summary_path)
    for r in results:
        print(f"{r['joint']}: {r['best_val_acc']:.4f} @ {r['best_epoch']}")


if __name__ == "__main__":
    main()
Device: cuda
[DIP]
src = 1262
train = 1010
val = 252
tgt = 1262
classes = 11
[AvgLoad]
loaded = 318
missing = 8
unexpected = 0
[DIP]
E01 / 12
train_loss = 1.9935
cls = 1.6917
dom = 1.3911
hyp = 0.1180
acc = 0.4095 | val_loss = 1.3126
val_acc = 0.5476
[DIP]
E02 / 12
train_loss = 1.4101
cls = 1.1197
dom = 1.3917
hyp = 0.0603
acc = 0.5665 | val_loss = 1.1431
val_acc = 0.5476
[DIP]
E03 / 12
train_loss = 1.2133
cls = 0.9254
dom = 1.3927
hyp = 0.0467
acc = 0.6306 | val_loss = 0.8670
val_acc = 0.6468
[DIP]
E04 / 12
train_loss = 1.1182
cls = 0.8309
dom = 1.3918
hyp = 0.0446
acc = 0.6707 | val_loss = 0.8554
val_acc = 0.6865
[DIP]
E05 / 12
train_loss = 0.9821
cls = 0.6954
dom = 1.3898
hyp = 0.0435
acc = 0.7196 | val_loss = 1.0199
val_acc = 0.6111
[DIP]
E06 / 12
train_loss = 0.8597
cls = 0.5737
dom = 1.3871
hyp = 0.0424
acc = 0.7620 | val_loss = 0.9158
val_acc = 0.6468
[DIP]
E07 / 12
train_loss = 0.7760
cls = 0.4888
dom = 1.3941
hyp = 0.0419
acc = 0.8013 | val_loss = 1.0646
val_acc = 0.6627
[DIP]
E08 / 12
train_loss = 0.6843
cls = 0.3981
dom = 1.3896
hyp = 0.0413
acc = 0.8261 | val_loss = 1.0860
val_acc = 0.6905
[DIP]
E09 / 12
train_loss = 0.5923
cls = 0.3060
dom = 1.3889
hyp = 0.0426
acc = 0.8750 | val_loss = 1.1666
val_acc = 0.7063
[DIP]
E10 / 12
train_loss = 0.5513
cls = 0.2654
dom = 1.3871
hyp = 0.0423
acc = 0.8838 | val_loss = 1.0621
val_acc = 0.7024
[DIP]
E11 / 12
train_loss = 0.4931
cls = 0.2070
dom = 1.3870
hyp = 0.0437
acc = 0.9095 | val_loss = 1.1137
val_acc = 0.7143
[DIP]
E12 / 12
train_loss = 0.5189
cls = 0.2333
dom = 1.3868
hyp = 0.0416
acc = 0.9095 | val_loss = 1.0766
val_acc = 0.7222
[DIPFirst]
src = 632
train = 506
val = 126
tgt = 632
classes = 11
[AvgLoad]
loaded = 318
missing = 8
unexpected = 0
[DIPFirst]
E01 / 12
train_loss = 2.4598
cls = 2.1494
dom = 1.3935
hyp = 0.1585
acc = 0.3013 | val_loss = 1.7585
val_acc = 0.4048
[DIPFirst]
E02 / 12
train_loss = 1.7436
cls = 1.4455
dom = 1.3886
hyp = 0.1023
acc = 0.4551 | val_loss = 1.4623
val_acc = 0.5556
[DIPFirst]
E03 / 12
train_loss = 1.5341
cls = 1.2392
dom = 1.3874
hyp = 0.0873
acc = 0.5625 | val_loss = 1.9296
val_acc = 0.5476
[DIPFirst]
E04 / 12
train_loss = 1.3626
cls = 1.0687
dom = 1.3962
hyp = 0.0731
acc = 0.5929 | val_loss = 1.1207
val_acc = 0.5635
[DIPFirst]
E05 / 12
train_loss = 1.0915
cls = 0.7993
dom = 1.3928
hyp = 0.0685
acc = 0.6587 | val_loss = 1.3909
val_acc = 0.5397
[DIPFirst]
E06 / 12
train_loss = 0.9826
cls = 0.6887
dom = 1.4000
hyp = 0.0693
acc = 0.7228 | val_loss = 1.2750
val_acc = 0.6111
[DIPFirst]
E07 / 12
train_loss = 0.8144
cls = 0.5221
dom = 1.3898
hyp = 0.0717
acc = 0.7837 | val_loss = 1.7294
val_acc = 0.5952
[DIPFirst]
E08 / 12
train_loss = 0.7193
cls = 0.4288
dom = 1.3875
hyp = 0.0653
acc = 0.8397 | val_loss = 1.5735
val_acc = 0.5635
[DIPFirst]
E09 / 12
train_loss = 0.6570
cls = 0.3657
dom = 1.3892
hyp = 0.0671
acc = 0.8446 | val_loss = 1.4589
val_acc = 0.6190
[DIPFirst]
E10 / 12
train_loss = 0.5969
cls = 0.3064
dom = 1.3850
hyp = 0.0675
acc = 0.8798 | val_loss = 1.5032
val_acc = 0.6349
[DIPFirst]
E11 / 12
train_loss = 0.5315
cls = 0.2402
dom = 1.3893
hyp = 0.0669
acc = 0.8974 | val_loss = 1.4733
val_acc = 0.6349
[DIPFirst]
E12 / 12
train_loss = 0.5634
cls = 0.2725
dom = 1.3869
hyp = 0.0676
acc = 0.8910 | val_loss = 1.4438
val_acc = 0.6508
[PIP]
src = 1262
train = 1010
val = 252
tgt = 1262
classes = 12
[AvgLoad]
loaded = 318
missing = 8
unexpected = 0
[PIP]
E01 / 12
train_loss = 2.1425
cls = 1.8404
dom = 1.3919
hyp = 0.1187
acc = 0.3934 | val_loss = 1.4206
val_acc = 0.4643
[PIP]
E02 / 12
train_loss = 1.4585
cls = 1.1670
dom = 1.3902
hyp = 0.0673
acc = 0.6010 | val_loss = 1.2173
val_acc = 0.5357
[PIP]
E03 / 12
train_loss = 1.2654
cls = 0.9757
dom = 1.3936
hyp = 0.0548
acc = 0.6394 | val_loss = 0.8666
val_acc = 0.6389
[PIP]
E04 / 12
train_loss = 1.0256
cls = 0.7369
dom = 1.3921
hyp = 0.0512
acc = 0.7139 | val_loss = 1.1527
val_acc = 0.6548
[PIP]
E05 / 12
train_loss = 0.9101
cls = 0.6208
dom = 1.3956
hyp = 0.0511
acc = 0.7756 | val_loss = 1.1967
val_acc = 0.6667
[PIP]
E06 / 12
train_loss = 0.8889
cls = 0.6017
dom = 1.3890
hyp = 0.0466
acc = 0.7716 | val_loss = 1.0487
val_acc = 0.6905
[PIP]
E07 / 12
train_loss = 0.7757
cls = 0.4884
dom = 1.3909
hyp = 0.0457
acc = 0.8093 | val_loss = 0.9938
val_acc = 0.6984
[PIP]
E08 / 12
train_loss = 0.6410
cls = 0.3536
dom = 1.3908
hyp = 0.0463
acc = 0.8646 | val_loss = 0.9448
val_acc = 0.7183
[PIP]
E09 / 12
train_loss = 0.5443
cls = 0.2564
dom = 1.3920
hyp = 0.0472
acc = 0.9014 | val_loss = 1.0618
val_acc = 0.6905
[PIP]
E10 / 12
train_loss = 0.4992
cls = 0.2126
dom = 1.3865
hyp = 0.0468
acc = 0.9223 | val_loss = 1.0298
val_acc = 0.7262
[PIP]
E11 / 12
train_loss = 0.4616
cls = 0.1753
dom = 1.3858
hyp = 0.0457
acc = 0.9415 | val_loss = 1.0125
val_acc = 0.7222
[PIP]
E12 / 12
train_loss = 0.4867
cls = 0.2003
dom = 1.3855
hyp = 0.0467
acc = 0.9343 | val_loss = 1.0027
val_acc = 0.7222
[PIPFirst]
src = 632
train = 506
val = 126
tgt = 632
classes = 12
[AvgLoad]
loaded = 318
missing = 8
unexpected = 0
[PIPFirst]
E01 / 12
train_loss = 2.3883
cls = 2.0826
dom = 1.3925
hyp = 0.1359
acc = 0.2901 | val_loss = 1.6593
val_acc = 0.4603
[PIPFirst]
E02 / 12
train_loss = 1.6235
cls = 1.3279
dom = 1.3908
hyp = 0.0871
acc = 0.4936 | val_loss = 1.3673
val_acc = 0.4921
[PIPFirst]
E03 / 12
train_loss = 1.3148
cls = 1.0209
dom = 1.3977
hyp = 0.0720
acc = 0.6186 | val_loss = 1.2696
val_acc = 0.6111
[PIPFirst]
E04 / 12
train_loss = 1.2339
cls = 0.9419
dom = 1.3971
hyp = 0.0624
acc = 0.6699 | val_loss = 1.4348
val_acc = 0.5000
[PIPFirst]
E05 / 12
train_loss = 1.0286
cls = 0.7400
dom = 1.3838
hyp = 0.0592
acc = 0.7532 | val_loss = 1.4667
val_acc = 0.5476
[PIPFirst]
E06 / 12
train_loss = 0.8586
cls = 0.5683
dom = 1.3958
hyp = 0.0559
acc = 0.7933 | val_loss = 1.3042
val_acc = 0.5794
[PIPFirst]
E07 / 12
train_loss = 0.6439
cls = 0.3542
dom = 1.3939
hyp = 0.0550
acc = 0.8702 | val_loss = 1.3901
val_acc = 0.6349
[PIPFirst]
E08 / 12
train_loss = 0.5948
cls = 0.3058
dom = 1.3893
hyp = 0.0558
acc = 0.8974 | val_loss = 1.3366
val_acc = 0.6349
[PIPFirst]
E09 / 12
train_loss = 0.5448
cls = 0.2564
dom = 1.3857
hyp = 0.0562
acc = 0.9167 | val_loss = 1.3575
val_acc = 0.6746
[PIPFirst]
E10 / 12
train_loss = 0.4934
cls = 0.2055
dom = 1.3856
hyp = 0.0537
acc = 0.9215 | val_loss = 1.4301
val_acc = 0.6587
[PIPFirst]
E11 / 12
train_loss = 0.4734
cls = 0.1852
dom = 1.3860
hyp = 0.0547
acc = 0.9519 | val_loss = 1.5010
val_acc = 0.6905
[PIPFirst]
E12 / 12
train_loss = 0.4491
cls = 0.1608
dom = 1.3877
hyp = 0.0539
acc = 0.9567 | val_loss = 1.4482
val_acc = 0.6667
[MCP]
src = 1262
train = 1010
val = 252
tgt = 1262
classes = 10
[AvgLoad]
loaded = 318
missing = 8
unexpected = 0
[MCP]
E01 / 12
train_loss = 1.8117
cls = 1.5089
dom = 1.3899
hyp = 0.1245
acc = 0.4575 | val_loss = 1.2749
val_acc = 0.4683
[MCP]
E02 / 12
train_loss = 1.2728
cls = 0.9805
dom = 1.3942
hyp = 0.0673
acc = 0.6122 | val_loss = 1.1705
val_acc = 0.5794
[MCP]
E03 / 12
train_loss = 1.1525
cls = 0.8625
dom = 1.3933
hyp = 0.0566
acc = 0.6506 | val_loss = 0.7693
val_acc = 0.7063
[MCP]
E04 / 12
train_loss = 0.9459
cls = 0.6583
dom = 1.3885
hyp = 0.0497
acc = 0.7252 | val_loss = 0.8189
val_acc = 0.6825
[MCP]
E05 / 12
train_loss = 0.8442
cls = 0.5565
dom = 1.3916
hyp = 0.0468
acc = 0.7620 | val_loss = 0.8223
val_acc = 0.6905
[MCP]
E06 / 12
train_loss = 0.7688
cls = 0.4812
dom = 1.3906
hyp = 0.0475
acc = 0.8013 | val_loss = 0.6858
val_acc = 0.7063
[MCP]
E07 / 12
train_loss = 0.6928
cls = 0.4054
dom = 1.3902
hyp = 0.0468
acc = 0.8261 | val_loss = 0.7787
val_acc = 0.6905
[MCP]
E08 / 12
train_loss = 0.5736
cls = 0.2871
dom = 1.3868
hyp = 0.0457
acc = 0.8870 | val_loss = 0.8113
val_acc = 0.6667
[MCP]
E09 / 12
train_loss = 0.5216
cls = 0.2345
dom = 1.3892
hyp = 0.0465
acc = 0.9079 | val_loss = 0.8805
val_acc = 0.6865
[MCP]
E10 / 12
train_loss = 0.4816
cls = 0.1950
dom = 1.3865
hyp = 0.0465
acc = 0.9287 | val_loss = 0.8633
val_acc = 0.7143
[MCP]
E11 / 12
train_loss = 0.4472
cls = 0.1610
dom = 1.3864
hyp = 0.0443
acc = 0.9407 | val_loss = 0.9125
val_acc = 0.7024
[MCP]
E12 / 12
train_loss = 0.4237
cls = 0.1372
dom = 1.3876
hyp = 0.0448
acc = 0.9567 | val_loss = 0.8657
val_acc = 0.6825
[MCPFirst]
src = 633
train = 507
val = 126
tgt = 633
classes = 11
[AvgLoad]
loaded = 318
missing = 8
unexpected = 0
[MCPFirst]
E01 / 12
train_loss = 2.2395
cls = 1.9309
dom = 1.3926
hyp = 0.1506
acc = 0.2981 | val_loss = 1.4363
val_acc = 0.4444
[MCPFirst]
E02 / 12
train_loss = 1.4830
cls = 1.1862
dom = 1.3985
hyp = 0.0852
acc = 0.5865 | val_loss = 1.2360
val_acc = 0.5238
[MCPFirst]
E03 / 12
train_loss = 1.2005
cls = 0.9094
dom = 1.3893
hyp = 0.0661
acc = 0.7067 | val_loss = 1.0546
val_acc = 0.6190
[MCPFirst]
E04 / 12
train_loss = 1.0028
cls = 0.7112
dom = 1.3973
hyp = 0.0604
acc = 0.7596 | val_loss = 1.0640
val_acc = 0.5714
[MCPFirst]
E05 / 12
train_loss = 0.8809
cls = 0.5923
dom = 1.3845
hyp = 0.0588
acc = 0.8109 | val_loss = 1.1312
val_acc = 0.6746
[MCPFirst]
E06 / 12
train_loss = 0.7309
cls = 0.4417
dom = 1.3908
hyp = 0.0554
acc = 0.8590 | val_loss = 1.2304
val_acc = 0.6825
[MCPFirst]
E07 / 12
train_loss = 0.6407
cls = 0.3528
dom = 1.3880
hyp = 0.0520
acc = 0.8782 | val_loss = 1.2821
val_acc = 0.7063
[MCPFirst]
E08 / 12
train_loss = 0.5890
cls = 0.3001
dom = 1.3937
hyp = 0.0508
acc = 0.9119 | val_loss = 0.9432
val_acc = 0.7302
[MCPFirst]
E09 / 12
train_loss = 0.4759
cls = 0.1867
dom = 1.3952
hyp = 0.0509
acc = 0.9583 | val_loss = 1.0139
val_acc = 0.7460
[MCPFirst]
E10 / 12
train_loss = 0.4344
cls = 0.1456
dom = 1.3943
hyp = 0.0496
acc = 0.9696 | val_loss = 1.0436
val_acc = 0.7381
[MCPFirst]
E11 / 12
train_loss = 0.4083
cls = 0.1198
dom = 1.3910
hyp = 0.0516
acc = 0.9760 | val_loss = 1.0781
val_acc = 0.7460
[MCPFirst]
E12 / 12
train_loss = 0.3968
cls = 0.1087
dom = 1.3902
hyp = 0.0500
acc = 0.9824 | val_loss = 1.0690
val_acc = 0.7460
[MIP]
src = 1262
train = 1010
val = 252
tgt = 1262
classes = 12
[AvgLoad]
loaded = 318
missing = 8
unexpected = 0
[MIP]
E01 / 12
train_loss = 2.2198
cls = 1.9193
dom = 1.3920
hyp = 0.1106
acc = 0.3510 | val_loss = 1.6668
val_acc = 0.4563
[MIP]
E02 / 12
train_loss = 1.6349
cls = 1.3448
dom = 1.3901
hyp = 0.0605
acc = 0.5136 | val_loss = 1.3820
val_acc = 0.5516
[MIP]
E03 / 12
train_loss = 1.4370
cls = 1.1483
dom = 1.3929
hyp = 0.0504
acc = 0.5657 | val_loss = 1.0848
val_acc = 0.5794
[MIP]
E04 / 12
train_loss = 1.2352
cls = 0.9477
dom = 1.3933
hyp = 0.0439
acc = 0.6402 | val_loss = 1.1061
val_acc = 0.6349
[MIP]
E05 / 12
train_loss = 0.9715
cls = 0.6850
dom = 1.3884
hyp = 0.0439
acc = 0.7380 | val_loss = 0.9637
val_acc = 0.6310
[MIP]
E06 / 12
train_loss = 0.9342
cls = 0.6468
dom = 1.3902
hyp = 0.0466
acc = 0.7452 | val_loss = 1.2133
val_acc = 0.6151
[MIP]
E07 / 12
train_loss = 0.7731
cls = 0.4863
dom = 1.3884
hyp = 0.0453
acc = 0.8061 | val_loss = 1.1252
val_acc = 0.6944
[MIP]
E08 / 12
train_loss = 0.6934
cls = 0.4069
dom = 1.3868
hyp = 0.0455
acc = 0.8389 | val_loss = 1.1755
val_acc = 0.7103
[MIP]
E09 / 12
train_loss = 0.5718
cls = 0.2846
dom = 1.3895
hyp = 0.0464
acc = 0.8878 | val_loss = 1.2138
val_acc = 0.6508
[MIP]
E10 / 12
train_loss = 0.5040
cls = 0.2173
dom = 1.3871
hyp = 0.0468
acc = 0.9231 | val_loss = 1.0273
val_acc = 0.7103
[MIP]
E11 / 12
train_loss = 0.4919
cls = 0.2044
dom = 1.3896
hyp = 0.0477
acc = 0.9295 | val_loss = 1.0129
val_acc = 0.7381
[MIP]
E12 / 12
train_loss = 0.4626
cls = 0.1760
dom = 1.3857
hyp = 0.0472
acc = 0.9399 | val_loss = 1.0112
val_acc = 0.7460
[Radius]
src = 633
train = 507
val = 126
tgt = 633
classes = 14
[AvgLoad]
loaded = 318
missing = 8
unexpected = 0
[Radius]
E01 / 12
train_loss = 2.4078
cls = 2.1057
dom = 1.3938
hyp = 0.1164
acc = 0.2869 | val_loss = 1.4132
val_acc = 0.5159
[Radius]
E02 / 12
train_loss = 1.5507
cls = 1.2572
dom = 1.3950
hyp = 0.0722
acc = 0.5192 | val_loss = 1.1581
val_acc = 0.4127
[Radius]
E03 / 12
train_loss = 1.2767
cls = 0.9853
dom = 1.3956
hyp = 0.0613
acc = 0.6170 | val_loss = 1.3288
val_acc = 0.5079
[Radius]
E04 / 12
train_loss = 1.0913
cls = 0.7998
dom = 1.3990
hyp = 0.0582
acc = 0.6587 | val_loss = 1.1821
val_acc = 0.5714
[Radius]
E05 / 12
train_loss = 0.9058
cls = 0.6167
dom = 1.3941
hyp = 0.0514
acc = 0.7548 | val_loss = 1.1499
val_acc = 0.5476
[Radius]
E06 / 12
train_loss = 0.8323
cls = 0.5437
dom = 1.3916
hyp = 0.0515
acc = 0.8061 | val_loss = 1.3896
val_acc = 0.5635
[Radius]
E07 / 12
train_loss = 0.6849
cls = 0.3965
dom = 1.3915
hyp = 0.0506
acc = 0.8413 | val_loss = 1.5173
val_acc = 0.5397
[Radius]
E08 / 12
train_loss = 0.5519
cls = 0.2655
dom = 1.3842
hyp = 0.0477
acc = 0.8910 | val_loss = 1.5181
val_acc = 0.5556
[Radius]
E09 / 12
train_loss = 0.5519
cls = 0.2646
dom = 1.3887
hyp = 0.0478
acc = 0.8942 | val_loss = 1.4230
val_acc = 0.5794
[Radius]
E10 / 12
train_loss = 0.4870
cls = 0.1989
dom = 1.3917
hyp = 0.0490
acc = 0.9247 | val_loss = 1.4849
val_acc = 0.5714
[Radius]
E11 / 12
train_loss = 0.4578
cls = 0.1695
dom = 1.3930
hyp = 0.0488
acc = 0.9535 | val_loss = 1.4709
val_acc = 0.5476
[Radius]
E12 / 12
train_loss = 0.4556
cls = 0.1681
dom = 1.3910
hyp = 0.0463
acc = 0.9295 | val_loss = 1.5462
val_acc = 0.5476
[Ulna]
src = 632
train = 506
val = 126
tgt = 632
classes = 12
[AvgLoad]
loaded = 318
missing = 8
unexpected = 0
[Ulna]
E01 / 12
train_loss = 2.4662
cls = 2.1604
dom = 1.3937
hyp = 0.1353
acc = 0.2869 | val_loss = 1.7392
val_acc = 0.5476
[Ulna]
E02 / 12
train_loss = 1.6814
cls = 1.3879
dom = 1.3852
hyp = 0.0823
acc = 0.5817 | val_loss = 1.2173
val_acc = 0.6111
[Ulna]
E03 / 12
train_loss = 1.4254
cls = 1.1307
dom = 1.4003
hyp = 0.0734
acc = 0.6474 | val_loss = 1.2185
val_acc = 0.6190
[Ulna]
E04 / 12
train_loss = 1.2624
cls = 0.9704
dom = 1.3922
hyp = 0.0678
acc = 0.6971 | val_loss = 1.3111
val_acc = 0.6349
[Ulna]
E05 / 12
train_loss = 1.0506
cls = 0.7599
dom = 1.3890
hyp = 0.0649
acc = 0.7821 | val_loss = 1.3298
val_acc = 0.6349
[Ulna]
E06 / 12
train_loss = 0.8457
cls = 0.5551
dom = 1.3937
hyp = 0.0590
acc = 0.8205 | val_loss = 1.4277
val_acc = 0.6587
[Ulna]
E07 / 12
train_loss = 0.7444
cls = 0.4533
dom = 1.3909
hyp = 0.0646
acc = 0.8718 | val_loss = 1.4050
val_acc = 0.6746
[Ulna]
E08 / 12
train_loss = 0.6244
cls = 0.3335
dom = 1.3935
hyp = 0.0609
acc = 0.9183 | val_loss = 1.2892
val_acc = 0.6746
[Ulna]
E09 / 12
train_loss = 0.5894
cls = 0.2983
dom = 1.3951
hyp = 0.0605
acc = 0.9231 | val_loss = 1.4211
val_acc = 0.6905
[Ulna]
E10 / 12
train_loss = 0.5037
cls = 0.2139
dom = 1.3920
hyp = 0.0570
acc = 0.9487 | val_loss = 1.3627
val_acc = 0.6825
[Ulna]
E11 / 12
train_loss = 0.4673
cls = 0.1786
dom = 1.3863
hyp = 0.0571
acc = 0.9551 | val_loss = 1.3865
val_acc = 0.7063
[Ulna]
E12 / 12
train_loss = 0.4580
cls = 0.1693
dom = 1.3853
hyp = 0.0578
acc = 0.9551 | val_loss = 1.3659
val_acc = 0.7222

== == DONE == ==
summary: / kaggle / working / rewrite_da_hyper / summary.csv
DIP: 0.7222 @ 12
DIPFirst: 0.6508 @ 12
PIP: 0.7262 @ 10
PIPFirst: 0.6905 @ 11
MCP: 0.7143 @ 10
MCPFirst: 0.7460 @ 9
MIP: 0.7460 @ 12
Radius: 0.5794 @ 9
Ulna: 0.7222 @ 12


