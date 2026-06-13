import subprocess

description = "Read from or write to the Windows clipboard."
args = {
    "action": {"type": "string", "description": "read | write | clear"},
    "text": {"type": "string", "description": "Text to write when action=write"},
}
required = ["action"]


def main(action, text=None):
    try:
        a = (action or "").strip().lower()

        if a == "read":
            res = subprocess.run(
                ["powershell", "-Command", "Get-Clipboard"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return {"action": "read", "text": res.stdout.strip()}

        if a == "write":
            if text is None:
                return {"error": "text is required for write"}
            cmd = f"Set-Clipboard -Value @'\n{text}\n'@"
            subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True, timeout=5)
            return {"action": "write", "status": "ok"}

        if a == "clear":
            subprocess.run(["powershell", "-Command", "Set-Clipboard -Value ''"], capture_output=True, text=True, timeout=5)
            return {"action": "clear", "status": "ok"}

        return {"error": "Unknown action. Use read, write, or clear."}
    except Exception as e:
        return {"error": f"clipboard tool failed: {e}"}
