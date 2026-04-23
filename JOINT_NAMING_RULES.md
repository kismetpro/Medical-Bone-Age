# 小关节命名规则详解

## 一、命名体系概述

小关节识别系统采用两级命名体系，从YOLO检测到分级模型需要经过两次名称转换：

```
YOLO原始类别 → 手指分配后名称 → 分级模型标签
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DistalPhalanx  →  DIPFirst/DIPThird/DIPFifth  →  DIPFirst / DIP
ProximalPhalanx →  PIPFirst/PIPThird/PIPFifth  →  PIPFirst / PIP
MiddlePhalanx   →  MIPThird/MIPFifth           →  MIP
MCP             →  MCPFirst/MCPThird/MCPFifth  →  MCPFirst / MCP
Radius          →  Radius                       →  Radius
Ulna            →  Ulna                         →  Ulna
```

## 二、YOLO检测原始类别（7类）

| 英文名称 | 中文含义 | 骨骼结构 | 检测数量 |
|---------|---------|----------|----------|
| DistalPhalanx | 远节指骨 | 指尖部分的骨骼 | 5个（每指1个） |
| ProximalPhalanx | 近节指骨 | 靠近掌部的指骨 | 5个（每指1个） |
| MiddlePhalanx | 中节指骨 | 位于中间的手指骨骼 | 4个（拇指除外） |
| MCP | 掌指关节 | 掌骨与指骨连接处 | 4个（拇指除外） |
| MCPFirst | 拇指掌指关节 | 拇指的特殊掌指关节 | 1个 |
| Radius | 桡骨 | 前臂外侧骨骼 | 1个 |
| Ulna | 尺骨 | 前臂内侧骨骼 | 1个 |

### 解剖学示意

```
    远节指骨 (DistalPhalanx)
           ↑
    中节指骨 (MiddlePhalanx)     ← 拇指没有中节指骨
           ↑
    近节指骨 (ProximalPhalanx)
           ↑
    掌指关节 (MCP)
           ↑
      [掌骨区域]
```

## 三、手指编号规则

手指编号采用 **X坐标空间排序** 方法：

```
左手X光片（从右到左排序）:
    拇指(First)   食指  中指(Third)  环指  小指(Fifth)
       ↓          ↓       ↓          ↓       ↓
      X=大       X=中    X=小       X=更小  X=最小
    [X坐标值最大]                    [X坐标值最小]

右手X光片（从左到右排序）:
    小指(Fifth)  环指  中指(Third)  食指  拇指(First)
       ↓          ↓       ↓          ↓       ↓
      X=小       X=中    X=大       X=更大  X=最大
    [X坐标值最小]                    [X坐标值最大]
```

### 手性判断逻辑

```python
# 判断依据：桡骨和尺骨的相对位置
if ulna_x < radius_x:      # 尺骨在左，桡骨在右 → 左手
    is_left = True
    sort_direction = False  # 从右到左
else:                       # 桡骨在左，尺骨在右 → 右手
    is_left = False
    sort_direction = True  # 从左到右
```

## 四、13点命名映射规则

### 4.1 腕部骨骼（2点）

| 原始YOLO名称 | 映射后名称 | 中文含义 | 说明 |
|-------------|-----------|---------|------|
| Radius | Radius | 桡骨 | 位置固定，不参与手指分配 |
| Ulna | Ulna | 尺骨 | 位置固定，不参与手指分配 |

### 4.2 掌指关节（4点）

| YOLO类别 | 手指 | 映射后名称 | 中文含义 | 分级模型 |
|---------|------|-----------|---------|---------|
| MCPFirst | - | MCPFirst | 拇指掌指关节 | MCPFirst.pth |
| MCP | 食指(索引0) | MCPSecond | 食指掌指关节 | MCP.pth |
| MCP | 中指(索引1) | MCPThird | 中指掌指关节 | MCP.pth |
| MCP | 环指(索引2) | MCPFourth | 环指掌指关节 | MCP.pth |
| MCP | 小指(索引3) | MCPFifth | 小指掌指关节 | MCP.pth |

### 4.3 近节指骨 → PIP（4点）

| YOLO类别 | 手指 | 映射后名称 | 中文含义 | 分级模型 |
|---------|------|-----------|---------|---------|
| ProximalPhalanx | 拇指(索引0) | PIPFirst | 拇指近节指骨 | PIPFirst.pth |
| ProximalPhalanx | 食指(索引1) | PIPSecond | 食指近节指骨 | PIP.pth |
| ProximalPhalanx | 中指(索引2) | PIPThird | 中指近节指骨 | PIP.pth |
| ProximalPhalanx | 环指(索引3) | PIPFourth | 环指近节指骨 | PIP.pth |
| ProximalPhalanx | 小指(索引4) | PIPFifth | 小指近节指骨 | PIP.pth |

### 4.4 中节指骨 → MIP（3点）

| YOLO类别 | 手指 | 映射后名称 | 中文含义 | 分级模型 |
|---------|------|-----------|---------|---------|
| MiddlePhalanx | 拇指 | ❌ 不存在 | 拇指没有中节指骨 | - |
| MiddlePhalanx | 食指(索引0) | MIPSecond | 食指中节指骨 | MIP.pth |
| MiddlePhalanx | 中指(索引1) | MIPThird | 中指中节指骨 | MIP.pth |
| MiddlePhalanx | 环指(索引2) | MIPFourth | 环指中节指骨 | MIP.pth |
| MiddlePhalanx | 小指(索引3) | MIPFifth | 小指中节指骨 | MIP.pth |

**注意**：中节指骨索引从1开始（跳过拇指），因为拇指没有MIP。

### 4.5 远节指骨 → DIP（5点）

