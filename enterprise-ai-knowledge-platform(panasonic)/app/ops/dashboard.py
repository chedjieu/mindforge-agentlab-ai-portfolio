"""Ops dashboard — Streamlit view of EGKP quality / volume metrics.

Run:
    uv run streamlit run app/ops/dashboard.py
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
HITL_LOG = DATA_DIR / "hitl_outcomes.jsonl"
PUBLISHED_LOG = DATA_DIR / "published_answers.log"


def _parse_ts(value: object) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def main() -> None:
    st.set_page_config(page_title="EGKP Ops", layout="wide")
    st.title("Panasonic EGKP — Ops Dashboard")
    st.caption("Read-only metrics from published answers + HITL outcomes")

    published = _load_jsonl(PUBLISHED_LOG)
    hitl = _load_jsonl(HITL_LOG)
    today = datetime.now(timezone.utc).date()

    pub_today = []
    for row in published:
        ts = _parse_ts(row.get("ts"))
        if ts and ts.date() == today:
            pub_today.append(row)

    domain_counts = Counter(str(r.get("domain") or "unknown") for r in pub_today)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Published today", len(pub_today))
    col2.metric("HITL outcomes (all)", len(hitl))
    hitl_rate = (len(hitl) / max(len(published) + len(hitl), 1)) if (published or hitl) else 0.0
    col3.metric("HITL rate (lifetime)", f"{100 * hitl_rate:.0f}%")
    grounds = [float(r["grounding_score"]) for r in published if r.get("grounding_score") is not None]
    col4.metric("Avg grounding", f"{(sum(grounds) / len(grounds)):.2f}" if grounds else "n/a")

    st.subheader("Today's queries by domain")
    if domain_counts:
        df_dom = pd.DataFrame(
            {"domain": list(domain_counts.keys()), "count": list(domain_counts.values())}
        ).set_index("domain")
        st.bar_chart(df_dom)
    else:
        st.info("No published answers today yet.")

    st.subheader("Grounding score histogram")
    if grounds:
        st.bar_chart(pd.DataFrame({"grounding": grounds}))
    else:
        st.info("No grounding scores logged yet.")

    st.subheader("HITL latency (seconds)")
    latencies = [
        float(h["hitl_latency_seconds"])
        for h in hitl
        if h.get("hitl_latency_seconds") is not None
    ]
    if latencies:
        sorted_lat = sorted(latencies)
        p50 = sorted_lat[len(sorted_lat) // 2]
        st.metric("P50 HITL latency", f"{p50:.2f}s")
        st.bar_chart(pd.DataFrame({"latency_s": latencies}))
    else:
        st.info("No HITL latency samples yet.")

    st.subheader("Last 20 published answers")
    recent = list(reversed(published[-20:]))
    if not recent:
        st.info("No published answers yet.")
    else:
        for row in recent:
            g = row.get("grounding_score")
            approval = row.get("approval") or "unknown"
            badge = "OK" if approval in ("auto", "approved", "edited") else "WARN"
            with st.expander(
                f"[{badge}] [{row.get('domain')}] grounding={g} — {(row.get('query') or '')[:80]}"
            ):
                st.write(row.get("answer") or "")
                st.json(
                    {
                        "thread_id": row.get("thread_id"),
                        "approval": approval,
                        "citations": row.get("citations"),
                        "ts": row.get("ts"),
                    }
                )


main()
