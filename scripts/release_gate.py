#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AAB = ROOT / "app/build/outputs/bundle/release/app-release.aab"
APK = ROOT / "app/build/outputs/apk/debug/app-debug.apk"
MANIFEST = ROOT / "app/src/main/AndroidManifest.xml"
APP_GRADLE = ROOT / "app/build.gradle.kts"
PLAY_EXTERNAL_READINESS = ROOT / "build/reports/play_external_readiness.json"
STORE_SCREENSHOT_FRESHNESS = ROOT / "build/reports/store_screenshot_freshness.json"
PHYSICAL_DEVICE_READINESS = ROOT / "build/reports/physical_device_readiness.json"
PRE_UPLOAD_BLOCKERS = ROOT / "build/reports/pre_upload_blockers.json"
FASTLANE_RUNTIME = ROOT / "build/reports/fastlane_runtime.json"
PLAY_UPLOAD_AUTH = ROOT / "build/reports/play_upload_auth.json"
PLAY_TARGET_API = ROOT / "build/reports/play_target_api.json"
PRIVACY_POLICY_HOSTING = ROOT / "build/reports/privacy_policy_hosting.json"
SIGNING_ENV_REPORT = ROOT / "build/reports/signing_env.json"
UPLOAD_KEYSTORE_SETUP = ROOT / "build/reports/upload_keystore_setup.json"
UPLOAD_OPERATOR_RUNBOOK = ROOT / "build/reports/upload_operator_runbook.json"
REPORT_JSON = ROOT / "build/reports/release_gate.json"
REPORT_MD = ROOT / "build/reports/release_gate.md"
REQUIRED_SIGNING_ENV = (
    "SHAWARMA58_KEYSTORE",
    "SHAWARMA58_KEYSTORE_PASSWORD",
    "SHAWARMA58_KEY_ALIAS",
    "SHAWARMA58_KEY_PASSWORD",
)
AGGREGATE_BLOCKER_ROWS = {"Play external readiness", "Pre-upload blockers"}


@dataclass
class Check:
    name: str
    status: str
    detail: str


def gate_status(checks: list[Check]) -> str:
    statuses = [check.status for check in checks]
    if any(status == "FAIL" for status in statuses):
        return "FAIL"
    if any(status == "EXTERNAL_BLOCKER" for status in statuses):
        return "EXTERNAL_BLOCKER"
    if any(status in {"PASS_WITH_WARNINGS", "WARN"} for status in statuses):
        return "PASS_WITH_WARNINGS"
    return "PASS"


def write_gate_report(checks: list[Check], argv: list[str]) -> None:
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    status = gate_status(checks)
    payload = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "command": argv,
        "checks": [check.__dict__ for check in checks],
        "externalBlockers": [check.__dict__ for check in checks if check.status == "EXTERNAL_BLOCKER"],
    }
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Release Gate",
        "",
        f"Generated: {payload['generatedAt']}",
        f"Status: {status}",
        "",
        f"Command: `{' '.join(argv)}`",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for check in checks:
        lines.append(f"| {check.name} | {check.status} | {check.detail} |")
    blockers = payload["externalBlockers"]
    if blockers:
        lines.extend(["", "## External Blockers"])
        for blocker in blockers:
            lines.append(f"- {blocker['name']}: {blocker['detail']}")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_command(name: str, command: list[str]) -> Check:
    print(f"==> {name}: {' '.join(command)}")
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode != 0:
        print(result.stdout)
        raise SystemExit(f"{name} failed with exit code {result.returncode}")
    return Check(name=name, status="PASS", detail="completed")


def status_from_checks(checks: list[object]) -> str:
    statuses = [str(check.get("status", "FAIL")) for check in checks if isinstance(check, dict)]
    if any(status == "FAIL" for status in statuses):
        return "FAIL"
    if any(status == "EXTERNAL_BLOCKER" for status in statuses):
        return "EXTERNAL_BLOCKER"
    if any(status == "PASS_WITH_WARNINGS" for status in statuses):
        return "PASS_WITH_WARNINGS"
    return "PASS"


