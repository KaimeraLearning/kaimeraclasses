"""Attendance routes - per-class per-day attendance tracking"""
import uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Request, Header
from typing import Optional

from database import db
from services.auth import get_current_user

router = APIRouter()


@router.post("/attendance/mark")
async def mark_attendance(request: Request, authorization: Optional[str] = Header(None)):
    """Teacher marks attendance for a specific class on a specific date. Once marked, cannot be changed."""
    user = await get_current_user(request, authorization)
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access only")

    body = await request.json()
    student_id = body.get("student_id")
    date = body.get("date")  # YYYY-MM-DD
    status = body.get("status", "present")  # present, absent, late
    class_id = body.get("class_id")
    reason = body.get("reason")  # 'forgot_to_mark' or 'rescheduled_class' (for off-day)

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
        raise HTTPException(status_code=404, detail="Student not found in your paid classes")

    # If class_id not provided, auto-detect which class covers this date
    if not class_id:
        matching_class = await db.class_sessions.find_one(
            {"teacher_id": user.user_id, "assigned_student_id": student_id,
             "status": {"$in": ["scheduled", "in_progress", "completed"]},
             "date": {"$lte": date}, "end_date": {"$gte": date}},
            {"_id": 0}
        )
        if matching_class:
            class_id = matching_class["class_id"]
        else:
            # No class on this date — need reason + class selection from teacher
            if not reason or not class_id:
                available_classes = await db.class_sessions.find(
                    {"teacher_id": user.user_id, "assigned_student_id": student_id,
                     "status": {"$in": ["scheduled", "in_progress", "completed"]}},
                    {"_id": 0, "class_id": 1, "title": 1, "date": 1, "end_date": 1}
                ).to_list(20)
                return {
                    "needs_class_selection": True,
                    "message": "No class scheduled for this date. Select which class this attendance is for.",
                    "available_classes": available_classes
                }
            if reason not in ["forgot_to_mark", "rescheduled_class"]:
                raise HTTPException(status_code=400, detail="Invalid reason. Use: forgot_to_mark or rescheduled_class")

    # Get class info for the record
    cls = await db.class_sessions.find_one({"class_id": class_id}, {"_id": 0, "class_id": 1, "title": 1})
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")

    # Check if already marked for this class+date — cannot re-mark
    existing = await db.attendance.find_one(
        {"teacher_id": user.user_id, "student_id": student_id, "class_id": class_id, "date": date},
        {"_id": 0}
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Attendance already marked as '{existing['status']}' for '{cls['title']}' on {date}. Cannot change."
        )

    attendance_id = f"att_{uuid.uuid4().hex[:12]}"
    record = {
        "attendance_id": attendance_id,
        "teacher_id": user.user_id,
        "teacher_name": user.name,
        "student_id": student_id,
        "student_name": assignment.get("student_name"),
        "class_id": class_id,
        "class_title": cls.get("title", ""),
        "date": date,
        "status": status,
        "marked_at": datetime.now(timezone.utc).isoformat()
    }
    if reason:
        record["reason"] = reason
        record["off_day_marking"] = True

    await db.attendance.insert_one(record)

    return {"message": f"Attendance marked as '{status}' for '{cls['title']}' on {date}"}


@router.get("/attendance/unmarked")
async def get_unmarked_attendance(request: Request, authorization: Optional[str] = Header(None)):
    """Get classes with unmarked attendance for this teacher (yesterday and before)"""
    user = await get_current_user(request, authorization)
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access only")

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Get all active classes for this teacher
    classes = await db.class_sessions.find(
        {"teacher_id": user.user_id, "status": {"$in": ["scheduled", "in_progress", "completed"]}},
        {"_id": 0}
    ).to_list(100)

    unmarked = []
    for cls in classes:
        student_id = cls.get("assigned_student_id")
        if not student_id:
            continue

        start = cls.get("date", "")
        end = cls.get("end_date", start)
        if not start:
            continue

        # Check each day from start to min(yesterday, end_date)
        try:
            start_dt = datetime.strptime(start, "%Y-%m-%d")
            end_dt = datetime.strptime(end, "%Y-%m-%d")
            yesterday = datetime.strptime(today, "%Y-%m-%d") - timedelta(days=1)
            check_end = min(end_dt, yesterday)
        except ValueError:
            continue

        # Skip cancelled session dates
        cancelled_dates = set()
        for c in (cls.get("cancellations") or []):
            if c.get("date"):
                cancelled_dates.add(c["date"])

        current = start_dt
        while current <= check_end:
            check_date = current.strftime("%Y-%m-%d")
            if check_date not in cancelled_dates:
                # Check if attendance exists for this class+date+student
                exists = await db.attendance.find_one(
                    {"teacher_id": user.user_id, "student_id": student_id,
                     "class_id": cls["class_id"], "date": check_date},
                    {"_id": 0, "attendance_id": 1}
                )
                if not exists:
                    unmarked.append({
                        "class_id": cls["class_id"],
                        "class_title": cls.get("title", ""),
                        "student_id": student_id,
                        "student_name": cls.get("student_name", ""),
                        "date": check_date
                    })
            current += timedelta(days=1)

    return unmarked


@router.get("/attendance/class-today/{student_id}")
async def get_today_classes_for_attendance(student_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Get today's classes for a student (for attendance marking). Also includes unmarked past days."""
    user = await get_current_user(request, authorization)
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access only")

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Today's classes for this student
    today_classes = await db.class_sessions.find(
        {"teacher_id": user.user_id, "assigned_student_id": student_id,
         "status": {"$in": ["scheduled", "in_progress", "completed"]},
         "date": {"$lte": today}, "end_date": {"$gte": today}},
        {"_id": 0, "class_id": 1, "title": 1, "date": 1, "end_date": 1}
    ).to_list(10)

    # Check which are already marked today
    result = []
    for cls in today_classes:
        existing = await db.attendance.find_one(
            {"teacher_id": user.user_id, "student_id": student_id,
             "class_id": cls["class_id"], "date": today},
            {"_id": 0, "status": 1}
        )
        cls["already_marked"] = existing is not None
        cls["marked_status"] = existing.get("status") if existing else None
        result.append(cls)

    return result


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

    records = await db.attendance.find({"student_id": user.user_id}, {"_id": 0}).sort("date", -1).to_list(500)
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
