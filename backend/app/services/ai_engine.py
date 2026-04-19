"""Claude Agentic AI Engine — the core differentiator of SimGuard.

Receives transaction details + CAMARA results + rule-based score,
and makes an autonomous fraud decision with human-readable explanation.
"""

import json
import logging
from typing import Optional
from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

SYSTEM_PROMPT = """You are SimGuard AI, an expert fraud detection system specializing in
SIM swap fraud prevention for African mobile money networks (M-Pesa, MTN MoMo, Airtel Money, etc.).

You have deep knowledge of:
- SIM swap fraud patterns: attackers obtain a duplicate SIM, intercept OTPs, drain mobile wallets
- Device swap fraud: victim's number ported to attacker's handset
- African mobile money fraud peaks: month-end (salary day), market days, festive seasons
- Agent collusion patterns: agents processing suspicious transactions for commission
- Velocity attacks: multiple small transactions to avoid detection
- Social engineering: fraudsters calling MNOs impersonating victims

Your job is to analyze transaction data + Nokia CAMARA API results and make a decision.

Always respond in valid JSON with this exact structure:
{
  "decision": "BLOCK" | "APPROVE" | "FLAG_FOR_REVIEW",
  "confidence": 0-100,
  "primary_reason": "one-sentence summary for the agent",
  "detailed_explanation": "2-3 sentence explanation suitable for a mobile money agent",
  "recommended_actions": ["action1", "action2"],
  "fraud_pattern": "sim_swap_drain" | "device_takeover" | "high_value_suspicious" | "normal" | "coordinated_attack"
}

Decision thresholds:
- BLOCK: risk_score >= 60 OR (SIM swap in last 24h AND amount > $100 equivalent)
- FLAG_FOR_REVIEW: risk_score 30-59 OR SIM swap in last 7 days
- APPROVE: risk_score < 30 AND no recent SIM swap signals

Be decisive. Mobile agents need clear guidance instantly."""


def analyze_fraud_risk(
    phone_number: str,
    amount: float,
    currency: str,
    transaction_type: str,
    recipient: Optional[str],
    camara_results: dict,
    risk_score: int,
    risk_level: str,
    reasons: list[str],
) -> dict:
    """Call Claude to analyze fraud risk and make a decision.

    Falls back to rule-based decision if API key is missing or call fails.
    """
    if not settings.anthropic_api_key or settings.anthropic_api_key.startswith("sk-ant-your"):
        logger.warning("ANTHROPIC_API_KEY not configured — using rule-based fallback")
        return _rule_based_fallback(risk_score, risk_level, reasons, camara_results)

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

        user_message = f"""Analyze this mobile money transaction for fraud:

TRANSACTION:
- Phone: {phone_number}
- Amount: {amount} {currency}
- Type: {transaction_type}
- Recipient: {recipient or 'N/A'}

CAMARA API RESULTS:
{json.dumps(camara_results, indent=2)}

RULE-BASED SCORING:
- Risk score: {risk_score}/100
- Risk level: {risk_level}
- Detected signals: {chr(10).join(f'  • {r}' for r in reasons) if reasons else '  • None'}

Make your fraud decision now."""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=600,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}]
        )

        raw = response.content[0].text.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw.strip())

        # Validate required fields
        required = {"decision", "confidence", "primary_reason", "detailed_explanation",
                    "recommended_actions", "fraud_pattern"}
        if not required.issubset(result.keys()):
            raise ValueError("Incomplete AI response")

        result["source"] = "claude_ai"
        return result

    except Exception as e:
        logger.error(f"Claude AI analysis failed: {e}")
        return _rule_based_fallback(risk_score, risk_level, reasons, camara_results)


def _rule_based_fallback(
    risk_score: int,
    risk_level: str,
    reasons: list[str],
    camara_results: dict,
) -> dict:
    """Deterministic fallback when Claude is unavailable."""
    sim_24h = camara_results.get("sim_swap_24h", {}).get("swapped", False)

    if risk_score >= 60 or sim_24h:
        decision = "BLOCK"
        primary = "High-risk transaction blocked due to fraud indicators"
        actions = [
            "Do NOT process this transaction",
            "Ask customer to visit a physical branch with ID",
            "Report to fraud team immediately"
        ]
        pattern = "sim_swap_drain" if sim_24h else "coordinated_attack"
    elif risk_score >= 30:
        decision = "FLAG_FOR_REVIEW"
        primary = "Transaction flagged — requires additional verification"
        actions = [
            "Request secondary ID verification from customer",
            "Call customer on an alternate number to confirm",
            "Proceed only after confirmation"
        ]
        pattern = "high_value_suspicious"
    else:
        decision = "APPROVE"
        primary = "Transaction appears legitimate"
        actions = ["Proceed with transaction normally"]
        pattern = "normal"

    return {
        "decision": decision,
        "confidence": min(risk_score + 20, 95),
        "primary_reason": primary,
        "detailed_explanation": f"Risk score: {risk_score}/100 ({risk_level}). " +
                                (f"Signals: {'; '.join(reasons[:2])}" if reasons else "No fraud signals detected."),
        "recommended_actions": actions,
        "fraud_pattern": pattern,
        "source": "rule_based_fallback"
    }
