"""Run each selected sister project's pytest suite from the workspace root."""

from __future__ import annotations

import pytest

from suite_runner import run_in, selected_packages


@pytest.mark.parametrize("pkg", selected_packages())
def test_sister_project_pytest(pkg: str) -> None:
    code = run_in(pkg, ["pytest"])
    assert code == 0, f"{pkg} pytest failed with exit {code}"
