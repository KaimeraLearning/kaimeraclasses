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
from services.helpers import insert_admin_mirror_txn

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


@router.post("/payments/pay-from-wallet")
async def pay_from_wallet(request: Request, authorization: Optional[str] = Header(None)):
    """Pay for assignment using wallet credits instead of Razorpay"""
    user = await get_current_user(request, authorization)
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Student access only")

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

    amount = assignment.get("learning_plan_price") or assignment.get("credit_price", 0)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid payment amount")

    # Check wallet balance
    student = await db.users.find_one({"user_id": user.user_id}, {"_id": 0})
    if student.get("credits", 0) < amount:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient wallet balance. Required: Rs.{amount}, Available: Rs.{student.get('credits', 0)}"
        )

    # Deduct from wallet
    await db.users.update_one({"user_id": user.user_id}, {"$inc": {"credits": -amount}})

    # Record transaction
    payment_id = f"pay_{uuid.uuid4().hex[:12]}"
    receipt_id = f"rcpt_{uuid.uuid4().hex[:12]}"
    await db.payment_transactions.insert_one({
        "payment_id": payment_id,
        "assignment_id": assignment_id,
        "student_id": user.user_id,
        "student_name": user.name,
        "student_email": user.email,
        "teacher_name": assignment.get("teacher_name"),
        "learning_plan_name": assignment.get("learning_plan_name"),
        "amount": amount,
        "amount_paise": int(amount * 100),
        "currency": "INR",
        "receipt_id": receipt_id,
        "status": "paid",
        "payment_method": "wallet",
        "paid_at": datetime.now(timezone.utc).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    })

    await db.transactions.insert_one({
        "transaction_id": f"txn_{uuid.uuid4().hex[:12]}",
        "user_id": user.user_id, "type": "assignment_payment",
        "amount": -amount,
        "description": f"Assignment payment (wallet): {assignment.get('learning_plan_name', 'Standard')} with {assignment.get('teacher_name')}",
        "assignment_id": assignment_id,
        "payment_id": payment_id,
        "counterparty_user_id": assignment.get('teacher_id'),
        "status": "completed", "created_at": datetime.now(timezone.utc).isoformat()
    })
    # Mirror: platform receives the wallet-payment
    await insert_admin_mirror_txn(
        amount=amount,
        description=f"Assignment payment received from {user.name}: {assignment.get('learning_plan_name', 'Standard')}",
        txn_type="assignment_payment_received",
        assignment_id=assignment_id,
        payment_id=payment_id,
        counterparty_user_id=user.user_id
    )

    # Mark assignment as paid
    await db.student_teacher_assignments.update_one(
        {"assignment_id": assignment_id},
        {"$set": {"payment_status": "paid", "payment_method": "wallet", "paid_at": datetime.now(timezone.utc).isoformat()}}
    )

    return {"message": "Payment successful from wallet!", "payment_id": payment_id, "receipt_id": receipt_id}



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


RECHARGE_PACKAGES = {
    "pack_2000": {"credits": 2000, "amount": 2000, "label": "2,000"},
    "pack_5000": {"credits": 5000, "amount": 5000, "label": "5,000"},
    "pack_10000": {"credits": 10000, "amount": 10000, "label": "10,000"},
}


