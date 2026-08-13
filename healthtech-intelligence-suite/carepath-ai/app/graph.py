"""LangGraph supervisor loop for CarePath AI."""

from __future__ import annotations

from typing import Any, Literal

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from app.agents import (
    firewall_node,
    hitl_node,
    medication_interaction_checker,
    patient_data_extractor,
    patient_preference_agent,
    plan_publish,
    supervisor_node,
    treatment_plan_evaluator,
    treatment_plan_generator,
)
from app.state import TreatmentPlanState

WORKER_NODES = (
    "patient_data_extractor",
    "medication_interaction_checker",
    "treatment_plan_generator",
    "patient_preference_agent",
    "treatment_plan_evaluator",
    "hitl",
    "plan_publish",
)


def _route_from_supervisor(
    state: TreatmentPlanState,
) -> Literal[
    "patient_data_extractor",
    "medication_interaction_checker",
    "treatment_plan_generator",
    "patient_preference_agent",
    "treatment_plan_evaluator",
    "hitl",
    "plan_publish",
    "__end__",
]:
    nxt = state.get("next") or "END"
    if nxt == "END":
        return END
    return nxt  # type: ignore[return-value]


def _route_after_firewall(
    state: TreatmentPlanState,
) -> Literal["supervisor", "plan_publish"]:
    if state.get("blocked"):
        return "plan_publish"
    return "supervisor"


def make_initial_state(
    *,
    thread_id: str,
    patient_id: str = "P001",
    clinician_id: str = "demo-clinician",
    query: str = "Generate a personalized treatment plan",
    patient_preferences: dict[str, Any] | None = None,
) -> TreatmentPlanState:
    return {
        "thread_id": thread_id,
        "clinician_id": clinician_id,
        "patient_id": patient_id,
        "query": query,
        "patient_preferences": patient_preferences or {},
        "patient_profile": None,
        "retrieved_evidence": [],
        "graph_paths": [],
        "medication_review": None,
        "draft_plan": None,
        "citations": [],
        "preferences_applied": False,
        "safety_score": None,
        "judge_feedback": None,
        "needs_revise": False,
        "revise_count": 0,
        "approval": "pending",
        "published": False,
        "final_plan": "",
        "step_log": [],
        "blocked": False,
        "block_reason": "",
        "next": "patient_data_extractor",
    }


def build_graph(checkpointer: Any = None):
    g = StateGraph(TreatmentPlanState)

    g.add_node("firewall", firewall_node)
    g.add_node("supervisor", supervisor_node)
    g.add_node("patient_data_extractor", patient_data_extractor)
    g.add_node("medication_interaction_checker", medication_interaction_checker)
    g.add_node("treatment_plan_generator", treatment_plan_generator)
    g.add_node("patient_preference_agent", patient_preference_agent)
    g.add_node("treatment_plan_evaluator", treatment_plan_evaluator)
    g.add_node("hitl", hitl_node)
    g.add_node("plan_publish", plan_publish)

    g.add_edge(START, "firewall")
    g.add_conditional_edges("firewall", _route_after_firewall, ["supervisor", "plan_publish"])
    g.add_conditional_edges(
        "supervisor",
        _route_from_supervisor,
        {
            "patient_data_extractor": "patient_data_extractor",
            "medication_interaction_checker": "medication_interaction_checker",
            "treatment_plan_generator": "treatment_plan_generator",
            "patient_preference_agent": "patient_preference_agent",
            "treatment_plan_evaluator": "treatment_plan_evaluator",
            "hitl": "hitl",
            "plan_publish": "plan_publish",
            END: END,
        },
    )
    for name in WORKER_NODES:
        if name == "plan_publish":
            g.add_edge("plan_publish", END)
        else:
            g.add_edge(name, "supervisor")

    return g.compile(checkpointer=checkpointer)


def build_graph_with_backends(checkpointer: Any = None):
    if checkpointer is None:
        import os

        memory_mode = os.getenv("CAREPATH_MEMORY", "memory").strip().lower()
        dsn = os.getenv("POSTGRES_DSN", "").strip()
        if memory_mode == "postgres" and dsn:
            try:
                from langgraph.checkpoint.postgres import PostgresSaver

                checkpointer = PostgresSaver.from_conn_string(dsn)
            except Exception:
                checkpointer = None
        if checkpointer is None:
            from langgraph.checkpoint.memory import MemorySaver

            checkpointer = MemorySaver()
    return build_graph(checkpointer=checkpointer)


SAMPLE_QUERY = (
    "Generate a personalized treatment plan for this complex chronic-care patient, "
    "addressing medication interactions, CKD-adjusted dosing, and patient preferences."
)


if __name__ == "__main__":
    import uuid

    from langgraph.types import Command

    graph = build_graph_with_backends()
    tid = str(uuid.uuid4())
    config = {"configurable": {"thread_id": tid}}
    state = make_initial_state(
        thread_id=tid,
        patient_id="P001",
        patient_preferences={
            "avoid_injectables": True,
            "avoid_medication_classes": ["injectable GLP-1"],
            "goals": ["prefer oral therapies"],
        },
    )
    print("Running CarePath fake smoke...")
    for update in graph.stream(state, config, stream_mode="updates"):
        node = next(iter(update.keys()), "?")
        print(f"  update: {node}")
    snap = graph.get_state(config)
    if any(intr for task in snap.tasks for intr in task.interrupts):
        print("HITL interrupt - auto-approving for smoke test")
        graph.invoke(Command(resume={"action": "approve"}), config)
        snap = graph.get_state(config)
    values = snap.values
    print("published:", values.get("published"))
    print("safety_score:", values.get("safety_score"))
    excerpt = (values.get("final_plan") or "")[:300].encode("ascii", "replace").decode()
    print("final_plan excerpt:", excerpt)
