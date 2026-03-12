# 小关节检测 + 分级流程说明

本文档说明 `backend/app/main.py` 中“小关节识别 + 关节分级 + RUS 对齐”的完整代码流程。

## 1. 模型来源与对应关系

- 检测模型：`app/models/recognize/best.pt`
- 分级模型目录：`app/models/joints`

当前分级权重文件：
- `best_DIP.pth`
- `best_DIPFirst.pth`
- `best_PIP.pth`
- `best_PIPFirst.pth`
- `best_MCP.pth`
- `best_MCPFirst.pth`
- `best_MIP.pth`
- `best_Ulna.pth`

检测到的 13 个目标点与分级模型映射：

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
- `Radius -> Radius`（若无 `best_Radius.pth`，返回 `model_missing`）

## 2. 推理主流程（/predict）

1. 接收上传影像与性别参数。  
2. `SmallJointRecognizer.recognize_13` 用 YOLO 检测并输出：
   - `joint_detect_13.joints`（13点 bbox）
   - `joint_detect_13.hand_side`
   - `joint_detect_13.plot_image_base64`（plt 可视化图）
3. `JointGrader.predict_detected_joints` 对每个检测框执行：
   - 按 bbox 裁剪 ROI（带少量外扩）
   - 统一到 `224x224`
   - 按训练脚本同分布预处理：ImageNet mean/std
   - 使用对应 `best_*.pth` 做分类分级
4. 输出 `joint_grades`（每个关节的等级、置信度、状态）。
5. `align_joint_semantics` + `calc_rus_score` 做 RUS 13点语义对齐和总分计算。
6. 同时返回骨龄主模型结果、异常检测结果、热力图等字段。

## 3. 关键实现点（与训练过程对齐）

参考 `参考关节分级的训练过程.py`：

- Backbone：ResNet50
- 预处理：`Resize -> ToTensor -> Normalize([0.485,0.456,0.406], [0.229,0.224,0.225])`
- checkpoint 含 `class_to_idx`，推理时反查原始等级号

线上推理已对齐上述规范：
- 输入通道为 RGB
- 归一化与训练一致
- 输出 `grade_raw` 作为原始分级号

## 4. 返回字段说明（新增/重点）

- `joint_detect_13`
  - `hand_side`
  - `detected_count`
  - `joints`（每个点 bbox/coord）
  - `plot_image_base64`（可直接前端 `<img src=...>` 显示）
- `joint_grades`
  - key 为 13点名称（如 `MCPThird`）
  - value:
    - `model_joint`：实际调用的模型名
    - `grade_idx`：连续索引
    - `grade_raw`：原始等级号
    - `score`：softmax 置信度
    - `status`：`ok | model_missing | crop_invalid`

## 5. 注意事项

- 当前目录缺少 `best_Radius.pth`，`Radius` 节点会返回 `model_missing`。  
- 若后续补充 `best_Radius.pth`，无需改代码即可自动生效。  
- 若检测框质量较差，`status` 可能出现 `crop_invalid`。建议优先优化检测模型质量与阈值。
