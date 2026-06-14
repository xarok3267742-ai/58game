#!/usr/bin/env python3
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAY_ANSWERS = ROOT / "store/play_console_answers.md"
UPLOAD_PACKET = ROOT / "store/play_upload_packet.md"
GOOGLE_PLAY_CHECKLIST = ROOT / "docs/google_play_checklist.md"
PRIVACY_POLICY = ROOT / "store/privacy_policy.html"
MANIFEST = ROOT / "app/src/main/AndroidManifest.xml"
REPORT_MD = ROOT / "build/reports/play_console_forms.md"
REPORT_JSON = ROOT / "build/reports/play_console_forms.json"
ANDROID_NS = "{http://schemas.android.com/apk/res/android}"

REQUIRED_FILES = [
    PLAY_ANSWERS,
    UPLOAD_PACKET,
    GOOGLE_PLAY_CHECKLIST,
    PRIVACY_POLICY,
    ROOT / "fastlane/metadata/android/ru-RU/title.txt",
    ROOT / "fastlane/metadata/android/ru-RU/short_description.txt",
    ROOT / "fastlane/metadata/android/ru-RU/full_description.txt",
    ROOT / "fastlane/metadata/android/ru-RU/changelogs/1.txt",
    ROOT / "store/play_icon.png",
    ROOT / "store/feature_graphic_concept.png",
    ROOT / "store/screenshots/shawarma_onboarding.png",
    ROOT / "store/screenshots/shawarma_menu.png",
    ROOT / "store/screenshots/shawarma_levels.png",
    ROOT / "store/screenshots/shawarma_gameplay.png",
    ROOT / "store/screenshots/shawarma_result.png",
]

SECTIONS = [
    "## App Details",
    "## Store Listing",
    "## Privacy Policy",
    "## App Access",
    "## Data Safety",
    "## Permissions",
    "## Content Rating",
    "## Other App Content Declarations",
    "## Target Audience",
    "## Release",
]
APP_DETAILS_TERMS = [
    "App name: Шаурма 58",
    "Default language: Russian (`ru-RU`)",
    "App or game: Game",
    "Category: Casual",
    "Free or paid: Free",
    "Contains ads: No",
    "In-app purchases: No",
]
STORE_TERMS = [
    "fastlane/metadata/android/ru-RU/title.txt",
    "fastlane/metadata/android/ru-RU/short_description.txt",
    "fastlane/metadata/android/ru-RU/full_description.txt",
    "fastlane/metadata/android/ru-RU/changelogs/1.txt",
    "store/play_icon.png",
    "store/feature_graphic_concept.png",
    "store/play_listing_ru.md",
]
PRIVACY_TERMS = [
    "public, non-geofenced, non-PDF URL",
    "Paste the hosted URL into Play Console",
    "developer contact email",
]
APP_ACCESS_TERMS = [
    "Does the app require login, membership, location-based access or special credentials? No.",
    "Are all app features available to reviewers immediately after install? Yes.",
    "no account, server, code, QR, payment or network connection is required",
]
DATA_SAFETY_TERMS = [
    "Does the app collect or share any required user data types? No.",
    "Not applicable; no user data is transmitted.",
    "Data shared with third parties: No.",
    "No data collected.",
    "Users can delete local progress in the app settings",
    "clearing app data",
]
PERMISSION_TERMS = [
    "Dangerous permissions: none.",
    "INTERNET permission: absent.",
    "camera, microphone: not used.",
]
CONTENT_RATING_TERMS = [
    "Violence: No.",
    "Fear/horror: No.",
    "Sexual content/nudity: No.",
    "Profanity: No.",
    "Controlled substances: No.",
    "Gambling or simulated gambling: No.",
    "User-generated content or user communication: No.",
    "Location sharing: No.",
    "Digital purchases: No.",
    "Ads: No.",
]
OTHER_DECLARATION_TERMS = [
    "News app: No.",
    "Health app: No.",
    "Government app: No.",
    "Financial features: No.",
    "COVID-19 contact tracing or status app: No.",
    "VPN service: No.",
    "Background location: No.",
    "Restricted content requiring reviewer credentials: No.",
]
TARGET_AUDIENCE_TERMS = [
    "Not specifically directed at children.",
    "Recommended Play Console target age selection: 13-15, 16-17, 18+.",
    "Do not opt into Designed for Families for v1.",
]
RELEASE_TERMS = [
    "app/build/outputs/bundle/release/app-release.aab",
    "do not upload it before configuring signing",
    "internal testing",
    "staged production rollout",
]
UPLOAD_PACKET_TERMS = [
    "Required policy answers for v1",
    "Data collected: No.",
    "Data shared: No.",
    "Data deletion: local progress can be reset in app settings",
    "Accounts/login: No.",
    "Target audience: not specifically directed at children",
    "python3 scripts/package_release_candidate.py --strict-signing --fetch-privacy-url --fetch-target-api-policy",
    "--strict-physical-device",
    "python3 scripts/pre_upload_blockers_qa.py --strict",
]
CHECKLIST_TERMS = [
    "Data safety: no data collected/shared",
    "Content rating: casual game",
    "Target audience: general casual Android users",
    "External readiness",
]
POLICY_SOURCES = [
    "https://support.google.com/googleplay/android-developer/answer/9859455",
    "https://support.google.com/googleplay/android-developer/answer/9867159",
    "https://support.google.com/googleplay/android-developer/answer/10787469",
]


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def require_terms(text: str, terms: list[str], name: str) -> Check:
    missing = [term for term in terms if term not in text]
    if missing:
        return Check(name, "FAIL", f"missing terms: {missing}")
    return Check(name, "PASS", f"{len(terms)} required terms present")


