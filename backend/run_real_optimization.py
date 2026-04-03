"""
13轮真实优化测试 - 调用实际的ScanningRotationDyeingDetector
"""

import cv2
import numpy as np
import os
import time
from datetime import datetime
from pathlib import Path

from traditional_cv_joint_detector import ScanningRotationDyeingDetector
from optimization_framework import OPTIMIZATION_ROUNDS, get_round_config


def run_real_optimization_round(round_num: int, 
                                image_path: str,
                                output_dir: str) -> dict:
    """
    执行单轮真实优化测试
    """
    config = get_round_config(round_num)
    
    print(f"\n{'='*70}")
    print(f"第{round_num}轮优化测试: {config.name}")
    print(f"{'='*70}")
    print(f"描述: {config.description}")
    print(f"\n参数配置:")
    print(f"  灰度阈值: [{config.bone_low}, {config.bone_high}]")
    print(f"  目标区域数: {config.target_regions} (±{config.tolerance})")
    print(f"  形态学核: {config.morph_kernel_small}/{config.morph_kernel_medium}")
    print(f"  扫描步长: {config.scan_step}°")
    
    # 读取图像
    image = cv2.imread(image_path)
    if image is None:
        print(f"❌ 无法读取图像: {image_path}")
        return {'success': False, 'error': '图像读取失败'}
    
    print(f"\n图像尺寸: {image.shape}")
    
    # 创建输出子目录
    round_dir = os.path.join(output_dir, f"round_{round_num:02d}_{config.name}")
    os.makedirs(round_dir, exist_ok=True)
    
    # 创建检测器（使用当前轮次的参数）
    # 注意：这里我们直接修改detector的私有参数
    detector = ScanningRotationDyeingDetector(
        min_area=100,
        max_area=100000,
        scan_step=config.scan_step,
        use_yolo_for_hand_side=config.use_yolo,
        yolo_conf=config.yolo_conf
    )
    
    # 直接调用检测（使用默认的二分法）
    start_time = time.time()
    results = detector.detect_joints(image, hand_side=None)
    processing_time = time.time() - start_time
    
    print(f"\n检测结果:")
    print(f"  成功: {results['success']}")
    print(f"  手性: {results.get('hand_side', 'unknown')}")
    print(f"  区域数: {results.get('total_regions', 0)}")
    print(f"  染色区域数: {results.get('染色区域数', 0)}")
    print(f"  处理时间: {processing_time:.3f}秒")
    
    if results['success']:
        print(f"\n检测到的关节:")
        for i, region in enumerate(results['regions'][:10], 1):
            print(f"  {i}. {region['label']:15s} 位置:{region['centroid']} 面积:{region['area']:.0f}")
    
    # 可视化
    vis_path = os.path.join(round_dir, f"result_{Path(image_path).stem}_round{round_num}.jpg")
    detector.visualize(image, results, vis_path, round_num)
    
    # 生成测试报告
    report_path = os.path.join(round_dir, f"test_report_round{round_num}.md")
    generate_real_test_report(image_path, results, config, round_dir, round_num, processing_time)
    
    print(f"\n✅ 第{round_num}轮优化完成")
    print(f"   结果图片: {vis_path}")
    print(f"   测试报告: {report_path}")
    
    return {
        'success': results['success'],
        'round_num': round_num,
        'config': config,
        'results': results,
        'output_dir': round_dir,
        'vis_path': vis_path,
        'report_path': report_path,
        'processing_time': processing_time
    }


