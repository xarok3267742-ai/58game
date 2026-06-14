#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "fastlane/metadata/android/ru-RU"
STORE = ROOT / "store"
PACKET = STORE / "play_upload_packet.md"
AAB = ROOT / "app/build/outputs/bundle/release/app-release.aab"
MANIFEST = ROOT / "app/src/main/AndroidManifest.xml"
REPORT_MD = ROOT / "build/reports/play_upload_packet.md"
REPORT_JSON = ROOT / "build/reports/play_upload_packet.json"

SCREENSHOT_ORDER = [
    "fastlane/metadata/android/ru-RU/images/phoneScreenshots/01_onboarding.png",
    "fastlane/metadata/android/ru-RU/images/phoneScreenshots/02_menu.png",
    "fastlane/metadata/android/ru-RU/images/phoneScreenshots/03_levels.png",
    "fastlane/metadata/android/ru-RU/images/phoneScreenshots/04_gameplay.png",
    "fastlane/metadata/android/ru-RU/images/phoneScreenshots/05_result.png",
]
QA_SCREENSHOTS = [
    "store/screenshots/shawarma_wrong_order.png",
    "store/screenshots/shawarma_endless_result.png",
]
METADATA_FILES = {
    "fastlane/metadata/android/ru-RU/title.txt": 30,
    "fastlane/metadata/android/ru-RU/short_description.txt": 80,
    "fastlane/metadata/android/ru-RU/full_description.txt": 4000,
    "fastlane/metadata/android/ru-RU/changelogs/1.txt": 500,
}
SIGNING_ENV = [
    "SHAWARMA58_KEYSTORE",
    "SHAWARMA58_KEYSTORE_PASSWORD",
    "SHAWARMA58_KEY_ALIAS",
    "SHAWARMA58_KEY_PASSWORD",
]
REQUIRED_PACKET_TERMS = [
    "com.andrejivliev.shawarma58",
    "app/build/outputs/bundle/release/app-release.aab",
    "Do not upload an unsigned AAB",
    "python3 scripts/release_gate.py --strict-signing",
    "store/privacy_policy.html",
    "public, non-geofenced, non-PDF HTTPS URL",
    "store/play_console_answers.md",
    "Data deletion: local progress can be reset in app settings",
    "internal testing",
    "docs/physical_device_sanity.md",
    "python3 scripts/physical_device_readiness_qa.py",
    "python3 scripts/workspace_hygiene_qa.py",
    "python3 scripts/prepare_upload_keystore.py",
    "docs/upload_operator_runbook.md",
    "python3 scripts/upload_operator_runbook_qa.py",
    "SHAWARMA58_KEYSTORE",
    "python3 scripts/asset_manifest_qa.py",
    "python3 scripts/sync_fastlane_assets.py",
    "python3 scripts/fastlane_assets_qa.py",
    "python3 scripts/content_copy_qa.py",
    "python3 scripts/store_visual_quality_qa.py",
    "python3 scripts/store_screenshot_freshness_qa.py",
    "python3 scripts/store_screenshot_capture_qa.py",
    "python3 scripts/accessibility_source_qa.py",
    "python3 scripts/play_console_forms_qa.py",
    "python3 scripts/play_upload_auth_qa.py",
    "python3 scripts/privacy_policy_hosting_qa.py",
    "python3 scripts/package_release_candidate.py --strict-signing --fetch-privacy-url --fetch-target-api-policy",
    "--strict-physical-device",
    "--strict-pre-upload",
    "python3 scripts/pre_upload_blockers_qa.py --strict",
    "python3 scripts/post_package_validation_qa.py",
    "python3 scripts/update_release_dates.py",
    "python3 scripts/play_handoff_secret_scan_qa.py",
    "python3 scripts/release_freshness_qa.py",
    "privacy/hosting/manifest.json",
    "fastlane/metadata/android/ru-RU/images/icon.png",
    "fastlane/metadata/android/ru-RU/images/featureGraphic.png",
    "fastlane/metadata/android/ru-RU/images/phoneScreenshots",
    "python3 scripts/play_external_readiness_qa.py",
    "bundle exec fastlane android validate_internal",
    "bundle exec fastlane android upload_internal",
    "bundle install",
    "Gemfile.lock",
    "native extension headers",
    "python3 scripts/fastlane_runtime_qa.py",
    "SUPPLY_JSON_KEY",
    "SHAWARMA58_PRIVACY_POLICY_URL",
]


errors: list[str] = []


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def require_file(path: Path) -> None:
    if not path.exists():
        errors.append(f"missing file: {rel(path)}")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def fenced_bash_blocks(text: str) -> list[str]:
    blocks: list[str] = []
    marker = "```bash"
    start = 0
    while True:
        block_start = text.find(marker, start)
        if block_start < 0:
            return blocks
        content_start = text.find("\n", block_start)
        if content_start < 0:
            return blocks
        block_end = text.find("```", content_start + 1)
        if block_end < 0:
            return blocks
        blocks.append(text[content_start + 1:block_end])
        start = block_end + 3


def block_has_strict_package_order(block: str) -> bool:
    pre_upload_index = block.find("python3 scripts/pre_upload_blockers_qa.py --strict")
    package_index = block.find("python3 scripts/package_release_candidate.py --strict-signing")
    post_package_index = block.find("python3 scripts/post_package_validation_qa.py", package_index)
    late_pre_upload_index = block.find("python3 scripts/pre_upload_blockers_qa.py --strict", package_index)
    return (
        pre_upload_index >= 0
        and package_index >= 0
        and post_package_index >= 0
        and pre_upload_index < package_index < post_package_index
        and late_pre_upload_index < 0
    )


