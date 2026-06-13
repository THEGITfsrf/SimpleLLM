import sounddevice as sd
import numpy as np
import openwakeword
import time

model = openwakeword.Model(
    wakeword_models=[r"C:\Users\safra\output\hey_manager\hey_manager.onnx"]
)

last_score = None
last_trigger = 0
THRESHOLD = 00.02338


def callback(indata, frames, time_info, status):
    global last_score, last_trigger

    audio = indata[:, 0].astype(np.float32)
    scores = model.predict(audio)

    score = float(list(scores.values())[0]) if scores else 0.0

    # 🚨 ONLY PRINT IF SCORE CHANGED SIGNIFICANTLY
    if last_score is None or abs(score - last_score) > 0.002:
        print(f"Score changed → {score:.5f}")
        last_score = score

    # 🔥 detection
    if score > THRESHOLD and (time.time() - last_trigger) > 2:
        print("🔥 DETECTED WAKE WORD")
        last_trigger = time.time()

with sd.InputStream(
    samplerate=16000,
    channels=1,
    blocksize=1280,
    callback=callback
):
    print("🎤 Listening (filtered debug mode)...")
    while True:
        sd.sleep(1000)