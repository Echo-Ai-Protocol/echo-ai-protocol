"""Simulation metrics contract helpers for Hybrid v1 observability."""

from __future__ import annotations

from typing import Any, Dict, Optional


SIM_METRICS_CONTRACT_VERSION = "echo.sim.metrics.v1"

# Canonical v1 keys and supported legacy aliases.
SIM_METRIC_ALIASES: Dict[str, tuple[str, ...]] = {
    "time_to_find_ticks": ("time_to_find_ticks", "D2_time_to_find_ticks"),
    "useful_hit_rate_top5_pct": ("useful_hit_rate_top5_pct", "useful_hit_rate_top5", "D1_useful_top5"),
    "false_promotion_rate_pct": ("false_promotion_rate_pct", "T1_false_promotion_rate"),
    "missed_promotion_rate_pct": ("missed_promotion_rate_pct", "T2_missed_promotion_rate"),
    "spam_survival_rate_pct": ("spam_survival_rate_pct", "A1_spam_survival_rate"),
}

# Advisory thresholds (not hard enforcement). Used for quick health signals.
SIM_METRIC_TARGETS: Dict[str, float] = {
    "max_time_to_find_ticks": 48.0,
    "min_useful_hit_rate_top5_pct": 60.0,
    "max_false_promotion_rate_pct": 5.0,
    "max_missed_promotion_rate_pct": 40.0,
    "max_spam_survival_rate_pct": 30.0,
}


def _as_float(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _normalize_percent(value: float) -> float:
    # Accept both ratios (0..1) and percentages (0..100).
    if 0.0 <= value <= 1.0:
        value *= 100.0
    if value < 0.0:
        value = 0.0
    if value > 100.0:
        value = 100.0
    return round(value, 4)


def _pick_first_numeric(payload: Dict[str, Any], aliases: tuple[str, ...]) -> Optional[float]:
    for name in aliases:
        value = _as_float(payload.get(name))
        if value is not None:
            return value
    return None


def extract_sim_metrics_v1(report: Dict[str, Any]) -> Optional[Dict[str, float]]:
    if not isinstance(report, dict):
        return None
    raw = report.get("metrics")
    if not isinstance(raw, dict):
        return None

    ttf = _pick_first_numeric(raw, SIM_METRIC_ALIASES["time_to_find_ticks"])
    useful = _pick_first_numeric(raw, SIM_METRIC_ALIASES["useful_hit_rate_top5_pct"])
    false_prom = _pick_first_numeric(raw, SIM_METRIC_ALIASES["false_promotion_rate_pct"])
    missed_prom = _pick_first_numeric(raw, SIM_METRIC_ALIASES["missed_promotion_rate_pct"])
    spam = _pick_first_numeric(raw, SIM_METRIC_ALIASES["spam_survival_rate_pct"])

    if None in {ttf, useful, false_prom, missed_prom, spam}:
        return None

    return {
        "time_to_find_ticks": round(max(0.0, float(ttf)), 4),
        "useful_hit_rate_top5_pct": _normalize_percent(float(useful)),
        "false_promotion_rate_pct": _normalize_percent(float(false_prom)),
        "missed_promotion_rate_pct": _normalize_percent(float(missed_prom)),
        "spam_survival_rate_pct": _normalize_percent(float(spam)),
    }


def evaluate_sim_metrics_v1(metrics: Dict[str, float]) -> Dict[str, Any]:
    checks = {
        "time_to_find_ticks": {
            "value": metrics["time_to_find_ticks"],
            "target": {"op": "<=", "value": SIM_METRIC_TARGETS["max_time_to_find_ticks"]},
            "pass": metrics["time_to_find_ticks"] <= SIM_METRIC_TARGETS["max_time_to_find_ticks"],
        },
        "useful_hit_rate_top5_pct": {
            "value": metrics["useful_hit_rate_top5_pct"],
            "target": {"op": ">=", "value": SIM_METRIC_TARGETS["min_useful_hit_rate_top5_pct"]},
            "pass": metrics["useful_hit_rate_top5_pct"] >= SIM_METRIC_TARGETS["min_useful_hit_rate_top5_pct"],
        },
        "false_promotion_rate_pct": {
            "value": metrics["false_promotion_rate_pct"],
            "target": {"op": "<=", "value": SIM_METRIC_TARGETS["max_false_promotion_rate_pct"]},
            "pass": metrics["false_promotion_rate_pct"] <= SIM_METRIC_TARGETS["max_false_promotion_rate_pct"],
        },
        "missed_promotion_rate_pct": {
            "value": metrics["missed_promotion_rate_pct"],
            "target": {"op": "<=", "value": SIM_METRIC_TARGETS["max_missed_promotion_rate_pct"]},
            "pass": metrics["missed_promotion_rate_pct"] <= SIM_METRIC_TARGETS["max_missed_promotion_rate_pct"],
        },
        "spam_survival_rate_pct": {
            "value": metrics["spam_survival_rate_pct"],
            "target": {"op": "<=", "value": SIM_METRIC_TARGETS["max_spam_survival_rate_pct"]},
            "pass": metrics["spam_survival_rate_pct"] <= SIM_METRIC_TARGETS["max_spam_survival_rate_pct"],
        },
    }
    return {
        "overall_pass": all(item["pass"] for item in checks.values()),
        "checks": checks,
    }