def verify_metadata_limits() -> None:
    for relative, limit in METADATA_FILES.items():
        path = ROOT / relative
        require_file(path)
        if not path.exists():
            continue
        value = read(path)
        if len(value) > limit:
            errors.append(f"{relative} length {len(value)} exceeds {limit}")
        if not value:
            errors.append(f"{relative} must not be empty")


def verify_images() -> None:
    icon = STORE / "play_icon.png"
    require_file(icon)
    if icon.exists() and Image.open(icon).size != (512, 512):
        errors.append("store/play_icon.png must be 512x512")

    feature = STORE / "feature_graphic_concept.png"
    require_file(feature)
    if feature.exists() and Image.open(feature).size != (1024, 500):
        errors.append("store/feature_graphic_concept.png must be 1024x500")

    for relative in SCREENSHOT_ORDER + QA_SCREENSHOTS:
        path = ROOT / relative
        require_file(path)
        if path.exists() and Image.open(path).size != (1080, 2400):
            errors.append(f"{relative} must be 1080x2400")
        if relative.startswith("fastlane/") and path.exists() and Image.open(path).mode != "RGB":
            errors.append(f"{relative} must be RGB PNG for Play upload")


def verify_manifest() -> None:
    require_file(MANIFEST)
    if not MANIFEST.exists():
        return
    tree = ET.parse(MANIFEST)
    root = tree.getroot()
    android = "{http://schemas.android.com/apk/res/android}"
    permissions = [node.attrib.get(f"{android}name", "") for node in root.findall("uses-permission")]
    if permissions:
        errors.append(f"manifest declares permissions: {permissions}")
    application = root.find("application")
    if application is None:
        errors.append("manifest is missing <application>")
    elif application.attrib.get(f"{android}allowBackup") != "false":
        errors.append("android:allowBackup must remain false")


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


def is_aab_signed() -> bool:
    signer = jarsigner_path()
    if signer is None or not AAB.exists():
        return False
    result = subprocess.run(
        [signer, "-verify", "-verbose", "-certs", str(AAB)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    output = result.stdout.lower()
    return "jar is unsigned" not in output and "signature was verified" in output


def verify_packet_doc() -> None:
    require_file(PACKET)
    if not PACKET.exists():
        return
    packet = read(PACKET)
    for term in REQUIRED_PACKET_TERMS:
        if term not in packet:
            errors.append(f"store/play_upload_packet.md is missing {term!r}")
    for relative in METADATA_FILES:
        if relative not in packet:
            errors.append(f"store/play_upload_packet.md does not reference {relative}")
    for relative in SCREENSHOT_ORDER + QA_SCREENSHOTS:
        if relative not in packet:
            errors.append(f"store/play_upload_packet.md does not reference {relative}")
    if not any(block_has_strict_package_order(block) for block in fenced_bash_blocks(packet)):
        errors.append("store/play_upload_packet.md must include a bash command block that runs strict pre-upload blockers before package, avoids rewriting that report after package and runs post-package validation after package")


def verify_upload_artifact_warning() -> None:
    require_file(AAB)
    if not AAB.exists() or not PACKET.exists():
        return
    signed = is_aab_signed()
    missing_env = [name for name in SIGNING_ENV if not os.environ.get(name)]
    packet = read(PACKET)
    if not signed and "Do not upload an unsigned AAB" not in packet:
        errors.append("packet must warn against uploading unsigned AABs")
    if signed and missing_env:
        errors.append("AAB appears signed but signing env vars are not set for reproducible rebuild")


def run_check(name: str, func) -> Check:
    before = len(errors)
    func()
    new_errors = errors[before:]
    if not new_errors:
        return Check(name, "PASS", "completed")
    detail = "; ".join(new_errors[:3])
    if len(new_errors) > 3:
        detail += f"; +{len(new_errors) - 3} more"
    return Check(name, "FAIL", detail)


def write_reports(checks: list[Check], signing_state: str) -> None:
    status = "FAIL" if errors else "PASS"
    payload = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "packet": rel(PACKET),
        "signingState": signing_state,
        "checks": [check.__dict__ for check in checks],
        "errors": errors,
        "metadataFiles": METADATA_FILES,
        "screenshots": SCREENSHOT_ORDER,
        "qaScreenshots": QA_SCREENSHOTS,
        "requiredPacketTerms": REQUIRED_PACKET_TERMS,
    }
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Play Upload Packet QA",
        "",
        f"Generated: {payload['generatedAt']}",
        f"Status: `{status}`",
        f"Packet: `{payload['packet']}`",
        f"Signing state: `{signing_state}`",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for check in checks:
        lines.append(f"| {check.name} | {check.status} | {check.detail} |")
    if errors:
        lines.extend(["", "## Errors"])
        for error in errors:
            lines.append(f"- {error}")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    checks = [
        run_check("Metadata limits", verify_metadata_limits),
        run_check("Store image dimensions", verify_images),
        run_check("Manifest privacy", verify_manifest),
        run_check("Upload packet content and command order", verify_packet_doc),
        run_check("Upload artifact warning", verify_upload_artifact_warning),
    ]
    signing_state = "signed" if is_aab_signed() else "unsigned external blocker"
    write_reports(checks, signing_state)

    if errors:
        print("Play upload packet QA failed")
        for error in errors:
            print(f"- {error}")
        print(f"Report: {rel(REPORT_MD)}")
        raise SystemExit(1)

    print(f"Play upload packet QA PASS ({signing_state}; {rel(REPORT_MD)}, {rel(REPORT_JSON)})")


if __name__ == "__main__":
    main()