| YOLO类别 | 手指 | 映射后名称 | 中文含义 | 分级模型 |
|---------|------|-----------|---------|---------|
| DistalPhalanx | 拇指(索引0) | DIPFirst | 拇指远节指骨 | DIPFirst.pth |
| DistalPhalanx | 食指(索引1) | DIPSecond | 食指远节指骨 | DIP.pth |
| DistalPhalanx | 中指(索引2) | DIPThird | 中指远节指骨 | DIP.pth |
| DistalPhalanx | 环指(索引3) | DIPFourth | 环指远节指骨 | DIP.pth |
| DistalPhalanx | 小指(索引4) | DIPFifth | 小指远节指骨 | DIP.pth |

## 五、完整命名映射表

### 5.1 YOLO → 13点映射

| YOLO原始名称 | 目标数量 | 映射后名称模式 | 示例 |
|-------------|---------|--------------|------|
| Radius | 1 | Radius | Radius |
| Ulna | 1 | Ulna | Ulna |
| MCPFirst | 1 | MCPFirst | MCPFirst |
| MCP | 4 | MCP{Second/Third/Fourth/Fifth} | MCPThird |
| ProximalPhalanx | 5 | PIP{First/Second/Third/Fourth/Fifth} | PIPThird |
| MiddlePhalanx | 4 | MIP{Second/Third/Fourth/Fifth} | MIPThird |
| DistalPhalanx | 5 | DIP{First/Second/Third/Fourth/Fifth} | DIPFifth |

### 5.2 手指分配算法

```python
def map_finger_logic(yolo_lbl, target_prefix, finger_indices=[0, 2, 4],
                     target_suffixes=['First', 'Third', 'Fifth']):
    """
    核心命名分配逻辑
    
    参数:
        yolo_lbl: YOLO检测的原始类别名
        target_prefix: 目标名称前缀 (如 PIP, DIP, MIP, MCP)
        finger_indices: 要分配的索引 [0, 2, 4] 表示拇指、中指、小指
        target_suffixes: 对应的后缀 ['First', 'Third', 'Fifth']
    """
    # 1. 筛选出该类别的所有检测结果
    subset = [d for d in all_d if d['lbl'] == yolo_lbl]
    
    # 2. 根据手性确定排序方向
    # 左手: 从右到左 (reverse=False)
    # 右手: 从左到右 (reverse=True)
    subset = sorted(subset, key=lambda x: x['cx'], reverse=not is_left)
    
    # 3. 按索引分配手指
    for idx, suffix in zip(finger_indices, target_suffixes):
        if len(subset) > idx:
            final_13[f"{target_prefix}{suffix}"] = subset[idx]
```

### 5.3 实际应用示例

假设YOLO检测到5个远节指骨（DistalPhalanx），左手影像：

```
输入: 5个 DistalPhalanx 检测结果
      ↓
排序后（左手从右到左）:
  索引0: x=350  → 分配给 First (拇指)
  索引1: x=300  → 分配给 Third (中指)
  索引2: x=250  → 分配给 Fifth (小指)
  索引3: x=200  → 不使用（只映射13点）
  索引4: x=150  → 不使用
      ↓
输出:
  DIPFirst  (拇指远节指骨)
  DIPThird (中指远节指骨)
  DIPFifth (小指远节指骨)
```

## 六、命名缩写对照

| 完整缩写 | 英文全称 | 中文含义 |
|---------|---------|---------|
| DIP | Distal Interphalangeal | 远端指间关节/远节指骨 |
| PIP | Proximal Interphalangeal | 近端指间关节/近节指骨 |
| MIP | Middle Interphalangeal | 中节指骨 |
| MCP | Metacarpophalangeal | 掌指关节 |
| CMC | Carpometacarpal | 腕掌关节 |

### 解剖学位置示意

```
指端 → DIP → PIP → MCP → 掌骨 → CMC → 腕骨
  ↑     ↑     ↑     ↑
远节  近节  中节  掌指关节
```

## 七、命名与分级模型对应

| 13点名称 | 分级模型 | 专用/通用 |
|---------|---------|----------|
| DIPFirst | best_DIPFirst.pth | 专用 |
| DIPThird | best_DIP.pth | 通用 |
| DIPFifth | best_DIP.pth | 通用 |
| PIPFirst | best_PIPFirst.pth | 专用 |
| PIPThird | best_PIP.pth | 通用 |
| PIPFifth | best_PIP.pth | 通用 |
| MIPThird | best_MIP.pth | 通用 |
| MIPFifth | best_MIP.pth | 通用 |
| MCPFirst | best_MCPFirst.pth | 专用 |
| MCPThird | best_MCP.pth | 通用 |
| MCPFifth | best_MCP.pth | 通用 |
| Radius | best_Radius.pth | 专用 |
| Ulna | best_Ulna.pth | 专用 |

## 八、命名规则总结

### 三层命名架构

1. **YOLO原始名称**（7类）
   - 用于目标检测输出
   - 基于骨骼解剖学分类

2. **手指分配名称**（21类）
   - 用于13点标准定位
   - 格式：`{骨骼类型}{手指}`
   - 手指编号基于X坐标空间排序

3. **分级模型标签**（9个模型）
   - 用于骨骼成熟度分级
   - 拇指使用专用模型
   - 其他手指使用通用模型

### 命名流程图

```
YOLO检测输出
    ↓
筛选特定类别骨骼 (如 DistalPhalanx)
    ↓
按X坐标排序（根据手性确定方向）
    ↓
按索引分配手指 (0→First, 2→Third, 4→Fifth)
    ↓
拼接命名 (DIP + First = DIPFirst)
    ↓
映射到分级模型 (DIPFirst → DIPFirst.pth)
```
