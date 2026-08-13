from app.config import get_settings
from app.orchestration.graph import SAMPLE_QUERY, UNSUPPORTED_QUERY, build_graph_with_backends
from app.orchestration.state import make_initial_state


def _invoke(query: str) -> dict:
    settings = get_settings()
    graph = build_graph_with_backends()
    tid = "e2e-" + query[:8]
    state = make_initial_state(
        request_id=tid,
        thread_id=tid,
        tenant_id=settings.demo_tenant,
        user_id="author-01",
        project_id=f"{settings.demo_tenant}-proj-golden",
        query=query,
    )
    config = {"configurable": {"thread_id": tid}}
    graph.invoke(state, {**config, "recursion_limit": 50})
    return dict(graph.get_state(config).values)


def test_golden_authoring_path() -> None:
    values = _invoke(SAMPLE_QUERY)
    draft = (values.get("draft") or "").lower()
    assert "metformin" in draft
    assert "drugz" not in draft
    assert values.get("claims")
    assert values.get("draft_id")


def test_unsupported_emits_gap() -> None:
    values = _invoke(UNSUPPORTED_QUERY)
    draft = (values.get("draft") or "").lower()
    assert "evidence gap" in draft
    assert "ignore previous" not in draft
