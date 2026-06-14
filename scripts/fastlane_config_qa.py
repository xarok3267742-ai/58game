#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APPFILE = ROOT / "fastlane/Appfile"
FASTFILE = ROOT / "fastlane/Fastfile"
FASTLANE_README = ROOT / "fastlane/README.md"
DOC = ROOT / "docs/fastlane_upload.md"
REPORT_MD = ROOT / "build/reports/fastlane_config.md"
REPORT_JSON = ROOT / "build/reports/fastlane_config.json"
REQUIRED_FILES = [
    APPFILE,
    FASTFILE,
    FASTLANE_README,
    DOC,
    ROOT / "Gemfile",
    ROOT / "Gemfile.lock",
    ROOT / "fastlane/metadata/android/ru-RU/title.txt",
    ROOT / "fastlane/metadata/android/ru-RU/short_description.txt",
    ROOT / "fastlane/metadata/android/ru-RU/full_description.txt",
    ROOT / "fastlane/metadata/android/ru-RU/changelogs/1.txt",
    ROOT / "fastlane/metadata/android/ru-RU/images/icon.png",
    ROOT / "fastlane/metadata/android/ru-RU/images/featureGraphic.png",
    ROOT / "fastlane/metadata/android/ru-RU/images/phoneScreenshots/01_onboarding.png",
    ROOT / "fastlane/metadata/android/ru-RU/images/phoneScreenshots/02_menu.png",
    ROOT / "fastlane/metadata/android/ru-RU/images/phoneScreenshots/03_levels.png",
    ROOT / "fastlane/metadata/android/ru-RU/images/phoneScreenshots/04_gameplay.png",
    ROOT / "fastlane/metadata/android/ru-RU/images/phoneScreenshots/05_result.png",
]
FASTFILE_REQUIRED = [
    'PACKAGE_NAME = "com.andrejivliev.shawarma58"',
    'AAB_PATH = "app/build/outputs/bundle/release/app-release.aab"',
    'METADATA_PATH = "fastlane/metadata/android"',
    'PLAY_TRACK = "internal"',
    'PLAY_RELEASE_STATUS = "draft"',
    'lane :validate_internal do',
    'lane :upload_internal do',
    'validate_only: true',
    'validate_only: false',
    'track: PLAY_TRACK',
    'release_status: PLAY_RELEASE_STATUS',
    'skip_upload_aab: false',
    'skip_upload_metadata: false',
    'skip_upload_images: false',
    'skip_upload_screenshots: false',
    'python3 scripts/prepare_upload_keystore.py --strict',
    'python3 scripts/play_upload_auth_qa.py --strict',
    'python3 scripts/privacy_policy_hosting_qa.py --strict --fetch-privacy-url',
    'python3 scripts/fastlane_runtime_qa.py --strict',
    'python3 scripts/package_release_candidate.py --strict-signing --fetch-privacy-url --fetch-target-api-policy',
    '--strict-screenshots',
    '--strict-physical-device',
    '--strict-pre-upload',
    'python3 scripts/pre_upload_blockers_qa.py --strict',
    'python3 scripts/play_handoff_secret_scan_qa.py',
    'python3 scripts/release_freshness_qa.py',
    'python3 scripts/post_package_validation_qa.py',
    'SHAWARMA58_PRIVACY_POLICY_URL',
    'SUPPLY_JSON_KEY',
]
APPFILE_REQUIRED = [
    'json_key(ENV["SUPPLY_JSON_KEY"])',
    'package_name("com.andrejivliev.shawarma58")',
]
DOC_REQUIRED = [
    "bundle exec fastlane android validate_internal",
    "bundle exec fastlane android upload_internal",
    "Google Play internal track",
    "draft release status",
    "SUPPLY_JSON_KEY",
    "SHAWARMA58_PRIVACY_POLICY_URL",
    "Do not put the service-account JSON, keystore or passwords in the repository.",
    "bundle install",
    "bundle install --path vendor/bundle",
    "python3 scripts/prepare_upload_keystore.py --strict",
    "python3 scripts/play_upload_auth_qa.py --strict",
    "python3 scripts/privacy_policy_hosting_qa.py --strict --fetch-privacy-url",
    "python3 scripts/fastlane_runtime_qa.py --strict",
    "python3 scripts/package_release_candidate.py --strict-signing --fetch-privacy-url --fetch-target-api-policy",
    "--strict-screenshots",
    "--strict-physical-device",
    "--strict-pre-upload",
    "python3 scripts/pre_upload_blockers_qa.py --strict",
    "python3 scripts/play_handoff_secret_scan_qa.py",
    "python3 scripts/post_package_validation_qa.py",
    "development headers",
    "Gemfile.lock",
]
FORBIDDEN_FASTFILE = [
    'track: "production"',
    "track('production')",
    'track("production")',
    'release_status: "completed"',
    "release_status('completed')",
    'skip_upload_aab: true',
    'skip_upload_metadata: true',
    'skip_upload_images: true',
    'skip_upload_screenshots: true',
    "rollout:",
]


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def add_check(checks: list[dict[str, str]], name: str, status: str, detail: str) -> None:
    checks.append({"name": name, "status": status, "detail": detail})