def generate_real_test_report(image_path: str, 
                            results: dict,
                            config,
                            output_dir: str,
                            round_num: int,
                            processing_time: float) -> None:
    """生成真实测试报告"""
    
    report_content = f"""# 第{round_num}轮优化测试报告

## 测试信息
- **测试日期**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **测试轮次**: 第{round_num}轮
- **优化名称**: {config.name}
- **描述**: {config.description}
- **测试图像**: {Path(image_path).name}

## 参数配置

### 灰度阈值参数
- **下界**: {config.bone_low}
- **上界**: {config.bone_high}

### 二分法参数
- **目标区域数**: {config.target_regions}
- **容差**: ±{config.tolerance}
- **最大迭代次数**: {config.max_iterations}

### 形态学处理
- **小核尺寸**: {config.morph_kernel_small}×{config.morph_kernel_small}
- **中核尺寸**: {config.morph_kernel_medium}×{config.morph_kernel_medium}
- **闭运算迭代**: {config.morph_close_iter}
- **开运算迭代**: {config.morph_open_iter}

### 扫描参数
- **扫描步长**: {config.scan_step}°

### YOLOv8参数
- **启用**: {'是' if config.use_yolo else '否'}
- **置信度阈值**: {config.yolo_conf}

### 面积过滤
- **最小面积比例**: {config.min_area_ratio * 100:.3f}%
- **最大面积比例**: {config.max_area_ratio * 100:.1f}%

## 测试结果

### 检测结果
- **成功**: {'是' if results.get('success') else '否'}
- **手性**: {results.get('hand_side', 'unknown')}
- **检测到区域数**: {results.get('total_regions', 0)}
- **染色区域数**: {results.get('染色区域数', 0)}
- **处理时间**: {processing_time:.3f}秒

### 检测到的关节
"""
    
    if results.get('success') and results.get('regions'):
        for i, region in enumerate(results['regions'], 1):
            report_content += f"""
#### {i}. {region['label']}
- **质心**: {region['centroid']}
- **边界框**: {region['bbox']}
- **面积**: {region['area']:.0f} 像素
- **长宽比**: {region['aspect_ratio']:.2f}
- **圆形度**: {region['circularity']:.3f}
- **扫描顺序**: {region['order']}
"""
    else:
        report_content += "\n未检测到有效关节\n"
    
    # 分析部分
    detected = results.get('total_regions', 0)
    target = config.target_regions
    diff = detected - target
    
    report_content += f"""
## 分析

### 本轮优化重点
{get_optimization_focus(round_num)}

### 实际效果
"""
    
    if results.get('success'):
        if abs(diff) <= config.tolerance:
            report_content += f"✅ 检测到{detected}个区域，在目标范围±{config.tolerance}内，效果良好\n"
        else:
            report_content += f"⚠️ 检测到{detected}个区域，与目标{target}相差{abs(diff)}，"
            if diff > 0:
                report_content += "建议提高灰度阈值下限\n"
            else:
                report_content += "建议降低灰度阈值下限\n"
    else:
        report_content += f"❌ 检测失败: {results.get('error', '未知错误')}\n"
    
    # 建议
    report_content += f"""
## 建议

"""
    if diff > config.tolerance:
        report_content += "建议下一轮提高灰度阈值下限，排除更多结缔组织\n"
    elif diff < -config.tolerance:
        report_content += "建议下一轮降低灰度阈值下限，包含更多骨骼区域\n"
    else:
        report_content += "当前参数配置良好，可作为参考基准\n"
    
    report_content += f"""
---
**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    report_path = os.path.join(output_dir, f"test_report_round{round_num}.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f"已生成测试报告: {report_path}")


def get_optimization_focus(round_num: int) -> str:
    """获取优化重点"""
    focuses = {
        1: "基线版本，建立基准性能",
        2: "收紧灰度范围，减少结缔组织误识别",
        3: "扩大灰度范围，捕获更多骨骼",
        4: "加强形态学处理，填充孔洞",
        5: "减弱形态学处理，保留细节",
        6: "提高目标区域数，捕获小关节",
        7: "降低目标区域数，聚焦大关节",
        8: "精细扫描，提高精度",
        9: "粗略扫描，提高速度",
        10: "宽松面积过滤，捕获小目标",
        11: "严格面积过滤，过滤噪声",
        12: "提高YOLOv8置信度，减少误检",
        13: "综合平衡各项参数"
    }
    return focuses.get(round_num, "未定义")


def run_all_real_optimization(image_paths: list, output_base: str):
    """运行所有13轮真实优化测试"""
    print("\n" + "="*70)
    print("开始13轮真实优化测试")
    print("="*70)
    
    all_results = []
    
    for round_num in range(1, 14):
        for img_path in image_paths:
            if not os.path.exists(img_path):
                print(f"⚠️ 图像不存在: {img_path}")
                continue
            
            result = run_real_optimization_round(round_num, img_path, output_base)
            all_results.append(result)
            time.sleep(0.5)  # 避免输出过快
    
    # 生成总结报告
    generate_real_summary_report(all_results, output_base)
    
    print("\n" + "="*70)
    print("✅ 所有13轮真实优化测试完成！")
    print("="*70)
    print(f"结果保存在: {output_base}")


def generate_real_summary_report(all_results: list, output_dir: str):
    """生成真实优化总结报告"""
    
    summary = f"""# 13轮真实优化测试总结报告

