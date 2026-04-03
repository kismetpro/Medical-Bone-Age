"""
13轮优化测试框架
每个测试轮的参数配置
"""

import os
from dataclasses import dataclass
from typing import Optional, Tuple, List


@dataclass
class OptimizationRound:
    """优化轮次配置"""
    round_num: int
    name: str
    description: str
    
    # 灰度阈值参数
    bone_low: int = 70
    bone_high: int = 180
    
    # 二分法参数
    target_regions: int = 12
    tolerance: int = 4
    max_iterations: int = 15
    
    # 形态学参数
    morph_kernel_small: int = 3
    morph_kernel_medium: int = 5
    morph_close_iter: int = 2
    morph_open_iter: int = 1
    
    # 面积过滤
    min_area_ratio: float = 0.001  # 占图像面积的最小比例
    max_area_ratio: float = 0.5    # 占图像面积的最大比例
    
    # 扫描参数
    scan_step: int = 15
    
    # YOLOv8参数
    use_yolo: bool = True
    yolo_conf: float = 0.5


# 13轮优化配置
OPTIMIZATION_ROUNDS = [
    OptimizationRound(
        round_num=1,
        name="基线版本",
        description="初始参数设置",
        bone_low=70, bone_high=180,
        target_regions=12, tolerance=4,
        morph_kernel_small=3, morph_kernel_medium=5,
        morph_close_iter=2, morph_open_iter=1
    ),
    OptimizationRound(
        round_num=2,
        name="缩小灰度范围",
        description="收紧骨骼灰度区间，排除结缔组织",
        bone_low=90, bone_high=150,
        target_regions=14, tolerance=3,
        morph_kernel_small=3, morph_kernel_medium=5,
        morph_close_iter=2, morph_open_iter=1
    ),
    OptimizationRound(
        round_num=3,
        name="放宽灰度范围",
        description="扩大骨骼灰度区间，捕获更多骨骼",
        bone_low=60, bone_high=190,
        target_regions=16, tolerance=4,
        morph_kernel_small=3, morph_kernel_medium=5,
        morph_close_iter=2, morph_open_iter=1
    ),
    OptimizationRound(
        round_num=4,
        name="加强形态学处理",
        description="增加闭运算迭代次数，填充更多孔洞",
        bone_low=80, bone_high=170,
        target_regions=13, tolerance=3,
        morph_kernel_small=3, morph_kernel_medium=7,
        morph_close_iter=4, morph_open_iter=2
    ),
    OptimizationRound(
        round_num=5,
        name="减弱形态学处理",
        description="减少形态学处理，保留更多细节",
        bone_low=80, bone_high=170,
        target_regions=15, tolerance=4,
        morph_kernel_small=2, morph_kernel_medium=3,
        morph_close_iter=1, morph_open_iter=1
    ),
    OptimizationRound(
        round_num=6,
        name="提高目标区域数",
        description="期望检测更多小关节",
        bone_low=75, bone_high=175,
        target_regions=18, tolerance=5,
        morph_kernel_small=3, morph_kernel_medium=5,
        morph_close_iter=2, morph_open_iter=1
    ),
    OptimizationRound(
        round_num=7,
        name="降低目标区域数",
        description="期望检测更少但更准确的大关节",
        bone_low=85, bone_high=165,
        target_regions=10, tolerance=3,
        morph_kernel_small=3, morph_kernel_medium=5,
        morph_close_iter=3, morph_open_iter=2
    ),
    OptimizationRound(
        round_num=8,
        name="精细扫描",
        description="减小扫描步长，提高扫描精度",
        bone_low=80, bone_high=170,
        target_regions=13, tolerance=3,
        morph_kernel_small=3, morph_kernel_medium=5,
        morph_close_iter=2, morph_open_iter=1,
        scan_step=10
    ),
    OptimizationRound(
        round_num=9,
        name="粗略扫描",
        description="增大扫描步长，加快处理速度",
        bone_low=80, bone_high=170,
        target_regions=13, tolerance=4,
        morph_kernel_small=3, morph_kernel_medium=5,
        morph_close_iter=2, morph_open_iter=1,
        scan_step=20
    ),
    OptimizationRound(
        round_num=10,
        name="宽松面积过滤",
        description="减小最小面积阈值，捕获更多小关节",
        bone_low=80, bone_high=170,
        target_regions=14, tolerance=4,
        morph_kernel_small=3, morph_kernel_medium=5,
        morph_close_iter=2, morph_open_iter=1,
        min_area_ratio=0.0005
    ),
    OptimizationRound(
        round_num=11,
        name="严格面积过滤",
        description="增大最小面积阈值，过滤噪声",
        bone_low=80, bone_high=170,
        target_regions=12, tolerance=3,
        morph_kernel_small=3, morph_kernel_medium=5,
        morph_close_iter=2, morph_open_iter=1,
        min_area_ratio=0.002
    ),
    OptimizationRound(
        round_num=12,
        name="提高YOLOv8置信度",
        description="使用更高的YOLOv8置信度阈值",
        bone_low=80, bone_high=170,
        target_regions=13, tolerance=3,
        morph_kernel_small=3, morph_kernel_medium=5,
        morph_close_iter=2, morph_open_iter=1,
        yolo_conf=0.7
    ),
    OptimizationRound(
        round_num=13,
        name="综合优化",
        description="平衡各项参数，寻找最佳配置",
        bone_low=82, bone_high=168,
        target_regions=13, tolerance=3,
        morph_kernel_small=3, morph_kernel_medium=5,
        morph_close_iter=2, morph_open_iter=1,
        scan_step=12,
        min_area_ratio=0.0015
    ),
]


def get_round_config(round_num: int) -> OptimizationRound:
    """获取指定轮次的配置"""
    for config in OPTIMIZATION_ROUNDS:
        if config.round_num == round_num:
            return config
    return OPTIMIZATION_ROUNDS[0]


def print_round_summary(round_num: int):
    """打印指定轮次的优化总结"""
    config = get_round_config(round_num)
    print(f"""
第{round_num}轮优化: {config.name}
{'='*60}
描述: {config.description}

参数配置:
  灰度阈值: [{config.bone_low}, {config.bone_high}]
  目标区域数: {config.target_regions} (±{config.tolerance})
  形态学核: 小={config.morph_kernel_small}, 中={config.morph_kernel_medium}
  形态学迭代: 闭={config.morph_close_iter}, 开={config.morph_open_iter}
  扫描步长: {config.scan_step}°
  YOLOv8置信度: {config.yolo_conf}
  面积过滤: [{config.min_area_ratio*100:.2f}%, {config.max_area_ratio*100:.1f}%]
""")
