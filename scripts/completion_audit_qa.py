#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_JSON = ROOT / "build/reports/completion_audit.json"
REPORT_MD = ROOT / "build/reports/completion_audit.md"


REQUIRED_FILES = [
    "AGENTS.md",
    "README.md",
    "Gemfile",
    "Gemfile.lock",
    "app/build.gradle.kts",
    "app/src/main/AndroidManifest.xml",
    "app/src/main/java/com/shawarma58/game/MainActivity.kt",
    "app/src/main/java/com/shawarma58/game/data/Models.kt",
    "app/src/main/java/com/shawarma58/game/data/LevelCatalog.kt",
    "app/src/main/java/com/shawarma58/game/data/ProgressStore.kt",
    "app/src/main/java/com/shawarma58/game/game/GameEngine.kt",
    "app/src/main/java/com/shawarma58/game/ui/Shawarma58App.kt",
    "app/src/main/java/com/shawarma58/game/ui/UiTestTags.kt",
    "app/src/test/java/com/shawarma58/game/GameRulesTest.kt",
    "app/src/androidTest/java/com/shawarma58/game/Shawarma58InstrumentedSmokeTest.kt",
    "docs/product_decision.md",
    "docs/product_spec.md",
    "docs/tech_stack_decision.md",
    "docs/art_direction.md",
    "docs/asset_prompts.md",
    "docs/asset_manifest.md",
    "docs/content_audit.md",
    "docs/ui_audit.md",
    "docs/accessibility_notes.md",
    "docs/performance_notes.md",
    "docs/privacy_and_permissions.md",
    "docs/qa_test_plan.md",
    "docs/android_emulator_smoke.md",
    "docs/google_play_checklist.md",
    "docs/release_plan.md",
    "docs/release_report.md",
    "docs/signing_setup.md",
    "docs/fastlane_upload.md",
    "docs/deobfuscation_notes.md",
    "docs/release_candidate_package.md",
    "docs/physical_device_sanity.md",
    "docs/completion_audit.md",
    "store/privacy_policy.html",
    "store/play_upload_packet.md",
    "store/play_console_answers.md",
    "store/play_listing_ru.md",
    "store/play_icon.png",
    "store/feature_graphic_concept.png",
    "store/launcher_icon_preview.png",
    "store/ingredient_alpha_contact_sheet.png",
    "store/screenshots/shawarma_onboarding.png",
    "store/screenshots/shawarma_menu.png",
    "store/screenshots/shawarma_levels.png",
    "store/screenshots/shawarma_gameplay.png",
    "store/screenshots/shawarma_result.png",
    "fastlane/metadata/android/ru-RU/title.txt",
    "fastlane/Appfile",
    "fastlane/Fastfile",
    "fastlane/README.md",
    "fastlane/metadata/android/ru-RU/short_description.txt",
    "fastlane/metadata/android/ru-RU/full_description.txt",
    "fastlane/metadata/android/ru-RU/changelogs/1.txt",
    "fastlane/metadata/android/ru-RU/images/icon.png",
    "fastlane/metadata/android/ru-RU/images/featureGraphic.png",
    "fastlane/metadata/android/ru-RU/images/phoneScreenshots/01_onboarding.png",
    "fastlane/metadata/android/ru-RU/images/phoneScreenshots/02_menu.png",
    "fastlane/metadata/android/ru-RU/images/phoneScreenshots/03_levels.png",
    "fastlane/metadata/android/ru-RU/images/phoneScreenshots/04_gameplay.png",
    "fastlane/metadata/android/ru-RU/images/phoneScreenshots/05_result.png",
    "scripts/asset_qa.py",
    "scripts/asset_manifest_qa.py",
    "scripts/accessibility_source_qa.py",
    "scripts/content_copy_qa.py",
    "scripts/android_smoke_qa.py",
    "scripts/instrumentation_smoke_qa.py",
    "scripts/ui_behavior_qa.py",
    "scripts/play_metadata_qa.py",
    "scripts/store_visual_quality_qa.py",
    "scripts/store_screenshot_freshness_qa.py",
    "scripts/store_screenshot_capture_qa.py",
    "scripts/store_screenshot_capture_guard_qa.py",
    "scripts/sync_fastlane_assets.py",
    "scripts/fastlane_assets_qa.py",
    "scripts/fastlane_config_qa.py",
    "scripts/fastlane_runtime_qa.py",
    "scripts/play_external_readiness_qa.py",
    "scripts/play_upload_auth_qa.py",
    "scripts/play_target_api_qa.py",
    "scripts/play_console_forms_qa.py",
    "scripts/play_upload_packet_qa.py",
    "scripts/privacy_data_safety_qa.py",
    "scripts/privacy_policy_hosting_qa.py",
    "scripts/prepare_upload_keystore.py",
    "scripts/signing_env_qa.py",
    "scripts/workspace_hygiene_qa.py",
    "scripts/artifact_provenance_qa.py",
    "scripts/performance_budget_qa.py",
    "scripts/physical_device_readiness_qa.py",
    "scripts/pre_upload_blockers_qa.py",
    "scripts/connected_performance_qa.py",
    "scripts/create_play_handoff.py",
    "scripts/play_handoff_qa.py",
    "scripts/create_play_handoff_archive.py",
    "scripts/play_handoff_archive_qa.py",
    "scripts/play_handoff_secret_scan_qa.py",
    "scripts/package_release_candidate.py",
    "scripts/post_package_validation_qa.py",
    "scripts/update_release_dates.py",
    "scripts/release_freshness_qa.py",
    "scripts/release_gate.py",
]

