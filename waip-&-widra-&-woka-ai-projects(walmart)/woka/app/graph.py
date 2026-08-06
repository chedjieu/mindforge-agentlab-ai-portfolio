"""LangGraph orchestrator — UC-1 multi-agent fan-out."""

from __future__ import annotations

from typing import Any, Literal

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from app.agents.analytics import run_analytics_agent
from app.agents.citation import run_citation_agent
from app.agents.compliance import run_compliance_agent
from app.agents.firewall import firewall_check
from app.agents.internet import run_internet_agent
from app.agents.retrieval import run_retrieval_agent
from app.agents.security import scope_from_request
from app.agents.sql import run_sql_agent
from app.state import WokaState

WORKER_NODES = ("retrieval_worker", "sql_worker", "internet_worker")


def _log(msg: str) -> list[str]:
    return [msg]


def firewall_node(state: WokaState) -> dict[str, Any]:
    check = firewall_check(state.get("query") or "")
    if check["blocked"]:
        return {
            "blocked": True,
            "block_reason": check["reason"],
            "answer": "Request blocked by security firewall.",
            "final_response": "Request blocked by security firewall.",
            "citations": [],
            "agents_used": ["firewall"],
            "confidence": 0.0,
            "step_log": _log("firewall:blocked"),
        }
    return {"blocked": False, "step_log": _log("firewall:ok")}


def security_node(state: WokaState) -> dict[str, Any]:
    scope = scope_from_request(
        user_id=state.get("user_id") or "user-001",
        role=state.get("role") or "associate",
        department=state.get("department") or "Store Ops",
        region=state.get("region") or "US",
    )
    q = (state.get("query") or "").lower()
    workers = ["retrieval_worker"]
    if any(k in q for k in ("hurricane", "dc", "supplier", "inventory", "stock", "contract", "shipment", "disruption")):
        workers.extend(["sql_worker", "internet_worker"])
    elif any(k in q for k in ("fda", "recall", "weather", "osha")):
        workers.append("internet_worker")
    workers = list(dict.fromkeys(workers))
    return {
        "scope": scope.to_dict(),
        "workers": workers,
        "worker_results": {},
        "step_log": _log(f"security:policies={scope.allowed_policies}"),
    }


def planner_node(state: WokaState) -> dict[str, Any]:
    return {"step_log": _log(f"planner:workers={state.get('workers')}")}


def retrieval_worker(state: WokaState) -> dict[str, Any]:
    from app.security.acl import AccessScope

    scope_dict = state.get("scope") or {}
    scope = AccessScope(
        user_id=scope_dict.get("user_id", "user"),
        role=scope_dict.get("role", "associate"),
        department=scope_dict.get("department", "Store Ops"),
        region=scope_dict.get("region", "US"),
        clearance=scope_dict.get("clearance", "internal"),
        allowed_policies=list(scope_dict.get("allowed_policies") or ["general_employee"]),
        allowed_regions=list(scope_dict.get("allowed_regions") or ["US"]),
    )
    result = run_retrieval_agent(state.get("query") or "", scope, top_k=5)
    return {
        "worker_results": {"retrieval": result},
        "retrieval": result,
        "step_log": _log("retrieval:done"),
        "agents_used": ["retrieval"],
    }


def sql_worker(state: WokaState) -> dict[str, Any]:
    result = run_sql_agent(state.get("query") or "", region=state.get("region") or "SE")
    return {
        "worker_results": {"sql": result},
        "sql": result,
        "step_log": _log("sql:done"),
        "agents_used": ["sql"],
    }


def internet_worker(state: WokaState) -> dict[str, Any]:
    result = run_internet_agent(state.get("query") or "")
    return {
        "worker_results": {"internet": result},
        "internet": result,
        "step_log": _log("internet:done"),
        "agents_used": ["internet"],
    }


def _fanout(state: WokaState) -> list[Send]:
    workers = state.get("workers") or ["retrieval_worker"]
    return [Send(w, state) for w in workers if w in WORKER_NODES]


def merge_node(state: WokaState) -> dict[str, Any]:
    wr = state.get("worker_results") or {}
    retrieval = wr.get("retrieval") or state.get("retrieval") or {}
    sql = wr.get("sql") or state.get("sql") or {}
    internet = wr.get("internet") or state.get("internet") or {}

    parts: list[str] = []
    agents = ["security", "retrieval"]
    if sql:
        agents.append("sql")
        data = sql.get("data") or {}
        suppliers = ", ".join(s.get("name", s.get("supplier_id", "")) for s in data.get("affected_suppliers") or [])
        delayed = ", ".join(
            f"{d.get('sku')}->{d.get('dest_dc')} (+{d.get('eta_hours')}h)"
            for d in data.get("delayed_shipments") or []
        )
        inv = ", ".join(
            f"{i.get('sku')} at {i.get('location_id')} ({i.get('qty')} units)"
            for i in data.get("inventory_within_300mi") or []
        )
        contracts = ", ".join(
            f"{c.get('contract_id')} ({c.get('notice_hours')}h notice)"
            for c in data.get("alt_sourcing_contracts") or []
        )
        stockouts = ", ".join(
            f"{s.get('store_id')}/{s.get('sku')} ({s.get('qty')} on hand)"
            for s in data.get("stockout_risk_48h") or []
        )
        closed = ", ".join(d.get("dc_id", "") for d in data.get("closed_dcs") or [])
        parts.append(
            f"Southeast DC closures ({closed or 'n/a'}) affect suppliers {suppliers or 'n/a'}. "
            f"Delayed products/shipments: {delayed or 'n/a'}. "
            f"Inventory within ~300 miles (open SE DCs): {inv or 'n/a'}. "
            f"Contracts permitting alternate sourcing: {contracts or 'n/a'}. "
            f"Stores at 48h stockout risk: {stockouts or 'n/a'}."
        )
    if internet and internet.get("summary"):
        agents.append("internet")
        parts.append(f"External context: {internet['summary']}")

    # Doc grounding snippets
    chunks = retrieval.get("chunks") or []
    if chunks:
        top = chunks[0]
        parts.append(
            f"Policy grounding: {(top.get('text') or '')[:180]} "
            f"(source: {top.get('title') or top.get('filename')})."
        )

    if not parts:
        parts.append(
            "No strong multi-source match. Refer to authorized documents returned by retrieval, if any."
        )

    answer = " ".join(parts)
    cite = run_citation_agent(retrieval=retrieval, sql=sql or None, internet=internet or None)
    analytics = run_analytics_agent(sql or None)

    return {
        "answer": answer,
        "citations": cite.get("citations") or [],
        "confidence": float(cite.get("avg_confidence") or 0.85),
        "agents_used": ["citation", "analytics"],
        "analytics": analytics,
        "retrieval": retrieval,
        "sql": sql,
        "internet": internet,
        "step_log": _log("merge:complete"),
    }


