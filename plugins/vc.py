import asyncio
import json
import os
import queue
import ctypes
import re
import tempfile
import time
import wave
import logging
import shutil
import subprocess
import numpy as np
import audioop
import threading
try:
    import winsound
except Exception:
    winsound = None

import aiohttp
import webrtcvad
try:
    from openwakeword.model import Model as OpenWakeWordModel
except Exception:
    OpenWakeWordModel = None
try:
    from PyQt6.QtCore import Qt, QTimer
    from PyQt6.QtGui import QColor, QPainter
    from PyQt6.QtWidgets import QApplication, QWidget
except Exception:
    QApplication = None
    QWidget = None
    QTimer = None
    Qt = None
    QColor = None
    QPainter = None
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.backends import default_backend
import os
import base64
import socket
from datetime import datetime
try:
    import psutil
except Exception:
    psutil = None

try:
    from addons import weather as addon_weather
except Exception:
    addon_weather = None
try:
    from addons import time_now as addon_time_now
except Exception:
    addon_time_now = None
try:
    from addons import sysinfo as addon_sysinfo
except Exception:
    addon_sysinfo = None

def _jarvis_cmd(cmd: str):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.3)
        s.connect(("127.0.0.1", 5055))
        s.sendall(cmd.encode())
        s.close()
    except Exception:
        pass
def derive_key(key: bytes | str, salt: bytes) -> bytes:
    """Derive a 256-bit AES key from any-length key using PBKDF2."""
    if isinstance(key, str):
        key = key.encode()
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=600_000,
        backend=default_backend()
    )
    return kdf.derive(key)

def encrypt(plaintext: str, key: bytes | str) -> str:
    """
    Encrypt a string using AES-256-CBC with any-length key.
    Returns a base64-encoded string: salt + IV + ciphertext.
    """
    salt = os.urandom(16)
    iv = os.urandom(16)
    derived = derive_key(key, salt)

    padder = padding.PKCS7(128).padder()
    padded = padder.update(plaintext.encode()) + padder.finalize()

    cipher = Cipher(algorithms.AES(derived), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded) + encryptor.finalize()

    return base64.b64encode(salt + iv + ciphertext).decode()

