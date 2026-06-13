from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
import importlib.util
import traceback
import requests
import threading
import time
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.backends import default_backend
import os
import base64

def log(tag: str, msg: str):
    print(f"[{tag}] {msg}")
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


class EventBus:
    def __init__(self) -> None:
        self.listeners: dict[str, list[Callable[[Any], Any]]] = {}

    def on(self, event_name: str):
        def decorator(func: Callable[[Any], Any]):
            self.listeners.setdefault(event_name, []).append(func)
            return func
        return decorator

    def emit(self, event_name: str, data: Any = None) -> list[Any]:
        results: list[Any] = []
        log("EVENT", f"{event_name} → data={data}")
        for fn in self.listeners.get(event_name, []):
            results.append(fn(data))
        return results


@dataclass
class HookResult:
    hook: str
    to_llm: bool
    payload: Any = None
    error: str | None = None


class HookHandler:
    """
    Loads hook modules from `simplellm/hooks` and routes events through an EventBus.

    Hook module contract:
    - Must expose `register(bus)`.
    - Inside register, use @bus.on("event_name") handlers.
    - Handlers can return either:
      1) {"to_llm": bool, "payload": any}
      2) any other value (treated as hidden, not sent to LLM)
    """

    def __init__(
        self,
        hooks_dir: str | Path | None = None,
        chat_url: str = "http://127.0.0.1:5000/chat",
    ) -> None:
        default_hooks_dir = Path(__file__).resolve().parents[1] / "hooks"
        self.hooks_dir = Path(hooks_dir) if hooks_dir else default_hooks_dir
        self.bus = EventBus()
        self.loaded_modules: dict[str, Any] = {}
        self.chat_url = chat_url

    def _hook_files(self) -> list[Path]:
        if not self.hooks_dir.exists():
            return []
        files = []
        for path in self.hooks_dir.glob("*.py"):
            if path.name in {"__init__.py", "handler.py"}:
                continue
            files.append(path)
        return sorted(files)

    def load_hooks(self) -> dict[str, str]:
        """Load all hook files and call their register(bus)."""
        status: dict[str, str] = {}
        for file_path in self._hook_files():
            log("HOOK", f"Loading: {file_path.name}")
            module_name = f"simplellm.hooks.{file_path.stem}"
            try:
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                if spec is None or spec.loader is None:
                    status[file_path.name] = "failed: could not create module spec"
                    continue

                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                register = getattr(module, "register", None)
                if not callable(register):
                    status[file_path.name] = "skipped: missing register(bus)"
                    continue

                register(self.bus)
                self.loaded_modules[file_path.stem] = module
                status[file_path.name] = "loaded"
                log("HOOK", f"Loaded: {file_path.stem}")
            except Exception:
                status[file_path.name] = "failed: " + traceback.format_exc(limit=1).strip()
        log("DEBUG", f"listeners = {self.bus.listeners}")
        return status

    def emit(self, event_name: str, data: Any = None) -> dict[str, Any]:
        """
        Run all listeners for the event.

        Returns:
        {
          "event": str,
          "all_results": [HookResult, ...],
          "llm_payloads": [payload, ...]
        }
        """
        raw_results = self.bus.emit(event_name, data)
        normalized: list[HookResult] = []
        llm_payloads: list[Any] = []

        listeners = self.bus.listeners.get(event_name, [])
        for idx, value in enumerate(raw_results):
            hook_name = listeners[idx].__module__ if idx < len(listeners) else "unknown"
            log( "HOOK_RUN", f"{hook_name} returned {value}" )
            if isinstance(value, dict) and "to_llm" in value:
                result = HookResult(
                    hook=hook_name,
                    to_llm=bool(value.get("to_llm", False)),
                    payload=value.get("payload"),
                )
            else:
                result = HookResult(hook=hook_name, to_llm=False, payload=value)

            normalized.append(result)
            if result.to_llm:
                llm_payloads.append(result.payload)

        return {
            "event": event_name,
            "all_results": normalized,
            "llm_payloads": llm_payloads,
        }

    def should_notify_llm(self, emit_result: dict[str, Any]) -> bool:
        return bool(emit_result.get("llm_payloads"))

    def notify_llm(
        self,
        emit_result: dict[str, Any],
        chat_id: str,
        think: bool = False,
        agent: str | None = None,
        timeout_sec: int = 30,
    ) -> list[str]:
        """
        Send LLM-visible hook payloads to `/chat` and return text responses.
        """
        payloads = emit_result.get("llm_payloads", [])
        if not payloads:
            return []

        responses: list[str] = []
        for payload in payloads:
            params: dict[str, str] = {
                "id": chat_id,
                "think": "1" if think else "0",
                "message": encrypt("Alert the user if nescessary, the user will not hear your response to this unless you use alert" + str(payload), "TOP_SECRET_KEY"),
            }
            if agent:
                params["agent"] = agent
            resp = requests.get(self.chat_url, params=params, timeout=timeout_sec)
            resp.raise_for_status()
            responses.append(resp.text)
        return responses


class Engine:
    def __init__(self, handler: HookHandler) -> None:
        self.handler = handler
        self.running = False
        self.thread = None
        self.interval = 5  # seconds between ticks
        self.cooldowns: dict[str, float] = {}

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)

    def _run_loop(self):
        while self.running:
            try:
                self._tick()
                
            except Exception as e:
                print(f"[HOOK ENGINE ERROR] {e}")
            time.sleep(self.interval)

    def _tick(self):
        log("ENGINE", "tick fired") 
        result = self.handler.emit("tick", {"time": time.time()})
        if self.handler.should_notify_llm(result):
            self.handler.notify_llm(result, chat_id="system")

    def _allowed(self, key: str, cooldown_sec: int = 30) -> bool:
        now = time.time()
        last = self.cooldowns.get(key, 0)
        if now - last < cooldown_sec:
            return False
        self.cooldowns[key] = now
        return True


__all__ = ["EventBus", "HookResult", "HookHandler", "Engine"]

if __name__ == "__main__":
    print("Hook Handler Starting")
    handler = HookHandler()
    handler.load_hooks()
    engine = Engine(handler)
    engine.start()
    try:
        while True:
            time.sleep(1)   # 👈 keeps process alive
    except KeyboardInterrupt:
        engine.stop()