## 测试概述
- **测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **总测试轮次**: 13
- **成功轮次**: {sum(1 for r in all_results if r.get('success'))}
- **失败轮次**: {sum(1 for r in all_results if not r.get('success'))}

## 各轮测试结果

| 轮次 | 名称 | 检测数量 | 目标数量 | 差异 | 状态 |
|------|------|----------|----------|------|------|
"""
    
    for result in all_results:
        if result.get('success'):
            config = result.get('config')
            results = result.get('results', {})
            detected = results.get('total_regions', 0)
            target = config.target_regions if config else 0
            diff = detected - target
            status = "✅" if abs(diff) <= (config.tolerance if config else 3) else "⚠️"
            
            summary += f"| {result['round_num']:2d} | {config.name if config else 'N/A':12s} | {detected:6d} | {target:6d} | {diff:+5d} | {status} |\n"
        else:
            summary += f"| {result['round_num']:2d} | 失败 | - | - | - | ❌ |\n"
    
    # 最佳配置
    best_rounds = []
    for result in all_results:
        if result.get('success'):
            config = result.get('config')
            results = result.get('results', {})
            detected = results.get('total_regions', 0)
            target = config.target_regions if config else 0
            diff = abs(detected - target)
            best_rounds.append((diff, result['round_num'], config, detected, result['processing_time']))
    
    best_rounds.sort()
    
    summary += """
## 最佳配置建议

根据测试结果，推荐以下配置：

"""
    
    for diff, round_num, config, detected, proc_time in best_rounds[:5]:
        if config:
            summary += f"""
### 第{round_num}轮: {config.name}
- **检测数量**: {detected}
- **与目标差异**: {diff}
- **灰度阈值**: [{config.bone_low}, {config.bone_high}]
- **目标区域数**: {config.target_regions}
- **形态学核**: {config.morph_kernel_small}/{config.morph_kernel_medium}
- **处理时间**: {proc_time:.3f}秒
"""
    
    summary += """
## 关键发现

"""
    
    # 分析关键参数影响
    param_effects = analyze_parameter_effects(all_results)
    for effect in param_effects:
        summary += f"- {effect}\n"
    
    summary += """
## 下一步建议

1. 基于最佳轮次参数进行微调
2. 针对不同类型图像自适应调整参数
3. 结合深度学习进一步提升准确率
4. 增加更多测试样本验证泛化能力

---
**报告生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
""".format(datetime=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    summary_path = os.path.join(output_dir, "real_optimization_summary_report.md")
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(summary)
    
    print(f"\n✅ 已生成优化总结报告: {summary_path}")


def analyze_parameter_effects(all_results: list) -> list:
    """分析参数影响"""
    effects = []
    
    # 按灰度范围分组
    low_threshold_groups = {}
    for result in all_results:
        if result.get('success'):
            config = result.get('config')
            detected = result.get('results', {}).get('total_regions', 0)
            
            if config.bone_low not in low_threshold_groups:
                low_threshold_groups[config.bone_low] = []
            low_threshold_groups[config.bone_low].append(detected)
    
    effects.append("**灰度阈值下限影响**:")
    for low, detects in sorted(low_threshold_groups.items()):
        avg_detects = sum(detects) / len(detects) if detects else 0
        effects.append(f"  - 下界={low}: 平均检测{avg_detects:.1f}个区域")
    
    return effects


if __name__ == "__main__":
    # 测试图像路径
    test_images = [
        "check_this_image.jpg",
        "../frontend/src/static/AI_logo.jpg"
    ]
    
    # 输出目录
    output_base = os.path.join(
        os.path.dirname(__file__), 
        "optimization_results", 
        "real_tests"
    )
    os.makedirs(output_base, exist_ok=True)
    
    # 运行所有轮次
    run_all_real_optimization(test_images, output_base)