def decrypt(token: str, key: bytes | str) -> str:
    """
    Decrypt a base64-encoded AES-256-CBC token with any-length key.
    Returns the original plaintext string.
    """
    raw = base64.b64decode(token)
    salt, iv, ciphertext = raw[:16], raw[16:32], raw[32:]
    derived = derive_key(key, salt)

    cipher = Cipher(algorithms.AES(derived), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    padded = decryptor.update(ciphertext) + decryptor.finalize()

    unpadder = padding.PKCS7(128).unpadder()
    return (unpadder.update(padded) + unpadder.finalize()).decode()

try:
    import pyaudio
except Exception:
    pyaudio = None

try:
    import edge_tts
except Exception:
    edge_tts = None

try:
    from faster_whisper import WhisperModel
except Exception:
    WhisperModel = None

try:
    import torch
except Exception:
    torch = None

try:
    import whisper
except Exception:
    whisper = None

try:
    from playsound import playsound
except Exception:
    playsound = None

try:
    from kokoro import KPipeline
except Exception:
    KPipeline = None

try:
    from openrgb import OpenRGBClient
    from openrgb.utils import DeviceType, RGBColor
except Exception:
    OpenRGBClient = None
    DeviceType = None
    RGBColor = None

description = "Local voice chat runtime using Whisper STT + VAD stop detection + TTS."
args = {
    "action": {"type": "string", "description": "start | transcribe_file"},
    "audio_file": {"type": "string", "description": "Path used when action=transcribe_file"},
}
required = ["action"]


AI_URL = "http://127.0.0.1:5000/chat"
AGENT_MAP = {
    "p": "qwen3.5:9b",
    "q": "qwen3.5:9b-q4_K_M",
    "d": "deepseek-coder:6.7b",
}
DEFAULT_AGENT_KEY = "p"
VAD_MODE = 2
SAMPLE_RATE = 16000
CHANNELS = 1
FRAME_MS = 30
FRAME_SIZE = int(SAMPLE_RATE * FRAME_MS / 1000)
FRAME_BYTES = FRAME_SIZE * 2
SILENCE_TO_STOP_SEC = 1.1
MIN_AUDIO_SEC = 0.20
VOICE_NAME = "en-GB-RyanNeural"
KOKORO_VOICE = "am_adam"
PRE_ROLL_SEC = 0.30
AUTO_PROMPT_FALLBACK = False
MAX_SEGMENT_SEC = 4.5
ENERGY_FLOOR = 220
FORCE_FLUSH_SEC = 8.0
POST_SPEAK_COOLDOWN_SEC = 0.70
DUPLICATE_PROMPT_WINDOW_SEC = 2.5
TRANSCRIPT_DUPLICATE_WINDOW_SEC = 1.8
TTS_LEAD_IN_MS = 1000
PREFERRED_MIC_NAME_SUBSTRING = "fifine"
WAKEWORD_MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Jarvis_20260313_215039.onnx")
WAKEWORD_ALEXA_KEY = "alexa"
WAKEWORD_THRESHOLD = 0.60
WAKEWORD_COOLDOWN_SEC = 1.5
WAKEWORD_GLOBAL_HOLD_SEC = 2.2
BARGE_IN_MIN_CHARS = 8
BARGE_IN_MIN_WORDS = 2
BARGE_IN_MIN_ALPHA_RATIO = 0.60
BARGE_IN_IGNORE_WORDS = {
    "uh", "um", "hmm", "mm", "mhm", "huh", "ah", "eh", "yo", "hey",
}

USE_FASTER = WhisperModel is not None
if USE_FASTER:
    has_cuda = bool(torch is not None and torch.cuda.is_available())
    fw_device = "cuda" if has_cuda else "cpu"
    fw_compute = "float16" if has_cuda else "int8"
    MODEL = WhisperModel("small.en", device=fw_device, compute_type=fw_compute)
else:
    if whisper is None:
        raise RuntimeError("Neither faster-whisper nor whisper is available.")
    MODEL = whisper.load_model("small.en")
vad = webrtcvad.Vad(VAD_MODE)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("vc")
if USE_FASTER:
    logger.info("Loaded faster-whisper model=base device=%s compute_type=%s", fw_device, fw_compute)

KOKORO_PIPELINE = None
if KPipeline is not None:
    try:
        KOKORO_PIPELINE = KPipeline(lang_code="a")
        logger.info("Kokoro TTS initialized with voice=%s", KOKORO_VOICE)
    except Exception as e:
        logger.warning("Kokoro TTS init failed: %s", e)
        KOKORO_PIPELINE = None


class StateOverlay:
    def __init__(self):
        self.state = "idle"
        self.running = False
        self.app = None
        self.widget = None
        self.phase = 0
        self.rms = 0.0
        self.rms_smooth = 0.0
        self.lock = threading.Lock()
        self.ready = threading.Event()
        self.rgb = OpenRGBController(self.snapshot)

    def start(self):
        if QApplication is None:
            logger.warning("PyQt6 not available; overlay disabled.")
            return
        self.rgb.start()
        self._run()

    def set_state(self, state: str):
        with self.lock:
            prev = self.state
            self.state = state
        if prev != state:
            if state == "listening":
                WAKE_TONE.beep_once()
                _jarvis_cmd("active")
            elif state == "thinking":
                _jarvis_cmd("thinking")
            elif state == "speaking":
                _jarvis_cmd("active")
            elif state == "idle":
                _jarvis_cmd("idle")
            elif prev == "listening":
                WAKE_TONE.beep_once()

    def set_rms(self, rms: float):
        with self.lock:
            self.rms = max(0.0, float(rms))

    def stop(self):
        self.running = False
        self.rgb.stop()
        try:
            if self.app:
                self.app.quit()
        except Exception:
            pass

    def _run(self):
        try:
            self.app = QApplication([])
            self.widget = OverlayWidget(self)
            self.widget.show()
            self.widget.raise_()
            self.running = True
            self.ready.set()
            logger.info("Overlay shown")
        except Exception as e:
            logger.warning("Overlay failed to start: %s", e)

    def run_event_loop(self):
        if self.app is not None:
            self.app.exec()

    def snapshot(self):
        with self.lock:
            return self.state, self.rms


class OpenRGBController:
    def __init__(self, snapshot_fn):
        self._snapshot_fn = snapshot_fn
        self._thread = None
        self._stop = threading.Event()
        self._client = None
        self._fans = []
        self._phase = 0.0
        self._rms_smooth = 0.0

    def start(self):
        if OpenRGBClient is None or RGBColor is None:
            logger.info("OpenRGB python library not available; fan RGB sync disabled.")
            return
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        t = self._thread
        if t and t.is_alive():
            t.join(timeout=0.8)
        self._thread = None

    def _run(self):
        try:
            self._client = OpenRGBClient()
            self._fans = self._get_fan_devices()
            if not self._fans:
                logger.info("OpenRGB connected but no fan-capable devices found.")
                return
            logger.info("OpenRGB connected. fan targets=%s", len(self._fans))
        except Exception as e:
            err = str(e).strip() or repr(e)
            logger.warning("OpenRGB connection failed: %s", err)
            return

        while not self._stop.is_set():
            self._phase += 0.11
            state, rms = self._snapshot_fn()
            target = min(1.0, max(0.0, float(rms) / 2500.0))
            alpha = 0.2 if state == "speaking" else 0.35
            self._rms_smooth = (1 - alpha) * self._rms_smooth + alpha * target
            colors = self._colors_for_state(state)
            if colors:
                self._apply_colors(colors)
            time.sleep(0.033)

    def _get_fan_devices(self):
        if self._client is None:
            return []
        devices = list(getattr(self._client, "devices", []))
        for d in devices:
            logger.info("Device found: name=%s type=%s", d.name, getattr(d, "type", None))
        return devices

    def _colors_for_state(self, state):
        n = max(1, len(self._fans))
        base_idle = np.array([255, 95, 31], dtype=np.float32)
        base_thinking = np.array([168, 85, 247], dtype=np.float32)
        base_speaking = np.array([56, 189, 248], dtype=np.float32)
        base_listening = np.array([34, 197, 94], dtype=np.float32)
        if state == "idle":
            vals = []
            for i in range(n):
                s = 0.5 + 0.5 * np.sin((self._phase * 1.8) + (i * 0.9))
                amp = 0.20 + (0.35 * s)
                rgb = np.clip(base_idle * amp, 0, 255).astype(np.uint8)
                vals.append(RGBColor(int(rgb[0]), int(rgb[1]), int(rgb[2])))
            return vals

        if state == "thinking":
            vals = []
            for i in range(n):
                s = 0.5 + 0.5 * np.sin((self._phase * 2.8) + (i * 2.09439510239))
                amp = 0.35 + (0.65 * s)
                rgb = np.clip(base_thinking * amp, 0, 255).astype(np.uint8)
                vals.append(RGBColor(int(rgb[0]), int(rgb[1]), int(rgb[2])))
            return vals

        if state == "speaking":
            vals = []
            for i in range(n):
                wave = 0.5 + 0.5 * np.sin((self._phase * 5.0) + (i * 0.7))
                amp = min(1.0, 0.25 + (self._rms_smooth * 1.25) + (0.25 * wave))
                rgb = np.clip(base_speaking * amp, 0, 255).astype(np.uint8)
                vals.append(RGBColor(int(rgb[0]), int(rgb[1]), int(rgb[2])))
            return vals

        vals = []
        for i in range(n):
            wave = 0.5 + 0.5 * np.sin((self._phase * 4.0) + (i * 0.65))
            amp = min(1.0, 0.22 + (self._rms_smooth * 1.4) + (0.22 * wave))
            rgb = np.clip(base_listening * amp, 0, 255).astype(np.uint8)
            vals.append(RGBColor(int(rgb[0]), int(rgb[1]), int(rgb[2])))
        return vals

    def _apply_colors(self, colors):
        for i, dev in enumerate(self._fans):
            c = colors[min(i, len(colors) - 1)]
            try:
                dev.set_color(c)
            except Exception:
                continue
    

class OverlayWidget(QWidget):
    def __init__(self, overlay: StateOverlay):
        super().__init__(None)

        self.overlay = overlay
        self.phase = 0.0
        self.rms_smoothed = 0.0

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.BypassWindowManagerHint
        )

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self.setStyleSheet("""
            background: transparent;
            border: none;
        """)

        self.resize(122, 50)

        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            screen.left() + 12,
            screen.bottom() - self.height() - 12
        )

        self.show()

        self._make_clickthrough()
        self._remove_shadow()
        self._force_topmost()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(33)

    def _make_clickthrough(self):
        if os.name != "nt":
            return

        hwnd = int(self.winId())

        GWL_EXSTYLE = -20

        WS_EX_LAYERED = 0x00080000
        WS_EX_TRANSPARENT = 0x00000020
        WS_EX_TOOLWINDOW = 0x00000080
        WS_EX_NOREDIRECTIONBITMAP = 0x00200000

        user32 = ctypes.windll.user32

        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)

        style |= (
            WS_EX_LAYERED
            | WS_EX_TRANSPARENT
            | WS_EX_TOOLWINDOW
            | WS_EX_NOREDIRECTIONBITMAP
        )

        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)

    def _remove_shadow(self):
        if os.name != "nt":
            return

        hwnd = int(self.winId())

        try:
            dwmapi = ctypes.windll.dwmapi

            DWMWA_NCRENDERING_ENABLED = 1
            DWMWA_BORDER_COLOR = 34
            DWMWA_CAPTION_COLOR = 35
            DWMWA_TEXT_COLOR = 36
            DWMWA_WINDOW_CORNER_PREFERENCE = 33

            DWMWCP_DONOTROUND = 1

            false_val = ctypes.c_int(0)
            corner = ctypes.c_int(DWMWCP_DONOTROUND)

            dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_NCRENDERING_ENABLED,
                ctypes.byref(false_val),
                ctypes.sizeof(false_val)
            )

            dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_WINDOW_CORNER_PREFERENCE,
                ctypes.byref(corner),
                ctypes.sizeof(corner)
            )

        except Exception as e:
            logger.warning("Shadow removal failed: %s", e)

    def _force_topmost(self):
        if os.name != "nt":
            return

        hwnd = int(self.winId())

        HWND_TOPMOST = -1

        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_NOACTIVATE = 0x0010
        SWP_SHOWWINDOW = 0x0040

        ctypes.windll.user32.SetWindowPos(
            hwnd,
            HWND_TOPMOST,
            0,
            0,
            0,
            0,
            SWP_NOMOVE
            | SWP_NOSIZE
            | SWP_NOACTIVATE
            | SWP_SHOWWINDOW,
        )

    def _tick(self):
        self.phase += 0.11

        state, rms = self.overlay.snapshot()

        target = min(1.0, rms / 2500.0)

        alpha = 0.2 if state == "speaking" else 0.35

        self.rms_smoothed = (
            (1 - alpha) * self.rms_smoothed
            + alpha * target
        )

        self.update()

    def paintEvent(self, _evt):
        p = QPainter(self)

        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        p.setPen(Qt.PenStyle.NoPen)

        state, _ = self.overlay.snapshot()

        cx = [25, 51, 77]

        base_y = 25

        r = 6.5

        if state == "idle":
            glow = 0.3 + 0.7 * (0.5 + 0.5 * np.sin(self.phase))

            for x in cx:
                p.setBrush(
                    QColor(
                        255,
                        95,
                        31,
                        int(150 + 80 * glow)
                    )
                )

                p.drawEllipse(
                    int(x - r),
                    int(base_y - r),
                    int(2 * r),
                    int(2 * r),
                )

            return

        if state == "thinking":
            center_x, center_y = 51, 25

            orbit_r = 12

            color = QColor(168, 85, 247, 230)

            for i in range(3):
                a = self.phase + (i * 2.094)

                x = center_x + orbit_r * np.cos(a)
                y = center_y + orbit_r * np.sin(a)

                p.setBrush(color)

                p.drawEllipse(
                    int(x - r),
                    int(y - r),
                    int(2 * r),
                    int(2 * r),
                )

            return

        if state == "speaking":
            color = QColor(56, 189, 248, 235)
            gain = 10.0
            amp = self.rms_smoothed * gain
        else:
            color = QColor(34, 197, 94, 235)
            gain = 16.0
            amp = self.rms_smoothed * gain

        for i, x in enumerate(cx):
            phase_offset = i * 0.55

            stretch = (
                1.0
                + amp
                * (
                    0.45
                    + 0.55
                    * (
                        0.5
                        + 0.5
                        * np.sin(
                            self.phase * 2.8
                            + phase_offset
                        )
                    )
                )
            )

            ry = float(
                max(
                    6.0,
                    min(20.0, r * stretch)
                )
            )

            p.setBrush(color)

            p.drawEllipse(
                int(x - r),
                int(base_y - ry),
                int(2 * r),
                int(2 * ry),
            )
            
