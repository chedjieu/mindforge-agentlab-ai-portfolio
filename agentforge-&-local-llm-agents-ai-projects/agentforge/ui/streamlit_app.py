from __future__ import annotations

import json
import os
import uuid

import httpx
import streamlit as st

API_BASE = os.getenv("AGENTFORGE_API", "http://localhost:8000")


st.set_page_config(page_title="AgentForge", page_icon="⚙️", layout="wide")
st.title("AgentForge")
st.caption("Local-first production agent platform")

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "events" not in st.session_state:
    st.session_state.events = []


with st.sidebar:
    st.subheader("Session")
    st.text_input("Thread ID", key="thread_id")
    st.text_input("API Base", value=API_BASE, key="api_base")

    if st.button("Ingest PDF from assets/", use_container_width=True):
        try:
            response = httpx.post(
                f"{st.session_state.api_base}/ingest",
                json={},
                timeout=300.0,
            )
            response.raise_for_status()
            st.success(response.json())
        except Exception as exc:
            st.error(str(exc))

    if st.button("Health check", use_container_width=True):
        try:
            response = httpx.get(f"{st.session_state.api_base}/health", timeout=30.0)
            st.json(response.json())
        except Exception as exc:
            st.error(str(exc))

    if st.button("Run evaluation", use_container_width=True):
        try:
            response = httpx.post(
                f"{st.session_state.api_base}/eval",
                json={"run_sample": True},
                timeout=600.0,
            )
            response.raise_for_status()
            st.json(response.json())
        except Exception as exc:
            st.error(str(exc))


for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

prompt = st.chat_input("Ask AgentForge…")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        event_box = st.expander("Agent events", expanded=False)
        assembled = ""
        final_payload = None

        try:
            with httpx.stream(
                "POST",
                f"{st.session_state.api_base}/chat",
                json={
                    "message": prompt,
                    "thread_id": st.session_state.thread_id,
                    "stream": True,
                },
                timeout=600.0,
            ) as response:
                response.raise_for_status()
                event_name = "message"
                for line in response.iter_lines():
                    if not line:
                        continue
                    if line.startswith("event:"):
                        event_name = line.split(":", 1)[1].strip()
                        continue
                    if not line.startswith("data:"):
                        continue
                    data_raw = line.split(":", 1)[1].strip()
                    try:
                        payload = json.loads(data_raw)
                    except json.JSONDecodeError:
                        continue

                    if payload.get("type") == "token":
                        assembled += payload.get("content", "")
                        placeholder.markdown(assembled)
                    elif payload.get("type") == "final":
                        final_payload = payload
                        assembled = payload.get("answer") or assembled
                        placeholder.markdown(assembled)
                    else:
                        event_box.write(payload)
                        st.session_state.events.append(payload)
        except Exception as exc:
            assembled = f"Request failed: {exc}"
            placeholder.error(assembled)

        if final_payload and final_payload.get("citations"):
            st.caption("Citations: " + ", ".join(final_payload["citations"]))

        st.session_state.messages.append({"role": "assistant", "content": assembled})
