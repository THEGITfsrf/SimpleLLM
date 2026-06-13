from __future__ import annotations

from typing import Any

# Stores previous values to turn raw metrics into "change events".
_PREV: dict[str, Any] = {
    "cpu": None,
    "ram": None,
    "disk_free_gb": None,
    "net_up": None,
    "known_processes": {},
}


def _changed(key: str, value: Any) -> bool:
    prev = _PREV.get(key)
    _PREV[key] = value
    return prev is not None and prev != value


def _metric_drop(prev: float | None, current: float, drop: float) -> bool:
    return prev is not None and (prev - current) >= drop


def register(bus):
    @bus.on("cpu_watch")
    def cpu_watch(data=None):
        data = data or {}
        cpu = float(data.get("cpu_percent", 0.0))
        prev = _PREV.get("cpu")
        _PREV["cpu"] = cpu

        high = cpu >= float(data.get("high_threshold", 90.0))
        sharp_jump = prev is not None and (cpu - prev) >= float(data.get("jump_threshold", 25.0))

        return {
            "to_llm": bool(high or sharp_jump),
            "payload": {
                "event": "cpu_watch",
                "cpu_percent": cpu,
                "high": high,
                "sharp_jump": sharp_jump,
            },
        }

    @bus.on("ram_watch")
    def ram_watch(data=None):
        data = data or {}
        ram = float(data.get("ram_percent", 0.0))
        prev = _PREV.get("ram")
        _PREV["ram"] = ram

        high = ram >= float(data.get("high_threshold", 90.0))
        sharp_jump = prev is not None and (ram - prev) >= float(data.get("jump_threshold", 20.0))

        return {
            "to_llm": bool(high or sharp_jump),
            "payload": {
                "event": "ram_watch",
                "ram_percent": ram,
                "high": high,
                "sharp_jump": sharp_jump,
            },
        }

    @bus.on("disk_space_watch")
    def disk_space_watch(data=None):
        data = data or {}
        free_gb = float(data.get("free_gb", 0.0))
        prev = _PREV.get("disk_free_gb")
        _PREV["disk_free_gb"] = free_gb

        low = free_gb <= float(data.get("low_threshold_gb", 5.0))
        sudden_drop = _metric_drop(prev, free_gb, float(data.get("drop_threshold_gb", 2.0)))

        return {
            "to_llm": bool(low or sudden_drop),
            "payload": {
                "event": "disk_space_watch",
                "free_gb": free_gb,
                "low": low,
                "sudden_drop": sudden_drop,
            },
        }

    @bus.on("network_up_down_watch")
    def network_up_down_watch(data=None):
        data = data or {}
        is_up = bool(data.get("is_up", True))
        changed = _changed("net_up", is_up)

        return {
            "to_llm": bool(changed),
            "payload": {
                "event": "network_up_down_watch",
                "is_up": is_up,
                "changed": changed,
            },
        }

    @bus.on("process_crash_watch")
    def process_crash_watch(data=None):
        data = data or {}
        name = str(data.get("process_name", "unknown"))
        pid = data.get("pid")
        is_running = bool(data.get("is_running", False))

        known = _PREV.setdefault("known_processes", {})
        prev_running = known.get(name)
        known[name] = is_running

        crashed = prev_running is True and is_running is False

        return {
            "to_llm": bool(crashed),
            "payload": {
                "event": "process_crash_watch",
                "process_name": name,
                "pid": pid,
                "crashed": crashed,
                "is_running": is_running,
            },
        }