EXPECTED_PROGRESS_KEYS = [
    "onboardingSeen",
    "soundEnabled",
    "reducedMotion",
    "completedLevels",
    "starsByLevel",
    "bestEndlessScore",
]

EXPECTED_AUDIT_TERMS = [
    "Verified Locally",
    "External Blocker",
    "Manual Final Check",
    "Intentional Non-goal",
    "SHAWARMA58_KEYSTORE",
    "public non-PDF HTTPS URL",
    "Play Console setup",
    "physical-device sanity",
]


errors: list[str] = []


@dataclass
class Check:
    name: str
    status: str
    detail: str


def path(relative: str) -> Path:
    return ROOT / relative


def text(relative: str) -> str:
    return path(relative).read_text(encoding="utf-8")


def require_file(relative: str) -> None:
    if not path(relative).exists():
        errors.append(f"missing file: {relative}")


def require_contains(relative: str, snippet: str) -> None:
    if snippet not in text(relative):
        errors.append(f"{relative} is missing {snippet!r}")


def read_json_if_present(relative: str) -> dict[str, object] | None:
    report_path = path(relative)
    if not report_path.exists():
        return None
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{relative} is not valid JSON: {exc}")
        return None
    if not isinstance(payload, dict):
        errors.append(f"{relative} JSON root must be an object")
        return None
    return payload


def run_check(name: str, checks: list[Check], callback) -> None:
    before = len(errors)
    callback()
    new_errors = len(errors) - before
    checks.append(
        Check(
            name=name,
            status="PASS" if new_errors == 0 else "FAIL",
            detail="completed" if new_errors == 0 else f"{new_errors} issue(s)",
        ),
    )


def write_reports(checks: list[Check]) -> None:
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    status = "FAIL" if errors or any(check.status == "FAIL" for check in checks) else "PASS"
    payload = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "requiredFiles": REQUIRED_FILES,
        "expectedProgressKeys": EXPECTED_PROGRESS_KEYS,
        "checks": [asdict(check) for check in checks],
        "errors": errors,
    }
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Completion Audit QA",
        "",
        f"Generated: {payload['generatedAt']}",
        f"Status: `{status}`",
        f"Required files checked: `{len(REQUIRED_FILES)}`",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for check in checks:
        lines.append(f"| {check.name} | {check.status} | {check.detail} |")
    if errors:
        lines.extend(["", "## Errors"])
        lines.extend(f"- {error}" for error in errors)
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def enum_entry_count(source: str, enum_name: str) -> int:
    match = re.search(rf"enum class {enum_name}\b[\s\S]*?\{{([\s\S]*?)\n\}}", source)
    if not match:
        errors.append(f"enum not found: {enum_name}")
        return 0
    body = match.group(1)
    return len(re.findall(r"^\s+[A-Z_]+\(", body, flags=re.MULTILINE))


