"""Razorpay payment routes"""
import os
import uuid
import hmac
import hashlib
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request, Header
from typing import Optional

import razorpay

from database import db
from services.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

razorpay_client = razorpay.Client(
    auth=(os.environ.get('RAZORPAY_KEY_ID', ''), os.environ.get('RAZORPAY_KEY_SECRET', ''))
)


@router.post("/payments/create-order")
async def create_razorpay_order(request: Request, authorization: Optional[str] = Header(None)):
    """Create Razorpay order for assignment payment"""
    user = await get_current_user(request, authorization)

    body = await request.json()
    assignment_id = body.get("assignment_id")

    if not assignment_id:
        raise HTTPException(status_code=400, detail="assignment_id required")

    assignment = await db.student_teacher_assignments.find_one(
        {"assignment_id": assignment_id, "student_id": user.user_id}, {"_id": 0}
    )
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    if assignment.get("payment_status") == "paid":
        raise HTTPException(status_code=400, detail="Already paid")

    # Use learning plan price or assignment credit_price
    amount = assignment.get("learning_plan_price") or assignment.get("credit_price", 0)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid payment amount")

    amount_paise = int(amount * 100)
    receipt_id = f"rcpt_{uuid.uuid4().hex[:12]}"

    try:
        order = razorpay_client.order.create({
            "amount": amount_paise,
            "currency": "INR",
            "receipt": receipt_id[:40],
            "payment_capture": 1,
            "notes": {
                "assignment_id": assignment_id,
                "student_id": user.user_id,
                "student_name": user.name,
                "learning_plan": assignment.get("learning_plan_name", "")
            }
        })
    except Exception as e:
        logger.error(f"Razorpay order creation failed: {e}")
        raise HTTPException(status_code=500, detail="Payment gateway error")

    # Store payment record
    payment_id = f"pay_{uuid.uuid4().hex[:12]}"
    await db.payment_transactions.insert_one({
        "payment_id": payment_id,
        "razorpay_order_id": order["id"],
        "assignment_id": assignment_id,
        "student_id": user.user_id,
        "student_name": user.name,
        "student_email": user.email,
        "teacher_name": assignment.get("teacher_name"),
        "learning_plan_name": assignment.get("learning_plan_name"),
        "amount": amount,
        "amount_paise": amount_paise,
        "currency": "INR",
        "receipt_id": receipt_id,
        "status": "created",
        "created_at": datetime.now(timezone.utc).isoformat()
    })

    return {
        "order_id": order["id"],
        "amount": amount_paise,
        "currency": "INR",
        "key_id": os.environ.get('RAZORPAY_KEY_ID', ''),
        "payment_id": payment_id,
        "student_name": user.name,
        "student_email": user.email
    }


