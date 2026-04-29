"""Utility helper functions"""
import os
import uuid
import random
import asyncio
import logging
import smtplib
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders
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


async def send_email(to_email: str, subject: str, html_content: str,
                     inline_images: list = None, attachments: list = None):
    """Send email via Gmail SMTP with TLS. Returns dict on success, dict with error on failure.

    `inline_images`: list of dicts {"cid": "logo", "path": "/abs/path", "mime": "image/png"}.
        These render inside the HTML body via <img src="cid:logo">.
    `attachments`: list of dicts {"path": "/abs/path", "filename": "doc.pdf"}.
        These appear as downloadable files in the email client.
    """
    try:
        config = await _get_email_config()
        if not config["password"]:
            logger.error("Gmail App Password not configured (GMAIL_APP_PASSWORD env var missing)")
            return {"error": "GMAIL_APP_PASSWORD not configured on server"}
        if not config["email"]:
            logger.error("SENDER_EMAIL not configured")
            return {"error": "SENDER_EMAIL not configured on server"}

        has_attachments = bool(attachments)
        has_inline = bool(inline_images)

        # Build the MIME tree adaptively:
        #   - alt:        plain text + HTML (always)
        #   - related:    alt + inline-cid images (only if any inline images)
        #   - mixed:      (related|alt) + file attachments (only if any attachments)
        # In multipart/alternative the LAST attached part is what email clients
        # render when supported — so plain first, HTML last.
        import re as _re
        plain_text = _re.sub(r'<[^>]+>', ' ', html_content)
        plain_text = _re.sub(r'\s+', ' ', plain_text).strip() or " "

        body_alt = MIMEMultipart("alternative")
        body_alt.attach(MIMEText(plain_text, "plain", "utf-8"))
        body_alt.attach(MIMEText(html_content, "html", "utf-8"))

        if has_inline:
            body_related = MIMEMultipart("related")
            body_related.attach(body_alt)
            for img in inline_images:
                try:
                    with open(img["path"], "rb") as fh:
                        part = MIMEImage(fh.read(), _subtype=(img.get("mime") or "image/png").split("/")[-1])
                    part.add_header("Content-ID", f"<{img['cid']}>")
                    part.add_header("Content-Disposition", "inline", filename=os.path.basename(img["path"]))
                    body_related.attach(part)
                except Exception as ie:
                    logger.warning(f"Failed to attach inline image {img.get('cid')}: {ie}")
            body_root = body_related
        else:
            body_root = body_alt

        if has_attachments:
            outer = MIMEMultipart("mixed")
            outer.attach(body_root)
            for att in attachments:
                try:
                    with open(att["path"], "rb") as fh:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(fh.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f'attachment; filename="{att.get("filename") or os.path.basename(att["path"])}"'
                    )
                    outer.attach(part)
                except Exception as ae:
                    logger.warning(f"Failed to attach file {att.get('filename')}: {ae}")
        else:
            outer = body_root

        outer["Subject"] = subject
        outer["From"] = f"Kaimera Learning <{config['email']}>"
        outer["To"] = to_email
        outer["Reply-To"] = config["email"]

        def _send():
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(config["email"], config["password"])
                result = server.sendmail(config["email"], to_email, outer.as_string())
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


def _wrap_email_html(title: str, intro: str, body_html: str = "", cta_label: str = "", cta_url: str = "",
                     inline_logo_cid: str = "") -> str:
    """Standard branded wrapper for transactional emails.
    If `inline_logo_cid` is provided, a logo image is rendered above the title (referenced via cid:)."""
    cta_block = ""
    if cta_label and cta_url:
        cta_block = f'<div style="text-align:center;margin:24px 0;"><a href="{cta_url}" style="display:inline-block;padding:12px 28px;background:#0ea5e9;color:#fff;border-radius:24px;text-decoration:none;font-weight:bold;">{cta_label}</a></div>'
    logo_block = ""
    if inline_logo_cid:
        logo_block = f'<div style="text-align:center;margin:0 0 16px;"><img src="cid:{inline_logo_cid}" alt="Kaimera Learning" style="max-width:160px;max-height:80px;"/></div>'
    return f"""<div style="font-family:Arial,sans-serif;max-width:520px;margin:0 auto;padding:32px 24px;background:#f8fafc;border-radius:16px;">
        {logo_block}
        <h2 style="color:#0ea5e9;margin:0 0 8px;">{title}</h2>
        <p style="color:#475569;margin:0 0 16px;">{intro}</p>
        {body_html}
        {cta_block}
        <p style="color:#94a3b8;font-size:12px;margin-top:24px;">Kaimera Learning · This is an automated email · Please do not reply.</p>
    </div>"""


async def _resolve_template_media(inline_image_id, attachment_ids):
    """Look up media files from `email_media` collection; return tuples ready for send_email."""
    inline = []
    files = []
    if inline_image_id:
        m = await db.email_media.find_one({"media_id": inline_image_id}, {"_id": 0})
        if m:
            p = Path(__file__).resolve().parent.parent / "uploads" / "email_media" / m["stored_name"]
            if p.exists():
                inline.append({"cid": "logo", "path": str(p), "mime": m.get("mime", "image/png")})
    if attachment_ids:
        for aid in attachment_ids:
            m = await db.email_media.find_one({"media_id": aid}, {"_id": 0})
            if not m:
                continue
            p = Path(__file__).resolve().parent.parent / "uploads" / "email_media" / m["stored_name"]
            if p.exists():
                files.append({"path": str(p), "filename": m.get("filename") or m["stored_name"]})
    return inline, files


async def notify_event(to_email: str, subject: str = "", title: str = "", intro: str = "",
                       body_html: str = "", cta_label: str = "", cta_url: str = "",
                       event_key: str = None, vars: dict = None):
    """Best-effort transactional email. Failures are logged but never raise (so
    they don't break primary flows like demo accept, class start, etc.).

    If `event_key` is provided, the system loads the admin-editable template from DB
    (or falls back to defaults registered in `services/email_templates.py`) and substitutes
    `{{var}}` placeholders from `vars`. The positional args still work as a fallback for
    legacy call sites that haven't been migrated yet.
    """
    if not to_email:
        return
    try:
        inline_images = []
        attachments = []
        if event_key:
            from services.email_templates import resolve_template
            tpl = await resolve_template(event_key, vars)
            if tpl:
                subject = tpl["subject"] or subject
                title = tpl["title"] or title
                intro = tpl["intro"] or intro
                body_html = tpl["body_html"] if tpl["body_html"] else body_html
                cta_label = tpl["cta_label"] or cta_label
                cta_url = tpl["cta_url"] or cta_url
                inline_images, attachments = await _resolve_template_media(
                    tpl.get("inline_image_id"), tpl.get("attachment_ids", [])
                )

        logo_cid = "logo" if inline_images else ""
        html = _wrap_email_html(title, intro, body_html, cta_label, cta_url, inline_logo_cid=logo_cid)
        result = await send_email(to_email, subject, html, inline_images=inline_images, attachments=attachments)
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
