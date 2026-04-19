import asyncio, random
from datetime import datetime
from fastapi import APIRouter
from ..websocket import manager

router = APIRouter(prefix="/api/demo", tags=["demo"])

PHONES = ["+254700000001", "+254711000002", "+254722000003"]

async def _run():
    for i in range(10):
        await asyncio.sleep(2)
        risk = random.randint(10, 95)
        decision = "BLOCK" if risk>=75 else "FLAG_FOR_REVIEW" if risk>=50 else "APPROVE"
        await manager.broadcast({
            "type": "transaction",
            "data": {
                "id": f"demo-{i}",
                "phone_number": random.choice(PHONES),
                "amount": random.randint(500, 50000),
                "currency": "KES",
                "status": "blocked" if decision=="BLOCK" else "flagged" if decision=="FLAG_FOR_REVIEW" else "approved",
                "risk_score": risk,
                "risk_level": "critical" if risk>=75 else "high" if risk>=50 else "low",
                "ai_decision": decision,
                "sim_swap": risk > 70,
                "device_swap": risk > 80,
                "risk_summary": f"Risk score {risk}/100",
                "recommended_actions": ["Verify identity"] if risk>50 else [],
                "created_at": datetime.utcnow().isoformat(),
            }
        })

@router.post("/start-stream")
async def start_stream():
    asyncio.create_task(_run())
    return {"status": "started", "transactions": 10}