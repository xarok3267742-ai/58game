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
REPORT_JSON = ROOT / "build/reports/instrumentation_smoke.json"
REPORT_MD = ROOT / "build/reports/instrumentation_smoke.md"
TARGET_PACKAGE = "com.andrejivliev.shawarma58.debug"
TEST_PACKAGE = "com.andrejivliev.shawarma58.debug.test"
TEST_RUNNER = "androidx.test.runner.AndroidJUnitRunner"
DEBUG_APK = ROOT / "app/build/outputs/apk/debug/app-debug.apk"
ANDROID_TEST_APK = ROOT / "app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk"
BUILD_COMMAND = ["./gradlew", "assembleDebug", "assembleDebugAndroidTest"]
GRADLE_CONNECTED_COMMAND = ["./gradlew", "connectedDebugAndroidTest"]
TRANSIENT_ADB_MARKERS = (
    "device not found",
    "device offline",
    "no devices/emulators found",
    "daemon not running",
    "device still connecting",
)


@dataclass(frozen=True)
class Device:
    serial: str
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


def connected_devices() -> tuple[list[Device], str]:
    if shutil.which("adb") is None:
        return [], "adb not found"
    result = run(["adb", "devices", "-l"], check=False)
    if result.returncode != 0:
        return [], result.stdout.strip()
    devices: list[Device] = []
    for line in result.stdout.splitlines()[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split(maxsplit=2)
        if len(parts) >= 2 and parts[1] == "device":
            devices.append(Device(serial=parts[0], detail=line))
    return devices, result.stdout.strip()


def pick_serial(explicit: str | None, devices: list[Device]) -> str | None:
    if explicit:
        return explicit
    return devices[0].serial if devices else None


def wait_for_device(serial: str, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    last_state = ""
    while time.monotonic() < deadline:
        state_result = adb(serial, "get-state", check=False)
        last_state = (state_result.stdout or "").strip() or (state_result.stderr or "").strip()
        if last_state == "device":
            boot_completed = adb(serial, "shell", "getprop", "sys.boot_completed", check=False).stdout.strip()
            if boot_completed == "1":
                return
            last_state = f"device boot_completed={boot_completed!r}"
        time.sleep(1.0)
    raise RuntimeError(f"Device {serial} was not ready within {timeout:.0f}s; last state: {last_state!r}")


def is_transient_adb_error(output: str) -> bool:
    lowered = output.lower()
    return any(marker in lowered for marker in TRANSIENT_ADB_MARKERS)


def install_apk_with_retry(serial: str, apk: Path, device_timeout: float) -> None:
    wait_for_device(serial, device_timeout)
    first = adb(serial, "install", "-r", str(apk), check=False)
    if first.returncode == 0:
        return
    if not is_transient_adb_error(first.stdout):
        raise RuntimeError(f"adb -s {serial} install -r {apk} failed:\n{first.stdout}")
    wait_for_device(serial, device_timeout)
    second = adb(serial, "install", "-r", str(apk), check=False)
    if second.returncode != 0:
        raise RuntimeError(
            f"adb install failed after retry; first output:\n{first.stdout}\nsecond output:\n{second.stdout}",
        )


def force_stop_other_third_party_apps(serial: str) -> list[str]:
    result = adb(serial, "shell", "pm", "list", "packages", "-3", check=False)
    stopped: list[str] = []
    allowed = {TARGET_PACKAGE, TEST_PACKAGE}
    for line in result.stdout.splitlines():
        if not line.startswith("package:"):
            continue
        package = line.removeprefix("package:").strip()
        if not package or package in allowed:
            continue
        adb(serial, "shell", "am", "force-stop", package, check=False)
        stopped.append(package)
    return stopped


def failed_instrumentation_output(result: subprocess.CompletedProcess[str]) -> bool:
    return (
        result.returncode != 0
        or "FAILURES!!!" in result.stdout
        or re.search(r"FAILURES?=", result.stdout) is not None
        or re.search(r"\bfailures:\s*[1-9]", result.stdout, flags=re.IGNORECASE) is not None
    )


def parse_instrumentation_result(output: str) -> dict[str, int | None]:
    test_count: int | None = None
    failure_count: int | None = None

    ok_match = re.search(r"\bOK \((\d+) tests?\)", output)
    if ok_match:
        test_count = int(ok_match.group(1))
        failure_count = 0

    run_match = re.search(r"\bTests run:\s*(\d+),\s*Failures:\s*(\d+)", output)
    if run_match:
        test_count = int(run_match.group(1))
        failure_count = int(run_match.group(2))

    numtests = [int(value) for value in re.findall(r"\bnumtests=(\d+)", output)]
    if test_count is None and numtests:
        test_count = max(numtests)

    failure_match = re.search(r"\bfailures?:\s*(\d+)", output, flags=re.IGNORECASE)
    if failure_count is None and failure_match:
        failure_count = int(failure_match.group(1))

    return {
        "testCount": test_count,
        "failureCount": failure_count,
    }


def is_class_filtered(command: list[str]) -> bool:
    command_tokens = [str(token) for token in command]
    return "-e" in command_tokens and "class" in command_tokens


def write_report(
    status: str,
    detail: str,
    devices: list[Device],
    command: list[str],
    *,
    output: str = "",
    mode: str,
    serial: str | None,
    stopped_packages: list[str] | None = None,
) -> None:
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    result_summary = parse_instrumentation_result(output)
    class_filtered = is_class_filtered(command)
    payload = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "detail": detail,
        "mode": mode,
        "serial": serial,
        "command": command,
        "devices": [device.__dict__ for device in devices],
        "stoppedThirdPartyPackages": stopped_packages or [],
        "targetPackage": TARGET_PACKAGE,
        "testPackage": TEST_PACKAGE,
        "testCount": result_summary["testCount"],
        "failureCount": result_summary["failureCount"],
        "classFiltered": class_filtered,
        "fullSuite": not class_filtered,
    }
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Instrumentation Smoke QA",
        "",
        f"Generated: {payload['generatedAt']}",
        f"Status: {status}",
        f"Detail: {detail}",
        f"Mode: `{mode}`",
        f"Serial: `{serial or ''}`",
        f"Test count: `{payload['testCount'] if payload['testCount'] is not None else ''}`",
        f"Failure count: `{payload['failureCount'] if payload['failureCount'] is not None else ''}`",
        f"Full suite: `{payload['fullSuite']}`",
        "",
        f"Command: `{' '.join(command)}`",
        "",
        "## Devices",
    ]
    if devices:
        lines.extend([f"- `{device.serial}`: {device.detail}" for device in devices])
    else:
        lines.append("- none")
    if stopped_packages:
        lines.extend(["", "## Stopped Third-party Packages"])
        lines.extend([f"- `{package}`" for package in stopped_packages])
    if output:
        tail = "\n".join(output.splitlines()[-100:])
        lines.extend(["", "## Command Tail", "", "```text", tail, "```"])
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_gradle_connected(devices: list[Device], serial: str | None) -> int:
    result = run(GRADLE_CONNECTED_COMMAND, check=False)
    status = "FAIL" if result.returncode != 0 else "PASS"
    detail = (
        f"connectedDebugAndroidTest failed with exit code {result.returncode}"
        if result.returncode != 0
        else f"connectedDebugAndroidTest passed on {len(devices)} device(s)"
    )
    write_report(
        status=status,
        detail=detail,
        devices=devices,
        command=GRADLE_CONNECTED_COMMAND,
        output=result.stdout,
        mode="gradle-connected",
        serial=serial,
    )
    if result.returncode != 0:
        print(result.stdout)
    return result.returncode


