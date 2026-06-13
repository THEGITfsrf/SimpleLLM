import os
import sounddevice as sd
import soundfile as sf
import threading

description = "JARVIS soundboard: play and list local sounds routed through Voicemeeter"
required = []

args = {
    "action": {
        "type": "string",
        "description": "play | list"
    },
    "file": {
        "type": "string",
        "description": "Sound filename inside ./sounds (required for play)"
    },
    "async_play": {
        "type": "boolean",
        "description": "Non-blocking playback",
        "default": True
    }
}

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SOUND_DIR = os.path.join(BASE_DIR, "sounds")

# Optional: force Voicemeeter device name
VOICEMEETER_DEVICE_NAME = "Voicemeeter Input"


# -------------------------
# DEVICE RESOLUTION
# -------------------------
def get_device():
    try:
        devices = sd.query_devices()
        for i, d in enumerate(devices):
            if VOICEMEETER_DEVICE_NAME.lower() in d["name"].lower():
                return i
    except Exception:
        pass
    return None  # fallback to default output


DEVICE = get_device()


# -------------------------
# SOUND PLAYBACK
# -------------------------
def _play_audio(path, async_play=True):
    try:
        data, sr = sf.read(path, dtype="float32")

        def run():
            sd.play(data, sr, device=DEVICE)
            sd.wait()

        if async_play:
            threading.Thread(target=run, daemon=True).start()
        else:
            run()

        return {
            "status": "ok",
            "message": f"[SOUND] Played {os.path.basename(path)}"
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"[ERROR] Playback failed: {str(e)}"
        }


# -------------------------
# LIST SOUNDS
# -------------------------
def list_sounds():
    if not os.path.exists(SOUND_DIR):
        return {
            "status": "error",
            "message": f"sounds folder missing at: {SOUND_DIR}"
        }

    files = [
        f for f in os.listdir(SOUND_DIR)
        if f.lower().endswith((".wav", ".mp3", ".ogg"))
    ]

    return {
        "status": "ok",
        "count": len(files),
        "sounds": files
    }


# -------------------------
# TOOL ENTRY
# -------------------------
def main(action="play", file=None, async_play=True):

    if action == "list":
        return list_sounds()

    if action == "play":
        if not file:
            return {
                "status": "error",
                "message": "No file provided"
            }

        path = os.path.join(SOUND_DIR, file)

        if not os.path.exists(path):
            return {
                "status": "error",
                "message": f"Sound not found: {file}"
            }

        result = _play_audio(path, async_play)
        if result.get("status") != "ok":
            return {
                "status": "error",
                "device": VOICEMEETER_DEVICE_NAME if DEVICE is not None else "default",
                "file": file,
                "message": result["message"],
            }

        return {
            "status": "ok",
            "device": VOICEMEETER_DEVICE_NAME if DEVICE is not None else "default",
            "file": file,
            "message": result["message"],
        }

    return {
        "status": "error",
        "message": f"Unknown action: {action}"
    }
