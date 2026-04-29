"""Email template registry and rendering.

Each `event_key` maps to a default template (subject/title/intro/body_html/cta_*) and
the list of variables that can be substituted via `{{var_name}}` placeholders.
Admins can override any field per event from the Admin Dashboard; overrides are
stored in the `email_templates` collection in MongoDB.
"""
import re
from typing import Optional, Dict, Any

from database import db


# ─── Registry of every email-trigger event the platform fires ─────────────────
EMAIL_EVENTS: Dict[str, Dict[str, Any]] = {
    "student_assigned_for_student": {
        "name": "Student → assigned to teacher (notify student)",
        "description": "Sent to a student when admin/counselor assigns them to a teacher.",
        "subject": "You've been assigned to {{teacher_name}}",
        "title": "Welcome to your learning journey, {{student_name}}!",
        "intro": "Our counselor has assigned <b>{{teacher_name}}</b> as your teacher for the <b>{{plan_label}}</b> ({{days_label}}). You'll receive class invitations soon.",
        "body_html": "",
        "cta_label": "Open Dashboard",
        "cta_url": "https://edu.kaimeralearning.com/student-dashboard",
        "variables": ["student_name", "teacher_name", "plan_label", "days_label"],
    },
    "student_assigned_for_teacher": {
        "name": "Student → assigned to teacher (notify teacher)",
        "description": "Sent to a teacher when a new student is assigned for review.",
        "subject": "New Class Request — Student {{student_name}}",
        "title": "You have a new class request",
        "intro": "<b>{{student_name}}</b> has been assigned to you for the <b>{{plan_label}}</b> ({{days_label}}). Please review and accept within 24 hours from your teacher dashboard.",
        "body_html": "",
        "cta_label": "Review Request",
        "cta_url": "https://edu.kaimeralearning.com/teacher-dashboard",
        "variables": ["student_name", "teacher_name", "plan_label", "days_label"],
    },
    "teacher_account_created": {
        "name": "Account created — Teacher (with credentials)",
        "description": "Sent when admin creates a teacher account.",
        "subject": "Welcome to Kaimera Learning — Teacher Account Credentials",
        "title": "Your Teacher Account is Ready",
        "intro": "Hi {{name}}, your teacher account on Kaimera Learning has been created by the admin.",
        "body_html": "{{credentials_block}}",
        "cta_label": "Sign In Now",
        "cta_url": "https://edu.kaimeralearning.com/login",
        "variables": ["name", "email", "temp_password", "credentials_block"],
    },
    "counsellor_account_created": {
        "name": "Account created — Counselor (with credentials)",
        "description": "Sent when admin creates a counselor account.",
        "subject": "Welcome to Kaimera Learning — Counselor Account Credentials",
        "title": "Your Counselor Account is Ready",
        "intro": "Hi {{name}}, your counselor account has been created by the admin.",
        "body_html": "{{credentials_block}}",
        "cta_label": "Sign In Now",
        "cta_url": "https://edu.kaimeralearning.com/login",
        "variables": ["name", "email", "temp_password", "credentials_block"],
    },
    "student_account_created": {
        "name": "Account created — Student (with credentials)",
        "description": "Sent when admin/counselor creates a student account.",
        "subject": "Welcome to Kaimera Learning — Student Account Credentials",
        "title": "Your Student Account is Ready",
        "intro": "Hi {{name}}, your student account on Kaimera Learning has been created.",
        "body_html": "{{credentials_block}}",
        "cta_label": "Sign In Now",
        "cta_url": "https://edu.kaimeralearning.com/login",
        "variables": ["name", "email", "temp_password", "credentials_block"],
    },
    "user_account_created": {
        "name": "Account created — Generic user (with credentials)",
        "description": "Sent when /api/admin/create-user creates any role.",
        "subject": "Welcome to Kaimera Learning — {{role_capitalized}} Account Credentials",
        "title": "Your {{role_capitalized}} Account is Ready",
        "intro": "Hi {{name}}, your {{role}} account on Kaimera Learning has been created.",
        "body_html": "{{credentials_block}}",
        "cta_label": "Sign In Now",
        "cta_url": "https://edu.kaimeralearning.com/login",
        "variables": ["name", "email", "role", "role_capitalized", "temp_password", "credentials_block"],
    },
    "password_reset_by_admin": {
        "name": "Password reset by admin",
        "description": "Sent when admin resets a user's password.",
        "subject": "Kaimera Learning — Password Reset by Admin",
        "title": "Your Password Was Reset",
        "intro": "Hi {{name}}, an administrator has reset your account password.",
        "body_html": "{{credentials_block}}",
        "cta_label": "Sign In Now",
        "cta_url": "https://edu.kaimeralearning.com/login",
        "variables": ["name", "email", "new_password", "credentials_block"],
    },
    "demo_accepted_new_student": {
        "name": "Demo accepted — new student (with credentials)",
        "description": "Sent when a teacher accepts a demo for a brand new student.",
        "subject": "Your Demo with {{teacher_name}} is Confirmed",
        "title": "Welcome to Kaimera Learning!",
        "intro": "Hi {{student_name}}, teacher <b>{{teacher_name}}</b> has accepted your demo request. Your demo class is scheduled for <b>{{preferred_date}} at {{preferred_time}}</b>. Use the credentials below to log in:",
        "body_html": "{{credentials_block}}",
        "cta_label": "Sign In Now",
        "cta_url": "https://edu.kaimeralearning.com/login",
        "variables": ["student_name", "teacher_name", "preferred_date", "preferred_time", "email", "temp_password", "credentials_block"],
    },
    "demo_accepted_existing_student": {
        "name": "Demo accepted — existing student",
        "description": "Sent when a teacher accepts a demo for a returning student.",
        "subject": "Your demo with {{teacher_name}} is confirmed",
        "title": "Demo Confirmed",
        "intro": "Hi {{student_name}}, teacher <b>{{teacher_name}}</b> has accepted your demo request. Your demo class is scheduled for <b>{{preferred_date}} at {{preferred_time}}</b>.",
        "body_html": "",
        "cta_label": "Open Dashboard",
        "cta_url": "https://edu.kaimeralearning.com/student-dashboard",
        "variables": ["student_name", "teacher_name", "preferred_date", "preferred_time"],
    },
    "demo_assigned_to_teacher": {
        "name": "Demo assigned (notify teacher)",
        "description": "Sent to a teacher when counselor assigns a demo to them.",
        "subject": "New Demo Session Assigned — {{student_name}}",
        "title": "Demo Session Assigned",
        "intro": "Counselor <b>{{counselor_name}}</b> has assigned a demo session with <b>{{student_name}}</b> to you on <b>{{preferred_date}} at {{preferred_time}}</b>.",
        "body_html": "",
        "cta_label": "View Teacher Dashboard",
        "cta_url": "https://edu.kaimeralearning.com/teacher-dashboard",
        "variables": ["student_name", "teacher_name", "counselor_name", "preferred_date", "preferred_time"],
    },
    "demo_assigned_new_student": {
        "name": "Demo assigned — new student (with credentials)",
        "description": "Sent to a brand-new student when counselor assigns them a demo.",
        "subject": "Your Demo with {{teacher_name}} is Scheduled",
        "title": "Welcome to Kaimera Learning!",
        "intro": "Hi {{student_name}}, our counselor has assigned <b>{{teacher_name}}</b> for your demo session on <b>{{preferred_date}} at {{preferred_time}}</b>. Use the credentials below to log in:",
        "body_html": "{{credentials_block}}",
        "cta_label": "Sign In Now",
        "cta_url": "https://edu.kaimeralearning.com/login",
        "variables": ["student_name", "teacher_name", "preferred_date", "preferred_time", "email", "temp_password", "credentials_block"],
    },
    "demo_assigned_existing_student": {
        "name": "Demo assigned — existing student",
        "description": "Sent to a returning student when counselor assigns them a new demo.",
        "subject": "Your demo with {{teacher_name}} is scheduled",
        "title": "Demo Scheduled",
        "intro": "Hi {{student_name}}, our counselor has assigned <b>{{teacher_name}}</b> as your demo teacher for <b>{{preferred_date}} at {{preferred_time}}</b>.",
        "body_html": "",
        "cta_label": "Open Dashboard",
        "cta_url": "https://edu.kaimeralearning.com/student-dashboard",
        "variables": ["student_name", "teacher_name", "preferred_date", "preferred_time"],
    },
}