def summarize_json_report(path: Path, name: str, pass_detail: str) -> Check:
    if not path.exists():
        raise SystemExit(f"{name} report is missing: {path.relative_to(ROOT)}")
    report = json.loads(path.read_text(encoding="utf-8"))
    checks = report.get("checks")
    if not isinstance(checks, list):
        raise SystemExit(f"{name} report has invalid checks")
    status = str(report.get("status") or status_from_checks(checks))
    blockers = [
        f"{check.get('name')}: {check.get('detail')}"
        for check in checks
        if isinstance(check, dict) and check.get("status") in {"FAIL", "EXTERNAL_BLOCKER"}
    ]
    if blockers:
        return Check(name=name, status=status, detail="; ".join(blockers))
    return Check(name=name, status=status, detail=pass_detail)


def summarize_external_readiness() -> Check:
    if not PLAY_EXTERNAL_READINESS.exists():
        raise SystemExit("Play external readiness report is missing")
    report = json.loads(PLAY_EXTERNAL_READINESS.read_text(encoding="utf-8"))
    checks = report.get("checks")
    if not isinstance(checks, list):
        raise SystemExit("Play external readiness report has invalid checks")
    blockers = [
        f"{check.get('name')}: {check.get('detail')}"
        for check in checks
        if isinstance(check, dict) and check.get("status") == "EXTERNAL_BLOCKER"
    ]
    if blockers:
        return Check(
            name="Play external readiness",
            status="EXTERNAL_BLOCKER",
            detail="; ".join(blockers),
        )
    return Check(
        name="Play external readiness",
        status="PASS",
        detail="external upload inputs are ready",
    )


def summarize_store_screenshot_freshness() -> Check:
    if not STORE_SCREENSHOT_FRESHNESS.exists():
        raise SystemExit("Store screenshot freshness report is missing")
    report = json.loads(STORE_SCREENSHOT_FRESHNESS.read_text(encoding="utf-8"))
    status = str(report.get("status", "FAIL"))
    stale = report.get("staleScreenshots")
    upload_count = 0
    qa_count = 0
    if isinstance(stale, dict):
        upload = stale.get("upload")
        qa = stale.get("qa")
        upload_count = len(upload) if isinstance(upload, list) else 0
        qa_count = len(qa) if isinstance(qa, list) else 0
    detail = (
        "screenshots are fresh"
        if upload_count == 0 and qa_count == 0
        else f"{upload_count} upload and {qa_count} QA screenshots need recapture before final upload"
    )
    return Check(name="Store screenshot freshness", status=status, detail=detail)


def summarize_physical_device_readiness() -> Check:
    if not PHYSICAL_DEVICE_READINESS.exists():
        raise SystemExit("Physical device readiness report is missing")
    report = json.loads(PHYSICAL_DEVICE_READINESS.read_text(encoding="utf-8"))
    status = str(report.get("status", "FAIL"))
    checks = report.get("checks")
    blockers: list[str] = []
    if isinstance(checks, list):
        blockers = [
            f"{check.get('name')}: {check.get('detail')}"
            for check in checks
            if isinstance(check, dict) and check.get("status") == "EXTERNAL_BLOCKER"
        ]
    detail = "; ".join(blockers) if blockers else "physical-device readiness is satisfied"
    return Check(name="Physical device readiness", status=status, detail=detail)


def summarize_pre_upload_blockers() -> Check:
    if not PRE_UPLOAD_BLOCKERS.exists():
        raise SystemExit("Pre-upload blockers report is missing")
    report = json.loads(PRE_UPLOAD_BLOCKERS.read_text(encoding="utf-8"))
    status = str(report.get("status", "FAIL"))
    groups = report.get("blockerGroups")
    blockers: list[str] = []
    if isinstance(groups, list):
        blockers = [
            f"{group.get('title')}: {group.get('action')}"
            for group in groups
            if isinstance(group, dict) and group.get("status") != "PASS"
        ]
    detail = "; ".join(blockers) if blockers else "no pre-upload blockers remain in source reports"
    return Check(name="Pre-upload blockers", status=status, detail=detail)


