"""Demo booking and feedback routes"""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request, Header
from typing import Optional

from database import db
from models.schemas import DemoRequestCreate, DemoAssign, DemoFeedbackCreate
from services.auth import get_current_user, hash_password
from services.helpers import send_email, notify_event

router = APIRouter()


async def _create_demo_class(demo: dict, teacher_user_id: str, teacher_name: str):
    """Shared helper to create a demo class from a demo request"""
    student = await db.users.find_one({"email": demo["email"]}, {"_id": 0})
    temp_password = None

    if not student:
        student_id = f"user_{uuid.uuid4().hex[:12]}"
        temp_password = f"demo{uuid.uuid4().hex[:8]}"
        password_hash_val = hash_password(temp_password)
        student = {
            "user_id": student_id, "email": demo["email"], "name": demo["name"],
            "role": "student", "credits": 0.0, "picture": None,
            "password_hash": password_hash_val, "is_approved": True,
            "phone": demo.get("phone"), "bio": None,
            "institute": demo.get("institute"), "goal": None,
            "preferred_time_slot": demo.get("preferred_time_slot"),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        insert_student = student.copy()
        await db.users.insert_one(insert_student)
    else:
        student_id = student["user_id"]

    pricing = await db.system_pricing.find_one({"pricing_id": "system_pricing"}, {"_id": 0})
    demo_price = pricing.get("demo_price_student", 0) if pricing else 0

    preferred_time = demo.get("preferred_time_slot", "10:00")
    try:
        parts = preferred_time.split(":")
        hour = int(parts[0])
        minute = parts[1] if len(parts) > 1 else "00"
        end_time = f"{hour + 1:02d}:{minute}"
    except Exception:
        preferred_time = "10:00"
        end_time = "11:00"

    class_id = f"class_{uuid.uuid4().hex[:12]}"
    class_doc = {
        "class_id": class_id, "teacher_id": teacher_user_id, "teacher_name": teacher_name,
        "title": f"Demo Session - {demo['name']}", "subject": "Demo",
        "class_type": "1:1", "is_demo": True,
        "date": demo["preferred_date"], "end_date": demo["preferred_date"],
        "duration_days": 1, "start_time": preferred_time, "end_time": end_time,
        "credits_required": demo_price, "max_students": 1,
        "assigned_student_id": student_id,
        "enrolled_students": [{"user_id": student_id, "name": demo["name"]}],
        "status": "scheduled", "verification_status": "pending",
        "cancellations": [], "cancellation_count": 0, "max_cancellations": 0,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    insert_class = class_doc.copy()
    await db.class_sessions.insert_one(insert_class)

    if demo_price > 0:
        await db.users.update_one({"user_id": student_id}, {"$inc": {"credits": -demo_price}})
        await db.transactions.insert_one({
            "transaction_id": f"txn_{uuid.uuid4().hex[:12]}",
            "user_id": student_id, "type": "demo_booking", "amount": demo_price,
            "description": f"Demo class with {teacher_name}",
            "status": "completed", "created_at": datetime.now(timezone.utc).isoformat()
        })

    await db.notifications.insert_one({
        "notification_id": f"notif_{uuid.uuid4().hex[:12]}",
        "user_id": student_id, "type": "demo_accepted",
        "title": "Demo Session Confirmed!",
        "message": f"Your demo has been accepted by {teacher_name}. Scheduled: {demo['preferred_date']} at {preferred_time}.",
        "read": False, "related_id": class_id, "created_at": datetime.now(timezone.utc).isoformat()
    })

    await send_email(
        demo["email"],
        "Your Demo Session is Confirmed! - Kaimera Learning",
        f"""<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;">
        <div style="background:linear-gradient(135deg,#0ea5e9,#8b5cf6);padding:30px;border-radius:16px;color:#fff;text-align:center;">
            <h1 style="margin:0;font-size:24px;">Demo Confirmed!</h1>
        </div>
        <div style="padding:20px;background:#f8fafc;border-radius:0 0 16px 16px;">
            <p>Hi <strong>{demo['name']}</strong>,</p>
            <p>Great news! Your demo session has been accepted by <strong>{teacher_name}</strong>.</p>
            <table style="width:100%;border-collapse:collapse;margin:16px 0;">
                <tr><td style="padding:8px;border-bottom:1px solid #e2e8f0;color:#64748b;">Date</td><td style="padding:8px;border-bottom:1px solid #e2e8f0;font-weight:bold;">{demo['preferred_date']}</td></tr>
                <tr><td style="padding:8px;border-bottom:1px solid #e2e8f0;color:#64748b;">Time</td><td style="padding:8px;border-bottom:1px solid #e2e8f0;font-weight:bold;">{preferred_time}</td></tr>
                <tr><td style="padding:8px;border-bottom:1px solid #e2e8f0;color:#64748b;">Teacher</td><td style="padding:8px;border-bottom:1px solid #e2e8f0;font-weight:bold;">{teacher_name}</td></tr>
            </table>
            {f'<p style="background:#fef3c7;padding:12px;border-radius:8px;">Your login: <strong>{demo["email"]}</strong> / <strong>{temp_password}</strong></p>' if temp_password else ''}
            <p style="color:#64748b;font-size:14px;">Log in to your dashboard to join the class when it\'s time.</p>
        </div>
        <p style="text-align:center;color:#94a3b8;font-size:12px;margin-top:16px;">Kaimera Learning</p>
        </div>"""
    )

    return class_id, student_id, temp_password


@router.post("/demo/request")
async def create_demo_request(demo_data: DemoRequestCreate):
    """Public endpoint - anyone can request a demo (no auth required)"""
    existing_demos = await db.demo_requests.count_documents({"email": demo_data.email})
    max_demos = 3
    extra = await db.demo_extras.find_one({"email": demo_data.email}, {"_id": 0})
    if extra:
        max_demos += extra.get("extra_count", 0)
    if existing_demos >= max_demos:
        raise HTTPException(status_code=400, detail=f"Maximum {max_demos} demo requests reached for this email. Contact admin for an additional chance.")

    demo_id = f"demo_{uuid.uuid4().hex[:12]}"
    existing_user = await db.users.find_one({"email": demo_data.email}, {"_id": 0})

    demo_doc = {
        "demo_id": demo_id, "name": demo_data.name, "email": demo_data.email,
        "phone": demo_data.phone, "age": demo_data.age, "institute": demo_data.institute,
        "preferred_date": demo_data.preferred_date, "preferred_time_slot": demo_data.preferred_time_slot,
        "message": demo_data.message, "status": "pending",
        "student_user_id": existing_user["user_id"] if existing_user else None,
        "accepted_by_teacher_id": None, "accepted_by_teacher_name": None,
        "assigned_by": None, "assigned_teacher_id": None, "assigned_teacher_name": None,
        "class_id": None, "demo_number": existing_demos + 1,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    insert_doc = demo_doc.copy()
    await db.demo_requests.insert_one(insert_doc)

    await db.history_logs.insert_one({
        "log_id": f"log_{uuid.uuid4().hex[:12]}",
        "action": "demo_requested", "actor_name": demo_data.name,
        "actor_email": demo_data.email,
        "actor_id": existing_user["user_id"] if existing_user else None,
        "actor_role": "student", "target_type": "demo", "target_id": demo_id,
        "related_student_id": existing_user["user_id"] if existing_user else None,
        "related_student_name": demo_data.name,
        "details": f"{demo_data.name} requested demo #{existing_demos + 1} for {demo_data.preferred_date} at {demo_data.preferred_time_slot}",
        "created_at": datetime.now(timezone.utc).isoformat()
    })

    return {"message": "Demo request submitted successfully!", "demo_id": demo_id}


@router.get("/demo/live-sheet")
async def get_demo_live_sheet(request: Request, authorization: Optional[str] = Header(None)):
    """Get all pending demo requests - visible to teachers and counsellors"""
    user = await get_current_user(request, authorization)
    if user.role not in ["teacher", "counsellor", "admin"]:
        raise HTTPException(status_code=403, detail="Access denied")

    demos = await db.demo_requests.find({"status": "pending"}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    teachers = []
    if user.role in ["counsellor", "admin"]:
        teachers = await db.users.find(
            {"role": "teacher", "is_approved": True}, {"_id": 0, "password_hash": 0}
        ).to_list(1000)

    return {"demos": demos, "teachers": teachers}


@router.post("/demo/accept/{demo_id}")
async def accept_demo(demo_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Teacher accepts a demo request - auto-creates demo class and notifies student"""
    user = await get_current_user(request, authorization)
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access only")
    if not user.is_approved:
        raise HTTPException(status_code=403, detail="Teacher not approved")

    demo = await db.demo_requests.find_one({"demo_id": demo_id}, {"_id": 0})
    if not demo:
        raise HTTPException(status_code=404, detail="Demo request not found")
    if demo["status"] != "pending":
        raise HTTPException(status_code=400, detail="Demo already processed")

    class_id, student_id, temp_password = await _create_demo_class(demo, user.user_id, user.name)

    await db.demo_requests.update_one(
        {"demo_id": demo_id},
        {"$set": {
            "status": "accepted", "accepted_by_teacher_id": user.user_id,
            "accepted_by_teacher_name": user.name, "student_user_id": student_id,
            "class_id": class_id, "accepted_at": datetime.now(timezone.utc).isoformat()
        }}
    )

    await db.history_logs.insert_one({
        "log_id": f"log_{uuid.uuid4().hex[:12]}",
        "action": "demo_accepted", "actor_id": user.user_id, "actor_name": user.name,
        "actor_role": "teacher", "target_type": "demo", "target_id": demo_id,
        "related_student_id": student_id, "related_student_name": demo["name"],
        "related_class_id": class_id,
        "details": f"{user.name} accepted demo for {demo['name']}. Class scheduled: {demo['preferred_date']} at {demo.get('preferred_time_slot', '')}",
        "created_at": datetime.now(timezone.utc).isoformat()
    })

    result = {"message": f"Demo accepted! Class created for {demo['preferred_date']} at {demo.get('preferred_time_slot', '')}", "class_id": class_id, "student_id": student_id}
    if temp_password:
        # Send credentials directly to student email (don't return password to teacher publicly)
        creds_html = f"""<div style="background:white;border:2px solid #e2e8f0;border-radius:12px;padding:20px;margin:16px 0;">
            <p style="margin:0 0 8px;color:#475569;font-size:14px;">Login Email:</p>
            <p style="margin:0 0 16px;font-weight:bold;color:#0f172a;font-size:16px;">{demo['email']}</p>
            <p style="margin:0 0 8px;color:#475569;font-size:14px;">Temporary Password:</p>
            <p style="margin:0 0 8px;font-family:monospace;background:#f1f5f9;padding:10px;border-radius:6px;font-size:18px;letter-spacing:1px;">{temp_password}</p>
        </div>"""
        await notify_event(
            demo['email'],
            f"Your Demo with {user.name} is Confirmed",
            "Welcome to Kaimera Learning!",
            f"Hi {demo['name']}, teacher <b>{user.name}</b> has accepted your demo request. Your demo class is scheduled for <b>{demo['preferred_date']} at {demo.get('preferred_time_slot','')}</b>. Use the credentials below to log in:",
            body_html=creds_html,
            cta_label="Sign In Now",
            cta_url="https://edu.kaimeralearning.com/login",
            event_key="demo_accepted_new_student",
            vars={"student_name": demo['name'], "teacher_name": user.name, "preferred_date": demo['preferred_date'], "preferred_time": demo.get('preferred_time_slot', ''), "email": demo['email'], "temp_password": temp_password, "credentials_block": creds_html},
        )
        # Don't expose password back to teacher anymore
        result["student_credentials_emailed"] = True
    else:
        # Existing student — just notify them about teacher accepting demo
        await notify_event(
            demo['email'],
            f"Your demo with {user.name} is confirmed",
            "Demo Confirmed",
            f"Hi {demo['name']}, teacher <b>{user.name}</b> has accepted your demo request. Your demo class is scheduled for <b>{demo['preferred_date']} at {demo.get('preferred_time_slot','')}</b>.",
            cta_label="Open Dashboard",
            cta_url="https://edu.kaimeralearning.com/student-dashboard",
            event_key="demo_accepted_existing_student",
            vars={"student_name": demo['name'], "teacher_name": user.name, "preferred_date": demo['preferred_date'], "preferred_time": demo.get('preferred_time_slot', '')},
        )
    return result


@router.post("/demo/assign")
async def assign_demo_to_teacher(data: DemoAssign, request: Request, authorization: Optional[str] = Header(None)):
    """Counsellor assigns a demo to a specific teacher - auto-creates class"""
    user = await get_current_user(request, authorization)
    if user.role not in ["counsellor", "admin"]:
        raise HTTPException(status_code=403, detail="Counsellor or Admin access only")

    demo = await db.demo_requests.find_one({"demo_id": data.demo_id}, {"_id": 0})
    if not demo:
        raise HTTPException(status_code=404, detail="Demo request not found")
    if demo["status"] != "pending":
        raise HTTPException(status_code=400, detail="Demo already processed")

    teacher = await db.users.find_one({"user_id": data.teacher_id, "role": "teacher"}, {"_id": 0})
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    class_id, student_id, temp_password = await _create_demo_class(demo, teacher["user_id"], teacher["name"])

    await db.demo_requests.update_one(
        {"demo_id": data.demo_id},
        {"$set": {
            "status": "accepted", "accepted_by_teacher_id": teacher["user_id"],
            "accepted_by_teacher_name": teacher["name"],
            "assigned_by": user.user_id, "assigned_teacher_id": teacher["user_id"],
            "assigned_teacher_name": teacher["name"],
            "student_user_id": student_id, "class_id": class_id,
            "accepted_at": datetime.now(timezone.utc).isoformat()
        }}
    )

    await db.notifications.insert_one({
        "notification_id": f"notif_{uuid.uuid4().hex[:12]}",
        "user_id": teacher["user_id"], "type": "demo_assigned",
        "title": "Demo Session Assigned",
        "message": f"Demo with {demo['name']} assigned to you by {user.name}. Class: {demo['preferred_date']} at {demo.get('preferred_time_slot', '')}",
        "read": False, "related_id": class_id, "created_at": datetime.now(timezone.utc).isoformat()
    })

    await db.history_logs.insert_one({
        "log_id": f"log_{uuid.uuid4().hex[:12]}",
        "action": "demo_assigned", "actor_id": user.user_id, "actor_name": user.name,
        "actor_role": user.role, "target_type": "demo", "target_id": data.demo_id,
        "related_teacher_id": teacher["user_id"], "related_teacher_name": teacher["name"],
        "related_student_id": student_id, "related_student_name": demo["name"],
        "related_class_id": class_id,
        "details": f"{user.name} assigned demo for {demo['name']} to {teacher['name']}",
        "created_at": datetime.now(timezone.utc).isoformat()
    })

    # Email teacher: new demo assigned
    await notify_event(
        teacher.get("email"),
        f"New Demo Session Assigned — {demo['name']}",
        "Demo Session Assigned",
        f"Counselor <b>{user.name}</b> has assigned a demo session with <b>{demo['name']}</b> to you on <b>{demo['preferred_date']} at {demo.get('preferred_time_slot','')}</b>.",
        cta_label="View Teacher Dashboard",
        cta_url="https://edu.kaimeralearning.com/teacher-dashboard",
        event_key="demo_assigned_to_teacher",
        vars={"student_name": demo['name'], "teacher_name": teacher['name'], "counselor_name": user.name, "preferred_date": demo['preferred_date'], "preferred_time": demo.get('preferred_time_slot', '')},
    )

    # Email student: confirm demo + send credentials if newly created
    if temp_password:
        creds_html = f"""<div style="background:white;border:2px solid #e2e8f0;border-radius:12px;padding:20px;margin:16px 0;">
            <p style="margin:0 0 8px;color:#475569;font-size:14px;">Login Email:</p>
            <p style="margin:0 0 16px;font-weight:bold;color:#0f172a;font-size:16px;">{demo['email']}</p>
            <p style="margin:0 0 8px;color:#475569;font-size:14px;">Temporary Password:</p>
            <p style="margin:0 0 8px;font-family:monospace;background:#f1f5f9;padding:10px;border-radius:6px;font-size:18px;letter-spacing:1px;">{temp_password}</p>
        </div>"""
        await notify_event(
            demo['email'],
            f"Your Demo with {teacher['name']} is Scheduled",
            "Welcome to Kaimera Learning!",
            f"Hi {demo['name']}, our counselor has assigned <b>{teacher['name']}</b> for your demo session on <b>{demo['preferred_date']} at {demo.get('preferred_time_slot','')}</b>. Use the credentials below to log in:",
            body_html=creds_html,
            cta_label="Sign In Now",
            cta_url="https://edu.kaimeralearning.com/login",
            event_key="demo_assigned_new_student",
            vars={"student_name": demo['name'], "teacher_name": teacher['name'], "preferred_date": demo['preferred_date'], "preferred_time": demo.get('preferred_time_slot', ''), "email": demo['email'], "temp_password": temp_password, "credentials_block": creds_html},
        )
    else:
        await notify_event(
            demo['email'],
            f"Your demo with {teacher['name']} is scheduled",
            "Demo Scheduled",
            f"Hi {demo['name']}, our counselor has assigned <b>{teacher['name']}</b> as your demo teacher for <b>{demo['preferred_date']} at {demo.get('preferred_time_slot','')}</b>.",
            cta_label="Open Dashboard",
            cta_url="https://edu.kaimeralearning.com/student-dashboard",
            event_key="demo_assigned_existing_student",
            vars={"student_name": demo['name'], "teacher_name": teacher['name'], "preferred_date": demo['preferred_date'], "preferred_time": demo.get('preferred_time_slot', '')},
        )

    return {"message": f"Demo assigned to {teacher['name']} and class created"}


@router.get("/demo/my-demos")
async def get_my_demos(request: Request, authorization: Optional[str] = Header(None)):
    """Get demos relevant to the current user"""
    user = await get_current_user(request, authorization)

    if user.role == "teacher":
        demos = await db.demo_requests.find(
            {"$or": [{"accepted_by_teacher_id": user.user_id}, {"assigned_teacher_id": user.user_id}]}, {"_id": 0}
        ).sort("created_at", -1).to_list(1000)
    elif user.role == "student":
        demos = await db.demo_requests.find(
            {"$or": [{"student_user_id": user.user_id}, {"email": user.email}]}, {"_id": 0}
        ).sort("created_at", -1).to_list(1000)
    else:
        demos = await db.demo_requests.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return demos


@router.get("/demo/all")
async def get_all_demos(request: Request, authorization: Optional[str] = Header(None)):
    """Get all demo requests - Admin/Counsellor only"""
    user = await get_current_user(request, authorization)
    if user.role not in ["admin", "counsellor"]:
        raise HTTPException(status_code=403, detail="Admin or Counsellor access only")
    demos = await db.demo_requests.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return demos


@router.post("/demo/feedback")
async def submit_demo_feedback(feedback: DemoFeedbackCreate, request: Request, authorization: Optional[str] = Header(None)):
    """Student submits feedback after a demo session"""
    user = await get_current_user(request, authorization)
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Student access only")

    demo = await db.demo_requests.find_one({"demo_id": feedback.demo_id}, {"_id": 0})
    if not demo:
        raise HTTPException(status_code=404, detail="Demo not found")
    if demo.get("student_user_id") != user.user_id and demo.get("email") != user.email:
        raise HTTPException(status_code=403, detail="Not your demo")

    existing = await db.demo_feedback.find_one({"demo_id": feedback.demo_id}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Feedback already submitted")

    feedback_id = f"dfb_{uuid.uuid4().hex[:12]}"
    feedback_doc = {
        "feedback_id": feedback_id, "demo_id": feedback.demo_id,
        "student_id": user.user_id, "student_name": user.name,
        "teacher_id": demo.get("accepted_by_teacher_id"),
        "teacher_name": demo.get("accepted_by_teacher_name"),
        "rating": feedback.rating, "feedback_text": feedback.feedback_text,
        "preferred_teacher_id": feedback.preferred_teacher_id,
        "status": "pending", "created_at": datetime.now(timezone.utc).isoformat()
    }
    insert_fb = feedback_doc.copy()
    await db.demo_feedback.insert_one(insert_fb)

    await db.demo_requests.update_one(
        {"demo_id": feedback.demo_id},
        {"$set": {"status": "feedback_submitted", "feedback_id": feedback_id}}
    )

    counsellors = await db.users.find({"role": "counsellor"}, {"_id": 0}).to_list(100)
    for c in counsellors:
        await db.notifications.insert_one({
            "notification_id": f"notif_{uuid.uuid4().hex[:12]}",
            "user_id": c["user_id"], "type": "demo_feedback",
            "title": "Demo Feedback Received",
            "message": f"{user.name} submitted feedback for demo with {demo.get('accepted_by_teacher_name', 'teacher')}. Ready for regular class allocation.",
            "read": False, "related_id": feedback.demo_id, "created_at": datetime.now(timezone.utc).isoformat()
        })

    await db.history_logs.insert_one({
        "log_id": f"log_{uuid.uuid4().hex[:12]}",
        "action": "demo_feedback_submitted", "actor_id": user.user_id, "actor_name": user.name,
        "actor_role": "student", "target_type": "demo", "target_id": feedback.demo_id,
        "related_teacher_id": demo.get("accepted_by_teacher_id"),
        "related_teacher_name": demo.get("accepted_by_teacher_name"),
        "related_student_id": user.user_id, "related_student_name": user.name,
        "details": f"{user.name} rated demo {feedback.rating}/5. Preferred teacher: {feedback.preferred_teacher_id or 'Any'}",
        "created_at": datetime.now(timezone.utc).isoformat()
    })

    return {"message": "Feedback submitted! A counsellor will assign you to a regular teacher soon."}


@router.get("/demo/feedback-pending")
async def get_pending_demo_feedback(request: Request, authorization: Optional[str] = Header(None)):
    """Get demo feedback pending counsellor action"""
    user = await get_current_user(request, authorization)
    if user.role not in ["counsellor", "admin"]:
        raise HTTPException(status_code=403, detail="Counsellor or Admin access only")

    feedbacks = await db.demo_feedback.find({"status": "pending"}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return feedbacks
