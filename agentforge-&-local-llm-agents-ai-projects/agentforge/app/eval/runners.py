from __future__ import annotations

from app.agents.graph import run_agent
from app.api.schemas import EvalCaseResult
from app.guardrails.groundedness import REFUSAL
from app.rag.retriever import retrieve

SAMPLE_CASES = [
    {
        "question": "What topics are covered in the certification?",
        "expect_grounded": True,
    },
    {
        "question": "What are the prerequisites?",
        "expect_grounded": True,
    },
    {
        "question": "What is today's weather in Cardiff?",
        "expect_grounded": False,
        "expect_contains": ["Temperature", "Wind"],
    },
    {
        "question": "Who won the 1812 World Cup of Quantum Chess?",
        "expect_grounded": False,
        "expect_refusal": True,
    },
]


def _score_overlap(answer: str, context: str) -> float:
    """Lightweight lexical groundedness proxy when DeepEval metrics are unavailable."""
    answer_tokens = {t.lower() for t in answer.split() if len(t) > 3}
    context_tokens = {t.lower() for t in context.split() if len(t) > 3}
    if not answer_tokens:
        return 0.0
    overlap = len(answer_tokens & context_tokens)
    return round(overlap / max(len(answer_tokens), 1), 3)


def _try_deepeval(question: str, answer: str, context: str) -> tuple[float | None, float | None, str]:
    try:
        from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric
        from deepeval.test_case import LLMTestCase

        test_case = LLMTestCase(
            input=question,
            actual_output=answer,
            retrieval_context=[context] if context else [""],
        )
        faithfulness = FaithfulnessMetric(threshold=0.5)
        relevancy = AnswerRelevancyMetric(threshold=0.5)
        faithfulness.measure(test_case)
        relevancy.measure(test_case)
        return float(faithfulness.score), float(relevancy.score), "deepeval"
    except Exception as exc:
        groundedness = _score_overlap(answer, context)
        relevance = groundedness
        return groundedness, relevance, f"fallback:{exc.__class__.__name__}"


def run_evaluation(run_sample: bool = True) -> list[EvalCaseResult]:
    cases = SAMPLE_CASES if run_sample else SAMPLE_CASES[:1]
    results: list[EvalCaseResult] = []

    for case in cases:
        question = case["question"]
        result = run_agent(question, thread_id=f"eval-{hash(question) & 0xffff}")
        answer = result.get("answer") or ""
        chunks = retrieve(question)
        context = "\n".join(c.text for c in chunks)

        groundedness, relevance, notes = _try_deepeval(question, answer, context)

        if case.get("expect_refusal") and REFUSAL.split(".")[0].lower() not in answer.lower():
            notes += "; expected refusal-like answer"
        if case.get("expect_contains"):
            missing = [s for s in case["expect_contains"] if s.lower() not in answer.lower()]
            if missing:
                notes += f"; missing expected terms: {missing}"

        results.append(
            EvalCaseResult(
                question=question,
                answer=answer[:1000],
                groundedness=groundedness,
                relevance=relevance,
                notes=notes,
            )
        )
    return results
