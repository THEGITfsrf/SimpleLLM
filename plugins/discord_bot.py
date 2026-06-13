import discord
from discord.ext import commands, voice_recv
import asyncio
import whisper
import edge_tts
import time
import json
import aiohttp
import webrtcvad
import audioop
import logging
from discord.opus import OpusError
from pathlib import Path
from datetime import datetime
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.backends import default_backend
import os
import base64

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


vad = webrtcvad.Vad(2)  # 0-3 (3 = most strict)
FRAME_MS = 20  # required by webrtcvad (10/20/30 only)
SAMPLE_RATE = 48000
SAMPLE_WIDTH = 2
FRAME_SIZE = int(SAMPLE_RATE * FRAME_MS / 1000) * SAMPLE_WIDTH

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("discord_bot")
logging.getLogger("discord.ext.voice_recv").setLevel(logging.INFO)
logging.getLogger("discord.ext.voice_recv.reader").setLevel(logging.WARNING)


def ensure_opus_loaded():
    if discord.opus.is_loaded():
        logger.info("Opus already loaded")
        return

    candidates = [
        "opus.dll",
        "libopus-0.x64.dll",
        "C:/Windows/System32/opus.dll",
    ]
    local_plugins = Path("C:/Users/safra/SimpleLLM/plugins")
    candidates.extend([str(p) for p in local_plugins.glob("*opus*.dll")])

    for dll in candidates:
        try:
            discord.opus.load_opus(dll)
            if discord.opus.is_loaded():
                logger.info("Loaded Opus library: %s", dll)
                return
        except Exception:
            continue

    logger.warning("Opus library not explicitly loaded; decode quality may be unstable")

def install_opus_decode_guard():
    # Keep router alive on intermittent bad opus packets.
    decoder_cls = getattr(discord.opus, "Decoder", None)
    if decoder_cls is None or not hasattr(decoder_cls, "decode"):
        logger.warning("Could not install Opus decode guard")
        return

    original_decode = decoder_cls.decode
    if getattr(original_decode, "_discord_bot_guarded", False):
        return

    last_warn = {"t": 0.0}

    def safe_decode(self, data, fec=False):
        try:
            return original_decode(self, data, fec=fec)
        except OpusError as e:
            now = time.time()
            if now - last_warn["t"] > 1.0:
                logger.warning("Opus decode errors are occurring (latest: %s)", e)
                last_warn["t"] = now
            # 20ms of 48kHz stereo 16-bit silence
            return b"\x00" * 3840

    safe_decode._discord_bot_guarded = True
    decoder_cls.decode = safe_decode
    logger.info("Installed Opus decode guard")

install_opus_decode_guard()
ensure_opus_loaded()

# -----------------------------
# CONFIG
# -----------------------------
def load_token():
    with open("C:/Users/safra/SimpleLLM/plugins/keys.json", "r", encoding="utf-8") as f:
        return json.load(f)["discord"].strip()


TOKEN = load_token()
GOOD_IDS = {1079183614715109526}  # whitelist users
# Set GOOD_IDS = set() to allow everyone in VC.
DEBUG_AUDIO_DIR = Path("C:/Users/safra/SimpleLLM/plugins/voice_debug")
DEBUG_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

MODEL = whisper.load_model("base")  # or "small"

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())


# -----------------------------
# JOIN VC
# -----------------------------
@bot.command()
async def join(ctx, channel_id: int):
    try:
        if not discord.opus.is_loaded():
            logger.warning("Opus not loaded (Discord will try auto)")

        channel = bot.get_channel(channel_id)

        if channel is None:
            await ctx.send("Channel not found")
            return

        if not isinstance(channel, discord.VoiceChannel):
            await ctx.send("That's not a voice channel")
            return

        # leave old VC if needed
        if ctx.voice_client:
            await ctx.voice_client.disconnect()

        vc = await channel.connect(cls=voice_recv.VoiceRecvClient)

        sink = MySink(ctx)
        vc.listen(sink)
        logger.info("Listening in VC channel=%s (%s)", channel.name, channel.id)

        await ctx.send(f"Joined VC: {channel.name}")

    except Exception as e:
        await ctx.send(f"join failed: {e}")
        logger.exception("JOIN ERROR")