def verify_manifest() -> Check:
    tree = ET.parse(MANIFEST)
    root = tree.getroot()
    android = "{http://schemas.android.com/apk/res/android}"
    permissions = [node.attrib.get(f"{android}name", "") for node in root.findall("uses-permission")]
    if permissions:
        raise SystemExit(f"Manifest declares permissions: {permissions}")
    application = root.find("application")
    if application is None:
        raise SystemExit("Manifest is missing <application>")
    allow_backup = application.attrib.get(f"{android}allowBackup")
    if allow_backup != "false":
        raise SystemExit(f"android:allowBackup must be false, got {allow_backup!r}")
    return Check(
        name="Manifest privacy invariants",
        status="PASS",
        detail="no permissions; allowBackup=false",
    )


def verify_artifacts() -> Check:
    required = [
        APK,
        AAB,
        ROOT / "store/privacy_policy.html",
        ROOT / "store/play_console_answers.md",
        ROOT / "store/play_listing_ru.md",
        ROOT / "store/feature_graphic_concept.png",
        ROOT / "store/screenshots/shawarma_onboarding.png",
        ROOT / "store/screenshots/shawarma_menu.png",
        ROOT / "store/screenshots/shawarma_levels.png",
        ROOT / "store/screenshots/shawarma_gameplay.png",
        ROOT / "store/screenshots/shawarma_result.png",
    ]
    missing = [path.relative_to(ROOT).as_posix() for path in required if not path.exists()]
    if missing:
        raise SystemExit(f"Missing release artifacts: {missing}")
    return Check(name="Release artifacts", status="PASS", detail="all expected files exist")


def verify_release_build_hardening() -> Check:
    script = APP_GRADLE.read_text(encoding="utf-8")
    required = {
        "isMinifyEnabled = true": "R8 minification",
        "isShrinkResources = true": "resource shrinking",
    }
    missing = [label for snippet, label in required.items() if snippet not in script]
    if missing:
        raise SystemExit(f"Release build hardening disabled: {', '.join(missing)}")
    return Check(
        name="Release build hardening",
        status="PASS",
        detail="R8 minify and resource shrinking enabled",
    )


