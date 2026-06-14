#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_MANIFEST = ROOT / "app/src/main/AndroidManifest.xml"
RELEASE_MANIFEST = ROOT / "app/build/intermediates/merged_manifests/release/processReleaseManifest/AndroidManifest.xml"
APP_GRADLE = ROOT / "app/build.gradle.kts"
SOURCE_DIR = ROOT / "app/src/main/java"
PRIVACY_DOC = ROOT / "docs/privacy_and_permissions.md"
PLAY_ANSWERS = ROOT / "store/play_console_answers.md"
PRIVACY_POLICY = ROOT / "store/privacy_policy.html"
BACKUP_RULES = ROOT / "app/src/main/res/xml/backup_rules.xml"
DATA_EXTRACTION_RULES = ROOT / "app/src/main/res/xml/data_extraction_rules.xml"
REPORT_JSON = ROOT / "build/reports/privacy_data_safety.json"
REPORT_MD = ROOT / "build/reports/privacy_data_safety.md"
ANDROID_NS = "{http://schemas.android.com/apk/res/android}"

TARGET_API_REQUIREMENT = 35
EXPECTED_PACKAGE = "com.andrejivliev.shawarma58"
ALLOWED_RELEASE_PERMISSIONS = {
    f"{EXPECTED_PACKAGE}.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION",
}
PROHIBITED_PERMISSIONS = {
    "android.permission.INTERNET",
    "android.permission.ACCESS_NETWORK_STATE",
    "android.permission.ACCESS_WIFI_STATE",
    "android.permission.CAMERA",
    "android.permission.RECORD_AUDIO",
    "android.permission.POST_NOTIFICATIONS",
    "android.permission.READ_CONTACTS",
    "android.permission.WRITE_CONTACTS",
    "android.permission.ACCESS_FINE_LOCATION",
    "android.permission.ACCESS_COARSE_LOCATION",
    "android.permission.READ_EXTERNAL_STORAGE",
    "android.permission.WRITE_EXTERNAL_STORAGE",
    "android.permission.READ_MEDIA_IMAGES",
    "android.permission.READ_MEDIA_VIDEO",
    "android.permission.READ_MEDIA_AUDIO",
    "com.android.vending.BILLING",
    "com.google.android.gms.permission.AD_ID",
}
FORBIDDEN_GRADLE_MARKERS = {
    "firebase": "Firebase/backend",
    "play-services": "Google Play Services",
    "billingclient": "Google Play Billing",
    "admob": "Ads SDK",
    "play-services-ads": "Ads SDK",
    "analytics": "Analytics SDK",
    "crashlytics": "Crash reporting SDK",
    "sentry": "Crash reporting SDK",
    "retrofit": "Network client",
    "okhttp": "Network client",
    "ktor-client": "Network client",
    "coil": "Network image loader",
    "glide": "Network image loader",
    "picasso": "Network image loader",
    "webkit": "WebView/browser SDK",
    "browser": "Browser SDK",
}
FORBIDDEN_SOURCE_PATTERNS = {
    r"\bWebView\b": "WebView",
    r"\bHttpURLConnection\b|\bURL\(": "network API",
    r"\bokhttp3\b|\bRetrofit\b|\bKtor\b": "network client",
    r"\bFirebase\b|\bBillingClient\b|\bAdView\b|\bAdvertisingIdClient\b": "backend/ads/billing API",
}
REQUIRED_PLAY_ANSWER_TERMS = [
    "Contains ads: No",
    "In-app purchases: No",
    "Does the app collect or share any required user data types? No.",
    "Data shared with third parties: No.",
    "Dangerous permissions: none.",
    "INTERNET permission: absent.",
    "Accounts/login",
    "No data collected",
    "Users can delete local progress in the app settings",
]
REQUIRED_PRIVACY_POLICY_TERMS = [
    "не собирает",
    "не передаёт",
    "не продаёт",
    "не требует аккаунта",
    "не содержит рекламы",
    "не объявлено разрешение INTERNET",
    "резервное копирование Android",
    "сбросит прогресс в настройках приложения",
    "удалит приложение",
]


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def parse_manifest(path: Path) -> dict[str, object]:
    tree = ET.parse(path)
    root = tree.getroot()
    application = root.find("application")
    permissions = [
        node.attrib.get(f"{ANDROID_NS}name", "")
        for node in root.findall("uses-permission")
    ]
    return {
        "path": relative(path),
        "permissions": permissions,
        "allowBackup": application.attrib.get(f"{ANDROID_NS}allowBackup", "") if application is not None else "",
        "dataExtractionRules": application.attrib.get(f"{ANDROID_NS}dataExtractionRules", "") if application is not None else "",
        "fullBackupContent": application.attrib.get(f"{ANDROID_NS}fullBackupContent", "") if application is not None else "",
    }


