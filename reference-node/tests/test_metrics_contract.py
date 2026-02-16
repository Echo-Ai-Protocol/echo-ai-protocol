from __future__ import annotations

import reference_node as core


def test_extract_sim_metrics_v1_from_canonical_payload() -> None:
    report = {
        "metrics": {
            "time_to_find_ticks": 12,
            "useful_hit_rate_top5_pct": 84.5,
            "false_promotion_rate_pct": 3.2,
            "missed_promotion_rate_pct": 11.0,
            "spam_survival_rate_pct": 24.0,
        }
    }

    metrics = core.extract_sim_metrics_v1(report)
    assert metrics is not None
    assert metrics["time_to_find_ticks"] == 12.0
    assert metrics["useful_hit_rate_top5_pct"] == 84.5
    assert metrics["false_promotion_rate_pct"] == 3.2
    assert metrics["missed_promotion_rate_pct"] == 11.0
    assert metrics["spam_survival_rate_pct"] == 24.0


def test_extract_sim_metrics_v1_from_legacy_payload_ratio() -> None:
    report = {
        "metrics": {
            "D2_time_to_find_ticks": 7,
            "D1_useful_top5": 0.8,
            "T1_false_promotion_rate": 0.03,
            "T2_missed_promotion_rate": 0.15,
            "A1_spam_survival_rate": 0.25,
        }
    }

    metrics = core.extract_sim_metrics_v1(report)
    assert metrics is not None
    assert metrics["time_to_find_ticks"] == 7.0
    assert metrics["useful_hit_rate_top5_pct"] == 80.0
    assert metrics["false_promotion_rate_pct"] == 3.0
    assert metrics["missed_promotion_rate_pct"] == 15.0
    assert metrics["spam_survival_rate_pct"] == 25.0


def test_evaluate_sim_metrics_v1_returns_checks() -> None:
    metrics = {
        "time_to_find_ticks": 20.0,
        "useful_hit_rate_top5_pct": 90.0,
        "false_promotion_rate_pct": 3.0,
        "missed_promotion_rate_pct": 20.0,
        "spam_survival_rate_pct": 18.0,
    }
    result = core.evaluate_sim_metrics_v1(metrics)
    assert isinstance(result, dict)
    assert "checks" in result
    assert isinstance(result["overall_pass"], bool)


def test_trend_sim_metrics_v1_direction() -> None:
    previous = {
        "time_to_find_ticks": 20.0,
        "useful_hit_rate_top5_pct": 70.0,
        "false_promotion_rate_pct": 4.0,
        "missed_promotion_rate_pct": 30.0,
        "spam_survival_rate_pct": 25.0,
    }
    latest = {
        "time_to_find_ticks": 15.0,
        "useful_hit_rate_top5_pct": 75.0,
        "false_promotion_rate_pct": 3.5,
        "missed_promotion_rate_pct": 35.0,
        "spam_survival_rate_pct": 25.0,
    }
    trend = core.trend_sim_metrics_v1(latest, previous)
    assert trend["delta"]["time_to_find_ticks"] == -5.0
    assert trend["direction"]["time_to_find_ticks"] == "improved"
    assert trend["direction"]["useful_hit_rate_top5_pct"] == "improved"
    assert trend["direction"]["false_promotion_rate_pct"] == "improved"
    assert trend["direction"]["missed_promotion_rate_pct"] == "regressed"
    assert trend["direction"]["spam_survival_rate_pct"] == "same"
