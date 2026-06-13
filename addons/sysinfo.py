description = "Returns detailed system information using PowerShell (no WMIC dependency)"

args = {}
required = []


def ps(command):
    import subprocess

    return subprocess.check_output(
        ["powershell", "-Command", command],
        text=True,
        stderr=subprocess.DEVNULL
    ).strip()


def bytes_to_gb(value):
    return round(int(value) / (1024 ** 3), 2)


def safe_ps(command, default="Unknown"):
    try:
        result = ps(command)
        return result if result else default
    except:
        return default


def main():
    import platform
    import psutil
    import sys
    import socket
    import uuid
    import time

    info = {}

    # =========================================================
    # OS
    # =========================================================
    info["os"] = platform.system()
    info["os_version"] = platform.version()
    info["os_release"] = platform.release()
    info["architecture"] = platform.machine()
    info["python_version"] = sys.version.split()[0]
    info["hostname"] = socket.gethostname()

    try:
        info["local_ip"] = socket.gethostbyname(socket.gethostname())
    except:
        info["local_ip"] = "Unknown"

    # =========================================================
    # CPU
    # =========================================================
    info["cpu_model"] = safe_ps(
        "(Get-CimInstance Win32_Processor).Name"
    )

    info["cpu_logical_cores"] = psutil.cpu_count(logical=True)
    info["cpu_physical_cores"] = psutil.cpu_count(logical=False)
    info["cpu_usage_percent"] = psutil.cpu_percent(interval=0.5)

    try:
        freq = psutil.cpu_freq()

        if freq:
            info["cpu_current_mhz"] = round(freq.current, 2)
            info["cpu_max_mhz"] = round(freq.max, 2)

    except:
        pass

    # =========================================================
    # GPU
    # =========================================================
    info["gpus"] = []

    try:
        import subprocess
        import json

        # Try NVIDIA first
        try:
            nvidia_output = subprocess.check_output(
                [
                    "nvidia-smi",
                    "--query-gpu=name,memory.total",
                    "--format=csv,noheader,nounits"
                ],
                text=True
            ).strip()

            for line in nvidia_output.splitlines():
                name, memory = line.split(",")

                info["gpus"].append({
                    "name": name.strip(),
                    "vram_gb": round(int(memory.strip()) / 1024, 2)
                })

        except:
            # Fallback to Windows
            gpu_json = ps("""
            Get-CimInstance Win32_VideoController |
            Select-Object Name,
            @{Name='AdapterRAMGB';Expression={[math]::Round($_.AdapterRAM / 1GB, 2)}} |
            ConvertTo-Json
            """)

            gpu_data = json.loads(gpu_json)

            if isinstance(gpu_data, dict):
                gpu_data = [gpu_data]

            for gpu in gpu_data:
                info["gpus"].append({
                    "name": gpu.get("Name", "Unknown"),
                    "vram_gb": gpu.get("AdapterRAMGB", "Unknown")
                })

    except:
        info["gpus"] = "Unknown"
    # =========================================================
    # Motherboard
    # =========================================================
    try:
        mobo_name = safe_ps("(Get-CimInstance Win32_BaseBoard).Product")
        mobo_mfg = safe_ps("(Get-CimInstance Win32_BaseBoard).Manufacturer")

        info["motherboard"] = {
            "manufacturer": mobo_mfg,
            "model": mobo_name
        }

    except:
        info["motherboard"] = "Unknown"

    # =========================================================
    # BIOS
    # =========================================================
    info["bios_version"] = safe_ps(
        "(Get-CimInstance Win32_BIOS).SMBIOSBIOSVersion"
    )

    # =========================================================
    # RAM
    # =========================================================
    ram = psutil.virtual_memory()

    info["ram"] = {
        "total_gb": round(ram.total / (1024 ** 3), 2),
        "used_gb": round(ram.used / (1024 ** 3), 2),
        "available_gb": round(ram.available / (1024 ** 3), 2),
        "percent_used": ram.percent
    }

    # RAM STICKS
    info["ram_sticks"] = []

    try:
        ram_json = ps(
            "Get-CimInstance Win32_PhysicalMemory | "
            "Select-Object Manufacturer,PartNumber,Capacity,Speed,DeviceLocator | "
            "ConvertTo-Json"
        )

        import json
        ram_data = json.loads(ram_json)

        if isinstance(ram_data, dict):
            ram_data = [ram_data]

        for stick in ram_data:
            info["ram_sticks"].append({
                "manufacturer": str(stick.get("Manufacturer", "")).strip(),
                "model": str(stick.get("PartNumber", "")).strip(),
                "slot": stick.get("DeviceLocator", "Unknown"),
                "capacity_gb": round(int(stick.get("Capacity", 0)) / (1024 ** 3), 2),
                "speed_mhz": stick.get("Speed", "Unknown")
            })

    except:
        info["ram_sticks"] = "Unknown"

    # =========================================================
    # STORAGE DRIVES
    # =========================================================
    info["storage_drives"] = []

    try:
        drive_json = ps(
            "Get-CimInstance Win32_DiskDrive | "
            "Select-Object Model,MediaType,Size,InterfaceType,SerialNumber | "
            "ConvertTo-Json"
        )

        import json
        drive_data = json.loads(drive_json)

        if isinstance(drive_data, dict):
            drive_data = [drive_data]

        for drive in drive_data:
            size = drive.get("Size", 0)

            info["storage_drives"].append({
                "model": str(drive.get("Model", "")).strip(),
                "serial": str(drive.get("SerialNumber", "")).strip(),
                "type": drive.get("MediaType", "Unknown"),
                "interface": drive.get("InterfaceType", "Unknown"),
                "size_gb": round(int(size) / (1024 ** 3), 2) if size else 0
            })

    except:
        info["storage_drives"] = "Unknown"

    # =========================================================
    # DISK PARTITIONS
    # =========================================================
    info["disks"] = []

    try:
        seen = set()

        partitions = psutil.disk_partitions(all=False)

        for part in partitions:

            if part.device in seen:
                continue

            seen.add(part.device)

            try:
                usage = psutil.disk_usage(part.mountpoint)

                info["disks"].append({
                    "device": part.device,
                    "mount": part.mountpoint,
                    "filesystem": part.fstype,
                    "total_gb": round(usage.total / (1024 ** 3), 2),
                    "used_gb": round(usage.used / (1024 ** 3), 2),
                    "free_gb": round(usage.free / (1024 ** 3), 2),
                    "percent_used": usage.percent
                })

            except PermissionError:
                continue

    except:
        info["disks"] = "Unknown"

    # =========================================================
    # NETWORK
    # =========================================================
    try:
        mac = ':'.join(
            ('%012X' % uuid.getnode())[i:i + 2]
            for i in range(0, 12, 2)
        )

        info["mac_address"] = mac

    except:
        info["mac_address"] = "Unknown"

    # =========================================================
    # BATTERY
    # =========================================================
    try:
        battery = psutil.sensors_battery()

        if battery:
            info["battery"] = {
                "percent": battery.percent,
                "plugged_in": battery.power_plugged
            }
        else:
            info["battery"] = "No Battery"

    except:
        info["battery"] = "Unknown"

    # =========================================================
    # SWAP
    # =========================================================
    try:
        swap = psutil.swap_memory()

        info["swap"] = {
            "total_gb": round(swap.total / (1024 ** 3), 2),
            "used_gb": round(swap.used / (1024 ** 3), 2),
            "percent_used": swap.percent
        }

    except:
        info["swap"] = "Unknown"

    # =========================================================
    # SYSTEM UPTIME
    # =========================================================
    try:
        uptime_seconds = time.time() - psutil.boot_time()

        info["uptime_hours"] = round(
            uptime_seconds / 3600,
            2
        )

    except:
        info["uptime_hours"] = "Unknown"

    # =========================================================
    # PROCESSES
    # =========================================================
    try:
        info["process_count"] = len(psutil.pids())
    except:
        info["process_count"] = "Unknown"

    # =========================================================
    # MONITORS
    # =========================================================
    try:
        monitors = safe_ps(
            "Get-CimInstance Win32_DesktopMonitor | "
            "Select-Object Name | ConvertTo-Json"
        )

        info["monitors"] = monitors

    except:
        info["monitors"] = "Unknown"

    # =========================================================
    # ANTIVIRUS
    # =========================================================
    try:
        antivirus = safe_ps(
            "Get-CimInstance -Namespace root/SecurityCenter2 "
            "AntivirusProduct | "
            "Select-Object displayName | ConvertTo-Json"
        )

        info["antivirus"] = antivirus

    except:
        info["antivirus"] = "Unknown"

    return info