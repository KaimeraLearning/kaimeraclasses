"""System repair / reconciliation tasks.

This module is the *single source of truth* for "fix existing data after a code
change" operations. It is invoked from the Admin → System Repair button.

Every task is:
  • idempotent (safe to re-run any number of times)
  • read-mostly except for surgical updates (no bulk deletes of user data)
  • additive when possible (e.g. backfill missing fields rather than rewriting)

Each task returns `{name, ok, count, message}`. The HTTP route aggregates them
into a report the admin sees in the UI.
"""
from datetime import datetime, timezone
from typing import Dict, Any, List

from database import db


async def _run(name: str, fn) -> Dict[str, Any]:
    try:
        result = await fn()
        return {"name": name, "ok": True, **result}
    except Exception as e:
        return {"name": name, "ok": False, "count": 0, "message": f"FAILED: {type(e).__name__}: {e}"}


# ─── Individual repair tasks ──────────────────────────────────────────────────

async def task_dedupe_demo_classes():
    """If multiple class_sessions exist for the same demo_id (caused by the
    pre-fix double-click bug), keep the EARLIEST and delete the rest.
    Only operates when the duplicate has no proofs / attendance / transactions
    against it (safety net — never removes a class that already has activity)."""
    pipeline = [
        {"$match": {"demo_id": {"$ne": None, "$exists": True}}},
        {"$group": {"_id": "$demo_id", "ids": {"$push": "$class_id"}, "count": {"$sum": 1}}},
        {"$match": {"count": {"$gt": 1}}},
    ]
    duplicates = await db.class_sessions.aggregate(pipeline).to_list(1000)
    deleted = 0
    skipped = 0
    for group in duplicates:
        # Keep earliest (sort ascending by created_at)
        classes = await db.class_sessions.find(
            {"class_id": {"$in": group["ids"]}}, {"_id": 0}
        ).sort("created_at", 1).to_list(100)
        if len(classes) <= 1:
            continue
        keep = classes[0]
        for dup in classes[1:]:
            cid = dup["class_id"]
            # Safety: skip if the dup has any proofs, transactions, or attendance
            has_activity = (
                await db.class_proofs.count_documents({"class_id": cid})
                or await db.transactions.count_documents({"class_id": cid})
                or await db.class_attendance.count_documents({"class_id": cid})
            )
            if has_activity:
                skipped += 1
                continue
            await db.class_sessions.delete_one({"class_id": cid})
            deleted += 1
        # Also make sure the kept class has the demo_id (idempotent)
        await db.class_sessions.update_one(
            {"class_id": keep["class_id"]},
            {"$set": {"demo_id": group["_id"]}}
        )
    msg = f"Removed {deleted} duplicate demo class(es)"
    if skipped:
        msg += f"; skipped {skipped} duplicate(s) that already have proofs/transactions/attendance (kept for audit)"
    return {"count": deleted, "message": msg}


async def task_unstick_demos():
    """Demos accidentally left in `processing` status (e.g. server crashed mid-flow)
    are reverted to `pending` so they can be retried by teacher/counselor."""
    res = await db.demo_requests.update_many(
        {"status": "processing"},
        {"$set": {"status": "pending"}}
    )
    return {"count": res.modified_count, "message": f"Reverted {res.modified_count} stuck demo(s) from 'processing' → 'pending'"}


async def task_link_demos_to_classes():
    """Backfill `demo_id` on class_sessions for old demo classes that were created
    before the back-link existed.

    Strategy:
      1. For demos with status=accepted and a stored class_id, set demo_id on that class.
      2. ALSO scan title-matched demo classes that share the same teacher+date+student
         as an accepted demo and link them too (covers double-class duplicates from
         the pre-fix bug)."""
    fixed = 0

    # Step 1: link via stored class_id (1:1 mapping)
    demos = await db.demo_requests.find(
        {"status": "accepted", "class_id": {"$exists": True}},
        {"_id": 0, "demo_id": 1, "class_id": 1, "name": 1, "preferred_date": 1,
         "accepted_by_teacher_id": 1, "student_user_id": 1}
    ).to_list(5000)

    for d in demos:
        if not d.get("class_id") or not d.get("demo_id"):
            continue
        # Primary class
        res = await db.class_sessions.update_one(
            {"class_id": d["class_id"], "$or": [{"demo_id": {"$exists": False}}, {"demo_id": None}]},
            {"$set": {"demo_id": d["demo_id"]}}
        )
        if res.modified_count:
            fixed += 1
        # Step 2: hunt other demo-flavor classes for this same student+teacher+date
        # (these are the duplicates). Only match classes that don't already belong
        # to a different demo.
        if d.get("student_user_id") and d.get("accepted_by_teacher_id"):
            res2 = await db.class_sessions.update_many(
                {
                    "title": {"$regex": "^Demo Session", "$options": "i"},
                    "teacher_id": d["accepted_by_teacher_id"],
                    "assigned_student_id": d["student_user_id"],
                    "date": d.get("preferred_date"),
                    "$or": [{"demo_id": {"$exists": False}}, {"demo_id": None}],
                },
                {"$set": {"demo_id": d["demo_id"]}}
            )
            fixed += res2.modified_count

    return {"count": fixed, "message": f"Back-linked {fixed} class(es) to their demo_id"}


