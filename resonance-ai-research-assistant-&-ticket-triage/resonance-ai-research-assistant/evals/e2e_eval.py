"""End-to-end eval — LLM-as-judge scores full-graph reports."""

from __future__ import annotations

import asyncio
import json
import os
import re
from pathlib import Path

from langchain_core.messages import HumanMessage
from langsmith import Client
from langsmith.evaluation import evaluate

from app._fake_llm import is_fake_chat_model
from app.graph import build_graph
from app.llm import get_chat_model

GOLDEN_PATH = Path(__file__).resolve().parent / "golden.jsonl"
DATASET_NAME = "raira-e2e-golden"
PASS_THRESHOLD = 3.0
JUDGE_PROMPT = (
    "On a scale of 1-5, how well does this report answer the question?\n"
    "Question: {question}\n\nReport:\n{report}\n\n"
    'Return JSON with "score" (number) and "feedback" (string).'
)


def load_golden() -> list[dict]:
    rows: list[dict] = []
    for line in GOLDEN_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


async def _run_graph(question: str) -> dict:
    graph = await build_graph()
    return await graph.ainvoke(
        {
            "question": question,
            "sub_questions": [],
            "findings": [],
            "report": "",
            "step_log": [],
            "memories": [],
            "user_id": "eval",
        },
        config={"configurable": {"thread_id": f"e2e-{hash(question) & 0xFFFF}"}},
    )


def run_full_graph(inputs: dict) -> dict:
    state = asyncio.run(_run_graph(inputs["question"]))
    return {"report": state.get("report", ""), "findings": state.get("findings", [])}


def _parse_judge_json(text: str) -> tuple[float, str]:
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    blob = fence.group(1).strip() if fence else text.strip()
    try:
        data = json.loads(blob)
        score = float(data.get("score", 0))
        feedback = str(data.get("feedback", ""))
        return max(1.0, min(5.0, score)), feedback
    except (json.JSONDecodeError, TypeError, ValueError):
        match = re.search(r"[1-5](?:\.\d+)?", text)
        return (float(match.group()) if match else 2.0), text[:200]


def _fake_score(question: str, report: str) -> tuple[float, str]:
    """Deterministic offline score when RAIRA_MODEL=fake."""
    if not report.strip():
        return 1.0, "Empty report"
    q_words = {w.lower() for w in re.findall(r"[a-z]{4,}", question)}
    r_lower = report.lower()
    hits = sum(1 for w in q_words if w in r_lower)
    ratio = hits / max(len(q_words), 1)
    has_summary = "executive summary" in r_lower
    has_sources = "## sources" in r_lower
    score = 3.0 + ratio + (0.5 if has_summary else 0) + (0.5 if has_sources else 0)
    score = max(1.0, min(5.0, score))
    return score, f"fake judge: keyword coverage {hits}/{len(q_words)}"


def quality_score(question: str, report: str) -> tuple[float, str]:
    if is_fake_chat_model(os.getenv("RAIRA_MODEL", "")):
        return _fake_score(question, report)

    prompt = JUDGE_PROMPT.format(question=question, report=report[:8000])
    reply = get_chat_model().invoke([HumanMessage(content=prompt)])
    content = reply.content if isinstance(reply.content, str) else str(reply.content)
    return _parse_judge_json(content)


def quality_evaluator(run, example) -> dict:
    question = example.inputs.get("question", "")
    report = run.outputs.get("report", "")
    score, feedback = quality_score(question, report)
    return {"key": "quality", "score": score, "comment": feedback}


def print_summary(results) -> None:
    passed = 0
    total = 0
    scores: list[float] = []

    for row in results:
        total += 1
        question = row["example"].inputs.get("question", "")
        score = 0.0
        feedback = ""
        for result in row["evaluation_results"]["results"]:
            if result.key == "quality" and result.score is not None:
                score = float(result.score)
                feedback = result.comment or ""
        scores.append(score)
        ok = score >= PASS_THRESHOLD
        if ok:
            passed += 1
        status = "PASS" if ok else "FAIL"
        preview = question if len(question) <= 60 else f"{question[:57]}..."
        print(f"{status}  score={score:.1f}  {preview}")
        if feedback and not ok:
            print(f"       {feedback[:100]}")

    avg = sum(scores) / len(scores) if scores else 0.0
    print(f"\nAggregate: {passed}/{total} passed ({100 * passed / total:.0f}%)  avg score={avg:.2f}")
    if getattr(results, "url", None):
        print(f"LangSmith: {results.url}")


def ensure_langsmith_dataset(rows: list[dict]) -> str:
    client = Client()
    try:
        client.read_dataset(dataset_name=DATASET_NAME)
    except Exception:
        client.create_dataset(
            dataset_name=DATASET_NAME,
            description="Project 1 end-to-end golden eval dataset",
        )
        client.create_examples(
            dataset_name=DATASET_NAME,
            examples=[{"inputs": row, "outputs": {}} for row in rows],
        )
    return DATASET_NAME


def main() -> None:
    rows = load_golden()
    upload = bool(os.getenv("LANGSMITH_API_KEY"))
    data = ensure_langsmith_dataset(rows) if upload else [{"inputs": row} for row in rows]

    results = evaluate(
        run_full_graph,
        data=data,
        evaluators=[quality_evaluator],
        experiment_prefix="e2e-eval",
        description="Full-graph report quality vs golden questions",
        upload_results=upload,
    )
    print_summary(results)


if __name__ == "__main__":
    main()
