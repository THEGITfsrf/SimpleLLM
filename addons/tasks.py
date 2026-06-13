import psutil

description = "Task manager control: list, inspect, set priority, and stop processes with safety confirmations."
args = {
    "action": {"type": "string", "description": "list | inspect | stop | set_priority"},
    "pid": {"type": "integer", "description": "Process ID for inspect/stop/set_priority"},
    "name_filter": {"type": "string", "description": "Optional process name filter for list"},
    "limit": {"type": "integer", "description": "Max number of processes returned for list"},
    "confirm_destructive": {"type": "boolean", "description": "Must be true for stop/set_priority"},
    "priority": {"type": "string", "description": "idle | below_normal | normal | above_normal | high"},
}
required = ["action"]


PRIORITY_MAP = {
    "idle": psutil.IDLE_PRIORITY_CLASS,
    "below_normal": psutil.BELOW_NORMAL_PRIORITY_CLASS,
    "normal": psutil.NORMAL_PRIORITY_CLASS,
    "above_normal": psutil.ABOVE_NORMAL_PRIORITY_CLASS,
    "high": psutil.HIGH_PRIORITY_CLASS,
}


def _proc_row(proc):
    with proc.oneshot():
        return {
            "pid": proc.pid,
            "name": proc.name(),
            "status": proc.status(),
            "cpu_percent": proc.cpu_percent(interval=0.0),
            "memory_mb": round(proc.memory_info().rss / (1024 ** 2), 2),
        }


def main(action, pid=None, name_filter=None, limit=25, confirm_destructive=False, priority="normal"):
    try:
        a = (action or "").strip().lower()

        if a == "list":
            rows = []
            needle = (name_filter or "").lower().strip()
            for proc in psutil.process_iter():
                try:
                    row = _proc_row(proc)
                    if needle and needle not in row["name"].lower():
                        continue
                    rows.append(row)
                except Exception:
                    continue
            rows.sort(key=lambda r: (r["cpu_percent"], r["memory_mb"]), reverse=True)
            return {"action": "list", "count": len(rows), "processes": rows[: max(1, int(limit))]}

        if a == "inspect":
            if pid is None:
                return {"error": "pid is required for inspect"}
            proc = psutil.Process(int(pid))
            row = _proc_row(proc)
            row["cmdline"] = proc.cmdline()
            row["create_time"] = proc.create_time()
            return {"action": "inspect", "process": row}

        if a == "stop":
            if pid is None:
                return {"error": "pid is required for stop"}
            if not bool(confirm_destructive):
                return {"error": "stop requires confirm_destructive=true"}
            proc = psutil.Process(int(pid))
            proc.terminate()
            return {"action": "stop", "pid": int(pid), "result": "terminate sent"}

        if a == "set_priority":
            if pid is None:
                return {"error": "pid is required for set_priority"}
            if not bool(confirm_destructive):
                return {"error": "set_priority requires confirm_destructive=true"}
            key = (priority or "normal").strip().lower()
            if key not in PRIORITY_MAP:
                return {"error": "invalid priority"}
            proc = psutil.Process(int(pid))
            proc.nice(PRIORITY_MAP[key])
            return {"action": "set_priority", "pid": int(pid), "priority": key, "result": "updated"}

        return {"error": "Unknown action."}
    except Exception as e:
        return {"error": f"tasks tool failed: {e}"}
