"""Dashboard statistics and timeline endpoints."""

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.transaction import Transaction, TransactionStatus
from ..models.fraud_alert import FraudAlert, RiskLevel

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Aggregate KPI stats for the dashboard."""
    total = db.query(func.count(Transaction.id)).scalar() or 0
    blocked = db.query(func.count(Transaction.id)).filter(
        Transaction.status == TransactionStatus.BLOCKED
    ).scalar() or 0
    flagged = db.query(func.count(Transaction.id)).filter(
        Transaction.status == TransactionStatus.FLAGGED
    ).scalar() or 0
    approved = db.query(func.count(Transaction.id)).filter(
        Transaction.status == TransactionStatus.APPROVED
    ).scalar() or 0

    total_amount_blocked = db.query(func.sum(Transaction.amount)).filter(
        Transaction.status == TransactionStatus.BLOCKED
    ).scalar() or 0

    # Last 24h
    since_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    recent_blocked = db.query(func.count(Transaction.id)).filter(
        Transaction.status == TransactionStatus.BLOCKED,
        Transaction.created_at >= since_24h,
    ).scalar() or 0

    # Critical alerts
    critical_alerts = db.query(func.count(FraudAlert.id)).filter(
        FraudAlert.risk_level == RiskLevel.CRITICAL
    ).scalar() or 0

    approval_rate = round((approved / total * 100), 1) if total > 0 else 0
    block_rate = round((blocked / total * 100), 1) if total > 0 else 0

    return {
        "total_transactions": total,
        "total_blocked": blocked,
        "total_flagged": flagged,
        "total_approved": approved,
        "approval_rate": approval_rate,
        "block_rate": block_rate,
        "total_amount_blocked": round(total_amount_blocked, 2),
        "recent_blocked_24h": recent_blocked,
        "critical_alerts": critical_alerts,
    }


@router.get("/timeline")
def get_timeline(
    db: Session = Depends(get_db),
    hours: int = 24,
):
    """Hourly transaction counts for the last N hours, broken down by status."""
    hours = min(hours, 168)  # max 7 days
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    transactions = db.query(Transaction).filter(
        Transaction.created_at >= since
    ).order_by(Transaction.created_at).all()

    # Build hourly buckets
    buckets: dict[str, dict] = {}
    now = datetime.now(timezone.utc)
    for h in range(hours, 0, -1):
        bucket_time = now - timedelta(hours=h)
        key = bucket_time.strftime("%Y-%m-%dT%H:00")
        buckets[key] = {"time": key, "approved": 0, "blocked": 0, "flagged": 0, "total": 0}

    for txn in transactions:
        key = txn.created_at.strftime("%Y-%m-%dT%H:00")
        if key not in buckets:
            buckets[key] = {"time": key, "approved": 0, "blocked": 0, "flagged": 0, "total": 0}
        buckets[key][txn.status] = buckets[key].get(txn.status, 0) + 1
        buckets[key]["total"] += 1

    return list(buckets.values())


@router.get("/risk-distribution")
def get_risk_distribution(db: Session = Depends(get_db)):
    """Distribution of transactions by risk level."""
    rows = db.query(
        Transaction.risk_score,
        Transaction.status
    ).all()

    distribution = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    for score, _ in rows:
        if score < 26:
            distribution["low"] += 1
        elif score < 51:
            distribution["medium"] += 1
        elif score < 75:
            distribution["high"] += 1
        else:
            distribution["critical"] += 1

    return distribution
