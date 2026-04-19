"""Direct SIM/device verification endpoints."""

import re
import logging
from fastapi import APIRouter, HTTPException, Path

from ..services.camara import camara_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/verification", tags=["verification"])

PHONE_RE = re.compile(r"^\+[1-9]\d{6,14}$")


def _validate_phone(phone: str) -> str:
    phone = phone.strip()
    if not PHONE_RE.match(phone):
        raise HTTPException(status_code=400, detail="Invalid phone number format. Use E.164, e.g. +254712345678")
    return phone


@router.get("/sim-status/{phone_number}")
def check_sim_status(phone_number: str = Path(..., max_length=20)):
    """Quick SIM swap check for a phone number."""
    phone = _validate_phone(phone_number)
    sim_24h = camara_service.check_sim_swap(phone, max_age_hours=24)
    sim_7d = camara_service.check_sim_swap(phone, max_age_hours=168)
    return {
        "phone_number": phone,
        "sim_swap_24h": sim_24h,
        "sim_swap_7d": sim_7d,
        "risk_summary": "HIGH" if sim_24h.get("swapped") else
                        "MEDIUM" if sim_7d.get("swapped") else "LOW"
    }


@router.get("/device-status/{phone_number}")
def check_device_status(phone_number: str = Path(..., max_length=20)):
    """Quick device swap check for a phone number."""
    phone = _validate_phone(phone_number)
    device = camara_service.check_device_swap(phone, max_age_hours=240)
    return {
        "phone_number": phone,
        "device_swap": device,
        "risk_summary": "HIGH" if device.get("swapped") else "LOW"
    }


@router.get("/full-check/{phone_number}")
def full_check(phone_number: str = Path(..., max_length=20)):
    """Run all CAMARA checks for a phone number."""
    phone = _validate_phone(phone_number)
    results = camara_service.full_check(phone)
    any_risk = (
        results["sim_swap_24h"].get("swapped") or
        results["sim_swap_7d"].get("swapped") or
        results["device_swap"].get("swapped")
    )
    return {
        "phone_number": phone,
        "results": results,
        "overall_risk": "HIGH" if results["sim_swap_24h"].get("swapped") else
                        "MEDIUM" if any_risk else "LOW"
    }
