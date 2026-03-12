import argparse
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv


def load_env() -> None:
    base_dir = Path(__file__).resolve().parent
    load_dotenv(base_dir / ".env")


def build_message(sender: str, recipient: str, subject: str, body: str) -> MIMEMultipart:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    msg.attach(MIMEText(body, "plain", "utf-8"))
    return msg


def send_email_ssl_465(msg: MIMEMultipart, sender: str, password: str, host: str, port: int) -> None:
    # Keep behavior exactly as requested: QQ SMTP via SSL on 465.
    print(f"[TRY] host={host} port={port} mode=SMTP_SSL")
    with smtplib.SMTP_SSL(host, port, timeout=20) as server:
        server.login(sender, password)
        server.send_message(msg)
    print(f"[OK] sent via {host}:{port} mode=SMTP_SSL")


def main() -> None:
    parser = argparse.ArgumentParser(description="Send test email via SMTP with multiple fallback modes.")
    parser.add_argument("--to", required=True, help="Recipient email address")
    parser.add_argument("--subject", default="BoneAge SMTP Test", help="Email subject")
    parser.add_argument("--body", default="This is a SMTP test email from BoneAge backend.", help="Email body")
    args = parser.parse_args()

    load_env()
    host = os.getenv("EMAIL_SMTP_SERVER", "smtp.qq.com")
    port = int(os.getenv("EMAIL_SMTP_PORT", "465"))
    sender = os.getenv("EMAIL_SENDER", "")
    password = os.getenv("EMAIL_PASSWORD", "")

    if not sender or not password:
        raise RuntimeError("Missing EMAIL_SENDER or EMAIL_PASSWORD in backend/.env")

    msg = build_message(sender, args.to, args.subject, args.body)
    send_email_ssl_465(msg, sender, password, host, port)


if __name__ == "__main__":
    main()
