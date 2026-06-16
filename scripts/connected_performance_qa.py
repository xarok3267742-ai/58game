#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_APK = ROOT / "app/build/outputs/apk/debug/app-debug.apk"
DEFAULT_PACKAGE = "com.shawarma58.game.debug"
DEFAULT_ACTIVITY = "com.shawarma58.game.MainActivity"
REPORT_ROOT = ROOT / "build/performance_connected"
LATEST_MD = ROOT / "build/reports/connected_performance.md"
LATEST_JSON = ROOT / "build/reports/connected_performance.json"

MAX_TOTAL_PSS_KB = 260_000
MAX_JANKY_PERCENT = 45.0
MAX_FRAME_90TH_MS = 90.0


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"{' '.join(command)} failed:\n{result.stdout}")
    return result


def adb(serial: str, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run(["adb", "-s", serial, *args], check=check)


def is_device_ready(serial: str) -> bool:
    state = adb(serial, "get-state", check=False).stdout.strip()
    if state != "device":
        return False
    boot_completed = adb(serial, "shell", "getprop", "sys.boot_completed", check=False).stdout.strip()
    return boot_completed == "1"


def wait_for_device(serial: str, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    last_state = ""
    while time.monotonic() < deadline:
        state_result = adb(serial, "get-state", check=False)
        last_state = state_result.stdout.strip()
        if last_state == "device":
            boot_completed = adb(serial, "shell", "getprop", "sys.boot_completed", check=False).stdout.strip()
            if boot_completed == "1":
                return
            last_state = f"device boot_completed={boot_completed!r}"
        time.sleep(1.0)
    raise RuntimeError(f"Device {serial} was not ready within {timeout:.0f}s; last state: {last_state!r}")


def install_apk_with_retry(serial: str, apk: Path, device_timeout: float) -> None:
    wait_for_device(serial, device_timeout)
    first = adb(serial, "install", "-r", str(apk), check=False)
    if first.returncode == 0:
        return
    output = first.stdout.lower()
    transient = any(
        marker in output
        for marker in [
            "device not found",
            "device offline",
            "no devices/emulators found",
            "daemon not running",
        ]
    )
    if not transient:
        raise RuntimeError(f"adb -s {serial} install -r {apk} failed:\n{first.stdout}")
    wait_for_device(serial, device_timeout)
    second = adb(serial, "install", "-r", str(apk), check=False)
    if second.returncode != 0:
        raise RuntimeError(
            f"adb install failed after retry; first output:\n{first.stdout}\nsecond output:\n{second.stdout}",
        )


def force_stop_other_third_party_apps(serial: str, package: str) -> list[str]:
    result = adb(serial, "shell", "pm", "list", "packages", "-3", check=False)
    stopped: list[str] = []
    for line in result.stdout.splitlines():
        if not line.startswith("package:"):
            continue
        candidate = line.removeprefix("package:").strip()
        if not candidate or candidate == package:
            continue
        adb(serial, "shell", "am", "force-stop", candidate, check=False)
        stopped.append(candidate)
    return stopped


def unique_preserving_order(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def pick_serial(explicit: str | None) -> str:
    if explicit:
        return explicit
    result = run(["adb", "devices"], check=False)
    devices = [
        line.split()[0]
        for line in result.stdout.splitlines()
        if line.startswith("emulator-") and "\tdevice" in line
    ]
    if not devices:
        raise RuntimeError("No booted emulator found. Pass --serial for a connected device.")
    return devices[0]


def launch_and_wait_for_process(serial: str, package: str, activity: str, timeout: float = 10.0) -> None:
    adb(serial, "shell", "am", "start", "-n", f"{package}/{activity}", check=True)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        pid = adb(serial, "shell", "pidof", package, check=False).stdout.strip()
        if pid:
            return
        time.sleep(0.4)
    raise RuntimeError(f"{package} process did not start")


def parse_total_pss_kb(meminfo: str) -> int | None:
    for pattern in [
        r"TOTAL\s+(\d+)\s+",
        r"TOTAL PSS:\s+(\d+)",
    ]:
        match = re.search(pattern, meminfo)
        if match:
            return int(match.group(1))
    return None


def parse_gfxinfo(gfxinfo: str) -> dict[str, float | int | None]:
    total_frames = None
    janky_frames = None
    janky_percent = None
    percentile_90 = None
    total_match = re.search(r"Total frames rendered:\s+(\d+)", gfxinfo)
    if total_match:
        total_frames = int(total_match.group(1))
    janky_match = re.search(r"Janky frames:\s+(\d+)\s+\(([0-9.]+)%\)", gfxinfo)
    if janky_match:
        janky_frames = int(janky_match.group(1))
        janky_percent = float(janky_match.group(2))
    percentile_match = re.search(r"90th percentile:\s+([0-9.]+)ms", gfxinfo)
    if percentile_match:
        percentile_90 = float(percentile_match.group(1))
    return {
        "totalFrames": total_frames,
        "jankyFrames": janky_frames,
        "jankyPercent": janky_percent,
        "frame90thMs": percentile_90,
    }


def check_metric(name: str, actual: float | int | None, limit: float | int, unit: str) -> Check:
    if actual is None:
        return Check(name, "WARN", "metric unavailable in dumpsys output")
    if actual > limit:
        return Check(name, "FAIL", f"{actual}{unit} exceeds {limit}{unit}")
    return Check(name, "PASS", f"{actual}{unit} <= {limit}{unit}")


def check_frame_metric(
    name: str,
    actual: float | int | None,
    limit: float | int,
    unit: str,
    total_frames: float | int | None,
) -> Check:
    if actual is None:
        return Check(name, "WARN", "metric unavailable in dumpsys output")
    if total_frames is None or total_frames < 30:
        return Check(name, "WARN", f"{actual}{unit}; only {total_frames} frames sampled on emulator")
    if actual > limit:
        return Check(name, "WARN", f"{actual}{unit} exceeds diagnostic threshold {limit}{unit} on emulator")
    return Check(name, "PASS", f"{actual}{unit} <= {limit}{unit}")


def write_reports(
    out: Path,
    serial: str,
    flow_evidence: str,
    checks: list[Check],
    metrics: dict[str, object],
    flow_output: str,
) -> None:
    status = "PASS"
    if any(check.status == "FAIL" for check in checks):
        status = "FAIL"
    elif any(check.status == "WARN" for check in checks):
        status = "PASS_WITH_WARNINGS"
    payload = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "serial": serial,
        "package": DEFAULT_PACKAGE,
        "flowEvidence": flow_evidence,
        "checks": [check.__dict__ for check in checks],
        "metrics": metrics,
        "artifacts": {
            "meminfo": relative(out / "meminfo.txt"),
            "gfxinfo": relative(out / "gfxinfo.txt"),
            "gfxinfoFramestats": relative(out / "gfxinfo-framestats.txt"),
            "logcat": relative(out / "logcat.txt"),
            "crashLog": relative(out / "logcat_crash.txt"),
        },
    }
    out.mkdir(parents=True, exist_ok=True)
    report_json = out / "summary.json"
    report_md = out / "summary.md"
    report_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Connected Performance QA",
        "",
        f"Generated: {payload['generatedAt']}",
        f"Serial: `{serial}`",
        f"Package: `{DEFAULT_PACKAGE}`",
        f"Flow evidence: `{flow_evidence}`",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for check in checks:
        lines.append(f"| {check.name} | {check.status} | {check.detail} |")
    lines.extend(
        [
            "",
            "## Metrics",
            f"- Total PSS: `{metrics.get('totalPssKb')}` KB",
            f"- Total frames: `{metrics.get('totalFrames')}`",
            f"- Janky frames: `{metrics.get('jankyFrames')}`",
            f"- Janky percent: `{metrics.get('jankyPercent')}`",
            f"- 90th percentile frame: `{metrics.get('frame90thMs')}` ms",
            "",
            "## Artifacts",
        ]
    )
    for label, path in payload["artifacts"].items():
        lines.append(f"- {label}: `{path}`")
    lines.extend(["", "## Flow Command Tail", "", "```text", "\n".join(flow_output.splitlines()[-40:]), "```"])
    report_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    shutil.copy2(report_json, LATEST_JSON)
    shutil.copy2(report_md, LATEST_MD)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--serial", help="adb serial. Defaults to first booted emulator.")
    parser.add_argument("--apk", default=str(DEFAULT_APK), help="debug APK path")
    parser.add_argument(
        "--out",
        default=f"build/performance_connected/{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        help="output directory under project root",
    )
    parser.add_argument("--extended", action="store_true", help="run extended smoke instead of basic flow")
    parser.add_argument(
        "--driver",
        choices=["instrumentation", "adb-smoke"],
        default="instrumentation",
        help="flow driver used before collecting meminfo/gfxinfo",
    )
    parser.add_argument(
        "--no-force-stop-others",
        action="store_true",
        help="do not force-stop other third-party packages on shared emulators",
    )
    parser.add_argument(
        "--device-timeout",
        type=float,
        default=45.0,
        help="seconds to wait for the target serial to be online and boot-completed before install/retry",
    )
    args = parser.parse_args()

    adb_path = shutil.which("adb")
    if adb_path is None:
        raise SystemExit("adb not found")
    serial = pick_serial(args.serial)
    apk = Path(args.apk)
    if not apk.is_absolute():
        apk = ROOT / apk
    if not apk.exists():
        raise SystemExit(f"missing APK: {apk}")

    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    flow_dir = out / args.driver

    install_apk_with_retry(serial, apk, args.device_timeout)
    stopped_packages = (
        force_stop_other_third_party_apps(serial, DEFAULT_PACKAGE)
        if not args.no_force_stop_others
        else []
    )
    adb(serial, "shell", "pm", "clear", DEFAULT_PACKAGE)
    if not args.no_force_stop_others:
        force_stop_other_third_party_apps(serial, DEFAULT_PACKAGE)
    adb(serial, "shell", "logcat", "-c", check=False)
    adb(serial, "shell", "dumpsys", "gfxinfo", DEFAULT_PACKAGE, "reset", check=False)

    if args.driver == "instrumentation":
        flow_command = ["python3", "scripts/instrumentation_smoke_qa.py", "--serial", serial, "--require-device"]
        if args.no_force_stop_others:
            flow_command.append("--no-force-stop-others")
        flow = run(flow_command)
        flow_dir.mkdir(parents=True, exist_ok=True)
        for source in [
            ROOT / "build/reports/instrumentation_smoke.md",
            ROOT / "build/reports/instrumentation_smoke.json",
        ]:
            if source.exists():
                shutil.copy2(source, flow_dir / source.name)
        flow_evidence = relative(flow_dir)
    else:
        flow_command = [
            "python3",
            "scripts/android_smoke_qa.py",
            "--serial",
            serial,
            "--skip-install",
            "--out",
            relative(flow_dir),
        ]
        if args.extended:
            flow_command.append("--extended")
        if args.no_force_stop_others:
            flow_command.append("--no-force-stop-others")
        flow = run(flow_command)
        flow_evidence = relative(flow_dir)

    if not args.no_force_stop_others:
        stopped_packages.extend(force_stop_other_third_party_apps(serial, DEFAULT_PACKAGE))
    adb(serial, "shell", "dumpsys", "gfxinfo", DEFAULT_PACKAGE, "reset", check=False)
    launch_and_wait_for_process(serial, DEFAULT_PACKAGE, DEFAULT_ACTIVITY)
    time.sleep(2.0)

    meminfo = adb(serial, "shell", "dumpsys", "meminfo", DEFAULT_PACKAGE, check=False).stdout
    gfxinfo = adb(serial, "shell", "dumpsys", "gfxinfo", DEFAULT_PACKAGE, check=False).stdout
    framestats = adb(serial, "shell", "dumpsys", "gfxinfo", DEFAULT_PACKAGE, "framestats", check=False).stdout
    logcat = adb(serial, "shell", "logcat", "-d", check=False).stdout
    crash = adb(serial, "shell", "logcat", "-b", "crash", "-d", check=False).stdout

    (out / "meminfo.txt").write_text(meminfo, encoding="utf-8", errors="replace")
    (out / "gfxinfo.txt").write_text(gfxinfo, encoding="utf-8", errors="replace")
    (out / "gfxinfo-framestats.txt").write_text(framestats, encoding="utf-8", errors="replace")
    (out / "logcat.txt").write_text(logcat, encoding="utf-8", errors="replace")
    (out / "logcat_crash.txt").write_text(crash, encoding="utf-8", errors="replace")

    gfx_metrics = parse_gfxinfo(gfxinfo)
    total_pss = parse_total_pss_kb(meminfo)
    metrics: dict[str, object] = {
        "totalPssKb": total_pss,
        "stoppedThirdPartyPackages": unique_preserving_order(stopped_packages),
        **gfx_metrics,
    }
    checks = [
        check_metric("Total PSS budget", total_pss, MAX_TOTAL_PSS_KB, " KB"),
        check_frame_metric(
            "Janky frame diagnostic",
            gfx_metrics["jankyPercent"],
            MAX_JANKY_PERCENT,
            "%",
            gfx_metrics["totalFrames"],
        ),
        check_frame_metric(
            "90th percentile frame diagnostic",
            gfx_metrics["frame90thMs"],
            MAX_FRAME_90TH_MS,
            " ms",
            gfx_metrics["totalFrames"],
        ),
    ]
    if DEFAULT_PACKAGE in crash:
        checks.append(Check("Crash buffer", "FAIL", "crash buffer contains app package"))
    else:
        checks.append(Check("Crash buffer", "PASS", "no app crash in crash buffer"))

    write_reports(out, serial, flow_evidence, checks, metrics, flow.stdout)

    failures = [check for check in checks if check.status == "FAIL"]
    if failures:
        print("Connected performance QA failed")
        for check in failures:
            print(f"- {check.name}: {check.detail}")
        print(f"Evidence: {relative(out)}")
        raise SystemExit(1)

    print(f"Connected performance QA PASS: {relative(out)}")


if __name__ == "__main__":
    main()
