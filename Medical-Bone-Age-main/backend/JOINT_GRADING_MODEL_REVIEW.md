# 关节分级模型审查文档

本文档用于审查 `backend/app/main.py` 中的关节分级链路实现是否与预期一致。

## 1. 审查范围

- 小关节检测：`SmallJointRecognizer`
- 关节分级：`JointGrader` + `JointClassifier`
- 缺失补全：`semantic_align_missing_joint_grades`
- 语义对齐与 RUS 打分：`align_joint_semantics`、`calc_rus_score`
- 接口集成点：`POST /predict`

## 2. 模型与文件依赖

- 检测模型：`app/models/recognize/best.pt`
- 分级模型目录：`app/models/joints`
- 分级模型命名规则：`best_<JointName>.pth`
- 当前代码声明的分级模型名：
  - `DIP`
  - `DIPFirst`
  - `PIP`
  - `PIPFirst`
  - `MCP`
  - `MCPFirst`
  - `MIP`
  - `Radius`
  - `Ulna`

## 3. 模型结构与输入输出

### 3.1 单关节分级模型（`JointClassifier`）

- Backbone：`resnet50(weights=None)`
- 分类头：`Linear(feat_dim, num_classes)`
- 输入：单关节 ROI，预处理为 `3x224x224`
- 输出：分类 logits

### 3.2 checkpoint 恢复逻辑

- 读取 `class_to_idx`（必须存在）
- 通过 `idx_to_class` 将预测 `grade_idx` 反查到 `grade_raw`
- 审查点：
  - 若 `class_to_idx` 缺失，该模型会被跳过
  - `load_state_dict(..., strict=False)`，需确认是否有不期望的 key mismatch

## 4. 推理流程（接口视角）

1. `/predict` 收到图像后，先进行小关节检测，得到 `joint_detect_13`
2. 使用检测框逐关节裁剪 ROI（`_safe_crop`，有边界扩展）
3. ROI 预处理后送入对应分级模型，输出：
   - `grade_idx`
   - `grade_raw`
   - `score`
   - `status=ok`
4. 若模型缺失或裁剪失败，写入：
   - `status=model_missing` 或 `status=crop_invalid`
5. 对缺失分级执行语义补全：
   - `status=semantic_imputed` 或 `status=semantic_default`
   - 补全时记录 `imputed`、`source_joint`
6. 做 RUS 语义对齐与总分计算，输出：
   - `joint_semantic_13`
   - `joint_rus_total_score`
   - `joint_rus_details`

## 5. 检测关节到分级模型映射（关键审查项）

- `DIPFirst -> DIPFirst`
- `DIPThird -> DIP`
- `DIPFifth -> DIP`
- `PIPFirst -> PIPFirst`
- `PIPThird -> PIP`
- `PIPFifth -> PIP`
- `MCPFirst -> MCPFirst`
- `MCPThird -> MCP`
- `MCPFifth -> MCP`
- `MIPThird -> MIP`
- `MIPFifth -> MIP`
- `Ulna -> Ulna`
- `Radius -> Radius`

说明：`Radius` 若缺 `best_Radius.pth`，会走 `model_missing`，随后可能被语义补全。

## 6. 预处理一致性审查

分级预处理参数：

- `JOINT_IMG_SIZE = 224`
- `IMAGENET_MEAN = [0.485, 0.456, 0.406]`
- `IMAGENET_STD = [0.229, 0.224, 0.225]`

流程：

- BGR -> RGB
- Resize 到 `224x224`
- `float32 / 255`
- Normalize（ImageNet）
- HWC -> CHW -> NCHW

审查结论标准：需与训练阶段保持同分布。

## 7. 输出字段审查清单

### 7.1 `joint_detect_13`

- `hand_side`
- `detected_count`
- `joints`（含 bbox 与归一化坐标）
- `plot_image_base64`

### 7.2 `joint_grades`

每个关节应包含：

- `model_joint`
- `grade_idx`
- `grade_raw`
- `score`
- `status`
- （补全场景）`imputed`、`source_joint`

### 7.3 RUS 相关

- `joint_semantic_13`
- `joint_rus_total_score`
- `joint_rus_details`

## 8. 风险与建议

- 风险1：模型文件不全（尤其 `Radius`）导致频繁补全，降低可信度。
- 风险2：检测框偏移会直接影响分级准确率。
- 风险3：`strict=False` 加载权重可能掩盖结构不匹配问题。

建议：

1. 启动日志中打印每个分级模型的 missing/unexpected keys。
2. 输出每次请求中 `model_missing` 与 `semantic_imputed` 的计数。
3. 用固定测试集对比“检测框裁剪分级”与“人工ROI分级”的一致性。

## 9. 最小验收用例

1. 正常样本：13关节全检测、全可分级，`status` 主要为 `ok`。
2. 缺模型样本：移除 `best_Radius.pth`，确认 `Radius` 先 `model_missing` 后可补全。
3. 异常框样本：制造无效 bbox，确认出现 `crop_invalid` 且流程不中断。
4. 性别切换：同一分级输入下，`joint_rus_total_score` 随性别表变化。
