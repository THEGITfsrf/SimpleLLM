from typing import Any
import psutil
import os

description = "Generates a monitor hook file compatible with HookHandler/Engine. The hook registers on 'tick', reads the metric itself, and returns {to_llm, payload}."

args = {
    "target": {
        "type": "string",
        "description": "cpu, ram, gpu"
    },
    "metric": {
        "type": "string",
        "description": "usage or temp"
    },
    "message": {
        "type": "string",
        "description": "Alert message with {value} and {threshold}"
    },
    "threshold": {
        "type": "number",
        "description": "Trigger threshold"
    }
}

required = ["target", "metric", "message"]

# ── SAFE CONFIG ─────────────────────────────────────────────

_DEFAULTS = {
    ("cpu", "usage"): 85,
    ("ram", "usage"): 90,
    ("gpu", "usage"): 85,
    ("gpu", "temp"): 85,
    ("cpu", "temp"): 80,
}

_CLAMP = {
    ("cpu", "usage"): (50, 99),
    ("ram", "usage"): (50, 99),
    ("gpu", "usage"): (50, 99),
    ("gpu", "temp"): (50, 110),
    ("cpu", "temp"): (50, 110),
}

_READERS = {
    ("cpu", "usage"): "psutil.cpu_percent(interval=None)",
    ("ram", "usage"): "psutil.virtual_memory().percent",
    ("gpu", "usage"): "_gpu_usage()",
    ("gpu", "temp"): "_gpu_temp()",
    ("cpu", "temp"): "_cpu_temp()",
}

_HELPERS = {
    "_gpu_usage": """
def _gpu_usage():
    try:
        import subprocess
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
            text=True
        )
        return float(out.strip().splitlines()[0])
    except:
        return None
""",
    "_gpu_temp": """
def _gpu_temp():
    try:
        import subprocess
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"],
            text=True
        )
        return float(out.strip().splitlines()[0])
    except:
        return None
""",
    "_cpu_temp": """
def _cpu_temp():
    try:
        temps = psutil.sensors_temperatures()
        for key in ("coretemp", "k10temp", "cpu_thermal"):
            if key in temps:
                return temps[key][0].current
        return None
    except:
        return None
"""
}

_VALID_TARGETS = {"cpu", "ram", "gpu"}
_VALID_METRICS = {"usage", "temp"}


def main(target: str, metric: str, message: str, threshold: float | None = None) -> str:
    target = target.lower().strip()
    metric = metric.lower().strip()

    if target not in _VALID_TARGETS:
        return f"Invalid target: {target}"
    if metric not in _VALID_METRICS:
        return f"Invalid metric: {metric}"

    key = (target, metric)

    if key not in _DEFAULTS:
        return f"Unsupported combo: {key}"

    default = _DEFAULTS[key]
    lo, hi = _CLAMP[key]

    final_threshold = default if threshold is None else int(max(lo, min(hi, float(threshold))))

    reader = _READERS[key]
    hook_name = f"monitor_{target}_{metric}"
    safe_msg = message.replace('"', '\\"')

    needed_helpers = "\n\n".join(
        body for name, body in _HELPERS.items() if name in reader
    )

    hook_code = f'''
from typing import Any
import psutil

{needed_helpers}

def register(bus):
    THRESHOLD = {final_threshold}

    @bus.on("tick")
    def {hook_name}(data: Any):
        value = {reader}

        print(f"[HOOK DEBUG] {hook_name} value={{value}} threshold={{THRESHOLD}}")

        if value is None:
            print("[HOOK] value is None")
            return {{"to_llm": False}}

        if value >= THRESHOLD:
            print("[HOOK TRIGGERED] {hook_name}")

            payload = (
                "{safe_msg}"
                .replace("{{value}}", str(round(value, 1)))
                .replace("{{threshold}}", str(THRESHOLD))
            )

            return {{
                "to_llm": True,
                "payload": payload
            }}

        return {{"to_llm": False}}
'''

    output_path = os.path.join("hooks", f"{hook_name}.py")
    os.makedirs("hooks", exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(hook_code)

    return f"Hook written to {output_path}\n\n{hook_code}"