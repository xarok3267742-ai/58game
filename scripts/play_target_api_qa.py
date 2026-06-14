#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_GRADLE = ROOT / "app/build.gradle.kts"
GOOGLE_PLAY_CHECKLIST = ROOT / "docs/google_play_checklist.md"
PRIVACY_NOTES = ROOT / "docs/privacy_and_permissions.md"
REPORT_JSON = ROOT / "build/reports/play_target_api.json"
REPORT_MD = ROOT / "build/reports/play_target_api.md"

TARGET_API_REQUIREMENT = 35
TARGET_ANDROID_VERSION = "Android 15"
POLICY_CHECK_DATE = "June 14, 2026"
TIMELINE_URL = "https://support.google.com/googleplay/android-developer/answer/11926878"
POLICY_URL = "https://support.google.com/googleplay/android-developer/answer/16561298"


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def status_from_checks(checks: list[Check]) -> str:
    if any(check.status == "FAIL" for check in checks):
        return "FAIL"
    if any(check.status == "WARN" for check in checks):
        return "PASS_WITH_WARNINGS"
    return "PASS"


def parse_gradle_int(source: str, name: str) -> int | None:
    match = re.search(rf"\b{name}\s*=\s*(\d+)", source)
    return int(match.group(1)) if match else None


def check_gradle_target_api() -> list[Check]:
    if not APP_GRADLE.exists():
        return [Check("Gradle build file", "FAIL", f"missing {rel(APP_GRADLE)}")]
    source = read_text(APP_GRADLE)
    target_sdk = parse_gradle_int(source, "targetSdk")
    compile_sdk = parse_gradle_int(source, "compileSdk")
    min_sdk = parse_gradle_int(source, "minSdk")
    checks: list[Check] = []
    if target_sdk is None:
        checks.append(Check("targetSdk declaration", "FAIL", "targetSdk is missing"))
    elif target_sdk < TARGET_API_REQUIREMENT:
        checks.append(
            Check(
                "Google Play mobile target API",
                "FAIL",
                f"targetSdk {target_sdk} < required {TARGET_API_REQUIREMENT}",
            ),
        )
    else:
        checks.append(
            Check(
                "Google Play mobile target API",
                "PASS",
                f"targetSdk {target_sdk} satisfies current mobile requirement {TARGET_API_REQUIREMENT}",
            ),
        )
    if compile_sdk is None:
        checks.append(Check("compileSdk declaration", "FAIL", "compileSdk is missing"))
    elif target_sdk is not None and compile_sdk < target_sdk:
        checks.append(Check("compileSdk coverage", "FAIL", f"compileSdk {compile_sdk} < targetSdk {target_sdk}"))
    else:
        detail = f"compileSdk {compile_sdk}"
        if target_sdk is not None:
            detail += f" covers targetSdk {target_sdk}"
        checks.append(Check("compileSdk coverage", "PASS", detail))
    if min_sdk is None:
        checks.append(Check("minSdk declaration", "FAIL", "minSdk is missing"))
    else:
        checks.append(Check("minSdk declaration", "PASS", f"minSdk {min_sdk}; target policy check is independent"))
    return checks


def check_policy_docs() -> list[Check]:
    checks: list[Check] = []
    if not GOOGLE_PLAY_CHECKLIST.exists():
        checks.append(Check("Google Play checklist target API notes", "FAIL", f"missing {rel(GOOGLE_PLAY_CHECKLIST)}"))
    else:
        checklist = read_text(GOOGLE_PLAY_CHECKLIST)
        required_terms = [
            f"`targetSdk`: {TARGET_API_REQUIREMENT}",
            "Google Play target API requirements",
            TIMELINE_URL,
            POLICY_URL,
            f"Checked on {POLICY_CHECK_DATE}",
        ]
        missing = [term for term in required_terms if term not in checklist]
        status = "PASS" if not missing else "FAIL"
        detail = "checklist records current source/date/requirement" if not missing else f"missing: {missing}"
        checks.append(Check("Google Play checklist target API notes", status, detail))
    if not PRIVACY_NOTES.exists():
        checks.append(Check("Privacy notes target API gate", "FAIL", f"missing {rel(PRIVACY_NOTES)}"))
    else:
        privacy_notes = read_text(PRIVACY_NOTES)
        required_terms = [
            "python3 scripts/play_target_api_qa.py",
            f"targetSdk >= {TARGET_API_REQUIREMENT}",
        ]
        missing = [term for term in required_terms if term not in privacy_notes]
        status = "PASS" if not missing else "FAIL"
        detail = "privacy/release notes reference standalone target API gate" if not missing else f"missing: {missing}"
        checks.append(Check("Privacy notes target API gate", status, detail))
    return checks


