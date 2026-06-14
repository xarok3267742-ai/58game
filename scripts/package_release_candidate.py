#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HANDOFF = ROOT / "build/play_handoff/shawarma58-v1.0.0"
ARCHIVE_REPORT = ROOT / "build/play_handoff/shawarma58-v1.0.0.zip.json"
ARCHIVE_PACKAGE_REPORT_JSON = ROOT / "build/play_handoff/shawarma58-v1.0.0.zip.package.json"
ARCHIVE_PACKAGE_REPORT_MD = ROOT / "build/play_handoff/shawarma58-v1.0.0.zip.package.md"
PACKAGE_REPORT_JSON = ROOT / "build/reports/release_candidate_package.json"
PACKAGE_REPORT_MD = ROOT / "build/reports/release_candidate_package.md"
PRE_UPLOAD_BLOCKERS_JSON = ROOT / "build/reports/pre_upload_blockers.json"
PRE_UPLOAD_BLOCKERS_MD = ROOT / "build/reports/pre_upload_blockers.md"
RELEASE_GATE_JSON = ROOT / "build/reports/release_gate.json"
RELEASE_GATE_MD = ROOT / "build/reports/release_gate.md"


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def run_step(name: str, command: list[str]) -> dict[str, object]:
    print(f"==> {name}: {' '.join(command)}")
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.stdout:
        print(result.stdout)
    if result.returncode != 0:
        raise SystemExit(f"{name} failed with exit code {result.returncode}")
    return {
        "name": name,
        "command": command,
        "status": "PASS",
    }


def load_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def collect_external_blockers() -> list[str]:
    blockers: list[str] = []
    for report_path in [
        ROOT / "build/reports/play_external_readiness.json",
        ROOT / "build/reports/play_upload_auth.json",
        ROOT / "build/reports/privacy_policy_hosting.json",
        ROOT / "build/reports/fastlane_runtime.json",
        ROOT / "build/reports/physical_device_readiness.json",
        ROOT / "build/reports/signing_env.json",
        ROOT / "build/reports/upload_keystore_setup.json",
        ROOT / "build/reports/artifact_provenance.json",
    ]:
        report = load_json(report_path)
        checks = report.get("checks")
        if not isinstance(checks, list):
            continue
        for check in checks:
            if isinstance(check, dict) and check.get("status") == "EXTERNAL_BLOCKER":
                blockers.append(f"{check.get('name')}: {check.get('detail')}")
    seen: set[str] = set()
    unique: list[str] = []
    for blocker in blockers:
        if blocker in seen:
            continue
        seen.add(blocker)
        unique.append(blocker)
    return unique


def collect_pre_upload_blockers() -> dict[str, object]:
    report = load_json(PRE_UPLOAD_BLOCKERS_JSON)
    groups = report.get("blockerGroups")
    pending: list[dict[str, object]] = []
    if isinstance(groups, list):
        for group in groups:
            if not isinstance(group, dict) or group.get("status") == "PASS":
                continue
            pending.append(
                {
                    "id": group.get("id", ""),
                    "title": group.get("title", ""),
                    "status": group.get("status", ""),
                    "action": group.get("action", ""),
                    "strictCommand": group.get("strictCommand", ""),
                },
            )
    return {
        "status": report.get("status", ""),
        "baseStatus": report.get("baseStatus", ""),
        "strict": report.get("strict", False),
        "report": rel(PRE_UPLOAD_BLOCKERS_MD),
        "jsonReport": rel(PRE_UPLOAD_BLOCKERS_JSON),
        "pendingActions": pending,
    }


def collect_optional_evidence(handoff_manifest: dict[str, object]) -> dict[str, object]:
    optional_evidence = handoff_manifest.get("optionalEvidence")
    if not isinstance(optional_evidence, dict):
        return {}
    return optional_evidence


def package_status(steps: list[dict[str, object]], release_gate: dict[str, object]) -> str:
    if any(step.get("status") == "FAIL" for step in steps):
        return "FAIL"
    release_gate_status = str(release_gate.get("status") or "")
    if release_gate_status in {"FAIL", "EXTERNAL_BLOCKER", "PASS_WITH_WARNINGS"}:
        return release_gate_status
    return "PASS"