def verify_required_files() -> None:
    for relative in REQUIRED_FILES:
        require_file(relative)


def verify_build_config() -> None:
    gradle = text("app/build.gradle.kts")
    for snippet in [
        'applicationId = "com.shawarma58.game"',
        "minSdk = 23",
        "targetSdk = 35",
        "versionCode = 1",
        'versionName = "1.0.0"',
        "isMinifyEnabled = true",
        "isShrinkResources = true",
        "SHAWARMA58_KEYSTORE",
        '"androidx.lifecycle:lifecycle-runtime-compose:2.8.7"',
    ]:
        if snippet not in gradle:
            errors.append(f"app/build.gradle.kts is missing {snippet!r}")


def verify_manifest() -> None:
    manifest = path("app/src/main/AndroidManifest.xml")
    tree = ET.parse(manifest)
    root = tree.getroot()
    android = "{http://schemas.android.com/apk/res/android}"
    permissions = [node.attrib.get(f"{android}name", "") for node in root.findall("uses-permission")]
    if permissions:
        errors.append(f"manifest declares permissions: {permissions}")
    application = root.find("application")
    if application is None:
        errors.append("manifest is missing <application>")
        return
    if application.attrib.get(f"{android}allowBackup") != "false":
        errors.append("manifest must set android:allowBackup=\"false\"")


def verify_content_shape() -> None:
    models = text("app/src/main/java/com/shawarma58/game/data/Models.kt")
    levels = text("app/src/main/java/com/shawarma58/game/data/LevelCatalog.kt")
    if enum_entry_count(models, "Ingredient") != 8:
        errors.append("Ingredient enum must contain 8 entries")
    if enum_entry_count(models, "CustomerType") != 4:
        errors.append("CustomerType enum must contain 4 entries")
    for snippet in ["(1..24)", "спокойно", "быстро", "жарко", "endlessLevel"]:
        if snippet not in levels:
            errors.append(f"LevelCatalog.kt is missing {snippet!r}")


def verify_progress_keys() -> None:
    store = text("app/src/main/java/com/shawarma58/game/data/ProgressStore.kt")
    for key in EXPECTED_PROGRESS_KEYS:
        if key not in store:
            errors.append(f"ProgressStore.kt is missing key {key!r}")
    if "resetProgress" not in store:
        errors.append("ProgressStore.kt is missing resetProgress")


