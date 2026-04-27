"""Class CRUD and lifecycle routes"""
import os
import uuid
from datetime import datetime, timezone, timedelta, timedelta
from fastapi import APIRouter, HTTPException, Request, Header
from typing import Optional

from database import db
from models.schemas import ClassSessionCreate, BookingRequest
from services.auth import get_current_user
from services.zoom import create_zoom_meeting, generate_zoom_sdk_signature

router = APIRouter()


@router.get("/classes/browse")
async def browse_classes(request: Request, authorization: Optional[str] = Header(None)):
    """Browse available classes - students only see classes created specifically for them"""
    user = await get_current_user(request, authorization)

    if user.role == "student":
        approved_assignment = await db.student_teacher_assignments.find_one(
            {"student_id": user.user_id, "status": "approved"},
            {"_id": 0}
        )
        if not approved_assignment:
            return []
        classes = await db.class_sessions.find(
            {"status": "scheduled", "teacher_id": approved_assignment['teacher_id'],
             "assigned_student_id": user.user_id},
            {"_id": 0}
        ).to_list(1000)
    else:
        classes = await db.class_sessions.find(
            {"status": "scheduled"},
            {"_id": 0}
        ).to_list(1000)

    for cls in classes:
        if isinstance(cls['created_at'], str):
            cls['created_at'] = datetime.fromisoformat(cls['created_at'])

    return classes


@router.post("/classes/book")
async def book_class(booking: BookingRequest, request: Request, authorization: Optional[str] = Header(None)):
    """Book a class - uses admin-set custom price for the student"""
    user = await get_current_user(request, authorization)

    if user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can book classes")

    cls = await db.class_sessions.find_one({"class_id": booking.class_id}, {"_id": 0})
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    if cls['status'] != "scheduled":
        raise HTTPException(status_code=400, detail="Class is not available for booking")

    enrolled = any(s['user_id'] == user.user_id for s in cls['enrolled_students'])
    if enrolled:
        raise HTTPException(status_code=400, detail="Already enrolled in this class")
    if len(cls['enrolled_students']) >= cls['max_students']:
        raise HTTPException(status_code=400, detail="Class is full")

    assignment = await db.student_teacher_assignments.find_one({
        "student_id": user.user_id, "teacher_id": cls['teacher_id'], "status": "approved"
    }, {"_id": 0})
    if not assignment:
        raise HTTPException(status_code=403, detail="You are not assigned to this teacher")

    credits_to_deduct = assignment['credit_price']
    if user.credits < credits_to_deduct:
        raise HTTPException(status_code=400, detail="Insufficient credits")

    await db.users.update_one({"user_id": user.user_id}, {"$inc": {"credits": -credits_to_deduct}})
    await db.class_sessions.update_one(
        {"class_id": booking.class_id},
        {"$push": {"enrolled_students": {"user_id": user.user_id, "name": user.name}}}
    )

    transaction_id = f"txn_{uuid.uuid4().hex[:12]}"
    await db.transactions.insert_one({
        "transaction_id": transaction_id, "user_id": user.user_id, "type": "booking",
        "amount": credits_to_deduct,
        "description": f"Booked class: {cls['title']} (Custom price: {credits_to_deduct} credits)",
        "status": "completed", "created_at": datetime.now(timezone.utc).isoformat()
    })

    return {"message": "Class booked successfully", "credits_remaining": user.credits - credits_to_deduct, "credits_deducted": credits_to_deduct}


