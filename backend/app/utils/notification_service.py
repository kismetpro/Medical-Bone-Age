import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import requests

from app.config import (
    DEFAULT_EMAIL_TEMPLATE,
    DEFAULT_FEISHU_TEMPLATE,
    DEFAULT_WECHAT_TEMPLATE,
    PUSH_RECORDS_DIR,
)


class NotificationService:
    SMTP_SCRIPT = Path(__file__).resolve().parents[2] / "send_smtp_email.py"

    @staticmethod
    def format_report_template(
        template: str,
        report_data: Dict[str, Any],
        remarks: str = "",
        report_id: str = "",
        is_html: bool = True,
    ) -> str:
        gender_text = "男性" if report_data.get("gender") == "male" else "女性"
        predicted_age_years = report_data.get("predicted_age_years", 0)
        predicted_age_months = report_data.get("predicted_age_months", 0)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        adult_height = report_data.get("predicted_adult_height")
        if is_html:
            adult_height_section = (
                f'<p><span class="label">预测成年身高:</span> <span class="value">{adult_height} cm</span></p>'
                if adult_height
                else ""
            )
            adult_height_line = ""
        else:
            adult_height_section = ""
            adult_height_line = f"预测成年身高: {adult_height} cm" if adult_height else ""

        if is_html:
            remarks_section = (
                f"""
            <div class="remarks">
                <h3>医生备注</h3>
                <p>{remarks}</p>
            </div>
            """
                if remarks
                else ""
            )
        else:
            remarks_section = f"\n医生备注\n{remarks}\n" if remarks else ""

        medical_report = NotificationService._generate_medical_report(report_data)

        rus_chn_details = report_data.get("rus_chn_details")
        if is_html and rus_chn_details:
            rus_chn_section = (
                "<h3>骨化中心明细 (RUS-CHN)</h3>"
                "<table><thead><tr><th>ROI</th><th>等级</th><th>得分</th></tr></thead><tbody>"
            )
            for detail in rus_chn_details.get("details", []):
                rus_chn_section += (
                    f"<tr><td>{detail['name']}</td><td>{detail['stage']}</td><td>{detail['score']}</td></tr>"
                )
            rus_chn_section += (
                f"</tbody></table><p><strong>总分:</strong> {rus_chn_details.get('total_score', 0)}</p>"
            )
        else:
            rus_chn_section = ""

        return template.format(
            report_id=report_id,
            gender=gender_text,
            predicted_age_years=round(predicted_age_years, 1),
            predicted_age_months=round(predicted_age_months, 1),
            adult_height_section=adult_height_section,
            adult_height_line=adult_height_line,
            timestamp=timestamp,
            remarks_section=remarks_section,
            medical_report=medical_report,
            rus_chn_section=rus_chn_section,
        )

    @staticmethod
    def _generate_medical_report(report_data: Dict[str, Any]) -> str:
        gender = report_data.get("gender", "male")
        gender_text = "男" if gender == "male" else "女"
        predicted_age_years = report_data.get("predicted_age_years", 0)
        anomalies = report_data.get("anomalies", [])

        fractures = [a for a in anomalies if a.get("score", 0) > 0.45 and "fracture" in a.get("type", "")]
        foreign_objects = [a for a in anomalies if a.get("score", 0) > 0.45 and a.get("type") == "metal"]

        report = "【影像学分析报告】\n"
        report += f"1. 基本信息：受检者性别为{gender_text}，测定骨龄约为 {round(predicted_age_years, 1)} 岁。\n\n"
        report += "2. 影像发现：\n"

        if fractures:
            report += f"   - [警告] 在影像中识别到 {len(fractures)} 处疑似骨折区域。建议临床结合压痛点进一步核实。\n"
        else:
            report += "   - 骨骼连续性尚好，未见明显骨折征象。\n"

        if foreign_objects:
            report += f"   - 注意：影像中存在 {len(foreign_objects)} 处高密度异物，可能影响骨龄判断。\n"

        report += "\n3. 结论建议：\n"
        report += "   结论：疑似存在外伤性改变。" if fractures else "   结论：骨龄发育符合当前生理阶段。"
        return report

    @staticmethod
    async def send_email(
        recipient: str,
        report_data: Dict[str, Any],
        remarks: str = "",
        custom_template: Optional[str] = None,
        report_id: str = "",
    ) -> Dict[str, Any]:
        try:
            # Keep one source of truth: send mail via standalone SMTP script.
            if not NotificationService.SMTP_SCRIPT.exists():
                raise RuntimeError(f"SMTP script not found: {NotificationService.SMTP_SCRIPT}")

            template = custom_template if custom_template else DEFAULT_WECHAT_TEMPLATE
            text_content = NotificationService.format_report_template(
                template=template,
                report_data=report_data,
                remarks=remarks,
                report_id=report_id,
                is_html=False,
            )

            subject = f"AI 骨龄评估报告 - {report_id}"
            cmd = [
                sys.executable,
                str(NotificationService.SMTP_SCRIPT),
                "--to",
                recipient,
                "--subject",
                subject,
                "--body",
                text_content,
            ]

            completed = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if completed.returncode != 0:
                stderr = (completed.stderr or "").strip()
                stdout = (completed.stdout or "").strip()
                detail = stderr or stdout or f"exit code {completed.returncode}"
                raise RuntimeError(detail)

            NotificationService.save_push_record(
                method="email",
                recipient=recipient,
                report_data=report_data,
                remarks=remarks,
                report_id=report_id,
                status="success",
            )
            return {"success": True, "message": f"邮件已成功发送至 {recipient}"}
        except Exception as exc:
            error_msg = f"邮件发送失败: {exc}"
            NotificationService.save_push_record(
                method="email",
                recipient=recipient,
                report_data=report_data,
                remarks=remarks,
                report_id=report_id,
                status="failed",
                error=error_msg,
            )
            return {"success": False, "message": error_msg}

    @staticmethod
    async def send_wechat_webhook(
        webhook_url: str,
        report_data: Dict[str, Any],
        remarks: str = "",
        custom_template: Optional[str] = None,
        report_id: str = "",
    ) -> Dict[str, Any]:
        try:
            template = custom_template if custom_template else DEFAULT_WECHAT_TEMPLATE
            content = NotificationService.format_report_template(
                template, report_data, remarks, report_id, is_html=False
            )
            payload = {"msgtype": "markdown", "markdown": {"content": content}}
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()

            if result.get("errcode") == 0:
                NotificationService.save_push_record(
                    method="wechat",
                    recipient=webhook_url,
                    report_data=report_data,
                    remarks=remarks,
                    report_id=report_id,
                    status="success",
                )
                return {"success": True, "message": "企业微信通知发送成功"}

            error_msg = f"企业微信通知发送失败: {result.get('errmsg', 'Unknown error')}"
            NotificationService.save_push_record(
                method="wechat",
                recipient=webhook_url,
                report_data=report_data,
                remarks=remarks,
                report_id=report_id,
                status="failed",
                error=error_msg,
            )
            return {"success": False, "message": error_msg}
        except Exception as exc:
            error_msg = f"企业微信通知发送失败: {exc}"
            NotificationService.save_push_record(
                method="wechat",
                recipient=webhook_url,
                report_data=report_data,
                remarks=remarks,
                report_id=report_id,
                status="failed",
                error=error_msg,
            )
            return {"success": False, "message": error_msg}

    @staticmethod
    async def send_feishu_webhook(
        webhook_url: str,
        report_data: Dict[str, Any],
        remarks: str = "",
        custom_template: Optional[str] = None,
        report_id: str = "",
    ) -> Dict[str, Any]:
        try:
            template = custom_template if custom_template else DEFAULT_FEISHU_TEMPLATE
            content = NotificationService.format_report_template(
                template, report_data, remarks, report_id, is_html=False
            )
            payload = {"msg_type": "text", "content": {"text": content}}
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()

            if result.get("code") == 0 or result.get("StatusCode") == 0:
                NotificationService.save_push_record(
                    method="feishu",
                    recipient=webhook_url,
                    report_data=report_data,
                    remarks=remarks,
                    report_id=report_id,
                    status="success",
                )
                return {"success": True, "message": "飞书通知发送成功"}

            error_msg = f"飞书通知发送失败: {result.get('msg', 'Unknown error')}"
            NotificationService.save_push_record(
                method="feishu",
                recipient=webhook_url,
                report_data=report_data,
                remarks=remarks,
                report_id=report_id,
                status="failed",
                error=error_msg,
            )
            return {"success": False, "message": error_msg}
        except Exception as exc:
            error_msg = f"飞书通知发送失败: {exc}"
            NotificationService.save_push_record(
                method="feishu",
                recipient=webhook_url,
                report_data=report_data,
                remarks=remarks,
                report_id=report_id,
                status="failed",
                error=error_msg,
            )
            return {"success": False, "message": error_msg}

    @staticmethod
    def save_push_record(
        method: str,
        recipient: str,
        report_data: Dict[str, Any],
        remarks: str,
        report_id: str,
        status: str,
        error: str = "",
    ) -> None:
        try:
            record = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "method": method,
                "recipient": recipient,
                "report_id": report_id,
                "status": status,
                "error": error,
                "remarks": remarks,
                "report_summary": {
                    "gender": report_data.get("gender"),
                    "predicted_age_years": report_data.get("predicted_age_years"),
                    "predicted_age_months": report_data.get("predicted_age_months"),
                    "predicted_adult_height": report_data.get("predicted_adult_height"),
                },
            }

            filename = f"push_record_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{report_id}.json"
            filepath = PUSH_RECORDS_DIR / filename
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(record, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            print(f"保存推送记录失败: {exc}")