def run_serial_adb(devices: list[Device], serial: str, stop_other_apps: bool, device_timeout: float) -> int:
    build = run(BUILD_COMMAND, check=False)
    if build.returncode != 0:
        write_report(
            status="FAIL",
            detail=f"instrumentation APK build failed with exit code {build.returncode}",
            devices=devices,
            command=BUILD_COMMAND,
            output=build.stdout,
            mode="serial-adb",
            serial=serial,
        )
        print(build.stdout)
        return build.returncode

    wait_for_device(serial, device_timeout)
    refreshed_devices, _ = connected_devices()
    report_devices = refreshed_devices or devices
    stopped = force_stop_other_third_party_apps(serial) if stop_other_apps else []
    install_apk_with_retry(serial, DEBUG_APK, device_timeout)
    install_apk_with_retry(serial, ANDROID_TEST_APK, device_timeout)
    wait_for_device(serial, device_timeout)
    adb(serial, "shell", "pm", "clear", TARGET_PACKAGE, check=False)
    adb(serial, "shell", "pm", "clear", TEST_PACKAGE, check=False)
    instrument_args = [
        "shell",
        "am",
        "instrument",
        "-w",
        "-r",
        f"{TEST_PACKAGE}/{TEST_RUNNER}",
    ]
    wait_for_device(serial, device_timeout)
    result = adb(serial, *instrument_args, check=False)
    command = ["adb", "-s", serial, *instrument_args]
    failed = failed_instrumentation_output(result)
    status = "FAIL" if failed else "PASS"
    detail = (
        f"serial adb instrumentation failed with exit code {result.returncode}"
        if failed
        else f"serial adb instrumentation passed on {serial}"
    )
    write_report(
        status=status,
        detail=detail,
        devices=report_devices,
        command=command,
        output=result.stdout,
        mode="serial-adb",
        serial=serial,
        stopped_packages=stopped,
    )
    if failed:
        print(result.stdout)
        return result.returncode or 1
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--serial", help="adb serial. Defaults to the first connected emulator/device.")
    parser.add_argument(
        "--gradle-connected",
        action="store_true",
        help="use Gradle connectedDebugAndroidTest instead of serial-scoped adb instrument",
    )
    parser.add_argument(
        "--require-device",
        action="store_true",
        help="fail instead of skipping when no connected emulator/device is available",
    )
    parser.add_argument(
        "--no-force-stop-others",
        action="store_true",
        help="do not force-stop other third-party packages on shared emulators",
    )
    parser.add_argument(
        "--device-timeout",
        type=float,
        default=120.0,
        help="seconds to wait for the target serial to be online and boot-completed before install/retry",
    )
    args = parser.parse_args()

    devices, adb_output = connected_devices()
    serial = pick_serial(args.serial, devices)
    if serial is None:
        status = "FAIL" if args.require_device else "SKIP"
        detail = "no connected Android device/emulator"
        if adb_output:
            detail += f"; {adb_output}"
        write_report(
            status=status,
            detail=detail,
            devices=devices,
            command=GRADLE_CONNECTED_COMMAND if args.gradle_connected else BUILD_COMMAND,
            mode="gradle-connected" if args.gradle_connected else "serial-adb",
            serial=None,
        )
        print(f"Instrumentation smoke QA {status}: {detail}")
        raise SystemExit(1 if args.require_device else 0)

    exit_code = (
        run_gradle_connected(devices, serial)
        if args.gradle_connected
        else run_serial_adb(
            devices,
            serial,
            stop_other_apps=not args.no_force_stop_others,
            device_timeout=args.device_timeout,
        )
    )
    if exit_code != 0:
        raise SystemExit(exit_code)

    print(f"Instrumentation smoke QA PASS ({relative(REPORT_MD)})")


if __name__ == "__main__":
    main()
