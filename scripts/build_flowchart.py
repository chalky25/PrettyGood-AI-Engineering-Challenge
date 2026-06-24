#!/usr/bin/env python3
"""Build agent flowchart markdown from saved call transcripts."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def parse_transcript(text: str) -> list[tuple[str, str]]:
    turns = []
    for line in text.strip().splitlines():
        if line.startswith("Agent:"):
            turns.append(("agent", line[6:].strip()))
        elif line.startswith("Patient:"):
            turns.append(("patient", line[8:].strip()))
    return turns


def to_mermaid(transcripts: dict[str, list[tuple[str, str]]]) -> str:
    lines = ["flowchart TD"]
    node_id = 0
    id_map: dict[str, str] = {}

    for scenario_id, turns in transcripts.items():
        prev = None
        for role, text in turns:
            if role != "agent":
                continue
            label = text[:60].replace('"', "'")
            if len(text) > 60:
                label += "..."
            nid = f"n{node_id}"
            node_id += 1
            lines.append(f'    {nid}["{label}"]')
            if prev:
                lines.append(f"    {prev} --> {nid}")
            prev = nid
            id_map.setdefault(scenario_id, []).append((nid, text))

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--transcripts", type=Path, default=Path("artifacts/transcripts"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/agent_flowchart.md"))
    args = parser.parse_args()

    by_scenario: dict[str, list[tuple[str, str]]] = {}
    sections = ["# Agent Call Flow — Pivot Point Orthopedics\n"]

    for txt_path in sorted(args.transcripts.glob("*.txt")):
        text = txt_path.read_text()
        if not text.strip():
            continue
        json_path = txt_path.with_suffix(".json")
        scenario_id = txt_path.stem
        if json_path.exists():
            meta = json.loads(json_path.read_text())
            scenario_id = meta.get("scenario_id", scenario_id)

        turns = parse_transcript(text)
        by_scenario[scenario_id] = turns

        sections.append(f"## {scenario_id} (`{txt_path.name}`)\n")
        sections.append("```mermaid")
        lines = ["flowchart TD"]
        prev = None
        for i, (role, t) in enumerate(turns):
            label = f"{role[:1].upper()}: {t[:50]}".replace('"', "'")
            nid = f"{scenario_id.replace('-', '_')}_{i}"
            lines.append(f'    {nid}["{label}"]')
            if prev:
                lines.append(f"    {prev} --> {nid}")
            prev = nid
        sections.append("\n".join(lines))
        sections.append("```\n")

        sections.append("### Transcript\n")
        sections.append(f"```\n{text.strip()}\n```\n")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(sections))
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
