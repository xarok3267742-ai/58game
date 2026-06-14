#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "build/play_handoff/shawarma58-v1.0.0"
STALE_OUTPUT_ROOT = ROOT / "build/stale_play_handoff"
AAB = ROOT / "app/build/outputs/bundle/release/app-release.aab"
APK = ROOT / "app/build/outputs/apk/debug/app-debug.apk"
SIGNING_ENV = [
    "SHAWARMA58_KEYSTORE",
    "SHAWARMA58_KEYSTORE_PASSWORD",
    "SHAWARMA58_KEY_ALIAS",
    "SHAWARMA58_KEY_PASSWORD",
]
SMOKE_SOURCE_GLOBS = [
    "app/build.gradle.kts",
    "build.gradle.kts",
    "settings.gradle.kts",
    "app/src/main/AndroidManifest.xml",
    "app/src/main/java/**/*.kt",
    "app/src/main/res/drawable/**/*",
    "app/src/main/res/drawable-nodpi/**/*",
    "app/src/main/res/mipmap-*/*",
    "app/src/main/res/values/**/*.xml",
    "app/src/main/res/xml/**/*.xml",
]
ANDROID_SMOKE_RERUN = "python3 scripts/android_smoke_qa.py --serial <adb-serial> --extended"
INSTRUMENTATION_SMOKE_RERUN = "python3 scripts/instrumentation_smoke_qa.py --require-device --serial <adb-serial>"
OPTIONAL_INSTRUMENTATION_SOURCE_GLOBS = [
    "app/src/androidTest/**/*.kt",
]
WORKSPACE_HYGIENE_FILES = {
    "qa/workspace_hygiene/workspace_hygiene.md": "build/reports/workspace_hygiene.md",
    "qa/workspace_hygiene/workspace_hygiene.json": "build/reports/workspace_hygiene.json",
}
RELEASE_GATE_REPORT = ROOT / "build/reports/release_gate.json"

