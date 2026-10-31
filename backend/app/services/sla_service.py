"""Deterministic SLA Calculation Engine for AegisRCA.

Evaluates contractual SLA obligations and financial credit penalties using
structured contract thresholds from Member 1's data layer.
"""

from typing import Any
from app.schemas.investigation import SLAAssessment, SLAStatus


def calculate_sla_assessment(
    contract_data: dict[str, Any] | None,
    downtime_minutes: int | None,
    customer_id: str | None,
    cause_exclusion: str | None = None,
) -> SLAAssessment:
    """Deterministically calculate SLA liability and credit penalties.

    Does not rely on LLM for mathematical or financial conclusions.
    """
    if not customer_id:
        return SLAAssessment(
            status=SLAStatus.NOT_APPLICABLE,
            explanation="No customer ID provided for SLA calculation.",
        )

    if not contract_data:
        return SLAAssessment(
            status=SLAStatus.UNABLE_TO_DETERMINE,
            customer_id=customer_id,
            downtime_minutes=downtime_minutes,
            explanation=f"No active SLA contract on file for customer '{customer_id}'.",
        )

    if downtime_minutes is None:
        return SLAAssessment(
            status=SLAStatus.UNABLE_TO_DETERMINE,
            customer_id=customer_id,
            downtime_minutes=None,
            explanation=f"Downtime duration could not be determined for customer '{customer_id}'.",
        )

    # Check contract exclusions
    exclusions = contract_data.get("exclusions", [])
    if cause_exclusion and cause_exclusion in exclusions:
        return SLAAssessment(
            status=SLAStatus.ASSESSED,
            customer_id=customer_id,
            downtime_minutes=downtime_minutes,
            rca_required=False,
            credit_percent=0.0,
            explanation=(
                f"Incident downtime ({downtime_minutes} min) is excluded under contract "
                f"clause '{cause_exclusion}' ({contract_data.get('contract_name', 'MSA')})."
            ),
        )

    # Evaluate against credit tiers
    credit_tiers = contract_data.get("credit_tiers", [])
    if not credit_tiers:
        return SLAAssessment(
            status=SLAStatus.UNABLE_TO_DETERMINE,
            customer_id=customer_id,
            downtime_minutes=downtime_minutes,
            explanation=f"Contract for '{customer_id}' lacks structured credit tier definitions.",
        )

    matched_tier = None
    for tier in credit_tiers:
        min_m = tier.get("min_downtime_minutes", 0)
        max_m = tier.get("max_downtime_minutes")

        if max_m is not None:
            if min_m <= downtime_minutes <= max_m:
                matched_tier = tier
                break
        else:
            if downtime_minutes >= min_m:
                matched_tier = tier
                break

    if not matched_tier:
        return SLAAssessment(
            status=SLAStatus.UNABLE_TO_DETERMINE,
            customer_id=customer_id,
            downtime_minutes=downtime_minutes,
            explanation=f"Downtime of {downtime_minutes} minutes did not match any defined contract tier.",
        )

    credit_percent = float(matched_tier.get("credit_percent", 0.0))
    rca_required = bool(matched_tier.get("rca_required", False))
    contract_name = contract_data.get("contract_name", "Contract")

    if credit_percent > 0:
        explanation = (
            f"Under {contract_name}, downtime of {downtime_minutes} minutes incurs a "
            f"{credit_percent}% service credit."
        )
        if rca_required:
            explanation += " A formal Root Cause Analysis (RCA) is also required."
    else:
        if rca_required:
            explanation = (
                f"Under {contract_name}, downtime of {downtime_minutes} minutes requires a "
                f"formal RCA within {contract_data.get('rca_policy', {}).get('delivery_window_days', 5)} "
                f"business days, with 0% financial credit penalty."
            )
        else:
            explanation = (
                f"Under {contract_name}, downtime of {downtime_minutes} minutes is below "
                f"the threshold for financial credit and RCA delivery."
            )

    return SLAAssessment(
        status=SLAStatus.ASSESSED,
        customer_id=customer_id,
        downtime_minutes=downtime_minutes,
        rca_required=rca_required,
        credit_percent=credit_percent,
        explanation=explanation,
    )

