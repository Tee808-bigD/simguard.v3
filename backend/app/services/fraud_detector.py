"""Rule-based fraud detection engine.

Computes a risk score (0-100) based on CAMARA results and transaction patterns.
This score is passed to the Claude AI engine for contextual analysis.
"""

import logging

logger = logging.getLogger(__name__)

# Score thresholds → risk levels
RISK_LEVELS = {
    "low": (0, 25),
    "medium": (26, 50),
    "high": (51, 74),
    "critical": (75, 100),
}


def compute_risk_score(
    phone_number: str,
    amount: float,
    currency: str,
    recipient: str | None,
    camara_results: dict,
) -> tuple[int, str, list[str]]:
    """
    Returns (score: int, risk_level: str, reasons: list[str])
    score is capped at 100.
    """
    score = 0
    reasons = []

    sim_24h = camara_results.get("sim_swap_24h", {})
    sim_7d = camara_results.get("sim_swap_7d", {})
    device = camara_results.get("device_swap", {})

    # ── CAMARA signals (highest weight) ──────────────────────────
    if sim_24h.get("swapped"):
        score += 60
        reasons.append("SIM swap detected within last 24 hours — critical fraud indicator")

    elif sim_7d.get("swapped"):
        score += 40
        reasons.append("SIM swap detected within last 7 days")

    if device.get("swapped"):
        score += 30
        reasons.append("Device swap detected — SIM moved to new handset")

    # ── Transaction amount risk ───────────────────────────────────
    # Normalise to USD equivalent (rough rates for scoring only)
    usd_rates = {
        "KES": 0.0077, "UGX": 0.00027, "TZS": 0.00039, "ZMW": 0.056,
        "GHS": 0.062, "NGN": 0.00063, "ZAR": 0.055, "USD": 1.0,
        "EUR": 1.09, "GBP": 1.27, "MWK": 0.00058, "MZN": 0.016,
        "RWF": 0.00073, "ETB": 0.018, "XOF": 0.0017, "XAF": 0.0017,
        "AOA": 0.0011, "MAD": 0.10, "EGP": 0.020,
    }
    rate = usd_rates.get(currency.upper(), 1.0)
    usd_amount = amount * rate

    if usd_amount > 1000:
        score += 30
        reasons.append(f"Very high transaction value (~${usd_amount:,.0f} USD)")
    elif usd_amount > 500:
        score += 20
        reasons.append(f"High transaction value (~${usd_amount:,.0f} USD)")
    elif usd_amount > 200:
        score += 10
        reasons.append(f"Above-average transaction value (~${usd_amount:,.0f} USD)")

    # ── Composite risk bonuses ────────────────────────────────────
    if sim_24h.get("swapped") and usd_amount > 200:
        score += 25
        reasons.append("COMPOSITE: Recent SIM swap + high-value transaction (classic drain attack)")

    if (sim_24h.get("swapped") or sim_7d.get("swapped")) and recipient:
        score += 20
        reasons.append("COMPOSITE: SIM swap + transfer to new recipient")

    if sim_24h.get("swapped") and device.get("swapped"):
        score += 15
        reasons.append("COMPOSITE: Both SIM and device swapped — coordinated attack pattern")

    # Cap score
    score = min(score, 100)

    # Determine risk level
    risk_level = "low"
    for level, (lo, hi) in RISK_LEVELS.items():
        if lo <= score <= hi:
            risk_level = level
            break

    return score, risk_level, reasons


def determine_alert_type(camara_results: dict) -> str:
    """Determine the primary alert type from CAMARA results."""
    sim_24h = camara_results.get("sim_swap_24h", {}).get("swapped", False)
    sim_7d = camara_results.get("sim_swap_7d", {}).get("swapped", False)
    device = camara_results.get("device_swap", {}).get("swapped", False)

    flags = sum([bool(sim_24h or sim_7d), bool(device)])

    if flags >= 2:
        return "composite"
    if sim_24h or sim_7d:
        return "sim_swap"
    if device:
        return "device_swap"
    return "high_value"
