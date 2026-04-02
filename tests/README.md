# Medical-Bone-Age 测试套件

本测试套件为Medical-Bone-Age医疗骨龄识别与管理系统提供全面的测试支持，适用于中国全国计算机设计大赛的开发文档。

## 目录结构

```
tests/
├── test_suite.py           # API接口测试套件
├── performance_metrics.py  # 模型性能指标计算
├── run_all_tests.py        # 综合测试运行器
├── sample_labels.json      # 示例测试数据标签
├── requirements.txt        # 测试依赖
└── README.md              # 本文件
```

## 快速开始

### 1. 安装依赖

```bash
cd tests
pip install -r requirements.txt
```

### 2. 启动后端服务

确保后端服务已启动:

```bash
cd backend
python entry_point.py
```

### 3. 运行测试

#### 基础API测试

```bash
python run_all_tests.py
```

#### 完整测试 (包含性能指标)

```bash
python run_all_tests.py --test-dir ./test_images --labels ./sample_labels.json
```

#### 指定服务器地址

```bash
python run_all_tests.py --url http://192.168.1.100:8000
```

## 测试内容

### 一、API接口测试

| 测试类别 | 测试项目 |
|---------|---------|
| 基础接口 | 根路径访问 |
| 用户认证 | 注册、登录、登出、Token验证 |
| 核心功能 | 骨龄预测、关节分级、手动分级计算 |
| 数据管理 | 预测记录、骨龄数据点、骨龄趋势 |
| 内容管理 | 文章列表、问答系统 |

### 二、性能指标测试

#### 2.1 骨龄预测指标

| 指标 | 说明 |
|------|------|
| MAE | 平均绝对误差 |
| RMSE | 均方根误差 |
| MAPE | 平均绝对百分比误差 |
| R² | 决定系数 |
| Pearson r | 皮尔逊相关系数 |
| 阈值准确率 | 误差在0.5/1.0/1.5/2.0年内的比例 |

#### 2.2 关节分级指标

| 指标 | 说明 |
|------|------|
| Accuracy | 准确率 |
| Precision | 精确率 (宏/微/加权平均) |
| Recall | 召回率 (宏/微/加权平均) |
| F1-Score | F1分数 (宏/微/加权平均) |
| Cohen's Kappa | 一致性系数 |

#### 2.3 推理性能指标

| 指标 | 说明 |
|------|------|
| 平均推理时间 | 单张图片推理耗时 |
| FPS | 每秒处理帧数 |
| 推理时间分布 | 最小/最大/标准差 |

## 测试报告

测试完成后会在`test_results`目录生成:

- `comprehensive_report_*.md` - Markdown格式报告
- `test_results_*.json` - JSON格式原始数据

## 命令行参数

```
--url         服务器地址 (默认: http://127.0.0.1:8000)
--image       单张测试图片路径
--test-dir    测试图片目录
--labels      标签文件路径 (JSON格式)
--output-dir  测试结果输出目录 (默认: test_results)
```

## 标签文件格式

```json
{
  "image_filename.jpg": {
    "gender": "male",
    "age": 5.5,
    "grades": {
      "Radius": 5,
      "Ulna": 4,
      ...
    }
  }
}
```

## 评分标准参考

| 指标 | 优秀 | 良好 | 一般 | 需改进 |
|------|------|------|------|--------|
| MAE | <0.5年 | <1.0年 | <1.5年 | ≥1.5年 |
| R² | >0.9 | >0.8 | >0.7 | ≤0.7 |
| 准确率 | >90% | >80% | >70% | ≤70% |

## 注意事项

1. 确保后端服务已正确启动
2. 测试图片需要是有效的X光片格式
3. 标签文件中的图片名需要与实际文件名一致
4. 首次测试建议使用小批量数据验证环境

## 联系方式

如有问题，请提交Issue至项目仓库。