OVERLAY = StateOverlay()
WAKE_PATTERN = re.compile(
    r"\b(?:hey\s+)?(?:jarvis|alexa)\b[\s,:-]*",
    re.I,
)
COMPUTER_WAKE_PATTERN = re.compile(r"\b(?:hey\s+)?jarvis\b[\s,:-]*", re.I)
ASSISTANT_WAKE_PATTERN = re.compile(r"\b(?:hey\s+)?alexa\b[\s,:-]*", re.I)
TTS_ACTIVE = threading.Event()
TTS_STOP = threading.Event()
SPEAK_LOCK = asyncio.Lock()
_SPEAK_COUNTER = 0
_last_spoken = {"text": "", "t": 0.0}


VOICE_BEHAVIORS = {
    "neutral": {"speed": 1.0, "pause_before": 0.15, "edge_rate": "+0%"},
    "confident": {"speed": 1.04, "pause_before": 0.08, "edge_rate": "+6%"},
    "careful": {"speed": 0.94, "pause_before": 0.35, "edge_rate": "-6%"},
    "thinking": {"speed": 0.92, "pause_before": 0.55, "edge_rate": "-8%"},
    "urgent": {"speed": 1.10, "pause_before": 0.02, "edge_rate": "+12%"},
    "warm": {"speed": 0.98, "pause_before": 0.20, "edge_rate": "-2%"},
}


def _clamp(value, low, high):
    return max(low, min(high, value))


def parse_speech_behavior(text: str, default_tone: str = "neutral") -> dict:
    """Extract optional model speech tags and infer a voice behavior."""
    raw = str(text or "").strip()
    behavior = {
        "text": raw,
        "tone": default_tone,
        **VOICE_BEHAVIORS.get(default_tone, VOICE_BEHAVIORS["neutral"]),
    }

    if raw.startswith("{"):
        try:
            payload = json.loads(raw)
            if isinstance(payload, dict) and "text" in payload:
                tone = str(payload.get("tone") or default_tone).lower()
                behavior.update(VOICE_BEHAVIORS.get(tone, VOICE_BEHAVIORS["neutral"]))
                behavior.update({
                    "text": clean_reply(str(payload.get("text") or "")),
                    "tone": tone if tone in VOICE_BEHAVIORS else "neutral",
                    "speed": _clamp(float(payload.get("speed", behavior["speed"])), 0.75, 1.25),
                    "pause_before": _clamp(float(payload.get("pause_before", behavior["pause_before"])), 0.0, 1.25),
                })
                return behavior
        except Exception:
            pass

    low = raw.lower()
    if re.search(r"\b(done|got it|handled|ready|yes|absolutely)\b", low):
        behavior.update({"tone": "confident", **VOICE_BEHAVIORS["confident"]})
    elif re.search(r"\b(checking|let me|looks like|probably|might|not sure)\b", low):
        behavior.update({"tone": "careful", **VOICE_BEHAVIORS["careful"]})
    elif re.search(r"\b(urgent|warning|critical|spiking|failed|error)\b", low):
        behavior.update({"tone": "urgent", **VOICE_BEHAVIORS["urgent"]})
    elif re.search(r"\b(thanks|nice|good|welcome)\b", low):
        behavior.update({"tone": "warm", **VOICE_BEHAVIORS["warm"]})
    return behavior


def thinking_ack(prompt: str) -> dict | None:
    low = (prompt or "").lower()
    if re.search(r"\b(debug|analy[sz]e|plan|architecture|why|complex|strategy|fix)\b", low):
        return {"text": "Hold on. I am tracing that.", "tone": "thinking", "speed": 0.94, "pause_before": 0.1}
    if re.search(r"\b(open|launch|stop|close|send|write|delete|reroute)\b", low):
        return {"text": "On it.", "tone": "confident", "speed": 1.05, "pause_before": 0.05}
    return None


class SystemAwareness:
    def __init__(self):
        self.last = {}
        self.last_alert_t = {}
        self.cpu_samples = []

    def snapshot(self):
        if psutil is None:
            return {"available": False}
        data = {"available": True, "time": time.time()}
        try:
            data["cpu_percent"] = psutil.cpu_percent(interval=None)
            vm = psutil.virtual_memory()
            data["ram_percent"] = vm.percent
            data["ram_available_gb"] = round(vm.available / (1024 ** 3), 2)
            data["top_processes"] = self._top_processes()
            data["focused_window"] = self._focused_window_title()
            data["network"] = self._network_snapshot()
            gpu = self._gpu_usage()
            if gpu is not None:
                data["gpu_percent"] = gpu
        except Exception as e:
            data["error"] = str(e)
        return data

    def maybe_alert(self):
        snap = self.snapshot()
        if not snap.get("available"):
            return None
        now = time.time()
        cpu = float(snap.get("cpu_percent") or 0.0)
        ram = float(snap.get("ram_percent") or 0.0)
        gpu = snap.get("gpu_percent")
        self.cpu_samples.append(cpu)
        self.cpu_samples = self.cpu_samples[-4:]
        top = (snap.get("top_processes") or [{}])[0]
        top_name = top.get("name", "unknown process")

        if len(self.cpu_samples) >= 3 and min(self.cpu_samples[-3:]) >= 92.0:
            if self._cooldown_ok("cpu_spike", now, 90):
                return f"Your CPU is pinned near {int(cpu)} percent. Top visible process is {top_name}."
        if ram >= 92.0 and self._cooldown_ok("ram_high", now, 120):
            return f"Memory pressure is high at {int(ram)} percent. Available RAM is {snap.get('ram_available_gb')} gigabytes."
        if isinstance(gpu, (int, float)) and gpu >= 92.0 and self._cooldown_ok("gpu_spike", now, 90):
            return f"Your GPU is spiking at {int(gpu)} percent. Same check says {top_name} is the busiest process."
        return None

    def _cooldown_ok(self, key, now, seconds):
        last = float(self.last_alert_t.get(key, 0.0))
        if now - last < seconds:
            return False
        self.last_alert_t[key] = now
        return True

    def _top_processes(self):
        rows = []
        for proc in psutil.process_iter(["pid", "name", "memory_info"]):
            try:
                rows.append({
                    "pid": proc.info["pid"],
                    "name": proc.info.get("name") or "unknown",
                    "memory_mb": round(proc.info["memory_info"].rss / (1024 ** 2), 1),
                })
            except Exception:
                continue
        rows.sort(key=lambda row: row["memory_mb"], reverse=True)
        return rows[:5]

    def _gpu_usage(self):
        try:
            out = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=1.5,
            ).strip()
            vals = [int(x.strip()) for x in out.splitlines() if x.strip()]
            return max(vals) if vals else None
        except Exception:
            return None

    def _network_snapshot(self):
        counters = psutil.net_io_counters()
        return {"bytes_sent": counters.bytes_sent, "bytes_recv": counters.bytes_recv}

    def _focused_window_title(self):
        if os.name != "nt":
            return None
        try:
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            length = user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            return buff.value or None
        except Exception:
            return None


SYSTEM_AWARENESS = SystemAwareness()


class WakeTone:
    def __init__(self):
        self._thread = None

    def beep_once(self):
        if winsound is None:
            return
        t = self._thread
        if t and t.is_alive():
            t.join(timeout=0.15)
        self._thread = threading.Thread(target=self._run_once, daemon=True)
        self._thread.start()

    def start(self):
        self.beep_once()

    def stop(self):
        t = self._thread
        if t and t.is_alive():
            t.join(timeout=0.3)
        self._thread = None

    def _run_once(self):
        sequence = [(784, 140), (1047, 140), (1319, 160), (988, 160)]
        for freq, dur in sequence:
            try:
                winsound.Beep(freq, dur)
            except Exception:
                try:
                    winsound.MessageBeep(winsound.MB_ICONASTERISK)
                    time.sleep(0.12)
                    winsound.MessageBeep(winsound.MB_OK)
                except Exception:
                    pass
                return


WAKE_TONE = WakeTone()


