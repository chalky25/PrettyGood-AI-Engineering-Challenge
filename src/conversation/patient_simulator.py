from __future__ import annotations

from dataclasses import dataclass, field

from groq import Groq

from src.config import settings
from src.conversation.scenario import Scenario, build_system_prompt


@dataclass
class Turn:
    role: str  # "patient" or "agent"
    text: str
    timestamp: float = 0.0


@dataclass
class ConversationState:
    scenario: Scenario
    turns: list[Turn] = field(default_factory=list)
    patient_turn_count: int = 0
    complete: bool = False

    def add_agent(self, text: str) -> None:
        if text.strip():
            self.turns.append(Turn(role="agent", text=text.strip()))

    def add_patient(self, text: str) -> None:
        if text.strip():
            self.turns.append(Turn(role="patient", text=text.strip()))
            self.patient_turn_count += 1

    def transcript_text(self) -> str:
        lines = []
        for t in self.turns:
            label = "Patient" if t.role == "patient" else "Agent"
            lines.append(f"{label}: {t.text}")
        return "\n".join(lines)

    def transcript_json(self) -> list[dict]:
        return [{"role": t.role, "text": t.text, "timestamp": t.timestamp} for t in self.turns]

    def should_end(self) -> bool:
        if self.patient_turn_count >= self.scenario.max_turns:
            return True
        if self.patient_turn_count >= self.scenario.min_turns and self.complete:
            return True
        return False


class PatientSimulator:
    def __init__(self, scenario: Scenario):
        self.scenario = scenario
        self.state = ConversationState(scenario=scenario)
        self.client = Groq(api_key=settings.groq_api_key)
        self.system_prompt = build_system_prompt(scenario, settings.max_reply_words)

    def opening_line(self) -> str:
        line = self.scenario.opening_line
        self.state.add_patient(line)
        return line

    def respond_to_agent(self, agent_text: str) -> str:
        self.state.add_agent(agent_text)

        messages = [{"role": "system", "content": self.system_prompt}]
        for turn in self.state.turns:
            if turn.role == "patient":
                messages.append({"role": "assistant", "content": turn.text})
            else:
                messages.append({"role": "user", "content": turn.text})

        response = self.client.chat.completions.create(
            model=settings.groq_model,
            messages=messages,
            temperature=0.7,
            max_tokens=150,
        )
        reply = (response.choices[0].message.content or "").strip()
        reply = reply.strip('"').strip("'")

        lower = reply.lower()
        if any(
            phrase in lower
            for phrase in ("goodbye", "thank you, bye", "thanks, bye", "have a good day")
        ):
            self.state.complete = True

        self.state.add_patient(reply)
        return reply

    def mark_complete(self) -> None:
        self.state.complete = True
