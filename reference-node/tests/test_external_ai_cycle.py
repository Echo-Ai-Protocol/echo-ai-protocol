from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _write_min_matrix(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "# External AI Compatibility Matrix",
                "",
                "| Integration ID | Agent | Lane | Protocol | Gate1 | Gate2 | Gate3 | Gate4 | Gate5 | Status | Last Verified | Blocking Issue |",
                "|---|---|---|---|---|---|---|---|---|---|---|---|",
                "",
                "## Update Policy",
                "- Keep updates machine-generated where possible.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_external_ai_cycle_skip_gate_fast_path(repo_root: Path) -> None:
    out_dir = repo_root / "tools" / "out" / "test-cycle-fast"
    out_dir.mkdir(parents=True, exist_ok=True)
    matrix_path = out_dir / "matrix.md"
    _write_min_matrix(matrix_path)

    shortlist_out = out_dir / "shortlist.json"
    report_out = out_dir / "zero_touch_ext-ai-fast.json"
    outreach_out = out_dir / "outreach.md"
    kpi_out = out_dir / "kpi.json"
    summary_out = out_dir / "summary.json"
    empty_glob = str(out_dir / "history" / "zero_touch_*.json")

    cmd = [
        sys.executable,
        str(repo_root / "tools" / "external_ai_cycle.py"),
        "--integration-id",
        "ext-ai-fast",
        "--agent-name",
        "Fast Candidate",
        "--lane",
        "code",
        "--skip-gate",
        "--candidate-input",
        str(repo_root / "examples" / "integration" / "candidate_pipeline.template.csv"),
        "--shortlist-out",
        str(shortlist_out),
        "--report-out",
        str(report_out),
        "--matrix",
        str(matrix_path),
        "--outreach-template",
        str(repo_root / "examples" / "integration" / "outreach_message.template.md"),
        "--outreach-out",
        str(outreach_out),
        "--kpi-out",
        str(kpi_out),
        "--kpi-glob",
        empty_glob,
        "--summary-out",
        str(summary_out),
    ]
    result = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + "\n" + result.stderr

    assert shortlist_out.exists()
    assert outreach_out.exists()
    assert kpi_out.exists()
    assert summary_out.exists()

    summary = json.loads(summary_out.read_text(encoding="utf-8"))
    assert summary["overall_ok"] is True
    step_status = {step["name"]: step["status"] for step in summary["steps"]}
    assert step_status["candidate-shortlist"] == "ok"
    assert step_status["zero-touch-gate"] == "skipped"
    assert step_status["external-kpi-summary"] == "ok"

    kpi = json.loads(kpi_out.read_text(encoding="utf-8"))
    assert int(kpi["integrations_total"]) == 0


def test_external_ai_cycle_uses_existing_report_for_matrix_sync(repo_root: Path) -> None:
    out_dir = repo_root / "tools" / "out" / "test-cycle-sync"
    out_dir.mkdir(parents=True, exist_ok=True)
    matrix_path = out_dir / "matrix.md"
    _write_min_matrix(matrix_path)

    template_report = json.loads(
        (repo_root / "examples" / "integration" / "pilot_feedback.template.json").read_text(encoding="utf-8")
    )
    template_report["integration_id"] = "ext-ai-sync"
    template_report["agent_name"] = "Sync Candidate"
    report_out = out_dir / "zero_touch_ext-ai-sync.json"
    report_out.write_text(json.dumps(template_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary_out = out_dir / "summary.json"
    kpi_out = out_dir / "kpi.json"
    cmd = [
        sys.executable,
        str(repo_root / "tools" / "external_ai_cycle.py"),
        "--integration-id",
        "ext-ai-sync",
        "--agent-name",
        "Sync Candidate",
        "--lane",
        "code",
        "--skip-gate",
        "--candidate-input",
        str(repo_root / "examples" / "integration" / "candidate_pipeline.template.csv"),
        "--shortlist-out",
        str(out_dir / "shortlist.json"),
        "--report-out",
        str(report_out),
        "--matrix",
        str(matrix_path),
        "--outreach-template",
        str(repo_root / "examples" / "integration" / "outreach_message.template.md"),
        "--outreach-out",
        str(out_dir / "outreach.md"),
        "--kpi-out",
        str(kpi_out),
        "--kpi-glob",
        str(out_dir / "history" / "zero_touch_*.json"),
        "--summary-out",
        str(summary_out),
    ]
    result = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + "\n" + result.stderr

    matrix_text = matrix_path.read_text(encoding="utf-8")
    assert "| ext-ai-sync | Sync Candidate | code | ECHO/1.0 |" in matrix_text

    summary = json.loads(summary_out.read_text(encoding="utf-8"))
    step_status = {step["name"]: step["status"] for step in summary["steps"]}
    assert step_status["pilot-feedback-lint"] == "ok"
    assert step_status["sync-compatibility-matrix"] == "ok"
