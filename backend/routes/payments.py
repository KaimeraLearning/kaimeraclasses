"""Stripe payment routes"""
import os
import uuid
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request, Header
from typing import Optional

from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionRequest, CheckoutSessionResponse, CheckoutStatusResponse

from database import db
from services.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

stripe_api_key = os.environ.get('STRIPE_API_KEY', '')

CREDIT_PACKAGES = {
    "small": {"credits": 10.0, "price": 10.0},
    "medium": {"credits": 25.0, "price": 20.0},
    "large": {"credits": 50.0, "price": 35.0}
}


@router.post("/payments/checkout")
async def create_checkout(package_id: str, origin_url: str, request: Request, authorization: Optional[str] = Header(None)):
    """Create Stripe checkout session for credits purchase"""
    user = await get_current_user(request, authorization)

    if package_id not in CREDIT_PACKAGES:
        raise HTTPException(status_code=400, detail="Invalid package")

    package = CREDIT_PACKAGES[package_id]
    success_url = f"{origin_url}/payment-success?session_id={{{{CHECKOUT_SESSION_ID}}}}"
    cancel_url = f"{origin_url}/browse-classes"

    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url=webhook_url)

    checkout_request = CheckoutSessionRequest(
        amount=package['price'], currency="usd",
        success_url=success_url, cancel_url=cancel_url,
        metadata={"user_id": user.user_id, "package_id": package_id, "credits": str(package['credits'])}
    )

    session: CheckoutSessionResponse = await stripe_checkout.create_checkout_session(checkout_request)

    payment_id = f"payment_{uuid.uuid4().hex[:12]}"
    await db.payment_transactions.insert_one({
        "payment_id": payment_id, "user_id": user.user_id, "session_id": session.session_id,
        "amount": package['price'], "currency": "usd", "payment_status": "pending", "status": "initiated",
        "metadata": {"package_id": package_id, "credits": package['credits']},
        "created_at": datetime.now(timezone.utc).isoformat(), "updated_at": datetime.now(timezone.utc).isoformat()
    })

    return {"url": session.url, "session_id": session.session_id}


@router.get("/payments/status/{session_id}")
async def get_payment_status(session_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Get payment status"""
    user = await get_current_user(request, authorization)

    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url=webhook_url)

    checkout_status: CheckoutStatusResponse = await stripe_checkout.get_checkout_status(session_id)
    payment_doc = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
    if not payment_doc:
        raise HTTPException(status_code=404, detail="Payment not found")

    if checkout_status.payment_status == "paid" and payment_doc['payment_status'] != "paid":
        credits = float(checkout_status.metadata.get('credits', 0))
        await db.users.update_one({"user_id": user.user_id}, {"$inc": {"credits": credits}})
        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {"$set": {"payment_status": "paid", "status": "completed", "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
        transaction_id = f"txn_{uuid.uuid4().hex[:12]}"
        await db.transactions.insert_one({
            "transaction_id": transaction_id, "user_id": user.user_id, "type": "purchase",
            "amount": credits, "description": f"Purchased {credits} credits",
            "status": "completed", "created_at": datetime.now(timezone.utc).isoformat()
        })

    return {
        "status": checkout_status.status, "payment_status": checkout_status.payment_status,
        "amount": checkout_status.amount_total / 100, "currency": checkout_status.currency
    }


@router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhooks - credits user account on successful payment"""
    body = await request.body()
    signature = request.headers.get("Stripe-Signature")

    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url=webhook_url)

    try:
        webhook_response = await stripe_checkout.handle_webhook(body, signature)

        payment_doc = await db.payment_transactions.find_one(
            {"session_id": webhook_response.session_id}, {"_id": 0}
        )

        await db.payment_transactions.update_one(
            {"session_id": webhook_response.session_id},
            {"$set": {
                "payment_status": webhook_response.payment_status,
                "status": "completed" if webhook_response.payment_status == "paid" else "pending",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )

        if webhook_response.payment_status == "paid" and payment_doc and payment_doc['payment_status'] != "paid":
            user_id = payment_doc.get('user_id')
            credits = float(payment_doc['metadata'].get('credits', 0))

            if user_id and credits > 0:
                await db.users.update_one({"user_id": user_id}, {"$inc": {"credits": credits}})
                transaction_id = f"txn_{uuid.uuid4().hex[:12]}"
                await db.transactions.insert_one({
                    "transaction_id": transaction_id, "user_id": user_id, "type": "purchase",
                    "amount": credits, "description": f"Purchased {credits} credits via Stripe",
                    "status": "completed", "created_at": datetime.now(timezone.utc).isoformat()
                })
                logger.info(f"Webhook: Credited {credits} to user {user_id}")

        return {"received": True}
    except Exception as e:
        logger.error(f"Stripe webhook error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
