#!/usr/bin/env python3
"""Render a personalized outreach message for an external AI candidate."""

from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    repo = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Render external AI outreach message")
    parser.add_argument("--integration-id", required=True, help="Integration id, e.g. ext-ai-001")
    parser.add_argument("--agent-name", required=True, help="Project or agent name")
    parser.add_argument("--lane", choices=("code", "research", "ops"), required=True)
    parser.add_argument(
        "--template",
        default=str(repo / "examples" / "integration" / "outreach_message.template.md"),
    )
    parser.add_argument(
        "--output",
        default=str(repo / "tools" / "out" / "outreach_message.md"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    template_path = Path(args.template).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    if not template_path.exists():
        print(f"FAIL: template not found: {template_path}")
        return 2

    text = template_path.read_text(encoding="utf-8")
    text = text.replace("{{integration_id}}", args.integration_id)
    text = text.replace("{{agent_or_project_name}}", args.agent_name)
    text = text.replace("{{lane}}", args.lane)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")
    print(f"WROTE: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
