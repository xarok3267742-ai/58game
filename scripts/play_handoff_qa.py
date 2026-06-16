#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
from datetime import datetime
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HANDOFF = ROOT / "build/play_handoff/shawarma58-v1.0.0"
CREATE_HANDOFF_SCRIPT = ROOT / "scripts/create_play_handoff.py"
REPORT_MD = ROOT / "build/reports/play_handoff_qa.md"
REPORT_JSON = ROOT / "build/reports/play_handoff_qa.json"
SECRET_SUFFIXES = {".jks", ".keystore", ".p12", ".pem"}
REQUIRED_UPLOAD_OPERATOR_ENV = {
    "SHAWARMA58_KEYSTORE",
    "SHAWARMA58_KEYSTORE_PASSWORD",
    "SHAWARMA58_KEY_ALIAS",
    "SHAWARMA58_KEY_PASSWORD",
    "SUPPLY_JSON_KEY",
    "SHAWARMA58_PRIVACY_POLICY_URL",
}
REQUIRED_UPLOAD_OPERATOR_COMMANDS = {
    "python3 scripts/pre_upload_blockers_qa.py --strict",
    "python3 scripts/package_release_candidate.py --strict-signing --fetch-privacy-url --fetch-target-api-policy --strict-screenshots --strict-physical-device --strict-pre-upload",
    "python3 scripts/post_package_validation_qa.py",
    "bundle exec fastlane android validate_internal",
}
EXPECTED_IMAGE_SIZES = {
    "graphics/play_icon.png": (512, 512),
    "graphics/feature_graphic_concept.png": (1024, 500),
    "graphics/screenshots/01_onboarding.png": (1080, 2400),
    "graphics/screenshots/02_menu.png": (1080, 2400),
    "graphics/screenshots/03_levels.png": (1080, 2400),
    "graphics/screenshots/04_gameplay.png": (1080, 2400),
    "graphics/screenshots/05_result.png": (1080, 2400),
    "fastlane/metadata/android/ru-RU/images/icon.png": (512, 512),
    "fastlane/metadata/android/ru-RU/images/featureGraphic.png": (1024, 500),
    "fastlane/metadata/android/ru-RU/images/phoneScreenshots/01_onboarding.png": (1080, 2400),
    "fastlane/metadata/android/ru-RU/images/phoneScreenshots/02_menu.png": (1080, 2400),
    "fastlane/metadata/android/ru-RU/images/phoneScreenshots/03_levels.png": (1080, 2400),
    "fastlane/metadata/android/ru-RU/images/phoneScreenshots/04_gameplay.png": (1080, 2400),
    "fastlane/metadata/android/ru-RU/images/phoneScreenshots/05_result.png": (1080, 2400),
    "qa/screenshots/wrong_order.png": (1080, 2400),
    "qa/screenshots/endless_result.png": (1080, 2400),
}
REQUIRED_FILES = [
    "README.md",
    "NEXT_ACTIONS.md",
    "CHECKSUMS.txt",
    "upload/app-release.aab",
    "debug/app-debug.apk",
    "metadata/ru-RU/title.txt",
    "metadata/ru-RU/short_description.txt",
    "metadata/ru-RU/full_description.txt",
    "metadata/ru-RU/changelogs/1.txt",
    "fastlane/Appfile",
    "fastlane/Fastfile",
    "fastlane/README.md",
    "Gemfile",
    "Gemfile.lock",
    "graphics/play_icon.png",
    "graphics/feature_graphic_concept.png",
    "fastlane/metadata/android/ru-RU/images/icon.png",
    "fastlane/metadata/android/ru-RU/images/featureGraphic.png",
    "fastlane/metadata/android/ru-RU/images/phoneScreenshots/01_onboarding.png",
    "fastlane/metadata/android/ru-RU/images/phoneScreenshots/02_menu.png",
    "fastlane/metadata/android/ru-RU/images/phoneScreenshots/03_levels.png",
    "fastlane/metadata/android/ru-RU/images/phoneScreenshots/04_gameplay.png",
    "fastlane/metadata/android/ru-RU/images/phoneScreenshots/05_result.png",
    "privacy/privacy_policy.html",
    "privacy/hosting/README.md",
    "privacy/hosting/manifest.json",
    "privacy/hosting/privacy_policy.html",
    "docs/play_upload_packet.md",
    "docs/play_console_answers.md",
    "docs/asset_manifest.md",
    "docs/rejected_assets.md",
    "docs/fastlane_upload.md",
    "docs/deobfuscation_notes.md",
    "docs/google_play_checklist.md",
    "docs/qa_test_plan.md",
    "docs/android_emulator_smoke.md",
    "docs/physical_device_sanity.md",
    "docs/upload_operator_runbook.md",
    "docs/release_plan.md",
    "docs/completion_audit.md",
    "qa/asset_manifest/asset_manifest.md",
    "qa/asset_manifest/asset_manifest.json",
    "qa/content_copy/content_copy.md",
    "qa/content_copy/content_copy.json",
    "qa/accessibility_source/accessibility_source.md",
    "qa/accessibility_source/accessibility_source.json",
    "qa/fastlane_assets/fastlane_assets.md",
    "qa/fastlane_assets/fastlane_assets.json",
    "qa/fastlane_config/fastlane_config.md",
    "qa/fastlane_config/fastlane_config.json",
    "qa/fastlane_runtime/fastlane_runtime.md",
    "qa/fastlane_runtime/fastlane_runtime.json",
    "qa/store_visual_quality/store_visual_quality.md",
    "qa/store_visual_quality/store_visual_quality.json",
    "qa/store_screenshot_capture_guard/store_screenshot_capture_guard.md",
    "qa/store_screenshot_capture_guard/store_screenshot_capture_guard.json",
    "qa/store_screenshot_freshness/store_screenshot_freshness.md",
    "qa/store_screenshot_freshness/store_screenshot_freshness.json",
    "qa/store_screenshot_capture/store_screenshot_capture.md",
    "qa/store_screenshot_capture/store_screenshot_capture.json",
    "qa/play_external_readiness/play_external_readiness.md",
    "qa/play_external_readiness/play_external_readiness.json",
    "qa/play_upload_packet/play_upload_packet.md",
    "qa/play_upload_packet/play_upload_packet.json",
    "qa/play_upload_auth/play_upload_auth.md",
    "qa/play_upload_auth/play_upload_auth.json",
    "qa/play_console_forms/play_console_forms.md",
    "qa/play_console_forms/play_console_forms.json",
    "qa/play_target_api/play_target_api.md",
    "qa/play_target_api/play_target_api.json",
    "qa/privacy_policy_hosting/privacy_policy_hosting.md",
    "qa/privacy_policy_hosting/privacy_policy_hosting.json",
    "qa/signing_env/signing_env.md",
    "qa/signing_env/signing_env.json",
    "qa/upload_keystore_setup/upload_keystore_setup.md",
    "qa/upload_keystore_setup/upload_keystore_setup.json",
    "qa/upload_operator_runbook/upload_operator_runbook.md",
    "qa/upload_operator_runbook/upload_operator_runbook.json",
    "qa/workspace_hygiene/workspace_hygiene.md",
    "qa/workspace_hygiene/workspace_hygiene.json",
    "qa/privacy_data_safety/privacy_data_safety.md",
    "qa/privacy_data_safety/privacy_data_safety.json",
    "qa/artifact_provenance/artifact_provenance.md",
    "qa/artifact_provenance/artifact_provenance.json",
    "qa/performance_budget/performance_budget.md",
    "qa/performance_budget/performance_budget.json",
    "qa/physical_device_readiness/physical_device_readiness.md",
    "qa/physical_device_readiness/physical_device_readiness.json",
    "qa/pre_upload_blockers/pre_upload_blockers.md",
    "qa/pre_upload_blockers/pre_upload_blockers.json",
    "qa/release_gate/release_gate.md",
    "qa/release_gate/release_gate.json",
    "deobfuscation/release/configuration.txt",
    "deobfuscation/release/mapping.txt",
    "deobfuscation/release/resources.txt",
    "deobfuscation/release/seeds.txt",
    "deobfuscation/release/usage.txt",
]
DEOBFUSCATION_FILES = {
    "deobfuscation/release/configuration.txt": "app/build/outputs/mapping/release/configuration.txt",
    "deobfuscation/release/mapping.txt": "app/build/outputs/mapping/release/mapping.txt",
    "deobfuscation/release/resources.txt": "app/build/outputs/mapping/release/resources.txt",
    "deobfuscation/release/seeds.txt": "app/build/outputs/mapping/release/seeds.txt",
    "deobfuscation/release/usage.txt": "app/build/outputs/mapping/release/usage.txt",
}
UPLOAD_VISUAL_PATHS = {
    "fastlane/metadata/android/ru-RU/images/phoneScreenshots/01_onboarding.png",
    "fastlane/metadata/android/ru-RU/images/phoneScreenshots/02_menu.png",
    "fastlane/metadata/android/ru-RU/images/phoneScreenshots/03_levels.png",
    "fastlane/metadata/android/ru-RU/images/phoneScreenshots/04_gameplay.png",
    "fastlane/metadata/android/ru-RU/images/phoneScreenshots/05_result.png",
}
UPLOAD_SCREENSHOT_HANDOFF_PATHS = {
    "store/screenshots/shawarma_onboarding.png": "fastlane/metadata/android/ru-RU/images/phoneScreenshots/01_onboarding.png",
    "store/screenshots/shawarma_menu.png": "fastlane/metadata/android/ru-RU/images/phoneScreenshots/02_menu.png",
    "store/screenshots/shawarma_levels.png": "fastlane/metadata/android/ru-RU/images/phoneScreenshots/03_levels.png",
    "store/screenshots/shawarma_gameplay.png": "fastlane/metadata/android/ru-RU/images/phoneScreenshots/04_gameplay.png",
    "store/screenshots/shawarma_result.png": "fastlane/metadata/android/ru-RU/images/phoneScreenshots/05_result.png",
}
QA_SCREENSHOT_HANDOFF_PATHS = {
    "store/screenshots/shawarma_wrong_order.png": "qa/screenshots/wrong_order.png",
    "store/screenshots/shawarma_endless_result.png": "qa/screenshots/endless_result.png",
}
STORE_SCREENSHOT_HANDOFF_PATHS = {
    **UPLOAD_SCREENSHOT_HANDOFF_PATHS,
    **QA_SCREENSHOT_HANDOFF_PATHS,
}
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
ANDROID_TEST_SOURCE_GLOBS = [
    "app/src/androidTest/**/*.kt",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def mandatory_handoff_copy_targets() -> list[str]:
    spec = importlib.util.spec_from_file_location(
        "create_play_handoff_for_qa",
        CREATE_HANDOFF_SCRIPT,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {CREATE_HANDOFF_SCRIPT.relative_to(ROOT)}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    files = getattr(module, "FILES", None)
    if not isinstance(files, dict):
        raise RuntimeError("create_play_handoff.FILES is not a dict")
    return sorted(target for target in files if isinstance(target, str))


def verify_copy_map_manifest_coverage(files: dict[str, object], errors: list[str]) -> None:
    try:
        required_targets = mandatory_handoff_copy_targets()
    except Exception as exc:
        errors.append(f"copy map manifest coverage check failed: {exc}")
        return
    missing = [target for target in required_targets if target not in files]
    if missing:
        errors.append(f"manifest is missing copy-map target(s): {missing}")


def write_report(
    *,
    handoff: Path,
    files: dict[str, object],
    errors: list[str],
    allow_basic_smoke: bool,
) -> None:
    try:
        copy_targets = mandatory_handoff_copy_targets()
    except Exception:
        copy_targets = []
    manifest_files = set(files)
    missing_copy_targets = [target for target in copy_targets if target not in manifest_files]
    status = "FAIL" if errors else "PASS"
    payload = {
        "generatedAt": datetime.now().astimezone().replace(microsecond=0).isoformat(),
        "status": status,
        "handoff": handoff.relative_to(ROOT).as_posix(),
        "manifestFileCount": len(files),
        "requiredFileCount": len(REQUIRED_FILES),
        "copyMapTargetCount": len(copy_targets),
        "copyMapMissingInManifest": missing_copy_targets,
        "allowBasicSmoke": allow_basic_smoke,
        "errors": errors,
    }
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Play Handoff QA",
        "",
        f"Generated: {payload['generatedAt']}",
        f"Status: `{status}`",
        f"Handoff: `{payload['handoff']}`",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Manifest files | `{payload['manifestFileCount']}` |",
        f"| Manual required files | `{payload['requiredFileCount']}` |",
        f"| Copy-map targets | `{payload['copyMapTargetCount']}` |",
        f"| Missing copy-map targets | `{len(missing_copy_targets)}` |",
        f"| Allow basic smoke | `{str(allow_basic_smoke).lower()}` |",
    ]
    if errors:
        lines.extend(["", "## Errors"])
        lines.extend(f"- {error}" for error in errors)
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def verify_source_parity(
    *,
    handoff: Path,
    files: dict[object, object],
    errors: list[str],
    handoff_relative: str,
    expected_source: str,
    label: str,
) -> None:
    source_path = ROOT / expected_source
    handoff_path = handoff / handoff_relative
    manifest_entry = files.get(handoff_relative)

    if not source_path.exists() or not source_path.is_file():
        errors.append(f"{label} source file is missing: {expected_source}")
        return
    if not handoff_path.exists() or not handoff_path.is_file():
        errors.append(f"{label} handoff file is missing: {handoff_relative}")
        return
    if not isinstance(manifest_entry, dict):
        errors.append(f"{label} missing from manifest: {handoff_relative}")
        return
    if manifest_entry.get("source") != expected_source:
        errors.append(
            f"{label} manifest source mismatch for {handoff_relative}: "
            f"expected {expected_source}, got {manifest_entry.get('source')!r}",
        )

    source_sha = sha256(source_path)
    handoff_sha = sha256(handoff_path)
    if source_sha != handoff_sha or manifest_entry.get("sha256") != source_sha:
        errors.append(f"{label} checksum mismatch against current source: {handoff_relative}")
    source_size = source_path.stat().st_size
    handoff_size = handoff_path.stat().st_size
    if source_size != handoff_size or manifest_entry.get("bytes") != source_size:
        errors.append(f"{label} byte-size mismatch against current source: {handoff_relative}")


def verify_manifest_source_parity(
    *,
    handoff: Path,
    files: dict[object, object],
    errors: list[str],
) -> None:
    root_resolved = ROOT.resolve()
    for raw_relative, raw_info in sorted(files.items(), key=lambda item: str(item[0])):
        relative = str(raw_relative)
        if not isinstance(raw_info, dict):
            continue
        source = raw_info.get("source")
        if not isinstance(source, str):
            errors.append(f"manifest entry missing source: {relative}")
            continue
        if source.startswith("generated"):
            continue
        source_path = ROOT / source
        try:
            source_resolved = source_path.resolve()
        except OSError:
            errors.append(f"manifest source cannot be resolved: {relative} -> {source}")
            continue
        if root_resolved != source_resolved and root_resolved not in source_resolved.parents:
            errors.append(f"manifest source escapes workspace: {relative} -> {source}")
            continue
        if not source_path.exists() or not source_path.is_file():
            errors.append(f"manifest source file is missing: {relative} -> {source}")
            continue
        verify_source_parity(
            handoff=handoff,
            files=files,
            errors=errors,
            handoff_relative=relative,
            expected_source=source,
            label="manifest source parity",
        )


def load_manifest(handoff: Path) -> dict[str, object]:
    manifest_path = handoff / "manifest.json"
    if not manifest_path.exists():
        raise AssertionError(f"missing manifest: {manifest_path}")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def parse_checksums(path: Path) -> tuple[dict[str, str], list[str]]:
    entries: dict[str, str] = {}
    errors: list[str] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw_line.strip():
            continue
        digest, separator, relative = raw_line.partition("  ")
        if separator != "  " or not relative:
            errors.append(f"CHECKSUMS.txt line {line_number} must use '<sha256>  <path>'")
            continue
        if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
            errors.append(f"CHECKSUMS.txt line {line_number} has invalid SHA-256")
            continue
        if relative in entries:
            errors.append(f"CHECKSUMS.txt duplicates path: {relative}")
            continue
        entries[relative] = digest
    return entries, errors


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


def latest_passing_smoke_dir(allow_basic: bool) -> Path | None:
    smoke_root = ROOT / "build/android_smoke"
    if not smoke_root.exists():
        return None
    candidates: list[tuple[Path, str, str, float]] = []
    for directory in sorted(smoke_root.iterdir()):
        summary = directory / "summary.md"
        if not directory.is_dir() or not summary.exists():
            continue
        text = summary.read_text(encoding="utf-8")
        if "Status: PASS" not in text:
            continue
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
    if allow_basic:
        return max(candidates, key=lambda candidate: (candidate[2], candidate[3]))[0]
    return None


def discover_smoke_sources() -> list[Path]:
    sources: set[Path] = set()
    for pattern in SMOKE_SOURCE_GLOBS:
        for path in ROOT.glob(pattern):
            if path.is_file():
                sources.add(path)
    return sorted(sources)


def smoke_generated_epoch(summary: str, summary_path: Path) -> float:
    generated = smoke_summary_generated(summary, summary_path)
    try:
        return datetime.fromisoformat(generated).timestamp()
    except ValueError:
        return summary_path.stat().st_mtime


def discover_android_test_sources() -> list[Path]:
    sources: set[Path] = set()
    for pattern in ANDROID_TEST_SOURCE_GLOBS:
        for path in ROOT.glob(pattern):
            if path.is_file():
                sources.add(path)
    return sorted(sources)


def report_generated_epoch(report: dict[str, object], fallback_path: Path) -> float:
    generated = report.get("generatedAt")
    if isinstance(generated, str):
        try:
            return datetime.fromisoformat(generated).timestamp()
        except ValueError:
            pass
    return fallback_path.stat().st_mtime


def expected_android_test_count(sources: list[Path]) -> int:
    return sum(
        len(re.findall(r"(?m)^\s*@Test\b", path.read_text(encoding="utf-8")))
        for path in sources
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--handoff", default=str(DEFAULT_HANDOFF), help="handoff directory")
    parser.add_argument("--allow-basic-smoke", action="store_true", help="do not require extended smoke evidence")
    args = parser.parse_args()

    handoff = Path(args.handoff)
    if not handoff.is_absolute():
        handoff = ROOT / handoff
    manifest = load_manifest(handoff)
    files = manifest.get("files")
    if not isinstance(files, dict):
        raise AssertionError("manifest.files must be an object")

    errors: list[str] = []
    for relative in REQUIRED_FILES:
        if relative not in files:
            errors.append(f"manifest is missing required file entry: {relative}")
    verify_copy_map_manifest_coverage(files, errors)

    checksums_path = handoff / "CHECKSUMS.txt"
    if checksums_path.exists():
        checksum_entries, checksum_errors = parse_checksums(checksums_path)
        errors.extend(checksum_errors)
        expected_entries = {
            relative: str(info.get("sha256"))
            for relative, info in files.items()
            if relative != "CHECKSUMS.txt" and isinstance(info, dict) and isinstance(info.get("sha256"), str)
        }
        if checksum_entries != expected_entries:
            missing = sorted(set(expected_entries) - set(checksum_entries))
            extra = sorted(set(checksum_entries) - set(expected_entries))
            mismatched = sorted(
                relative
                for relative in set(checksum_entries) & set(expected_entries)
                if checksum_entries[relative] != expected_entries[relative]
            )
            errors.append(
                "CHECKSUMS.txt does not match manifest file checksums; "
                f"missing={missing}, extra={extra}, mismatched={mismatched}",
            )
        for relative, digest in checksum_entries.items():
            path = handoff / relative
            if path.exists() and sha256(path) != digest:
                errors.append(f"CHECKSUMS.txt digest does not match file bytes: {relative}")
    else:
        errors.append("CHECKSUMS.txt missing from handoff root")

    for relative in files:
        if Path(str(relative)).suffix.lower() in SECRET_SUFFIXES:
            errors.append(f"handoff manifest contains forbidden secret-like file: {relative}")

    for relative, info in files.items():
        if not isinstance(info, dict):
            errors.append(f"manifest entry is not an object: {relative}")
            continue
        path = handoff / relative
        if not path.exists():
            errors.append(f"manifest file missing on disk: {relative}")
            continue
        expected_sha = info.get("sha256")
        actual_sha = sha256(path)
        if expected_sha != actual_sha:
            errors.append(f"sha mismatch for {relative}")
        expected_bytes = info.get("bytes")
        if expected_bytes != path.stat().st_size:
            errors.append(f"size mismatch for {relative}")

    verify_manifest_source_parity(handoff=handoff, files=files, errors=errors)

    for relative, expected_size in EXPECTED_IMAGE_SIZES.items():
        path = handoff / relative
        if path.exists() and Image.open(path).size != expected_size:
            errors.append(f"{relative} expected {expected_size}, got {Image.open(path).size}")

    source_aab = ROOT / "app/build/outputs/bundle/release/app-release.aab"
    upload_info = files.get("upload/app-release.aab")
    if source_aab.exists() and isinstance(upload_info, dict):
        if upload_info.get("sha256") != sha256(source_aab):
            errors.append("handoff AAB checksum does not match current app-release.aab")

    rejected_doc = handoff / "docs/rejected_assets.md"
    if rejected_doc.exists():
        rejected_names = [
            Path(part).name
            for part in rejected_doc.read_text(encoding="utf-8").split("`")[1::2]
            if part.startswith("store/rejected_assets/")
        ]
        for rejected_name in rejected_names:
            hits = [relative for relative in files if Path(str(relative)).name == rejected_name]
            if hits:
                errors.append(f"handoff contains rejected asset {rejected_name}: {hits}")
    else:
        errors.append("handoff rejected assets doc missing")

    for handoff_relative, source_relative in DEOBFUSCATION_FILES.items():
        source_path = ROOT / source_relative
        handoff_path = handoff / handoff_relative
        if not source_path.exists():
            errors.append(f"current deobfuscation source is missing: {source_relative}")
            continue
        if not handoff_path.exists():
            errors.append(f"handoff deobfuscation file is missing: {handoff_relative}")
            continue
        if handoff_path.stat().st_size == 0:
            errors.append(f"handoff deobfuscation file is empty: {handoff_relative}")
        if sha256(handoff_path) != sha256(source_path):
            errors.append(f"handoff deobfuscation checksum does not match current output: {handoff_relative}")

    signing_env_path = handoff / "qa/signing_env/signing_env.json"
    if signing_env_path.exists():
        signing_env = json.loads(signing_env_path.read_text(encoding="utf-8"))
        checks = signing_env.get("checks")
        if not isinstance(checks, list):
            errors.append("signing env checks must be a list")
        else:
            failed = [check for check in checks if isinstance(check, dict) and check.get("status") == "FAIL"]
            if failed:
                errors.append("signing env report contains FAIL checks")
            names = {check.get("name") for check in checks if isinstance(check, dict)}
            for required_name in {"Signing env completeness", "Workspace secret files"}:
                if required_name not in names:
                    errors.append(f"signing env report missing {required_name!r}")
        if "env" not in signing_env:
            errors.append("signing env report missing env object")

    upload_keystore_path = handoff / "qa/upload_keystore_setup/upload_keystore_setup.json"
    if upload_keystore_path.exists():
        upload_keystore = json.loads(upload_keystore_path.read_text(encoding="utf-8"))
        if upload_keystore.get("status") not in {"PASS", "EXTERNAL_BLOCKER"}:
            errors.append("upload keystore setup report must be PASS or EXTERNAL_BLOCKER in local handoff")
        checks = upload_keystore.get("checks")
        if not isinstance(checks, list):
            errors.append("upload keystore setup checks must be a list")
        else:
            failed = [check for check in checks if isinstance(check, dict) and check.get("status") == "FAIL"]
            if failed:
                errors.append("upload keystore setup report contains FAIL checks")
            names = {check.get("name") for check in checks if isinstance(check, dict)}
            for required_name in {
                "keytool runtime",
                "Keystore location",
                "Keystore password env",
                "Gradle keystore env",
                "Gradle key alias env",
                "Keystore file",
                "Keystore alias",
            }:
                if required_name not in names:
                    errors.append(f"upload keystore setup report missing {required_name!r}")
        if not isinstance(upload_keystore.get("keystorePath"), str) or not upload_keystore.get("keystorePath"):
            errors.append("upload keystore setup report missing keystorePath")
        if not isinstance(upload_keystore.get("alias"), str) or not upload_keystore.get("alias"):
            errors.append("upload keystore setup report missing alias")
        md_path = handoff / "qa/upload_keystore_setup/upload_keystore_setup.md"
        if not md_path.exists():
            errors.append("upload keystore setup markdown report missing")

    upload_operator_doc = handoff / "docs/upload_operator_runbook.md"
    if upload_operator_doc.exists():
        runbook_text = upload_operator_doc.read_text(encoding="utf-8")
        for required_term in {
            "signing.status = signed",
            "play_handoff_secret_scan_qa.py",
            "upload/app-release.aab",
        }:
            if required_term not in runbook_text:
                errors.append(f"upload operator runbook missing {required_term!r}")
        if "-----BEGIN" in runbook_text or re.search(r'"(?:private_key|client_email)"\s*:', runbook_text):
            errors.append("upload operator runbook contains secret-like credential material")

    upload_operator_path = handoff / "qa/upload_operator_runbook/upload_operator_runbook.json"
    if upload_operator_path.exists():
        upload_operator = json.loads(upload_operator_path.read_text(encoding="utf-8"))
        if upload_operator.get("status") != "PASS":
            errors.append("upload operator runbook report must be PASS in handoff")
        if upload_operator.get("runbook") != "docs/upload_operator_runbook.md":
            errors.append("upload operator runbook report has unexpected runbook path")
        checks = upload_operator.get("checks")
        if not isinstance(checks, list):
            errors.append("upload operator runbook checks must be a list")
        else:
            failed = [check for check in checks if isinstance(check, dict) and check.get("status") == "FAIL"]
            if failed:
                errors.append("upload operator runbook report contains FAIL checks")
            names = {check.get("name") for check in checks if isinstance(check, dict)}
            for required_name in {
                "Runbook file",
                "Required environment variables",
                "Required strict commands",
                "Required operator terms",
                "Forbidden private key block",
            }:
                if required_name not in names:
                    errors.append(f"upload operator runbook report missing {required_name!r}")
        required_env = upload_operator.get("requiredEnv")
        if not isinstance(required_env, list) or not REQUIRED_UPLOAD_OPERATOR_ENV.issubset(set(required_env)):
            errors.append("upload operator runbook report missing required environment variable coverage")
        required_commands = upload_operator.get("requiredCommands")
        if not isinstance(required_commands, list) or not REQUIRED_UPLOAD_OPERATOR_COMMANDS.issubset(set(required_commands)):
            errors.append("upload operator runbook report missing required command coverage")
        md_path = handoff / "qa/upload_operator_runbook/upload_operator_runbook.md"
        if not md_path.exists():
            errors.append("upload operator runbook markdown report missing")

    workspace_hygiene_path = handoff / "qa/workspace_hygiene/workspace_hygiene.json"
    if workspace_hygiene_path.exists():
        workspace_hygiene = json.loads(workspace_hygiene_path.read_text(encoding="utf-8"))
        if workspace_hygiene.get("status") != "PASS":
            errors.append("workspace hygiene report must be PASS in handoff")
        checks = workspace_hygiene.get("checks")
        if not isinstance(checks, list):
            errors.append("workspace hygiene checks must be a list")
        else:
            failed = [check for check in checks if isinstance(check, dict) and check.get("status") == "FAIL"]
            if failed:
                errors.append("workspace hygiene report contains FAIL checks")
            names = {check.get("name") for check in checks if isinstance(check, dict)}
            for required_name in {
                ".gitignore contains vendor/bundle/",
                ".gitignore contains *.keystore",
                "Source workspace secret-like files",
                "Handoff manifest hygiene",
                "Generated report duplicates",
            }:
                if required_name not in names:
                    errors.append(f"workspace hygiene report missing {required_name!r}")
        ignored = workspace_hygiene.get("ignoredRoots")
        if not isinstance(ignored, list) or "vendor/bundle" not in ignored or "build" not in ignored:
            errors.append("workspace hygiene report missing ignored root coverage")
        patterns = workspace_hygiene.get("requiredGitignorePatterns")
        if not isinstance(patterns, list) or "fastlane/.env*" not in patterns:
            errors.append("workspace hygiene report missing gitignore pattern coverage")
        md_path = handoff / "qa/workspace_hygiene/workspace_hygiene.md"
        if not md_path.exists():
            errors.append("workspace hygiene markdown report missing")

    privacy_path = handoff / "qa/privacy_data_safety/privacy_data_safety.json"
    if privacy_path.exists():
        privacy = json.loads(privacy_path.read_text(encoding="utf-8"))
        checks = privacy.get("checks")
        if not isinstance(checks, list):
            errors.append("privacy data safety checks must be a list")
        else:
            failed = [check for check in checks if isinstance(check, dict) and check.get("status") == "FAIL"]
            if failed:
                errors.append("privacy data safety report contains FAIL checks")
            names = {check.get("name") for check in checks if isinstance(check, dict)}
            for required_name in {
                "Source manifest privacy",
                "Merged release permissions",
                "Google Play target API",
                "Play Console data-safety answers",
                "Privacy policy no-data terms",
            }:
                if required_name not in names:
                    errors.append(f"privacy data safety report missing {required_name!r}")

    play_target_api_path = handoff / "qa/play_target_api/play_target_api.json"
    if play_target_api_path.exists():
        play_target_api = json.loads(play_target_api_path.read_text(encoding="utf-8"))
        if play_target_api.get("status") != "PASS":
            errors.append("play target API report must be PASS in handoff")
        if play_target_api.get("targetApiRequirement") != 35:
            errors.append("play target API report must record API 35 as the current checked mobile baseline")
        policy_sources = play_target_api.get("policySources")
        if (
            not isinstance(policy_sources, list)
            or "https://support.google.com/googleplay/android-developer/answer/11926878" not in policy_sources
            or "https://support.google.com/googleplay/android-developer/answer/16561298" not in policy_sources
        ):
            errors.append("play target API report missing official policy source URLs")
        checks = play_target_api.get("checks")
        if not isinstance(checks, list):
            errors.append("play target API checks must be a list")
        else:
            failed = [check for check in checks if isinstance(check, dict) and check.get("status") == "FAIL"]
            if failed:
                errors.append("play target API report contains FAIL checks")
            names = {check.get("name") for check in checks if isinstance(check, dict)}
            for required_name in {
                "Google Play mobile target API",
                "compileSdk coverage",
                "Google Play checklist target API notes",
                "Privacy notes target API gate",
            }:
                if required_name not in names:
                    errors.append(f"play target API report missing {required_name!r}")
        md_path = handoff / "qa/play_target_api/play_target_api.md"
        if not md_path.exists():
            errors.append("play target API markdown report missing")

    privacy_hosting_path = handoff / "qa/privacy_policy_hosting/privacy_policy_hosting.json"
    if privacy_hosting_path.exists():
        privacy_hosting = json.loads(privacy_hosting_path.read_text(encoding="utf-8"))
        if privacy_hosting.get("status") not in {"PASS", "EXTERNAL_BLOCKER"}:
            errors.append("privacy policy hosting report must be PASS or EXTERNAL_BLOCKER in local handoff")
        if privacy_hosting.get("sourcePath") != "store/privacy_policy.html":
            errors.append("privacy policy hosting report sourcePath mismatch")
        if not isinstance(privacy_hosting.get("fetchPrivacyUrl"), bool):
            errors.append("privacy policy hosting report missing fetchPrivacyUrl boolean")
        checks = privacy_hosting.get("checks")
        if not isinstance(checks, list):
            errors.append("privacy policy hosting checks must be a list")
        else:
            failed = [check for check in checks if isinstance(check, dict) and check.get("status") == "FAIL"]
            if failed:
                errors.append("privacy policy hosting report contains FAIL checks")
            names = {check.get("name") for check in checks if isinstance(check, dict)}
            for required_name in {
                "Source privacy policy file",
                "HTML document structure",
                "Publish-safe HTML surface",
                "Privacy policy terms",
                "Hosting bundle copy",
                "Hosted privacy policy URL",
            }:
                if required_name not in names:
                    errors.append(f"privacy policy hosting report missing {required_name!r}")
        bundle = privacy_hosting.get("hostingBundle")
        if not isinstance(bundle, dict):
            errors.append("privacy policy hosting report missing hostingBundle object")
        else:
            if bundle.get("source") != "store/privacy_policy.html":
                errors.append("privacy policy hosting bundle source mismatch")
            if not isinstance(bundle.get("sha256"), str) or len(str(bundle.get("sha256"))) != 64:
                errors.append("privacy policy hosting bundle missing sha256")
            handoff_policy = handoff / "privacy/hosting/privacy_policy.html"
            handoff_manifest = handoff / "privacy/hosting/manifest.json"
            handoff_readme = handoff / "privacy/hosting/README.md"
            if not handoff_policy.exists():
                errors.append("privacy hosting handoff HTML missing")
            elif bundle.get("sha256") != sha256(handoff_policy):
                errors.append("privacy hosting handoff HTML sha256 does not match hostingBundle")
            if not handoff_manifest.exists():
                errors.append("privacy hosting handoff manifest missing")
            else:
                hosting_manifest = json.loads(handoff_manifest.read_text(encoding="utf-8"))
                if hosting_manifest.get("sha256") != bundle.get("sha256"):
                    errors.append("privacy hosting handoff manifest sha256 mismatch")
                if hosting_manifest.get("requiredPublicUrlEnv") != "SHAWARMA58_PRIVACY_POLICY_URL":
                    errors.append("privacy hosting handoff manifest missing public URL env")
            if not handoff_readme.exists():
                errors.append("privacy hosting handoff README missing")
            elif "privacy_policy.html" not in handoff_readme.read_text(encoding="utf-8"):
                errors.append("privacy hosting handoff README must reference privacy_policy.html")
        md_path = handoff / "qa/privacy_policy_hosting/privacy_policy_hosting.md"
        if not md_path.exists():
            errors.append("privacy policy hosting markdown report missing")

    provenance_path = handoff / "qa/artifact_provenance/artifact_provenance.json"
    if provenance_path.exists():
        provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
        checks = provenance.get("checks")
        if not isinstance(checks, list):
            errors.append("artifact provenance checks must be a list")
        else:
            failed = [check for check in checks if isinstance(check, dict) and check.get("status") == "FAIL"]
            if failed:
                errors.append("artifact provenance report contains FAIL checks")
            names = {check.get("name") for check in checks if isinstance(check, dict)}
            for required_name in {
                "Merged release manifest",
                "Release AAB structure",
                "Release mapping outputs",
                "Secret-like files",
                "Release AAB signing",
            }:
                if required_name not in names:
                    errors.append(f"artifact provenance report missing {required_name!r}")
        artifacts = provenance.get("artifacts")
        if isinstance(artifacts, dict):
            release_aab = artifacts.get("releaseAab")
            if isinstance(release_aab, dict) and isinstance(upload_info, dict):
                if release_aab.get("sha256") != upload_info.get("sha256"):
                    errors.append("artifact provenance AAB checksum does not match handoff upload AAB")
        else:
            errors.append("artifact provenance report missing artifacts object")
        if provenance.get("packageName") != "com.shawarma58.game":
            errors.append("artifact provenance packageName mismatch")
        if provenance.get("versionName") != "1.0.0":
            errors.append("artifact provenance versionName mismatch")

    performance_path = handoff / "qa/performance_budget/performance_budget.json"
    if performance_path.exists():
        performance = json.loads(performance_path.read_text(encoding="utf-8"))
        checks = performance.get("checks")
        if not isinstance(checks, list):
            errors.append("performance budget checks must be a list")
        else:
            failed = [check for check in checks if isinstance(check, dict) and check.get("status") == "FAIL"]
            if failed:
                errors.append("performance budget report contains FAIL checks")
            names = {check.get("name") for check in checks if isinstance(check, dict)}
            for required_name in {
                "Release AAB size budget",
                "Android resource size budget",
                "Direct runtime dependencies",
                "Forbidden dependency markers",
                "Release base dex budget",
            }:
                if required_name not in names:
                    errors.append(f"performance budget report missing {required_name!r}")

    physical_device_path = handoff / "qa/physical_device_readiness/physical_device_readiness.json"
    if physical_device_path.exists():
        physical_device = json.loads(physical_device_path.read_text(encoding="utf-8"))
        if physical_device.get("status") not in {"PASS", "EXTERNAL_BLOCKER"}:
            errors.append("physical device readiness report must be PASS or EXTERNAL_BLOCKER in local handoff")
        checks = physical_device.get("checks")
        if not isinstance(checks, list):
            errors.append("physical device readiness checks must be a list")
        else:
            failed = [check for check in checks if isinstance(check, dict) and check.get("status") == "FAIL"]
            if failed:
                errors.append("physical device readiness report contains FAIL checks")
            names = {check.get("name") for check in checks if isinstance(check, dict)}
            for required_name in {
                "ADB runtime",
                "Connected Android devices",
                "Physical Android phone",
                "Physical sanity checklist",
            }:
                if required_name not in names:
                    errors.append(f"physical device readiness report missing {required_name!r}")
        if not isinstance(physical_device.get("devices"), list):
            errors.append("physical device readiness report missing devices list")
        md_path = handoff / "qa/physical_device_readiness/physical_device_readiness.md"
        if not md_path.exists():
            errors.append("physical device readiness markdown report missing")

    content_copy_path = handoff / "qa/content_copy/content_copy.json"
    if content_copy_path.exists():
        content_copy = json.loads(content_copy_path.read_text(encoding="utf-8"))
        if content_copy.get("status") != "PASS":
            errors.append("content copy report must be PASS in handoff")
        checks = content_copy.get("checks")
        if not isinstance(checks, list):
            errors.append("content copy checks must be a list")
        else:
            failed = [check for check in checks if isinstance(check, dict) and check.get("status") == "FAIL"]
            if failed:
                errors.append("content copy report contains FAIL checks")
            names = {check.get("name") for check in checks if isinstance(check, dict)}
            for required_name in {
                "App visible Russian copy",
                "Domain catalog Russian copy",
                "Store and policy copy",
            }:
                if required_name not in names:
                    errors.append(f"content copy report missing {required_name!r}")
        targets = content_copy.get("targetFiles")
        if not isinstance(targets, list) or "app/src/main/java/com/shawarma58/game/ui/Shawarma58App.kt" not in targets:
            errors.append("content copy report missing targetFiles coverage")
        md_path = handoff / "qa/content_copy/content_copy.md"
        if not md_path.exists():
            errors.append("content copy markdown report missing")

    asset_path = handoff / "qa/asset/asset.json"
    if not asset_path.exists():
        errors.append("asset QA report missing from handoff")
    else:
        asset = json.loads(asset_path.read_text(encoding="utf-8"))
        if asset.get("status") != "PASS":
            errors.append("asset QA report must be PASS in handoff")
        checks = asset.get("checks")
        if not isinstance(checks, list):
            errors.append("asset QA checks must be a list")
        else:
            failed = [check for check in checks if isinstance(check, dict) and check.get("status") == "FAIL"]
            if failed:
                errors.append("asset QA report contains FAIL checks")
            paths = {check.get("path") for check in checks if isinstance(check, dict)}
            for required_path in {
                "app/src/main/res/drawable-nodpi/ic_launcher_foreground.webp",
                "app/src/main/res/drawable-nodpi/bg_counter.webp",
                "app/src/main/res/drawable-nodpi/bg_route_map.webp",
                "app/src/main/res/drawable-nodpi/bg_prep_station.webp",
                "app/src/main/res/drawable-nodpi/bg_receipt_counter.webp",
                "app/src/main/res/drawable-nodpi/ingredient_lavash.webp",
                "store/screenshots/shawarma_gameplay.png",
            }:
                if required_path not in paths:
                    errors.append(f"asset QA report missing {required_path!r}")
        summary = asset.get("summary")
        if not isinstance(summary, dict):
            errors.append("asset QA report missing summary")
        else:
            expected_minimums = {
                "runtimeDrawableCount": 18,
                "launcherIconCount": 10,
                "screenshotCount": 7,
                "transparentAlphaRequiredCount": 9,
            }
            for key, minimum in expected_minimums.items():
                value = summary.get(key)
                if not isinstance(value, int) or value < minimum:
                    errors.append(f"asset QA summary {key} must be >= {minimum}, got {value}")
        md_path = handoff / "qa/asset/asset.md"
        if not md_path.exists():
            errors.append("asset QA markdown report missing")

    ui_behavior_path = handoff / "qa/ui_behavior/ui_behavior.json"
    if not ui_behavior_path.exists():
        errors.append("UI behavior report missing from handoff")
    else:
        ui_behavior = json.loads(ui_behavior_path.read_text(encoding="utf-8"))
        if ui_behavior.get("status") != "PASS":
            errors.append("UI behavior report must be PASS in handoff")
        checks = ui_behavior.get("checks")
        if not isinstance(checks, list):
            errors.append("UI behavior checks must be a list")
        else:
            failed = [check for check in checks if isinstance(check, dict) and check.get("status") == "FAIL"]
            if failed:
                errors.append("UI behavior report contains FAIL checks")
            names = {check.get("name") for check in checks if isinstance(check, dict)}
            for required_name in {
                "Forbidden UI tokens",
                "UI behavior source snippets",
                "Required Russian UI copy",
                "UI test tags",
                "UI behavior test coverage",
                "Sound safety guard",
            }:
                if required_name not in names:
                    errors.append(f"UI behavior report missing {required_name!r}")
        source_files = ui_behavior.get("sourceFiles")
        if not isinstance(source_files, list) or "app/src/main/java/com/shawarma58/game/ui/Shawarma58App.kt" not in source_files:
            errors.append("UI behavior report missing sourceFiles coverage")
        required_coverage = ui_behavior.get("requiredTestCoverage")
        if not isinstance(required_coverage, list) or "activeSessionSaveableValuesRestoreCurrentShift" not in required_coverage:
            errors.append("UI behavior report missing configuration restore coverage marker")
        md_path = handoff / "qa/ui_behavior/ui_behavior.md"
        if not md_path.exists():
            errors.append("UI behavior markdown report missing")

    play_metadata_path = handoff / "qa/play_metadata/play_metadata.json"
    if not play_metadata_path.exists():
        errors.append("Play metadata report missing from handoff")
    else:
        play_metadata = json.loads(play_metadata_path.read_text(encoding="utf-8"))
        if play_metadata.get("status") != "PASS":
            errors.append("Play metadata report must be PASS in handoff")
        lengths = play_metadata.get("lengths")
        text_limits = play_metadata.get("textLimits")
        if not isinstance(lengths, dict) or not isinstance(text_limits, dict):
            errors.append("Play metadata report missing lengths/textLimits")
        else:
            for required_file, limit in {
                "fastlane/metadata/android/ru-RU/title.txt": 30,
                "fastlane/metadata/android/ru-RU/short_description.txt": 80,
                "fastlane/metadata/android/ru-RU/full_description.txt": 4000,
                "fastlane/metadata/android/ru-RU/changelogs/1.txt": 500,
            }.items():
                if text_limits.get(required_file) != limit:
                    errors.append(f"Play metadata report has wrong limit for {required_file}")
                value = lengths.get(required_file)
                if not isinstance(value, int) or value <= 0 or value > limit:
                    errors.append(f"Play metadata length invalid for {required_file}: {value}")
        checks = play_metadata.get("checks")
        if not isinstance(checks, list):
            errors.append("Play metadata checks must be a list")
        else:
            failed = [check for check in checks if isinstance(check, dict) and check.get("status") == "FAIL"]
            if failed:
                errors.append("Play metadata report contains FAIL checks")
            names = {check.get("name") for check in checks if isinstance(check, dict)}
            for required_name in {
                "store/privacy_policy.html required terms",
                "store/feature_graphic_concept.png dimensions",
                "fastlane/metadata/android/ru-RU/images/phoneScreenshots/01_onboarding.png dimensions",
                "fastlane/metadata/android/ru-RU/images/phoneScreenshots/04_gameplay.png dimensions",
            }:
                if required_name not in names:
                    errors.append(f"Play metadata report missing {required_name!r}")
        screenshots = play_metadata.get("screenshots")
        if not isinstance(screenshots, list) or len(screenshots) != 5:
            errors.append("Play metadata report must list five upload screenshots")
        qa_only = play_metadata.get("qaOnlyScreenshots")
        if not isinstance(qa_only, list) or len(qa_only) != 2:
            errors.append("Play metadata report must list two QA-only screenshots")
        terms = play_metadata.get("requiredPrivacyTerms")
        if not isinstance(terms, list) or "не собирает" not in terms:
            errors.append("Play metadata report missing privacy term coverage")
        md_path = handoff / "qa/play_metadata/play_metadata.md"
        if not md_path.exists():
            errors.append("Play metadata markdown report missing")

    asset_manifest_path = handoff / "qa/asset_manifest/asset_manifest.json"
    if asset_manifest_path.exists():
        asset_manifest = json.loads(asset_manifest_path.read_text(encoding="utf-8"))
        if asset_manifest.get("status") != "PASS":
            errors.append("asset manifest report must be PASS in handoff")
        checks = asset_manifest.get("checks")
        if not isinstance(checks, list):
            errors.append("asset manifest checks must be a list")
        else:
            failed = [check for check in checks if isinstance(check, dict) and check.get("status") == "FAIL"]
            if failed:
                errors.append("asset manifest report contains FAIL checks")
            names = {check.get("name") for check in checks if isinstance(check, dict)}
            for required_name in {
                "Manifest documents store/app_icon_concept.png",
                "Manifest documents app/src/main/res/drawable-nodpi/ic_launcher_foreground.webp",
                "Rejected asset documentation",
            }:
                if required_name not in names:
                    errors.append(f"asset manifest report missing {required_name!r}")
        required_terms = asset_manifest.get("requiredManifestTerms")
        if not isinstance(required_terms, list) or "store/feature_graphic_concept.png" not in required_terms:
            errors.append("asset manifest report missing required manifest term coverage")
        rejected = asset_manifest.get("rejectedAssets")
        if not isinstance(rejected, list) or "store/rejected_assets/lavash_v1_rejected.png" not in rejected:
            errors.append("asset manifest report missing rejected asset coverage")
        md_path = handoff / "qa/asset_manifest/asset_manifest.md"
        if not md_path.exists():
            errors.append("asset manifest markdown report missing")

    completion_audit_path = handoff / "qa/completion_audit/completion_audit.json"
    if not completion_audit_path.exists():
        errors.append("completion audit report missing from handoff")
    else:
        completion_audit = json.loads(completion_audit_path.read_text(encoding="utf-8"))
        if completion_audit.get("status") != "PASS":
            errors.append("completion audit report must be PASS in handoff")
        required_files = completion_audit.get("requiredFiles")
        if not isinstance(required_files, list) or "docs/completion_audit.md" not in required_files:
            errors.append("completion audit report missing requiredFiles coverage")
        checks = completion_audit.get("checks")
        if not isinstance(checks, list):
            errors.append("completion audit checks must be a list")
        else:
            failed = [check for check in checks if isinstance(check, dict) and check.get("status") == "FAIL"]
            if failed:
                errors.append("completion audit report contains FAIL checks")
            names = {check.get("name") for check in checks if isinstance(check, dict)}
            for required_name in {
                "Required project files",
                "Build config",
                "Manifest privacy invariants",
                "Static content shape",
                "Progress persistence keys",
                "Completion audit document",
                "Release docs and asset evidence",
            }:
                if required_name not in names:
                    errors.append(f"completion audit report missing {required_name!r}")
        md_path = handoff / "qa/completion_audit/completion_audit.md"
        if not md_path.exists():
            errors.append("completion audit markdown report missing")

    pre_upload_path = handoff / "qa/pre_upload_blockers/pre_upload_blockers.json"
    if pre_upload_path.exists():
        pre_upload = json.loads(pre_upload_path.read_text(encoding="utf-8"))
        next_actions_path = handoff / "NEXT_ACTIONS.md"
        next_actions_text = next_actions_path.read_text(encoding="utf-8") if next_actions_path.exists() else ""
        if not next_actions_path.exists():
            errors.append("NEXT_ACTIONS.md missing from handoff root")
        elif "python3 scripts/package_release_candidate.py --strict-signing --fetch-privacy-url --fetch-target-api-policy --strict-screenshots --strict-physical-device --strict-pre-upload" not in next_actions_text:
            errors.append("NEXT_ACTIONS.md missing final strict package command")
        elif "python3 scripts/post_package_validation_qa.py" not in next_actions_text:
            errors.append("NEXT_ACTIONS.md missing final post-package validation command")
        if next_actions_path.exists():
            for required_term in {
                "privacy/hosting/privacy_policy.html",
                "privacy/hosting/manifest.json",
            }:
                if required_term not in next_actions_text:
                    errors.append(f"NEXT_ACTIONS.md missing privacy hosting term: {required_term}")
        if pre_upload.get("status") not in {"PASS", "EXTERNAL_BLOCKER"}:
            errors.append("pre-upload blockers report must be PASS or EXTERNAL_BLOCKER in local handoff")
        if pre_upload.get("baseStatus") not in {"PASS", "EXTERNAL_BLOCKER"}:
            errors.append("pre-upload blockers baseStatus must be PASS or EXTERNAL_BLOCKER in local handoff")
        groups = pre_upload.get("blockerGroups")
        if not isinstance(groups, list):
            errors.append("pre-upload blockers report missing blockerGroups list")
        else:
            failed_groups = [group for group in groups if isinstance(group, dict) and group.get("status") == "FAIL"]
            if failed_groups:
                errors.append("pre-upload blockers report contains FAIL groups")
            group_ids = {group.get("id") for group in groups if isinstance(group, dict)}
            for required_group in {
                "signing",
                "privacy_policy",
                "play_console",
                "fastlane_runtime",
                "physical_device",
                "report_integrity",
                "other",
            }:
                if required_group not in group_ids:
                    errors.append(f"pre-upload blockers report missing group {required_group!r}")
            for group in groups:
                if not isinstance(group, dict):
                    errors.append("pre-upload blockers group entry is not an object")
                    continue
                for required_field in {"title", "status", "action", "strictCommand", "items"}:
                    if required_field not in group:
                        errors.append(f"pre-upload blockers group missing {required_field!r}")
                if group.get("status") not in {"PASS", "EXTERNAL_BLOCKER"}:
                    errors.append(f"pre-upload blockers group has unexpected status: {group.get('id')}")
                if group.get("status") == "EXTERNAL_BLOCKER" and next_actions_path.exists():
                    title = group.get("title")
                    strict_command = group.get("strictCommand")
                    if isinstance(title, str) and title not in next_actions_text:
                        errors.append(f"NEXT_ACTIONS.md missing blocker title: {title}")
                    if isinstance(strict_command, str) and strict_command not in next_actions_text:
                        errors.append(f"NEXT_ACTIONS.md missing strict command for blocker: {group.get('id')}")
        issues = pre_upload.get("issues")
        if not isinstance(issues, list):
            errors.append("pre-upload blockers report missing issues list")
        else:
            failed_issues = [issue for issue in issues if isinstance(issue, dict) and issue.get("status") == "FAIL"]
            if failed_issues:
                errors.append("pre-upload blockers report contains FAIL issues")
        sources = pre_upload.get("sources")
        if not isinstance(sources, list):
            errors.append("pre-upload blockers report missing sources list")
        else:
            source_paths = {source.get("path") for source in sources if isinstance(source, dict)}
            for required_source in {
                "build/reports/play_external_readiness.json",
                "build/reports/play_upload_auth.json",
                "build/reports/privacy_policy_hosting.json",
                "build/reports/fastlane_runtime.json",
                "build/reports/signing_env.json",
                "build/reports/upload_keystore_setup.json",
                "build/reports/physical_device_readiness.json",
                "build/reports/artifact_provenance.json",
            }:
                if required_source not in source_paths:
                    errors.append(f"pre-upload blockers report missing source {required_source!r}")
        md_path = handoff / "qa/pre_upload_blockers/pre_upload_blockers.md"
        if not md_path.exists():
            errors.append("pre-upload blockers markdown report missing")

    release_gate_path = handoff / "qa/release_gate/release_gate.json"
    if release_gate_path.exists():
        verify_source_parity(
            handoff=handoff,
            files=files,
            errors=errors,
            handoff_relative="qa/release_gate/release_gate.json",
            expected_source="build/reports/release_gate.json",
            label="release gate JSON",
        )
        verify_source_parity(
            handoff=handoff,
            files=files,
            errors=errors,
            handoff_relative="qa/release_gate/release_gate.md",
            expected_source="build/reports/release_gate.md",
            label="release gate markdown",
        )
        release_gate = json.loads(release_gate_path.read_text(encoding="utf-8"))
        if release_gate.get("status") not in {"PASS", "PASS_WITH_WARNINGS", "EXTERNAL_BLOCKER"}:
            errors.append("release gate report must be PASS, PASS_WITH_WARNINGS or EXTERNAL_BLOCKER in local handoff")
        command = release_gate.get("command")
        if not isinstance(command, list) or "scripts/release_gate.py" not in " ".join(str(token) for token in command):
            errors.append("release gate report command must reference scripts/release_gate.py")
        checks = release_gate.get("checks")
        if not isinstance(checks, list):
            errors.append("release gate checks must be a list")
        else:
            failed = [check for check in checks if isinstance(check, dict) and check.get("status") == "FAIL"]
            if failed:
                errors.append("release gate report contains FAIL checks")
            names = {check.get("name") for check in checks if isinstance(check, dict)}
            for required_name in {
                "Gradle gates",
                "Play target API QA",
                "Artifact provenance QA",
                "Performance budget QA",
                "Pre-upload blockers",
                "AAB signing",
            }:
                if required_name not in names:
                    errors.append(f"release gate report missing {required_name!r}")
        blockers = release_gate.get("externalBlockers")
        if not isinstance(blockers, list):
            errors.append("release gate report missing externalBlockers list")
        md_path = handoff / "qa/release_gate/release_gate.md"
        if not md_path.exists():
            errors.append("release gate markdown report missing")
        manifest_release_gate = manifest.get("releaseGate")
        if not isinstance(manifest_release_gate, dict):
            errors.append("manifest.releaseGate must be present")
        else:
            if manifest_release_gate.get("status") != release_gate.get("status"):
                errors.append("manifest.releaseGate.status does not match release gate report")
            if manifest_release_gate.get("source") != "build/reports/release_gate.json":
                errors.append("manifest.releaseGate.source must be build/reports/release_gate.json")
            if manifest_release_gate.get("target") != "qa/release_gate/release_gate.json":
                errors.append("manifest.releaseGate.target must be qa/release_gate/release_gate.json")
            if manifest_release_gate.get("generatedAt") != release_gate.get("generatedAt"):
                errors.append("manifest.releaseGate.generatedAt does not match release gate report")
            if manifest_release_gate.get("command") != release_gate.get("command"):
                errors.append("manifest.releaseGate.command does not match release gate report")
            if isinstance(checks, list) and manifest_release_gate.get("checkCount") != len(checks):
                errors.append("manifest.releaseGate.checkCount does not match release gate report")
            if isinstance(blockers, list) and manifest_release_gate.get("externalBlockerCount") != len(blockers):
                errors.append("manifest.releaseGate.externalBlockerCount does not match release gate report")

    fastlane_assets_path = handoff / "qa/fastlane_assets/fastlane_assets.json"
    if fastlane_assets_path.exists():
        fastlane_assets = json.loads(fastlane_assets_path.read_text(encoding="utf-8"))
        if fastlane_assets.get("fastlaneImagesDir") != "fastlane/metadata/android/ru-RU/images":
            errors.append("fastlane assets report has unexpected images dir")
        asset_files = fastlane_assets.get("files")
        if not isinstance(asset_files, list) or len(asset_files) != 7:
            errors.append("fastlane assets report must list seven upload graphics")
        else:
            for item in asset_files:
                if not isinstance(item, dict):
                    errors.append("fastlane assets report entry is not an object")
                    continue
                target = item.get("target")
                if not isinstance(target, str):
                    errors.append("fastlane assets report entry missing target")
                    continue
                manifest_entry = files.get(target)
                if not isinstance(manifest_entry, dict):
                    errors.append(f"fastlane assets report target missing from handoff manifest: {target}")
                    continue
                if manifest_entry.get("sha256") != item.get("sha256"):
                    errors.append(f"fastlane assets checksum mismatch for {target}")
        md_path = handoff / "qa/fastlane_assets/fastlane_assets.md"
        if not md_path.exists():
            errors.append("fastlane assets markdown report missing")

    accessibility_path = handoff / "qa/accessibility_source/accessibility_source.json"
    if accessibility_path.exists():
        accessibility = json.loads(accessibility_path.read_text(encoding="utf-8"))
        checks = accessibility.get("checks")
        if not isinstance(checks, list):
            errors.append("accessibility source checks must be a list")
        else:
            failed = [check for check in checks if isinstance(check, dict) and check.get("status") == "FAIL"]
            if failed:
                errors.append("accessibility source report contains FAIL checks")
            names = {check.get("name") for check in checks if isinstance(check, dict)}
            for required_name in {
                "Back button accessible label",
                "Back button tap target",
                "Ingredient tile semantics",
                "Level tile semantics",
                "Instrumentation accessibility assertion",
            }:
                if required_name not in names:
                    errors.append(f"accessibility source report missing {required_name!r}")
        md_path = handoff / "qa/accessibility_source/accessibility_source.md"
        if not md_path.exists():
            errors.append("accessibility source markdown report missing")

    fastlane_config_path = handoff / "qa/fastlane_config/fastlane_config.json"
    if fastlane_config_path.exists():
        fastlane_config = json.loads(fastlane_config_path.read_text(encoding="utf-8"))
        if fastlane_config.get("status") != "PASS":
            errors.append("fastlane config report must be PASS in handoff")
        if fastlane_config.get("errors") not in ([], None):
            errors.append("fastlane config report must not contain errors")
        checks = fastlane_config.get("checks")
        if not isinstance(checks, list):
            errors.append("fastlane config checks must be a list")
        else:
            failed = [check for check in checks if isinstance(check, dict) and check.get("status") == "FAIL"]
            if failed:
                errors.append("fastlane config report contains FAIL checks")
            names = {check.get("name") for check in checks if isinstance(check, dict)}
            for required_name in {
                "Required fastlane files",
                "Fastfile guarded lanes",
                "Fastfile unsafe upload guards",
                "Fastfile upload guard order",
                "Appfile identity",
                "Fastlane upload docs",
            }:
                if required_name not in names:
                    errors.append(f"fastlane config report missing {required_name!r}")
        md_path = handoff / "qa/fastlane_config/fastlane_config.md"
        if not md_path.exists():
            errors.append("fastlane config markdown report missing")

    fastlane_runtime_path = handoff / "qa/fastlane_runtime/fastlane_runtime.json"
    if fastlane_runtime_path.exists():
        fastlane_runtime = json.loads(fastlane_runtime_path.read_text(encoding="utf-8"))
        if fastlane_runtime.get("status") not in {"PASS", "EXTERNAL_BLOCKER"}:
            errors.append("fastlane runtime report must be PASS or EXTERNAL_BLOCKER in local handoff")
        checks = fastlane_runtime.get("checks")
        if not isinstance(checks, list):
            errors.append("fastlane runtime checks must be a list")
        else:
            failed = [check for check in checks if isinstance(check, dict) and check.get("status") == "FAIL"]
            if failed:
                errors.append("fastlane runtime report contains FAIL checks")
            names = {check.get("name") for check in checks if isinstance(check, dict)}
            for required_name in {
                "Fastlane Gemfile",
                "Fastlane lockfile version",
                "Bundler lockfile version",
                "Bundler local config",
                "Ruby runtime",
                "Ruby native extension headers",
                "Ruby toolchain manager options",
                "Bundler runtime",
                "Bundler dependency set",
                "Vendor bundle directory",
                "Fastlane runtime",
            }:
                if required_name not in names:
                    errors.append(f"fastlane runtime report missing {required_name!r}")
        expected = fastlane_runtime.get("expected")
        if not isinstance(expected, dict) or expected.get("fastlane") != "2.230.0":
            errors.append("fastlane runtime report missing expected fastlane version")
        remediation = fastlane_runtime.get("remediation")
        if not isinstance(remediation, dict) or not isinstance(remediation.get("commands"), list):
            errors.append("fastlane runtime report missing remediation commands")
        md_path = handoff / "qa/fastlane_runtime/fastlane_runtime.md"
        if not md_path.exists():
            errors.append("fastlane runtime markdown report missing")

    visual_quality_path = handoff / "qa/store_visual_quality/store_visual_quality.json"
    if visual_quality_path.exists():
        visual_quality = json.loads(visual_quality_path.read_text(encoding="utf-8"))
        checks = visual_quality.get("checks")
        if not isinstance(checks, list):
            errors.append("store visual quality checks must be a list")
        else:
            failed = [check for check in checks if isinstance(check, dict) and check.get("status") == "FAIL"]
            if failed:
                errors.append("store visual quality report contains FAIL checks")
            names = {check.get("name") for check in checks if isinstance(check, dict)}
            if "Upload screenshot uniqueness" not in names:
                errors.append("store visual quality report missing upload uniqueness check")
        images = visual_quality.get("images")
        if not isinstance(images, list):
            errors.append("store visual quality report missing images list")
        else:
            upload_images = [
                image
                for image in images
                if isinstance(image, dict) and image.get("path") in UPLOAD_VISUAL_PATHS
            ]
            if len(upload_images) != 5:
                errors.append("store visual quality report must include five upload screenshots")
            for image in upload_images:
                if image.get("width") != 1080 or image.get("height") != 2400:
                    errors.append(f"store visual quality size mismatch for {image.get('path')}")
                if not isinstance(image.get("sha256"), str) or len(str(image.get("sha256"))) != 64:
                    errors.append(f"store visual quality missing sha256 for {image.get('path')}")
        pair_distances = visual_quality.get("pairDistances")
        if not isinstance(pair_distances, list) or len(pair_distances) != 10:
            errors.append("store visual quality report must include ten upload screenshot pair distances")
        md_path = handoff / "qa/store_visual_quality/store_visual_quality.md"
        if not md_path.exists():
            errors.append("store visual quality markdown report missing")

    capture_guard_path = handoff / "qa/store_screenshot_capture_guard/store_screenshot_capture_guard.json"
    if capture_guard_path.exists():
        capture_guard = json.loads(capture_guard_path.read_text(encoding="utf-8"))
        if capture_guard.get("status") != "PASS":
            errors.append("store screenshot capture guard report must be PASS")
        checks = capture_guard.get("checks")
        if not isinstance(checks, list):
            errors.append("store screenshot capture guard checks must be a list")
        else:
            failed = [check for check in checks if isinstance(check, dict) and check.get("status") == "FAIL"]
            if failed:
                errors.append("store screenshot capture guard report contains FAIL checks")
            names = {check.get("name") for check in checks if isinstance(check, dict)}
            for required_name in {
                "Current store screenshots",
                "Black candidate rejection",
                "Pre-overwrite capture wiring",
            }:
                if required_name not in names:
                    errors.append(f"store screenshot capture guard report missing {required_name!r}")
        thresholds = capture_guard.get("candidateThresholds")
        if not isinstance(thresholds, dict) or thresholds.get("minBytes") != 120000:
            errors.append("store screenshot capture guard report missing candidate thresholds")
        md_path = handoff / "qa/store_screenshot_capture_guard/store_screenshot_capture_guard.md"
        if not md_path.exists():
            errors.append("store screenshot capture guard markdown report missing")

    screenshot_freshness_path = handoff / "qa/store_screenshot_freshness/store_screenshot_freshness.json"
    if screenshot_freshness_path.exists():
        screenshot_freshness = json.loads(screenshot_freshness_path.read_text(encoding="utf-8"))
        if screenshot_freshness.get("status") not in {"PASS", "PASS_WITH_WARNINGS"}:
            errors.append("store screenshot freshness report must be PASS or PASS_WITH_WARNINGS in local handoff")
        checks = screenshot_freshness.get("checks")
        if not isinstance(checks, list):
            errors.append("store screenshot freshness checks must be a list")
        else:
            failed = [check for check in checks if isinstance(check, dict) and check.get("status") == "FAIL"]
            if failed:
                errors.append("store screenshot freshness report contains FAIL checks")
            names = {check.get("name") for check in checks if isinstance(check, dict)}
            for required_name in {
                "Required screenshot files",
                "UI source baseline",
                "Upload screenshot freshness",
                "QA screenshot freshness",
            }:
                if required_name not in names:
                    errors.append(f"store screenshot freshness report missing {required_name!r}")
        stale = screenshot_freshness.get("staleScreenshots")
        if not isinstance(stale, dict) or not isinstance(stale.get("upload"), list):
            errors.append("store screenshot freshness report missing stale upload list")
        newest = screenshot_freshness.get("newestSource")
        if not isinstance(newest, dict) or not newest.get("path"):
            errors.append("store screenshot freshness report missing newest source")
        md_path = handoff / "qa/store_screenshot_freshness/store_screenshot_freshness.md"
        if not md_path.exists():
            errors.append("store screenshot freshness markdown report missing")

    screenshot_capture_path = handoff / "qa/store_screenshot_capture/store_screenshot_capture.json"
    if screenshot_capture_path.exists():
        screenshot_capture = json.loads(screenshot_capture_path.read_text(encoding="utf-8"))
        if screenshot_capture.get("status") != "PASS":
            errors.append("store screenshot capture report must be PASS in handoff")
        summary = screenshot_capture.get("summary")
        if not isinstance(summary, dict):
            errors.append("store screenshot capture report missing summary object")
        else:
            if summary.get("package") != "com.shawarma58.game.debug":
                errors.append("store screenshot capture package must be the debug app")
            captured = summary.get("captured")
            if not isinstance(captured, list) or len(captured) != 7:
                errors.append("store screenshot capture summary must list seven screenshots")
        capture_dir = screenshot_capture.get("captureDir")
        if not isinstance(capture_dir, str) or not capture_dir.startswith("build/store_screenshot_capture/"):
            errors.append("store screenshot capture report missing captureDir")
        newest_source = screenshot_capture.get("newestSource")
        if not isinstance(newest_source, dict) or not newest_source.get("path"):
            errors.append("store screenshot capture report missing newestSource")
        screenshots = screenshot_capture.get("screenshots")
        if not isinstance(screenshots, list) or len(screenshots) != 7:
            errors.append("store screenshot capture report must include seven screenshot records")
        else:
            seen_store_paths: set[str] = set()
            for record in screenshots:
                if not isinstance(record, dict):
                    errors.append("store screenshot capture record is not an object")
                    continue
                store_path = record.get("storePath")
                capture_sha = record.get("captureSha256")
                store_sha = record.get("storeSha256")
                if not isinstance(store_path, str):
                    errors.append("store screenshot capture record missing storePath")
                    continue
                seen_store_paths.add(store_path)
                if capture_sha != store_sha:
                    errors.append(f"store screenshot capture SHA mismatch for {store_path}")
                handoff_path = STORE_SCREENSHOT_HANDOFF_PATHS.get(store_path)
                if handoff_path is None:
                    errors.append(f"unexpected store screenshot capture path: {store_path}")
                    continue
                manifest_entry = files.get(handoff_path)
                if not isinstance(manifest_entry, dict):
                    errors.append(f"store screenshot capture target missing from handoff manifest: {handoff_path}")
                    continue
                if store_path in UPLOAD_SCREENSHOT_HANDOFF_PATHS:
                    source_pixels = Image.open(ROOT / store_path).convert("RGB").tobytes()
                    handoff_pixels = Image.open(handoff / handoff_path).convert("RGB").tobytes()
                    if source_pixels != handoff_pixels:
                        errors.append(f"upload screenshot RGB pixels do not match store capture: {handoff_path}")
                    continue
                if manifest_entry.get("sha256") != store_sha:
                    errors.append(f"store screenshot capture SHA does not match handoff file: {handoff_path}")
            missing = set(STORE_SCREENSHOT_HANDOFF_PATHS) - seen_store_paths
            if missing:
                errors.append(f"store screenshot capture report missing screenshots: {sorted(missing)}")
        checks = screenshot_capture.get("checks")
        if not isinstance(checks, list):
            errors.append("store screenshot capture checks must be a list")
        else:
            failed = [check for check in checks if isinstance(check, dict) and check.get("status") == "FAIL"]
            if failed:
                errors.append("store screenshot capture report contains FAIL checks")
            names = {check.get("name") for check in checks if isinstance(check, dict)}
            for required_name in {
                "Latest passing capture",
                "Capture freshness baseline",
                "Capture evidence freshness",
                "Capture package",
                "Summary captured list",
            }:
                if required_name not in names:
                    errors.append(f"store screenshot capture report missing {required_name!r}")
        md_path = handoff / "qa/store_screenshot_capture/store_screenshot_capture.md"
        if not md_path.exists():
            errors.append("store screenshot capture markdown report missing")

    external_readiness_path = handoff / "qa/play_external_readiness/play_external_readiness.json"
    if external_readiness_path.exists():
        external_readiness = json.loads(external_readiness_path.read_text(encoding="utf-8"))
        checks = external_readiness.get("checks")
        if not isinstance(checks, list):
            errors.append("play external readiness checks must be a list")
        else:
            failed = [check for check in checks if isinstance(check, dict) and check.get("status") == "FAIL"]
            if failed:
                errors.append("play external readiness report contains FAIL checks")
            names = {check.get("name") for check in checks if isinstance(check, dict)}
            for required_name in {
                "Upload signing env",
                "Play service account",
                "Hosted privacy policy URL",
                "Fastlane Gemfile",
                "Workspace secret files",
            }:
                if required_name not in names:
                    errors.append(f"play external readiness report missing {required_name!r}")
        md_path = handoff / "qa/play_external_readiness/play_external_readiness.md"
        if not md_path.exists():
            errors.append("play external readiness markdown report missing")

    play_upload_packet_path = handoff / "qa/play_upload_packet/play_upload_packet.json"
    if play_upload_packet_path.exists():
        play_upload_packet = json.loads(play_upload_packet_path.read_text(encoding="utf-8"))
        if play_upload_packet.get("status") != "PASS":
            errors.append("play upload packet report must be PASS in handoff")
        if play_upload_packet.get("packet") != "store/play_upload_packet.md":
            errors.append("play upload packet report has unexpected packet path")
        if play_upload_packet.get("signingState") not in {"signed", "unsigned external blocker"}:
            errors.append("play upload packet report has unexpected signing state")
        checks = play_upload_packet.get("checks")
        if not isinstance(checks, list):
            errors.append("play upload packet checks must be a list")
        else:
            failed = [check for check in checks if isinstance(check, dict) and check.get("status") == "FAIL"]
            if failed:
                errors.append("play upload packet report contains FAIL checks")
            names = {check.get("name") for check in checks if isinstance(check, dict)}
            for required_name in {
                "Metadata limits",
                "Store image dimensions",
                "Manifest privacy",
                "Upload packet content and command order",
                "Upload artifact warning",
            }:
                if required_name not in names:
                    errors.append(f"play upload packet report missing {required_name!r}")
        required_terms = play_upload_packet.get("requiredPacketTerms")
        if not isinstance(required_terms, list) or "--strict-pre-upload" not in required_terms:
            errors.append("play upload packet report missing strict-pre-upload required term")
        md_path = handoff / "qa/play_upload_packet/play_upload_packet.md"
        if not md_path.exists():
            errors.append("play upload packet markdown report missing")

    play_upload_auth_path = handoff / "qa/play_upload_auth/play_upload_auth.json"
    if play_upload_auth_path.exists():
        play_upload_auth = json.loads(play_upload_auth_path.read_text(encoding="utf-8"))
        if play_upload_auth.get("status") not in {"PASS", "EXTERNAL_BLOCKER"}:
            errors.append("play upload auth report must be PASS or EXTERNAL_BLOCKER in local handoff")
        checks = play_upload_auth.get("checks")
        if not isinstance(checks, list):
            errors.append("play upload auth checks must be a list")
        else:
            failed = [check for check in checks if isinstance(check, dict) and check.get("status") == "FAIL"]
            if failed:
                errors.append("play upload auth report contains FAIL checks")
            names = {check.get("name") for check in checks if isinstance(check, dict)}
            for required_name in {
                "Play upload auth env",
                "Source workspace service-account files",
            }:
                if required_name not in names:
                    errors.append(f"play upload auth report missing {required_name!r}")
        env = play_upload_auth.get("env")
        if not isinstance(env, dict) or "SUPPLY_JSON_KEY" not in env:
            errors.append("play upload auth report missing redacted SUPPLY_JSON_KEY env")
        md_path = handoff / "qa/play_upload_auth/play_upload_auth.md"
        if not md_path.exists():
            errors.append("play upload auth markdown report missing")

    play_forms_path = handoff / "qa/play_console_forms/play_console_forms.json"
    if play_forms_path.exists():
        play_forms = json.loads(play_forms_path.read_text(encoding="utf-8"))
        checks = play_forms.get("checks")
        if not isinstance(checks, list):
            errors.append("play console forms checks must be a list")
        else:
            failed = [check for check in checks if isinstance(check, dict) and check.get("status") == "FAIL"]
            if failed:
                errors.append("play console forms report contains FAIL checks")
            names = {check.get("name") for check in checks if isinstance(check, dict)}
            for required_name in {
                "App details answers",
                "App access answers",
                "Data safety answers",
                "Content rating answers",
                "Target audience answers",
                "Upload packet policy summary",
            }:
                if required_name not in names:
                    errors.append(f"play console forms report missing {required_name!r}")
        md_path = handoff / "qa/play_console_forms/play_console_forms.md"
        if not md_path.exists():
            errors.append("play console forms markdown report missing")

    instrumentation_path = handoff / "qa/instrumentation_smoke/instrumentation_smoke.json"
    if instrumentation_path.exists():
        verify_source_parity(
            handoff=handoff,
            files=files,
            errors=errors,
            handoff_relative="qa/instrumentation_smoke/instrumentation_smoke.json",
            expected_source="build/reports/instrumentation_smoke.json",
            label="instrumentation smoke JSON",
        )
        verify_source_parity(
            handoff=handoff,
            files=files,
            errors=errors,
            handoff_relative="qa/instrumentation_smoke/instrumentation_smoke.md",
            expected_source="build/reports/instrumentation_smoke.md",
            label="instrumentation smoke markdown",
        )
        instrumentation = json.loads(instrumentation_path.read_text(encoding="utf-8"))
        if instrumentation.get("status") != "PASS":
            errors.append("instrumentation smoke report must have PASS status when included")
        command = instrumentation.get("command")
        if not isinstance(command, list) or not command:
            errors.append("instrumentation smoke command mismatch")
        else:
            command_tokens = [str(token) for token in command]
            if instrumentation.get("mode") == "serial-adb" and "-e" in command_tokens and "class" in command_tokens:
                errors.append("serial instrumentation smoke must run the full test APK, not a single -e class filter")
        mode = instrumentation.get("mode")
        if mode not in {"serial-adb", "gradle-connected"}:
            errors.append("instrumentation smoke mode must be serial-adb or gradle-connected")
        devices = instrumentation.get("devices")
        if not isinstance(devices, list) or not devices:
            errors.append("instrumentation smoke report must include at least one connected device")
        if instrumentation.get("classFiltered") is True:
            errors.append("instrumentation smoke report must not be class-filtered")
        if instrumentation.get("fullSuite") is not True:
            errors.append("instrumentation smoke report must mark fullSuite=true")
        failure_count = instrumentation.get("failureCount")
        if failure_count != 0:
            errors.append(f"instrumentation smoke failureCount must be 0, got {failure_count!r}")
        md_path = handoff / "qa/instrumentation_smoke/instrumentation_smoke.md"
        if not md_path.exists():
            errors.append("instrumentation smoke markdown report missing")
        else:
            md_text = md_path.read_text(encoding="utf-8")
            android_test_sources = discover_android_test_sources()
            newest_test_source = max(android_test_sources, key=lambda path: path.stat().st_mtime) if android_test_sources else None
            if newest_test_source is None:
                errors.append("instrumentation smoke freshness baseline has no androidTest source files")
            elif report_generated_epoch(instrumentation, instrumentation_path) < newest_test_source.stat().st_mtime:
                errors.append(
                    "instrumentation smoke report is older than androidTest source; "
                    f"newest source is {newest_test_source.relative_to(ROOT).as_posix()}",
                )
            expected_test_count = expected_android_test_count(android_test_sources)
            if expected_test_count <= 0:
                errors.append("instrumentation smoke expected test count is zero")
            elif instrumentation.get("testCount") != expected_test_count:
                errors.append(
                    "instrumentation smoke JSON does not show the full androidTest count; "
                    f"expected {expected_test_count}, got {instrumentation.get('testCount')!r}",
                )
            elif (
                f"OK ({expected_test_count} tests)" not in md_text
                and f"Finished {expected_test_count} tests" not in md_text
            ):
                errors.append(
                    "instrumentation smoke markdown does not show the full androidTest count; "
                    f"expected {expected_test_count} tests",
                )

    connected_perf_path = handoff / "qa/connected_performance/connected_performance.json"
    optional_evidence = manifest.get("optionalEvidence")
    if not isinstance(optional_evidence, dict):
        errors.append("manifest.optionalEvidence must be present")
        optional_connected: dict[str, object] = {}
    else:
        optional_instrumentation_raw = optional_evidence.get("instrumentationSmoke")
        optional_instrumentation = optional_instrumentation_raw if isinstance(optional_instrumentation_raw, dict) else {}
        if not optional_instrumentation:
            errors.append("manifest.optionalEvidence.instrumentationSmoke must be present")
        else:
            instrumentation_status = optional_instrumentation.get("status")
            if instrumentation_status not in {"included", "skipped", "missing"}:
                errors.append("manifest optional instrumentation smoke status is invalid")
            if not isinstance(optional_instrumentation.get("detail"), str) or not optional_instrumentation.get("detail"):
                errors.append("manifest optional instrumentation smoke detail is missing")
            rerun = optional_instrumentation.get("rerunCommand")
            if not isinstance(rerun, str) or "instrumentation_smoke_qa.py" not in rerun:
                errors.append("manifest optional instrumentation smoke rerun command is missing")
            if instrumentation_status == "included" and not instrumentation_path.exists():
                errors.append("manifest says instrumentation smoke is included but report is absent")
            if instrumentation_status in {"skipped", "missing"} and instrumentation_path.exists():
                errors.append("manifest says instrumentation smoke is omitted but report is present")
            if instrumentation_status in {"skipped", "missing"}:
                next_actions_path = handoff / "NEXT_ACTIONS.md"
                if not next_actions_path.exists():
                    errors.append("NEXT_ACTIONS.md missing instrumentation smoke refresh instructions")
                else:
                    next_actions_text = next_actions_path.read_text(encoding="utf-8")
                    instrumentation_detail = optional_instrumentation.get("detail")
                    instrumentation_rerun = optional_instrumentation.get("rerunCommand")
                    required_terms = [
                        "## Instrumentation Smoke To Refresh",
                        "Compose instrumentation smoke evidence is not included in this handoff.",
                        f"Status: `{instrumentation_status}`",
                    ]
                    if isinstance(instrumentation_detail, str) and instrumentation_detail:
                        required_terms.append(instrumentation_detail)
                    if isinstance(instrumentation_rerun, str) and instrumentation_rerun:
                        required_terms.append(instrumentation_rerun)
                    for required_term in required_terms:
                        if required_term not in next_actions_text:
                            errors.append(
                                "NEXT_ACTIONS.md missing instrumentation smoke refresh term: "
                                f"{required_term}",
                            )

        optional_connected_raw = optional_evidence.get("connectedPerformance")
        optional_connected = optional_connected_raw if isinstance(optional_connected_raw, dict) else {}
        if not optional_connected:
            errors.append("manifest.optionalEvidence.connectedPerformance must be present")
        else:
            optional_status = optional_connected.get("status")
            if optional_status not in {"included", "skipped", "missing"}:
                errors.append("manifest optional connected performance status is invalid")
            if not isinstance(optional_connected.get("detail"), str) or not optional_connected.get("detail"):
                errors.append("manifest optional connected performance detail is missing")
            if not isinstance(optional_connected.get("rerunCommand"), str) or "connected_performance_qa.py" not in optional_connected.get("rerunCommand", ""):
                errors.append("manifest optional connected performance rerun command is missing")
            if optional_status == "included" and not connected_perf_path.exists():
                errors.append("manifest says connected performance is included but report is absent")
            if optional_status in {"skipped", "missing"} and connected_perf_path.exists():
                errors.append("manifest says connected performance is omitted but report is present")
            if optional_status in {"skipped", "missing"}:
                next_actions_path = handoff / "NEXT_ACTIONS.md"
                if not next_actions_path.exists():
                    errors.append("NEXT_ACTIONS.md missing optional connected performance refresh instructions")
                else:
                    next_actions_text = next_actions_path.read_text(encoding="utf-8")
                    optional_detail = optional_connected.get("detail")
                    optional_rerun = optional_connected.get("rerunCommand")
                    required_terms = [
                        "## Optional Evidence To Refresh",
                        "Connected performance evidence is not included in this handoff.",
                        f"Status: `{optional_status}`",
                    ]
                    if isinstance(optional_detail, str) and optional_detail:
                        required_terms.append(optional_detail)
                    if isinstance(optional_rerun, str) and optional_rerun:
                        required_terms.append(optional_rerun)
                    for required_term in required_terms:
                        if required_term not in next_actions_text:
                            errors.append(
                                "NEXT_ACTIONS.md missing optional connected performance refresh term: "
                                f"{required_term}",
                            )

    if connected_perf_path.exists():
        verify_source_parity(
            handoff=handoff,
            files=files,
            errors=errors,
            handoff_relative="qa/connected_performance/connected_performance.json",
            expected_source="build/reports/connected_performance.json",
            label="connected performance JSON",
        )
        verify_source_parity(
            handoff=handoff,
            files=files,
            errors=errors,
            handoff_relative="qa/connected_performance/connected_performance.md",
            expected_source="build/reports/connected_performance.md",
            label="connected performance markdown",
        )
        connected_perf = json.loads(connected_perf_path.read_text(encoding="utf-8"))
        if connected_perf.get("status") not in {"PASS", "PASS_WITH_WARNINGS"}:
            errors.append("connected performance report must be PASS or PASS_WITH_WARNINGS when included")
        if connected_perf.get("package") != "com.shawarma58.game.debug":
            errors.append("connected performance package must be the debug app")
        if not isinstance(connected_perf.get("serial"), str) or not connected_perf.get("serial"):
            errors.append("connected performance report missing serial")
        flow_evidence = connected_perf.get("flowEvidence")
        if not isinstance(flow_evidence, str) or not flow_evidence.startswith("build/performance_connected/"):
            errors.append("connected performance report missing flowEvidence")
        checks = connected_perf.get("checks")
        if not isinstance(checks, list):
            errors.append("connected performance checks must be a list")
        else:
            failed = [check for check in checks if isinstance(check, dict) and check.get("status") == "FAIL"]
            if failed:
                errors.append("connected performance report contains FAIL checks")
            names = {check.get("name") for check in checks if isinstance(check, dict)}
            for required_name in {"Total PSS budget", "Crash buffer"}:
                if required_name not in names:
                    errors.append(f"connected performance report missing {required_name!r}")
        sources = discover_smoke_sources()
        newest_source = max(sources, key=lambda path: path.stat().st_mtime) if sources else None
        if newest_source is None:
            errors.append("connected performance freshness baseline has no app source files")
        elif report_generated_epoch(connected_perf, connected_perf_path) < newest_source.stat().st_mtime:
            errors.append(
                "connected performance report is older than app source; "
                f"newest source is {newest_source.relative_to(ROOT).as_posix()}",
            )
        artifacts = connected_perf.get("artifacts")
        if not isinstance(artifacts, dict):
            errors.append("connected performance report missing artifacts object")
        else:
            required_artifacts = {"meminfo", "gfxinfo", "gfxinfoFramestats", "logcat", "crashLog"}
            missing_artifacts = required_artifacts - set(artifacts)
            if missing_artifacts:
                errors.append(f"connected performance report missing artifacts: {sorted(missing_artifacts)}")
            for label, source in artifacts.items():
                if not isinstance(label, str) or not isinstance(source, str):
                    errors.append("connected performance artifact entry must be string:string")
                    continue
                source_path = ROOT / source
                if not source_path.exists() or not source_path.is_file():
                    errors.append(f"connected performance source artifact missing: {source}")
                    continue
                handoff_relative = f"qa/connected_performance/artifacts/{Path(source).name}"
                handoff_artifact = handoff / handoff_relative
                if not handoff_artifact.exists():
                    errors.append(f"connected performance artifact missing from handoff: {handoff_relative}")
                    continue
                manifest_entry = files.get(handoff_relative)
                if not isinstance(manifest_entry, dict):
                    errors.append(f"connected performance artifact missing from manifest: {handoff_relative}")
                    continue
                source_sha = sha256(source_path)
                handoff_sha = sha256(handoff_artifact)
                if source_sha != handoff_sha or manifest_entry.get("sha256") != source_sha:
                    errors.append(f"connected performance artifact checksum mismatch: {handoff_relative}")
        md_path = handoff / "qa/connected_performance/connected_performance.md"
        if not md_path.exists():
            errors.append("connected performance markdown report missing")

    smoke = manifest.get("connectedSmoke")
    if not isinstance(smoke, dict):
        errors.append("manifest.connectedSmoke must be present")
    else:
        smoke_status = smoke.get("status")
        latest_smoke = latest_passing_smoke_dir(allow_basic=args.allow_basic_smoke)
        sources = discover_smoke_sources()
        newest_source = max(sources, key=lambda path: path.stat().st_mtime) if sources else None
        latest_smoke_fresh = False
        if latest_smoke is not None and newest_source is not None:
            latest_summary_path = latest_smoke / "summary.md"
            latest_summary = latest_summary_path.read_text(encoding="utf-8")
            latest_smoke_fresh = smoke_generated_epoch(latest_summary, latest_summary_path) >= newest_source.stat().st_mtime
        if smoke_status == "included":
            mode = smoke.get("mode")
            if mode != "extended" and not args.allow_basic_smoke:
                errors.append(f"connected smoke must be extended, got {mode!r}")
            summary_path = handoff / str(smoke.get("target", "")) / "summary.md"
            if not summary_path.exists():
                errors.append("connected smoke summary is missing")
            else:
                summary = summary_path.read_text(encoding="utf-8")
                required_terms = ["Status: PASS", "Package: `com.shawarma58.game.debug`"]
                if not args.allow_basic_smoke:
                    required_terms.append("Mode: `extended`")
                for term in required_terms:
                    if term not in summary:
                        errors.append(f"connected smoke summary missing {term!r}")
                if newest_source is None:
                    errors.append("connected smoke freshness baseline has no app source files")
                elif smoke_generated_epoch(summary, summary_path) < newest_source.stat().st_mtime:
                    errors.append(
                        "connected smoke is older than app source; "
                        f"newest source is {newest_source.relative_to(ROOT).as_posix()}",
                    )
            actual_smoke_files = list((handoff / str(smoke.get("target", ""))).glob("*"))
            if smoke.get("files") != len([path for path in actual_smoke_files if path.is_file()]):
                errors.append("connected smoke file count does not match copied files")
            if latest_smoke is not None:
                expected_source = latest_smoke.relative_to(ROOT).as_posix()
                if smoke.get("source") != expected_source:
                    errors.append(f"connected smoke source is not the latest passing smoke: expected {expected_source}, got {smoke.get('source')}")
                expected_files = sorted(path for path in latest_smoke.iterdir() if path.is_file())
                actual_names = sorted(path.name for path in actual_smoke_files if path.is_file())
                expected_names = sorted(path.name for path in expected_files)
                if actual_names != expected_names:
                    errors.append(
                        "connected smoke copied file set does not match source; "
                        f"missing={sorted(set(expected_names) - set(actual_names))}, "
                        f"extra={sorted(set(actual_names) - set(expected_names))}",
                    )
                if smoke.get("files") != len(expected_files):
                    errors.append("connected smoke manifest file count does not match source file count")
                for source_path in expected_files:
                    verify_source_parity(
                        handoff=handoff,
                        files=files,
                        errors=errors,
                        handoff_relative=f"{smoke.get('target')}/{source_path.name}",
                        expected_source=source_path.relative_to(ROOT).as_posix(),
                        label="connected smoke evidence",
                    )
        elif smoke_status in {"skipped", "missing"}:
            if latest_smoke_fresh:
                errors.append("fresh connected smoke exists but manifest.connectedSmoke is not included")
            rerun = smoke.get("rerunCommand")
            if rerun != "python3 scripts/android_smoke_qa.py --serial <adb-serial> --extended":
                errors.append("connected smoke rerunCommand is missing or unexpected")
            detail = smoke.get("detail")
            if not isinstance(detail, str) or not detail:
                errors.append("connected smoke skipped/missing detail is required")
            next_actions = (handoff / "NEXT_ACTIONS.md").read_text(encoding="utf-8") if (handoff / "NEXT_ACTIONS.md").exists() else ""
            for term in ["Connected Smoke To Refresh", str(smoke_status), str(rerun)]:
                if term not in next_actions:
                    errors.append(f"NEXT_ACTIONS.md missing connected smoke refresh term {term!r}")
            if smoke_status == "skipped" and latest_smoke is not None:
                expected_source = latest_smoke.relative_to(ROOT).as_posix()
                if smoke.get("source") != expected_source:
                    errors.append(f"skipped connected smoke source should be latest passing smoke: expected {expected_source}, got {smoke.get('source')}")
        else:
            errors.append("manifest.connectedSmoke.status must be included, skipped or missing")

    metadata = manifest.get("metadataLengths")
    if not isinstance(metadata, dict):
        errors.append("manifest.metadataLengths must be an object")
    else:
        limits = {
            "title": 30,
            "shortDescription": 80,
            "fullDescription": 4000,
            "releaseNotes": 500,
        }
        for key, limit in limits.items():
            value = metadata.get(key)
            if not isinstance(value, int) or value <= 0 or value > limit:
                errors.append(f"metadata length {key} invalid: {value}")

    signing = manifest.get("signing")
    if not isinstance(signing, dict) or signing.get("status") not in {"signed", "external_blocker"}:
        errors.append("manifest.signing.status must be signed or external_blocker")

    write_report(
        handoff=handoff,
        files=files,
        errors=errors,
        allow_basic_smoke=args.allow_basic_smoke,
    )
    if errors:
        print("Play handoff QA failed")
        for error in errors:
            print(f"- {error}")
        print(f"Report: {REPORT_MD.relative_to(ROOT).as_posix()}")
        raise SystemExit(1)

    print(
        f"Play handoff QA PASS "
        f"({handoff.relative_to(ROOT).as_posix()}; {REPORT_MD.relative_to(ROOT).as_posix()})",
    )


if __name__ == "__main__":
    main()