def check_source_manifest(info: dict[str, object]) -> Check:
    permissions = info.get("permissions")
    if permissions:
        return Check("Source manifest permissions", "FAIL", f"source manifest declares permissions: {permissions}")
    if info.get("allowBackup") != "false":
        return Check("Source manifest backup", "FAIL", "android:allowBackup must be false")
    return Check("Source manifest privacy", "PASS", "no permissions; allowBackup=false")


def check_release_manifest(info: dict[str, object]) -> Check:
    permissions = [str(item) for item in info.get("permissions", [])]
    prohibited = sorted(set(permissions) & PROHIBITED_PERMISSIONS)
    unexpected = sorted(set(permissions) - ALLOWED_RELEASE_PERMISSIONS)
    if prohibited:
        return Check("Merged release permissions", "FAIL", f"prohibited permissions present: {prohibited}")
    if unexpected:
        return Check("Merged release permissions", "FAIL", f"unexpected permissions present: {unexpected}")
    return Check("Merged release permissions", "PASS", "only allowed signature-level AndroidX receiver permission is merged")


def check_target_api() -> Check:
    gradle = APP_GRADLE.read_text(encoding="utf-8")
    match = re.search(r"targetSdk\s*=\s*(\d+)", gradle)
    target = int(match.group(1)) if match else 0
    if target < TARGET_API_REQUIREMENT:
        return Check("Google Play target API", "FAIL", f"targetSdk {target} < {TARGET_API_REQUIREMENT}")
    return Check("Google Play target API", "PASS", f"targetSdk {target} >= {TARGET_API_REQUIREMENT}")


def check_backup_rules() -> Check:
    missing = [relative(path) for path in [BACKUP_RULES, DATA_EXTRACTION_RULES] if not path.exists()]
    if missing:
        return Check("Backup/data extraction rules", "FAIL", f"missing: {missing}")
    backup = BACKUP_RULES.read_text(encoding="utf-8")
    extraction = DATA_EXTRACTION_RULES.read_text(encoding="utf-8")
    if "<exclude" not in backup or "<exclude" not in extraction:
        return Check("Backup/data extraction rules", "FAIL", "backup and data extraction rules must exclude app data")
    return Check("Backup/data extraction rules", "PASS", "backup and device-transfer rules exclude app data")


def check_gradle_markers() -> Check:
    gradle = APP_GRADLE.read_text(encoding="utf-8").lower()
    hits = sorted({label for marker, label in FORBIDDEN_GRADLE_MARKERS.items() if marker in gradle})
    if hits:
        return Check("Forbidden SDK markers", "FAIL", f"found in Gradle file: {hits}")
    return Check("Forbidden SDK markers", "PASS", "no backend/network/ads/billing/analytics SDK markers in Gradle file")


def check_source_markers() -> Check:
    hits: list[str] = []
    for path in SOURCE_DIR.rglob("*.kt"):
        source = path.read_text(encoding="utf-8")
        for pattern, label in FORBIDDEN_SOURCE_PATTERNS.items():
            if re.search(pattern, source):
                hits.append(f"{relative(path)}: {label}")
    if hits:
        return Check("Forbidden source API markers", "FAIL", "; ".join(hits))
    return Check("Forbidden source API markers", "PASS", "no network/webview/backend/ads/billing API markers in app source")


