# 小关节识别系统架构图

## 整体架构

```mermaid
graph TB
    subgraph INPUT["📥 输入层"]
        A1["📷 手部X光图像<br/>原始尺寸 W×H"]
        A2["🔄 图像预处理<br/>Resize 1024×1024"]
    end
    
    subgraph DETECTION["🔍 检测层"]
        B1["🤖 YOLOv8检测器<br/>best.pt模型<br/>21类骨骼检测"]
        B2["🖼️ YOLO遮罩生成<br/>排除已检测区域"]
        B3["🔵 BFS洪水填充<br/>灰度聚类分块"]
        B4["🔗 Union-Find去重<br/>合并重叠区域"]
        B5["📊 DP灰度扩展<br/>目标23个骨骼"]
    end
    
    subgraph HYBRID["🔀 混合检测层"]
        C1["🎯 YOLO检测结果<br/>21个骨骼"]
        C2["💧 FloodFill补充<br/>剩余腕骨检测"]
        C3["🔀 结果融合<br/>YOLO + CV"]
    end
    
    subgraph POST["🔧 后处理层"]
        D1["🖐️ 手性判断<br/>尺骨/桡骨位置关系"]
        D2["📍 13点精准映射<br/>手指骨骼分配"]
        D3["🏷️ 骨骼类别映射<br/>→分级模型标签"]
    end
    
    subgraph OUTPUT["📤 输出层"]
        E1["✅ 13/21个骨骼点<br/>位置+类别+置信度"]
        E2["🖐️ 手性判定<br/>left/right"]
        E3["📊 检测可视化图像<br/>标注框+标签"]
    end
    
    A1 --> A2
    A2 --> B1
    B1 --> C1
    B1 --> B2
    B2 --> B3
    B3 --> B4
    B4 --> B5
    B5 --> C2
    C1 --> C3
    C2 --> C3
    C3 --> D1
    C3 --> D2
    D2 --> D3
    D1 --> E1
    D2 --> E1
    D3 --> E2
    D3 --> E3
```

## YOLO检测模块详解

```mermaid
graph LR
    subgraph YOLO_INPUT["输入"]
        Y1["1024×1024图像"]
    end
    
    subgraph YOLO_CORE["YOLOv8核心"]
        Y2["CSPDarknet骨干网络"]
        Y3["PANet特征金字塔"]
        Y4["检测头输出"]
    end
    
    subgraph YOLO_OUTPUT["输出"]
        Y5["边界框 xyxy"]
        Y6["类别置信度"]
        Y7["类别ID"]
    end
    
    Y1 --> Y2 --> Y3 --> Y4
    Y4 --> Y5
    Y4 --> Y6
    Y4 --> Y7
```

## 骨骼类别与检测目标

```mermaid
graph TB
    subgraph HAND["🖐️ 手部骨骼结构"]
        subgraph WRIST["📍 腕部 2点"]
            W1["<b>桡骨 Radius</b><br/>检测: 1"]
            W2["<b>尺骨 Ulna</b><br/>检测: 1"]
        end
        
        subgraph THUMB["👆 拇指 3点"]
            T1["MCPFirst<br/>掌指关节"]
            T2["PIPFirst<br/>近节指骨"]
            T3["DIPFirst<br/>远节指骨"]
        end
        
        subgraph FINGER_2_5["👉 2-5指 各4点"]
            F1["MCP<br/>掌指关节"]
            F2["PIP<br/>近节指骨"]
            F3["MIP<br/>中节指骨"]
            F4["DIP<br/>远节指骨"]
        end
    end
    
    W1 --- W2
    T1 --> T2 --> T3
    F1 --> F2 --> F3 --> F4
```

## DP V3灰度扩展算法流程

```mermaid
flowchart TD
    START["�开始"] --> STEP1["Step 1: YOLO检测"]
    STEP1 --> STEP2["Step 2: 创建YOLO遮罩"]
    STEP2 --> STEP3["Step 3: BFS聚类分块"]
    STEP3 --> STEP4["Step 4: Union-Find去重"]
    STEP4 --> STEP5["Step 5: 学习初始灰度范围"]
    STEP5 --> STEP6{"Step 6: DP灰度扩展"}
    STEP6 --> STEP7{"骨骼数量<br/>≥ 目标23?"}
    STEP7 -- 是 --> STEP8["使用当前灰度范围"]
    STEP7 -- 否 --> STEP9["扩大灰度范围"]
    STEP9 --> STEP6
    STEP8 --> STEP10["Step 7: 检测腕骨"]
    STEP10 --> STEP11["Step 8: 合并YOLO+BFS"]
    STEP11 --> END["✅ 输出23个骨骼"]
```

## 手性判断逻辑

```mermaid
flowchart TD
    H1["输入骨骼检测结果"] --> H2{"是否有<br/>Radius和Ulna?"}
    H2 -- 否 --> H3["返回: unknown"]
    H2 -- 是 --> H4["获取Radius中心X坐标"]
    H4 --> H5["获取Ulna中心X坐标"]
    H5 --> H6{"Ulna.X < Radius.X?"}
    
    H6 -- 是 --> H7["左手影像<br/>标准PA位"]
    H7 --> H8["return 'left'"]
    
    H6 -- 否 --> H9["右手影像<br/>标准PA位"]
    H9 --> H10["return 'right'"]
    
    H3 --> END_H["手性判断完成"]
    H8 --> END_H
    H10 --> END_H
```

## 13点手指分配算法

```mermaid
flowchart LR
    subgraph INPUT_13["输入检测结果"]
        I1["21个YOLO骨骼"]
        I2["手性: left/right"]
    end
    
    subgraph SORT["全局排序"]
        S1["按X坐标排序每类骨骼"]
        S2{"手性?"}
        S3["左手: 从右到左"]
        S4["右手: 从左到右"]
    end
    
    subgraph ASSIGN["手指分配"]
        A1["索引0 → First拇指"]
        A2["索引2 → Third中指"]
        A3["索引4 → Fifth小指"]
    end
    
    subgraph OUTPUT_13["输出13点"]
        O1["DIPFirst/PIPFirst/MCPFirst"]
        O2["DIPThird/PIPThird/MCPThird"]
        O3["DIPFifth/PIPFifth/MCPFifth"]
        O4["MIPThird/MIPFifth"]
        O5["Radius/Ulna"]
    end
    
    I1 --> S1
    I2 --> S2
    S1 --> S2
    S2 --> S3
    S2 --> S4
    S3 --> A1
    S4 --> A1
    A1 --> A2 --> A3
    A1 --> O1
    A2 --> O2
    A3 --> O3
    A2 --> O4
    A3 --> O4
    I1 --> O5
```

## 完整处理流程

```mermaid
sequenceDiagram
    participant User as 用户
    participant API as API接口
    participant Pre as 预处理
    participant YOLO as YOLO检测器
    participant DPV3 as DP V3增强
    participant Map as 13点映射
    participant Out as 输出结果
    
    User->>API: 上传X光图像 + 性别
    API->>Pre: 图像预处理
    Pre->>YOLO: 1024×1024图像
    YOLO-->>DPV3: 21个骨骼 + 遮罩
    DPV3-->>Map: 补充腕骨
    Map->>Map: 手性判断
    Map->>Map: 手指分配
    Map->>Out: 13点结果
    Out-->>User: 可视化 + 分级数据
```

## 性能指标

| 指标 | 数值 |
|------|------|
| mAP50 | 0.994 |
| mAP50-95 | 0.734 |
| 检测类别数 | 7类 |
| 目标骨骼数 | 13/21/23 |
| 单图处理时间 | ~10ms |
