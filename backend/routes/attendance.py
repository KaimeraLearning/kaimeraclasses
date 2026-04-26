"""Attendance routes"""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request, Header
from typing import Optional

from database import db
from services.auth import get_current_user

router = APIRouter()


@router.post("/attendance/mark")
async def mark_attendance(request: Request, authorization: Optional[str] = Header(None)):
    """Teacher marks daily attendance for a student"""
    user = await get_current_user(request, authorization)
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access only")

    body = await request.json()
    student_id = body.get("student_id")
    date = body.get("date")  # YYYY-MM-DD
    status = body.get("status", "present")  # present, absent, late
    reason = body.get("reason")  # 'forgot_to_mark' or 'rescheduled_class'
    class_id = body.get("class_id")  # which class this attendance is for

    if not student_id or not date:
        raise HTTPException(status_code=400, detail="student_id and date required")

    if status not in ["present", "absent", "late"]:
        raise HTTPException(status_code=400, detail="Invalid status. Use: present, absent, late")

    # Verify the student is assigned to this teacher (paid)
    assignment = await db.student_teacher_assignments.find_one(
        {"teacher_id": user.user_id, "student_id": student_id, "status": "approved", "payment_status": "paid"},
        {"_id": 0}
    )
    if not assignment:
        raise HTTPException(status_code=404, detail="Student not found in your class")

    # Check if there's a class scheduled for this date
    has_class_today = await db.class_sessions.find_one(
        {"teacher_id": user.user_id, "assigned_student_id": student_id,
         "status": {"$in": ["scheduled", "in_progress", "completed"]},
         "date": {"$lte": date}, "end_date": {"$gte": date}},
        {"_id": 0}
    )

    # If no class on this date, require reason and class selection
    if not has_class_today:
        if not reason:
            # Return available classes so frontend can ask
            available_classes = await db.class_sessions.find(
                {"teacher_id": user.user_id, "assigned_student_id": student_id,
                 "status": {"$in": ["scheduled", "in_progress"]}},
                {"_id": 0, "class_id": 1, "title": 1, "date": 1, "end_date": 1}
            ).to_list(20)
            return {
                "needs_reason": True,
                "message": "No class scheduled for this date. Please specify why you are marking attendance.",
                "available_classes": available_classes
            }
        if not class_id:
            raise HTTPException(status_code=400, detail="Please select which class this attendance is for")
        if reason not in ["forgot_to_mark", "rescheduled_class"]:
            raise HTTPException(status_code=400, detail="Invalid reason. Use: forgot_to_mark or rescheduled_class")

    # Upsert attendance record
    attendance_id = f"att_{uuid.uuid4().hex[:12]}"
    record = {
        "attendance_id": attendance_id,
        "teacher_id": user.user_id,
        "teacher_name": user.name,
        "student_id": student_id,
        "student_name": assignment.get("student_name"),
        "date": date,
        "status": status,
        "marked_at": datetime.now(timezone.utc).isoformat()
    }
    if class_id:
        record["class_id"] = class_id
    if reason:
        record["reason"] = reason
    if not has_class_today:
        record["off_day_marking"] = True

    await db.attendance.update_one(
        {"teacher_id": user.user_id, "student_id": student_id, "date": date},
        {"$set": record},
        upsert=True
    )

    return {"message": f"Attendance marked as {status} for {date}"}


@router.get("/attendance/teacher")
async def teacher_attendance_history(request: Request, authorization: Optional[str] = Header(None)):
    """Get attendance records for a teacher's students"""
    user = await get_current_user(request, authorization)
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access only")

    params = dict(request.query_params)
    query = {"teacher_id": user.user_id}

    if params.get("student_id"):
        query["student_id"] = params["student_id"]
    if params.get("date_from"):
        query["date"] = query.get("date", {})
        query["date"]["$gte"] = params["date_from"]
    if params.get("date_to"):
        query["date"] = query.get("date", {})
        query["date"]["$lte"] = params["date_to"]

    records = await db.attendance.find(query, {"_id": 0}).sort("date", -1).to_list(500)
    return records


@router.get("/attendance/student")
async def student_attendance_history(request: Request, authorization: Optional[str] = Header(None)):
    """Get attendance records for a student"""
    user = await get_current_user(request, authorization)
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Student access only")

    params = dict(request.query_params)
    query = {"student_id": user.user_id}

    if params.get("date_from"):
        query["date"] = query.get("date", {})
        query["date"]["$gte"] = params["date_from"]
    if params.get("date_to"):
        query["date"] = query.get("date", {})
        query["date"]["$lte"] = params["date_to"]

    records = await db.attendance.find(query, {"_id": 0}).sort("date", -1).to_list(500)
    return records


@router.get("/attendance/summary/{student_id}")
async def attendance_summary(student_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Get attendance summary for a student"""
    user = await get_current_user(request, authorization)
    if user.role not in ["teacher", "admin", "counsellor"] and user.user_id != student_id:
        raise HTTPException(status_code=403, detail="Access denied")

    records = await db.attendance.find({"student_id": student_id}, {"_id": 0}).to_list(1000)

    total = len(records)
    present = sum(1 for r in records if r.get("status") == "present")
    absent = sum(1 for r in records if r.get("status") == "absent")
    late = sum(1 for r in records if r.get("status") == "late")
    percentage = round((present / total) * 100, 1) if total > 0 else 0

    return {
        "student_id": student_id,
        "total_days": total,
        "present": present,
        "absent": absent,
        "late": late,
        "attendance_percentage": percentage
    }