class OpenWakeWordDetector:
    def __init__(self):
        self.model = None
        self.model_keys = []
        self.last_detection_t = {}
        self.global_lock_until = 0.0
        self.available = False
        if OpenWakeWordModel is None:
            logger.warning("openwakeword not available; using transcript wake detection only.")
            return
        if not os.path.exists(WAKEWORD_MODEL_PATH):
            logger.warning("Wake model file not found at %s; using transcript wake detection only.", WAKEWORD_MODEL_PATH)
            return
        try:
            self.model = OpenWakeWordModel(
                wakeword_models=[WAKEWORD_MODEL_PATH, WAKEWORD_ALEXA_KEY],
                inference_framework="onnx",
            )
            custom_key = os.path.splitext(os.path.basename(WAKEWORD_MODEL_PATH))[0]
            self.model_keys = [custom_key, WAKEWORD_ALEXA_KEY]
            self.available = True
            logger.info("openwakeword initialized: models=%s", self.model_keys)
        except Exception as e:
            logger.warning("openwakeword init failed: %s", e)

    def process(self, pcm_chunk: bytes):
        if not self.available or not pcm_chunk:
            return None
        try:
            audio_frame = np.frombuffer(pcm_chunk, dtype=np.int16)
            predictions = self.model.predict(audio_frame)
            now = time.time()
            if now < self.global_lock_until:
                for key in self.model_keys:
                    try:
                        if key in self.model.prediction_buffer:
                            self.model.prediction_buffer[key].clear()
                    except Exception:
                        pass
                return None
            best_key = None
            best_conf = 0.0
            for key in self.model_keys:
                conf = float(predictions.get(key, 0.0))
                if conf > best_conf:
                    best_conf = conf
                    best_key = key
            if not best_key:
                return None
            last_t = float(self.last_detection_t.get(best_key, 0.0))
            if (now - last_t) > WAKEWORD_COOLDOWN_SEC and best_conf > WAKEWORD_THRESHOLD:
                self.last_detection_t[best_key] = now
                self.global_lock_until = now + WAKEWORD_GLOBAL_HOLD_SEC
                logger.info("Wake word detected via openwakeword: key=%s confidence=%.2f", best_key, best_conf)
                return best_key.lower()
            if (now - last_t) <= WAKEWORD_COOLDOWN_SEC:
                for key in self.model_keys:
                    try:
                        if key in self.model.prediction_buffer:
                            self.model.prediction_buffer[key].clear()
                    except Exception:
                        pass
        except Exception as e:
            logger.debug("openwakeword process error: %s", e)
        return None


def clean_reply(text: str) -> str:
    out = str(text or "")
    fixed = out.strip().replace(",]", "]")
    payload = None
    try:
        payload = json.loads(fixed)
    except Exception:
        payload = None
    if isinstance(payload, list):
        parts = []
        for evt in payload:
            if not isinstance(evt, dict):
                continue
            if evt.get("type") == "response":
                parts.append(str(evt.get("content", "")))
        out = "".join(parts)
    out = re.sub(r"\[THINK_START\][\s\S]*?\[THINK_END\]", " ", out)
    out = out.replace("[THINK_START]", "").replace("[THINK_END]", "")
    out = re.sub(r"\[THINK\][^\n\r]*", " ", out)
    out = re.sub(r"\[TOOL\][\s\S]*", "", out)
    out = re.sub(r"```[\s\S]*?```", " ", out)
    out = re.sub(r"[`*_>#~\-]+", " ", out)
    out = re.sub(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]", "", out)
    out = re.sub(r"\s{2,}", " ", out).strip()
    return out


def parse_command(text: str):
    t = (text or "").strip()
    if not t:
        return None
    low = t.lower()
    if re.search(r"\b(?:hey\s+)?alexa[\s,:-]+new\s+chat\b", low):
        return {"type": "new_chat"}
    m = re.search(r"\b(?:hey\s+)?jarvis[\s,:-]+(.+)$", t, re.I)
    if m and m.group(1).strip():
        return {"type": "prompt", "prompt": m.group(1).strip()}
    m2 = re.search(r"\bjarvis\b[\s,:-]*(.+)$", t, re.I)
    if m2 and m2.group(1).strip():  # FIX: was m2.group(2) — only one capture group
        return {"type": "prompt", "prompt": m2.group(1).strip()}
    return None


def parse_model_switch(text: str):
    t = (text or "").strip()
    if not t:
        return None
    m = re.search(
        r"\b(?:hey\s+)?alexa\b[\s,:-]*change\s+model\s+([qgd])\b",
        t,
        re.I,
    )
    if not m:
        m = re.search(r"\bchange\s+model\s+([qgd])\b", t, re.I)
    if not m:
        return None
    key = m.group(1).lower()
    agent = AGENT_MAP.get(key)
    if not agent:
        return None
    return {"type": "change_model", "key": key, "agent": agent}


def has_wake_phrase(text: str) -> bool:
    return bool(WAKE_PATTERN.search(text or ""))


def has_assistant_wake(text: str) -> bool:
    return bool(ASSISTANT_WAKE_PATTERN.search(text or ""))


def has_computer_wake(text: str) -> bool:
    return bool(COMPUTER_WAKE_PATTERN.search(text or ""))


def strip_wake_phrase(text: str) -> str:
    t = text or ""
    out = WAKE_PATTERN.sub("", t, count=1).strip()
    out = re.sub(r"^[\W_]+|[\W_]+$", "", out, flags=re.UNICODE).strip()
    if not re.search(r"[A-Za-z0-9]", out):
        return ""
    return out


def should_barge_in(text: str) -> bool:
    t = (text or "").strip().lower()
    if not t:
        return False
    if has_wake_phrase(t):
        return True
    words = re.findall(r"[a-z0-9']+", t)
    if len(words) < BARGE_IN_MIN_WORDS:
        return False
    if all(w in BARGE_IN_IGNORE_WORDS for w in words):
        return False
    alpha_count = sum(1 for ch in t if ch.isalpha())
    ratio = (alpha_count / max(1, len(t)))
    if ratio < BARGE_IN_MIN_ALPHA_RATIO:
        return False
    if len(" ".join(words)) < BARGE_IN_MIN_CHARS:
        return False
    return True


def _extract_weather_location(prompt: str) -> str:
    t = (prompt or "").strip()
    m = re.search(r"\bweather\s+(?:in|for|at)\s+([a-z0-9 .,'-]+)$", t, re.I)
    if m:
        return m.group(1).strip(" ,.")
    return ""


def route_deterministic_intent(prompt: str):
    t = (prompt or "").strip()
    low = t.lower()

    if re.search(r"\bwhat(?:'s| is)?\s+the\s+time\b|\bcurrent\s+time\b|\btime\s+now\b", low):
        if addon_time_now is not None:
            out = addon_time_now.main(timezone_name="America/Denver", format_24h=False)
            if isinstance(out, dict) and out.get("time"):
                return f"It is {out['time']}."
        now = datetime.now().astimezone()
        return f"It is {now.strftime('%Y-%m-%d %I:%M:%S %p %Z')}."

    if re.search(r"\b(today'?s|current)\s+date\b|\bwhat(?:'s| is)?\s+the\s+date\b", low):
        now = datetime.now().astimezone()
        return f"Today is {now.strftime('%A, %B %d, %Y')}."

    if re.search(r"\b(system|computer|pc|machine)\s+(info|information|status|specs)\b|\bsystem\s+usage\b", low):
        if addon_sysinfo is not None:
            out = addon_sysinfo.main()
            if isinstance(out, dict):
                os_name = out.get("os", "Unknown")
                cpu = out.get("cpu_model", "Unknown CPU")
                ram = (out.get("ram") or {}).get("total_gb", "Unknown")
                host = out.get("hostname", "Unknown host")
                return f"System summary: host {host}, OS {os_name}, CPU {cpu}, RAM {ram} gigabytes."
        return "I could not fetch full system info, but your machine appears available."

    if re.search(r"\bweather\b", low):
        if addon_weather is None:
            return "Weather tool is unavailable in VC mode right now."
        location = _extract_weather_location(t)
        if not location:
            return "Tell me a city, for example: weather in Denver."
        out = addon_weather.main(location=location, days=1)
        if isinstance(out, dict) and out.get("error"):
            return f"Weather lookup failed: {out['error']}"
        cur = (out or {}).get("current") or {}
        desc = cur.get("description", "unknown conditions")
        tf = cur.get("temp_f", "?")
        feels = cur.get("feels_like_f", "?")
        return f"Weather in {location}: {desc}, {tf} degrees Fahrenheit, feels like {feels}."

    return None


def transcribe_wav(path: str) -> str:
    logger.info("Transcribing wav: %s", path)
    if USE_FASTER:
        segments, info = MODEL.transcribe(
            path,
            beam_size=1,
            vad_filter=False,
        )
        text = " ".join((seg.text or "").strip() for seg in segments).strip()
        logger.info("faster-whisper language=%s prob=%.3f", getattr(info, "language", None), float(getattr(info, "language_probability", 0.0)))
    else:
        result = MODEL.transcribe(path)
        text = (result.get("text") or "").strip()
    logger.info("Whisper transcript: %r", text)
    return text