def require_terms(path: Path, terms: list[str], check_name: str) -> Check:
    if not path.exists():
        return Check(check_name, "FAIL", f"missing file: {relative(path)}")
    text = path.read_text(encoding="utf-8")
    missing = [term for term in terms if term not in text]
    if missing:
        return Check(check_name, "FAIL", f"missing required terms: {missing}")
    return Check(check_name, "PASS", f"{relative(path)} contains required privacy/data-safety terms")


def check_privacy_doc() -> Check:
    if not PRIVACY_DOC.exists():
        return Check("Privacy notes", "FAIL", f"missing file: {relative(PRIVACY_DOC)}")
    text = PRIVACY_DOC.read_text(encoding="utf-8")
    required = [
        "no `INTERNET` permission",
        "Data collected: No.",
        "Data shared: No.",
        "android:allowBackup=\"false\"",
        "bestEndlessScore",
        "resets progress in app settings",
    ]
    missing = [term for term in required if term not in text]
    if missing:
        return Check("Privacy notes", "FAIL", f"missing required terms: {missing}")
    return Check("Privacy notes", "PASS", "privacy notes match no-collection/no-sharing claim")


def write_reports(checks: list[Check], details: dict[str, object]) -> None:
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "checks": [check.__dict__ for check in checks],
        "details": details,
        "policySources": [
            "https://support.google.com/googleplay/android-developer/answer/11926878",
            "https://support.google.com/googleplay/android-developer/answer/10787469",
        ],
    }
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Privacy Data Safety QA",
        "",
        f"Generated: {payload['generatedAt']}",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for check in checks:
        lines.append(f"| {check.name} | {check.status} | {check.detail} |")
    lines.extend(
        [
            "",
            "## Policy Sources Checked",
            "- https://support.google.com/googleplay/android-developer/answer/11926878",
            "- https://support.google.com/googleplay/android-developer/answer/10787469",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    required = [SOURCE_MANIFEST, APP_GRADLE, PRIVACY_DOC, PLAY_ANSWERS, PRIVACY_POLICY]
    missing = [relative(path) for path in required if not path.exists()]
    if missing:
        raise SystemExit(f"Missing privacy QA inputs: {missing}")

    source_manifest = parse_manifest(SOURCE_MANIFEST)
    release_manifest = parse_manifest(RELEASE_MANIFEST) if RELEASE_MANIFEST.exists() else {"permissions": []}
    checks = [
        check_source_manifest(source_manifest),
        check_release_manifest(release_manifest),
        check_target_api(),
        check_backup_rules(),
        check_gradle_markers(),
        check_source_markers(),
        require_terms(PLAY_ANSWERS, REQUIRED_PLAY_ANSWER_TERMS, "Play Console data-safety answers"),
        require_terms(PRIVACY_POLICY, REQUIRED_PRIVACY_POLICY_TERMS, "Privacy policy no-data terms"),
        check_privacy_doc(),
    ]
    details = {
        "sourceManifest": source_manifest,
        "releaseManifest": release_manifest,
    }
    write_reports(checks, details)

    failures = [check for check in checks if check.status == "FAIL"]
    if failures:
        print("Privacy data safety QA failed")
        for check in failures:
            print(f"- {check.name}: {check.detail}")
        print(f"Report: {relative(REPORT_MD)}")
        raise SystemExit(1)

    print("Privacy data safety QA summary")
    print("| Check | Status | Detail |")
    print("|---|---|---|")
    for check in checks:
        print(f"| {check.name} | {check.status} | {check.detail} |")
    print(f"\nReports: {relative(REPORT_MD)}, {relative(REPORT_JSON)}")


if __name__ == "__main__":
    main()
