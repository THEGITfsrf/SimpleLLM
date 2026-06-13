# SimpleLLM

SimpleLLM is a local, Windows-first assistant workspace. The main project is a JARVIS-style voice assistant backed by a Flask chat server, local Ollama models, dynamically loaded tools, optional wakeword detection, speech-to-text, text-to-speech, a desktop HUD overlay, and a small hook/event system for background monitoring.

This repository is also a working sandbox. It contains the assistant runtime plus experiments for wakeword training, image generation, audio assets, UI tests, and small Flask/Three.js games. Treat `main.py`, `plugins/`, `addons/`, `simplellm/hooks/`, `templates/`, `test.html`, `save.json`, and `memory.json` as the core assistant surface.

## What This Project Does

- Runs a local web chat server with Ollama tool calling.
- Loads Python tool modules from `addons/` at startup.
- Stores conversation history in `save.json`.
- Stores simple long-term memories in `memory.json`.
- Routes prompts through intent/state metadata with a backward-compatible fast/thinker route in `test_router.py`.
- Accepts encrypted chat requests from voice, Telegram, Discord, and hook integrations.
- Provides a voice runtime with wakeword support, VAD speech segmentation, Whisper/faster-whisper transcription, TTS playback, and optional RGB effects.
- Provides a PyQt6 JARVIS HUD overlay controlled through a local socket.
- Provides hook/event machinery for background system monitoring and LLM notifications.
- Includes optional Gmail, clipboard, screenshot, task manager, weather, soundboard, crawler, app launcher, system-awareness, and system-info tools.

## Core Runtime Architecture

```text
User voice / browser / bot
        |
        v
Encrypted /chat request
        |
        v
main.py Flask chat server
        |
        +-- Ollama model selection and streaming response
        +-- built-in tools: file, shell, search, memory, agent mode
        +-- addon tools loaded from addons/*.py
        +-- conversation persistence in save.json
        |
        v
Tool results and final assistant response
        |
        +-- browser UI renders response chunks
        +-- voice runtime speaks response
        +-- bots relay response
```

### `main.py`

`main.py` is the primary assistant server.

Routes:

- `GET /` serves `test.html`, the browser chat UI.
- `GET /chat` handles encrypted prompt requests, streams JSON-like response chunks, runs tool calls, and saves chat history.
- `GET /vc` tries to serve `vc.html` if present.
- `GET /new` returns the number of active chat IDs in memory.

Important behavior:

- The default model is currently `qwen3.5:9b`.
- `/chat` expects `message`, `id`, and `think` query parameters.
- `message` must be encrypted with the shared AES helper and `TOP_SECRET_KEY`.
- `think` is accepted as `0` or `1`, but the final routing decision is recalculated by `test_router.py`.
- On startup, every `*.py` file in `plugins/` is launched as a subprocess.
- Every valid `addons/*.py` module is loaded into the tool registry.
- Tool-call loops are guarded by `LoopGuard`.
- Logs are written to `server.log` and stdout.

### `plugins/vc.py`

`plugins/vc.py` is the voice runtime.

It handles:

- Microphone capture through PyAudio.
- Voice activity detection through `webrtcvad`.
- Wakeword detection through `openwakeword` when available.
- Speech transcription through `faster-whisper` or OpenAI Whisper.
- Deterministic local routing for some requests such as weather, time, and system info.
- Encrypted prompt submission to `http://127.0.0.1:5000/chat`.
- TTS through Kokoro or Edge TTS paths when available.
- Optional OpenRGB device state changes.
- Optional PyQt overlay state updates.
- Speech behavior metadata such as tone, speed, and pause timing.
- Idle-time proactive CPU/RAM/GPU alerts through `SystemAwareness`.

Key constants to know:

- `AI_URL = "http://127.0.0.1:5000/chat"`
- `AGENT_MAP` maps short voice model keys to Ollama model names.
- `DEFAULT_AGENT_KEY = "p"`
- `WAKEWORD_MODEL_PATH` points to `Jarvis_20260313_215039.onnx`.
- `PREFERRED_MIC_NAME_SUBSTRING = "fifine"`

### `plugins/jarvis_overlay_v3.py`

This is a standalone transparent PyQt6 HUD overlay. It can be run directly and controlled through a socket server on:

```text
127.0.0.1:5055
```

Expected socket commands include state controls such as `idle`, `active`, `thinking`, and `toggle`.

### `plugins/handler.py`

This file implements the hook/event framework.

Main pieces:

- `EventBus`: registers and emits named events.
- `HookHandler`: loads hook modules from `simplellm/hooks/`.
- `Engine`: emits periodic `tick` events and can notify the LLM through `/chat`.

Hook modules must expose:

```python
def register(bus):
    @bus.on("event_name")
    def handler(data=None):
        return {"to_llm": True, "payload": {"message": "something happened"}}
```

### `test_router.py`

Despite the name, this is part of runtime routing. It classifies prompts into richer runtime metadata:

- `intent`: chat, question, coding, system status, automation, tool action, web lookup, creative, or control.
- `urgency`: low, normal, high, or critical.
- `complexity`: simple, moderate, or complex.
- `tool_need`: none, optional, or required.
- `factual_mode`: true when specs, benchmarks, APIs, dates, prices, standards, or other precise facts matter.
- `response_style`: brief, conversational, stepwise, technical, or confirm-then-act.
- `assistant_state`: idle assistant, active helper, executing task, monitoring background, or voice-only mode.
- `route`: fast or thinker, preserved for Ollama think-mode compatibility.

It asks the Ollama model `fauxpaslife/arch-router:1.5b` for structured JSON and falls back to local heuristics if the model is unavailable. Comparison/spec queries such as `P100 vs RTX 3070 in specs` are forced into `technical_comparison`, `structured_table`, `factual_mode`, and `thinker` routing. Confidence below `0.75` also escalates non-chat/control requests away from the fast path.

## Tool System

Tools are available to the Ollama chat model through the OpenAI-style function/tool schema.

### Built-In Tools

Defined in `main.py`:

- `write_file(file_path, file_content)`: writes text to disk, creating parent directories when needed.
- `read_file(file_path)`: reads a text file from disk.
- `shell(cmd, cwd=None)`: runs a PowerShell command with a simple destructive-command blocklist.
- `search(query)`: queries a local Searx-style endpoint at `http://localhost:8080/?q=...`.
- `agent_mode(goal)`: runs a planner, researcher, executor, and verifier sequence through Ollama.
- `remember(memory)`: appends a memory string to `memory.json`.
- `recall_memories()`: returns saved memory strings.

### Addon Tools

Every `addons/*.py` file can become a model-callable tool if it defines:

```python
description = "What the tool does"
args = {
    "name": {"type": "string", "description": "Argument description"}
}
required = ["name"]

def main(name):
    return "result"
```

Current addon tools:

| Tool | Purpose |
| --- | --- |
| `alert` | Speaks an alert through the voice/TTS path. |
| `app_launcher` | Lists and opens desktop apps. |
| `calculator` | Safely evaluates math expressions. |
| `clipboard` | Reads or writes the Windows clipboard. |
| `code_test` | Compiles/tests snippets for errors. |
| `crawlee` | Crawls and extracts structured web content with depth/domain controls. |
| `discord_sender` | Sends messages to Discord. |
| `echo` | Echoes input text. |
| `gmail` | Sends, reads, and deletes Gmail messages. |
| `hello` | Returns a hello response. |
| `highlight` | Shows a temporary screen highlight circle. |
| `hooks` | Generates monitor hook files for the hook engine. |
| `request` | Voice-command intake bypass with safety gating. |
| `screenshot` | Captures the user's screen and returns image metadata/path. |
| `soundboard` | Plays and lists local sound files. |
| `system_awareness` | Returns CPU, RAM, disk, network, focused window, GPU, and top-process snapshot. |
| `sysinfo` | Returns broad Windows system information. |
| `sysinfo_specific` | Returns targeted CPU/RAM/GPU/disk/OS metrics. |
| `tasks` | Lists, inspects, prioritizes, and stops processes with confirmation gates. |
| `time_convert` | Converts datetimes between time zones. |
| `time_now` | Gets current time in a time zone. |
| `weather` | Gets current weather and short forecast through wttr.in. |

Restart `main.py` after adding or changing addon tools.

## Plugins

Files in `plugins/` are not just importable helpers. `main.py` starts every `plugins/*.py` file as a subprocess when the server launches.

Current important plugins:

- `vc.py`: voice runtime and a callable `transcribe_file` mode.
- `jarvis_overlay_v3.py`: transparent desktop HUD.
- `handler.py`: event and hook runner.
- `telegram_bot.py`: Telegram integration.
- `discord_bot.py`: Discord voice/chat integration.
- `open_app.py`: older app-opening plugin/tool implementation.

Because plugin files are auto-started, do not place throwaway Python scripts in `plugins/` unless you want them launched with the server.

## State, Secrets, And Generated Files

Runtime state:

- `save.json`: persisted chat sessions.
- `memory.json`: simple long-term memory list.
- `server.log`: Flask/tool-call logs.
- `sessions.json`: small session metadata.
- `mem0_db/`: local memory/vector database artifacts.

Local model/audio assets:

- `Jarvis_20260313_215039.onnx`: custom wakeword model.
- `Jarvis_20260313_215039.tflite`: wakeword/model artifact.
- `piper_cli/`: bundled Piper executable and support files.
- `piper_models/`: local Piper voices.
- `addons/sounds/`: soundboard audio files.
- `workspace_fast/`, `dataset/`, `esc50.zip`: wakeword/audio training data and artifacts.

