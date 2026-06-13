#!/usr/bin/env python3
import argparse
import json
import os
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class RunResult:
    ok: bool
    elapsed_sec: float
    stdout: str
    stderr: str
    returncode: int


def run_once(script_path: str, action: str, audio_file: Optional[str], timeout_sec: float) -> RunResult:
    runner = (
        "import importlib.util,sys;"
        "p=sys.argv[1];a=sys.argv[2];f=sys.argv[3] if len(sys.argv)>3 and sys.argv[3] else None;"
        "spec=importlib.util.spec_from_file_location('vc_mod', p);"
        "m=importlib.util.module_from_spec(spec);"
        "spec.loader.exec_module(m);"
        "out=m.main(a, f);"
        "print(out)"
    )
    cmd = [sys.executable, "-c", runner, script_path, action, audio_file or ""]
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
        elapsed = time.perf_counter() - t0
        return RunResult(
            ok=(proc.returncode == 0),
            elapsed_sec=elapsed,
            stdout=proc.stdout.strip(),
            stderr=proc.stderr.strip(),
            returncode=proc.returncode,
        )
    except subprocess.TimeoutExpired as e:
        elapsed = time.perf_counter() - t0
        return RunResult(
            ok=False,
            elapsed_sec=elapsed,
            stdout=(e.stdout or "").strip() if e.stdout else "",
            stderr=f"Timed out after {timeout_sec:.1f}s",
            returncode=124,
        )


def summarize(label: str, results: List[RunResult]) -> dict:
    ok_runs = [r for r in results if r.ok]
    all_times = [r.elapsed_sec for r in results]
    summary = {
        "label": label,
        "runs_total": len(results),
        "runs_ok": len(ok_runs),
        "runs_failed": len(results) - len(ok_runs),
        "min_sec": min(all_times) if all_times else None,
        "max_sec": max(all_times) if all_times else None,
        "avg_sec": statistics.mean(all_times) if all_times else None,
        "median_sec": statistics.median(all_times) if all_times else None,
        "last_stdout": results[-1].stdout if results else "",
        "last_stderr": results[-1].stderr if results else "",
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare response time of vc.py vs deprecated/vc_old.py"
    )
    parser.add_argument("--runs", type=int, default=5, help="Runs per script (default: 5)")
    parser.add_argument(
        "--action",
        default="transcribe_file",
        help="Action passed to main(action, audio_file). Default: transcribe_file",
    )
    parser.add_argument(
        "--audio-file",
        default=None,
        help="Audio file used when action=transcribe_file",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="Per-run timeout seconds (default: 60)",
    )
    parser.add_argument(
        "--current",
        default=os.path.join("plugins", "vc.py"),
        help="Path to current vc script",
    )
    parser.add_argument(
        "--old",
        default=os.path.join("deprecated", "vc_old.py"),
        help="Path to old vc script",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON summary only",
    )
    args = parser.parse_args()

    base = os.path.dirname(os.path.abspath(__file__))
    current_path = os.path.abspath(os.path.join(base, args.current))
    old_path = os.path.abspath(os.path.join(base, args.old))

    targets = [
        ("current", current_path),
        ("old", old_path),
    ]

    output = {
        "config": {
            "runs": args.runs,
            "action": args.action,
            "audio_file": args.audio_file,
            "timeout_sec": args.timeout,
            "python": sys.executable,
        },
        "results": [],
    }

    for label, path in targets:
        if not os.path.exists(path):
            output["results"].append(
                {
                    "label": label,
                    "path": path,
                    "skipped": True,
                    "reason": "file_not_found",
                }
            )
            continue

        runs: List[RunResult] = []
        for _ in range(args.runs):
            runs.append(run_once(path, args.action, args.audio_file, args.timeout))
        summary = summarize(label, runs)
        summary["path"] = path
        summary["skipped"] = False
        output["results"].append(summary)

    if args.json:
        print(json.dumps(output, indent=2))
        return 0

    print("VC Response Time Benchmark")
    print(f"action={args.action} runs={args.runs} timeout={args.timeout}s")
    if args.audio_file:
        print(f"audio_file={args.audio_file}")
    print("")

    for item in output["results"]:
        print(f"[{item['label']}] {item['path']}")
        if item.get("skipped"):
            print(f"  skipped: {item.get('reason')}")
            print("")
            continue
        print(
            "  ok={runs_ok}/{runs_total} failed={runs_failed} "
            "avg={avg_sec:.3f}s median={median_sec:.3f}s min={min_sec:.3f}s max={max_sec:.3f}s".format(
                **item
            )
        )
        if item.get("last_stderr"):
            print(f"  last stderr: {item['last_stderr']}")
        if item.get("last_stdout"):
            print(f"  last stdout: {item['last_stdout']}")
        print("")

    valid = [r for r in output["results"] if not r.get("skipped")]
    if len(valid) == 2 and valid[0]["avg_sec"] and valid[1]["avg_sec"]:
        a, b = valid[0], valid[1]
        faster = a if a["avg_sec"] < b["avg_sec"] else b
        slower = b if faster is a else a
        ratio = slower["avg_sec"] / faster["avg_sec"] if faster["avg_sec"] > 0 else float("inf")
        print(
            f"Faster on average: {faster['label']} ({faster['avg_sec']:.3f}s) "
            f"vs {slower['label']} ({slower['avg_sec']:.3f}s), ~{ratio:.2f}x"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
