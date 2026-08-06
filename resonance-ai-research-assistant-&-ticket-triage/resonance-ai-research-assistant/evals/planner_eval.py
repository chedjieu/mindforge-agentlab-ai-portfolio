"""Planner eval — score sub-question coverage against golden expected_sections."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langsmith import Client
from langsmith.evaluation import evaluate

from app._fake_llm import is_fake_chat_model
from app.llm import get_chat_model
from app.nodes.planner import planner_node

load_dotenv(override=False)

GOLDEN_PATH = Path(__file__).resolve().parent / "golden.jsonl"
DATASET_NAME = "raira-planner-golden"
PASS_THRESHOLD = 0.7
JUDGE_PROMPT = (
    "Given the sub-questions {sqs} and the expected coverage areas {expected_sections}, "
    "return a number 0.0-1.0 representing how well the sub-questions cover the expected "
    "areas. Return only a number."
)


def _is_throttling_error(exc: BaseException) -> bool:
    name = type(exc).__name__
    msg = str(exc).lower()
    return "throttl" in name.lower() or "throttl" in msg or "too many tokens" in msg


def _use_fake_planner() -> None:
    """Switch to offline fake planner (clears cached real model)."""
    os.environ["RAIRA_MODEL"] = "fake"
    get_chat_model.cache_clear()


def _ensure_planner_available() -> None:
    """Use fake planner when Bedrock/Vertex is throttled or unavailable."""
    if is_fake_chat_model(os.getenv("RAIRA_MODEL", "")):
        return
    try:
        get_chat_model().invoke([HumanMessage(content="Reply with exactly: ok")])
    except Exception as exc:
        if _is_throttling_error(exc):
            print(
                "  !! Bedrock throttled — using RAIRA_MODEL=fake for planner eval "
                "(set export RAIRA_MODEL=fake to skip this probe)"
            )
            _use_fake_planner()
            return
        raise


def load_golden() -> list[dict]:
    rows: list[dict] = []
    for line in GOLDEN_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def run_planner(inputs: dict) -> dict:
    """Run planner_node alone for one golden row."""
    state = {
        "question": inputs["question"],
        "sub_questions": [],
        "findings": [],
        "report": "",
        "step_log": [],
        "memories": [],
        "user_id": "eval",
    }
    try:
        return planner_node(state)
    except Exception as exc:
        if _is_throttling_error(exc):
            _use_fake_planner()
            return planner_node(state)
        raise


def _parse_score(text: str) -> float:
    match = re.search(r"0?\.\d+|1\.0|1|0", text.strip())
    if not match:
        return 0.0
    return max(0.0, min(1.0, float(match.group())))


def _programmatic_coverage(sub_questions: list[dict], expected_sections: list[str]) -> float:
    if not expected_sections:
        return 1.0
    blob = " ".join(str(sq.get("text", "")) for sq in sub_questions).lower()
    hits = sum(1 for area in expected_sections if area.lower() in blob)
    return hits / len(expected_sections)


def _missing_sections(sub_questions: list[dict], expected_sections: list[str]) -> list[str]:
    blob = " ".join(str(sq.get("text", "")) for sq in sub_questions).lower()
    return [area for area in expected_sections if area.lower() not in blob]


def _llm_judge_score(sub_questions: list[dict], expected_sections: list[str]) -> float | None:
    """Optional LLM-as-judge (skipped when fake or throttled)."""
    if is_fake_chat_model(os.getenv("RAIRA_MODEL", "")):
        return None
    if os.getenv("PLANNER_EVAL_LLM_JUDGE", "").lower() not in ("1", "true", "yes"):
        return None
    try:
        prompt = JUDGE_PROMPT.format(sqs=sub_questions, expected_sections=expected_sections)
        reply = get_chat_model().invoke([HumanMessage(content=prompt)])
        content = reply.content if isinstance(reply.content, str) else str(reply.content)
        return _parse_score(content)
    except Exception as exc:
        if _is_throttling_error(exc):
            return None
        raise


def coverage_score(sub_questions: list[dict], expected_sections: list[str]) -> float:
    """Programmatic keyword coverage — deterministic and works offline."""
    return _programmatic_coverage(sub_questions, expected_sections)


def coverage_evaluator(run, example) -> dict:
    sub_questions = run.outputs.get("sub_questions", [])
    expected_sections = example.inputs.get("expected_sections", [])
    score = coverage_score(sub_questions, expected_sections)
    return {"key": "coverage", "score": score}


def print_summary(results) -> None:
    passed = 0
    total = 0
    scores: list[float] = []

    for row in results:
        total += 1
        question = row["example"].inputs.get("question", "")
        score = 0.0
        for result in row["evaluation_results"]["results"]:
            if result.key == "coverage" and result.score is not None:
                score = float(result.score)
        scores.append(score)
        ok = score >= PASS_THRESHOLD
        if ok:
            passed += 1
        status = "PASS" if ok else "FAIL"
        preview = question if len(question) <= 72 else f"{question[:69]}..."
        run = row.get("run")
        outputs = getattr(run, "outputs", None) if run is not None else {}
        if not isinstance(outputs, dict):
            outputs = {}
        missing = _missing_sections(
            outputs.get("sub_questions", []),
            row["example"].inputs.get("expected_sections", []),
        )
        detail = f"  missing: {missing}" if missing and not ok else ""
        print(f"{status}  coverage={score:.2f}  {preview}{detail}")

    avg = sum(scores) / len(scores) if scores else 0.0
    print(f"\nAggregate: {passed}/{total} passed ({100 * passed / total:.0f}%)  avg coverage={avg:.2f}")
    if getattr(results, "url", None):
        print(f"LangSmith: {results.url}")
    if passed < total:
        sys.exit(1)


def ensure_langsmith_dataset(rows: list[dict]) -> str:
    """Create the golden dataset in LangSmith if it does not exist yet."""
    client = Client()
    try:
        client.read_dataset(dataset_name=DATASET_NAME)
    except Exception:
        client.create_dataset(
            dataset_name=DATASET_NAME,
            description="Project 1 planner golden eval dataset",
        )
        client.create_examples(
            dataset_name=DATASET_NAME,
            examples=[{"inputs": row, "outputs": {}} for row in rows],
        )
    return DATASET_NAME


def main() -> None:
    _ensure_planner_available()
    rows = load_golden()
    upload = bool(os.getenv("LANGSMITH_API_KEY"))
    data = ensure_langsmith_dataset(rows) if upload else [{"inputs": row} for row in rows]

    results = evaluate(
        run_planner,
        data=data,
        evaluators=[coverage_evaluator],
        experiment_prefix="planner-eval",
        description="Planner sub-question coverage vs golden expected_sections",
        upload_results=upload,
    )
    print_summary(results)


if __name__ == "__main__":
    main()
