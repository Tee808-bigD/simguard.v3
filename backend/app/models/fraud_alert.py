import enum
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, Enum, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column
from ..database import Base


class AlertType(str, enum.Enum):
    SIM_SWAP = "sim_swap"
    DEVICE_SWAP = "device_swap"
    NUMBER_MISMATCH = "number_mismatch"
    COMPOSITE = "composite"
    HIGH_VALUE = "high_value"


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ActionTaken(str, enum.Enum):
    APPROVED = "approved"
    BLOCKED = "blocked"
    FLAGGED = "flagged"


class FraudAlert(Base):
    __tablename__ = "fraud_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    transaction_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    phone_number: Mapped[str] = mapped_column(String(20), index=True)
    alert_type: Mapped[str] = mapped_column(Enum(AlertType))
    risk_level: Mapped[str] = mapped_column(Enum(RiskLevel))
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    camara_checks: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ai_analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    action_taken: Mapped[str] = mapped_column(Enum(ActionTaken))
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
