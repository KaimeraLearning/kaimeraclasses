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
    """Send email via Gmail SMTP with TLS. Returns dict on success, dict with error on failure."""
    try:
        config = _get_email_config()
        if not config["password"]:
            logger.error("Gmail App Password not configured (GMAIL_APP_PASSWORD env var missing)")
            return {"error": "GMAIL_APP_PASSWORD not configured on server"}
        if not config["email"]:
            logger.error("SENDER_EMAIL not configured")
            return {"error": "SENDER_EMAIL not configured on server"}

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"Kaimera Learning <{config['email']}>"
        msg["To"] = to_email
        msg["Reply-To"] = config["email"]
        msg.attach(MIMEText(html_content, "html"))
        # Also add plain text version for better deliverability
        import re
        plain_text = re.sub(r'<[^>]+>', '', html_content).strip()
        msg.attach(MIMEText(plain_text, "plain"))

        def _send():
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(config["email"], config["password"])
                result = server.sendmail(config["email"], to_email, msg.as_string())
                logger.info(f"SMTP sendmail result for {to_email}: {result}")
                return result

        await asyncio.to_thread(_send)
        logger.info(f"Email sent to {to_email} via Gmail SMTP (TLS/587)")
        return {"id": f"gmail_{uuid.uuid4().hex[:8]}"}
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"Gmail SMTP auth failed for {config.get('email')}: {e}")
        return {"error": f"Gmail rejected credentials: {str(e)[:200]}"}
    except smtplib.SMTPException as e:
        logger.error(f"Gmail SMTP error: {e}")
        return {"error": f"SMTP error: {str(e)[:200]}"}
    except (TimeoutError, OSError) as e:
        logger.error(f"Network error reaching Gmail SMTP: {e}")
        return {"error": f"Cannot reach smtp.gmail.com:587 — port may be blocked. {str(e)[:150]}"}
    except Exception as e:
        logger.error(f"Email send failed to {to_email}: {e}")
        return {"error": str(e)[:200]}


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
