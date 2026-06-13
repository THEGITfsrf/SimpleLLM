import os
import platform
import subprocess
import psutil

description = "Fetches targeted system metrics (CPU, RAM, GPU, disk, OS) without dumping everything."
args = {
    "metric": {"type": "string", "description": "cpu_usage | ram_used_percent | ram_available_gb | gpu_usage | disk_used_percent | os_info"},
    "disk_path": {"type": "string", "description": "Disk path for disk metric, default C:/"},
}
required = ["metric"]


def _gpu_usage():
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        vals = [int(x.strip()) for x in out.splitlines() if x.strip()]
        if not vals:
            return None
        return {"gpu_usage_percent": vals}
    except Exception:
        return None


def main(metric, disk_path="C:/"):
    try:
        m = (metric or "").strip().lower()

        if m == "cpu_usage":
            return {"metric": m, "value": psutil.cpu_percent(interval=0.5), "unit": "%"}

        if m == "ram_used_percent":
            return {"metric": m, "value": psutil.virtual_memory().percent, "unit": "%"}

        if m == "ram_available_gb":
            gb = round(psutil.virtual_memory().available / (1024 ** 3), 2)
            return {"metric": m, "value": gb, "unit": "GB"}

        if m == "gpu_usage":
            gpu = _gpu_usage()
            if gpu:
                return {"metric": m, **gpu}
            return {"metric": m, "value": "Unavailable (no supported GPU telemetry found)"}

        if m == "disk_used_percent":
            path = disk_path if disk_path else "C:/"
            used = psutil.disk_usage(path).percent
            return {"metric": m, "path": path, "value": used, "unit": "%"}

        if m == "os_info":
            return {
                "metric": m,
                "os": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "arch": platform.machine(),
                "hostname": platform.node(),
                "cpu_count": os.cpu_count(),
            }

        return {"error": "Unknown metric."}
    except Exception as e:
        return {"error": f"sysinfo_specific failed: {e}"}
