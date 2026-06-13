from __future__ import annotations

from typing import Any

_STATE: dict[str, Any] = {
    "services": {},
    "plugins": {},
    "files": {},
}


def register(bus):
    @bus.on("app_started")
    def app_started(data=None):
        data = data or {}
        app_name = str(data.get("app_name", "unknown"))
        version = data.get("version")

        return {
            "to_llm": bool(data.get("notify", False)),
            "payload": {
                "event": "app_started",
                "app_name": app_name,
                "version": version,
            },
        }

    @bus.on("app_crashed")
    def app_crashed(data=None):
        data = data or {}
        return {
            "to_llm": True,
            "payload": {
                "event": "app_crashed",
                "app_name": data.get("app_name", "unknown"),
                "reason": data.get("reason"),
                "exit_code": data.get("exit_code"),
            },
        }

    @bus.on("service_restart")
    def service_restart(data=None):
        data = data or {}
        service = str(data.get("service_name", "unknown"))
        restart_count = int(data.get("restart_count", 1))

        previous = _STATE["services"].get(service, 0)
        _STATE["services"][service] = restart_count
        changed = restart_count != previous

        return {
            "to_llm": bool(changed and restart_count >= int(data.get("notify_after", 2))),
            "payload": {
                "event": "service_restart",
                "service_name": service,
                "restart_count": restart_count,
            },
        }

    @bus.on("file_changed_watch")
    def file_changed_watch(data=None):
        data = data or {}
        path = str(data.get("path", ""))
        fingerprint = data.get("fingerprint") or data.get("mtime") or data.get("hash")

        prev = _STATE["files"].get(path)
        _STATE["files"][path] = fingerprint
        changed = prev is not None and prev != fingerprint

        return {
            "to_llm": bool(changed),
            "payload": {
                "event": "file_changed_watch",
                "path": path,
                "changed": changed,
                "fingerprint": fingerprint,
            },
        }

    @bus.on("plugin_loaded")
    def plugin_loaded(data=None):
        data = data or {}
        plugin = str(data.get("plugin_name", "unknown"))
        _STATE["plugins"][plugin] = "loaded"

        return {
            "to_llm": bool(data.get("notify", False)),
            "payload": {
                "event": "plugin_loaded",
                "plugin_name": plugin,
            },
        }

    @bus.on("plugin_failed")
    def plugin_failed(data=None):
        data = data or {}
        plugin = str(data.get("plugin_name", "unknown"))
        error = data.get("error")
        _STATE["plugins"][plugin] = "failed"

        return {
            "to_llm": True,
            "payload": {
                "event": "plugin_failed",
                "plugin_name": plugin,
                "error": error,
            },
        }