def check_required_files() -> Check:
    missing = [rel(path) for path in REQUIRED_FILES if not path.exists()]
    if missing:
        return Check("Play Console source files", "FAIL", f"missing files: {missing}")
    return Check("Play Console source files", "PASS", f"{len(REQUIRED_FILES)} files present")


def check_manifest_permissions() -> Check:
    tree = ET.parse(MANIFEST)
    root = tree.getroot()
    permissions = [node.attrib.get(f"{ANDROID_NS}name", "") for node in root.findall("uses-permission")]
    if permissions:
        return Check("Manifest permissions", "FAIL", f"source manifest declares permissions: {permissions}")
    return Check("Manifest permissions", "PASS", "source manifest declares no permissions")


def write_reports(checks: list[Check]) -> None:
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "checks": [check.__dict__ for check in checks],
        "policySources": POLICY_SOURCES,
    }
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Play Console Forms QA",
        "",
        f"Generated: {payload['generatedAt']}",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for check in checks:
        lines.append(f"| {check.name} | {check.status} | {check.detail} |")
    lines.extend(["", "## Policy Sources Checked"])
    for source in POLICY_SOURCES:
        lines.append(f"- {source}")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    checks = [check_required_files()]
    if any(check.status == "FAIL" for check in checks):
        write_reports(checks)
        print("Play Console forms QA failed")
        for check in checks:
            if check.status == "FAIL":
                print(f"- {check.name}: {check.detail}")
        raise SystemExit(1)

    answers = read(PLAY_ANSWERS)
    upload_packet = read(UPLOAD_PACKET)
    checklist = read(GOOGLE_PLAY_CHECKLIST)
    checks.extend(
        [
            require_terms(answers, SECTIONS, "Play answer sections"),
            require_terms(answers, APP_DETAILS_TERMS, "App details answers"),
            require_terms(answers, STORE_TERMS, "Store listing answers"),
            require_terms(answers, PRIVACY_TERMS, "Privacy policy answers"),
            require_terms(answers, APP_ACCESS_TERMS, "App access answers"),
            require_terms(answers, DATA_SAFETY_TERMS, "Data safety answers"),
            require_terms(answers, PERMISSION_TERMS, "Permission answers"),
            require_terms(answers, CONTENT_RATING_TERMS, "Content rating answers"),
            require_terms(answers, OTHER_DECLARATION_TERMS, "Other app-content declarations"),
            require_terms(answers, TARGET_AUDIENCE_TERMS, "Target audience answers"),
            require_terms(answers, RELEASE_TERMS, "Release answers"),
            require_terms(upload_packet, UPLOAD_PACKET_TERMS, "Upload packet policy summary"),
            require_terms(checklist, CHECKLIST_TERMS, "Google Play checklist policy summary"),
            check_manifest_permissions(),
        ],
    )
    write_reports(checks)
    failures = [check for check in checks if check.status == "FAIL"]
    if failures:
        print("Play Console forms QA failed")
        for check in failures:
            print(f"- {check.name}: {check.detail}")
        print(f"Report: {rel(REPORT_MD)}")
        raise SystemExit(1)
    print("Play Console forms QA PASS")


if __name__ == "__main__":
    main()
