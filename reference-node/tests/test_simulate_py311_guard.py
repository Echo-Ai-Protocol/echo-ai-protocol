from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_simulate_module_import_and_params_isolation(repo_root: Path) -> None:
    script = (
        "import sys\n"
        "import importlib.util\n"
        "import pathlib\n"
        "p = pathlib.Path(sys.argv[1])\n"
        "spec = importlib.util.spec_from_file_location('echo_simulate', p)\n"
        "mod = importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(mod)\n"
        "a = mod.SimParams()\n"
        "b = mod.SimParams()\n"
        "a.promo.min_success_rate = 0.5\n"
        "assert b.promo.min_success_rate == 0.70\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script, str(repo_root / "tools" / "simulate.py")],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_simulate_help_runs(repo_root: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(repo_root / "tools" / "simulate.py"), "--help"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "usage: simulate.py" in result.stdout
    assert "--use-reference-node" in result.stdout
