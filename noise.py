import os
import time
import numpy as np
import sounddevice as sd
from openwakeword.model import Model

# 1. Paths and Identity Definitions
jarvis_model_path = r"C:\Users\safra\SimpleLLM\Jarvis_20260313_215039.onnx"

if not os.path.exists(jarvis_model_path):
    raise FileNotFoundError(f"Could not find custom model file at: {jarvis_model_path}")

# Explicit exact key strings assigned inside openWakeWord dictionary arrays
model_key_1 = "Jarvis_20260313_215039"
model_key_2 = "alexa"  # Native pre-trained string key name

# 2. Initialize openWakeWord engine with mixed Custom File + Built-in Key
model = Model(
    wakeword_models=[jarvis_model_path, model_key_2], 
    inference_framework="onnx"
)

# 3. Independent Tracking for Cooldown States (keeps triggers separate)
COOLDOWN_PERIOD = 1.5  # Seconds
cooldown_tracker = {
    model_key_1: 0.0,
    model_key_2: 0.0
}

# 4. Audio streaming settings
SAMPLE_RATE = 16000
BLOCK_DURATION = 0.08  # 80ms chunks
BLOCK_SIZE = int(SAMPLE_RATE * BLOCK_DURATION)
MICROPHONE_ID = 2  # Fifine Mic via Windows MME

def audio_callback(indata, frames, time_info, status):
    """Processes audio chunks looking for Jarvis and Alexa simultaneously."""
    if status:
        print(f"Status flag: {status}")
        
    # Scale and convert to signed 16-bit integers
    audio_frame = (indata[:, 0].flatten() * 32767.0).astype(np.int16)
    
    # Run the audio through the joint evaluation pass
    predictions = model.predict(audio_frame)
    current_time = time.time()
    
    # Check predictions for all active wake words
    for key, confidence in predictions.items():
        # Evaluate if the active word is clear of its 1.5-second cooldown block
        if (current_time - cooldown_tracker.get(key, 0.0)) > COOLDOWN_PERIOD:
            if confidence > 0.60:
                print(f"\n🚀 Wake word '{key}' detected! (Confidence: {confidence:.2f})")
                
                # Activate individual cooldown lockout
                cooldown_tracker[key] = current_time
                
                # Route specific execution triggers based on what phrase was matched
                if key == model_key_1:
                    print("--> Action: Triggering primary Jarvis workflow.")
                elif key == model_key_2:
                    print("--> Action: Triggering native Alexa routing assistant.")
        else:
            # Clear internal historical tracking array data while locked out
            if key in model.prediction_buffer:
                model.prediction_buffer[key].clear()

# 5. Start streaming from your Fifine microphone
print(f"Listening using Fifine Mic (Index {MICROPHONE_ID}) for dual wake words ('{model_key_1}' & '{model_key_2}')...")
try:
    with sd.InputStream(
        device=MICROPHONE_ID,
        channels=1, 
        samplerate=SAMPLE_RATE, 
        blocksize=BLOCK_SIZE, 
        dtype='float32',
        callback=audio_callback
    ):
        while True:
            sd.sleep(1000)
except KeyboardInterrupt:
    print("\nStream stopped.")