def fetch_url(url: str) -> str:
    fetch_url_value = f"{url}?hl=en" if "?" not in url else url
    request = urllib.request.Request(
        fetch_url_value,
        headers={"User-Agent": "Shawarma58TargetApiQa/1.0"},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read(512_000).decode("utf-8", errors="ignore")


def normalize_fetched_text(source: str) -> str:
    text = re.sub(r"<[^>]+>", " ", source)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text)


def check_fetched_policy() -> list[Check]:
    checks: list[Check] = []
    try:
        timeline = normalize_fetched_text(fetch_url(TIMELINE_URL))
    except (urllib.error.URLError, TimeoutError) as exc:
        checks.append(Check("Official target API timeline fetch", "FAIL", f"could not fetch timeline source: {exc}"))
    else:
        required_terms = [
            "new apps and app updates must target",
            f"{TARGET_ANDROID_VERSION} (API level {TARGET_API_REQUIREMENT})",
            "to be submitted to Google Play",
            "August 31, 2025",
        ]
        timeline_lower = timeline.lower()
        missing = [term for term in required_terms if term.lower() not in timeline_lower]
        status = "PASS" if not missing else "FAIL"
        detail = "official timeline still lists API 35 mobile submission baseline" if not missing else f"missing: {missing}"
        checks.append(Check("Official target API timeline fetch", status, detail))
    try:
        policy = normalize_fetched_text(fetch_url(POLICY_URL))
    except (urllib.error.URLError, TimeoutError) as exc:
        checks.append(Check("Official target API policy fetch", "FAIL", f"could not fetch policy source: {exc}"))
    else:
        required_terms = [
            "within one year of the latest major Android release",
            "prevented from app submission in Play Console",
            "For exact timelines and exceptions",
        ]
        policy_lower = policy.lower()
        missing = [term for term in required_terms if term.lower() not in policy_lower]
        status = "PASS" if not missing else "FAIL"
        detail = "official policy source records one-year target API rule" if not missing else f"missing: {missing}"
        checks.append(Check("Official target API policy fetch", status, detail))
    return checks


def write_reports(checks: list[Check], fetch_policy: bool) -> None:
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": status_from_checks(checks),
        "fetchPolicy": fetch_policy,
        "targetApiRequirement": TARGET_API_REQUIREMENT,
        "targetAndroidVersion": TARGET_ANDROID_VERSION,
        "policyCheckDate": POLICY_CHECK_DATE,
        "policySources": [TIMELINE_URL, POLICY_URL],
        "checks": [check.__dict__ for check in checks],
    }
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Play Target API QA",
        "",
        f"Generated: {payload['generatedAt']}",
        f"Status: {payload['status']}",
        f"Fetch official policy: `{fetch_policy}`",
        "",
        f"- Current mobile submission baseline: `{TARGET_ANDROID_VERSION} / API {TARGET_API_REQUIREMENT}`.",
        f"- Policy check date: `{POLICY_CHECK_DATE}`.",
        f"- Timeline source: {TIMELINE_URL}",
        f"- Policy source: {POLICY_URL}",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for check in checks:
        lines.append(f"| {check.name} | {check.status} | {check.detail} |")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fetch-policy",
        action="store_true",
        help="fetch official Google Play target API sources and fail if the expected current baseline text changes",
    )
    args = parser.parse_args()
    checks = [
        *check_gradle_target_api(),
        *check_policy_docs(),
    ]
    if args.fetch_policy:
        checks.extend(check_fetched_policy())
    write_reports(checks, fetch_policy=args.fetch_policy)
    failures = [check for check in checks if check.status == "FAIL"]
    if failures:
        print("Play target API QA failed")
        for failure in failures:
            print(f"- {failure.name}: {failure.detail}")
        raise SystemExit(1)
    print(f"Play target API QA PASS ({rel(REPORT_MD)})")


if __name__ == "__main__":
    main()