def transcribe_pcm(pcm: bytes, sample_rate: int = SAMPLE_RATE) -> str:
    if not pcm:
        return ""
    logger.info("PCM len=%d", len(pcm))
    audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
    logger.info("Transcribing PCM: samples=%s rate=%s", audio.shape[0], sample_rate)
    if USE_FASTER:
        segments, info = MODEL.transcribe(
            audio,
            beam_size=1,
            vad_filter=False,
            language="en",
        )
        text = " ".join((seg.text or "").strip() for seg in segments).strip()
        logger.info(
            "faster-whisper language=%s prob=%.3f",
            getattr(info, "language", None),
            float(getattr(info, "language_probability", 0.0)),
        )
    else:
        result = MODEL.transcribe(audio)
        text = (result.get("text") or "").strip()
    logger.info("Whisper transcript: %r", text)
    return text


def write_wav(path: str, pcm: bytes):
    with wave.open(path, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm)


def _play_audio_sync(path: str):
    """Blocking audio playback without playsound overlap quirks on Windows."""
    p = str(path or "")
    if not p:
        return
    if os.name == "nt":
        winmm = ctypes.windll.winmm
        alias = f"tts_{int(time.time()*1000)}"
        def _cmd(s: str):
            winmm.mciSendStringW(s, None, 0, None)
        def _status_mode() -> str:
            out = ctypes.create_unicode_buffer(64)
            winmm.mciSendStringW(f"status {alias} mode", out, 64, None)
            return out.value.strip().lower()
        _cmd(f'open "{p}" alias {alias}')
        _cmd(f"play {alias}")
        try:
            while True:
                if TTS_STOP.is_set():
                    _cmd(f"stop {alias}")
                    break
                if _status_mode() in ("stopped", "not ready"):
                    break
                time.sleep(0.03)
        finally:
            _cmd(f"close {alias}")
        return
    if p.lower().endswith(".wav") and winsound is not None:
        winsound.PlaySound(p, winsound.SND_FILENAME | winsound.SND_NODEFAULT)
        return
    if playsound is not None:
        playsound(p)


def interrupt_tts(reason: str = "interrupt"):
    if not TTS_ACTIVE.is_set():
        return
    logger.info("TTS interrupt requested: reason=%s", reason)
    TTS_STOP.set()