@router.post("/payments/verify")
async def verify_razorpay_payment(request: Request, authorization: Optional[str] = Header(None)):
    """Verify Razorpay payment signature and activate assignment"""
    await get_current_user(request, authorization)  # Auth check

    body = await request.json()
    razorpay_order_id = body.get("razorpay_order_id")
    razorpay_payment_id = body.get("razorpay_payment_id")
    razorpay_signature = body.get("razorpay_signature")

    if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
        raise HTTPException(status_code=400, detail="Missing payment verification data")

    # Verify signature
    key_secret = os.environ.get('RAZORPAY_KEY_SECRET', '')
    generated_signature = hmac.new(
        key_secret.encode('utf-8'),
        f"{razorpay_order_id}|{razorpay_payment_id}".encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    if generated_signature != razorpay_signature:
        raise HTTPException(status_code=400, detail="Payment verification failed - invalid signature")

    # Find and update payment record
    payment = await db.payment_transactions.find_one(
        {"razorpay_order_id": razorpay_order_id}, {"_id": 0}
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Payment record not found")

    # Atomically update payment status (prevent double credit)
    result = await db.payment_transactions.update_one(
        {"razorpay_order_id": razorpay_order_id, "status": {"$ne": "paid"}},
        {"$set": {
            "status": "paid",
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature,
            "paid_at": datetime.now(timezone.utc).isoformat()
        }}
    )

    if result.modified_count > 0:
        # Update assignment payment_status to "paid"
        await db.student_teacher_assignments.update_one(
            {"assignment_id": payment["assignment_id"]},
            {"$set": {"payment_status": "paid", "paid_at": datetime.now(timezone.utc).isoformat()}}
        )
        logger.info(f"Payment verified: {razorpay_payment_id} for assignment {payment['assignment_id']}")

    return {
        "message": "Payment verified successfully!",
        "payment_id": payment["payment_id"],
        "receipt_id": payment["receipt_id"]
    }


@router.get("/payments/receipt/{payment_id}")
async def get_receipt(payment_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Get payment receipt details"""
    user = await get_current_user(request, authorization)

    query = {"payment_id": payment_id}
    if user.role not in ["admin", "counsellor"]:
        query["student_id"] = user.user_id

    payment = await db.payment_transactions.find_one(query, {"_id": 0})
    if not payment:
        raise HTTPException(status_code=404, detail="Receipt not found")

    # Get assignment details
    assignment = await db.student_teacher_assignments.find_one(
        {"assignment_id": payment.get("assignment_id")}, {"_id": 0}
    )

    return {
        "receipt_id": payment.get("receipt_id"),
        "payment_id": payment.get("payment_id"),
        "razorpay_payment_id": payment.get("razorpay_payment_id"),
        "student_name": payment.get("student_name"),
        "student_email": payment.get("student_email"),
        "teacher_name": payment.get("teacher_name"),
        "learning_plan_name": payment.get("learning_plan_name"),
        "amount": payment.get("amount"),
        "currency": payment.get("currency", "INR"),
        "status": payment.get("status"),
        "paid_at": payment.get("paid_at"),
        "created_at": payment.get("created_at"),
        "assignment_id": payment.get("assignment_id"),
        "teacher_name_assignment": assignment.get("teacher_name") if assignment else None,
    }


@router.get("/payments/my-payments")
async def get_my_payments(request: Request, authorization: Optional[str] = Header(None)):
    """Get current user's payment history"""
    user = await get_current_user(request, authorization)
    payments = await db.payment_transactions.find(
        {"student_id": user.user_id}, {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    return payments


@router.get("/admin/payments")
async def admin_payments(request: Request, authorization: Optional[str] = Header(None)):
    """Admin view of all payments with filters"""
    user = await get_current_user(request, authorization)
    if user.role not in ["admin"]:
        raise HTTPException(status_code=403, detail="Admin access only")

    # Parse query params
    params = dict(request.query_params)
    query = {}

    if params.get("student_name"):
        query["student_name"] = {"$regex": params["student_name"], "$options": "i"}
    if params.get("student_id"):
        query["student_id"] = params["student_id"]
    if params.get("status"):
        query["status"] = params["status"]

    date_from = params.get("date_from")
    date_to = params.get("date_to")
    if date_from or date_to:
        query["created_at"] = {}
        if date_from:
            query["created_at"]["$gte"] = date_from
        if date_to:
            query["created_at"]["$lte"] = date_to + "T23:59:59"
        if not query["created_at"]:
            del query["created_at"]

    payments = await db.payment_transactions.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)

    total_revenue = sum(p.get("amount", 0) for p in payments if p.get("status") == "paid")

    return {"payments": payments, "total_revenue": total_revenue, "count": len(payments)}


@router.post("/webhook/razorpay")
async def razorpay_webhook(request: Request):
    """Handle Razorpay webhooks"""
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")

    # Verify webhook signature if secret is configured
    webhook_secret = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "")
    if webhook_secret and signature:
        try:
            razorpay_client.utility.verify_webhook_signature(
                body.decode(), signature, webhook_secret
            )
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid webhook signature")

    import json
    payload = json.loads(body)
    event = payload.get("event", "")

    if event == "payment.captured":
        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        order_id = payment_entity.get("order_id")

        if order_id:
            result = await db.payment_transactions.update_one(
                {"razorpay_order_id": order_id, "status": {"$ne": "paid"}},
                {"$set": {
                    "status": "paid",
                    "razorpay_payment_id": payment_entity.get("id"),
                    "paid_at": datetime.now(timezone.utc).isoformat()
                }}
            )
            if result.modified_count > 0:
                payment = await db.payment_transactions.find_one({"razorpay_order_id": order_id}, {"_id": 0})
                if payment:
                    await db.student_teacher_assignments.update_one(
                        {"assignment_id": payment["assignment_id"]},
                        {"$set": {"payment_status": "paid", "paid_at": datetime.now(timezone.utc).isoformat()}}
                    )
                    logger.info(f"Webhook: Payment captured for order {order_id}")

    return {"received": True}
