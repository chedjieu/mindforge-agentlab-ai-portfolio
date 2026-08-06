"""Vertex Agent Engine deploy scaffold."""

from __future__ import annotations

import os

from app.graph import SAMPLE_CLIENT, SAMPLE_PACK, build_graph, make_initial_state


def main() -> None:
    os.environ.setdefault("RFAI_MODEL", "fake")
    print("Vertex Agent Engine scaffold — local smoke with fake model")
    g = build_graph()
    state = make_initial_state("RF-VTX", SAMPLE_PACK, SAMPLE_CLIENT)
    config = {"configurable": {"thread_id": "vtx-demo"}}
    for _ in g.stream(state, config, stream_mode="updates"):
        pass
    print("paused_or_done", g.get_state(config).values.get("domain"))


if __name__ == "__main__":
    main()