def write_report(steps: list[dict[str, object]]) -> None:
    handoff_manifest = load_json(HANDOFF / "manifest.json")
    archive_report = load_json(ARCHIVE_REPORT)
    release_gate = load_json(RELEASE_GATE_JSON)
    files = handoff_manifest.get("files")
    upload = files.get("upload/app-release.aab") if isinstance(files, dict) else {}
    deobfuscation = files.get("deobfuscation/release/mapping.txt") if isinstance(files, dict) else {}
    optional_evidence = collect_optional_evidence(handoff_manifest)
    status = package_status(steps, release_gate)
    archive_path = Path(str(archive_report.get("archive", "")))
    archive_sidecar_path = Path(str(archive_report.get("sha256File", "")))
    archive_verify_command = (
        f"cd {archive_path.parent.as_posix()} && shasum -a 256 -c {archive_sidecar_path.name}"
        if archive_path.parent.as_posix() and archive_sidecar_path.name
        else ""
    )
    package_report = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "steps": steps,
        "releaseGate": {
            "status": release_gate.get("status", ""),
            "report": rel(RELEASE_GATE_MD),
            "jsonReport": rel(RELEASE_GATE_JSON),
        },
        "handoff": {
            "path": rel(HANDOFF),
            "fileCount": len(files) if isinstance(files, dict) else 0,
            "signing": handoff_manifest.get("signing", {}),
            "releaseGate": handoff_manifest.get("releaseGate", {}),
            "connectedSmoke": handoff_manifest.get("connectedSmoke", {}),
            "aabSha256": upload.get("sha256") if isinstance(upload, dict) else "",
            "mappingSha256": deobfuscation.get("sha256") if isinstance(deobfuscation, dict) else "",
            "optionalEvidence": optional_evidence,
        },
        "archive": {
            "path": archive_report.get("archive", ""),
            "bytes": archive_report.get("bytes", 0),
            "sha256": archive_report.get("sha256", ""),
            "manifestSha256": archive_report.get("manifestSha256", ""),
            "sha256File": archive_report.get("sha256File", ""),
            "fileCount": archive_report.get("fileCount", 0),
            "verifyCommand": archive_verify_command,
        },
        "externalBlockers": collect_external_blockers(),
        "preUploadBlockers": collect_pre_upload_blockers(),
    }
    lines = [
        "# Release Candidate Package",
        "",
        f"Generated: {package_report['generatedAt']}",
        f"Status: `{status}`",
        "",
        "| Step | Status | Command |",
        "|---|---|---|",
    ]
    for step in steps:
        lines.append(f"| {step['name']} | {step['status']} | `{' '.join(step['command'])}` |")
    handoff = package_report["handoff"]
    archive = package_report["archive"]
    lines.extend(
        [
            "",
            "## Handoff",
            f"- Directory: `{handoff['path']}`",
            f"- Files in manifest: `{handoff['fileCount']}`",
            f"- Signing: `{handoff['signing'].get('status', '<unknown>')}`",
            f"- Release gate: `{handoff['releaseGate'].get('status', '<unknown>')}`",
            f"- AAB SHA-256: `{handoff['aabSha256']}`",
            f"- Mapping SHA-256: `{handoff['mappingSha256']}`",
            "",
            "## Archive",
            f"- Archive: `{archive['path']}`",
            f"- SHA sidecar: `{archive['sha256File']}`",
            f"- Bytes: `{archive['bytes']}`",
            f"- Files: `{archive['fileCount']}`",
            f"- SHA-256: `{archive['sha256']}`",
            f"- Manifest SHA-256: `{archive['manifestSha256']}`",
            f"- Verify sidecar: `{archive['verifyCommand']}`",
        ]
    )
    blockers = package_report["externalBlockers"]
    pre_upload = package_report["preUploadBlockers"]
    optional_connected = optional_evidence.get("connectedPerformance")
    optional_instrumentation = optional_evidence.get("instrumentationSmoke")
    connected_smoke = handoff.get("connectedSmoke")
    if isinstance(connected_smoke, dict):
        lines.extend(
            [
                "",
                "## Connected Smoke",
                f"- Status: `{connected_smoke.get('status', '<unknown>')}`",
                f"- Detail: {connected_smoke.get('detail', 'Included fresh Android smoke evidence.')}",
                f"- Refresh: `{connected_smoke.get('rerunCommand', 'python3 scripts/android_smoke_qa.py --serial <adb-serial> --extended')}`",
            ],
        )
        if connected_smoke.get("status") == "included":
            lines.append("- Handoff report: `qa/android_smoke/latest/summary.md`")
    if isinstance(optional_connected, dict) or isinstance(optional_instrumentation, dict):
        lines.extend(
            [
                "",
                "## Optional Evidence",
            ],
        )
    if isinstance(optional_instrumentation, dict):
        lines.extend(
            [
                f"- Instrumentation smoke: `{optional_instrumentation.get('status', '<unknown>')}`",
                f"- Detail: {optional_instrumentation.get('detail', 'No detail recorded.')}",
                f"- Refresh: `{optional_instrumentation.get('rerunCommand', 'python3 scripts/instrumentation_smoke_qa.py --require-device --serial <adb-serial>')}`",
            ],
        )
        if optional_instrumentation.get("status") == "included":
            lines.append("- Handoff report: `qa/instrumentation_smoke/instrumentation_smoke.md`")
    if isinstance(optional_connected, dict):
        lines.extend(
            [
                f"- Connected performance: `{optional_connected.get('status', '<unknown>')}`",
                f"- Detail: {optional_connected.get('detail', 'No detail recorded.')}",
                f"- Refresh: `{optional_connected.get('rerunCommand', 'python3 scripts/connected_performance_qa.py --serial <adb-serial>')}`",
            ],
        )
        if optional_connected.get("status") == "included":
            lines.append("- Handoff report: `qa/connected_performance/connected_performance.md`")
    if isinstance(pre_upload, dict):
        lines.extend(
            [
                "",
                "## Pre-upload Blocker Summary",
                f"- Status: `{pre_upload.get('status', '<unknown>')}`",
                f"- Base status: `{pre_upload.get('baseStatus', '<unknown>')}`",
                f"- Report: `{pre_upload.get('report', '')}`",
            ],
        )
        pending = pre_upload.get("pendingActions")
        if isinstance(pending, list) and pending:
            lines.append("- Pending actions:")
            for item in pending:
                if not isinstance(item, dict):
                    continue
                lines.append(
                    f"  - {item.get('title')}: {item.get('action')} (`{item.get('strictCommand')}`)",
                )
        else:
            lines.append("- Pending actions: none")
    if blockers:
        lines.append("")
        lines.append("## External Blocker Details")
        lines.append(f"- Raw detail count: `{len(blockers)}`")
        lines.append(f"- Full raw details: `{rel(PACKAGE_REPORT_JSON)}`")
        lines.append(f"- Operator action report: `{pre_upload.get('report', '') if isinstance(pre_upload, dict) else rel(PRE_UPLOAD_BLOCKERS_MD)}`")
    package_markdown = "\n".join(lines) + "\n"

    PACKAGE_REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    PACKAGE_REPORT_JSON.write_text(json.dumps(package_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    PACKAGE_REPORT_MD.write_text(package_markdown, encoding="utf-8")
    ARCHIVE_PACKAGE_REPORT_JSON.write_text(json.dumps(package_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ARCHIVE_PACKAGE_REPORT_MD.write_text(package_markdown, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict-signing", action="store_true", help="fail unless signing/upload inputs are ready")
    parser.add_argument("--connected-tests", action="store_true", help="run instrumentation smoke through release_gate")
    parser.add_argument("--connected-performance", action="store_true", help="run connected performance through release_gate")
    parser.add_argument("--serial", help="adb serial to use with connected release_gate checks")
    parser.add_argument("--fetch-privacy-url", action="store_true", help="fetch and inspect hosted privacy URL")
    parser.add_argument("--fetch-target-api-policy", action="store_true", help="fetch official Google Play target API policy sources")
    parser.add_argument("--strict-screenshots", action="store_true", help="fail if store screenshots are stale")
    parser.add_argument("--strict-physical-device", action="store_true", help="fail unless a non-emulator Android phone is connected")
    parser.add_argument("--strict-pre-upload", action="store_true", help="fail if any consolidated pre-upload blocker remains")
    args = parser.parse_args()

    release_gate = ["python3", "scripts/release_gate.py"]
    handoff = ["python3", "scripts/create_play_handoff.py"]
    if args.strict_signing:
        release_gate.append("--strict-signing")
        handoff.append("--strict-signing")
    if args.connected_tests:
        release_gate.append("--connected-tests")
    if args.connected_performance:
        release_gate.append("--connected-performance")
    if args.serial:
        release_gate.extend(["--serial", args.serial])
    if args.fetch_privacy_url:
        release_gate.append("--fetch-privacy-url")
        handoff.append("--fetch-privacy-url")
    if args.fetch_target_api_policy:
        release_gate.append("--fetch-target-api-policy")
    if args.strict_screenshots:
        release_gate.append("--strict-screenshots")
    if args.strict_physical_device:
        release_gate.append("--strict-physical-device")
    if args.strict_pre_upload:
        release_gate.append("--strict-pre-upload")

    steps = [
        run_step("Update release dates", ["python3", "scripts/update_release_dates.py"]),
        run_step("Release gate", release_gate),
        run_step("Create Play handoff", handoff),
        run_step("Play handoff QA", ["python3", "scripts/play_handoff_qa.py"]),
        run_step("Create Play handoff archive", ["python3", "scripts/create_play_handoff_archive.py"]),
    ]
    write_report(steps)
    steps.append(run_step("Play handoff archive QA", ["python3", "scripts/play_handoff_archive_qa.py", "--require-package-report"]))
    write_report(steps)
    steps.append(run_step("Play handoff secret scan QA", ["python3", "scripts/play_handoff_secret_scan_qa.py"]))
    write_report(steps)
    steps.append(run_step("Release freshness QA", ["python3", "scripts/release_freshness_qa.py"]))
    write_report(steps)
    run_step("Final transfer sidecar secret scan QA", ["python3", "scripts/play_handoff_secret_scan_qa.py"])
    run_step("Final release freshness QA", ["python3", "scripts/release_freshness_qa.py"])
    run_step("Post-package validation QA", ["python3", "scripts/post_package_validation_qa.py"])
    print(f"Release candidate package report: {rel(PACKAGE_REPORT_MD)}")
    print(f"Transfer package report: {rel(ARCHIVE_PACKAGE_REPORT_MD)}")


if __name__ == "__main__":
    main()
