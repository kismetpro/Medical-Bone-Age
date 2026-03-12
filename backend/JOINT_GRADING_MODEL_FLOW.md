# 关节分级模型流程

## 1. 目标

将手部 X 光中的 13 个关键关节（RUS 相关）进行自动分级，并生成可用于 RUS 评分的结构化结果。

---

## 2. 输入与输出

### 输入
- 原始手部 X 光图像（`file`）
- 性别（`male` / `female`）

### 输出（核心）
- `joint_detect_13`：13 个关节检测结果（bbox、手性、可视化图）
- `joint_grades`：每个关节的分级结果
- `joint_semantic_13`：语义对齐后的 13 关节分级
- `joint_rus_total_score` / `joint_rus_details`：RUS 总分与明细

---

## 3. 模型组成

1. 小关节检测模型  
- 路径：`app/models/recognize/best.pt`  
- 作用：检测关节位置并构建 13 关节语义点位。

2. 单关节分级模型（ResNet50）  
- 路径：`app/models/joints/best_*.pth`  
- 每个模型负责一个关节类别（如 `MCP`、`DIPFirst`）。
- checkpoint 含 `class_to_idx`，用于恢复 `grade_raw`。

---

## 4. 推理流程

1. 图像进入 `/predict`。  
2. 用检测模型输出 13 关节点（含 `bbox_xyxy`）。  
3. 对每个关节点：
- 按 bbox 裁剪 ROI（带少量边界扩展）
- 预处理：`RGB -> Resize(224x224) -> Normalize(ImageNet mean/std)`
- 送入对应分级模型，得到 `grade_idx / grade_raw / score`

4. 若关节无对应模型或裁剪失败：
- 记录 `status = model_missing / crop_invalid`
- 后续进入语义补全

5. 语义补全（`semantic_align_missing_joint_grades`）：
- 按 `FALLBACKS` 用相邻语义关节补全缺失等级
- 记录 `imputed=true`、`source_joint`
- 若仍无可用来源，使用保守默认等级（`semantic_default`）

6. 语义对齐（`align_joint_semantics`）：
- 将分级结果统一映射到 RUS 13 点语义空间

7. RUS 打分（`calc_rus_score`）：
- 按性别使用对应 `SCORE_TABLE`
- 输出总分与关节级明细

---

## 5. 关节映射规则（检测点 -> 分级模型）

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
- `Radius -> Radius`（缺模型时进入语义补全）

---

## 6. 关键状态说明（joint_grades.status）

- `ok`：正常分级完成
- `model_missing`：该关节无可用模型文件
- `crop_invalid`：裁剪区域无效
- `semantic_imputed`：由语义近邻补全
- `semantic_default`：无近邻可补，使用默认等级

---

## 7. 训练对齐说明

分级推理预处理与训练脚本保持一致：
- `Resize`
- `ToTensor`
- `Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])`

这保证线上推理分布与训练分布一致，降低偏移风险。
