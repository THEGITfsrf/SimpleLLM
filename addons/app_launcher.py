import os
import subprocess
import re
import json

description = "Open desktop apps by name and list openable apps."
args = {
    "action": {"type": "string", "description": "open | list"},
    "target": {"type": "string", "description": "App name, app key, or URL (for action=open)"},
    "argument": {"type": "string", "description": "Optional argument passed to app"},
}
required = ["action"]

ALLOWED_APPS = {
    "notepad": {"name": "Notepad", "cmd": ["notepad.exe"]},
    "calculator": {"name": "Calculator", "cmd": ["calc.exe"]},
    "paint": {"name": "Paint", "cmd": ["mspaint.exe"]},
    "explorer": {"name": "Explorer", "cmd": ["explorer.exe"]},
    "cmd": {"name": "Command Prompt", "cmd": ["cmd.exe"]},
    "powershell": {"name": "PowerShell", "cmd": ["powershell.exe"]},
}


def _start_menu_dirs():
    dirs = []
    appdata = os.environ.get("APPDATA")
    program_data = os.environ.get("ProgramData")
    if appdata:
        dirs.append(os.path.join(appdata, "Microsoft", "Windows", "Start Menu", "Programs"))
    if program_data:
        dirs.append(os.path.join(program_data, "Microsoft", "Windows", "Start Menu", "Programs"))
    return [d for d in dirs if os.path.isdir(d)]


def _desktop_dirs():
    dirs = []
    user_profile = os.environ.get("USERPROFILE")
    public_dir = os.environ.get("PUBLIC")
    one_drive = os.environ.get("OneDrive")
    if user_profile:
        dirs.append(os.path.join(user_profile, "Desktop"))
    if public_dir:
        dirs.append(os.path.join(public_dir, "Desktop"))
    if one_drive:
        dirs.append(os.path.join(one_drive, "Desktop"))
    return [d for d in dirs if os.path.isdir(d)]


def _start_menu_apps():
    found = {}
    for base in _start_menu_dirs():
        for root, _dirs, files in os.walk(base):
            for file_name in files:
                if not file_name.lower().endswith(".lnk"):
                    continue
                full = os.path.join(root, file_name)
                name = os.path.splitext(file_name)[0].strip()
                if not name:
                    continue
                key = name.lower()
                if key not in found:
                    found[key] = {"name": name, "lnk": full}
    return found


def _desktop_shortcuts():
    found = {}
    for base in _desktop_dirs():
        for root, _dirs, files in os.walk(base):
            for file_name in files:
                lower = file_name.lower()
                if not (lower.endswith(".lnk") or lower.endswith(".url")):
                    continue
                full = os.path.join(root, file_name)
                name = os.path.splitext(file_name)[0].strip()
                if not name:
                    continue
                key = name.lower()
                if key not in found:
                    found[key] = {"name": name, "lnk": full}
    return found


def _winget_apps():
    meta = {"available": False, "returncode": None, "stderr": ""}
    cmd = ["winget", "list", "--accept-source-agreements", "--disable-interactivity"]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            encoding="utf-8",
            errors="replace",
        )
    except Exception:
        return [], meta

    meta["available"] = True
    meta["returncode"] = proc.returncode
    meta["stderr"] = (proc.stderr or "").strip()[:500]
    if proc.returncode != 0:
        return [], meta

    lines = (proc.stdout or "").splitlines()
    if not lines:
        return [], meta

    names = []
    header_seen = False
    for raw in lines:
        line = raw.rstrip("\r\n")
        if not line.strip():
            continue
        if not header_seen:
            if "Name" in line and "Id" in line:
                header_seen = True
            continue
        if re.match(r"^\s*-{3,}\s*$", line):
            continue

        # winget columns are usually padded with 2+ spaces: Name  Id  Version ...
        parts = re.split(r"\s{2,}", line.strip())
        if not parts:
            continue
        name = parts[0].strip()
        if name:
            names.append(name)

    return sorted(set(names), key=str.lower), meta


def _startapps_catalog():
    cmd = (
        "Get-StartApps | "
        "Select-Object Name,AppID | "
        "ConvertTo-Json -Depth 3"
    )
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", cmd],
            capture_output=True,
            text=True,
            timeout=20,
            encoding="utf-8",
            errors="replace",
        )
    except Exception:
        return {}

    if proc.returncode != 0:
        return {}

    raw = (proc.stdout or "").strip()
    if not raw:
        return {}

    try:
        data = json.loads(raw)
    except Exception:
        return {}

    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        return {}

    found = {}
    for item in data:
        if not isinstance(item, dict):
            continue
        name = str(item.get("Name") or "").strip()
        appid = str(item.get("AppID") or "").strip()
        if not name or not appid:
            continue
        key = name.lower()
        if key not in found:
            found[key] = {"name": name, "appid": appid}
    return found


