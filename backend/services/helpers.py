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


_EMAIL_CONFIG_CACHE = {"value": None, "stamp": 0}


async def _get_email_config():
    """Returns active Gmail SMTP config.
    Priority: DB-stored (system_config) > .env. Cached for 30s so most calls are sub-ms.
    Admin can override values from /api/admin/email-config without restarting the backend.
    """
    import time
    now = time.time()
    if _EMAIL_CONFIG_CACHE["value"] and now - _EMAIL_CONFIG_CACHE["stamp"] < 30:
        return _EMAIL_CONFIG_CACHE["value"]
    cfg = {
        "email": os.environ.get('SENDER_EMAIL') or os.environ.get('EMAIL_USER') or 'info@kaimeralearning.com',
        "password": os.environ.get('GMAIL_APP_PASSWORD') or os.environ.get('EMAIL_PASS') or ''
    }
    try:
        doc = await db.system_config.find_one({"config_id": "email"}, {"_id": 0})
        if doc:
            if doc.get("sender_email"):
                cfg["email"] = doc["sender_email"]
            if doc.get("app_password"):
                cfg["password"] = doc["app_password"]
    except Exception:
        pass
    _EMAIL_CONFIG_CACHE["value"] = cfg
    _EMAIL_CONFIG_CACHE["stamp"] = now
    return cfg


def invalidate_email_config_cache():
    _EMAIL_CONFIG_CACHE["value"] = None
    _EMAIL_CONFIG_CACHE["stamp"] = 0


# Cache for the primary admin user_id so we don't hit Mongo on every transaction.
_PRIMARY_ADMIN_ID = None


async def _get_primary_admin_id():
    """Return the user_id of the first admin (used as the platform's wallet for double-entry mirrors)."""
    global _PRIMARY_ADMIN_ID
    if _PRIMARY_ADMIN_ID:
        return _PRIMARY_ADMIN_ID
    admin = await db.users.find_one({"role": "admin"}, {"_id": 0, "user_id": 1})
    if admin:
        _PRIMARY_ADMIN_ID = admin["user_id"]
    return _PRIMARY_ADMIN_ID


async def insert_admin_mirror_txn(amount: float, description: str, txn_type: str = "platform_mirror", **refs):
    """Insert a mirror transaction in the admin's wallet whenever money moves on the platform.

    Convention: pass `amount` with the sign as seen FROM THE ADMIN'S PERSPECTIVE.
      - Student pays platform / Razorpay recharge → admin gets POSITIVE (+amount)
      - Admin disburses to teacher (proof approved) / refunds student → admin gets NEGATIVE (-amount)
    """
    admin_id = await _get_primary_admin_id()
    if not admin_id:
        return  # No admin seeded — silently skip
    doc = {
        "transaction_id": f"txn_{uuid.uuid4().hex[:12]}",
        "user_id": admin_id,
        "type": txn_type,
        "amount": amount,
        "description": description,
        "status": "completed",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    # Carry over any reference IDs (class_id, payment_id, proof_id, assignment_id, counterparty_user_id, etc.)
    for k, v in refs.items():
        if v is not None:
            doc[k] = v
    await db.transactions.insert_one(doc)



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
        config = await _get_email_config()
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


# ─── Notification email helpers ───────────────────────────────────────────────
import secrets as _secrets
import string as _string


def _wrap_email_html(title: str, intro: str, body_html: str = "", cta_label: str = "", cta_url: str = "") -> str:
    """Standard branded wrapper for transactional emails."""
    cta_block = ""
    if cta_label and cta_url:
        cta_block = f'<div style="text-align:center;margin:24px 0;"><a href="{cta_url}" style="display:inline-block;padding:12px 28px;background:#0ea5e9;color:#fff;border-radius:24px;text-decoration:none;font-weight:bold;">{cta_label}</a></div>'
    return f"""<div style="font-family:Arial,sans-serif;max-width:520px;margin:0 auto;padding:32px 24px;background:#f8fafc;border-radius:16px;">
        <h2 style="color:#0ea5e9;margin:0 0 8px;">{title}</h2>
        <p style="color:#475569;margin:0 0 16px;">{intro}</p>
        {body_html}
        {cta_block}
        <p style="color:#94a3b8;font-size:12px;margin-top:24px;">Kaimera Learning · This is an automated email · Please do not reply.</p>
    </div>"""


async def notify_event(to_email: str, subject: str, title: str, intro: str,
                       body_html: str = "", cta_label: str = "", cta_url: str = ""):
    """Best-effort transactional email. Failures are logged but never raise (so
    they don't break primary flows like demo accept, class start, etc.)."""
    if not to_email:
        return
    try:
        html = _wrap_email_html(title, intro, body_html, cta_label, cta_url)
        result = await send_email(to_email, subject, html)
        if not result or (isinstance(result, dict) and result.get("error")):
            logger.warning(f"notify_event failed for {to_email}: {result}")
    except Exception as e:
        logger.warning(f"notify_event exception for {to_email}: {e}")


def generate_temp_password(length: int = 12) -> str:
    """Generates a cryptographically secure random password with mixed character classes."""
    alphabet = _string.ascii_letters + _string.digits
    # ensure mixed: at least 1 uppercase, 1 lowercase, 1 digit
    while True:
        pwd = ''.join(_secrets.choice(alphabet) for _ in range(length))
        if (any(c.islower() for c in pwd) and any(c.isupper() for c in pwd) and any(c.isdigit() for c in pwd)):
            return pwd
