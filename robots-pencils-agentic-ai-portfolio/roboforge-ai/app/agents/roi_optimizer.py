"""ROI / cost optimizer."""

from __future__ import annotations

import json

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.llm import get_chat_model, invoke_with_throttle_fallback
from app.state import ForgeState


class RoiOut(BaseModel):
    monthly_infra_usd: float = 0
    monthly_token_usd: float = 0
    annual_savings_usd: float = 0
    payback_months: float = 0
    notes: str = ""


def roi_optimizer_node(state: ForgeState) -> dict:
    def _call() -> RoiOut:
        return get_chat_model().with_structured_output(RoiOut).invoke(
            [
                SystemMessage(
                    content=(
                        "You estimate ROI and cost for RoboForge blueprints. "
                        "Be conservative; never invent GPU fleets not in estate."
                    )
                ),
                HumanMessage(
                    content=(
                        f"Estate: {json.dumps(state.get('estate'))[:1500]}\n"
                        f"Blueprint: {json.dumps(state.get('blueprint'))[:1500]}"
                    )
                ),
            ]
        )

    try:
        roi = invoke_with_throttle_fallback(_call).model_dump()
    except Exception:
        score = (state.get("estate") or {}).get("modernization_score", 0.6)
        roi = {
            "monthly_infra_usd": 3500 + (1 - score) * 2000,
            "monthly_token_usd": 1500,
            "annual_savings_usd": 360000,
            "payback_months": 5,
            "notes": "Heuristic ROI from Velocity Pod compression",
        }

    return {
        "roi": roi,
        "step_log": state["step_log"]
        + [f"roi_optimizer: payback={roi.get('payback_months')}mo"],
    }