def jarsigner_path() -> str | None:
    candidates = [
        Path("/Applications/Android Studio.app/Contents/jbr/Contents/Home/bin/jarsigner"),
    ]
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        candidates.append(Path(java_home) / "bin/jarsigner")
    path_candidate = shutil.which("jarsigner")
    if path_candidate:
        candidates.append(Path(path_candidate))
    for candidate in candidates:
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def verify_signing(strict: bool) -> Check:
    missing_env = [name for name in REQUIRED_SIGNING_ENV if not os.environ.get(name)]
    signer = jarsigner_path()
    if signer is None:
        detail = "jarsigner unavailable"
        if strict:
            raise SystemExit(detail)
        return Check(name="AAB signing", status="EXTERNAL_BLOCKER", detail=detail)

    result = subprocess.run(
        [signer, "-verify", "-verbose", "-certs", str(AAB)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    output = result.stdout
    signed = "jar is unsigned" not in output.lower() and "signature was verified" in output.lower()
    if signed:
        return Check(name="AAB signing", status="PASS", detail="signature verified")

    detail = "AAB is unsigned"
    if missing_env:
        detail += f"; missing env vars: {', '.join(missing_env)}"
    if strict:
        print(output)
        raise SystemExit(detail)
    return Check(name="AAB signing", status="EXTERNAL_BLOCKER", detail=detail)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--strict-signing",
        action="store_true",
        help="fail if the release AAB is unsigned",
    )
    parser.add_argument(
        "--connected-tests",
        action="store_true",
        help="run serial-scoped instrumentation smoke QA on a connected emulator/device",
    )
    parser.add_argument(
        "--connected-performance",
        action="store_true",
        help="run connected performance smoke on a connected emulator/device",
    )
    parser.add_argument(
        "--serial",
        help="adb serial to use with --connected-tests and --connected-performance",
    )
    parser.add_argument(
        "--fetch-privacy-url",
        action="store_true",
        help="fetch and inspect SHAWARMA58_PRIVACY_POLICY_URL in external readiness QA",
    )
    parser.add_argument(
        "--fetch-target-api-policy",
        action="store_true",
        help="fetch official Google Play target API policy sources in Play target API QA",
    )
    parser.add_argument(
        "--strict-screenshots",
        action="store_true",
        help="fail if store screenshots are older than UI/gameplay source files",
    )
    parser.add_argument(
        "--strict-physical-device",
        action="store_true",
        help="fail unless a non-emulator Android phone is connected for physical-device sanity",
    )
    parser.add_argument(
        "--strict-pre-upload",
        action="store_true",
        help="fail if any consolidated pre-upload blocker remains",
    )
    args = parser.parse_args()

    checks: list[Check] = []
    checks.append(run_command("Asset QA", ["python3", "scripts/asset_qa.py"]))
    checks.append(run_command("Asset manifest QA", ["python3", "scripts/asset_manifest_qa.py"]))
    checks.append(run_command("UI behavior QA", ["python3", "scripts/ui_behavior_qa.py"]))
    checks.append(run_command("Content copy QA", ["python3", "scripts/content_copy_qa.py"]))
    checks.append(run_command("Accessibility source QA", ["python3", "scripts/accessibility_source_qa.py"]))
    checks.append(run_command("Play metadata QA", ["python3", "scripts/play_metadata_qa.py"]))
    play_target_api_command = ["python3", "scripts/play_target_api_qa.py"]
    if args.fetch_target_api_policy:
        play_target_api_command.append("--fetch-policy")
    checks.append(run_command("Play target API QA", play_target_api_command))
    checks.append(run_command("Store visual quality QA", ["python3", "scripts/store_visual_quality_qa.py"]))
    checks.append(run_command("Store screenshot capture guard QA", ["python3", "scripts/store_screenshot_capture_guard_qa.py"]))
    screenshot_freshness_command = ["python3", "scripts/store_screenshot_freshness_qa.py"]
    if args.strict_screenshots:
        screenshot_freshness_command.append("--strict")
    run_command("Store screenshot freshness QA", screenshot_freshness_command)
    checks.append(summarize_store_screenshot_freshness())
    checks.append(run_command("Store screenshot capture QA", ["python3", "scripts/store_screenshot_capture_qa.py"]))
    checks.append(run_command("Fastlane asset sync", ["python3", "scripts/sync_fastlane_assets.py"]))
    checks.append(run_command("Fastlane assets QA", ["python3", "scripts/fastlane_assets_qa.py"]))
    checks.append(run_command("Fastlane config QA", ["python3", "scripts/fastlane_config_qa.py"]))
    fastlane_runtime_command = ["python3", "scripts/fastlane_runtime_qa.py"]
    if args.strict_signing:
        fastlane_runtime_command.append("--strict")
    run_command("Fastlane runtime QA", fastlane_runtime_command)
    checks.append(summarize_json_report(FASTLANE_RUNTIME, "Fastlane runtime QA", "fastlane runtime is ready"))
    checks.append(run_command("Play upload packet QA", ["python3", "scripts/play_upload_packet_qa.py"]))
    checks.append(run_command("Play Console forms QA", ["python3", "scripts/play_console_forms_qa.py"]))
    play_upload_auth_command = ["python3", "scripts/play_upload_auth_qa.py"]
    if args.strict_signing:
        play_upload_auth_command.append("--strict")
    run_command("Play upload auth QA", play_upload_auth_command)
    checks.append(summarize_json_report(PLAY_UPLOAD_AUTH, "Play upload auth QA", "Play service-account auth is ready"))
    checks.append(run_command("Privacy data safety QA", ["python3", "scripts/privacy_data_safety_qa.py"]))
    privacy_policy_hosting_command = ["python3", "scripts/privacy_policy_hosting_qa.py"]
    if args.strict_signing:
        privacy_policy_hosting_command.append("--strict")
    if args.fetch_privacy_url:
        privacy_policy_hosting_command.append("--fetch-privacy-url")
    run_command("Privacy policy hosting QA", privacy_policy_hosting_command)
    checks.append(summarize_json_report(PRIVACY_POLICY_HOSTING, "Privacy policy hosting QA", "privacy policy hosting is ready"))
    physical_device_command = ["python3", "scripts/physical_device_readiness_qa.py"]
    if args.strict_physical_device:
        physical_device_command.append("--strict")
    run_command("Physical device readiness QA", physical_device_command)
    checks.append(summarize_physical_device_readiness())
    checks.append(run_command("Completion audit QA", ["python3", "scripts/completion_audit_qa.py"]))
    external_readiness_command = ["python3", "scripts/play_external_readiness_qa.py"]
    if args.strict_signing:
        external_readiness_command.append("--strict")
    if args.fetch_privacy_url:
        external_readiness_command.append("--fetch-privacy-url")
    run_command("Play external readiness QA", external_readiness_command)
    checks.append(summarize_external_readiness())
    signing_env_command = ["python3", "scripts/signing_env_qa.py"]
    if args.strict_signing:
        signing_env_command.append("--strict")
    run_command("Signing environment QA", signing_env_command)
    checks.append(summarize_json_report(SIGNING_ENV_REPORT, "Signing environment QA", "signing environment is ready"))
    upload_keystore_command = ["python3", "scripts/prepare_upload_keystore.py"]
    if args.strict_signing:
        upload_keystore_command.append("--strict")
    run_command("Upload keystore setup", upload_keystore_command)
    checks.append(summarize_json_report(UPLOAD_KEYSTORE_SETUP, "Upload keystore setup", "upload keystore is ready"))
    run_command("Upload operator runbook QA", ["python3", "scripts/upload_operator_runbook_qa.py"])
    checks.append(summarize_json_report(UPLOAD_OPERATOR_RUNBOOK, "Upload operator runbook QA", "upload operator runbook is complete"))
    checks.append(run_command("Workspace hygiene QA", ["python3", "scripts/workspace_hygiene_qa.py"]))
    checks.append(run_command("Gradle gates", ["./gradlew", "test", "lint", "assembleDebug", "assembleDebugAndroidTest", "bundleRelease"]))
    artifact_command = ["python3", "scripts/artifact_provenance_qa.py"]
    if args.strict_signing:
        artifact_command.append("--strict-signing")
    checks.append(run_command("Artifact provenance QA", artifact_command))
    checks.append(run_command("Performance budget QA", ["python3", "scripts/performance_budget_qa.py"]))
    pre_upload_command = ["python3", "scripts/pre_upload_blockers_qa.py"]
    if args.strict_pre_upload:
        pre_upload_command.append("--strict")
    run_command("Pre-upload blockers QA", pre_upload_command)
    checks.append(summarize_pre_upload_blockers())
    if args.connected_tests:
        instrumentation_command = ["python3", "scripts/instrumentation_smoke_qa.py", "--require-device"]
        if args.serial:
            instrumentation_command.extend(["--serial", args.serial])
        checks.append(
            run_command(
                "Instrumentation smoke QA",
                instrumentation_command,
            ),
        )
    if args.connected_performance:
        performance_command = ["python3", "scripts/connected_performance_qa.py"]
        if args.serial:
            performance_command.extend(["--serial", args.serial])
        checks.append(
            run_command(
                "Connected performance QA",
                performance_command,
            ),
        )
    checks.append(verify_manifest())
    checks.append(verify_release_build_hardening())
    checks.append(verify_artifacts())
    checks.append(verify_signing(strict=args.strict_signing))
    write_gate_report(checks, sys.argv)

    print("\nRelease gate summary")
    print("| Check | Status | Detail |")
    print("|---|---|---|")
    for check in checks:
        print(f"| {check.name} | {check.status} | {check.detail} |")

    blockers = [check for check in checks if check.status == "EXTERNAL_BLOCKER"]
    if blockers:
        actionable_blockers = [check for check in blockers if check.name not in AGGREGATE_BLOCKER_ROWS]
        displayed_blockers = actionable_blockers or blockers
        print("\nLocal release checks passed. External blockers remain:")
        for blocker in displayed_blockers:
            print(f"- {blocker.name}: {blocker.detail}")
        print("Use --strict-signing in the final production-signing environment.")
    else:
        print("\nRelease gate passed without local or signing blockers.")


if __name__ == "__main__":
    main()
