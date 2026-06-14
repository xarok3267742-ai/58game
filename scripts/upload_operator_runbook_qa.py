#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNBOOK = ROOT / "docs/upload_operator_runbook.md"
REPORT_MD = ROOT / "build/reports/upload_operator_runbook.md"
REPORT_JSON = ROOT / "build/reports/upload_operator_runbook.json"

REQUIRED_ENV = [
    "SHAWARMA58_KEYSTORE",
    "SHAWARMA58_KEYSTORE_PASSWORD",
    "SHAWARMA58_KEY_ALIAS",
    "SHAWARMA58_KEY_PASSWORD",
    "SUPPLY_JSON_KEY",
    "SHAWARMA58_PRIVACY_POLICY_URL",
]
REQUIRED_COMMANDS = [
    "bundle install --path vendor/bundle",
    "python3 scripts/fastlane_runtime_qa.py --strict",
    "python3 scripts/prepare_upload_keystore.py --strict",
    "python3 scripts/signing_env_qa.py --strict",
    "python3 scripts/play_upload_auth_qa.py --strict",
    "python3 scripts/privacy_policy_hosting_qa.py --strict --fetch-privacy-url",
    "python3 scripts/physical_device_readiness_qa.py --strict",
    "python3 scripts/play_external_readiness_qa.py --strict --fetch-privacy-url",
    "./gradlew bundleRelease",
    "python3 scripts/artifact_provenance_qa.py --strict-signing",
    "python3 scripts/pre_upload_blockers_qa.py --strict",
    "python3 scripts/package_release_candidate.py --strict-signing --fetch-privacy-url --fetch-target-api-policy --strict-screenshots --strict-physical-device --strict-pre-upload",
    "python3 scripts/post_package_validation_qa.py",
    "cd build/play_handoff && shasum -a 256 -c shawarma58-v1.0.0.zip.sha256",
    "shasum -a 256 -c CHECKSUMS.txt",
    "bundle exec fastlane android validate_internal",
    "bundle exec fastlane android upload_internal",
]
REQUIRED_TERMS = [
    "outside the repository",
    "public HTTPS",
    "non-PDF",
    "non-emulator Android phone",
    "manifest.json",
    "signing.status = signed",
    "build/reports/post_package_validation.md",
    "--strict-pre-upload",
    "play_handoff_secret_scan_qa.py",
    "upload/app-release.aab",
    "deobfuscation/release/",
    "relative to the generated handoff root",
]
FORBIDDEN_PATTERNS = {
    "private key block": re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"),
    "service-account private_key field": re.compile(r'"private_key"\s*:'),
    "service-account client_email field": re.compile(r'"client_email"\s*:'),
    "developer placeholder": re.compile(r"\b(TODO|FIXME|lorem ipsum)\b", re.IGNORECASE),
}


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def missing_terms(text: str, terms: list[str]) -> list[str]:
    return [term for term in terms if term not in text]


def command_block_has_strict_order(text: str) -> bool:
    section_start = text.find("## Rebuild And Package")
    section_end = text.find("From the repository root", section_start)
    section = text[section_start:section_end] if section_start >= 0 and section_end > section_start else text
    pre_upload_index = section.find("python3 scripts/pre_upload_blockers_qa.py --strict")
    package_index = section.find("python3 scripts/package_release_candidate.py --strict-signing")
    post_package_index = section.find("python3 scripts/post_package_validation_qa.py", package_index)
    late_pre_upload_index = section.find("python3 scripts/pre_upload_blockers_qa.py --strict", package_index)
    return (
        pre_upload_index >= 0
        and package_index >= 0
        and post_package_index >= 0
        and pre_upload_index < package_index < post_package_index
        and late_pre_upload_index < 0
    )


def write_reports(checks: list[Check]) -> None:
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    status = "FAIL" if any(check.status == "FAIL" for check in checks) else "PASS"
    payload = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "runbook": rel(RUNBOOK),
        "checks": [check.__dict__ for check in checks],
        "requiredEnv": REQUIRED_ENV,
        "requiredCommands": REQUIRED_COMMANDS,
    }
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Upload Operator Runbook QA",
        "",
        f"Generated: {payload['generatedAt']}",
        f"Status: `{status}`",
        f"Runbook: `{payload['runbook']}`",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for check in checks:
        lines.append(f"| {check.name} | {check.status} | {check.detail} |")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    checks: list[Check] = []
    if not RUNBOOK.exists():
        checks.append(Check("Runbook file", "FAIL", f"missing {rel(RUNBOOK)}"))
        write_reports(checks)
        raise SystemExit("Upload operator runbook QA failed")

    text = RUNBOOK.read_text(encoding="utf-8")
    checks.append(Check("Runbook file", "PASS", f"{rel(RUNBOOK)} exists"))

    env_missing = missing_terms(text, REQUIRED_ENV)
    checks.append(
        Check(
            "Required environment variables",
            "FAIL" if env_missing else "PASS",
            f"missing: {env_missing}" if env_missing else f"{len(REQUIRED_ENV)} variables documented",
        ),
    )

    command_missing = missing_terms(text, REQUIRED_COMMANDS)
    checks.append(
        Check(
            "Required strict commands",
            "FAIL" if command_missing else "PASS",
            f"missing: {command_missing}" if command_missing else f"{len(REQUIRED_COMMANDS)} commands documented",
        ),
    )

    if command_block_has_strict_order(text):
        checks.append(
            Check(
                "Strict package command order",
                "PASS",
                "strict pre-upload blockers run before package; post-package validation runs after package; no pre-upload report rewrite after package",
            ),
        )
    else:
        checks.append(
            Check(
                "Strict package command order",
                "FAIL",
                "expected Rebuild And Package command block to run pre_upload_blockers --strict before package, then post_package_validation after package without a second pre-upload report rewrite",
            ),
        )

    term_missing = missing_terms(text, REQUIRED_TERMS)
    checks.append(
        Check(
            "Required operator terms",
            "FAIL" if term_missing else "PASS",
            f"missing: {term_missing}" if term_missing else f"{len(REQUIRED_TERMS)} terms documented",
        ),
    )

    for name, pattern in FORBIDDEN_PATTERNS.items():
        matches = pattern.findall(text)
        checks.append(
            Check(
                f"Forbidden {name}",
                "FAIL" if matches else "PASS",
                f"{len(matches)} match(es)",
            ),
        )

    write_reports(checks)
    failures = [check for check in checks if check.status == "FAIL"]
    if failures:
        print("Upload operator runbook QA failed")
        for failure in failures:
            print(f"- {failure.name}: {failure.detail}")
        print(f"Report: {rel(REPORT_MD)}")
        raise SystemExit(1)
    print(f"Upload operator runbook QA PASS ({rel(REPORT_MD)}, {rel(REPORT_JSON)})")


if __name__ == "__main__":
    main()
