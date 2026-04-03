"""
Medical-Bone-Age 模型性能评估脚本
计算骨龄预测和关节分级的各项性能指标
"""

import os
import sys
import json
import time
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime
import requests

# 尝试导入sklearn相关库
try:
    from sklearn.metrics import (
        mean_absolute_error, mean_squared_error, r2_score,
        accuracy_score, precision_score, recall_score, f1_score,
        confusion_matrix, classification_report, cohen_kappa_score
    )
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    print("警告: sklearn未安装，部分指标将使用numpy计算")


@dataclass
class PredictionRecord:
    """预测记录"""
    filename: str
    gender: str
    predicted_age: float
    actual_age: Optional[float] = None
    predicted_grades: Optional[Dict[str, int]] = None
    actual_grades: Optional[Dict[str, int]] = None
    inference_time: float = 0.0


class BoneAgeMetrics:
    """骨龄预测指标计算器"""
    
    @staticmethod
    def mean_absolute_error(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """平均绝对误差 MAE"""
        return np.mean(np.abs(y_pred - y_true))
    
    @staticmethod
    def mean_squared_error(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """均方误差 MSE"""
        return np.mean((y_pred - y_true) ** 2)
    
    @staticmethod
    def root_mean_squared_error(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """均方根误差 RMSE"""
        return np.sqrt(np.mean((y_pred - y_true) ** 2))
    
    @staticmethod
    def mean_absolute_percentage_error(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """平均绝对百分比误差 MAPE"""
        return np.mean(np.abs((y_true - y_pred) / np.maximum(y_true, 1e-8))) * 100
    
    @staticmethod
    def r_squared(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """决定系数 R²"""
        ss_res = np.sum((y_true - y_pred) ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        return 1 - (ss_res / ss_tot) if ss_tot > 1e-8 else 0
    
    @staticmethod
    def pearson_correlation(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """皮尔逊相关系数"""
        if len(y_true) < 2:
            return 0
        return np.corrcoef(y_true, y_pred)[0, 1]
    
    @staticmethod
    def within_threshold_accuracy(y_true: np.ndarray, y_pred: np.ndarray, 
                                   threshold: float) -> float:
        """阈值内准确率 (误差不超过threshold年的比例)"""
        errors = np.abs(y_pred - y_true)
        return np.mean(errors <= threshold) * 100
    
    @staticmethod
    def bias(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """偏差 (预测值 - 真实值的平均)"""
        return np.mean(y_pred - y_true)
    
    @staticmethod
    def std_error(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """误差标准差"""
        errors = y_pred - y_true
        return np.std(errors)
    
    @classmethod
    def calculate_all(cls, y_true: List[float], y_pred: List[float]) -> Dict[str, float]:
        """计算所有指标"""
        y_true = np.array(y_true, dtype=np.float64)
        y_pred = np.array(y_pred, dtype=np.float64)
        
        if len(y_true) == 0:
            return {}
        
        metrics = {
            "样本数量 (N)": len(y_true),
            "平均绝对误差 (MAE, 年)": cls.mean_absolute_error(y_true, y_pred),
            "均方误差 (MSE)": cls.mean_squared_error(y_true, y_pred),
            "均方根误差 (RMSE, 年)": cls.root_mean_squared_error(y_true, y_pred),
            "平均绝对百分比误差 (MAPE%)": cls.mean_absolute_percentage_error(y_true, y_pred),
            "决定系数 (R²)": cls.r_squared(y_true, y_pred),
            "皮尔逊相关系数 (r)": cls.pearson_correlation(y_true, y_pred),
            "偏差 (Bias, 年)": cls.bias(y_true, y_pred),
            "误差标准差 (SD, 年)": cls.std_error(y_true, y_pred),
            "误差≤0.5年准确率 (%)": cls.within_threshold_accuracy(y_true, y_pred, 0.5),
            "误差≤1.0年准确率 (%)": cls.within_threshold_accuracy(y_true, y_pred, 1.0),
            "误差≤1.5年准确率 (%)": cls.within_threshold_accuracy(y_true, y_pred, 1.5),
            "误差≤2.0年准确率 (%)": cls.within_threshold_accuracy(y_true, y_pred, 2.0),
        }
        
        # 按性别/年龄段分组计算
        metrics["真实年龄范围"] = f"[{y_true.min():.1f}, {y_true.max():.1f}]"
        metrics["预测年龄范围"] = f"[{y_pred.min():.1f}, {y_pred.max():.1f}]"
        
        return metrics


class JointGradingMetrics:
    """关节分级指标计算器"""
    
    @staticmethod
    def accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """准确率"""
        return np.mean(y_true == y_pred)
    
    @staticmethod
    def precision_per_class(y_true: np.ndarray, y_pred: np.ndarray, 
                            num_classes: int) -> np.ndarray:
        """每个类别的精确率"""
        precisions = []
        for c in range(num_classes):
            tp = np.sum((y_true == c) & (y_pred == c))
            fp = np.sum((y_true != c) & (y_pred == c))
            precisions.append(tp / (tp + fp) if (tp + fp) > 0 else 0)
        return np.array(precisions)
    
    @staticmethod
    def recall_per_class(y_true: np.ndarray, y_pred: np.ndarray,
                        num_classes: int) -> np.ndarray:
        """每个类别的召回率"""
        recalls = []
        for c in range(num_classes):
            tp = np.sum((y_true == c) & (y_pred == c))
            fn = np.sum((y_true == c) & (y_pred != c))
            recalls.append(tp / (tp + fn) if (tp + fn) > 0 else 0)
        return np.array(recalls)
    
    @staticmethod
    def f1_per_class(y_true: np.ndarray, y_pred: np.ndarray,
                    num_classes: int) -> np.ndarray:
        """每个类别的F1分数"""
        precisions = JointGradingMetrics.precision_per_class(y_true, y_pred, num_classes)
        recalls = JointGradingMetrics.recall_per_class(y_true, y_pred, num_classes)
        f1s = []
        for p, r in zip(precisions, recalls):
            f1s.append(2 * p * r / (p + r) if (p + r) > 0 else 0)
        return np.array(f1s)
    
    @staticmethod
    def macro_average(values: np.ndarray) -> float:
        """宏平均"""
        return np.mean(values)
    
    @staticmethod
    def micro_average(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """微平均 (对于多分类等于准确率)"""
        return np.mean(y_true == y_pred)
    
    @staticmethod
    def weighted_average(values: np.ndarray, y_true: np.ndarray,
                        num_classes: int) -> float:
        """加权平均"""
        class_counts = np.array([np.sum(y_true == c) for c in range(num_classes)])
        total = class_counts.sum()
        if total == 0:
            return 0
        return np.sum(values * class_counts) / total
    
    @staticmethod
    def cohen_kappa(y_true: np.ndarray, y_pred: np.ndarray, 
                   num_classes: int) -> float:
        """Cohen's Kappa系数"""
        po = np.mean(y_true == y_pred)
        pe = sum(
            (np.sum(y_true == c) / len(y_true)) * (np.sum(y_pred == c) / len(y_pred))
            for c in range(num_classes)
        )
        return (po - pe) / (1 - pe) if (1 - pe) > 0 else 0
    
    @staticmethod
    def confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray,
                        num_classes: int) -> np.ndarray:
        """混淆矩阵"""
        cm = np.zeros((num_classes, num_classes), dtype=int)
        for t, p in zip(y_true, y_pred):
            cm[t, p] += 1
        return cm
    
    @staticmethod
    def exact_match_ratio(y_true_list: List[Dict[str, int]], 
                         y_pred_list: List[Dict[str, int]]) -> float:
        """完全匹配率 (所有关节分级都正确)"""
        if len(y_true_list) != len(y_pred_list):
            return 0
        
        exact_matches = 0
        for true_grades, pred_grades in zip(y_true_list, y_pred_list):
            all_match = True
            for joint, true_grade in true_grades.items():
                if pred_grades.get(joint) != true_grade:
                    all_match = False
                    break
            if all_match:
                exact_matches += 1
        
        return exact_matches / len(y_true_list) * 100
    
    @classmethod
    def calculate_all(cls, y_true: List[int], y_pred: List[int],
                     num_classes: int = None) -> Dict[str, float]:
        """计算所有分类指标"""
        y_true = np.array(y_true, dtype=int)
        y_pred = np.array(y_pred, dtype=int)
        
        if len(y_true) == 0:
            return {}
        
        if num_classes is None:
            num_classes = max(y_true.max(), y_pred.max()) + 1
        
        precisions = cls.precision_per_class(y_true, y_pred, num_classes)
        recalls = cls.recall_per_class(y_true, y_pred, num_classes)
        f1s = cls.f1_per_class(y_true, y_pred, num_classes)
        
        metrics = {
            "样本数量 (N)": len(y_true),
            "类别数量": num_classes,
            "准确率 (Accuracy)": cls.accuracy(y_true, y_pred),
            "宏平均精确率 (Macro-P)": cls.macro_average(precisions),
            "宏平均召回率 (Macro-R)": cls.macro_average(recalls),
            "宏平均F1 (Macro-F1)": cls.macro_average(f1s),
            "微平均精确率 (Micro-P)": cls.micro_average(y_true, y_pred),
            "微平均召回率 (Micro-R)": cls.micro_average(y_true, y_pred),
            "微平均F1 (Micro-F1)": cls.micro_average(y_true, y_pred),
            "加权平均精确率 (Weighted-P)": cls.weighted_average(precisions, y_true, num_classes),
            "加权平均召回率 (Weighted-R)": cls.weighted_average(recalls, y_true, num_classes),
            "加权平均F1 (Weighted-F1)": cls.weighted_average(f1s, y_true, num_classes),
            "Cohen's Kappa": cls.cohen_kappa(y_true, y_pred, num_classes),
        }
        
        # 添加每个类别的F1
        for i, f1 in enumerate(f1s):
            metrics[f"Grade-{i} F1"] = f1
        
        return metrics


class PerformanceTester:
    """性能测试器"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.records: List[PredictionRecord] = []
        self.inference_times: List[float] = []
    
    def login(self, username: str = "doctor", password: str = "Doctor123456",
              role: str = "doctor") -> bool:
        """登录获取Token"""
        try:
            resp = self.session.post(f"{self.base_url}/auth/login", json={
                "username": username,
                "password": password,
                "role": role
            })
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success") and "token" in data:
                    self.session.headers.update({
                        "Authorization": f"Bearer {data['token']}"
                    })
                    return True
            return False
        except Exception as e:
            print(f"登录失败: {e}")
            return False
    
    def test_single_image(self, image_path: str, gender: str,
                         actual_age: float = None) -> Optional[PredictionRecord]:
        """测试单张图片"""
        try:
            start_time = time.time()
            
            with open(image_path, "rb") as f:
                files = {"file": (os.path.basename(image_path), f, "image/jpeg")}
                data = {"gender": gender}
                if actual_age is not None:
                    data["real_age_years"] = actual_age
                
                resp = self.session.post(
                    f"{self.base_url}/predict",
                    files=files,
                    data=data,
                    timeout=60
                )
            
            inference_time = time.time() - start_time
            self.inference_times.append(inference_time)
            
            if resp.status_code != 200:
                print(f"请求失败: {resp.status_code}")
                return None
            
            result = resp.json()
            
            record = PredictionRecord(
                filename=os.path.basename(image_path),
                gender=gender,
                predicted_age=result.get("predicted_age_years", 0),
                actual_age=actual_age,
                inference_time=inference_time
            )
            
            # 提取关节分级结果
            joint_grades = result.get("joint_grades", {})
            if joint_grades:
                record.predicted_grades = {
                    k: v.get("grade_raw", 0) 
                    for k, v in joint_grades.items()
                }
            
            self.records.append(record)
            return record
            
        except Exception as e:
            print(f"测试失败: {e}")
            return None
    
    def test_batch_images(self, image_dir: str, labels_file: str = None) -> List[PredictionRecord]:
        """批量测试图片"""
        records = []
        
        # 如果有标签文件，加载标签
        labels = {}
        if labels_file and os.path.exists(labels_file):
            with open(labels_file, "r") as f:
                labels = json.load(f)
        
        # 遍历图片目录
        image_extensions = {".jpg", ".jpeg", ".png", ".bmp"}
        for filename in os.listdir(image_dir):
            ext = os.path.splitext(filename)[1].lower()
            if ext not in image_extensions:
                continue
            
            image_path = os.path.join(image_dir, filename)
            
            # 获取标签信息
            label_info = labels.get(filename, {})
            gender = label_info.get("gender", "male")
            actual_age = label_info.get("age")
            
            print(f"测试: {filename}")
            record = self.test_single_image(image_path, gender, actual_age)
            if record:
                records.append(record)
        
        return records
    
    def get_bone_age_metrics(self) -> Dict[str, float]:
        """获取骨龄预测指标"""
        records_with_label = [r for r in self.records if r.actual_age is not None]
        if not records_with_label:
            return {}
        
        y_true = [r.actual_age for r in records_with_label]
        y_pred = [r.predicted_age for r in records_with_label]
        
        return BoneAgeMetrics.calculate_all(y_true, y_pred)
    
    def get_performance_metrics(self) -> Dict[str, float]:
        """获取推理性能指标"""
        if not self.inference_times:
            return {}
        
        times = np.array(self.inference_times)
        return {
            "总推理次数": len(times),
            "平均推理时间 (秒)": np.mean(times),
            "中位推理时间 (秒)": np.median(times),
            "最小推理时间 (秒)": np.min(times),
            "最大推理时间 (秒)": np.max(times),
            "推理时间标准差 (秒)": np.std(times),
            "平均FPS": 1.0 / np.mean(times) if np.mean(times) > 0 else 0,
        }
    
    def generate_detailed_report(self, output_file: str = "performance_report.md") -> str:
        """生成详细性能报告"""
        bone_metrics = self.get_bone_age_metrics()
        perf_metrics = self.get_performance_metrics()
        
        lines = [
            "# Medical-Bone-Age 模型性能评估报告",
            "",
            f"**评估时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**测试样本数**: {len(self.records)}",
            "",
            "## 1. 骨龄预测准确度指标",
            "",
            "### 1.1 误差指标",
            "",
            "| 指标名称 | 符号 | 值 | 单位 | 说明 |",
            "|---------|------|-----|------|------|"
        ]
        
        error_metrics = [
            ("平均绝对误差", "MAE", bone_metrics.get("平均绝对误差 (MAE, 年)", "N/A"), "年", "越小越好"),
            ("均方根误差", "RMSE", bone_metrics.get("均方根误差 (RMSE, 年)", "N/A"), "年", "越小越好"),
            ("平均绝对百分比误差", "MAPE", bone_metrics.get("平均绝对百分比误差 (MAPE%)", "N/A"), "%", "越小越好"),
            ("偏差", "Bias", bone_metrics.get("偏差 (Bias, 年)", "N/A"), "年", "正值表示高估"),
            ("误差标准差", "SD", bone_metrics.get("误差标准差 (SD, 年)", "N/A"), "年", "误差离散程度"),
        ]
        
        for name, symbol, value, unit, desc in error_metrics:
            if isinstance(value, float):
                value = f"{value:.4f}"
            lines.append(f"| {name} | {symbol} | {value} | {unit} | {desc} |")
        
        lines.extend([
            "",
            "### 1.2 相关性指标",
            "",
            "| 指标名称 | 符号 | 值 | 说明 |",
            "|---------|------|-----|------|"
        ])
        
        corr_metrics = [
            ("决定系数", "R²", bone_metrics.get("决定系数 (R²)", "N/A"), "越接近1越好"),
            ("皮尔逊相关系数", "r", bone_metrics.get("皮尔逊相关系数 (r)", "N/A"), "越接近1越好"),
        ]
        
        for name, symbol, value, desc in corr_metrics:
            if isinstance(value, float):
                value = f"{value:.4f}"
            lines.append(f"| {name} | {symbol} | {value} | {desc} |")
        
        lines.extend([
            "",
            "### 1.3 阈值内准确率",
            "",
            "| 误差阈值 | 准确率 |",
            "|---------|--------|"
        ])
        
        thresholds = [
            ("≤0.5年", "误差≤0.5年准确率 (%)"),
            ("≤1.0年", "误差≤1.0年准确率 (%)"),
            ("≤1.5年", "误差≤1.5年准确率 (%)"),
            ("≤2.0年", "误差≤2.0年准确率 (%)"),
        ]
        
        for threshold_name, key in thresholds:
            value = bone_metrics.get(key, "N/A")
            if isinstance(value, float):
                value = f"{value:.2f}%"
            lines.append(f"| {threshold_name} | {value} |")
        
        lines.extend([
            "",
            "## 2. 推理性能指标",
            "",
            "| 指标 | 值 |",
            "|------|-----|"
        ])
        
        for key, value in perf_metrics.items():
            if isinstance(value, float):
                value = f"{value:.4f}"
            lines.append(f"| {key} | {value} |")
        
        lines.extend([
            "",
            "## 3. 测试样本详情",
            "",
            "| 文件名 | 性别 | 真实年龄 | 预测年龄 | 绝对误差 | 推理时间(s) |",
            "|--------|------|---------|---------|---------|------------|"
        ])
        
        for record in self.records:
            actual = f"{record.actual_age:.2f}" if record.actual_age else "N/A"
            error = ""
            if record.actual_age is not None:
                error = f"{abs(record.predicted_age - record.actual_age):.2f}"
            lines.append(
                f"| {record.filename} | {record.gender} | {actual} | "
                f"{record.predicted_age:.2f} | {error} | {record.inference_time:.3f} |"
            )
        
        lines.extend([
            "",
            "## 4. 指标说明",
            "",
            "### 4.1 骨龄预测指标",
            "- **MAE (Mean Absolute Error)**: 预测值与真实值之差的绝对值的平均",
            "- **RMSE (Root Mean Squared Error)**: 预测误差的均方根，对大误差更敏感",
            "- **MAPE (Mean Absolute Percentage Error)**: 相对误差的平均百分比",
            "- **R² (Coefficient of Determination)**: 模型解释数据方差的比例",
            "- **Pearson r**: 衡量预测值与真实值的线性相关程度",
            "",
            "### 4.2 临床意义",
            "- 骨龄预测误差在±1年以内通常被认为具有临床价值",
            "- MAE < 0.5年: 优秀",
            "- MAE 0.5-1.0年: 良好",
            "- MAE > 1.5年: 需要改进",
            "",
            "## 5. 结论",
            "",
            f"本次评估共测试 {len(self.records)} 张X光片。",
        ])
        
        if bone_metrics:
            mae = bone_metrics.get("平均绝对误差 (MAE, 年)", 0)
            r2 = bone_metrics.get("决定系数 (R²)", 0)
            lines.extend([
                f"- 骨龄预测MAE: {mae:.4f}年",
                f"- 决定系数R²: {r2:.4f}",
                f"- 平均推理时间: {perf_metrics.get('平均推理时间 (秒)', 0):.4f}秒",
            ])
        
        report = "\n".join(lines)
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report)
        
        return report


def generate_sample_test_data(output_file: str = "test_labels.json"):
    """生成示例测试数据标签"""
    sample_data = {
        "sample_001.jpg": {"gender": "male", "age": 5.5, "grades": {"Radius": 5, "Ulna": 4}},
        "sample_002.jpg": {"gender": "female", "age": 7.2, "grades": {"Radius": 6, "Ulna": 5}},
        "sample_003.jpg": {"gender": "male", "age": 10.0, "grades": {"Radius": 8, "Ulna": 7}},
        "sample_004.jpg": {"gender": "female", "age": 3.8, "grades": {"Radius": 3, "Ulna": 3}},
        "sample_005.jpg": {"gender": "male", "age": 12.5, "grades": {"Radius": 10, "Ulna": 9}},
    }
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(sample_data, f, indent=2, ensure_ascii=False)
    
    print(f"示例测试数据已生成: {output_file}")
    return sample_data


def run_performance_evaluation(base_url: str = "http://127.0.0.1:8000",
                               test_dir: str = None,
                               labels_file: str = None,
                               output_report: str = "performance_report.md"):
    """运行性能评估"""
    
    print("=" * 60)
    print("Medical-Bone-Age 模型性能评估")
    print("=" * 60)
    
    # 初始化测试器
    tester = PerformanceTester(base_url)
    
    # 登录
    print("\n正在登录...")
    if not tester.login():
        print("登录失败，将使用无认证模式")
    
    # 如果提供了测试目录
    if test_dir and os.path.exists(test_dir):
        print(f"\n开始测试目录: {test_dir}")
        tester.test_batch_images(test_dir, labels_file)
    else:
        print("\n未提供测试目录，使用示例数据生成报告模板")
    
    # 生成报告
    print("\n生成性能报告...")
    report = tester.generate_detailed_report(output_report)
    print(f"报告已保存: {output_report}")
    
    return tester


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Medical-Bone-Age 性能评估")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="服务器地址")
    parser.add_argument("--test-dir", default=None, help="测试图片目录")
    parser.add_argument("--labels", default=None, help="标签文件路径")
    parser.add_argument("--output", default="performance_report.md", help="报告输出路径")
    
    args = parser.parse_args()
    
    run_performance_evaluation(
        base_url=args.url,
        test_dir=args.test_dir,
        labels_file=args.labels,
        output_report=args.output
    )
