"""Utility helper functions"""
import os
import uuid
import random
import asyncio
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta

from database import db

logger = logging.getLogger(__name__)


def _get_email_config():
    """Lazy-load Gmail SMTP config"""
    return {
        "email": os.environ.get('SENDER_EMAIL', 'info@kaimeralearning.com'),
        "password": os.environ.get('GMAIL_APP_PASSWORD', '')
    }


async def generate_teacher_code():
    """Auto-generate unique teacher ID like KL-T0001"""
    await db.counters.update_one(
        {"counter_id": "teacher_code"},
        {"$inc": {"seq": 1}},
        upsert=True
    )
    doc = await db.counters.find_one({"counter_id": "teacher_code"}, {"_id": 0})
    return f"KL-T{doc['seq']:04d}"


async def generate_student_code():
    """Auto-generate unique student ID like KL-S0001"""
    await db.counters.update_one(
        {"counter_id": "student_code"},
        {"$inc": {"seq": 1}},
        upsert=True
    )
    doc = await db.counters.find_one({"counter_id": "student_code"}, {"_id": 0})
    return f"KL-S{doc['seq']:04d}"


async def send_email(to_email: str, subject: str, html_content: str):
    """Send email via Gmail SMTP"""
    try:
        config = _get_email_config()
        if not config["password"]:
            logger.error("Gmail App Password not configured")
            return None

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"Kaimera Learning <{config['email']}>"
        msg["To"] = to_email
        msg.attach(MIMEText(html_content, "html"))

        def _send():
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(config["email"], config["password"])
                server.sendmail(config["email"], to_email, msg.as_string())

        await asyncio.to_thread(_send)
        logger.info(f"Email sent to {to_email} via Gmail SMTP")
        return {"id": f"gmail_{uuid.uuid4().hex[:8]}"}
    except Exception as e:
        logger.error(f"Email send failed to {to_email}: {e}")
        return None


async def generate_otp(email: str) -> str:
    """Generate and store a 6-digit OTP for email verification"""
    otp = f"{random.randint(100000, 999999)}"
    await db.otp_codes.delete_many({"email": email})
    await db.otp_codes.insert_one({
        "email": email,
        "otp": otp,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
        "verified": False
    })
    return otp