def main() -> None:
    checks: list[dict[str, str]] = []
    errors: list[str] = []

    missing = [rel(path) for path in REQUIRED_FILES if not path.exists()]
    if missing:
        errors.extend(f"missing file: {path}" for path in missing)
        add_check(checks, "Required fastlane files", "FAIL", ", ".join(missing))
    else:
        add_check(checks, "Required fastlane files", "PASS", f"{len(REQUIRED_FILES)} files present")

    fastfile = read(FASTFILE) if FASTFILE.exists() else ""
    appfile = read(APPFILE) if APPFILE.exists() else ""
    doc = read(DOC) if DOC.exists() else ""
    readme = read(FASTLANE_README) if FASTLANE_README.exists() else ""

    missing_fastfile = [snippet for snippet in FASTFILE_REQUIRED if snippet not in fastfile]
    if missing_fastfile:
        errors.extend(f"fastlane/Fastfile missing {snippet!r}" for snippet in missing_fastfile)
        add_check(checks, "Fastfile guarded lanes", "FAIL", f"{len(missing_fastfile)} snippets missing")
    else:
        add_check(checks, "Fastfile guarded lanes", "PASS", "internal draft validate/upload lanes configured")

    forbidden = [snippet for snippet in FORBIDDEN_FASTFILE if snippet in fastfile]
    if forbidden:
        errors.extend(f"fastlane/Fastfile contains forbidden snippet {snippet!r}" for snippet in forbidden)
        add_check(checks, "Fastfile unsafe upload guards", "FAIL", ", ".join(forbidden))
    else:
        add_check(checks, "Fastfile unsafe upload guards", "PASS", "no production/completed/skip-upload shortcuts")

    pre_upload_index = fastfile.find("python3 scripts/pre_upload_blockers_qa.py --strict")
    package_index = fastfile.find("python3 scripts/package_release_candidate.py --strict-signing")
    final_scan_index = fastfile.find("python3 scripts/play_handoff_secret_scan_qa.py", package_index)
    final_freshness_index = fastfile.find("python3 scripts/release_freshness_qa.py", package_index)
    post_package_index = fastfile.find("python3 scripts/post_package_validation_qa.py", package_index)
    late_pre_upload_index = fastfile.find("python3 scripts/pre_upload_blockers_qa.py --strict", package_index)
    if min(pre_upload_index, package_index, final_scan_index, final_freshness_index, post_package_index) < 0:
        errors.append("fastlane/Fastfile missing ordered pre-upload/package/post-package guard sequence")
        add_check(checks, "Fastfile upload guard order", "FAIL", "missing ordered guard marker")
    elif pre_upload_index < package_index < final_scan_index < final_freshness_index < post_package_index and late_pre_upload_index < 0:
        add_check(
            checks,
            "Fastfile upload guard order",
            "PASS",
            "strict pre-upload blockers run before package; final scan/freshness/post-package run after package; no pre-upload report rewrite after package",
        )
    else:
        errors.append("fastlane/Fastfile runs a mutating or final guard in the wrong order")
        add_check(
            checks,
            "Fastfile upload guard order",
            "FAIL",
            "expected pre_upload_blockers --strict before package, then secret scan, freshness and post-package validation",
        )

    missing_appfile = [snippet for snippet in APPFILE_REQUIRED if snippet not in appfile]
    if missing_appfile:
        errors.extend(f"fastlane/Appfile missing {snippet!r}" for snippet in missing_appfile)
        add_check(checks, "Appfile identity", "FAIL", f"{len(missing_appfile)} snippets missing")
    else:
        add_check(checks, "Appfile identity", "PASS", "package and service-account env var configured")

    combined_doc = doc + "\n" + readme
    missing_doc = [snippet for snippet in DOC_REQUIRED if snippet not in combined_doc]
    if missing_doc:
        errors.extend(f"fastlane docs missing {snippet!r}" for snippet in missing_doc)
        add_check(checks, "Fastlane upload docs", "FAIL", f"{len(missing_doc)} snippets missing")
    else:
        add_check(checks, "Fastlane upload docs", "PASS", "operator commands and secret rules documented")

    status = "FAIL" if errors else "PASS"
    report = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "checks": checks,
        "errors": errors,
    }
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Fastlane Config QA",
        "",
        f"Generated: {report['generatedAt']}",
        f"Status: `{status}`",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for check in checks:
        lines.append(f"| {check['name']} | {check['status']} | {check['detail']} |")
    if errors:
        lines.append("")
        lines.append("## Errors")
        for error in errors:
            lines.append(f"- {error}")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    if errors:
        print("Fastlane config QA failed")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print("Fastlane config QA PASS")


if __name__ == "__main__":
    main()
