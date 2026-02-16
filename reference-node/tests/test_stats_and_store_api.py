from __future__ import annotations

import json
import os
from pathlib import Path

import reference_node as core


def load_sample(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def test_get_object_and_stats(tmp_path: Path, sample_dir: Path) -> None:
    storage_root = tmp_path / "storage"

    eo = load_sample(sample_dir / "eo.sample.json")
    rr = load_sample(sample_dir / "rr.sample.json")

    core.store_object(storage_root=storage_root, object_type="eo", obj=eo)
    core.store_object(storage_root=storage_root, object_type="rr", obj=rr)

    fetched = core.get_object(storage_root, "eo", eo["eo_id"])
    assert fetched["eo_id"] == eo["eo_id"]

    stats = core.compute_stats(storage_root)
    assert stats["objects"]["counts"]["eo"] == 1
    assert stats["objects"]["counts"]["rr"] == 1
    assert stats["objects"]["total"] == 2


def test_bundle_payload_export_import(tmp_path: Path, manifest_path: Path, schemas_dir: Path, sample_dir: Path) -> None:
    src_storage = tmp_path / "src_storage"
    dst_storage = tmp_path / "dst_storage"

    eo = load_sample(sample_dir / "eo.sample.json")
    core.store_object(storage_root=src_storage, object_type="eo", obj=eo)

    bundle = core.export_bundle_payload(
        storage_root=src_storage,
        manifest_path=manifest_path,
        object_type="eo",
    )
    assert len(bundle["objects"]) == 1

    imported = core.import_bundle_payload(
        storage_root=dst_storage,
        manifest_path=manifest_path,
        schemas_dir=schemas_dir,
        bundle=bundle,
        skip_signature=False,
    )
    assert imported == 1

    stats = core.compute_stats(dst_storage)
    assert stats["objects"]["counts"]["eo"] == 1


def test_stats_include_latest_simulation_report(tmp_path: Path, sample_dir: Path) -> None:
    storage_root = tmp_path / "storage"
    tools_out = tmp_path / "tools_out"
    tools_out.mkdir(parents=True, exist_ok=True)

    eo = load_sample(sample_dir / "eo.sample.json")
    core.store_object(storage_root=storage_root, object_type="eo", obj=eo)

    report_path = tools_out / "sim_report_state.template.json"
    report_path.write_text(
        json.dumps(
            {
                "metrics": {
                    "D2_time_to_find_ticks": 2,
                    "D1_useful_top5": 0.8,
                    "T1_false_promotion_rate": 0.04,
                    "T2_missed_promotion_rate": 0.2,
                    "A1_spam_survival_rate": 0.3,
                },
                "reference_node": {"enabled": True},
            }
        ),
        encoding="utf-8",
    )

    stats = core.compute_stats(storage_root, tools_out_dir=tools_out)
    sim = stats["simulator"]
    assert sim["found"] is True
    assert sim["path"] == str(report_path)
    assert isinstance(sim["report"], dict)
    assert sim["contract_version"] == core.SIM_METRICS_CONTRACT_VERSION
    assert sim["metrics_v1"]["time_to_find_ticks"] == 2.0
    assert sim["metrics_v1"]["useful_hit_rate_top5_pct"] == 80.0
    assert sim["metrics_v1"]["false_promotion_rate_pct"] == 4.0
    assert isinstance(sim["evaluation_v1"]["overall_pass"], bool)


def test_stats_include_simulation_history(tmp_path: Path) -> None:
    storage_root = tmp_path / "storage"
    tools_out = tmp_path / "tools_out"
    tools_out.mkdir(parents=True, exist_ok=True)

    older = tools_out / "sim_report_old.json"
    newer = tools_out / "sim_report_new.json"

    older.write_text(
        json.dumps(
            {
                "metrics": {
                    "time_to_find_ticks": 20,
                    "useful_hit_rate_top5_pct": 70,
                    "false_promotion_rate_pct": 2,
                    "missed_promotion_rate_pct": 25,
                    "spam_survival_rate_pct": 21,
                }
            }
        ),
        encoding="utf-8",
    )
    newer.write_text(
        json.dumps(
            {
                "metrics": {
                    "time_to_find_ticks": 10,
                    "useful_hit_rate_top5_pct": 80,
                    "false_promotion_rate_pct": 1,
                    "missed_promotion_rate_pct": 18,
                    "spam_survival_rate_pct": 17,
                }
            }
        ),
        encoding="utf-8",
    )
    os.utime(older, (1000, 1000))
    os.utime(newer, (2000, 2000))

    stats = core.compute_stats(storage_root, tools_out_dir=tools_out, history_limit=2)
    history = stats["simulator_history"]
    assert len(history) == 2
    assert history[0]["path"] == str(newer)
    assert history[1]["path"] == str(older)
    assert history[0]["metrics_v1"]["time_to_find_ticks"] == 10.0
