import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# Email Configuration
EMAIL_SMTP_SERVER = os.getenv("EMAIL_SMTP_SERVER", "smtp.gmail.com")
EMAIL_SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", "888"))
EMAIL_SENDER = os.getenv("EMAIL_SENDER", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").lower() == "true"
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "False").lower() == "true"

# Storage Configuration
PUSH_RECORDS_DIR = BASE_DIR / "push_records"
PUSH_RECORDS_DIR.mkdir(exist_ok=True)

# Default Push Template
DEFAULT_EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; background: #f9fafb; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: white; padding: 30px; border-radius: 0 0 10px 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .info-card {{ background: #eff6ff; border-left: 4px solid #3b82f6; padding: 15px; margin: 15px 0; border-radius: 4px; }}
        .label {{ font-weight: bold; color: #1e40af; }}
        .value {{ color: #1f2937; font-size: 1.1em; }}
        .remarks {{ background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 15px 0; border-radius: 4px; }}
        .footer {{ text-align: center; margin-top: 20px; font-size: 0.9em; color: #6b7280; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #e5e7eb; }}
        th {{ background: #f3f4f6; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>AI 骨龄智能评估报告</h1>
            <p>专业级深度学习辅助诊断</p>
        </div>
        <div class="content">
            <h2>诊断结果</h2>
            <div class="info-card">
                <p><span class="label">报告编号:</span> <span class="value">{report_id}</span></p>
                <p><span class="label">患者性别:</span> <span class="value">{gender}</span></p>
                <p><span class="label">预测骨龄:</span> <span class="value">{predicted_age_years} 岁 ({predicted_age_months} 月)</span></p>
                {adult_height_section}
                <p><span class="label">分析时间:</span> <span class="value">{timestamp}</span></p>
            </div>
            {remarks_section}
            <h3>影像学分析</h3>
            <div style="background: #f3f4f6; padding: 15px; border-radius: 4px;">
                <pre style="white-space: pre-wrap; margin: 0; font-family: 'Courier New', monospace; font-size: 0.9em;">{medical_report}</pre>
            </div>
            {rus_chn_section}
            <div class="footer">
                <p>本报告由 AI 系统自动生成，仅供临床参考</p>
                <p>© 2026 AI 骨龄智能评估系统</p>
            </div>
        </div>
    </div>
</body>
</html>
"""

DEFAULT_WECHAT_TEMPLATE = """
AI 骨龄评估报告

报告编号: {report_id}
患者性别: {gender}
预测骨龄: {predicted_age_years} 岁
{adult_height_line}
分析时间: {timestamp}

{remarks_section}

影像学分析
{medical_report}
"""

DEFAULT_FEISHU_TEMPLATE = DEFAULT_WECHAT_TEMPLATE
