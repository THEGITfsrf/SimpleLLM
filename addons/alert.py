# alrt.py
# Hook into vc.py to speak an alert message via its TTS pipeline.

import asyncio
import sys
import os

description = "speaks an alert message aloud using the vc.py TTS pipeline"
args = {
    "text": {
        "type": "string",
        "description": "The message to be spoken aloud via vc.py TTS"
    }
}
required = ["text"]

# vc.py lives in ../plugins/ relative to this file (addons/)
_HERE = os.path.dirname(os.path.abspath(__file__))
_VC_DIR = os.path.normpath(os.path.join(_HERE, "..", "plugins"))
if _VC_DIR not in sys.path:
    sys.path.insert(0, _VC_DIR)

import vc  # noqa: E402



def main(text: str):
    if not text or not text.strip():
        return False, "text must be a non-empty string"

    text = text.strip()

    try:
        # If vc's async event loop is already running (i.e. run_live() is active),
        # schedule speak() onto that loop from this thread.
        loop = asyncio._get_running_loop()  # None if called from outside a loop
    except AttributeError:
        loop = None

    if loop is None:
        # Try the legacy get_event_loop path
        try:
            loop = asyncio.get_event_loop()
            if not loop.is_running():
                loop = None
        except RuntimeError:
            loop = None

    try:
        if loop is not None and loop.is_running():
            # vc's run_live loop is active — thread-safe submission
            future = asyncio.run_coroutine_threadsafe(vc.speak(text), loop)
            future.result(timeout=60)          # block until TTS finishes
        else:
            # Standalone call (no live session) — just spin up a fresh loop
            asyncio.run(vc.speak(text))

        return True, f"Spoke: {text!r}"

    except TimeoutError:
        return False, "TTS timed out after 60 s"
    except Exception as e:
        return False, f"TTS error: {e}"


if __name__ == "__main__":
    msg = " ".join(sys.argv[1:]) or "Alert. This is a test message."
    ok, info = main(msg)
    print(f"{'OK' if ok else 'FAIL'}: {info}")