_VAR_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")


def _substitute(text: str, vars: Dict[str, Any]) -> str:
    """Replace `{{var_name}}` placeholders with values from `vars`. Unknown vars become empty."""
    if not text:
        return text or ""

    def repl(match):
        key = match.group(1)
        val = vars.get(key, "")
        return "" if val is None else str(val)

    return _VAR_RE.sub(repl, text)


# ─── Cache to keep template lookups sub-ms ────────────────────────────────────
_CACHE: Dict[str, Any] = {"value": {}, "stamp": 0}


def invalidate_template_cache():
    _CACHE["value"] = {}
    _CACHE["stamp"] = 0


async def _load_overrides() -> Dict[str, Dict[str, Any]]:
    """Loads all overrides from DB. Cached for 30s."""
    import time
    now = time.time()
    if _CACHE["value"] and now - _CACHE["stamp"] < 30:
        return _CACHE["value"]
    docs = await db.email_templates.find({}, {"_id": 0}).to_list(200)
    overrides = {d["event_key"]: d for d in docs if d.get("event_key")}
    _CACHE["value"] = overrides
    _CACHE["stamp"] = now
    return overrides


async def resolve_template(event_key: str, vars: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Returns the resolved template (defaults overlaid by DB override + variable substitution).
    Returns None if the event_key is unknown.
    Includes `inline_image_id` and `attachment_ids` from the override (admin-attached media).
    """
    base = EMAIL_EVENTS.get(event_key)
    if not base:
        return None
    overrides = await _load_overrides()
    override = overrides.get(event_key) or {}
    vars = vars or {}

    out: Dict[str, Any] = {}
    for field in ("subject", "title", "intro", "body_html", "cta_label", "cta_url"):
        raw = override.get(field) if override.get(field) else base.get(field, "")
        out[field] = _substitute(raw, vars)
    out["inline_image_id"] = override.get("inline_image_id")
    out["attachment_ids"] = override.get("attachment_ids", []) or []
    return out


def list_events() -> Dict[str, Dict[str, Any]]:
    """Returns the registry as plain dict (for admin UI)."""
    return EMAIL_EVENTS
