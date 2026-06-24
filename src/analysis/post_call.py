from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from groq import Groq

from src.config import settings
from src.conversation.scenario import Scenario


@dataclass
class BugFinding:
    title: str
    severity: str
    timestamp: str
    evidence_quote: str
    expected_behavior: str
    reproducibility: str


@dataclass
class CallAnalysis:
    scenario_id: str
    bugs: list[BugFinding]
    scenario_passed: bool
    conversation_quality: int
    notes: str


def save_transcript(
    call_id: str,
    transcript_text: str,
    metadata: dict,
    artifacts_dir: Path | None = None,
) -> Path:
    base = artifacts_dir or Path(settings.artifacts_dir) / "transcripts"
    base.mkdir(parents=True, exist_ok=True)

    txt_path = base / f"{call_id}.txt"
    json_path = base / f"{call_id}.json"

    txt_path.write_text(transcript_text)
    json_path.write_text(json.dumps(metadata, indent=2))
    return txt_path


def analyze_call(scenario: Scenario, transcript: str) -> CallAnalysis:
    client = Groq(api_key=settings.groq_api_key)
    criteria = "\n".join(f"- {c}" for c in scenario.success_criteria)

    prompt = f"""You are evaluating a phone call between a simulated patient and an AI medical office agent.

Scenario ID: {scenario.id}
Scenario goal: {scenario.goal}
Success criteria:
{criteria}

Transcript:
{transcript}

Analyze the AGENT's behavior (not the patient). Return ONLY valid JSON with this shape:
{{
  "bugs": [
    {{
      "title": "short summary",
      "severity": "High|Medium|Low",
      "timestamp": "approximate position e.g. mid-call or turn 5",
      "evidence_quote": "exact quote from agent",
      "expected_behavior": "what agent should have done",
      "reproducibility": "scenario id and steps to reproduce"
    }}
  ],
  "scenario_passed": true,
  "conversation_quality": 4,
  "notes": "brief overall assessment"
}}

Focus on high-severity healthcare voice agent bugs: scheduling outside hours, missing verification, hallucinated facts, poor error recovery, talk-over issues. Return empty bugs array if none found."""

    response = client.chat.completions.create(
        model=settings.groq_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=1500,
    )
    raw = response.choices[0].message.content or "{}"
    raw = re.sub(r"^```json\s*|\s*```$", "", raw.strip())

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {
            "bugs": [],
            "scenario_passed": False,
            "conversation_quality": 3,
            "notes": "Analysis parse failed",
        }

    bugs = [
        BugFinding(
            title=b.get("title", "Unknown"),
            severity=b.get("severity", "Medium"),
            timestamp=b.get("timestamp", ""),
            evidence_quote=b.get("evidence_quote", ""),
            expected_behavior=b.get("expected_behavior", ""),
            reproducibility=b.get("reproducibility", scenario.id),
        )
        for b in data.get("bugs", [])
    ]

    return CallAnalysis(
        scenario_id=scenario.id,
        bugs=bugs,
        scenario_passed=bool(data.get("scenario_passed", False)),
        conversation_quality=int(data.get("conversation_quality", 3)),
        notes=data.get("notes", ""),
    )


def save_scenario_result(call_id: str, analysis: CallAnalysis) -> Path:
    out_dir = Path(settings.artifacts_dir) / "scenario_results"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{call_id}.json"
    payload = {
        "scenario_id": analysis.scenario_id,
        "scenario_passed": analysis.scenario_passed,
        "conversation_quality": analysis.conversation_quality,
        "notes": analysis.notes,
        "bugs": [
            {
                "title": b.title,
                "severity": b.severity,
                "timestamp": b.timestamp,
                "evidence_quote": b.evidence_quote,
                "expected_behavior": b.expected_behavior,
                "reproducibility": b.reproducibility,
            }
            for b in analysis.bugs
        ],
    }
    path.write_text(json.dumps(payload, indent=2))
    return path


def append_to_bug_report(analyses: list[CallAnalysis], report_path: Path) -> None:
    lines = ["# Bug Report\n"]
    seen = set()

    for analysis in analyses:
        for bug in analysis.bugs:
            key = (bug.title, bug.evidence_quote)
            if key in seen:
                continue
            seen.add(key)
            lines.append(f"## {bug.title}\n")
            lines.append(f"- **Severity:** {bug.severity}")
            lines.append(f"- **Call:** {analysis.scenario_id} ({bug.timestamp})")
            lines.append(f"- **Details:** {bug.evidence_quote}")
            lines.append(f"- **Expected:** {bug.expected_behavior}")
            lines.append(f"- **Repro:** {bug.reproducibility}\n")

    if len(lines) == 1:
        lines.append("_No bugs detected yet. Run batch calls and re-analyze._\n")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines))