def compliance_node(state: WokaState) -> dict[str, Any]:
    result = run_compliance_agent(
        answer=state.get("answer") or "",
        citations=list(state.get("citations") or []),
        sql_data=state.get("sql"),
        blocked=bool(state.get("blocked")),
    )
    return {
        "compliance": result,
        "agents_used": ["compliance"],
        "step_log": _log(f"compliance:{'pass' if result.get('passed') else 'fail'}"),
    }


def publish_node(state: WokaState) -> dict[str, Any]:
    from app.observability.audit import write_audit
    from evals.judges import evaluate_answer

    if state.get("blocked"):
        answer = state.get("answer") or state.get("block_reason") or "Blocked"
        audit = write_audit(
            user_id=state.get("user_id") or "anonymous",
            action="chat_blocked",
            query_text=state.get("query"),
            details={"reason": state.get("block_reason"), "agents": state.get("agents_used")},
        )
        judges = evaluate_answer(
            query=state.get("query") or "",
            answer=answer,
            citations=[],
            blocked=True,
        )
        return {
            "final_response": answer,
            "judges": judges,
            "audit_id": audit["audit_id"],
            "step_log": _log("publish:blocked"),
            "agents_used": ["observability"],
        }

    compliance = state.get("compliance") or {}
    answer = state.get("answer") or ""
    if compliance and not compliance.get("passed"):
        answer = (
            answer
            + "\n\n[Compliance note: "
            + "; ".join(compliance.get("issues") or ["needs review"])
            + "]"
        )

    judges = evaluate_answer(
        query=state.get("query") or "",
        answer=answer,
        citations=list(state.get("citations") or []),
        sql=state.get("sql"),
        blocked=False,
    )
    audit = write_audit(
        user_id=state.get("user_id") or "anonymous",
        action="chat",
        query_text=state.get("query"),
        details={
            "agents_used": state.get("agents_used"),
            "citation_count": len(state.get("citations") or []),
            "judges_pass": judges.get("pass"),
            "confidence": state.get("confidence"),
        },
    )
    return {
        "final_response": answer,
        "judges": judges,
        "audit_id": audit["audit_id"],
        "step_log": _log(f"publish:ok judges={'pass' if judges.get('pass') else 'fail'}"),
        "agents_used": ["observability"],
    }


def _after_firewall(state: WokaState) -> Literal["security", "publish"]:
    return "publish" if state.get("blocked") else "security"


def build_graph(checkpointer: Any = None):
    g = StateGraph(WokaState)
    g.add_node("firewall", firewall_node)
    g.add_node("security", security_node)
    g.add_node("planner", planner_node)
    g.add_node("retrieval_worker", retrieval_worker)
    g.add_node("sql_worker", sql_worker)
    g.add_node("internet_worker", internet_worker)
    g.add_node("merge", merge_node)
    # Node name must not collide with WokaState keys (e.g. "compliance")
    g.add_node("compliance_check", compliance_node)
    g.add_node("publish", publish_node)

    g.add_edge(START, "firewall")
    g.add_conditional_edges("firewall", _after_firewall, ["security", "publish"])
    g.add_edge("security", "planner")
    g.add_conditional_edges("planner", _fanout, list(WORKER_NODES))
    for w in WORKER_NODES:
        g.add_edge(w, "merge")
    g.add_edge("merge", "compliance_check")
    g.add_edge("compliance_check", "publish")
    g.add_edge("publish", END)

    if checkpointer is None:
        from langgraph.checkpoint.memory import MemorySaver

        checkpointer = MemorySaver()
    return g.compile(checkpointer=checkpointer)


_GRAPH = None


def get_graph():
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_graph()
    return _GRAPH


def run_uc1(
    query: str,
    *,
    user_id: str = "user-sc-001",
    role: str = "analyst",
    department: str = "Supply Chain",
    region: str = "SE",
) -> dict[str, Any]:
    import uuid

    from app.observability.langsmith import configure_langsmith

    configure_langsmith()
    graph = get_graph()
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    return graph.invoke(
        {
            "query": query,
            "user_id": user_id,
            "role": role,
            "department": department,
            "region": region,
            "step_log": [],
            "worker_results": {},
        },
        config=config,
    )