def _convert_mp3_to_wav(mp3_path: str, wav_path: str) -> bool:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return False
    try:
        proc = subprocess.run(
            [
                ffmpeg,
                "-y",
                "-loglevel",
                "error",
                "-i",
                mp3_path,
                "-ac",
                "1",
                "-ar",
                "24000",
                wav_path,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        return proc.returncode == 0 and os.path.exists(wav_path) and os.path.getsize(wav_path) > 44
    except Exception:
        return False


def _prepend_wav_silence(path: str, lead_in_ms: int) -> float:
    with wave.open(path, "rb") as rf:
        nch = rf.getnchannels()
        sampw = rf.getsampwidth()
        rate = rf.getframerate()
        frames = rf.readframes(rf.getnframes())
    silent_frames = max(0, int((lead_in_ms / 1000.0) * rate))
    silence = b"\x00" * (silent_frames * nch * sampw)
    merged = silence + frames
    with wave.open(path, "wb") as wf:
        wf.setnchannels(nch)
        wf.setsampwidth(sampw)
        wf.setframerate(rate)
        wf.writeframes(merged)
    total_frames = silent_frames + (len(frames) // (nch * sampw))
    return (total_frames / float(rate)) * 1000.0


async def ask_ai(chat_id: str, prompt: str, agent: str) -> str:
    parts = []
    async for piece in ask_ai_stream(chat_id, prompt, agent):
        parts.append(piece)
    return clean_reply("".join(parts))


async def ask_ai_stream(chat_id: str, prompt: str, agent: str):
    style_guard = """
    You are a tool-using assistant.

    If the user asks for:
    - time
    - date
    - system info
    - weather

    You MUST use the matching tool. Do not answer manually.

    Reply in plain text only.
    No markdown, no bullets, no code fences.
    """
    guarded = f"{style_guard}\n\nUser request: {prompt}"
    params = {"id": chat_id, "message": encrypt(guarded, "TOP_SECRET_KEY"), "think": 0, "agent": agent}
    decoder = json.JSONDecoder()
    buf = ""
    async with aiohttp.ClientSession() as sess:
        async with sess.get(AI_URL, params=params) as resp:
            async for chunk in resp.content.iter_chunked(1024):
                if not chunk:
                    continue
                buf += chunk.decode("utf-8", errors="ignore")
                while True:
                    buf = buf.lstrip()
                    if not buf:
                        break
                    if buf[0] in "[,":
                        buf = buf[1:]
                        continue
                    if buf[0] == "]":
                        return
                    try:
                        evt, idx = decoder.raw_decode(buf)
                    except ValueError:
                        break
                    buf = buf[idx:]
                    if isinstance(evt, dict) and evt.get("type") == "response":
                        content = str(evt.get("content", ""))
                        if content:
                            yield content


def _pop_speak_chunk(buffer: str):
    if not buffer:
        return "", ""
    m = re.search(r"[.!?]+[\]\"')]*\s+", buffer)
    if m:
        idx = m.end()
        return buffer[:idx], buffer[idx:]
    return "", buffer


async def speak(text: str, lead_in_ms: int = None, behavior: dict | None = None):
    global _SPEAK_COUNTER
    behavior = behavior or parse_speech_behavior(text)
    text = behavior.get("text", text)
    if not text:
        return
    pause_before = float(behavior.get("pause_before", 0.0) or 0.0)
    if pause_before > 0:
        await asyncio.sleep(pause_before)
    now = time.time()
    if text == _last_spoken["text"] and (now - _last_spoken["t"]) < 3.0:
        logger.warning("Dropped duplicate TTS: %r", text)
        return
    _last_spoken["text"] = text
    _last_spoken["t"] = now
    if SPEAK_LOCK.locked():
        logger.warning("Dropped overlapping TTS request while another speak() is active.")
        return
    if edge_tts is None:
        print(f"assistant: {text}")
        return
    async with SPEAK_LOCK:
        TTS_STOP.clear()
        _SPEAK_COUNTER += 1
        speak_id = _SPEAK_COUNTER
        logger.info(
            "TTS start: speak_id=%s chars=%s tone=%s speed=%s",
            speak_id,
            len(text),
            behavior.get("tone"),
            behavior.get("speed"),
        )
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            mp3_path = tmp.name
        wav_path = None
        edge_wav_path = None
        output_path = None
        engine_used = None
        tts_format_selected = None
        wav_duration_ms = 0.0
        playback_backend = "unknown"
        effective_lead_in_ms = TTS_LEAD_IN_MS if lead_in_ms is None else max(0, int(lead_in_ms))
        try:
            TTS_ACTIVE.set()
            OVERLAY.set_state("speaking")
            if KOKORO_PIPELINE is not None:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as wtmp:
                    wav_path = wtmp.name
                try:
                    audio_parts = []
                    gen = KOKORO_PIPELINE(text, voice=KOKORO_VOICE, speed=float(behavior.get("speed", 1.0)))
                    for _gs, _ps, audio in gen:
                        audio_parts.append(np.asarray(audio, dtype=np.float32))
                    if audio_parts:
                        audio_full = np.concatenate(audio_parts)
                        pcm16 = np.clip(audio_full, -1.0, 1.0)
                        pcm16 = (pcm16 * 32767.0).astype(np.int16)
                        with wave.open(wav_path, "wb") as wf:
                            wf.setnchannels(1)
                            wf.setsampwidth(2)
                            wf.setframerate(24000)
                            wf.writeframes(pcm16.tobytes())
                        if os.path.getsize(wav_path) > 44:
                            wav_duration_ms = _prepend_wav_silence(wav_path, effective_lead_in_ms)
                            output_path = wav_path
                            engine_used = "kokoro"
                            tts_format_selected = "wav"
                except Exception as e:
                    logger.warning("Kokoro synthesis failed, falling back to edge_tts: %s", e)

            if output_path is None:
                edge_rate = behavior.get("edge_rate")
                if not edge_rate:
                    speed = float(behavior.get("speed", 1.0))
                    pct = int(round((speed - 1.0) * 100))
                    edge_rate = f"{pct:+d}%"
                tts = edge_tts.Communicate(text, VOICE_NAME, rate=edge_rate)
                await tts.save(mp3_path)
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as ew:
                    edge_wav_path = ew.name
                if _convert_mp3_to_wav(mp3_path, edge_wav_path):
                    wav_duration_ms = _prepend_wav_silence(edge_wav_path, effective_lead_in_ms)
                    output_path = edge_wav_path
                    engine_used = "edge_tts"
                    tts_format_selected = "wav"
                else:
                    output_path = mp3_path
                    engine_used = "edge_tts"
                    tts_format_selected = "mp3_fallback"

            if output_path.lower().endswith(".wav"):
                playback_backend = "winsound_wav" if os.name == "nt" else "playsound_wav"
            else:
                playback_backend = "winmm_mci_mp3" if os.name == "nt" else "playsound_mp3"
            logger.info(
                "TTS selected engine: speak_id=%s engine=%s tts_format_selected=%s lead_in_ms=%s wav_duration_ms=%.1f playback_backend=%s",
                speak_id,
                engine_used,
                tts_format_selected,
                effective_lead_in_ms,
                wav_duration_ms,
                playback_backend,
            )
            await asyncio.to_thread(_play_audio_sync, output_path)
            logger.info("TTS playback complete: speak_id=%s", speak_id)
        finally:
            TTS_ACTIVE.clear()
            OVERLAY.set_state("idle")
            if os.path.exists(mp3_path):
                os.remove(mp3_path)
            if wav_path and os.path.exists(wav_path):
                os.remove(wav_path)
            if edge_wav_path and os.path.exists(edge_wav_path):
                os.remove(edge_wav_path)


class MicSegmenter:
    def __init__(self):
        if pyaudio is None:
            raise RuntimeError("pyaudio is required for live VC mode.")
        self.pa = pyaudio.PyAudio()
        self.q = queue.Queue()
        self.stream = None
        self.speaking = False
        self.buffer = bytearray()
        self.pre_roll = bytearray()
        self.last_speech_t = 0.0
        self.segment_start_t = 0.0
        self.last_emit_t = time.time()
        self.frames_total = 0
        self.frames_speech = 0
        self.frames_silence = 0
        self.last_stats_t = time.time()
        self.device_idx = None
        self.wakeword = OpenWakeWordDetector()
        self._wake_triggered = None

    def _pick_input_device(self):
        preferred = (PREFERRED_MIC_NAME_SUBSTRING or "").strip().lower()
        fallback_info = self.pa.get_default_input_device_info()
        fallback_idx = fallback_info.get("index")

        try:
            device_count = self.pa.get_device_count()
        except Exception:
            device_count = 0

        for i in range(device_count):
            try:
                info = self.pa.get_device_info_by_index(i)
            except Exception:
                continue
            max_inputs = int(info.get("maxInputChannels", 0) or 0)
            name = str(info.get("name") or "")
            if max_inputs <= 0:
                continue
            if preferred and preferred in name.lower():
                return info.get("index"), info

        return fallback_idx, fallback_info

    def _callback(self, in_data, frame_count, time_info, status):
        if status:
            logger.warning("PyAudio callback status: %s", status)
        self.q.put(in_data)
        return (None, pyaudio.paContinue)

    def start(self):
        self.device_idx, info = self._pick_input_device()
        logger.info(
            "Opening mic device index=%s name=%s rate=%s channels=%s chunk=%s",
            info.get("index"),
            info.get("name"),
            SAMPLE_RATE,
            CHANNELS,
            FRAME_SIZE,
        )
        self.stream = self.pa.open(
            format=pyaudio.paInt16,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            input_device_index=self.device_idx,
            frames_per_buffer=FRAME_SIZE,
            stream_callback=self._callback,
        )
        self.stream.start_stream()
        logger.info("Mic stream started")

    def stop(self):
        logger.info("Stopping mic stream")
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.pa.terminate()
        logger.info("Mic stream terminated")

    def reset_buffers(self, reason: str):
        q_before = self.q.qsize()
        buf_before = len(self.buffer)
        pre_before = len(self.pre_roll)
        dropped = 0
        while True:
            try:
                self.q.get_nowait()
                dropped += 1
            except queue.Empty:
                break
        self.buffer = bytearray()
        self.pre_roll = bytearray()
        self.speaking = False
        self.segment_start_t = 0.0
        self.last_speech_t = 0.0
        self.frames_speech = 0
        self.frames_silence = 0
        self.last_emit_t = time.time()
        logger.info(
            "Mic reset: reason=%s q_before=%s q_dropped=%s q_after=%s buffer_before=%s pre_before=%s",
            reason,
            q_before,
            dropped,
            self.q.qsize(),
            buf_before,
            pre_before,
        )

    def next_segment(self, stop_event=None):
        while True:
            if stop_event is not None and stop_event.is_set():
                return None
            try:
                chunk = self.q.get(timeout=0.05 if stop_event is not None else None)
            except queue.Empty:
                continue
            if len(chunk) < FRAME_BYTES:
                continue
            wake_key = self.wakeword.process(chunk)
            if wake_key:
                self._wake_triggered = wake_key
            speech = False
            try:
                speech = vad.is_speech(chunk[:FRAME_BYTES], SAMPLE_RATE)
            except Exception:
                speech = False
            try:
                rms = audioop.rms(chunk, 2)
            except Exception:
                rms = 0
            OVERLAY.set_rms(rms)
            energy_speech = rms >= ENERGY_FLOOR
            speech = speech or energy_speech

            self.frames_total += 1
            now = time.time()
            self.pre_roll.extend(chunk)
            max_pre_roll_bytes = int(SAMPLE_RATE * PRE_ROLL_SEC) * 2
            if len(self.pre_roll) > max_pre_roll_bytes:
                self.pre_roll = self.pre_roll[-max_pre_roll_bytes:]

            if speech:
                self.frames_speech += 1
                if not self.speaking and self.pre_roll:
                    self.buffer.extend(self.pre_roll)
                if not self.speaking:
                    self.segment_start_t = now
                self.speaking = True
                self.last_speech_t = now
                self.buffer.extend(chunk)
            elif self.speaking:
                self.frames_silence += 1
                self.buffer.extend(chunk)
                if now - self.last_speech_t >= SILENCE_TO_STOP_SEC:
                    pcm = bytes(self.buffer)
                    self.buffer = bytearray()
                    self.speaking = False
                    min_bytes = int(SAMPLE_RATE * MIN_AUDIO_SEC) * 2
                    if len(pcm) >= min_bytes:
                        sec = len(pcm) / (SAMPLE_RATE * 2)
                        logger.info(
                            "Segment ready: bytes=%s seconds=%.2f speech_frames=%s silence_frames=%s",
                            len(pcm),
                            sec,
                            self.frames_speech,
                            self.frames_silence,
                        )
                        self.frames_speech = 0
                        self.frames_silence = 0
                        self.last_emit_t = now
                        return pcm
                    logger.info("Discarded too-short segment: bytes=%s", len(pcm))

            if self.speaking and self.segment_start_t and (now - self.segment_start_t >= MAX_SEGMENT_SEC):
                pcm = bytes(self.buffer)
                self.buffer = bytearray()
                self.speaking = False
                self.segment_start_t = 0.0
                min_bytes = int(SAMPLE_RATE * MIN_AUDIO_SEC) * 2
                if len(pcm) >= min_bytes:
                    sec = len(pcm) / (SAMPLE_RATE * 2)
                    logger.info("Forced segment flush: bytes=%s seconds=%.2f rms=%s", len(pcm), sec, rms)
                    self.last_emit_t = now
                    return pcm

            if self.buffer and (now - self.last_emit_t >= FORCE_FLUSH_SEC):
                pcm = bytes(self.buffer)
                self.buffer = bytearray()
                self.speaking = False
                self.segment_start_t = 0.0
                min_bytes = int(SAMPLE_RATE * MIN_AUDIO_SEC) * 2
                if len(pcm) >= min_bytes:
                    sec = len(pcm) / (SAMPLE_RATE * 2)
                    logger.info("Emergency flush: bytes=%s seconds=%.2f", len(pcm), sec)
                    self.last_emit_t = now
                    return pcm

            if now - self.last_stats_t >= 2.0:
                logger.info(
                    "Audio stats: total_frames=%s speech_frames=%s silence_frames=%s queued=%s speaking=%s rms=%s",
                    self.frames_total,
                    self.frames_speech,
                    self.frames_silence,
                    self.q.qsize(),
                    self.speaking,
                    rms,
                )
                self.last_stats_t = now

    def consume_wake_trigger(self):
        triggered = self._wake_triggered
        self._wake_triggered = None
        return triggered

RUNNING = False
async def run_live(): 
    global RUNNING
    if RUNNING:
        logger.warning("run_live already running — blocked duplicate start")
        return
    RUNNING = True
    chat_id = f"vc_{int(time.time())}"
    agent_key = DEFAULT_AGENT_KEY
    current_agent = AGENT_MAP[agent_key]
    mic = MicSegmenter()
    mic.start()
    OVERLAY.set_state("idle")
    wake_armed_mode = None
    suppress_until = 0.0
    barge_in_prompt_requested = False
    last_prompt_norm = ""
    last_prompt_t = 0.0
    last_transcript_norm = ""
    last_transcript_t = 0.0
    runtime_state = {"mode": "idle_assistant", "last_prompt": "", "last_alert": ""}
    logger.info("VC running. chat_id=%s", chat_id)
    logger.info("Current agent=%s", current_agent)
    logger.info("Say: hey alexa new chat")
    logger.info("Say: hey jarvis <prompt>")
    logger.info("Say: alexa change model Q|G|D")

    def _enter_post_tts_state():
        nonlocal suppress_until, wake_armed_mode, barge_in_prompt_requested
        if barge_in_prompt_requested:
            suppress_until = 0.0
            wake_armed_mode = "prompt"
            barge_in_prompt_requested = False
            OVERLAY.set_state("listening")
            return
        suppress_until = time.time() + POST_SPEAK_COOLDOWN_SEC
        OVERLAY.set_state("idle")

    async def _speak_interruptible(reply: str, lead_in_ms: int = None, behavior: dict | None = None) -> bool:
        nonlocal suppress_until, wake_armed_mode, barge_in_prompt_requested
        if not reply:
            return False
        monitor_done = threading.Event()
        speak_task = asyncio.create_task(speak(reply, lead_in_ms=lead_in_ms, behavior=behavior))
        speak_task.add_done_callback(lambda _task: monitor_done.set())
        interrupted = False
        try:
            while not speak_task.done():
                pcm = await asyncio.to_thread(mic.next_segment, monitor_done)
                if pcm is None:
                    break
                if not TTS_ACTIVE.is_set():
                    continue
                barged_text = transcribe_pcm(pcm, SAMPLE_RATE)
                barged_norm = (barged_text or "").strip()
                if should_barge_in(barged_norm):
                    interrupt_tts("barge_in")
                    mic.reset_buffers("barge_in")
                    suppress_until = 0.0
                    wake_armed_mode = "prompt"
                    barge_in_prompt_requested = True
                    OVERLAY.set_state("listening")
                    logger.info("Barge-in detected during TTS. text=%r", barged_text)
                    interrupted = True
                    break
                logger.info("Dropped segment during TTS: no barge-in threshold match")
                mic.reset_buffers("suppressed_drop_tts")
            await speak_task
            if interrupted:
                await speak("Hold on.", behavior={"text": "Hold on.", "tone": "urgent", **VOICE_BEHAVIORS["urgent"]})
            return interrupted or TTS_STOP.is_set()
        finally:
            monitor_done.set()

    async def _speak_with_reason(reply: str, reason: str):
        logger.info(">>> SPEAK CALLED: reason=%s text=%r", reason, (reply or "")[:60])
        logger.info("TTS trigger accepted: reason=%s reply_len=%s", reason, len(reply or ""))
        mic.reset_buffers("pre_tts")
        behavior = parse_speech_behavior(reply)
        await _speak_interruptible(behavior["text"], behavior=behavior)
        mic.reset_buffers("post_tts")
        mic.reset_buffers("cooldown_enter")

    async def _stream_and_speak(prompt: str, reason: str) -> str:
        logger.info(">>> STREAM+SPEAK CALLED: reason=%s prompt=%r", reason, (prompt or "")[:80])
        mic.reset_buffers("pre_tts_stream")
        print("assistant: ", end="", flush=True)
        reply_parts = []
        pending = ""
        tts_queue = asyncio.Queue()
        tts_done = object()

        async def _tts_worker():
            while True:
                chunk = await tts_queue.get()
                if chunk is tts_done:
                    break
                text_chunk = str((chunk or ("", 0, None))[0]).strip()
                lead_in = int((chunk or ("", 0, None))[1])
                behavior = (chunk or ("", 0, None))[2]
                if text_chunk:
                    interrupted = await _speak_interruptible(text_chunk, lead_in_ms=lead_in, behavior=behavior)
                    if interrupted:
                        break

        worker = asyncio.create_task(_tts_worker())
        first_sentence = True
        interrupted = False
        try:
            async for piece in ask_ai_stream(chat_id, prompt, current_agent):
                if worker.done():
                    interrupted = True
                    break
                reply_parts.append(piece)
                print(piece, end="", flush=True)
                pending += piece
                while True:
                    speak_chunk, pending = _pop_speak_chunk(pending)
                    if not speak_chunk:
                        break
                    lead_in = TTS_LEAD_IN_MS if first_sentence else 0
                    first_sentence = False
                    behavior = parse_speech_behavior(speak_chunk, default_tone="confident" if not first_sentence else "neutral")
                    await tts_queue.put((behavior["text"], lead_in, behavior))
            if pending.strip():
                lead_in = TTS_LEAD_IN_MS if first_sentence else 0
                behavior = parse_speech_behavior(pending, default_tone="careful" if first_sentence else "neutral")
                await tts_queue.put((behavior["text"], lead_in, behavior))
            print()
            if not interrupted:
                await tts_queue.put(tts_done)
                await worker
        finally:
            if not worker.done():
                await tts_queue.put(tts_done)
                await worker
            mic.reset_buffers("post_tts_stream")
            mic.reset_buffers("cooldown_enter")
        reply = clean_reply("".join(reply_parts))
        logger.info("Assistant reply len=%s", len(reply))
        return reply

    async def _respond_to_prompt(prompt: str, model_reason: str, tool_reason: str) -> str:
        runtime_state["mode"] = "active_helper"
        runtime_state["last_prompt"] = prompt
        ack = thinking_ack(prompt)
        if ack:
            await _speak_interruptible(ack["text"], lead_in_ms=0, behavior=ack)
        direct = route_deterministic_intent(prompt)
        if direct:
            logger.info("Deterministic intent routed directly: reason=%s prompt=%r", tool_reason, prompt)
            await _speak_with_reason(direct, tool_reason)
            runtime_state["mode"] = "idle_assistant"
            return direct
        reply = await _stream_and_speak(prompt, model_reason)
        runtime_state["mode"] = "idle_assistant"
        return reply

    async def _proactive_system_monitor():
        while True:
            await asyncio.sleep(10.0)
            if runtime_state.get("mode") != "idle_assistant":
                continue
            if TTS_ACTIVE.is_set() or wake_armed_mode is not None:
                continue
            alert = SYSTEM_AWARENESS.maybe_alert()
            if not alert or alert == runtime_state.get("last_alert"):
                continue
            runtime_state["last_alert"] = alert
            logger.info("Proactive system alert: %s", alert)
            await _speak_with_reason(
                json.dumps({
                    "text": alert,
                    "tone": "urgent",
                    "speed": 1.06,
                    "pause_before": 0.2,
                }),
                "proactive_system_awareness",
            )

    try:
        monitor_task = asyncio.create_task(_proactive_system_monitor())
        while True:
            pcm = await asyncio.to_thread(mic.next_segment)
            logger.info("PCM segment received: %d bytes", len(pcm))
            wake_triggered = mic.consume_wake_trigger()
            if wake_triggered:
                if not wake_armed_mode:
                    if wake_triggered == "alexa":
                        wake_armed_mode = "control"
                        OVERLAY.set_state("listening")
                        logger.info("Alexa wake armed by openwakeword; waiting for control segment")
                    else:
                        wake_armed_mode = "prompt"
                        OVERLAY.set_state("listening")
                        logger.info("Jarvis wake armed by openwakeword; waiting for prompt segment")
                # The wake segment may contain speech before the wake word.
                # Drop it and start transcription on the next segment only.
                mic.reset_buffers("wake_segment_drop_arm_next")
                logger.info("Dropped wake segment; waiting for post-wake segment only")
                continue
            now = time.time()
            if TTS_ACTIVE.is_set():
                barged_text = transcribe_pcm(pcm, SAMPLE_RATE)
                barged_norm = (barged_text or "").strip()
                if should_barge_in(barged_norm):
                    interrupt_tts("barge_in")
                    mic.reset_buffers("barge_in")
                    suppress_until = 0.0
                    wake_armed_mode = "prompt"
                    OVERLAY.set_state("listening")
                    logger.info("Barge-in detected; interrupted TTS. text=%r", barged_text)
                else:
                    logger.info("Dropped segment during TTS: no barge-in threshold match")
                    mic.reset_buffers("suppressed_drop_tts")
                continue
            if now < suppress_until:
                logger.info(
                    "Dropped segment (cooldown): cooldown_left=%.2fs",
                    max(0.0, suppress_until - now),
                )
                mic.reset_buffers("suppressed_drop_cooldown")
                continue
            if wake_armed_mode is None:
                logger.info("Dropped segment: not wake-armed, skipping Whisper transcription")
                OVERLAY.set_state("idle")
                continue
            OVERLAY.set_state("thinking")
            print(f"[PCM] {len(pcm)} bytes")
            text = transcribe_pcm(pcm, SAMPLE_RATE)
            print(text)
            if not text:
                logger.info("Segment produced empty transcript")
                if wake_triggered == "alexa":
                    wake_armed_mode = "control"
                    OVERLAY.set_state("listening")
                    logger.info("Alexa wake detected with empty transcript; staying armed")
                elif wake_triggered:
                    wake_armed_mode = "prompt"
                    OVERLAY.set_state("listening")
                    logger.info("Jarvis wake detected with empty transcript; staying armed")
                elif not wake_armed_mode:
                    OVERLAY.set_state("idle")
                continue

            logger.info("Heard text: %r", text)

            model_cmd = parse_model_switch(text)
            if model_cmd:
                agent_key = model_cmd["key"]
                current_agent = model_cmd["agent"]
                logger.info("Model switched: key=%s agent=%s", agent_key.upper(), current_agent)
                await _speak_with_reason(
                    f"Switched model to {agent_key.upper()}",
                    "change_model_command",
                )
                _enter_post_tts_state()
                continue

            text_norm = re.sub(r"\s+", " ", text.strip().lower())
            if text_norm and text_norm == last_transcript_norm and (now - last_transcript_t) < TRANSCRIPT_DUPLICATE_WINDOW_SEC:
                logger.info(
                    "Dropped transcript: reason=duplicate text=%r age=%.2fs window=%.2fs",
                    text,
                    now - last_transcript_t,
                    TRANSCRIPT_DUPLICATE_WINDOW_SEC,
                )
                OVERLAY.set_state("idle")
                continue
            last_transcript_norm = text_norm
            last_transcript_t = now

            if wake_armed_mode == "control":
                rem_model_cmd = parse_model_switch(f"alexa {text}")
                if rem_model_cmd:
                    agent_key = rem_model_cmd["key"]
                    current_agent = rem_model_cmd["agent"]
                    logger.info("Model switched (alexa armed): key=%s agent=%s", agent_key.upper(), current_agent)
                    await _speak_with_reason(
                        f"Switched model to {agent_key.upper()}",
                        "change_model_alexa_armed",
                    )
                    wake_armed_mode = None
                    _enter_post_tts_state()
                    continue
                if re.search(r"\bnew\s+chat\b", text, re.I):
                    chat_id = f"vc_{int(time.time())}"
                    logger.info("Voice command (alexa armed): new chat -> chat_id=%s", chat_id)
                    await _speak_with_reason("New chat created.", "new_chat_alexa_armed")
                    wake_armed_mode = None
                    _enter_post_tts_state()
                    continue
                logger.info("Alexa armed but no control command found; waiting for next segment")
                OVERLAY.set_state("listening")
                continue

            if wake_armed_mode == "prompt":
                prompt = strip_wake_phrase(text)
                if not prompt:
                    logger.info("Wake active but transcript had no prompt text yet; waiting for next segment")
                    OVERLAY.set_state("listening")
                    continue
                wake_armed_mode = None
                logger.info("Voice command (armed): prompt -> %r", prompt)
                prompt_norm = re.sub(r"\s+", " ", prompt.strip().lower())
                if prompt_norm and prompt_norm == last_prompt_norm and (time.time() - last_prompt_t) < DUPLICATE_PROMPT_WINDOW_SEC:
                    logger.info("Dropped prompt: reason=duplicate_armed prompt=%r", prompt)
                    OVERLAY.set_state("idle")
                    continue
                last_prompt_norm = prompt_norm
                last_prompt_t = time.time()
                reply = await _respond_to_prompt(prompt, "wake_armed_prompt", "deterministic_wake_armed_prompt")
                _enter_post_tts_state()
                continue

            if has_wake_phrase(text):
                OVERLAY.set_state("listening")
                remainder = strip_wake_phrase(text)
                assistant_wake = has_assistant_wake(text)
                computer_wake = has_computer_wake(text)

                if assistant_wake and not computer_wake:
                    if remainder:
                        rem_model_cmd = parse_model_switch(f"jarvis {remainder}")
                        if rem_model_cmd:
                            agent_key = rem_model_cmd["key"]
                            current_agent = rem_model_cmd["agent"]
                            logger.info("Model switched (assistant wake): key=%s agent=%s", agent_key.upper(), current_agent)
                            await _speak_with_reason(
                                f"Switched model to {agent_key.upper()}",
                                "change_model_assistant_wake",
                            )
                            _enter_post_tts_state()
                            continue
                        if re.search(r"\bnew\s+chat\b", remainder, re.I):
                            chat_id = f"vc_{int(time.time())}"
                            logger.info("Voice command (assistant wake): new chat -> chat_id=%s", chat_id)
                            await _speak_with_reason("New chat created.", "new_chat_assistant_wake")
                            _enter_post_tts_state()
                            continue
                    wake_armed_mode = "control"
                    logger.info("Alexa wake detected; armed for next segment control command")
                    continue

                if remainder:
                    rem_model_cmd = parse_model_switch(f"jarvis {remainder}")
                    if rem_model_cmd:
                        agent_key = rem_model_cmd["key"]
                        current_agent = rem_model_cmd["agent"]
                        logger.info("Model switched (wake remainder): key=%s agent=%s", agent_key.upper(), current_agent)
                        await _speak_with_reason(
                            f"Switched model to {agent_key.upper()}",
                            "change_model_wake_remainder",
                        )
                        _enter_post_tts_state()
                        continue
                    logger.info("Voice command: prompt -> %r", remainder)
                    prompt_norm = re.sub(r"\s+", " ", remainder.strip().lower())
                    if prompt_norm and prompt_norm == last_prompt_norm and (time.time() - last_prompt_t) < DUPLICATE_PROMPT_WINDOW_SEC:
                        logger.info("Dropped prompt: reason=duplicate_wake_same_segment prompt=%r", remainder)
                        OVERLAY.set_state("idle")
                        continue
                    last_prompt_norm = prompt_norm
                    last_prompt_t = time.time()
                    reply = await _respond_to_prompt(remainder, "wake_same_segment_prompt", "deterministic_wake_same_segment_prompt")
                    _enter_post_tts_state()
                else:
                    wake_armed_mode = "prompt"
                    logger.info("Jarvis wake detected; armed for next segment prompt")
                continue

            cmd = parse_command(text)
            if not cmd:
                if AUTO_PROMPT_FALLBACK:
                    logger.info("No wake command matched; fallback sends full transcript")
                    cmd = {"type": "prompt", "prompt": text}
                else:
                    logger.info("Dropped transcript: reason=no_wake_match text=%r", text)
                    OVERLAY.set_state("idle")
                    continue
            if cmd["type"] == "new_chat":
                chat_id = f"vc_{int(time.time())}"
                logger.info("Voice command: new chat -> chat_id=%s", chat_id)
                await _speak_with_reason("New chat created.", "new_chat_command")
                OVERLAY.set_state("idle")
                continue

            prompt = cmd["prompt"]
            logger.info("Voice command: prompt -> %r", prompt)
            prompt_norm = re.sub(r"\s+", " ", prompt.strip().lower())
            if prompt_norm and prompt_norm == last_prompt_norm and (time.time() - last_prompt_t) < DUPLICATE_PROMPT_WINDOW_SEC:
                logger.info("Dropped prompt: reason=duplicate_fallback prompt=%r", prompt)
                OVERLAY.set_state("idle")
                continue
            last_prompt_norm = prompt_norm
            last_prompt_t = time.time()
            reply = await _respond_to_prompt(prompt, "parse_command_prompt", "deterministic_parse_command_prompt")
            _enter_post_tts_state()
    finally:
        try:
            monitor_task.cancel()
        except Exception:
            pass
        OVERLAY.set_state("idle")
        mic.stop()


def transcribe_file_mode(audio_file: str):
    if not audio_file:
        return "audio_file is required for transcribe_file"
    if not os.path.exists(audio_file):
        return f"File not found: {audio_file}"
    return transcribe_wav(audio_file)


def main(action: str, audio_file: str = None):
    action = (action or "").strip().lower()
    if action == "transcribe_file":
        return transcribe_file_mode(audio_file)
    if action == "start":
        #OVERLAY.start()
        if OVERLAY.app is None:
            asyncio.run(run_live())
            return "vc session ended"

        err_holder = {"err": None}

        def _worker():
            try:
                asyncio.run(run_live())
            except Exception as e:
                err_holder["err"] = e
            finally:
                OVERLAY.stop()

        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        OVERLAY.run_event_loop()
        t.join(timeout=1.0)
        if err_holder["err"] is not None:
            raise err_holder["err"]
        return "vc session ended"
    return "Unknown action. Use start or transcribe_file."


if __name__ == "__main__":
    print(main("start"))