Credentials and sensitive files:

- `plugins/keys.json` is used by bot/plugin integrations.
- Gmail code expects credentials under `C:/Users/safra/SimpleLLM/.google/`.
- The encryption key string `TOP_SECRET_KEY` is hardcoded in multiple files.

This project assumes trusted local use. Do not expose the Flask server, plugin sockets, bot endpoints, or search/tool services to an untrusted network without hardening them.

## Setup

### 1. Install system tools

Required:

- Windows 10/11
- Python 3.11 or newer
- PowerShell
- Ollama

Recommended:

- A working microphone.
- A local Searx/SearxNG-compatible search endpoint on port `8080` if you want the `search` tool.
- OpenRGB if you want RGB device feedback.

### 2. Install Python dependencies

There is no single root `requirements.txt` for the whole assistant runtime. Install the pieces you need.

Core server:

```powershell
pip install flask ollama requests cryptography markdown mem0 qdrant-client pydantic
```

Voice runtime:

```powershell
pip install aiohttp pyaudio webrtcvad faster-whisper openai-whisper edge-tts numpy sounddevice soundfile playsound PyQt6 openwakeword openrgb-python
```

Tool-specific dependencies:

```powershell
pip install beautifulsoup4 pyautogui pillow psutil google-auth google-auth-oauthlib google-api-python-client
```

Wakeword/image/audio training extras are listed in `requirements-ai-gen.txt`:

```powershell
pip install -r requirements-ai-gen.txt
```

Some dependencies are optional and are guarded by `try/except` imports. Missing optional packages may disable one feature while leaving the rest of the assistant usable.

### 3. Pull Ollama models

Models referenced by the current code include:

```powershell
ollama pull qwen3.5:9b
ollama pull qwen3.5:9b-q4_K_M
ollama pull deepseek-coder:6.7b
ollama pull qwen2.5:7b-instruct-q4_0
ollama pull fauxpaslife/arch-router:1.5b
ollama pull qwen3:4b-q4_K_M
ollama pull mxbai-embed-large
```

You only need the models used by the path you run. For the default server path, start with `qwen3.5:9b` and `fauxpaslife/arch-router:1.5b`.

## Running The Assistant

Start Ollama:

```powershell
ollama serve
```

Start the Flask chat/tool server:

```powershell
python main.py
```

Open the browser UI:

```text
http://127.0.0.1:5000/
```

Start voice mode in a second terminal:

```powershell
python plugins/vc.py
```

Start only the HUD overlay:

```powershell
python plugins/jarvis_overlay_v3.py
```

Run the hook engine:

```powershell
python plugins/handler.py
```

Expected voice flow:

1. Say a wake phrase such as `hey jarvis`.
2. Speak the request.
3. `vc.py` transcribes audio.
4. The prompt is encrypted and sent to `/chat`.
5. `main.py` streams model/tool output.
6. `vc.py` cleans and speaks the response.
7. The overlay moves through states such as idle, listening, thinking, and speaking.

## API Notes

`/chat` is a GET endpoint:

```text
/chat?id=<chat-id>&think=0&agent=<optional-model>&message=<encrypted-message>
```

`message` must be AES-encrypted using the helper functions duplicated in `main.py`, `plugins/vc.py`, and `plugins/handler.py`.

The response is streamed as an array-like sequence of JSON objects with types such as:

- `thinking`
- `response`
- `tool`
- `stop`

The stream is currently returned with `text/html`, not `application/json`.

## Development

### Add A Tool

1. Create `addons/my_tool.py`.
2. Define `description`, `args`, `required`, and `main(...)`.
3. Restart `python main.py`.
4. Ask the assistant something that should trigger the tool.

Example:

```python
description = "Returns a greeting for a person."
args = {
    "name": {"type": "string", "description": "Person to greet"}
}
required = ["name"]

def main(name):
    return f"Hello, {name}."
```

### Add A Hook

1. Create a file in `simplellm/hooks/`.
2. Expose `register(bus)`.
3. Register handlers with `@bus.on("event_name")`.
4. Return `{"to_llm": True, "payload": ...}` when the assistant should be notified.

Existing hook examples:

- `simplellm/hooks/event_hooks.py`
- `simplellm/hooks/system_reality_hooks.py`

### Change Models

- Server default model: edit `model` in `main.py`.
- Voice model aliases: edit `AGENT_MAP` and `DEFAULT_AGENT_KEY` in `plugins/vc.py`.
- Router model: edit `test_router.py`.
- Agent-mode planner/researcher/executor/verifier models: edit those functions in `main.py`.