FILES = {
    "upload/app-release.aab": "app/build/outputs/bundle/release/app-release.aab",
    "debug/app-debug.apk": "app/build/outputs/apk/debug/app-debug.apk",
    "metadata/ru-RU/title.txt": "fastlane/metadata/android/ru-RU/title.txt",
    "metadata/ru-RU/short_description.txt": "fastlane/metadata/android/ru-RU/short_description.txt",
    "metadata/ru-RU/full_description.txt": "fastlane/metadata/android/ru-RU/full_description.txt",
    "metadata/ru-RU/changelogs/1.txt": "fastlane/metadata/android/ru-RU/changelogs/1.txt",
    "fastlane/Appfile": "fastlane/Appfile",
    "fastlane/Fastfile": "fastlane/Fastfile",
    "fastlane/README.md": "fastlane/README.md",
    "Gemfile": "Gemfile",
    "Gemfile.lock": "Gemfile.lock",
    "graphics/play_icon.png": "store/play_icon.png",
    "graphics/feature_graphic_concept.png": "store/feature_graphic_concept.png",
    "graphics/screenshots/01_onboarding.png": "fastlane/metadata/android/ru-RU/images/phoneScreenshots/01_onboarding.png",
    "graphics/screenshots/02_menu.png": "fastlane/metadata/android/ru-RU/images/phoneScreenshots/02_menu.png",
    "graphics/screenshots/03_levels.png": "fastlane/metadata/android/ru-RU/images/phoneScreenshots/03_levels.png",
    "graphics/screenshots/04_gameplay.png": "fastlane/metadata/android/ru-RU/images/phoneScreenshots/04_gameplay.png",
    "graphics/screenshots/05_result.png": "fastlane/metadata/android/ru-RU/images/phoneScreenshots/05_result.png",
    "fastlane/metadata/android/ru-RU/images/icon.png": "fastlane/metadata/android/ru-RU/images/icon.png",
    "fastlane/metadata/android/ru-RU/images/featureGraphic.png": "fastlane/metadata/android/ru-RU/images/featureGraphic.png",
    "fastlane/metadata/android/ru-RU/images/phoneScreenshots/01_onboarding.png": "fastlane/metadata/android/ru-RU/images/phoneScreenshots/01_onboarding.png",
    "fastlane/metadata/android/ru-RU/images/phoneScreenshots/02_menu.png": "fastlane/metadata/android/ru-RU/images/phoneScreenshots/02_menu.png",
    "fastlane/metadata/android/ru-RU/images/phoneScreenshots/03_levels.png": "fastlane/metadata/android/ru-RU/images/phoneScreenshots/03_levels.png",
    "fastlane/metadata/android/ru-RU/images/phoneScreenshots/04_gameplay.png": "fastlane/metadata/android/ru-RU/images/phoneScreenshots/04_gameplay.png",
    "fastlane/metadata/android/ru-RU/images/phoneScreenshots/05_result.png": "fastlane/metadata/android/ru-RU/images/phoneScreenshots/05_result.png",
    "qa/screenshots/wrong_order.png": "store/screenshots/shawarma_wrong_order.png",
    "qa/screenshots/endless_result.png": "store/screenshots/shawarma_endless_result.png",
    "privacy/privacy_policy.html": "store/privacy_policy.html",
    "privacy/hosting/README.md": "build/privacy_policy_handoff/README.md",
    "privacy/hosting/manifest.json": "build/privacy_policy_handoff/manifest.json",
    "privacy/hosting/privacy_policy.html": "build/privacy_policy_handoff/privacy_policy.html",
    "docs/play_upload_packet.md": "store/play_upload_packet.md",
    "docs/play_console_answers.md": "store/play_console_answers.md",
    "docs/play_listing_ru.md": "store/play_listing_ru.md",
    "docs/asset_manifest.md": "docs/asset_manifest.md",
    "docs/rejected_assets.md": "docs/rejected_assets.md",
    "docs/fastlane_upload.md": "docs/fastlane_upload.md",
    "docs/deobfuscation_notes.md": "docs/deobfuscation_notes.md",
    "docs/google_play_checklist.md": "docs/google_play_checklist.md",
    "docs/qa_test_plan.md": "docs/qa_test_plan.md",
    "docs/android_emulator_smoke.md": "docs/android_emulator_smoke.md",
    "docs/physical_device_sanity.md": "docs/physical_device_sanity.md",
    "docs/upload_operator_runbook.md": "docs/upload_operator_runbook.md",
    "docs/release_plan.md": "docs/release_plan.md",
    "docs/completion_audit.md": "docs/completion_audit.md",
    "docs/release_report.md": "docs/release_report.md",
    "qa/asset/asset.md": "build/reports/asset.md",
    "qa/asset/asset.json": "build/reports/asset.json",
    "qa/asset_manifest/asset_manifest.md": "build/reports/asset_manifest.md",
    "qa/asset_manifest/asset_manifest.json": "build/reports/asset_manifest.json",
    "qa/content_copy/content_copy.md": "build/reports/content_copy.md",
    "qa/content_copy/content_copy.json": "build/reports/content_copy.json",
    "qa/ui_behavior/ui_behavior.md": "build/reports/ui_behavior.md",
    "qa/ui_behavior/ui_behavior.json": "build/reports/ui_behavior.json",
    "qa/accessibility_source/accessibility_source.md": "build/reports/accessibility_source.md",
    "qa/accessibility_source/accessibility_source.json": "build/reports/accessibility_source.json",
    "qa/completion_audit/completion_audit.md": "build/reports/completion_audit.md",
    "qa/completion_audit/completion_audit.json": "build/reports/completion_audit.json",
    "qa/fastlane_assets/fastlane_assets.md": "build/reports/fastlane_assets.md",
    "qa/fastlane_assets/fastlane_assets.json": "build/reports/fastlane_assets.json",
    "qa/fastlane_config/fastlane_config.md": "build/reports/fastlane_config.md",
    "qa/fastlane_config/fastlane_config.json": "build/reports/fastlane_config.json",
    "qa/fastlane_runtime/fastlane_runtime.md": "build/reports/fastlane_runtime.md",
    "qa/fastlane_runtime/fastlane_runtime.json": "build/reports/fastlane_runtime.json",
    "qa/store_visual_quality/store_visual_quality.md": "build/reports/store_visual_quality.md",
    "qa/store_visual_quality/store_visual_quality.json": "build/reports/store_visual_quality.json",
    "qa/store_screenshot_capture_guard/store_screenshot_capture_guard.md": "build/reports/store_screenshot_capture_guard.md",
    "qa/store_screenshot_capture_guard/store_screenshot_capture_guard.json": "build/reports/store_screenshot_capture_guard.json",
    "qa/store_screenshot_freshness/store_screenshot_freshness.md": "build/reports/store_screenshot_freshness.md",
    "qa/store_screenshot_freshness/store_screenshot_freshness.json": "build/reports/store_screenshot_freshness.json",
    "qa/store_screenshot_capture/store_screenshot_capture.md": "build/reports/store_screenshot_capture.md",
    "qa/store_screenshot_capture/store_screenshot_capture.json": "build/reports/store_screenshot_capture.json",
    "qa/play_external_readiness/play_external_readiness.md": "build/reports/play_external_readiness.md",
    "qa/play_external_readiness/play_external_readiness.json": "build/reports/play_external_readiness.json",
    "qa/play_upload_packet/play_upload_packet.md": "build/reports/play_upload_packet.md",
    "qa/play_upload_packet/play_upload_packet.json": "build/reports/play_upload_packet.json",
    "qa/play_metadata/play_metadata.md": "build/reports/play_metadata.md",
    "qa/play_metadata/play_metadata.json": "build/reports/play_metadata.json",
    "qa/play_upload_auth/play_upload_auth.md": "build/reports/play_upload_auth.md",
    "qa/play_upload_auth/play_upload_auth.json": "build/reports/play_upload_auth.json",
    "qa/play_console_forms/play_console_forms.md": "build/reports/play_console_forms.md",
    "qa/play_console_forms/play_console_forms.json": "build/reports/play_console_forms.json",
    "qa/play_target_api/play_target_api.md": "build/reports/play_target_api.md",
    "qa/play_target_api/play_target_api.json": "build/reports/play_target_api.json",
    "qa/privacy_policy_hosting/privacy_policy_hosting.md": "build/reports/privacy_policy_hosting.md",
    "qa/privacy_policy_hosting/privacy_policy_hosting.json": "build/reports/privacy_policy_hosting.json",
    "qa/signing_env/signing_env.md": "build/reports/signing_env.md",
    "qa/signing_env/signing_env.json": "build/reports/signing_env.json",
    "qa/upload_keystore_setup/upload_keystore_setup.md": "build/reports/upload_keystore_setup.md",
    "qa/upload_keystore_setup/upload_keystore_setup.json": "build/reports/upload_keystore_setup.json",
    "qa/upload_operator_runbook/upload_operator_runbook.md": "build/reports/upload_operator_runbook.md",
    "qa/upload_operator_runbook/upload_operator_runbook.json": "build/reports/upload_operator_runbook.json",
    **WORKSPACE_HYGIENE_FILES,
    "qa/privacy_data_safety/privacy_data_safety.md": "build/reports/privacy_data_safety.md",
    "qa/privacy_data_safety/privacy_data_safety.json": "build/reports/privacy_data_safety.json",
    "qa/artifact_provenance/artifact_provenance.md": "build/reports/artifact_provenance.md",
    "qa/artifact_provenance/artifact_provenance.json": "build/reports/artifact_provenance.json",
    "qa/performance_budget/performance_budget.md": "build/reports/performance_budget.md",
    "qa/performance_budget/performance_budget.json": "build/reports/performance_budget.json",
    "qa/physical_device_readiness/physical_device_readiness.md": "build/reports/physical_device_readiness.md",
    "qa/physical_device_readiness/physical_device_readiness.json": "build/reports/physical_device_readiness.json",
    "qa/pre_upload_blockers/pre_upload_blockers.md": "build/reports/pre_upload_blockers.md",
    "qa/pre_upload_blockers/pre_upload_blockers.json": "build/reports/pre_upload_blockers.json",
    "qa/release_gate/release_gate.md": "build/reports/release_gate.md",
    "qa/release_gate/release_gate.json": "build/reports/release_gate.json",
    "deobfuscation/release/configuration.txt": "app/build/outputs/mapping/release/configuration.txt",
    "deobfuscation/release/mapping.txt": "app/build/outputs/mapping/release/mapping.txt",
    "deobfuscation/release/resources.txt": "app/build/outputs/mapping/release/resources.txt",
    "deobfuscation/release/seeds.txt": "app/build/outputs/mapping/release/seeds.txt",
    "deobfuscation/release/usage.txt": "app/build/outputs/mapping/release/usage.txt",
}
OPTIONAL_FILES = {
    "qa/instrumentation_smoke/instrumentation_smoke.md": "build/reports/instrumentation_smoke.md",
    "qa/instrumentation_smoke/instrumentation_smoke.json": "build/reports/instrumentation_smoke.json",
    "qa/connected_performance/connected_performance.md": "build/reports/connected_performance.md",
    "qa/connected_performance/connected_performance.json": "build/reports/connected_performance.json",
}
OPTIONAL_REPORT_STATUS = {
    "build/reports/instrumentation_smoke.json": {"PASS"},
    "build/reports/connected_performance.json": {"PASS", "PASS_WITH_WARNINGS"},
}
OPTIONAL_CONNECTED_PERFORMANCE_SOURCE_GLOBS = [
    "app/build.gradle.kts",
    "build.gradle.kts",
    "settings.gradle.kts",
    "app/src/main/AndroidManifest.xml",
    "app/src/main/java/**/*.kt",
    "app/src/main/res/drawable/**/*",
    "app/src/main/res/drawable-nodpi/**/*",
    "app/src/main/res/mipmap-*/*",
    "app/src/main/res/values/**/*.xml",
    "app/src/main/res/xml/**/*.xml",
]


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_info(path: Path) -> dict[str, object]:
    info: dict[str, object] = {
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }
    if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
        image = Image.open(path)
        info["width"] = image.size[0]
        info["height"] = image.size[1]
        info["mode"] = image.mode
    return info