def verify_completion_audit() -> None:
    audit = text("docs/completion_audit.md")
    for term in EXPECTED_AUDIT_TERMS:
        if term not in audit:
            errors.append(f"docs/completion_audit.md is missing {term!r}")
    for required_path in [
        "docs/product_decision.md",
        "app/build.gradle.kts",
        "data/ProgressStore.kt",
        "scripts/release_gate.py",
        "scripts/accessibility_source_qa.py",
        "scripts/asset_manifest_qa.py",
        "scripts/content_copy_qa.py",
        "scripts/privacy_data_safety_qa.py",
        "scripts/play_target_api_qa.py",
        "scripts/privacy_policy_hosting_qa.py",
        "scripts/prepare_upload_keystore.py",
        "scripts/signing_env_qa.py",
        "scripts/workspace_hygiene_qa.py",
        "scripts/artifact_provenance_qa.py",
        "scripts/performance_budget_qa.py",
        "scripts/physical_device_readiness_qa.py",
        "scripts/pre_upload_blockers_qa.py",
        "scripts/connected_performance_qa.py",
        "scripts/instrumentation_smoke_qa.py",
        "scripts/store_visual_quality_qa.py",
        "scripts/store_screenshot_freshness_qa.py",
        "scripts/store_screenshot_capture_qa.py",
        "scripts/store_screenshot_capture_guard_qa.py",
        "scripts/sync_fastlane_assets.py",
        "scripts/fastlane_assets_qa.py",
        "scripts/fastlane_config_qa.py",
        "scripts/fastlane_runtime_qa.py",
        "scripts/play_external_readiness_qa.py",
        "scripts/play_upload_auth_qa.py",
        "build/reports/play_upload_packet.md",
        "build/reports/play_upload_packet.json",
        "scripts/play_console_forms_qa.py",
        "fastlane/Fastfile",
        "Gemfile",
        "Gemfile.lock",
        "docs/fastlane_upload.md",
        "docs/deobfuscation_notes.md",
        "fastlane/metadata/android/ru-RU/images",
        "scripts/create_play_handoff_archive.py",
        "scripts/play_handoff_archive_qa.py",
        "scripts/play_handoff_secret_scan_qa.py",
        "scripts/package_release_candidate.py",
        "scripts/post_package_validation_qa.py",
        "build/reports/post_package_validation.md",
        "package_release_candidate.py --strict-signing --fetch-privacy-url --fetch-target-api-policy",
        "--strict-physical-device",
        "Connected smoke include/skip state",
        "scripts/update_release_dates.py",
        "scripts/release_freshness_qa.py",
        "package status parity",
        "docs/release_candidate_package.md",
        "androidTest",
        "store/play_upload_packet.md",
        "store/privacy_policy.html",
        "resetProgress",
        "docs/physical_device_sanity.md",
        "docs/android_emulator_smoke.md",
        "gameplayBackOpensPauseOverlayBeforeLeavingShift",
        "Android Back opens pause overlay",
        "lifecycle background pause",
        "configuration-change restore",
        "activeSessionSaveableValuesRestoreCurrentShift",
    ]:
        if required_path not in audit:
            errors.append(f"docs/completion_audit.md does not reference {required_path}")

    target_api = read_json_if_present("build/reports/play_target_api.json")
    if target_api is not None:
        policy_date = target_api.get("policyCheckDate")
        if isinstance(policy_date, str) and f"against the {policy_date} official" not in audit:
            errors.append(f"docs/completion_audit.md does not reference current target API policy date {policy_date!r}")

    instrumentation = read_json_if_present("build/reports/instrumentation_smoke.json")
    if instrumentation is not None:
        serial = instrumentation.get("serial")
        test_count = instrumentation.get("testCount")
        failure_count = instrumentation.get("failureCount")
        if isinstance(serial, str) and f"current serial-scoped run on `{serial}`" not in audit:
            errors.append(f"docs/completion_audit.md does not reference current instrumentation serial {serial!r}")
        if isinstance(test_count, int) and f"passed {test_count} tests" not in audit:
            errors.append(f"docs/completion_audit.md does not reference current instrumentation test count {test_count}")
        if isinstance(failure_count, int) and f"{failure_count} failures" not in audit:
            errors.append(f"docs/completion_audit.md does not reference current instrumentation failure count {failure_count}")

    connected_performance = read_json_if_present("build/reports/connected_performance.json")
    if connected_performance is not None:
        flow_evidence = connected_performance.get("flowEvidence")
        if isinstance(flow_evidence, str):
            evidence_path = Path(flow_evidence)
            summary_path = (
                evidence_path.parent / "summary.md"
                if evidence_path.name == "instrumentation"
                else evidence_path / "summary.md"
            )
            summary_relative = summary_path.as_posix()
            if summary_relative not in audit:
                errors.append(
                    "docs/completion_audit.md does not reference current connected-performance "
                    f"evidence {summary_relative!r}",
                )

    store_capture = read_json_if_present("build/reports/store_screenshot_capture.json")
    if store_capture is not None:
        capture_dir = store_capture.get("captureDir")
        if isinstance(capture_dir, str):
            summary_relative = f"{capture_dir}/summary.md"
            if summary_relative not in audit:
                errors.append(
                    "docs/completion_audit.md does not reference current store screenshot "
                    f"capture evidence {summary_relative!r}",
                )


