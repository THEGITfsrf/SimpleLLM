import json
import re
from typing import Literal

import ollama
from pydantic import BaseModel, Field


class IntentStateOutput(BaseModel):
    intent: Literal[
        "chat",
        "question",
        "technical_comparison",
        "coding",
        "system_status",
        "automation",
        "tool_action",
        "web_lookup",
        "creative",
        "control",
    ] = Field(description="The user's likely intent.")
    urgency: Literal["low", "normal", "high", "critical"] = Field(description="How time-sensitive the request is.")
    complexity: Literal["simple", "moderate", "complex"] = Field(description="How much reasoning is needed.")
    tool_need: Literal["none", "optional", "required"] = Field(description="Whether tools are needed.")
    response_style: Literal["brief", "conversational", "stepwise", "technical", "structured_table", "confirm_then_act"] = Field(
        description="How the assistant should answer."
    )
    assistant_state: Literal[
        "idle_assistant",
        "active_helper",
        "executing_task",
        "monitoring_background",
        "voice_only_mode",
    ] = Field(description="The runtime state this request should move the assistant toward.")
    route: Literal["fast", "thinker"] = Field(description="Compatibility route for Ollama think mode.")
    factual_mode: bool = Field(description="True when the request depends on precise specs, numbers, APIs, benchmarks, or external facts.")
    confidence: float = Field(ge=0.0, le=1.0, description="Classifier confidence.")


DEFAULT_INTENT_STATE = {
    "intent": "question",
    "urgency": "normal",
    "complexity": "simple",
    "tool_need": "optional",
    "response_style": "conversational",
    "assistant_state": "active_helper",
    "route": "fast",
    "factual_mode": False,
    "confidence": 0.45,
}

VALID_FIELDS = {
    "intent": {"chat", "question", "technical_comparison", "coding", "system_status", "automation", "tool_action", "web_lookup", "creative", "control"},
    "urgency": {"low", "normal", "high", "critical"},
    "complexity": {"simple", "moderate", "complex"},
    "tool_need": {"none", "optional", "required"},
    "response_style": {"brief", "conversational", "stepwise", "technical", "structured_table", "confirm_then_act"},
    "assistant_state": {"idle_assistant", "active_helper", "executing_task", "monitoring_background", "voice_only_mode"},
    "route": {"fast", "thinker"},
}


INTENT_DIMENSIONS = {
    "intent": [
        "chat: greetings, casual conversation, personality, small talk",
        "question: normal factual or explanatory request",
        "technical_comparison: compare multiple named products, models, APIs, libraries, hardware, versions, benchmarks, or specs",
        "coding: code generation, debugging, architecture, tests, refactors",
        "system_status: CPU, GPU, RAM, processes, active app, machine state",
        "automation: reminders, repeated checks, background monitoring, scheduled work",
        "tool_action: open apps, write files, shell, clipboard, screenshots, email",
        "web_lookup: current web, news, weather, search, external info",
        "creative: names, stories, images, style, brainstorming",
        "control: new chat, switch model, stop, hold, reroute",
    ],
    "assistant_state": [
        "idle_assistant: no active task",
        "active_helper: answering a direct user request",
        "executing_task: tool use or multi-step work is likely",
        "monitoring_background: continuous observation or future alerting is implied",
        "voice_only_mode: spoken interaction constraints are important",
    ],
    "factual_mode": [
        "true for hardware specs, benchmark numbers, API/library details, medical/legal/financial facts, dates, prices, standards, or anything where numeric precision matters",
        "false for casual chat, preference, drafting, or creative work without factual claims",
    ],
}


