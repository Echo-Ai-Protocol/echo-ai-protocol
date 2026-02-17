from __future__ import annotations

import json
from pathlib import Path

import reference_node as core
import server


def load_sample(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def test_reputation_v1_empty(tmp_path: Path) -> None:
    out = server._compute_reputation(tmp_path / "storage", "did:echo:agent.none")
    assert out["version"] == "echo.reputation.v1"
    assert out["score"] == 0.0
    assert out["receipts_total"] == 0
    assert out["success_receipts"] == 0
    assert out["top_targets"] == []


def test_reputation_v1_with_receipts(tmp_path: Path, sample_dir: Path) -> None:
    storage_root = tmp_path / "storage"
    rr = load_sample(sample_dir / "rr.sample.json")

    rows = []
    for i, verdict in enumerate(["SUCCESS", "SUCCESS", "FAIL", "SUCCESS"], start=1):
        obj = dict(rr)
        obj["rr_id"] = f"echo.rr.rep.v1.{i}"
        obj["issuer_agent_did"] = "did:echo:agent.rep.1"
        obj["target_eo_id"] = "echo.eo.rep.target.1" if i < 4 else "echo.eo.rep.target.2"
        obj["verdict"] = verdict
        obj["outcome_metrics"] = {"effectiveness_score": 0.8 if verdict == "SUCCESS" else 0.4}
        rows.append(obj)

    for obj in rows:
        core.store_object(storage_root=storage_root, object_type="rr", obj=obj)

    out = server._compute_reputation(storage_root, "did:echo:agent.rep.1")
    assert out["version"] == "echo.reputation.v1"
    assert out["receipts_total"] == 4
    assert out["success_receipts"] == 3
    assert out["status_breakdown"]["FAIL"] == 1
    assert 0.0 <= out["score"] <= 1.0
    assert out["evidence_factor"] > 0.0
    assert len(out["top_targets"]) == 2
    assert out["top_targets"][0]["target_eo_id"] == "echo.eo.rep.target.1"
    assert out["top_targets"][0]["receipts_total"] == 3