def verify_assets_and_metadata_docs() -> None:
    require_contains("docs/asset_manifest.md", "RGBA WebP")
    require_contains("docs/asset_manifest.md", "Real Android emulator screenshot")
    require_contains("docs/asset_manifest.md", "store/rejected_assets/")
    require_contains("docs/google_play_checklist.md", "targetSdk")
    require_contains("docs/privacy_and_permissions.md", "no `INTERNET` permission")
    require_contains("docs/privacy_and_permissions.md", "resets progress in app settings")
    require_contains("store/privacy_policy.html", "сбросит прогресс в настройках приложения")
    require_contains("docs/release_report.md", "python3 scripts/completion_audit_qa.py")
    require_contains("docs/release_report.md", "python3 scripts/asset_manifest_qa.py")
    require_contains("docs/release_report.md", "python3 scripts/content_copy_qa.py")
    require_contains("docs/release_report.md", "python3 scripts/accessibility_source_qa.py")
    require_contains("docs/release_report.md", "python3 scripts/play_upload_packet_qa.py")
    require_contains("docs/release_report.md", "python3 scripts/store_visual_quality_qa.py")
    require_contains("docs/release_report.md", "python3 scripts/store_screenshot_freshness_qa.py")
    require_contains("docs/release_report.md", "python3 scripts/store_screenshot_capture_qa.py")
    require_contains("docs/release_report.md", "python3 scripts/store_screenshot_capture_guard_qa.py")
    require_contains("docs/release_report.md", "python3 scripts/sync_fastlane_assets.py")
    require_contains("docs/release_report.md", "python3 scripts/fastlane_assets_qa.py")
    require_contains("docs/release_report.md", "python3 scripts/fastlane_config_qa.py")
    require_contains("docs/release_report.md", "python3 scripts/fastlane_runtime_qa.py")
    require_contains("docs/release_report.md", "python3 scripts/play_external_readiness_qa.py")
    require_contains("docs/release_report.md", "python3 scripts/play_upload_auth_qa.py")
    require_contains("docs/release_report.md", "python3 scripts/play_console_forms_qa.py")
    require_contains("docs/release_report.md", "python3 scripts/play_target_api_qa.py")
    require_contains("docs/release_report.md", "python3 scripts/privacy_data_safety_qa.py")
    require_contains("docs/release_report.md", "python3 scripts/privacy_policy_hosting_qa.py")
    require_contains("docs/release_report.md", "python3 scripts/prepare_upload_keystore.py")
    require_contains("docs/release_report.md", "python3 scripts/signing_env_qa.py")
    require_contains("docs/release_report.md", "python3 scripts/workspace_hygiene_qa.py")
    require_contains("docs/release_report.md", "python3 scripts/artifact_provenance_qa.py")
    require_contains("docs/release_report.md", "python3 scripts/performance_budget_qa.py")
    require_contains("docs/release_report.md", "python3 scripts/physical_device_readiness_qa.py")
    require_contains("docs/release_report.md", "python3 scripts/pre_upload_blockers_qa.py")
    require_contains("docs/release_report.md", "python3 scripts/connected_performance_qa.py")
    require_contains("docs/release_report.md", "python3 scripts/instrumentation_smoke_qa.py")
    require_contains("docs/release_report.md", "serial-scoped `adb am instrument`")
    require_contains("docs/release_report.md", "python3 scripts/android_smoke_qa.py")
    require_contains("docs/release_report.md", "python3 scripts/ui_behavior_qa.py")
    require_contains("docs/release_report.md", "python3 scripts/create_play_handoff.py")
    require_contains("docs/release_report.md", "python3 scripts/play_handoff_qa.py")
    require_contains("docs/release_report.md", "python3 scripts/create_play_handoff_archive.py")
    require_contains("docs/release_report.md", "python3 scripts/play_handoff_archive_qa.py")
    require_contains("docs/release_report.md", "python3 scripts/play_handoff_secret_scan_qa.py")
    require_contains("docs/release_report.md", "python3 scripts/package_release_candidate.py")
    require_contains("docs/release_report.md", "python3 scripts/update_release_dates.py")
    require_contains("docs/release_report.md", "python3 scripts/release_freshness_qa.py")
    require_contains("docs/release_report.md", "deobfuscation/release")
    require_contains("scripts/release_gate.py", "Completion audit QA")
    require_contains("scripts/release_gate.py", "Asset manifest QA")
    require_contains("scripts/release_gate.py", "Content copy QA")
    require_contains("scripts/release_gate.py", "Accessibility source QA")
    require_contains("scripts/release_gate.py", "Privacy data safety QA")
    require_contains("scripts/release_gate.py", "Privacy policy hosting QA")
    require_contains("scripts/release_gate.py", "Upload keystore setup")
    require_contains("scripts/release_gate.py", "Workspace hygiene QA")
    require_contains("scripts/release_gate.py", "Signing environment QA")
    require_contains("scripts/release_gate.py", "Artifact provenance QA")
    require_contains("scripts/release_gate.py", "Performance budget QA")
    require_contains("scripts/release_gate.py", "Physical device readiness QA")
    require_contains("scripts/release_gate.py", "Pre-upload blockers QA")
    require_contains("scripts/release_gate.py", "Connected performance QA")
    require_contains("scripts/release_gate.py", "Instrumentation smoke QA")
    require_contains("scripts/release_gate.py", "UI behavior QA")
    require_contains("scripts/release_gate.py", "Fastlane asset sync")
    require_contains("scripts/release_gate.py", "Fastlane assets QA")
    require_contains("scripts/release_gate.py", "Fastlane config QA")
    require_contains("scripts/release_gate.py", "Fastlane runtime QA")
    require_contains("scripts/release_gate.py", "Play external readiness QA")
    require_contains("scripts/release_gate.py", "Play upload auth QA")
    require_contains("scripts/release_gate.py", "Play target API QA")
    require_contains("scripts/release_gate.py", "Play Console forms QA")
    require_contains("scripts/release_gate.py", "Play upload packet QA")
    require_contains("scripts/create_play_handoff.py", "qa/play_upload_packet/play_upload_packet.json")
    require_contains("scripts/play_handoff_qa.py", "play upload packet report must be PASS")
    require_contains("scripts/release_freshness_qa.py", "build/reports/play_upload_packet.json")
    require_contains("scripts/release_gate.py", "Store visual quality QA")
    require_contains("scripts/release_gate.py", "Store screenshot freshness QA")
    require_contains("scripts/release_gate.py", "Store screenshot capture QA")
    require_contains("scripts/release_gate.py", "Store screenshot capture guard QA")
    require_contains("scripts/ui_behavior_qa.py", "rememberSaveable(stateSaver = AppScreenSaver)")
    require_contains("scripts/ui_behavior_qa.py", "activeSessionSaveableValuesRestoreCurrentShift")
    require_contains("app/src/main/java/com/shawarma58/game/ui/Shawarma58App.kt", "GameSessionSaver")
    require_contains("app/src/test/java/com/shawarma58/game/GameRulesTest.kt", "activeSessionSaveableValuesRestoreCurrentShift")
    require_contains("scripts/capture_store_screenshots.py", "validate_screenshot_candidate")
    require_contains("scripts/capture_store_screenshots.py", "candidate_")
    require_contains("scripts/release_gate.py", "assembleDebugAndroidTest")
    require_contains("fastlane/Fastfile", "python3 scripts/package_release_candidate.py --strict-signing --fetch-privacy-url --fetch-target-api-policy")
    require_contains("fastlane/Fastfile", "python3 scripts/pre_upload_blockers_qa.py --strict")
    require_contains("fastlane/Fastfile", "--strict-physical-device")
    require_contains("fastlane/Fastfile", "--strict-pre-upload")
    require_contains("fastlane/Fastfile", "python3 scripts/play_handoff_secret_scan_qa.py")
    require_contains("fastlane/Fastfile", "python3 scripts/post_package_validation_qa.py")
    require_contains("scripts/release_gate.py", "--strict-pre-upload")
    require_contains("scripts/package_release_candidate.py", "--strict-pre-upload")
    require_contains("scripts/fastlane_config_qa.py", "Fastfile upload guard order")
    require_contains("scripts/fastlane_config_qa.py", "no pre-upload report rewrite after package")
    require_contains("scripts/play_upload_packet_qa.py", "avoids rewriting that report after package")
    require_contains("scripts/play_handoff_qa.py", "fastlane config report must be PASS in handoff")
    require_contains("scripts/play_handoff_qa.py", "Fastfile upload guard order")
    require_contains("scripts/play_handoff_qa.py", "mandatory_handoff_copy_targets")
    require_contains("scripts/play_handoff_qa.py", "manifest is missing copy-map target")
    require_contains("scripts/play_handoff_qa.py", "build/reports/play_handoff_qa.json")
    require_contains("scripts/release_freshness_qa.py", "build/reports/play_handoff_qa.json")
    require_contains("scripts/release_freshness_qa.py", "build/play_handoff/shawarma58-v1.0.0/qa/fastlane_config/fastlane_config.json")
    require_contains("scripts/release_freshness_qa.py", "build/play_handoff/shawarma58-v1.0.0/qa/upload_operator_runbook/upload_operator_runbook.json")
    require_contains("scripts/release_freshness_qa.py", "mandatory_handoff_json_reports")
    require_contains("scripts/release_freshness_qa.py", "Mandatory handoff QA JSON coverage")
    require_contains("scripts/package_release_candidate.py", "Release freshness QA")
    require_contains("scripts/package_release_candidate.py", '"status": status')
    require_contains("scripts/package_release_candidate.py", '"connectedSmoke": handoff_manifest.get("connectedSmoke", {})')
    require_contains("scripts/create_play_handoff.py", "Connected Smoke To Refresh")
    require_contains("scripts/play_handoff_qa.py", "manifest.connectedSmoke.status must be included, skipped or missing")
    require_contains("scripts/play_handoff_archive_qa.py", "connectedSmoke does not match handoff manifest")
    require_contains("scripts/release_freshness_qa.py", "check_package_report_status")
    require_contains("scripts/release_freshness_qa.py", "Package status derivation")
    require_contains("docs/release_report.md", "package status derivation/sidecar parity")
    require_contains("scripts/play_handoff_archive_qa.py", "archive package report status")
    require_contains("scripts/play_handoff_archive_qa.py", "build/reports/play_handoff_archive_qa.json")
    require_contains("scripts/release_freshness_qa.py", "build/reports/play_handoff_archive_qa.json")
    require_contains("scripts/package_release_candidate.py", "Play handoff secret scan QA")
    require_contains("scripts/package_release_candidate.py", "Update release dates")
    require_contains("scripts/package_release_candidate.py", "Post-package validation QA")
    require_contains("scripts/post_package_validation_qa.py", "Final sidecar secret scan ordering")
    require_contains("scripts/post_package_validation_qa.py", "Package manifest SHA parity")
    require_contains("scripts/post_package_validation_qa.py", "Handoff directory manifest files")
    require_contains("scripts/post_package_validation_qa.py", "Handoff directory checksum parity")
    require_contains("scripts/post_package_validation_qa.py", "Local handoff QA report status")
    require_contains("scripts/post_package_validation_qa.py", "Local archive QA report status")
    require_contains("scripts/post_package_validation_qa.py", "Post-package report excluded from handoff manifest")
    require_contains("scripts/post_package_validation_qa.py", "Package flow no sidecar rewrite after final scan")
    require_contains("docs/upload_operator_runbook.md", "python3 scripts/post_package_validation_qa.py")
    require_contains("scripts/upload_operator_runbook_qa.py", "python3 scripts/post_package_validation_qa.py")
    require_contains("scripts/upload_operator_runbook_qa.py", "Strict package command order")
    require_contains("scripts/upload_operator_runbook_qa.py", "no pre-upload report rewrite after package")
    require_contains("scripts/package_release_candidate.py", 'handoff.append("--fetch-privacy-url")')
    require_contains("scripts/create_play_handoff.py", "--fetch-privacy-url")


def main() -> None:
    checks: list[Check] = []
    run_check("Required project files", checks, verify_required_files)
    if errors:
        write_reports(checks)
        print("Completion audit QA failed")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    run_check("Build config", checks, verify_build_config)
    run_check("Manifest privacy invariants", checks, verify_manifest)
    run_check("Static content shape", checks, verify_content_shape)
    run_check("Progress persistence keys", checks, verify_progress_keys)
    run_check("Completion audit document", checks, verify_completion_audit)
    run_check("Release docs and asset evidence", checks, verify_assets_and_metadata_docs)
    write_reports(checks)

    if errors:
        print("Completion audit QA failed")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print("Completion audit QA PASS")


if __name__ == "__main__":
    main()
