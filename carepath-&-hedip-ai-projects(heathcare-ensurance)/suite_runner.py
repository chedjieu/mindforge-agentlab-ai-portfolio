"""Dispatch suite-root quality/run commands into sister packages."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

PACKAGES: tuple[tuple[str, str], ...] = (
    ("RAIP_MODEL", "raip"),
    ("CAREPATH_MODEL", "carepath-ai"),
    ("HEDIP_MODEL", "hedip"),
)

FAKE_ENV = {
    "raip": {
        "RAIP_MODEL": "fake",
        "RAIP_JUDGE_MODEL": "fake",
        "RAIP_EMBEDDINGS": "fake",
        "RAIP_HITL": "evaluate",
    },
    "carepath-ai": {"CAREPATH_MODEL": "fake"},
    "hedip": {"HEDIP_MODEL": "fake"},
}

UV_EXTRA = {
    "carepath-ai": ["--extra", "dev"],
    "hedip": ["--extra", "dev"],
}


def selected_packages() -> list[str]:
    chosen = [pkg for env_name, pkg in PACKAGES if os.environ.get(env_name)]
    return chosen or [pkg for _, pkg in PACKAGES]


def _child_env(pkg: str) -> dict[str, str]:
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)
    env.pop("UV_PROJECT_ENVIRONMENT", None)
    for key, value in FAKE_ENV[pkg].items():
        env.setdefault(key, value)
    return env


def _python_module_args(argv: list[str]) -> list[str]:
    if argv[:1] == ["pytest"]:
        return ["-m", "pytest", *argv[1:]]
    if argv[:2] == ["python", "-m"]:
        return ["-m", *argv[2:]]
    if argv[:1] == ["python"]:
        return argv[1:]
    return argv


def _run_raip(argv: list[str]) -> int:
    pkg_dir = ROOT / "raip"
    py_args = _python_module_args(argv)
    if os.name == "nt":
        script = pkg_dir / "scripts" / "with-python.ps1"
        cmd = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            *py_args,
        ]
    else:
        script = pkg_dir / "scripts" / "with-python.sh"
        cmd = ["bash", str(script), *py_args]
    print(f"\n==> raip: {' '.join(py_args)}", flush=True)
    return subprocess.call(cmd, cwd=pkg_dir, env=_child_env("raip"))


def run_in(pkg: str, argv: list[str]) -> int:
    if pkg == "raip":
        return _run_raip(argv)
    extra = UV_EXTRA.get(pkg, [])
    cmd = ["uv", "run", "--directory", str(ROOT / pkg), *extra, *argv]
    print(f"\n==> {pkg}: {' '.join(argv)}", flush=True)
    return subprocess.call(cmd, cwd=ROOT / pkg, env=_child_env(pkg))


def run_all(argv: list[str]) -> int:
    code = 0
    for pkg in selected_packages():
        code = run_in(pkg, argv) or code
    return code


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if not args:
        args = ["pytest"]
    return run_all(args)


if __name__ == "__main__":
    raise SystemExit(main())