# -----------------------------
# AUDIO SINK (core brain)
# -----------------------------
class MySink(voice_recv.AudioSink):
    def __init__(self, ctx):
        self.ctx = ctx
        self.buffers = {}
        self.speaking = {}
        self.silence_start = {}
        self.frame_stats = {}
        self.filtered_users_logged = set()

        # start background task
        self.task = asyncio.create_task(self.cleanup_loop())

    def write(self, user, data):
        if not user:
            return

        uid = user.id
        if GOOD_IDS and uid not in GOOD_IDS:
            if uid not in self.filtered_users_logged:
                logger.info("Ignoring user not in GOOD_IDS: %s", uid)
                self.filtered_users_logged.add(uid)
            return

        pcm = data.pcm
        if not pcm:
            return

        # voice-recv PCM is typically stereo; VAD requires mono.
        try:
            mono = audioop.tomono(pcm, 2, 0.5, 0.5)
        except Exception:
            return

        if uid not in self.buffers:
            self.buffers[uid] = bytearray()
            self.frame_stats[uid] = {"speech": 0, "silence": 0, "last_log": time.time()}

        # VAD expects a full 10/20/30ms frame; skip partial frames safely.
        frame = mono[:FRAME_SIZE]
        if len(frame) < FRAME_SIZE:
            return

        try:
            # VAD expects 16-bit mono PCM @ 16k/48k.
            is_speech = vad.is_speech(frame, SAMPLE_RATE)
        except Exception:
            return

        if is_speech:
            self.buffers[uid] += mono
            self.speaking[uid] = True
            self.silence_start[uid] = None
            self.frame_stats[uid]["speech"] += 1
        else:
            self.frame_stats[uid]["silence"] += 1
            if self.speaking.get(uid):
                self.silence_start[uid] = time.time()
                self.speaking[uid] = False

        stats = self.frame_stats[uid]
        now = time.time()
        if now - stats["last_log"] > 2.0:
            logger.info(
                "uid=%s speech_frames=%s silence_frames=%s buffered_bytes=%s speaking=%s",
                uid,
                stats["speech"],
                stats["silence"],
                len(self.buffers.get(uid, b"")),
                self.speaking.get(uid, False),
            )
            stats["speech"] = 0
            stats["silence"] = 0
            stats["last_log"] = now

    async def cleanup_loop(self):
        await asyncio.sleep(1)

        while True:
            await asyncio.sleep(0.2)

            now = time.time()

            for uid in list(self.buffers.keys()):
                silence = self.silence_start.get(uid)

                if silence and now - silence > 1.0:
                    audio = bytes(self.buffers[uid])
                    self.buffers[uid] = bytearray()
                    self.silence_start[uid] = None

                    if len(audio) > 3000:
                        logger.info("Processing speech segment uid=%s bytes=%s", uid, len(audio))
                        await self.process_audio(audio, uid)

    async def process_audio(self, audio, uid):
        logger.info("processing audio uid=%s bytes=%s", uid, len(audio))

        import wave
        import tempfile
        import os

        # safe temp file
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        tmp_name = tmp.name
        tmp.close()

        # write proper wav
        with wave.open(tmp_name, "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(48000)
            f.writeframes(audio)

        # Save what Whisper hears for debugging.
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        base = f"uid_{uid}_{ts}"
        debug_wav = DEBUG_AUDIO_DIR / f"{base}.wav"
        debug_mp3 = DEBUG_AUDIO_DIR / f"{base}.mp3"
        try:
            with wave.open(str(debug_wav), "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(48000)
                wf.writeframes(audio)

            vc = self.ctx.voice_client
            if vc:
                ffmpeg_exe = getattr(getattr(vc, "client", None), "_ffmpeg_executable", None) or "ffmpeg"
            else:
                ffmpeg_exe = "ffmpeg"
            ffmpeg_probe = discord.FFmpegPCMAudio(str(debug_wav), executable=ffmpeg_exe)
            ffmpeg_probe.cleanup()
            process = await asyncio.create_subprocess_exec(
                ffmpeg_exe,
                "-y",
                "-i",
                str(debug_wav),
                "-codec:a",
                "libmp3lame",
                "-qscale:a",
                "4",
                str(debug_mp3),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await process.communicate()
            if process.returncode == 0:
                logger.info("Saved debug audio wav=%s mp3=%s", debug_wav, debug_mp3)
            else:
                logger.warning("Failed to convert debug mp3 for %s", debug_wav)
        except Exception as e:
            logger.warning("Failed to save debug audio: %s", e)

        # STT
        result = MODEL.transcribe(tmp_name)
        text = result["text"].strip()

        os.remove(tmp_name)

        logger.info("whisper text uid=%s text=%r", uid, text)

        if not text:
            return

        async with aiohttp.ClientSession() as session:
            async with session.get(
                "http://localhost:5000/chat",
                params={
                    "id": str(uid),
                    "message": encrypt(text,"TOP_SECRET_KEY"),
                    "think": 0,
                },
            ) as resp:
                reply = await resp.text()

        reply = clean(reply)

        await self.tts_and_speak(reply)

    async def tts_and_speak(self, text):
        import tempfile
        import os

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tmp_name = tmp.name
        tmp.close()

        communicate = edge_tts.Communicate(text, "en-US-JennyNeural")
        await communicate.save(tmp_name)

        vc = self.ctx.voice_client
        if not vc:
            return

        if vc.is_playing():
            vc.stop()

        vc.play(discord.FFmpegPCMAudio(tmp_name))

        while vc.is_playing():
            await asyncio.sleep(0.2)

        os.remove(tmp_name)

    def wants_opus(self) -> bool:
        return False  # raw PCM for Whisper/VAD

    def cleanup(self):
        pass


# -----------------------------
# CLEAN TEXT
# -----------------------------
def clean(text):
    raw = str(text or "").strip()
    if not raw:
        return ""
    fixed = raw.replace(",]", "]")
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
        joined = "".join(parts).strip()
        if joined:
            return joined
    return raw.replace("[THINK_START]", "").replace("[THINK_END]", "").strip()


# -----------------------------
# START LOOP TASK
# -----------------------------
@bot.event
async def on_ready():
    logger.info("Logged in as %s", bot.user)


# -----------------------------
# RUN
# -----------------------------
bot.run(TOKEN)
