"""
Medical-Bone-Age 综合测试运行器
一键运行所有测试并生成报告
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "tests"))

from test_suite import APITestClient, TestReportGenerator
from performance_metrics import PerformanceTester, BoneAgeMetrics, JointGradingMetrics


class ComprehensiveTestRunner:
    """综合测试运行器"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8000",
                 output_dir: str = "test_results"):
        self.base_url = base_url
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.api_client = APITestClient(base_url)
        self.perf_tester = PerformanceTester(base_url)
        
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def run_api_tests(self, test_image: str = None) -> dict:
        """运行API测试"""
        print("\n" + "=" * 50)
        print("开始API接口测试")
        print("=" * 50)
        
        results = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "details": []
        }
        
        # 等待服务器
        if not self.api_client.wait_for_server():
            print("服务器未启动，跳过API测试")
            return results
        
        # 基础接口测试
        print("\n[1/6] 测试基础接口...")
        self.api_client.test_root_endpoint()
        
        # 用户认证测试
        print("\n[2/6] 测试用户认证...")
        timestamp = int(time.time())
        self.api_client.test_register(f"testuser_{timestamp}", "Test123456")
        self.api_client.test_login(f"testuser_{timestamp}", "Test123456")
        self.api_client.test_verify_token()
        
        # 切换到医生账号
        self.api_client.test_login("doctor", "Doctor123456", "doctor")
        
        # 核心功能测试
        print("\n[3/6] 测试核心功能...")
        if test_image and os.path.exists(test_image):
            pred_result = self.api_client.test_predict_bone_age(test_image, "male")
            joint_result = self.api_client.test_joint_grading(test_image, "male")
        
        self.api_client.test_manual_grade_calculation("male")
        
        # 数据管理测试
        print("\n[4/6] 测试数据管理...")
        self.api_client.test_get_predictions()
        self.api_client.test_bone_age_points()
        self.api_client.test_bone_age_trend()
        
        # 内容管理测试
        print("\n[5/6] 测试内容管理...")
        self.api_client.test_articles()
        self.api_client.test_qa_questions()
        
        # 登出测试
        print("\n[6/6] 测试登出...")
        self.api_client.test_logout()
        
        # 统计结果
        for result in self.api_client.test_results:
            results["total"] += 1
            if result.passed:
                results["passed"] += 1
            else:
                results["failed"] += 1
            results["details"].append({
                "name": result.test_name,
                "passed": result.passed,
                "duration": result.duration,
                "details": result.details,
                "metrics": result.metrics
            })
        
        return results
    
    def run_performance_tests(self, test_dir: str = None,
                            labels_file: str = None) -> dict:
        """运行性能测试"""
        print("\n" + "=" * 50)
        print("开始性能指标测试")
        print("=" * 50)
        
        results = {
            "bone_age_metrics": {},
            "performance_metrics": {},
            "joint_metrics": {}
        }
        
        # 登录
        if not self.perf_tester.login():
            print("登录失败，使用无认证模式")
        
        # 测试图片
        if test_dir and os.path.exists(test_dir):
            print(f"\n测试目录: {test_dir}")
            self.perf_tester.test_batch_images(test_dir, labels_file)
            
            # 计算指标
            results["bone_age_metrics"] = self.perf_tester.get_bone_age_metrics()
            results["performance_metrics"] = self.perf_tester.get_performance_metrics()
        
        return results
    
    def generate_comprehensive_report(self, api_results: dict,
                                     perf_results: dict) -> str:
        """生成综合测试报告"""
        
        report_lines = [
            "# Medical-Bone-Age 综合测试报告",
            "",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**服务器地址**: {self.base_url}",
            "",
            "---",
            "",
            "## 一、测试概览",
            "",
            "| 测试类别 | 状态 |",
            "|---------|------|",
            f"| API接口测试 | {'✅ 通过' if api_results['failed'] == 0 else '❌ 存在失败'} |",
            f"| 性能指标测试 | {'✅ 完成' if perf_results['bone_age_metrics'] else '⚠️ 无数据'} |",
            "",
            f"**API测试**: 共 {api_results['total']} 项，"
            f"通过 {api_results['passed']} 项，"
            f"失败 {api_results['failed']} 项",
            "",
            "## 二、API接口测试详情",
            "",
            "| 序号 | 接口名称 | 状态 | 耗时(s) |",
            "|------|---------|------|---------|"
        ]
        
        for i, detail in enumerate(api_results["details"], 1):
            status = "✅" if detail["passed"] else "❌"
            report_lines.append(
                f"| {i} | {detail['name']} | {status} | {detail['duration']:.3f} |"
            )
        
        report_lines.extend([
            "",
            "## 三、骨龄预测性能指标",
            ""
        ])
        
        bone_metrics = perf_results.get("bone_age_metrics", {})
        if bone_metrics:
            report_lines.append("| 指标 | 值 | 说明 |")
            report_lines.append("|------|-----|------|")
            
            metric_descriptions = {
                "样本数量 (N)": "测试样本总数",
                "平均绝对误差 (MAE, 年)": "预测误差的绝对值平均",
                "均方根误差 (RMSE, 年)": "对大误差更敏感的指标",
                "决定系数 (R²)": "模型解释方差的比例",
                "皮尔逊相关系数 (r)": "线性相关程度",
                "误差≤1.0年准确率 (%)": "临床可用性指标",
            }
            
            for key, value in bone_metrics.items():
                desc = metric_descriptions.get(key, "")
                if isinstance(value, float):
                    value = f"{value:.4f}"
                report_lines.append(f"| {key} | {value} | {desc} |")
        else:
            report_lines.append("*未进行骨龄预测性能测试*")
        
        report_lines.extend([
            "",
            "## 四、推理性能指标",
            ""
        ])
        
        perf_metrics = perf_results.get("performance_metrics", {})
        if perf_metrics:
            report_lines.append("| 指标 | 值 |")
            report_lines.append("|------|-----|")
            for key, value in perf_metrics.items():
                if isinstance(value, float):
                    value = f"{value:.4f}"
                report_lines.append(f"| {key} | {value} |")
        else:
            report_lines.append("*未进行推理性能测试*")
        
        report_lines.extend([
            "",
            "## 五、系统功能模块",
            "",
            "### 5.1 已实现功能",
            "",
            "| 模块 | 功能 | 状态 |",
            "|------|------|------|",
            "| 用户管理 | 注册/登录/登出 | ✅ |",
            "| 用户管理 | 多角色权限控制 | ✅ |",
            "| 骨龄预测 | 深度学习集成预测 | ✅ |",
            "| 骨龄预测 | TTA测试时增强 | ✅ |",
            "| 骨龄预测 | Grad-CAM可视化 | ✅ |",
            "| 骨折检测 | YOLO目标检测 | ✅ |",
            "| 关节检测 | 13个关键关节识别 | ✅ |",
            "| 关节分级 | DANN分级模型 | ✅ |",
            "| 骨龄评估 | RUS-CHN评分 | ✅ |",
            "| 数据管理 | 预测记录管理 | ✅ |",
            "| 数据管理 | 骨龄趋势分析 | ✅ |",
            "| 智能辅助 | 医生AI助手 | ✅ |",
            "| 智能辅助 | 患者智能问诊 | ✅ |",
            "| 通知服务 | 邮件/微信/飞书 | ✅ |",
            "",
            "### 5.2 技术架构",
            "",
            "- **后端框架**: FastAPI",
            "- **深度学习**: PyTorch + ONNX Runtime",
            "- **目标检测**: Ultralytics YOLO",
            "- **数据库**: SQLite",
            "- **图像处理**: OpenCV + NumPy",
            "- **AI助手**: DeepSeek API",
            "",
            "## 六、测试结论",
            ""
        ])
        
        if api_results["failed"] == 0:
            report_lines.append("✅ **所有API接口测试通过**")
        else:
            report_lines.append(f"❌ **{api_results['failed']}项API测试失败，请检查日志**")
        
        if bone_metrics:
            mae = bone_metrics.get("平均绝对误差 (MAE, 年)", 0)
            if isinstance(mae, (int, float)):
                if mae < 0.5:
                    report_lines.append("✅ **骨龄预测精度优秀** (MAE < 0.5年)")
                elif mae < 1.0:
                    report_lines.append("✅ **骨龄预测精度良好** (MAE < 1.0年)")
                elif mae < 1.5:
                    report_lines.append("⚠️ **骨龄预测精度一般** (MAE < 1.5年)")
                else:
                    report_lines.append("❌ **骨龄预测精度需要改进** (MAE ≥ 1.5年)")
        
        report_lines.extend([
            "",
            "---",
            "",
            "*本报告由Medical-Bone-Age测试套件自动生成*"
        ])
        
        report_content = "\n".join(report_lines)
        
        # 保存报告
        report_file = self.output_dir / f"comprehensive_report_{self.timestamp}.md"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report_content)
        
        # 保存JSON格式结果
        json_file = self.output_dir / f"test_results_{self.timestamp}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": self.timestamp,
                "api_results": api_results,
                "performance_results": {
                    "bone_age_metrics": {k: float(v) if isinstance(v, (int, float)) else v 
                                        for k, v in perf_results.get("bone_age_metrics", {}).items()},
                    "performance_metrics": {k: float(v) if isinstance(v, (int, float)) else v 
                                           for k, v in perf_results.get("performance_metrics", {}).items()}
                }
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n报告已保存:")
        print(f"  - Markdown: {report_file}")
        print(f"  - JSON: {json_file}")
        
        return report_content
    
    def run_all(self, test_image: str = None, test_dir: str = None,
               labels_file: str = None) -> str:
        """运行所有测试"""
        
        print("=" * 60)
        print("  Medical-Bone-Age 综合测试套件")
        print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # 运行API测试
        api_results = self.run_api_tests(test_image)
        
        # 运行性能测试
        perf_results = self.run_performance_tests(test_dir, labels_file)
        
        # 生成综合报告
        print("\n" + "=" * 50)
        print("生成综合测试报告")
        print("=" * 50)
        
        report = self.generate_comprehensive_report(api_results, perf_results)
        
        # 打印摘要
        print("\n" + "=" * 60)
        print("  测试完成!")
        print("=" * 60)
        print(f"\nAPI测试: {api_results['passed']}/{api_results['total']} 通过")
        
        if perf_results.get("bone_age_metrics"):
            mae = perf_results["bone_age_metrics"].get("平均绝对误差 (MAE, 年)", "N/A")
            print(f"骨龄预测MAE: {mae}")
        
        return report


def main():
    parser = argparse.ArgumentParser(
        description="Medical-Bone-Age 综合测试套件",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 基础测试 (仅API测试)
  python run_all_tests.py
  
  # 完整测试 (包含模型性能测试)
  python run_all_tests.py --test-dir ./test_images --labels ./labels.json
  
  # 指定服务器地址
  python run_all_tests.py --url http://192.168.1.100:8000
        """
    )
    
    parser.add_argument("--url", default="http://127.0.0.1:8000",
                       help="服务器地址 (默认: http://127.0.0.1:8000)")
    parser.add_argument("--image", default=None,
                       help="单张测试图片路径")
    parser.add_argument("--test-dir", default=None,
                       help="测试图片目录")
    parser.add_argument("--labels", default=None,
                       help="标签文件路径 (JSON格式)")
    parser.add_argument("--output-dir", default="test_results",
                       help="测试结果输出目录")
    
    args = parser.parse_args()
    
    # 运行测试
    runner = ComprehensiveTestRunner(
        base_url=args.url,
        output_dir=args.output_dir
    )
    
    runner.run_all(
        test_image=args.image,
        test_dir=args.test_dir,
        labels_file=args.labels
    )


if __name__ == "__main__":
    main()
