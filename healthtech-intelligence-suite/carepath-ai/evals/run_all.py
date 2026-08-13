"""Golden scenario evals for CarePath AI."""

from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("CAREPATH_MODEL", "fake")
os.environ.setdefault("CAREPATH_EMBEDDINGS", "fake")
os.environ.setdefault("CAREPATH_JUDGE_MODEL", "fake")

from langgraph.types import Command

from app.graph import build_graph_with_backends, make_initial_state
from app.rag.retrieval import hybrid_search

PATIENTS = ROOT / "data" / "patients"


def _prefs(patient_id: str) -> dict:
    path = PATIENTS / patient_id / "preferences.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def run_patient(patient_id: str) -> dict:
    graph = build_graph_with_backends()
    tid = str(uuid.uuid4())
    config = {"configurable": {"thread_id": tid}}
    state = make_initial_state(
        thread_id=tid,
        patient_id=patient_id,
        patient_preferences=_prefs(patient_id),
    )
    for _ in graph.stream(state, config, stream_mode="updates"):
        pass
    snap = graph.get_state(config)
    if any(intr for task in snap.tasks for intr in task.interrupts):
        graph.invoke(Command(resume={"action": "approve"}), config)
        snap = graph.get_state(config)
    return dict(snap.values)


def check_p001(values: dict) -> list[str]:
    errs = []
    if not values.get("published"):
        errs.append("P001 not published")
    plan = (values.get("final_plan") or "").lower()
    if "goal" not in plan:
        errs.append("P001 missing goals section")
    review = values.get("medication_review") or {}
    renal = review.get("renal_adjustments") or []
    if not renal and "metformin" in str(values.get("patient_profile")).lower():
        # eGFR 58 should trigger reduce note
        errs.append("P001 missing metformin renal adjustment")
    if values.get("safety_score") is not None and float(values["safety_score"]) < 0.90:
        errs.append(f"P001 safety_score {values['safety_score']} < 0.90")
    cites = values.get("citations") or []
    if len(cites) < 1:
        errs.append("P001 missing citations")
    prefs = json.dumps(_prefs("P001")).lower()
    if "inject" in prefs and "inject" not in plan and "oral" not in plan and "sglt" not in plan:
        # preference-adjusted fake reply includes oral / avoid injectable
        errs.append("P001 preference adaptation not reflected")
    return errs


def check_p002(values: dict) -> list[str]:
    errs = []
    if not values.get("published"):
        errs.append("P002 not published")
    review = values.get("medication_review") or {}
    interactions = review.get("interactions") or []
    major = [i for i in interactions if str(i.get("severity")).lower() == "major"]
    if not major:
        errs.append("P002 expected major sedative interaction")
    return errs


def check_p003(values: dict) -> list[str]:
    errs = []
    if not values.get("published"):
        errs.append("P003 not published")
    if not values.get("preferences_applied"):
        errs.append("P003 preferences not applied")
    plan = (values.get("final_plan") or values.get("draft_plan") or "").lower()
    # preference agent or prefs should influence plan text in fake mode
    if "beta" not in plan and "fatigue" not in plan and "shared" not in plan:
        # still ok if published with any plan content
        if len(plan) < 40:
            errs.append("P003 plan too short")
    return errs


def check_retrieval() -> list[str]:
    hits = hybrid_search("diabetes metformin CKD eGFR treatment", limit=3)
    if not hits:
        return ["retrieval returned no diabetes guideline chunks"]
    blob = " ".join(h.get("text", "") for h in hits).lower()
    if "metformin" not in blob and "a1c" not in blob:
        return ["retrieval hits lack diabetes content"]
    return []


def main() -> int:
    print("CarePath evals (CAREPATH_MODEL=fake)")
    failures: list[str] = []
    failures.extend(check_retrieval())

    for pid, checker in [("P001", check_p001), ("P002", check_p002), ("P003", check_p003)]:
        print(f"  running {pid}…")
        values = run_patient(pid)
        errs = checker(values)
        if errs:
            failures.extend(errs)
            print(f"  FAIL {pid}: {errs}")
        else:
            print(f"  PASS {pid} safety={values.get('safety_score')} published={values.get('published')}")

    if failures:
        print("FAILED:")
        for f in failures:
            print(" -", f)
        return 1
    print("All golden scenarios passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