def _heuristic_intent_state(user_prompt: str) -> dict:
    text = (user_prompt or "").strip()
    low = text.lower()
    state = dict(DEFAULT_INTENT_STATE)
    comparison_trigger = bool(re.search(r"\b(vs\.?|versus|compare|comparison|difference between|differences between)\b", low))
    factual_trigger = bool(re.search(
        r"\b(specs?|specifications?|benchmark|benchmarks|fps|cuda|vram|gb|ghz|mhz|watt|tdp|"
        r"rtx|gtx|quadro|tesla|gpu|cpu|api|sdk|version|price|release date|medical|legal|"
        r"financial|standard|iso|math)\b",
        low,
    ))
    named_entity_count = len(re.findall(r"\b[A-Z][A-Za-z0-9+-]{1,}\b|\b(?:rtx|gtx|quadro|tesla)\s*\d+[a-z0-9-]*\b", text, re.I))

    if re.fullmatch(r"\s*(hi|hello|hey|thanks|thank you|yo|sup)\s*[.!?]?\s*", low):
        state.update(
            intent="chat",
            urgency="low",
            complexity="simple",
            tool_need="none",
            response_style="brief",
            assistant_state="idle_assistant",
            route="fast",
            factual_mode=False,
            confidence=0.9,
        )
        return state

    if comparison_trigger or (factual_trigger and named_entity_count >= 2):
        state.update(
            intent="technical_comparison",
            urgency="low",
            complexity="moderate",
            tool_need="required" if factual_trigger else "optional",
            response_style="structured_table",
            assistant_state="active_helper",
            route="thinker",
            factual_mode=True,
            confidence=max(state["confidence"], 0.78 if comparison_trigger and factual_trigger else 0.68),
        )

    if re.search(r"\b(cpu|gpu|ram|memory|disk|process|focused window|active app|network|microphone|system)\b", low):
        state.update(
            intent="system_status",
            tool_need="required",
            response_style="brief",
            assistant_state="monitoring_background",
            factual_mode=True,
            confidence=0.72,
        )
    if re.search(r"\b(open|launch|close|kill|stop|write|read|screenshot|clipboard|email|send|delete)\b", low):
        state.update(
            intent="tool_action",
            tool_need="required",
            response_style="confirm_then_act",
            assistant_state="executing_task",
            factual_mode=False,
            confidence=max(state["confidence"], 0.72),
        )
    if re.search(r"\b(debug|fix|code|function|class|api|test|architecture|refactor|optimi[sz]e)\b", low):
        state.update(
            intent="coding",
            complexity="complex",
            response_style="technical",
            assistant_state="executing_task",
            route="thinker",
            factual_mode=True,
            confidence=max(state["confidence"], 0.75),
        )
    if re.search(r"\b(remind|monitor|watch|keep an eye|background|when|if .* then)\b", low):
        state.update(
            intent="automation",
            urgency="normal",
            complexity="moderate",
            tool_need="required",
            response_style="confirm_then_act",
            assistant_state="monitoring_background",
            route="thinker",
            factual_mode=True,
            confidence=max(state["confidence"], 0.76),
        )
    if re.search(r"\b(weather|news|latest|search|look up|current)\b", low):
        state.update(intent="web_lookup", tool_need="required", factual_mode=True, route="thinker", confidence=max(state["confidence"], 0.68))
    if re.search(r"\b(urgent|asap|right now|emergency|critical|immediately)\b", low):
        state["urgency"] = "high"
    if re.search(r"\b(prove|strategy|design|step by step|why|explain deeply|tradeoff|migration)\b", low):
        state.update(complexity="complex", route="thinker", response_style="stepwise", factual_mode=True)
    if re.search(r"\b(new chat|change model|switch model|stop talking|hold on|reroute)\b", low):
        state.update(intent="control", tool_need="none", response_style="brief", assistant_state="voice_only_mode")

    return state


def _extract_json_object(raw_output: str) -> dict:
    raw = (raw_output or "").strip()
    if not raw:
        return {}

    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        pass

    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        candidate = raw[start : end + 1]
        try:
            parsed = json.loads(candidate)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            pass

    repaired = {}
    for key in DEFAULT_INTENT_STATE:
        pattern = rf'"?{re.escape(key)}"?\s*:\s*"([^"\n\r}}]+)'
        match = re.search(pattern, raw)
        if match:
            repaired[key] = match.group(1).strip().strip(",")
    return repaired


