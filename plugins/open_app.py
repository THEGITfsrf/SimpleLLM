import os
import json
import subprocess

description = "List openable desktop apps and open one by name."
args = {
    "action": {"type": "string", "description": "list | open"},
    "name": {"type": "string", "description": "App name to open when action=open"},
}
required = ["action"]


def _start_menu_dirs():
    dirs = []
    appdata = os.environ.get("APPDATA")
    program_data = os.environ.get("ProgramData")
    if appdata:
        dirs.append(os.path.join(appdata, "Microsoft", "Windows", "Start Menu", "Programs"))
    if program_data:
        dirs.append(os.path.join(program_data, "Microsoft", "Windows", "Start Menu", "Programs"))
    return [d for d in dirs if os.path.isdir(d)]


def _discover_start_menu_apps():
    found = {}
    for base in _start_menu_dirs():
        for root, _dirs, files in os.walk(base):
            for f in files:
                if not f.lower().endswith(".lnk"):
                    continue
                full = os.path.join(root, f)
                name = os.path.splitext(f)[0].strip()
                if not name:
                    continue
                key = name.lower()
                if key not in found:
                    found[key] = {"name": name, "type": "lnk", "target": full}
    return found


def _builtin_apps():
    windir = os.environ.get("WINDIR", r"C:\Windows")
    system32 = os.path.join(windir, "System32")
    return {
        "notepad": {"name": "Notepad", "type": "exe", "target": os.path.join(system32, "notepad.exe")},
        "calculator": {"name": "Calculator", "type": "exe", "target": os.path.join(system32, "calc.exe")},
        "paint": {"name": "Paint", "type": "exe", "target": os.path.join(system32, "mspaint.exe")},
        "command prompt": {"name": "Command Prompt", "type": "exe", "target": os.path.join(system32, "cmd.exe")},
        "powershell": {"name": "PowerShell", "type": "exe", "target": os.path.join(system32, "WindowsPowerShell", "v1.0", "powershell.exe")},
    }


def _catalog():
    apps = _discover_start_menu_apps()
    for k, v in _builtin_apps().items():
        if k not in apps:
            apps[k] = v
    return apps


def _list_apps():
    apps = _catalog()
    names = sorted({v["name"] for v in apps.values()}, key=lambda s: s.lower())
    return {"status": "ok", "count": len(names), "apps": names}


def _pick_app(name: str, apps: dict):
    query = (name or "").strip().lower()
    if not query:
        return None
    if query in apps:
        return apps[query]

    for k, v in apps.items():
        if query == v["name"].strip().lower():
            return v

    contains = [v for _k, v in apps.items() if query in v["name"].lower()]
    if len(contains) == 1:
        return contains[0]
    return contains


def _open_app(name: str):
    apps = _catalog()
    pick = _pick_app(name, apps)
    if pick is None:
        return {"status": "error", "message": f"No app matched '{name}'."}
    if isinstance(pick, list):
        choices = sorted({x["name"] for x in pick}, key=lambda s: s.lower())[:15]
        return {
            "status": "ambiguous",
            "message": f"Multiple apps matched '{name}'. Be more specific.",
            "matches": choices,
        }

    target = pick["target"]
    try:
        if pick["type"] == "lnk":
            os.startfile(target)
        else:
            subprocess.Popen([target], shell=False)
        return {"status": "ok", "message": f"Opened {pick['name']}.", "app": pick["name"]}
    except Exception as e:
        return {"status": "error", "message": f"Failed to open {pick['name']}: {e}"}


def main(action: str, name: str = ""):
    act = (action or "").strip().lower()
    if act == "list":
        return json.dumps(_list_apps(), ensure_ascii=False)
    if act == "open":
        return json.dumps(_open_app(name), ensure_ascii=False)
    return json.dumps({"status": "error", "message": "Unknown action. Use list or open."}, ensure_ascii=False)