async def task_verify_admin_created_users():
    """Old admin-created users were stored as `is_verified=False`, which now
    breaks their login. Mark every user who has a password_hash AND was not
    self-registered as verified (admin sent them their credentials by email,
    so the email is already proven)."""
    res = await db.users.update_many(
        {
            "password_hash": {"$exists": True, "$ne": None, "$ne": ""},
            "is_verified": False,
        },
        {"$set": {"is_verified": True}}
    )
    return {"count": res.modified_count, "message": f"Marked {res.modified_count} admin-created user(s) as verified"}


async def task_force_password_change_for_unflagged():
    """Users with a password_hash but no `must_change_password` field at all are
    legacy accounts. We do NOT force them to change (could be people who already
    set a real password). The flag stays default-False — owner can still change
    via Profile any time."""
    res = await db.users.update_many(
        {"must_change_password": {"$exists": False}},
        {"$set": {"must_change_password": False}}
    )
    return {"count": res.modified_count, "message": f"Initialized must_change_password=False on {res.modified_count} legacy account(s)"}


async def task_normalize_transaction_signs():
    """Legacy transactions stored deductions as positive amounts (e.g. type='booking').
    Convert these to negative so the wallet UI shows red minus signs correctly.
    Idempotent: each row is only flipped if amount > 0 AND type ∈ outflow set."""
    OUTFLOW_TYPES = ["booking", "demo_booking", "class_booking", "class_purchase",
                     "assignment_payment", "credit_deduct", "debit",
                     "payout_to_teacher", "admin_payout", "refund_issued"]
    flipped = 0
    cursor = db.transactions.find(
        {"type": {"$in": OUTFLOW_TYPES}, "amount": {"$gt": 0}},
        {"_id": 0, "transaction_id": 1, "amount": 1}
    )
    async for t in cursor:
        await db.transactions.update_one(
            {"transaction_id": t["transaction_id"]},
            {"$set": {"amount": -abs(t["amount"])}}
        )
        flipped += 1
    return {"count": flipped, "message": f"Flipped {flipped} legacy outflow transaction(s) from + to −"}


async def task_backfill_class_demo_flag():
    """Older demo classes had `is_demo` missing; set it to True for any class
    whose title starts with 'Demo Session' or has demo_id populated."""
    res = await db.class_sessions.update_many(
        {
            "$and": [
                {"is_demo": {"$ne": True}},
                {"$or": [
                    {"demo_id": {"$exists": True, "$ne": None}},
                    {"title": {"$regex": "^Demo Session", "$options": "i"}},
                ]},
            ]
        },
        {"$set": {"is_demo": True}}
    )
    return {"count": res.modified_count, "message": f"Marked {res.modified_count} legacy class(es) as is_demo=True"}


async def task_clear_orphan_processing_classes():
    """Classes created during a failed demo-accept (pre-fix) where the demo is
    still in `pending` and the class has no activity at all."""
    pending_demos = [d["demo_id"] for d in await db.demo_requests.find(
        {"status": "pending"}, {"_id": 0, "demo_id": 1}
    ).to_list(5000)]
    if not pending_demos:
        return {"count": 0, "message": "No pending demos found — nothing to repair"}

    deleted = 0
    cursor = db.class_sessions.find(
        {"demo_id": {"$in": pending_demos}},
        {"_id": 0, "class_id": 1}
    )
    async for c in cursor:
        cid = c["class_id"]
        has_activity = (
            await db.class_proofs.count_documents({"class_id": cid})
            or await db.transactions.count_documents({"class_id": cid})
            or await db.class_attendance.count_documents({"class_id": cid})
        )
        if has_activity:
            continue
        await db.class_sessions.delete_one({"class_id": cid})
        deleted += 1
    return {"count": deleted, "message": f"Removed {deleted} orphan class(es) whose demo is still pending"}


async def task_set_default_credits():
    """Initialize `credits: 0` on any user document where the field is missing."""
    res = await db.users.update_many(
        {"credits": {"$exists": False}},
        {"$set": {"credits": 0.0}}
    )
    return {"count": res.modified_count, "message": f"Initialized credits=0 on {res.modified_count} user(s)"}


async def task_invalidate_caches():
    """Reset in-memory caches so admin sees the latest after running repairs."""
    try:
        from services.email_templates import invalidate_template_cache
        invalidate_template_cache()
    except Exception:
        pass
    try:
        from services.helpers import invalidate_email_config_cache
        invalidate_email_config_cache()
    except Exception:
        pass
    return {"count": 0, "message": "Cleared in-memory caches"}


# ─── Public entry point ───────────────────────────────────────────────────────

async def run_all_repairs() -> List[Dict[str, Any]]:
    """Run every repair task in order. Each task is wrapped so a single failure
    won't abort the rest. Returns a flat list of per-task reports."""
    tasks = [
        ("Unstick demos in 'processing'", task_unstick_demos),
        ("Backfill demo→class back-links", task_link_demos_to_classes),
        ("Remove duplicate demo classes", task_dedupe_demo_classes),
        ("Clear orphan classes (failed demo accepts)", task_clear_orphan_processing_classes),
        ("Mark legacy classes as is_demo", task_backfill_class_demo_flag),
        ("Verify admin-created users (fixes login)", task_verify_admin_created_users),
        ("Initialize must_change_password on legacy users", task_force_password_change_for_unflagged),
        ("Initialize credits=0 on legacy users", task_set_default_credits),
        ("Normalize transaction signs (legacy outflows)", task_normalize_transaction_signs),
        ("Invalidate in-memory caches", task_invalidate_caches),
    ]
    out: List[Dict[str, Any]] = []
    for name, fn in tasks:
        out.append(await _run(name, fn))
    return out

