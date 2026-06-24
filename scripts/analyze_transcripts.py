#!/usr/bin/env python3
"""Analyze saved transcripts and regenerate bug report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.analysis.post_call import analyze_call, append_to_bug_report, save_scenario_result
from src.conversation.scenario import load_scenario


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--transcripts",
        type=Path,
        default=Path("artifacts/transcripts"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/bug_report.md"),
    )
    args = parser.parse_args()

    analyses = []
    for json_path in sorted(args.transcripts.glob("*.json")):
        data = json.loads(json_path.read_text())
        scenario_id = data.get("scenario_id")
        if not scenario_id:
            continue
        scenario_path = Path("scenarios") / f"{scenario_id}.yaml"
        if not scenario_path.exists():
            continue
        scenario = load_scenario(scenario_path)
        txt_path = json_path.with_suffix(".txt")
        if not txt_path.exists():
            continue
        transcript = txt_path.read_text()
        if not transcript.strip():
            continue
        analysis = analyze_call(scenario, transcript)
        save_scenario_result(json_path.stem, analysis)
        analyses.append(analysis)
        print(f"{json_path.stem}: quality={analysis.conversation_quality}, bugs={len(analysis.bugs)}")

    append_to_bug_report(analyses, args.output)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