### Change Ports

Current defaults:

- Flask chat server: `127.0.0.1:5000`
- Voice runtime chat target: `http://127.0.0.1:5000/chat`
- Hook chat target: `http://127.0.0.1:5000/chat`
- Overlay socket: `127.0.0.1:5055`
- Search tool endpoint: `http://localhost:8080/`
- `app.py` zombie-game server: port `5001`

Keep these in sync if you move the Flask server.

## Tests And Diagnostics

The repository has several test and diagnostic scripts, but not all of them target the current `main.py` runtime.

Useful checks:

```powershell
python -m pytest test_router.py
python test_simple.py
python test_fixes.py
python test-onnx.py
python animations_test.py
```

Notes:

- `test_router.py` contains executable sample cases at module import time and depends on Ollama.
- `test_app.py` appears to target old `/add` and `/mul` endpoints that are not present in the current `main.py`.
- Voice and overlay scripts are best tested manually because they depend on microphone, audio output, GUI, and local model availability.
- Check `server.log` after server runs.

## Other Projects In This Workspace

These directories are side projects or experiments:

- `game/`: static browser game files.
- `zombie-game/`: standalone Flask zombie game.
- `threejs_multiplier_game/`: Three.js multiplier game experiment.
- `multiplier-game/`, `shooter_game/`, `turret_game.py`: game experiments.
- `myapp/`: separate app/database/migration workspace.
- `ai_gen.py`, `image-generator.py`, `noise.py`, `benchmark_vc_response_time.py`: wakeword, audio, image, and benchmark scripts.
- `templates/`: HTML templates used by assistant and game experiments.

## Troubleshooting

### Server will not start

- Confirm Ollama is installed and reachable.
- Install core Python dependencies.
- Check whether any `plugins/*.py` subprocess is crashing or blocking startup.
- Review `server.log`.

### `/chat` returns errors

- Confirm `message` is encrypted with the expected key.
- Confirm `id` and `think` are present.
- Confirm the router model exists locally or let routing fall back to `fast`.
- Confirm the selected Ollama chat model exists locally.

### Voice does not respond

- Confirm microphone access and PyAudio installation.
- Check `PREFERRED_MIC_NAME_SUBSTRING` in `plugins/vc.py`.
- Confirm Whisper or faster-whisper is installed.
- Confirm the wakeword model file exists.
- Try lowering `WAKEWORD_THRESHOLD`.
- Watch stdout logs from `plugins/vc.py`.

### Overlay does not appear

- Install `PyQt6`.
- Run `python plugins/jarvis_overlay_v3.py` directly.
- Check that the overlay socket port `5055` is free.
- Confirm Windows is not blocking always-on-top transparent windows.

### Tools do not show up

- Confirm the file is in `addons/`.
- Confirm it defines `description`, `args`, `required`, and `main`.
- Restart `main.py`.
- Watch startup output for `INVALID FILE: ...`.

## Security And Hardening

Current behavior is designed for a local trusted machine. Important risks:

- The Flask server exposes file read/write tools and a PowerShell execution tool.
- The `shell` blocklist is limited and should not be treated as a security sandbox.
- The encryption key is hardcoded as `TOP_SECRET_KEY`.
- Bot and Gmail integrations rely on local credential files.
- Plugins auto-start when `main.py` starts.
- The app assumes localhost access and does not implement user authentication.

Recommended hardening before any broader use:

- Move keys, ports, model names, and credential paths into environment variables.
- Add authentication to HTTP and socket endpoints.
- Replace the shell tool with an allowlisted command runner.
- Do not auto-start every plugin file.
- Move generated data, logs, model binaries, and credentials out of source control.
- Add a real root `requirements.txt` or `pyproject.toml`.
- Split tests into current runtime tests and legacy/experiment tests.

## Quick File Map

| Path | Role |
| --- | --- |
| `main.py` | Main Flask assistant server and tool-calling loop. |
| `test.html` | Browser chat UI served by `main.py`. |
| `plugins/vc.py` | Voice runtime. |
| `plugins/jarvis_overlay_v3.py` | Transparent desktop HUD overlay. |
| `plugins/handler.py` | Hook/event framework. |
| `addons/` | Dynamic assistant tools. |
| `simplellm/hooks/` | Hook modules loaded by `HookHandler`. |
| `simple_llm.py` | Gmail helper module. |
| `simplellm/` | Python package namespace for hooks. |
| `test_router.py` | Ollama prompt router used by `/chat`. |
| `save.json` | Conversation storage. |
| `memory.json` | Simple long-term memory storage. |
| `server.log` | Runtime log file. |
| `piper_cli/`, `piper_models/` | Local TTS assets. |
| `requirements-ai-gen.txt` | Extra dependencies for wakeword/image/audio generation work. |
