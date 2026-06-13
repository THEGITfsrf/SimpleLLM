import ctypes
import os
import subprocess
import time

try:
    import psutil
except Exception:
    psutil = None


description = "Returns a real-time system awareness snapshot: CPU, RAM, disk, network, focused window, microphone activity hint, and top processes."
args = {
    "include_processes": {"type": "boolean", "description": "Include top memory-heavy processes. Default true."},
    "limit": {"type": "integer", "description": "Maximum number of processes to include. Default 5."},
}
required = []


def _focused_window_title():
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


def _gpu_usage():
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=1.5,
        ).strip()
        vals = [int(x.strip()) for x in out.splitlines() if x.strip()]
        return vals if vals else None
    except Exception:
        return None


def _top_processes(limit):
    rows = []
    for proc in psutil.process_iter(["pid", "name", "memory_info", "status"]):
        try:
            mem = proc.info.get("memory_info")
            rows.append({
                "pid": proc.info.get("pid"),
                "name": proc.info.get("name") or "unknown",
                "status": proc.info.get("status"),
                "memory_mb": round((mem.rss if mem else 0) / (1024 ** 2), 1),
            })
        except Exception:
            continue
    rows.sort(key=lambda row: row["memory_mb"], reverse=True)
    return rows[: max(1, int(limit or 5))]


def main(include_processes=True, limit=5):
    if psutil is None:
        return {"error": "psutil is required for system_awareness"}

    vm = psutil.virtual_memory()
    disk = psutil.disk_usage("C:/")
    net = psutil.net_io_counters()
    snapshot = {
        "timestamp": time.time(),
        "cpu_percent": psutil.cpu_percent(interval=0.25),
        "ram_percent": vm.percent,
        "ram_available_gb": round(vm.available / (1024 ** 3), 2),
        "disk_c_used_percent": disk.percent,
        "network": {
            "bytes_sent": net.bytes_sent,
            "bytes_recv": net.bytes_recv,
        },
        "focused_window": _focused_window_title(),
        "gpu_usage_percent": _gpu_usage(),
        "microphone_state": "unknown",
    }
    if include_processes:
        snapshot["top_processes"] = _top_processes(limit)
    return snapshot