def _normalize_intent_state(candidate: dict, fallback: dict) -> dict:
    normalized = dict(fallback)
    for key, value in (candidate or {}).items():
        if key == "confidence":
            try:
                normalized[key] = max(0.0, min(1.0, float(value)))
            except Exception:
                continue
            continue
        if key == "factual_mode":
            if isinstance(value, bool):
                normalized[key] = value
            else:
                normalized[key] = str(value or "").strip().lower() in {"true", "1", "yes", "required"}
            continue
        if key not in VALID_FIELDS:
            continue
        value = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
        if value in VALID_FIELDS[key]:
            normalized[key] = value

    if normalized["intent"] == "technical_comparison":
        normalized["complexity"] = "moderate" if normalized["complexity"] == "simple" else normalized["complexity"]
        normalized["tool_need"] = "required" if normalized["factual_mode"] else "optional"
        normalized["response_style"] = "structured_table"
        normalized["assistant_state"] = "active_helper"
        normalized["route"] = "thinker"

    if normalized["factual_mode"] and normalized["tool_need"] == "none":
        normalized["tool_need"] = "optional"

    if normalized["complexity"] == "complex" or normalized["intent"] in {"coding", "automation", "technical_comparison"}:
        normalized["route"] = "thinker"

    if normalized["confidence"] < 0.75 and normalized["intent"] not in {"chat", "control"}:
        normalized["route"] = "thinker"

    if normalized["confidence"] < 0.5 and normalized["intent"] not in {"chat", "control"}:
        normalized["factual_mode"] = True
        if normalized["tool_need"] == "none":
            normalized["tool_need"] = "optional"
    return normalized


def get_intent_state(user_prompt: str) -> dict:
    """Return rich routing metadata used by the server and voice runtime."""
    fallback = _heuristic_intent_state(user_prompt)
    routes_json = json.dumps(INTENT_DIMENSIONS, indent=2)
    conversation_json = json.dumps([{"role": "user", "content": user_prompt}])
    formatted_prompt = f"""Classify the user's request for a local JARVIS-style assistant.

Use these dimensions:
<dimensions>
{routes_json}
</dimensions>

Return only JSON matching the schema.

Rules:
- Any "A vs B", "compare", "difference between", or spec table request is technical_comparison.
- Set factual_mode=true for specs, benchmark numbers, APIs, dates, prices, standards, or other precision-heavy facts.
- Low confidence is not fast. If confidence is below 0.75, prefer route="thinker" unless this is obvious chat/control.
- technical_comparison should normally use response_style="structured_table" and route="thinker".

<conversation>
{conversation_json}
</conversation>"""

    try:
        response = ollama.generate(
            model="fauxpaslife/arch-router:1.5b",
            prompt=formatted_prompt,
            format=IntentStateOutput.model_json_schema(),
            options={"temperature": 0.0},
        )
        raw_output = response["response"].strip()
        parsed = _extract_json_object(raw_output)
        if not parsed:
            print("Intent classifier returned no parseable JSON; using heuristic fallback.")
            return fallback
        return _normalize_intent_state(parsed, fallback)
    except Exception as e:
        print("Intent classifier failed; using heuristic fallback.")
        print(f"Reason: {e}")
        return fallback


def get_routing_decision(user_prompt: str) -> str:
    """Backward-compatible fast/thinker route."""
    return get_intent_state(user_prompt).get("route", "fast")


if __name__ == "__main__":
    test_cases = [
        "What time is it?",
        "Debug this Python function and explain the likely edge cases.",
        "Watch my GPU and tell me if the same process spikes again.",
        "Open Discord and start voice-only mode.",
        "Why is my Kubernetes ingress giving intermittent 502 errors?",
        "quadro p100 vs rtx 3070 in specs",
    ]

    for query in test_cases:
        print(f"User Query: {query!r}")
        print(json.dumps(get_intent_state(query), indent=2))
