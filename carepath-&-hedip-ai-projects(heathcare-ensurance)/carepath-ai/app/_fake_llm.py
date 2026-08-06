"""Deterministic fake LLM for offline demos and CI."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field


class FakeChatModel(BaseChatModel):
    """Heuristic clinical responses keyed off the last human message."""

    model_name: str = Field(default="carepath-fake")

    @property
    def _llm_type(self) -> str:
        return "carepath-fake"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        text = " ".join(str(m.content) for m in messages).lower()
        payload = self._reply(text)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=payload))])

    def _reply(self, text: str) -> str:
        # Order matters: generation/preference before judge (prompts may include "judge_feedback").
        if "extract" in text or ("ehr" in text and "profile" in text):
            return json.dumps(
                {
                    "conditions": ["Type 2 diabetes mellitus", "Hypertension", "Hyperlipidemia", "CKD stage 3a"],
                    "medications": [
                        "metformin",
                        "lisinopril",
                        "atorvastatin",
                        "amlodipine",
                        "aspirin",
                        "omeprazole",
                    ],
                    "allergies": ["sulfa"],
                    "labs": {"egfr": 58, "a1c": 8.2, "ldl": 112},
                    "lifestyle": {"activity": "sedentary", "diet": "high carb"},
                }
            )

        if "adapt the plan" in text or "honor patient preferences" in text:
            return (
                "## Personalized Treatment Plan (preference-adjusted)\n\n"
                "### Goals\n"
                "- A1C < 7.0% within 3 months\n"
                "- BP < 130/80 mmHg\n"
                "- Avoid injectable therapies per patient preference\n\n"
                "### Interventions\n"
                "- Continue metformin with CKD-adjusted dosing (eGFR 58)\n"
                "- Prefer oral SGLT2 inhibitor over injectable GLP-1\n"
                "- Intensify lifestyle counseling (diet, walking 150 min/week)\n\n"
                "### Monitoring\n"
                "- A1C and BMP in 12 weeks; BMP sooner if GI symptoms\n"
                "- Home BP log weekly\n\n"
                "### Follow-up\n"
                "- Endocrinology follow-up in 8-12 weeks\n"
            )

        if (
            "generate a personalized treatment plan" in text
            or "sections: goals" in text
            or ("treatment plan" in text and "generate" in text)
        ):
            return (
                "## Personalized Treatment Plan\n\n"
                "### Goals\n"
                "- Improve glycemic control (A1C target < 7%)\n"
                "- Optimize blood pressure and lipid management\n\n"
                "### Interventions\n"
                "- Review metformin dosing for CKD stage 3a (eGFR 58)\n"
                "- Consider GLP-1 RA or SGLT2i intensification\n"
                "- Continue ACE inhibitor and statin therapy\n"
                "- Mediterranean-style diet counseling\n\n"
                "### Monitoring\n"
                "- Labs: A1C, BMP, lipids in 3 months\n"
                "- Screen for hypoglycemia if intensifying\n\n"
                "### Follow-up\n"
                "- Primary care or endocrinology in 8-12 weeks\n"
            )

        if (
            "evaluate this treatment plan" in text
            or "return json with keys: safety_score" in text
            or ("groundedness" in text and "safety_score" in text)
        ):
            return json.dumps(
                {
                    "safety_score": 0.93,
                    "guideline_adherence": 0.91,
                    "citation_coverage": 0.94,
                    "completeness": 0.92,
                    "needs_revise": False,
                    "feedback": "Plan addresses CKD-adjusted metformin and preference to avoid injectables.",
                }
            )

        return (
            "Based on retrieved clinical guidelines and the patient profile, "
            "a personalized chronic-care plan should address glycemic control, "
            "cardiovascular risk, medication safety, and patient preferences."
        )


class FakeEmbeddings:
    """Hash-based embedding vectors for offline hybrid search."""

    def __init__(self, dim: int = 64):
        self.dim = dim

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        vals = [(digest[i % len(digest)] / 255.0) for i in range(self.dim)]
        for tok in text.lower().split():
            h = int(hashlib.md5(tok.encode()).hexdigest()[:8], 16)
            vals[h % self.dim] = min(1.0, vals[h % self.dim] + 0.15)
        return vals


def is_fake_chat_model(name: str) -> bool:
    return (name or "").strip().lower() in ("fake", "carepath-fake") or (
        name or ""
    ).strip().lower().startswith("fake")


def is_fake_embeddings(name: str) -> bool:
    return is_fake_chat_model(name) or (name or "").strip().lower() in ("fake",)
