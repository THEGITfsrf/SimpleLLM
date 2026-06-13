import json
import aiohttp
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
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


# -----------------------------
# CONFIG
# -----------------------------
def load_token():
    with open("C:/Users/safra/SimpleLLM/plugins/keys.json", "r", encoding="utf-8") as f:
        return json.load(f)["telegram"]

TOKEN = load_token()

GOOD_IDS = {5784669276}  # whitelist

AI_URL = "http://localhost:5000/chat"

# -----------------------------
# STATE
# -----------------------------
sessions = {}

def get_session(user_id):
    if user_id not in sessions:
        sessions[user_id] = []
    return sessions[user_id]

# -----------------------------
# CLEAN OUTPUT
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
# START COMMAND
# -----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 AI bot online. Just talk to me.")

# -----------------------------
# MAIN CHAT HANDLER
# -----------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # 🔒 whitelist check
    if user.id not in GOOD_IDS:
        await update.message.reply_text("❌ Not authorized.")
        return

    text = update.message.text
    session = get_session(user.id)
    session.append({"role": "user", "content": text})

    await update.message.chat.send_action("typing")

    async with aiohttp.ClientSession() as session_http:
        async with session_http.get(
            AI_URL,
            params={
                "id": str(user.id),
                "message": encrypt(text,"TOP_SECRET_KEY"),
                "think": 0
            }
        ) as resp:
            reply = await resp.text()

    reply = clean(reply)

    session.append({"role": "assistant", "content": reply})

    await update.message.reply_text(reply[:4000])

# -----------------------------
# MAIN
# -----------------------------
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Telegram bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