def jarsigner_path() -> str | None:
    candidates = []
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        candidates.append(Path(java_home) / "bin/jarsigner")
    path_candidate = shutil.which("jarsigner")
    if path_candidate:
        candidates.append(Path(path_candidate))
    candidates.append(Path("/Applications/Android Studio.app/Contents/jbr/Contents/Home/bin/jarsigner"))
    for candidate in candidates:
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def signing_status() -> dict[str, object]:
    missing_env = [name for name in SIGNING_ENV if not os.environ.get(name)]
    signer = jarsigner_path()
    if signer is None:
        return {
            "status": "external_blocker",
            "detail": "jarsigner unavailable",
            "missing_env": missing_env,
        }
    if not AAB.exists():
        return {
            "status": "missing",
            "detail": "release AAB is missing",
            "missing_env": missing_env,
        }
    result = subprocess.run(
        [signer, "-verify", "-verbose", "-certs", str(AAB)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    output = result.stdout.lower()
    signed = "jar is unsigned" not in output and "signature was verified" in output
    if signed:
        return {
            "status": "signed",
            "detail": "AAB signature verified",
            "missing_env": missing_env,
        }
    return {
        "status": "external_blocker",
        "detail": "AAB is unsigned",
        "missing_env": missing_env,
    }


def ensure_output_path(out: Path) -> None:
    resolved = out.resolve()
    allowed = (ROOT / "build").resolve()
    if allowed != resolved and allowed not in resolved.parents:
        raise SystemExit(f"Refusing to write outside build/: {out}")


def reset_output_path(out: Path) -> None:
    ensure_output_path(out)
    if out.exists():
        STALE_OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        stale = STALE_OUTPUT_ROOT / f"{out.name}-{timestamp}"
        suffix = 1
        while stale.exists():
            suffix += 1
            stale = STALE_OUTPUT_ROOT / f"{out.name}-{timestamp}-{suffix}"
        out.rename(stale)
        print(f"Moved stale handoff output to {relative(stale)}")
    out.mkdir(parents=True, exist_ok=False)


def validate_sources() -> None:
    missing = [source for source in FILES.values() if not (ROOT / source).exists()]
    if missing:
        raise SystemExit(f"Missing handoff sources: {missing}")


def copy_files(out: Path) -> dict[str, dict[str, object]]:
    copied: dict[str, dict[str, object]] = {}
    for target, source in [*FILES.items(), *OPTIONAL_FILES.items()]:
        source_path = ROOT / source
        if target in OPTIONAL_FILES:
            if not source_path.exists() or not should_copy_optional_report(source):
                continue
        target_path = out / target
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)
        copied[target] = {
            "source": source,
            **file_info(target_path),
        }
    return copied


def copy_connected_performance_artifacts(out: Path, copied: dict[str, dict[str, object]]) -> None:
    report_path = ROOT / "build/reports/connected_performance.json"
    if not report_path.exists() or not should_copy_optional_report("build/reports/connected_performance.json"):
        return
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return
    artifacts = report.get("artifacts")
    if not isinstance(artifacts, dict):
        return
    for label, source in sorted(artifacts.items()):
        if not isinstance(label, str) or not isinstance(source, str):
            continue
        source_path = ROOT / source
        if not source_path.exists() or not source_path.is_file():
            continue
        safe_name = Path(source).name
        target = f"qa/connected_performance/artifacts/{safe_name}"
        target_path = out / target
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)
        copied[target] = {
            "source": source,
            "artifact": label,
            **file_info(target_path),
        }


