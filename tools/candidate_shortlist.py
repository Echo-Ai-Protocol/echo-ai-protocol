#!/usr/bin/env python3
"""Build a prioritized external AI candidate shortlist from CSV."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


SCORE_FIELDS = (
    "technical_fit",
    "readiness",
    "freshness",
    "feedback_quality",
    "strategic_value",
)

LANES = ("code", "research", "ops")


def _as_int(value: str) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def load_rows(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = [dict(r) for r in reader]
    for row in rows:
        total = sum(_as_int(row.get(name, "0")) for name in SCORE_FIELDS)
        row["score_total"] = total
    return rows


def lane_balanced_top(
    rows: List[Dict[str, Any]],
    top_n: int,
    min_code: int,
    min_research: int,
    min_ops: int,
) -> List[Dict[str, Any]]:
    by_score = sorted(rows, key=lambda r: (-int(r.get("score_total", 0)), r.get("candidate_id", "")))
    out: List[Dict[str, Any]] = []
    used_ids = set()

    minima: List[Tuple[str, int]] = [
        ("code", max(0, min_code)),
        ("research", max(0, min_research)),
        ("ops", max(0, min_ops)),
    ]
    for lane, required in minima:
        picks = [r for r in by_score if r.get("lane") == lane and r.get("candidate_id") not in used_ids]
        for row in picks[:required]:
            out.append(row)
            used_ids.add(row.get("candidate_id"))

    remaining = [r for r in by_score if r.get("candidate_id") not in used_ids]
    for row in remaining:
        if len(out) >= top_n:
            break
        out.append(row)
        used_ids.add(row.get("candidate_id"))

    return out[:top_n]


def parse_args() -> argparse.Namespace:
    repo = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Create ranked external AI shortlist from CSV")
    parser.add_argument(
        "--input",
        default=str(repo / "examples" / "integration" / "candidate_pipeline.template.csv"),
    )
    parser.add_argument(
        "--output",
        default=str(repo / "tools" / "out" / "candidate_shortlist.json"),
    )
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--min-code", type=int, default=3)
    parser.add_argument("--min-research", type=int, default=3)
    parser.add_argument("--min-ops", type=int, default=2)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    in_path = Path(args.input).expanduser().resolve()
    out_path = Path(args.output).expanduser().resolve()

    if not in_path.exists():
        print(f"FAIL: input CSV not found: {in_path}")
        return 2

    rows = load_rows(in_path)
    shortlist = lane_balanced_top(
        rows=rows,
        top_n=max(1, int(args.top_n)),
        min_code=int(args.min_code),
        min_research=int(args.min_research),
        min_ops=int(args.min_ops),
    )

    payload = {
        "version": "echo.integration.shortlist.v1",
        "input": str(in_path),
        "total_candidates": len(rows),
        "shortlist_count": len(shortlist),
        "constraints": {
            "top_n": int(args.top_n),
            "min_code": int(args.min_code),
            "min_research": int(args.min_research),
            "min_ops": int(args.min_ops),
        },
        "shortlist": shortlist,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"WROTE: {out_path}")
    print(f"SHORTLIST_COUNT: {len(shortlist)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
