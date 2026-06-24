from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Persona:
    name: str
    tone: str


@dataclass
class Scenario:
    id: str
    category: str
    persona: Persona
    goal: str
    opening_line: str
    volunteer_info: dict[str, str] = field(default_factory=dict)
    constraints: list[str] = field(default_factory=list)
    success_criteria: list[str] = field(default_factory=list)
    edge_behaviors: list[str] = field(default_factory=list)
    min_turns: int = 8
    max_turns: int = 20
    allow_barge_in: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Scenario:
        persona_data = data.get("persona", {})
        return cls(
            id=data["id"],
            category=data.get("category", "general"),
            persona=Persona(
                name=persona_data.get("name", "Alex Patient"),
                tone=persona_data.get("tone", "polite and natural"),
            ),
            goal=data["goal"],
            opening_line=data.get(
                "opening_line", "Hi, I'd like to schedule an appointment."
            ),
            volunteer_info=data.get("volunteer_info", {}),
            constraints=data.get("constraints", []),
            success_criteria=data.get("success_criteria", []),
            edge_behaviors=data.get("edge_behaviors", []),
            min_turns=data.get("min_turns", 8),
            max_turns=data.get("max_turns", 20),
            allow_barge_in=data.get("allow_barge_in", False),
        )


def load_scenario(path: Path) -> Scenario:
    with path.open() as f:
        data = yaml.safe_load(f)
    return Scenario.from_dict(data)


def load_scenarios(directory: Path) -> list[Scenario]:
    scenarios = []
    for path in sorted(directory.glob("*.yaml")):
        scenarios.append(load_scenario(path))
    return scenarios


def build_system_prompt(scenario: Scenario, max_words: int) -> str:
    volunteer_lines = "\n".join(
        f"- {key}: {value}" for key, value in scenario.volunteer_info.items()
    )
    constraints = "\n".join(f"- {c}" for c in scenario.constraints) or "- None"
    edge = "\n".join(f"- {e}" for e in scenario.edge_behaviors) or "- None"

    return f"""You are simulating a real patient calling Pivot Point Orthopedics on the phone.

Persona: {scenario.persona.name}, {scenario.persona.tone}
Your goal: {scenario.goal}

Information you can share when asked:
{volunteer_lines or "- Answer naturally when the agent asks"}

Behavior rules:
- Speak like a real patient on a phone call: short sentences, natural fillers ok ("um", "sure")
- Keep each reply under {max_words} words unless listing specific info (name, DOB, medication)
- Answer the agent's questions directly before pursuing your goal
- Never reveal you are an AI or test bot
- One intent per turn; do not stack multiple questions
- Stay in character as {scenario.persona.name}
- End politely once your goal is achieved or clearly cannot be completed

Constraints:
{constraints}

Special behaviors if triggered:
{edge}

Respond with ONLY what you would say out loud. No stage directions, quotes, or labels."""