def run_workspace_hygiene_qa() -> None:
    result = subprocess.run(
        ["python3", "scripts/workspace_hygiene_qa.py"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode != 0:
        print(result.stdout)
        raise SystemExit("Workspace hygiene QA failed while creating Play handoff")


def run_upload_keystore_setup(strict: bool) -> None:
    command = ["python3", "scripts/prepare_upload_keystore.py"]
    if strict:
        command.append("--strict")
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode != 0:
        print(result.stdout)
        raise SystemExit("Upload keystore setup failed while creating Play handoff")


def run_privacy_policy_hosting_qa(strict: bool, fetch_privacy_url: bool) -> None:
    command = ["python3", "scripts/privacy_policy_hosting_qa.py"]
    if strict:
        command.append("--strict")
    if fetch_privacy_url:
        command.append("--fetch-privacy-url")
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode != 0:
        print(result.stdout)
        raise SystemExit("Privacy policy hosting QA failed while creating Play handoff")


def run_play_upload_auth_qa(strict: bool) -> None:
    command = ["python3", "scripts/play_upload_auth_qa.py"]
    if strict:
        command.append("--strict")
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode != 0:
        print(result.stdout)
        raise SystemExit("Play upload auth QA failed while creating Play handoff")


def run_fastlane_runtime_qa(strict: bool) -> None:
    command = ["python3", "scripts/fastlane_runtime_qa.py"]
    if strict:
        command.append("--strict")
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode != 0:
        print(result.stdout)
        raise SystemExit("Fastlane runtime QA failed while creating Play handoff")


def run_upload_operator_runbook_qa() -> None:
    result = subprocess.run(
        ["python3", "scripts/upload_operator_runbook_qa.py"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode != 0:
        print(result.stdout)
        raise SystemExit("Upload operator runbook QA failed while creating Play handoff")


def refresh_workspace_hygiene_reports(out: Path, copied: dict[str, dict[str, object]]) -> None:
    run_workspace_hygiene_qa()
    for target, source in WORKSPACE_HYGIENE_FILES.items():
        source_path = ROOT / source
        target_path = out / target
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)
        copied[target] = {
            "source": source,
            **file_info(target_path),
        }


def should_copy_optional_report(source: str) -> bool:
    allowed_statuses = OPTIONAL_REPORT_STATUS.get(source)
    if allowed_statuses is None:
        json_source = source.removesuffix(".md") + ".json"
        allowed_statuses = OPTIONAL_REPORT_STATUS.get(json_source)
        if allowed_statuses is None:
            return True
        source = json_source
    report_path = ROOT / source
    if not report_path.exists():
        return False
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    if report.get("status") not in allowed_statuses:
        return False
    if source == "build/reports/instrumentation_smoke.json":
        return instrumentation_report_is_fresh(report, report_path)
    if source == "build/reports/connected_performance.json":
        return connected_performance_report_is_fresh(report, report_path)
    return True


def report_generated_epoch(report: dict[str, object], report_path: Path) -> float:
    generated = report.get("generatedAt")
    if isinstance(generated, str):
        try:
            return datetime.fromisoformat(generated).timestamp()
        except ValueError:
            pass
    return report_path.stat().st_mtime


def instrumentation_report_is_fresh(report: dict[str, object], report_path: Path) -> bool:
    return instrumentation_freshness_detail(report, report_path)[0]


def instrumentation_freshness_detail(report: dict[str, object], report_path: Path) -> tuple[bool, str]:
    sources: set[Path] = set()
    for pattern in OPTIONAL_INSTRUMENTATION_SOURCE_GLOBS:
        for path in ROOT.glob(pattern):
            if path.is_file():
                sources.add(path)
    if not sources:
        return False, "no androidTest source files found for freshness comparison"
    newest_source = max(sources, key=lambda path: path.stat().st_mtime)
    if report_generated_epoch(report, report_path) < newest_source.stat().st_mtime:
        return False, f"report is older than {relative(newest_source)}"
    return True, "report is fresh against androidTest source"


def connected_performance_report_is_fresh(report: dict[str, object], report_path: Path) -> bool:
    return connected_performance_freshness_detail(report, report_path)[0]


def connected_performance_freshness_detail(report: dict[str, object], report_path: Path) -> tuple[bool, str]:
    sources: set[Path] = set()
    for pattern in OPTIONAL_CONNECTED_PERFORMANCE_SOURCE_GLOBS:
        for path in ROOT.glob(pattern):
            if path.is_file():
                sources.add(path)
    if not sources:
        return False, "no app source files found for freshness comparison"
    newest_source = max(sources, key=lambda path: path.stat().st_mtime)
    if report_generated_epoch(report, report_path) < newest_source.stat().st_mtime:
        return False, f"report is older than {relative(newest_source)}"
    return True, "report is fresh against app source"


def optional_evidence_summary(copied: dict[str, dict[str, object]]) -> dict[str, object]:
    instrumentation_path = ROOT / "build/reports/instrumentation_smoke.json"
    instrumentation: dict[str, object] = {
        "status": "missing",
        "source": "build/reports/instrumentation_smoke.json",
        "detail": "instrumentation smoke report is not present in build/reports",
        "rerunCommand": INSTRUMENTATION_SMOKE_RERUN,
    }
    if instrumentation_path.exists():
        try:
            report = json.loads(instrumentation_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            instrumentation.update(
                {
                    "status": "skipped",
                    "detail": "instrumentation smoke report JSON could not be parsed",
                },
            )
        else:
            instrumentation.update(
                {
                    "reportStatus": report.get("status", ""),
                    "generatedAt": report.get("generatedAt", ""),
                    "mode": report.get("mode", ""),
                    "serial": report.get("serial", ""),
                },
            )
            allowed = OPTIONAL_REPORT_STATUS["build/reports/instrumentation_smoke.json"]
            fresh, freshness_detail = instrumentation_freshness_detail(report, instrumentation_path)
            if report.get("status") not in allowed:
                instrumentation.update(
                    {
                        "status": "skipped",
                        "detail": f"report status {report.get('status')!r} is not allowed for handoff",
                    },
                )
            elif not fresh:
                instrumentation.update({"status": "skipped", "detail": freshness_detail})
            elif "qa/instrumentation_smoke/instrumentation_smoke.json" in copied:
                instrumentation.update({"status": "included", "detail": "fresh report is copied"})
            else:
                instrumentation.update(
                    {
                        "status": "skipped",
                        "detail": "fresh report was not copied into the handoff",
                    },
                )

    connected_path = ROOT / "build/reports/connected_performance.json"
    rerun_command = "python3 scripts/connected_performance_qa.py --serial <adb-serial>"
    connected: dict[str, object] = {
        "status": "missing",
        "source": "build/reports/connected_performance.json",
        "detail": "connected performance report is not present in build/reports",
        "rerunCommand": rerun_command,
    }
    if connected_path.exists():
        try:
            report = json.loads(connected_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            connected.update(
                {
                    "status": "skipped",
                    "detail": "connected performance report JSON could not be parsed",
                },
            )
        else:
            connected.update(
                {
                    "reportStatus": report.get("status", ""),
                    "generatedAt": report.get("generatedAt", ""),
                    "flowEvidence": report.get("flowEvidence", ""),
                },
            )
            allowed = OPTIONAL_REPORT_STATUS["build/reports/connected_performance.json"]
            fresh, freshness_detail = connected_performance_freshness_detail(report, connected_path)
            if report.get("status") not in allowed:
                connected.update(
                    {
                        "status": "skipped",
                        "detail": f"report status {report.get('status')!r} is not allowed for handoff",
                    },
                )
            elif not fresh:
                connected.update({"status": "skipped", "detail": freshness_detail})
            elif "qa/connected_performance/connected_performance.json" in copied:
                connected.update({"status": "included", "detail": "fresh report and raw artifacts are copied"})
            else:
                connected.update(
                    {
                        "status": "skipped",
                        "detail": "fresh report was not copied into the handoff",
                    },
                )
    return {"instrumentationSmoke": instrumentation, "connectedPerformance": connected}


def smoke_summary_mode(summary: str) -> str:
    if "Mode: `extended`" in summary:
        return "extended"
    if "Mode: `basic`" in summary:
        return "basic"
    return "basic"


def smoke_summary_generated(summary: str, summary_path: Path) -> str:
    for line in summary.splitlines():
        if line.startswith("Generated: `") and line.endswith("`"):
            return line.removeprefix("Generated: `").removesuffix("`")
    return datetime.fromtimestamp(summary_path.stat().st_mtime).isoformat(timespec="seconds")


def smoke_generated_epoch(summary: str, summary_path: Path) -> float:
    generated = smoke_summary_generated(summary, summary_path)
    try:
        return datetime.fromisoformat(generated).timestamp()
    except ValueError:
        return summary_path.stat().st_mtime


def discover_smoke_sources() -> list[Path]:
    sources: set[Path] = set()
    for pattern in SMOKE_SOURCE_GLOBS:
        for path in ROOT.glob(pattern):
            if path.is_file():
                sources.add(path)
    return sorted(sources)


def latest_passing_smoke_dir() -> Path | None:
    smoke_root = ROOT / "build/android_smoke"
    if not smoke_root.exists():
        return None
    candidates: list[tuple[Path, str, str, float]] = []
    for directory in sorted(smoke_root.iterdir()):
        summary = directory / "summary.md"
        if not directory.is_dir() or not summary.exists():
            continue
        text = summary.read_text(encoding="utf-8")
        if "Status: PASS" in text:
            candidates.append((
                directory,
                smoke_summary_mode(text),
                smoke_summary_generated(text, summary),
                summary.stat().st_mtime,
            ))
    if not candidates:
        return None
    extended = [candidate for candidate in candidates if candidate[1] == "extended"]
    if extended:
        return max(extended, key=lambda candidate: (candidate[2], candidate[3]))[0]
    return max(candidates, key=lambda candidate: (candidate[2], candidate[3]))[0]


def copy_latest_smoke(out: Path, copied: dict[str, dict[str, object]]) -> dict[str, object]:
    smoke_dir = latest_passing_smoke_dir()
    if smoke_dir is None:
        return {
            "status": "missing",
            "detail": "No passing Android smoke evidence is available.",
            "rerunCommand": ANDROID_SMOKE_RERUN,
        }
    summary_path = smoke_dir / "summary.md"
    summary = summary_path.read_text(encoding="utf-8")
    generated_at = smoke_summary_generated(summary, summary_path)
    sources = discover_smoke_sources()
    newest_source = max(sources, key=lambda path: path.stat().st_mtime) if sources else None
    if newest_source is None:
        return {
            "status": "skipped",
            "source": smoke_dir.relative_to(ROOT).as_posix(),
            "mode": smoke_summary_mode(summary),
            "generatedAt": generated_at,
            "detail": "Android smoke freshness baseline has no app source files.",
            "rerunCommand": ANDROID_SMOKE_RERUN,
        }
    if smoke_generated_epoch(summary, summary_path) < newest_source.stat().st_mtime:
        return {
            "status": "skipped",
            "source": smoke_dir.relative_to(ROOT).as_posix(),
            "mode": smoke_summary_mode(summary),
            "generatedAt": generated_at,
            "detail": f"Latest passing Android smoke is older than app source {newest_source.relative_to(ROOT).as_posix()}.",
            "rerunCommand": ANDROID_SMOKE_RERUN,
        }
    target_root = out / "qa/android_smoke/latest"
    target_root.mkdir(parents=True, exist_ok=True)
    copied_files = 0
    for source_path in sorted(smoke_dir.iterdir()):
        if not source_path.is_file():
            continue
        target_path = target_root / source_path.name
        shutil.copy2(source_path, target_path)
        manifest_key = target_path.relative_to(out).as_posix()
        copied[manifest_key] = {
            "source": source_path.relative_to(ROOT).as_posix(),
            **file_info(target_path),
        }
        copied_files += 1
    return {
        "status": "included",
        "source": smoke_dir.relative_to(ROOT).as_posix(),
        "target": target_root.relative_to(out).as_posix(),
        "files": copied_files,
        "mode": smoke_summary_mode(summary),
        "generatedAt": generated_at,
    }


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8").strip()


def release_gate_summary() -> dict[str, object]:
    if not RELEASE_GATE_REPORT.exists():
        return {
            "status": "missing",
            "source": "build/reports/release_gate.json",
            "target": "qa/release_gate/release_gate.json",
            "detail": "release gate report is missing",
        }
    try:
        report = json.loads(RELEASE_GATE_REPORT.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {
            "status": "invalid",
            "source": "build/reports/release_gate.json",
            "target": "qa/release_gate/release_gate.json",
            "detail": "release gate report JSON could not be parsed",
        }
    checks = report.get("checks")
    blockers = report.get("externalBlockers")
    return {
        "status": report.get("status", ""),
        "source": "build/reports/release_gate.json",
        "target": "qa/release_gate/release_gate.json",
        "generatedAt": report.get("generatedAt", ""),
        "command": report.get("command", []),
        "checkCount": len(checks) if isinstance(checks, list) else 0,
        "externalBlockerCount": len(blockers) if isinstance(blockers, list) else 0,
    }


def add_generated_file(
    out: Path,
    copied: dict[str, dict[str, object]],
    target: str,
    content: str,
    source: str,
) -> None:
    target_path = out / target
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(content, encoding="utf-8")
    copied[target] = {
        "source": source,
        **file_info(target_path),
    }


def write_next_actions(
    out: Path,
    copied: dict[str, dict[str, object]],
    signing: dict[str, object],
    smoke_evidence: dict[str, object],
    optional_evidence: dict[str, object],
) -> None:
    report_path = ROOT / "build/reports/pre_upload_blockers.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    groups = [
        group for group in report.get("blockerGroups", [])
        if isinstance(group, dict) and group.get("status") == "EXTERNAL_BLOCKER"
    ]
    lines = [
        "# Next Actions",
        "",
        "This file is generated for the Play Console operator. Resolve these items before uploading the AAB.",
        "",
        f"- Signing state: `{signing['status']}` - {signing['detail']}",
        f"- Pre-upload blocker status: `{report.get('status', 'UNKNOWN')}`",
        "",
    ]
    if groups:
        lines.append("## Required Before Play Upload")
        for index, group in enumerate(groups, start=1):
            title = str(group.get("title", "External action"))
            action = str(group.get("action", "Resolve this external blocker."))
            strict_command = str(group.get("strictCommand", "python3 scripts/pre_upload_blockers_qa.py --strict"))
            lines.extend(
                [
                    "",
                    f"{index}. {title}",
                    f"   - Action: {action}",
                    f"   - Verify: `{strict_command}`",
                ],
            )
    else:
        lines.extend(["## Required Before Play Upload", "", "No external blockers are listed in the latest report."])

    if smoke_evidence.get("status") != "included":
        lines.extend(
            [
                "",
                "## Connected Smoke To Refresh",
                "",
                "Connected Android smoke evidence is not included in this handoff.",
                f"- Status: `{smoke_evidence.get('status', 'unknown')}`",
                f"- Detail: {smoke_evidence.get('detail', 'No detail recorded.')}",
                f"- Refresh: `{smoke_evidence.get('rerunCommand', ANDROID_SMOKE_RERUN)}`",
            ],
        )

    instrumentation = optional_evidence.get("instrumentationSmoke")
    if isinstance(instrumentation, dict) and instrumentation.get("status") != "included":
        lines.extend(
            [
                "",
                "## Instrumentation Smoke To Refresh",
                "",
                "Compose instrumentation smoke evidence is not included in this handoff.",
                f"- Status: `{instrumentation.get('status', 'unknown')}`",
                f"- Detail: {instrumentation.get('detail', 'No detail recorded.')}",
                f"- Refresh: `{instrumentation.get('rerunCommand', INSTRUMENTATION_SMOKE_RERUN)}`",
            ],
        )

    connected_perf = optional_evidence.get("connectedPerformance")
    if isinstance(connected_perf, dict) and connected_perf.get("status") != "included":
        lines.extend(
            [
                "",
                "## Optional Evidence To Refresh",
                "",
                "Connected performance evidence is not included in this handoff.",
                f"- Status: `{connected_perf.get('status', 'unknown')}`",
                f"- Detail: {connected_perf.get('detail', 'No detail recorded.')}",
                f"- Refresh: `{connected_perf.get('rerunCommand', 'python3 scripts/connected_performance_qa.py --serial <adb-serial>')}`",
            ],
        )

    lines.extend(
        [
            "",
            "## Final Gate",
            "After the items above pass, rebuild this handoff from the upload machine:",
            "",
            "```bash",
            "python3 scripts/pre_upload_blockers_qa.py --strict",
            "python3 scripts/package_release_candidate.py --strict-signing --fetch-privacy-url --fetch-target-api-policy --strict-screenshots --strict-physical-device --strict-pre-upload",
            "python3 scripts/post_package_validation_qa.py",
            "```",
            "",
            "Upload `upload/app-release.aab` only when `manifest.json` reports `signing.status = signed`.",
        ],
    )
    add_generated_file(
        out=out,
        copied=copied,
        target="NEXT_ACTIONS.md",
        content="\n".join(lines) + "\n",
        source="generated from build/reports/pre_upload_blockers.json",
    )


def write_checksums(out: Path, copied: dict[str, dict[str, object]]) -> None:
    lines = [
        f"{info['sha256']}  {relative_path}"
        for relative_path, info in sorted(copied.items())
        if relative_path != "CHECKSUMS.txt" and isinstance(info.get("sha256"), str)
    ]
    add_generated_file(
        out=out,
        copied=copied,
        target="CHECKSUMS.txt",
        content="\n".join(lines) + "\n",
        source="generated from handoff manifest file checksums",
    )


def write_readme(out: Path, copied: dict[str, dict[str, object]], signing: dict[str, object]) -> None:
    warning = ""
    if signing["status"] != "signed":
        warning = (
            "\nIMPORTANT: upload/app-release.aab is not upload-ready. "
            "Configure signing env vars and rerun `python3 scripts/release_gate.py --strict-signing`.\n"
        )
    content = f"""# Шаурма 58 Play Handoff

Generated from the local workspace for the v1.0.0 internal-test upload.
{warning}
## Use
1. Read `NEXT_ACTIONS.md` first; it is the short operator checklist generated from the latest pre-upload blocker report.
2. Verify file integrity from the handoff root with `shasum -a 256 -c CHECKSUMS.txt`.
3. Upload `upload/app-release.aab` only after `manifest.json` reports `signing.status = signed`.
4. Copy ru-RU listing text from `metadata/ru-RU/`.
5. For automated upload tooling, use the ready layout under `fastlane/metadata/android/ru-RU/images/`.
6. For manual upload, use `graphics/play_icon.png`, `graphics/feature_graphic_concept.png` and screenshots from `graphics/screenshots/` in filename order.
7. Review `qa/asset/asset.md`; runtime ImageGen assets, launcher icons and screenshots must have expected dimensions/alpha.
8. Review `docs/asset_manifest.md`, `docs/rejected_assets.md` and `qa/asset_manifest/asset_manifest.md`; accepted ImageGen/runtime/store assets must be documented and rejected variants must stay out of release paths.
9. Review `qa/fastlane_assets/fastlane_assets.md`; every listed fastlane image must match the curated store source.
10. Review `qa/content_copy/content_copy.md`; app, listing and policy copy must have no placeholder/dev wording and required Russian microcopy must be present.
11. Review `qa/fastlane_config/fastlane_config.md`; lanes must remain internal-track draft uploads with validate-only support.
12. Review `qa/ui_behavior/ui_behavior.md`; UI behavior wiring and Russian gameplay copy must be `PASS`.
13. Review `qa/accessibility_source/accessibility_source.md`; custom controls must keep 48dp+ targets and TalkBack labels/states.
14. Review `qa/completion_audit/completion_audit.md`; the release scope evidence must be `PASS` before upload.
15. Review `qa/store_visual_quality/store_visual_quality.md`; upload screenshots must be real, readable and visually distinct.
16. Review `qa/store_screenshot_freshness/store_screenshot_freshness.md`; `PASS_WITH_WARNINGS` means screenshots must be recaptured before final Play upload.
17. Review `qa/store_screenshot_capture/store_screenshot_capture.md`; it proves the current store screenshots match the latest real app capture evidence by SHA-256.
18. Review `qa/play_metadata/play_metadata.md`; Play listing lengths, privacy terms and store image dimensions must be `PASS`.
19. Review `qa/play_console_forms/play_console_forms.md`; Play Console answer coverage must be `PASS` before copying form answers.
20. Review `qa/play_target_api/play_target_api.md`; targetSdk must satisfy the current Google Play mobile submission baseline before upload.
21. Review `qa/play_upload_auth/play_upload_auth.md`; final upload machines must set `SUPPLY_JSON_KEY` to a service-account JSON outside the repo.
22. Review `qa/privacy_policy_hosting/privacy_policy_hosting.md`; final upload handoffs should be generated with `--fetch-privacy-url` after the public HTTPS policy URL is set.
23. Review `qa/fastlane_runtime/fastlane_runtime.md`; final fastlane machines must pass Ruby headers, `bundle check` and `bundle exec fastlane --version`.
24. Review `qa/play_external_readiness/play_external_readiness.md`; unsigned local handoffs can show `EXTERNAL_BLOCKER`, but final upload must pass `python3 scripts/play_external_readiness_qa.py --strict --fetch-privacy-url`.
25. Host `privacy/hosting/privacy_policy.html` at a public HTTPS URL; verify the SHA-256 in `privacy/hosting/manifest.json` before upload.
26. Fill Play Console forms from `docs/play_console_answers.md`.
27. Review `docs/upload_operator_runbook.md` and `qa/upload_operator_runbook/upload_operator_runbook.md`; the final upload machine should follow that runbook exactly.
28. Review `qa/android_smoke/latest/summary.md` if present; rerun `docs/android_emulator_smoke.md` when app code or assets change.
29. Review `qa/signing_env/signing_env.md`; in unsigned local handoffs it may report `EXTERNAL_BLOCKER`, but partial env or workspace keystores are `FAIL`.
30. Review `qa/upload_keystore_setup/upload_keystore_setup.md`; final signing machines must have a keystore outside the repo and matching `SHAWARMA58_KEYSTORE*` env vars.
31. Review `qa/workspace_hygiene/workspace_hygiene.md`; local caches and upload-secret-like files must stay out of source and handoff paths.
32. Review `qa/privacy_data_safety/privacy_data_safety.md`; every privacy/data-safety check must be `PASS`.
33. Review `qa/artifact_provenance/artifact_provenance.md` before upload; it should only report signing as an external blocker in unsigned local environments.
34. Keep `deobfuscation/release/` with the release record; `mapping.txt` must match the uploaded AAB.
35. Review `qa/performance_budget/performance_budget.md`; every budget check must be `PASS`.
36. Review `qa/physical_device_readiness/physical_device_readiness.md`; local emulator-only handoffs can show `EXTERNAL_BLOCKER`, but production rollout needs a real phone pass.
37. Review `qa/pre_upload_blockers/pre_upload_blockers.md`; it consolidates signing, privacy URL, Play service-account, fastlane runtime and physical-device blockers into operator actions.
38. Review `qa/release_gate/release_gate.md`; local handoffs can show `EXTERNAL_BLOCKER`, but final upload-machine gates must have no `FAIL` checks.
39. Review `qa/connected_performance/connected_performance.md` and `qa/connected_performance/artifacts/` if present; `WARN` frame diagnostics on emulator are non-blocking, `FAIL` is blocking.
40. Review `qa/instrumentation_smoke/instrumentation_smoke.md` if present; rerun `python3 scripts/instrumentation_smoke_qa.py --require-device` after UI changes.
41. Run `docs/physical_device_sanity.md` on a real device after internal testing is available.

## Signing State
`{signing["status"]}`: {signing["detail"]}
"""
    add_generated_file(
        out=out,
        copied=copied,
        target="README.md",
        content=content,
        source="generated handoff README",
    )


def create_manifest(
    out: Path,
    copied: dict[str, dict[str, object]],
    signing: dict[str, object],
    smoke_evidence: dict[str, object] | None,
    optional_evidence: dict[str, object],
) -> dict[str, object]:
    manifest = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "project": "Шаурма 58",
        "packageName": "com.andrejivliev.shawarma58",
        "versionCode": 1,
        "versionName": "1.0.0",
        "defaultLanguage": "ru-RU",
        "signing": signing,
        "releaseGate": release_gate_summary(),
        "connectedSmoke": smoke_evidence,
        "optionalEvidence": optional_evidence,
        "metadataLengths": {
            "title": len(read_text("fastlane/metadata/android/ru-RU/title.txt")),
            "shortDescription": len(read_text("fastlane/metadata/android/ru-RU/short_description.txt")),
            "fullDescription": len(read_text("fastlane/metadata/android/ru-RU/full_description.txt")),
            "releaseNotes": len(read_text("fastlane/metadata/android/ru-RU/changelogs/1.txt")),
        },
        "files": copied,
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        default=str(DEFAULT_OUT),
        help="output directory under build/",
    )
    parser.add_argument(
        "--strict-signing",
        action="store_true",
        help="fail unless the copied AAB signature verifies",
    )
    parser.add_argument(
        "--fetch-privacy-url",
        action="store_true",
        help="fetch and inspect SHAWARMA58_PRIVACY_POLICY_URL in privacy policy hosting QA",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="print only the output path",
    )
    args = parser.parse_args()

    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    ensure_output_path(out)
    run_upload_keystore_setup(strict=args.strict_signing)
    run_play_upload_auth_qa(strict=args.strict_signing)
    run_privacy_policy_hosting_qa(
        strict=args.strict_signing,
        fetch_privacy_url=args.fetch_privacy_url,
    )
    run_fastlane_runtime_qa(strict=args.strict_signing)
    run_upload_operator_runbook_qa()
    validate_sources()

    signing = signing_status()
    if args.strict_signing and signing["status"] != "signed":
        raise SystemExit(f"AAB signing is not ready: {signing['detail']}")

    reset_output_path(out)
    run_workspace_hygiene_qa()

    copied = copy_files(out)
    copy_connected_performance_artifacts(out, copied)
    optional_evidence = optional_evidence_summary(copied)
    smoke_evidence = copy_latest_smoke(out, copied)
    write_readme(out, copied, signing)
    write_next_actions(out, copied, signing, smoke_evidence, optional_evidence)
    manifest = create_manifest(out, copied, signing, smoke_evidence, optional_evidence)
    refresh_workspace_hygiene_reports(out, copied)
    write_checksums(out, copied)
    manifest = create_manifest(out, copied, signing, smoke_evidence, optional_evidence)

    if args.quiet:
        print(relative(out))
        return

    print(f"Play handoff bundle: {relative(out)}")
    print(f"Signing: {manifest['signing']['status']} ({manifest['signing']['detail']})")
    print(f"Files copied: {len(copied)}")
    if smoke_evidence.get("status") == "included":
        print(f"Connected smoke: {smoke_evidence['source']} -> {smoke_evidence['target']}")
    else:
        print(f"Connected smoke: {smoke_evidence.get('status', 'unknown')} ({smoke_evidence.get('detail', 'no detail')})")
    print(f"Manifest: {relative(out / 'manifest.json')}")


if __name__ == "__main__":
    main()