@router.post("/classes/cancel/{class_id}")
async def cancel_booking(class_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Cancel a class booking - refunds custom price"""
    user = await get_current_user(request, authorization)

    cls = await db.class_sessions.find_one({"class_id": class_id}, {"_id": 0})
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")

    enrolled_student = None
    for s in cls['enrolled_students']:
        if s['user_id'] == user.user_id:
            enrolled_student = s
            break
    if not enrolled_student:
        raise HTTPException(status_code=400, detail="Not enrolled in this class")

    class_datetime = datetime.fromisoformat(f"{cls['date']}T{cls['start_time']}:00")
    if class_datetime.tzinfo is None:
        class_datetime = class_datetime.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) >= class_datetime:
        raise HTTPException(status_code=400, detail="Cannot cancel after class start time")

    assignment = await db.student_teacher_assignments.find_one({
        "student_id": user.user_id, "teacher_id": cls['teacher_id'], "status": "approved"
    }, {"_id": 0})
    refund_amount = assignment['credit_price'] if assignment else cls['credits_required']

    await db.users.update_one({"user_id": user.user_id}, {"$inc": {"credits": refund_amount}})
    await db.class_sessions.update_one(
        {"class_id": class_id},
        {"$pull": {"enrolled_students": {"user_id": user.user_id}}}
    )

    transaction_id = f"txn_{uuid.uuid4().hex[:12]}"
    await db.transactions.insert_one({
        "transaction_id": transaction_id, "user_id": user.user_id, "type": "refund",
        "amount": refund_amount, "description": f"Cancelled class: {cls['title']}",
        "status": "completed", "created_at": datetime.now(timezone.utc).isoformat()
    })

    return {"message": "Booking cancelled and credits refunded"}


@router.post("/classes/cancel-session/{class_id}")
async def cancel_todays_session(class_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Student cancels today's live session (not the entire enrollment)"""
    user = await get_current_user(request, authorization)

    cls = await db.class_sessions.find_one({"class_id": class_id}, {"_id": 0})
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")

    is_enrolled = any(s["user_id"] == user.user_id for s in cls.get("enrolled_students", []))
    if not is_enrolled:
        raise HTTPException(status_code=400, detail="Not enrolled")

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cancellations = cls.get("cancellations", [])
    max_cancel = cls.get("max_cancellations", 3)

    if len(cancellations) >= max_cancel:
        raise HTTPException(status_code=400, detail=f"Maximum {max_cancel} cancellations reached")
    if any(c.get("date") == today for c in cancellations):
        raise HTTPException(status_code=400, detail="Already cancelled today's session")

    cancellations.append({
        "date": today,
        "cancelled_by": user.user_id,
        "cancelled_at": datetime.now(timezone.utc).isoformat()
    })

    end_date = cls.get("end_date", cls.get("date"))
    new_end = (datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")

    await db.class_sessions.update_one(
        {"class_id": class_id},
        {"$set": {"cancellations": cancellations, "cancelled_today": True, "end_date": new_end}}
    )

    await db.notifications.insert_one({
        "notification_id": f"notif_{uuid.uuid4().hex[:12]}",
        "user_id": cls["teacher_id"], "type": "session_cancelled",
        "title": "Session Cancelled by Student",
        "message": f"Student {user.name} cancelled today's session for '{cls['title']}'. You can reschedule.",
        "read": False, "created_at": datetime.now(timezone.utc).isoformat()
    })

    return {"message": "Today's session cancelled. Teacher will reschedule."}


@router.post("/classes/create")
async def create_class(class_data: ClassSessionCreate, request: Request, authorization: Optional[str] = Header(None)):
    """Create a new class session - teacher must select student"""
    user = await get_current_user(request, authorization)

    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access only")
    if not user.is_approved:
        raise HTTPException(status_code=403, detail="Teacher account not approved yet")

    # Check suspension
    if getattr(user, 'is_suspended', False):
        susp_until = getattr(user, 'suspended_until', None)
        raise HTTPException(status_code=403, detail=f"Account suspended until {susp_until}. Cannot create classes.")

    assignment = await db.student_teacher_assignments.find_one({
        "teacher_id": user.user_id, "student_id": class_data.assigned_student_id, "status": "approved"
    }, {"_id": 0})
    if not assignment:
        raise HTTPException(status_code=403, detail="Student not assigned to you or assignment not approved")

    # Must have paid
    if assignment.get("payment_status") != "paid":
        raise HTTPException(status_code=400, detail="Student has not paid for this assignment yet")

    # Auto-enforce assigned_days from counsellor's assignment
    enforced_days = assignment.get("assigned_days")
    if enforced_days and enforced_days > 0:
        if class_data.duration_days != enforced_days:
            class_data.duration_days = enforced_days

    # DUPLICATE PREVENTION
    existing_active = await db.class_sessions.find_one({
        "teacher_id": user.user_id, "assigned_student_id": class_data.assigned_student_id,
        "status": {"$in": ["scheduled", "in_progress"]}
    }, {"_id": 0})
    if existing_active:
        raise HTTPException(status_code=400, detail="You already have an active class with this student. Complete or cancel it first.")

    pricing = await db.system_pricing.find_one({"pricing_id": "system_pricing"}, {"_id": 0})
    if not pricing:
        raise HTTPException(status_code=500, detail="System pricing not configured")

    if class_data.is_demo:
        price_per_day = pricing.get('demo_price_student', 0)
    else:
        price_per_day = pricing.get('class_price_student', 0)

    total_cost = price_per_day * class_data.duration_days

    student = await db.users.find_one({"user_id": class_data.assigned_student_id}, {"_id": 0})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    if student.get("credits", 0) < total_cost and total_cost > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Action Failed: Insufficient funds in student account. Required: {total_cost} credits, Available: {student.get('credits', 0)} credits."
        )

    start_date = datetime.fromisoformat(class_data.date)
    end_date = start_date + timedelta(days=class_data.duration_days - 1)

    class_id = f"class_{uuid.uuid4().hex[:12]}"
    class_doc = {
        "class_id": class_id, "teacher_id": user.user_id, "teacher_name": user.name,
        "title": class_data.title, "subject": class_data.subject,
        "class_type": class_data.class_type, "is_demo": class_data.is_demo,
        "date": class_data.date, "end_date": end_date.isoformat().split('T')[0],
        "duration_days": class_data.duration_days, "current_day": 1,
        "start_time": class_data.start_time, "end_time": class_data.end_time,
        "credits_required": total_cost, "price_per_day": price_per_day,
        "max_students": class_data.max_students, "assigned_student_id": class_data.assigned_student_id,
        "enrolled_students": [], "status": "scheduled", "verification_status": "pending",
        "cancellations": [], "cancellation_count": 0, "max_cancellations": 3,
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    insert_doc = class_doc.copy()
    await db.class_sessions.insert_one(insert_doc)

    await db.class_sessions.update_one(
        {"class_id": class_id},
        {"$push": {"enrolled_students": {"user_id": student['user_id'], "name": student['name']}}}
    )

    if total_cost > 0:
        await db.users.update_one({"user_id": student['user_id']}, {"$inc": {"credits": -total_cost}})
        transaction_id = f"txn_{uuid.uuid4().hex[:12]}"
        await db.transactions.insert_one({
            "transaction_id": transaction_id, "user_id": student['user_id'], "type": "class_booking",
            "amount": -total_cost,
            "description": f"Class: {class_data.title} ({class_data.duration_days} days x {price_per_day} credits/day)",
            "status": "completed", "created_at": datetime.now(timezone.utc).isoformat()
        })

    if not class_data.is_demo:
        demo = await db.demo_requests.find_one({
            "student_id": class_data.assigned_student_id,
            "accepted_by_teacher_id": user.user_id,
            "status": {"$in": ["completed", "feedback_submitted"]}
        }, {"_id": 0})
        if demo:
            await db.users.update_one(
                {"user_id": class_data.assigned_student_id},
                {"$set": {"matured_lead": True, "matured_at": datetime.now(timezone.utc).isoformat()}}
            )

    response_doc = {k: v for k, v in class_doc.items() if k != 'credits_required'}
    return {"message": "Class created successfully", "class": response_doc}


@router.delete("/classes/delete/{class_id}")
async def delete_class(class_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Admin deletes a class - refunds student credits if charged"""
    user = await get_current_user(request, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can delete classes")

    cls = await db.class_sessions.find_one({"class_id": class_id}, {"_id": 0})
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")

    # Refund student credits if class was charged
    refund_amount = cls.get("credits_required", 0)
    student_id = cls.get("assigned_student_id")
    teacher_id = cls.get("teacher_id")
    if student_id and refund_amount > 0 and cls.get("status") != "completed":
        await db.users.update_one({"user_id": student_id}, {"$inc": {"credits": refund_amount}})
        await db.transactions.insert_one({
            "transaction_id": f"txn_{uuid.uuid4().hex[:12]}",
            "user_id": student_id, "type": "class_delete_refund",
            "amount": refund_amount,
            "description": f"Refund: Class '{cls['title']}' deleted by admin",
            "status": "completed", "created_at": datetime.now(timezone.utc).isoformat()
        })

    await db.class_sessions.delete_one({"class_id": class_id})

    # Notify teacher
    if teacher_id:
        await db.notifications.insert_one({
            "notification_id": f"notif_{uuid.uuid4().hex[:12]}",
            "user_id": teacher_id, "type": "class_deleted_by_admin",
            "title": "Class Deleted by Admin",
            "message": f"Your class '{cls['title']}' has been deleted by admin.",
            "read": False, "created_at": datetime.now(timezone.utc).isoformat()
        })

    return {"message": "Class deleted successfully", "refunded": refund_amount if student_id and refund_amount > 0 else 0}


@router.post("/classes/start/{class_id}")
async def start_class(class_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Teacher starts a class session - only allowed 5 min before start_time, blocked after end_time"""
    user = await get_current_user(request, authorization)
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access only")

    cls = await db.class_sessions.find_one({"class_id": class_id}, {"_id": 0})
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    if cls['teacher_id'] != user.user_id:
        raise HTTPException(status_code=403, detail="Not your class")
    if cls['status'] not in ['scheduled', 'in_progress']:
        raise HTTPException(status_code=400, detail=f"Cannot start class with status: {cls['status']}")

    # Block starting if a cancelled session needs reschedule first
    if cls.get("needs_reschedule"):
        raise HTTPException(status_code=400, detail="Cannot start class: A cancelled session needs to be rescheduled first.")

    # Time window check: 5 min before start_time to end_time
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")
    class_date = cls.get("date", "")
    start_time_str = cls.get("start_time", "")
    end_time_str = cls.get("end_time", "")

    if class_date and start_time_str and end_time_str and class_date <= today_str:
        try:
            from datetime import time as dt_time
            # Parse start and end times
            start_parts = start_time_str.split(":")
            end_parts = end_time_str.split(":")
            start_hour, start_min = int(start_parts[0]), int(start_parts[1]) if len(start_parts) > 1 else 0
            end_hour, end_min = int(end_parts[0]), int(end_parts[1]) if len(end_parts) > 1 else 0

            # Use IST (UTC+5:30) for time comparison
            ist_offset = timedelta(hours=5, minutes=30)
            now_ist = now + ist_offset
            current_hour = now_ist.hour
            current_min = now_ist.minute
            current_total_min = current_hour * 60 + current_min
            start_total_min = start_hour * 60 + start_min
            end_total_min = end_hour * 60 + end_min

            # Can start 5 min before start_time
            if current_total_min < start_total_min - 5:
                raise HTTPException(status_code=400, detail=f"Class starts at {start_time_str}. You can start 5 minutes before.")
            # Cannot start after end_time — auto-cancel this session
            if current_total_min > end_total_min:
                # Record auto-cancel in session_history
                session_history = cls.get("session_history", [])
                today_date = now.strftime("%Y-%m-%d")
                already_recorded = any(s.get("date") == today_date and s.get("status") == "auto_cancelled" for s in session_history)
                if not already_recorded:
                    session_history.append({
                        "date": today_date,
                        "status": "auto_cancelled",
                        "reason": "Teacher did not start class before end time",
                        "cancelled_at": now.isoformat()
                    })
                    # Shift end_date +1 day
                    end_date = cls.get("end_date", cls.get("date"))
                    new_end = (datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
                    await db.class_sessions.update_one(
                        {"class_id": class_id},
                        {"$set": {
                            "session_history": session_history,
                            "end_date": new_end,
                            "needs_reschedule": True,
                            "last_cancelled_by": "auto",
                            "last_cancelled_at": now.isoformat()
                        }}
                    )
                raise HTTPException(status_code=400, detail=f"Class time has ended ({end_time_str}). Session auto-cancelled. Please reschedule.")
        except HTTPException:
            raise
        except Exception:
            pass  # If time parsing fails, allow start

    # Verify payment for assigned student (skip for demo classes)
    if not cls.get("is_demo") and cls.get("assigned_student_id"):
        assignment = await db.student_teacher_assignments.find_one(
            {"teacher_id": user.user_id, "student_id": cls["assigned_student_id"], "status": "approved"},
            {"_id": 0}
        )
        if assignment and assignment.get("payment_status") != "paid":
            raise HTTPException(status_code=400, detail="Cannot start class: Student payment is still pending.")

    # Create Zoom meeting (or reuse existing)
    zoom_data = cls.get("zoom_meeting")
    if not zoom_data or not zoom_data.get("id"):
        try:
            zoom_meeting = create_zoom_meeting(
                topic=f"{cls['title']} - Kaimera Learning",
                duration=120
            )
            zoom_data = {
                "id": zoom_meeting["id"],
                "join_url": zoom_meeting["join_url"],
                "password": zoom_meeting.get("password", ""),
                "host_email": zoom_meeting.get("host_email", "")
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to create video meeting: {str(e)}")

    # Generate SDK signatures for host (teacher) and participant (student)
    meeting_number = zoom_data["id"]
    try:
        host_signature = generate_zoom_sdk_signature(meeting_number, role=1)
        participant_signature = generate_zoom_sdk_signature(meeting_number, role=0)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate video credentials: {str(e)}")

    await db.class_sessions.update_one(
        {"class_id": class_id},
        {"$set": {
            "status": "in_progress",
            "zoom_meeting": zoom_data,
            "zoom_host_signature": host_signature,
            "zoom_participant_signature": participant_signature,
            "room_id": str(meeting_number),
            "last_started_at": datetime.now(timezone.utc).isoformat()
        }}
    )

    for student in cls.get('enrolled_students', []):
        await db.notifications.insert_one({
            "notification_id": f"notif_{uuid.uuid4().hex[:12]}", "user_id": student['user_id'],
            "type": "class_started", "title": "Class Started!",
            "message": f"'{cls['title']}' has started. Join now!",
            "read": False, "related_id": class_id, "created_at": datetime.now(timezone.utc).isoformat()
        })

    return {
        "message": "Class started",
        "room_id": str(meeting_number),
        "zoom_meeting_id": meeting_number,
        "zoom_join_url": zoom_data["join_url"],
        "zoom_password": zoom_data["password"],
        "zoom_signature": host_signature,
        "zoom_sdk_key": os.environ.get("ZOOM_SDK_KEY", "")
    }


@router.post("/classes/end/{class_id}")
async def end_class(class_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Teacher ends a class session"""
    user = await get_current_user(request, authorization)
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access only")

    cls = await db.class_sessions.find_one({"class_id": class_id}, {"_id": 0})
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    if cls['teacher_id'] != user.user_id:
        raise HTTPException(status_code=403, detail="Not your class")

    today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    end_date_str = cls.get('end_date', cls['date'])
    assigned_days = cls.get('duration_days', 1)
    sessions_conducted = cls.get('sessions_conducted', 0) + 1

    # Record this session in session_history
    session_record = {
        "date": today_str,
        "status": "conducted",
        "started_at": cls.get("last_started_at"),
        "ended_at": datetime.now(timezone.utc).isoformat()
    }
    session_history = cls.get("session_history", [])
    session_history.append(session_record)

    # Class completes only when all assigned sessions are successfully conducted
    if sessions_conducted >= assigned_days:
        new_status = "completed"
    else:
        new_status = "scheduled"

    await db.class_sessions.update_one(
        {"class_id": class_id},
        {"$set": {
            "status": new_status, "room_id": None,
            "last_ended_at": datetime.now(timezone.utc).isoformat(),
            "sessions_conducted": sessions_conducted,
            "session_history": session_history
        }}
    )

    # If this is a demo class and it's completed, mark the demo_request as completed
    if new_status == "completed" and cls.get("is_demo"):
        student_id = cls.get("assigned_student_id")
        teacher_id = cls.get("teacher_id")
        if student_id and teacher_id:
            await db.demo_requests.update_many(
                {"$or": [{"student_user_id": student_id}, {"student_id": student_id}],
                 "accepted_by_teacher_id": teacher_id, "status": "accepted"},
                {"$set": {"status": "completed", "completed_at": datetime.now(timezone.utc).isoformat()}}
            )

    return {"message": f"Class ended. Status: {new_status}", "status": new_status}


@router.get("/classes/status/{class_id}")
async def get_class_status(class_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Get class current status and room info - restricted to involved users"""
    user = await get_current_user(request, authorization)

    cls = await db.class_sessions.find_one({"class_id": class_id}, {"_id": 0})
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")

    # Only allow involved users or admin/counsellor
    if user.role not in ["admin", "counsellor"]:
        if user.role == "teacher" and cls['teacher_id'] != user.user_id:
            raise HTTPException(status_code=403, detail="Not authorized to view this class")
        if user.role == "student" and cls.get('assigned_student_id') != user.user_id:
            raise HTTPException(status_code=403, detail="Not authorized to view this class")

    # Determine role for Zoom signature
    zoom_meeting = cls.get("zoom_meeting", {})
    zoom_signature = ""
    zoom_sdk_key = os.environ.get("ZOOM_SDK_KEY", "")
    if zoom_meeting.get("id") and cls['status'] == 'in_progress':
        role = 1 if user.role == "teacher" and cls['teacher_id'] == user.user_id else 0
        zoom_signature = generate_zoom_sdk_signature(zoom_meeting["id"], role)

    return {
        "class_id": cls['class_id'], "title": cls['title'],
        "status": cls['status'], "room_id": cls.get('room_id'),
        "teacher_id": cls['teacher_id'], "teacher_name": cls['teacher_name'],
        "is_in_progress": cls['status'] == 'in_progress',
        "zoom_meeting_id": zoom_meeting.get("id"),
        "zoom_join_url": zoom_meeting.get("join_url"),
        "zoom_password": zoom_meeting.get("password", ""),
        "zoom_signature": zoom_signature,
        "zoom_sdk_key": zoom_sdk_key
    }


@router.post("/classes/cancel-day/{class_id}")
async def cancel_class_day(class_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Student cancels class for a day - extends duration, max 3 cancellations"""
    user = await get_current_user(request, authorization)
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Student access only")

    cls = await db.class_sessions.find_one({"class_id": class_id}, {"_id": 0})
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    if cls.get('assigned_student_id') != user.user_id:
        raise HTTPException(status_code=403, detail="Not your class")
    if cls['status'] != 'scheduled':
        raise HTTPException(status_code=400, detail="Class is not active")

    cancellation_count = cls.get('cancellation_count', 0)
    max_cancellations = cls.get('max_cancellations', 3)

    if cancellation_count >= max_cancellations:
        await db.class_sessions.update_one({"class_id": class_id}, {"$set": {"status": "dismissed"}})
        await db.notifications.insert_one({
            "notification_id": f"notif_{uuid.uuid4().hex[:12]}", "user_id": cls['teacher_id'],
            "type": "class_dismissed", "title": "Class Dismissed",
            "message": f"Class '{cls['title']}' has been dismissed. {user.name} exceeded max cancellations ({max_cancellations}).",
            "read": False, "related_id": class_id, "created_at": datetime.now(timezone.utc).isoformat()
        })
        raise HTTPException(status_code=400, detail="Maximum cancellations reached. Class has been dismissed.")

    today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    existing_cancellations = cls.get('cancellations', [])
    for c in existing_cancellations:
        if c.get('date') == today_str:
            raise HTTPException(status_code=400, detail="Already cancelled for today")

    cancellation_record = {
        "date": today_str,
        "cancelled_at": datetime.now(timezone.utc).isoformat(),
        "student_id": user.user_id
    }

    current_end_date = datetime.fromisoformat(cls.get('end_date', cls['date']))
    new_end_date = current_end_date + timedelta(days=1)
    new_duration = cls.get('duration_days', 1) + 1
    new_count = cancellation_count + 1

    await db.class_sessions.update_one(
        {"class_id": class_id},
        {"$push": {"cancellations": cancellation_record},
         "$set": {"cancellation_count": new_count, "end_date": new_end_date.strftime('%Y-%m-%d'), "duration_days": new_duration}}
    )

    await db.notifications.insert_one({
        "notification_id": f"notif_{uuid.uuid4().hex[:12]}", "user_id": cls['teacher_id'],
        "type": "class_cancelled_day", "title": "Class Cancelled Today",
        "message": f"{user.name} cancelled today's session of '{cls['title']}'. Class extended by 1 day. ({new_count}/{max_cancellations} cancellations used)",
        "read": False, "related_id": class_id, "created_at": datetime.now(timezone.utc).isoformat()
    })

    remaining = max_cancellations - new_count
    return {
        "message": f"Class cancelled for today. Duration extended by 1 day. {remaining} cancellations remaining.",
        "cancellation_count": new_count, "remaining_cancellations": remaining,
        "new_end_date": new_end_date.strftime('%Y-%m-%d')
    }
