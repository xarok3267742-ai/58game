#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_MD = ROOT / "build/reports/physical_device_readiness.md"
REPORT_JSON = ROOT / "build/reports/physical_device_readiness.json"
SANITY_DOC = ROOT / "docs/physical_device_sanity.md"

DOC_REQUIRED_TERMS = [
    "real Android phone",
    "airplane mode",
    "Сбросить прогресс",
    "Удалить прогресс",
    "Пауза",
    "Progress/settings persist",
    "Evidence To Keep",
]


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def external_or_fail(strict: bool) -> str:
    return "FAIL" if strict else "EXTERNAL_BLOCKER"


def parse_device_line(line: str) -> dict[str, str]:
    parts = line.split()
    device: dict[str, str] = {
        "serial": parts[0] if parts else "",
        "state": parts[1] if len(parts) > 1 else "",
        "raw": line,
    }
    for part in parts[2:]:
        if ":" in part:
            key, value = part.split(":", 1)
            device[key] = value
    return device


def is_emulator(device: dict[str, str]) -> bool:
    serial = device.get("serial", "").lower()
    if serial.startswith("emulator-"):
        return True
    values = " ".join(
        device.get(key, "").lower()
        for key in ("product", "model", "device")
    )
    emulator_markers = ("sdk", "gphone", "emulator", "emu64", "ranchu", "goldfish")
    return any(marker in values for marker in emulator_markers)


def list_adb_devices() -> tuple[list[dict[str, str]], Check]:
    if shutil.which("adb") is None:
        return [], Check("ADB runtime", "EXTERNAL_BLOCKER", "adb command is not available")
    result = subprocess.run(
        ["adb", "devices", "-l"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=20,
    )
    if result.returncode != 0:
        return [], Check("ADB runtime", "EXTERNAL_BLOCKER", f"adb devices failed: {result.stdout.strip()}")
    devices = [
        parse_device_line(line.strip())
        for line in result.stdout.splitlines()[1:]
        if line.strip()
    ]
    return devices, Check("ADB runtime", "PASS", "adb devices completed")


def check_sanity_doc() -> list[Check]:
    if not SANITY_DOC.exists():
        return [Check("Physical sanity checklist", "FAIL", f"missing {rel(SANITY_DOC)}")]
    text = SANITY_DOC.read_text(encoding="utf-8")
    missing = [term for term in DOC_REQUIRED_TERMS if term not in text]
    if missing:
        return [Check("Physical sanity checklist", "FAIL", f"missing terms: {', '.join(missing)}")]
    return [Check("Physical sanity checklist", "PASS", "manual phone checklist covers offline/gameplay/settings/reset/evidence")]


def classify_devices(devices: list[dict[str, str]], strict: bool) -> list[Check]:
    connected = [device for device in devices if device.get("state") == "device"]
    physical = [device for device in connected if not is_emulator(device)]
    emulators = [device for device in connected if is_emulator(device)]
    checks = [
        Check(
            "Connected Android devices",
            "PASS" if connected else external_or_fail(strict),
            f"{len(connected)} connected, {len(emulators)} emulator, {len(physical)} physical",
        ),
    ]
    if physical:
        serials = ", ".join(device["serial"] for device in physical)
        checks.append(Check("Physical Android phone", "PASS", f"candidate physical serial(s): {serials}"))
    else:
        detail = "no non-emulator Android phone connected; run docs/physical_device_sanity.md before production rollout"
        checks.append(Check("Physical Android phone", external_or_fail(strict), detail))
    unavailable = [device for device in devices if device.get("state") in {"unauthorized", "offline"}]
    if unavailable:
        checks.append(
            Check(
                "Unavailable Android devices",
                external_or_fail(strict),
                ", ".join(f"{device.get('serial')}:{device.get('state')}" for device in unavailable),
            ),
        )
    return checks


def report_status(checks: list[Check]) -> str:
    if any(check.status == "FAIL" for check in checks):
        return "FAIL"
    if any(check.status == "EXTERNAL_BLOCKER" for check in checks):
        return "EXTERNAL_BLOCKER"
    return "PASS"


def write_reports(strict: bool, devices: list[dict[str, str]], checks: list[Check]) -> str:
    status = report_status(checks)
    payload = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "strict": strict,
        "devices": devices,
        "checks": [check.__dict__ for check in checks],
    }
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Physical Device Readiness QA",
        "",
        f"Generated: {payload['generatedAt']}",
        f"Status: `{status}`",
        f"Strict mode: `{strict}`",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for check in checks:
        lines.append(f"| {check.name} | {check.status} | {check.detail} |")
    lines.extend(
        [
            "",
            "## Devices",
            "| Serial | State | Product | Model | Device |",
            "|---|---|---|---|---|",
        ],
    )
    if devices:
        for device in devices:
            lines.append(
                "| {serial} | {state} | {product} | {model} | {device} |".format(
                    serial=device.get("serial", ""),
                    state=device.get("state", ""),
                    product=device.get("product", ""),
                    model=device.get("model", ""),
                    device=device.get("device", ""),
                ),
            )
    else:
        lines.append("| <none> |  |  |  |  |")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return status


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true", help="fail unless a non-emulator Android phone is connected")
    args = parser.parse_args()

    devices, adb_check = list_adb_devices()
    if args.strict and adb_check.status == "EXTERNAL_BLOCKER":
        adb_check = Check(adb_check.name, "FAIL", adb_check.detail)
    checks = [adb_check, *classify_devices(devices, strict=args.strict), *check_sanity_doc()]
    status = write_reports(strict=args.strict, devices=devices, checks=checks)

    if status == "FAIL":
        print("Physical device readiness QA failed")
        for failure in [check for check in checks if check.status == "FAIL"]:
            print(f"- {failure.name}: {failure.detail}")
        raise SystemExit(1)
    if status == "EXTERNAL_BLOCKER":
        print(f"Physical device readiness QA EXTERNAL_BLOCKER ({rel(REPORT_MD)}, {rel(REPORT_JSON)})")
        for blocker in [check for check in checks if check.status == "EXTERNAL_BLOCKER"]:
            print(f"- {blocker.name}: {blocker.detail}")
        return
    print(f"Physical device readiness QA PASS ({rel(REPORT_MD)}, {rel(REPORT_JSON)})")


if __name__ == "__main__":
    main()