@router.post("/payments/recharge")
async def create_recharge_order(request: Request, authorization: Optional[str] = Header(None)):
    """Create Razorpay order for credit recharge.
    Accepts EITHER:
      - package_id: one of RECHARGE_PACKAGES keys (uses fixed credits/amount mapping), OR
      - custom_amount: any positive integer rupees (1:1 credits-to-rupee).
    """
    user = await get_current_user(request, authorization)

    body = await request.json()
    package_id = body.get("package_id")
    custom_amount = body.get("custom_amount") or body.get("amount")

    if package_id and package_id in RECHARGE_PACKAGES:
        pkg = RECHARGE_PACKAGES[package_id]
        amount = float(pkg["amount"])
        credits = int(pkg["credits"])
    else:
        # Custom amount path — package_id may be 'custom' or anything; we use custom_amount.
        try:
            amount = float(custom_amount) if custom_amount is not None else 0.0
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Invalid amount")
        if amount < 1:
            raise HTTPException(status_code=400, detail="Minimum recharge amount is ₹1")
        if amount > 1_000_000:
            raise HTTPException(status_code=400, detail="Maximum recharge is ₹10,00,000 per transaction")
        credits = int(amount)  # 1:1 credits per rupee

    amount_paise = int(amount * 100)
    receipt_id = f"rch_{uuid.uuid4().hex[:12]}"

    try:
        order = razorpay_client.order.create({
            "amount": amount_paise,
            "currency": "INR",
            "receipt": receipt_id[:40],
            "payment_capture": 1,
            "notes": {
                "type": "recharge",
                "student_id": user.user_id,
                "student_name": user.name,
                "credits": credits
            }
        })
    except Exception as e:
        logger.error(f"Razorpay recharge order failed: {e}")
        raise HTTPException(status_code=500, detail="Payment gateway error")

    await db.payment_transactions.insert_one({
        "payment_id": f"pay_{uuid.uuid4().hex[:12]}",
        "razorpay_order_id": order["id"],
        "type": "recharge",
        "student_id": user.user_id,
        "student_name": user.name,
        "student_email": user.email,
        "amount": amount,
        "credits": credits,
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
        "student_name": user.name,
        "student_email": user.email
    }


@router.post("/payments/verify-recharge")
async def verify_recharge(request: Request, authorization: Optional[str] = Header(None)):
    """Verify Razorpay recharge payment and add credits"""
    user = await get_current_user(request, authorization)

    body = await request.json()
    razorpay_order_id = body.get("razorpay_order_id")
    razorpay_payment_id = body.get("razorpay_payment_id")
    razorpay_signature = body.get("razorpay_signature")

    if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
        raise HTTPException(status_code=400, detail="Missing payment data")

    key_secret = os.environ.get('RAZORPAY_KEY_SECRET', '')
    generated_signature = hmac.new(
        key_secret.encode('utf-8'),
        f"{razorpay_order_id}|{razorpay_payment_id}".encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    if generated_signature != razorpay_signature:
        raise HTTPException(status_code=400, detail="Invalid signature")

    payment = await db.payment_transactions.find_one(
        {"razorpay_order_id": razorpay_order_id, "type": "recharge"}, {"_id": 0}
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

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
        credits_to_add = payment.get("credits", 0)
        recharge_payment_id = payment.get("payment_id")
        await db.users.update_one(
            {"user_id": user.user_id},
            {"$inc": {"credits": credits_to_add}}
        )
        # Record transaction
        await db.transactions.insert_one({
            "transaction_id": f"txn_{uuid.uuid4().hex[:12]}",
            "user_id": user.user_id,
            "type": "recharge",
            "amount": credits_to_add,
            "description": f"Recharged {credits_to_add} credits via Razorpay",
            "payment_id": recharge_payment_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        # Mirror: platform received the rupee inflow via Razorpay
        await insert_admin_mirror_txn(
            amount=credits_to_add,
            description=f"Wallet recharge received via Razorpay from {user.name} (+{credits_to_add} credits)",
            txn_type="recharge_received",
            payment_id=recharge_payment_id,
            counterparty_user_id=user.user_id
        )

    return {"message": f"Recharged {payment.get('credits', 0)} credits!", "credits_added": payment.get("credits", 0)}


@router.get("/payments/receipt-pdf/{payment_id}")
async def download_receipt_pdf(payment_id: str, request: Request, authorization: Optional[str] = Header(None), token: Optional[str] = None):
    """Generate and return a PDF receipt"""
    from fpdf import FPDF
    from fastapi.responses import Response as FastAPIResponse

    # Support token via query param for download-in-new-tab
    if token and not authorization:
        authorization = f"Bearer {token}"
    user = await get_current_user(request, authorization)

    query = {"payment_id": payment_id}
    if user.role not in ["admin", "counsellor"]:
        query["student_id"] = user.user_id

    payment = await db.payment_transactions.find_one(query, {"_id": 0})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Header
    pdf.set_fill_color(14, 165, 233)
    pdf.rect(0, 0, 210, 45, 'F')
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_y(10)
    pdf.cell(0, 12, "Kaimera Learning", ln=True, align="C")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, "Payment Receipt", ln=True, align="C")

    # Body
    pdf.set_text_color(30, 41, 59)
    pdf.ln(15)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, f"Receipt: {payment.get('receipt_id', 'N/A')}", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.ln(3)

    fields = [
        ("Date", payment.get("paid_at", payment.get("created_at", "N/A"))[:10] if payment.get("paid_at") or payment.get("created_at") else "N/A"),
        ("Student Name", payment.get("student_name", "N/A")),
        ("Student Email", payment.get("student_email", "N/A")),
        ("Payment Type", payment.get("type", "assignment").title()),
    ]

    if payment.get("teacher_name"):
        fields.append(("Teacher", payment["teacher_name"]))
    if payment.get("learning_plan_name"):
        fields.append(("Learning Plan", payment["learning_plan_name"]))
    if payment.get("credits"):
        fields.append(("Credits", str(payment["credits"])))

    fields.extend([
        ("Amount", f"INR {payment.get('amount', 0):,.2f}"),
        ("Status", payment.get("status", "N/A").upper()),
        ("Razorpay Payment ID", payment.get("razorpay_payment_id", "N/A")),
    ])

    for label, value in fields:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(60, 8, label, border=0)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 8, str(value), ln=True)

    pdf.ln(10)
    pdf.set_draw_color(226, 232, 240)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(0, 6, "This is a computer-generated receipt. No signature required.", ln=True, align="C")
    pdf.cell(0, 6, f"Generated on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}", ln=True, align="C")

    pdf_bytes = pdf.output()

    return FastAPIResponse(
        content=bytes(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=receipt_{payment.get('receipt_id','')}.pdf"}
    )
