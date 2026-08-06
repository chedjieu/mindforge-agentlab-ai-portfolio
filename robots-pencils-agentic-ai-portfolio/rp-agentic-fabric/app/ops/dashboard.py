"""Minimal Streamlit ops dashboard (stretch)."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
AUDIT = ROOT / "data" / "audit_packs.log"
HITL = ROOT / "data" / "hitl_outcomes.jsonl"

st.set_page_config(page_title="RPADF Ops", layout="wide")
st.title("R&P Agentic Fabric — Ops")

col1, col2 = st.columns(2)
with col1:
    st.subheader("Audit packs")
    if AUDIT.exists():
        st.code(AUDIT.read_text(encoding="utf-8")[-4000:] or "(empty)")
    else:
        st.info("No audit packs yet")
with col2:
    st.subheader("HITL outcomes")
    if HITL.exists():
        st.code(HITL.read_text(encoding="utf-8")[-4000:] or "(empty)")
    else:
        st.info("No HITL outcomes yet")
