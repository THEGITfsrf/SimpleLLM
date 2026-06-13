import os
import sys
import random
import subprocess
from datetime import datetime

# =========================
# CONFIG
# =========================

OUTPUT_DIR = "output"

# Change this to your Piper executable path if needed
PIPER_CMD = "piper"

# Put your .onnx models here
PIPER_VOICES = [
    "voices/en_US-amy-medium.onnx",
    "voices/en_US-danny-medium.onnx",
    "voices/en_US-lessac-medium.onnx",
]

# =========================
# TEXT VARIANTS (AUTO CHAOS MODE)
# =========================

def make_variants(text: str):
    return [
        text,
        text.upper(),
        f"{text}...",
        f"system message: {text}",
        f"{text} online",
        f"hey. {text}",
    ]

# =========================
# SAFE FILENAME
# =========================

def safe_name(s):
    return "".join(c for c in s if c.isalnum() or c in "_-")[:50]

# =========================
# PIPER TTS RUNNER
# =========================

def run_piper(text, voice_path, out_path):
    try:
        # Piper CLI usage:
        # echo "text" | piper --model model.onnx --output_file out.wav
        cmd = [
            PIPER_CMD,
            "--model", voice_path,
            "--output_file", out_path
        ]

        subprocess.run(
            cmd,
            input=text.encode("utf-8"),
            check=True
        )

        return True

    except Exception as e:
        print(f"[ERROR] Piper failed: {e}")
        return False

# =========================
# MAIN GENERATOR
# =========================

def main():
    if len(sys.argv) < 2:
        print("Usage: py generator.py <text>")
        return

    text = " ".join(sys.argv[1:])

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    variants = make_variants(text)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"\n[INFO] Generating voices for: {text}\n")

    count = 0

    for voice in PIPER_VOICES:
        voice_name = os.path.splitext(os.path.basename(voice))[0]

        for i, variant in enumerate(variants):
            filename = f"{safe_name(text)}_{voice_name}_{i}_{timestamp}.wav"
            out_path = os.path.join(OUTPUT_DIR, filename)

            print(f"[TTS] {voice_name} -> {variant}")

            ok = run_piper(variant, voice, out_path)

            if ok:
                print(f"   saved: {out_path}")
                count += 1
            else:
                print("   failed")

    print(f"\n[DONE] Generated {count} audio files 🎧")


if __name__ == "__main__":
    main()