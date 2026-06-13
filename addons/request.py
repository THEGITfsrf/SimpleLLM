import re
import time

description = "VC-only command intake (activation bypass mode) with strict gating to prevent accidental triggers."
args = {
    "text": {"type": "string", "description": "Raw speech-to-text command"},
    "voice_context_verified": {"type": "boolean", "description": "Must be true for VC-only access"},
    "bypass_activation": {"type": "boolean", "description": "Allow no wake-word mode when true"},
    "safety_phrase": {"type": "string", "description": "Optional safety token phrase; default DIRECT-MIC"},
}
required = ["text", "voice_context_verified"]


def _normalize_command(text):
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    return cleaned


def main(text, voice_context_verified, bypass_activation=False, safety_phrase="DIRECT-MIC"):
    try:
        if not bool(voice_context_verified):
            return {"accepted": False, "reason": "Rejected: VC-only gate failed (voice context not verified)."}

        cmd = _normalize_command(text)
        if not cmd:
            return {"accepted": False, "reason": "Rejected: empty command."}

        if len(cmd) > 300:
            return {"accepted": False, "reason": "Rejected: command too long for direct mic mode."}

        if not bool(bypass_activation):
            if not re.search(r"\b(hey\s+computer|computer)\b", cmd, re.I):
                return {"accepted": False, "reason": "Rejected: activation phrase missing and bypass disabled."}
        else:
            if safety_phrase and safety_phrase.lower() not in cmd.lower():
                return {
                    "accepted": False,
                    "reason": f"Rejected: bypass mode requires safety phrase '{safety_phrase}'.",
                }

        return {
            "accepted": True,
            "source": "voice",
            "mode": "bypass" if bypass_activation else "wake_word",
            "command": cmd,
            "received_at_unix": int(time.time()),
        }
    except Exception as e:
        return {"accepted": False, "reason": f"request tool failed: {e}"}