def _list_apps():
    launchable = sorted({v["name"] for v in ALLOWED_APPS.values()}, key=str.lower)
    discovered = _start_menu_apps()
    discovered_names = sorted({v["name"] for v in discovered.values()}, key=str.lower)
    desktop = _desktop_shortcuts()
    desktop_names = sorted({v["name"] for v in desktop.values()}, key=str.lower)
    installed_names, winget_meta = _winget_apps()
    startapps = _startapps_catalog()
    startapps_names = sorted({v["name"] for v in startapps.values()}, key=str.lower)

    combined = sorted(
        set(launchable)
        | set(discovered_names)
        | set(desktop_names)
        | set(installed_names)
        | set(startapps_names),
        key=str.lower
    )
    return {
        "status": "ok",
        "apps": combined,
        "count": len(combined),
    }


def _resolve_app(target: str):
    t = (target or "").strip()
    q = t.lower()
    if q in ALLOWED_APPS:
        return ("allowed", ALLOWED_APPS[q])

    by_name = [v for v in ALLOWED_APPS.values() if v["name"].lower() == q]
    if by_name:
        return ("allowed", by_name[0])

    start_menu = _start_menu_apps()
    desktop = _desktop_shortcuts()
    startapps = _startapps_catalog()

    # Exact key match priority: desktop > start menu > startapps
    if q in desktop:
        return ("lnk", desktop[q])
    if q in start_menu:
        return ("lnk", start_menu[q])
    if q in startapps:
        return ("startapp", startapps[q])

    # Name equality priority: desktop > start menu > startapps
    desktop_eq = [v for v in desktop.values() if v["name"].lower() == q]
    if desktop_eq:
        return ("lnk", desktop_eq[0])
    start_menu_eq = [v for v in start_menu.values() if v["name"].lower() == q]
    if start_menu_eq:
        return ("lnk", start_menu_eq[0])
    startapps_eq = [v for v in startapps.values() if v["name"].lower() == q]
    if startapps_eq:
        return ("startapp", startapps_eq[0])

    # Contains match from all sources; prefer desktop when unique there.
    desktop_contains = [v for v in desktop.values() if q and q in v["name"].lower()]
    if len(desktop_contains) == 1:
        return ("lnk", desktop_contains[0])
    start_menu_contains = [v for v in start_menu.values() if q and q in v["name"].lower()]
    if len(start_menu_contains) == 1 and not desktop_contains:
        return ("lnk", start_menu_contains[0])
    startapps_contains = [v for v in startapps.values() if q and q in v["name"].lower()]
    if len(startapps_contains) == 1 and not desktop_contains and not start_menu_contains:
        return ("startapp", startapps_contains[0])

    combined_matches = sorted(
        {x["name"] for x in (desktop_contains + start_menu_contains + startapps_contains)},
        key=str.lower
    )
    if combined_matches:
        return ("ambiguous", combined_matches[:20])

    return (None, None)


def main(action, target=None, argument=None):
    try:
        act = (action or "").strip().lower()

        if act == "list":
            return _list_apps()
        if act != "open":
            return {"error": "Invalid action. Use open or list."}

        t = (target or "").strip()
        if not t:
            return {"error": "target is required when action=open"}

        lower = t.lower()
        if lower.startswith("http://") or lower.startswith("https://"):
            subprocess.Popen(["powershell", "-Command", f"Start-Process '{t}'"])
            return {"target": t, "status": "opened_url"}

        kind, payload = _resolve_app(t)
        if kind == "allowed":
            cmd = list(payload["cmd"])
            if argument:
                cmd.append(str(argument))
            subprocess.Popen(cmd)
            return {"target": payload["name"], "status": "launched"}
        if kind == "lnk":
            os.startfile(payload["lnk"])
            return {"target": payload["name"], "status": "launched"}
        if kind == "startapp":
            # Launch UWP/Store apps and other entries exposed by Get-StartApps.
            os.startfile(f"shell:AppsFolder\\{payload['appid']}")
            return {"target": payload["name"], "status": "launched"}
        if kind == "ambiguous":
            return {
                "error": "Multiple apps matched target. Be more specific.",
                "matches": payload,
            }

        return {
            "error": "No app matched target. Use action=list to see available apps."
        }
    except Exception as e:
        return {"error": f"app_launcher tool failed: {e}"}
