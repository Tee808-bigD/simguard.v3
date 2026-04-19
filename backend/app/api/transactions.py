"""Transaction API endpoints — submit and retrieve transactions."""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.transaction import Transaction, TransactionStatus
from ..models.fraud_alert import FraudAlert, ActionTaken
from ..schemas.transaction import TransactionCreate, TransactionResponse
from ..schemas.fraud_alert import FraudAlertResponse
from ..services.camara import camara_service
from ..services.fraud_detector import compute_risk_score, determine_alert_type
from ..services.ai_engine import analyze_fraud_risk
from ..websocket import ws_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.post("", response_model=TransactionResponse, status_code=201)
async def create_transaction(
    payload: TransactionCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    """Submit a transaction for real-time fraud analysis."""

    # 1. CAMARA checks
    camara_results = camara_service.full_check(payload.phone_number)

    # 2. Rule-based scoring
    risk_score, risk_level, reasons = compute_risk_score(
        phone_number=payload.phone_number,
        amount=payload.amount,
        currency=payload.currency,
        recipient=payload.recipient,
        camara_results=camara_results,
    )

    # 3. AI decision
    ai_result = analyze_fraud_risk(
        phone_number=payload.phone_number,
        amount=payload.amount,
        currency=payload.currency,
        transaction_type=payload.transaction_type.value,
        recipient=payload.recipient,
        camara_results=camara_results,
        risk_score=risk_score,
        risk_level=risk_level,
        reasons=reasons,
    )

    # 4. Map AI decision to status
    decision = ai_result.get("decision", "FLAG_FOR_REVIEW")
    status_map = {
        "BLOCK": TransactionStatus.BLOCKED,
        "APPROVE": TransactionStatus.APPROVED,
        "FLAG_FOR_REVIEW": TransactionStatus.FLAGGED,
    }
    status = status_map.get(decision, TransactionStatus.FLAGGED)

    # 5. Persist transaction
    txn = Transaction(
        phone_number=payload.phone_number,
        amount=payload.amount,
        currency=payload.currency,
        transaction_type=payload.transaction_type,
        recipient=payload.recipient,
        status=status,
        risk_score=risk_score,
        ai_decision=decision,
        ai_explanation=ai_result.get("detailed_explanation"),
        camara_results=camara_results,
    )
    db.add(txn)
    db.flush()

    # 6. Persist fraud alert if risk >= medium
    if risk_score >= 26 or status in (TransactionStatus.BLOCKED, TransactionStatus.FLAGGED):
        action_map = {
            TransactionStatus.BLOCKED: ActionTaken.BLOCKED,
            TransactionStatus.FLAGGED: ActionTaken.FLAGGED,
            TransactionStatus.APPROVED: ActionTaken.APPROVED,
        }
        alert = FraudAlert(
            transaction_id=txn.id,
            phone_number=payload.phone_number,
            alert_type=determine_alert_type(camara_results),
            risk_level=risk_level,
            risk_score=risk_score,
            camara_checks=camara_results,
            ai_analysis=ai_result,
            action_taken=action_map.get(status, ActionTaken.FLAGGED),
            explanation=ai_result.get("primary_reason"),
        )
        db.add(alert)

    db.commit()
    db.refresh(txn)

    # 7. Broadcast to dashboard via WebSocket
    await ws_manager.broadcast({
        "type": "transaction",
        "data": {
            "id": txn.id,
            "phone_number": txn.phone_number,
            "amount": txn.amount,
            "currency": txn.currency,
            "status": txn.status,
            "risk_score": txn.risk_score,
            "ai_decision": txn.ai_decision,
            "ai_explanation": txn.ai_explanation,
            "primary_reason": ai_result.get("primary_reason"),
            "recommended_actions": ai_result.get("recommended_actions", []),
            "fraud_pattern": ai_result.get("fraud_pattern"),
            "camara_results": camara_results,
            "created_at": txn.created_at.isoformat(),
        }
    })

    return txn


@router.get("", response_model=list[TransactionResponse])
def list_transactions(
    db: Session = Depends(get_db),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    status: Optional[str] = Query(default=None),
    phone: Optional[str] = Query(default=None),
):
    """List transactions with optional filters."""
    q = db.query(Transaction)
    if status:
        q = q.filter(Transaction.status == status)
    if phone:
        # Validate phone before using in query
        import re
        if not re.match(r"^\+[1-9]\d{6,14}$", phone):
            raise HTTPException(status_code=400, detail="Invalid phone format")
        q = q.filter(Transaction.phone_number == phone)
    transactions = q.order_by(Transaction.created_at.desc()).offset(offset).limit(limit).all()
    return transactions


@router.get("/{txn_id}", response_model=TransactionResponse)
def get_transaction(txn_id: int, db: Session = Depends(get_db)):
    """Get a single transaction by ID."""
    txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return txn
