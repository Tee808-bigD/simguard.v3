import re
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from ..models.transaction import TransactionType, TransactionStatus

PHONE_RE = re.compile(r"^\+[1-9]\d{6,14}$")

SUPPORTED_CURRENCIES = {
    "KES", "UGX", "TZS", "ZMW", "GHS", "NGN", "ZAR",
    "USD", "EUR", "GBP", "MWK", "MZN", "RWF", "ETB",
    "XOF", "XAF", "AOA", "MAD", "EGP"
}


class TransactionCreate(BaseModel):
    phone_number: str = Field(..., max_length=20)
    amount: float = Field(..., gt=0, le=10_000_000)
    currency: str = Field(default="KES", max_length=5)
    transaction_type: TransactionType
    recipient: Optional[str] = Field(default=None, max_length=100)
    agent_id: Optional[str] = Field(default=None, max_length=50)

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v = v.strip()
        if not PHONE_RE.match(v):
            raise ValueError("Phone must be E.164 format, e.g. +254712345678")
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        v = v.strip().upper()
        if v not in SUPPORTED_CURRENCIES:
            raise ValueError(f"Unsupported currency. Supported: {', '.join(sorted(SUPPORTED_CURRENCIES))}")
        return v

    @field_validator("recipient")
    @classmethod
    def sanitize_recipient(cls, v: Optional[str]) -> Optional[str]:
        if v:
            # Strip HTML-like tags
            v = re.sub(r"<[^>]+>", "", v).strip()
        return v or None


class TransactionResponse(BaseModel):
    id: int
    phone_number: str
    amount: float
    currency: str
    transaction_type: TransactionType
    recipient: Optional[str]
    status: TransactionStatus
    risk_score: int
    ai_decision: Optional[str]
    ai_explanation: Optional[str]
    camara_results: Optional[dict]
    created_at: datetime

    model_config = {"from_attributes": True}
