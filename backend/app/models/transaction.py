import enum
from datetime import datetime, timezone
from sqlalchemy import String, Float, Integer, DateTime, Enum, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column
from ..database import Base


class TransactionType(str, enum.Enum):
    SEND = "send"
    RECEIVE = "receive"
    WITHDRAW = "withdraw"
    DEPOSIT = "deposit"


class TransactionStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    BLOCKED = "blocked"
    FLAGGED = "flagged"


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    phone_number: Mapped[str] = mapped_column(String(20), index=True)
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(10), default="KES")
    transaction_type: Mapped[str] = mapped_column(Enum(TransactionType))
    recipient: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(Enum(TransactionStatus), default=TransactionStatus.PENDING)
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    ai_decision: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ai_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    camara_results: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
