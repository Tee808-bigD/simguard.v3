from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from ..models.fraud_alert import AlertType, RiskLevel, ActionTaken


class FraudAlertResponse(BaseModel):
    id: int
    transaction_id: Optional[int]
    phone_number: str
    alert_type: AlertType
    risk_level: RiskLevel
    risk_score: int
    camara_checks: Optional[dict]
    ai_analysis: Optional[dict]
    action_taken: ActionTaken
    explanation: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
