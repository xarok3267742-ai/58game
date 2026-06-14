#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT_JSON = ROOT / "build/reports/pre_upload_blockers.json"
REPORT_MD = ROOT / "build/reports/pre_upload_blockers.md"

SOURCE_REPORTS = [
    ("build/reports/play_external_readiness.json", "Play external readiness"),
    ("build/reports/play_upload_auth.json", "Play upload auth"),
    ("build/reports/privacy_policy_hosting.json", "Privacy policy hosting"),
    ("build/reports/fastlane_runtime.json", "Fastlane runtime"),
    ("build/reports/signing_env.json", "Signing environment"),
    ("build/reports/upload_keystore_setup.json", "Upload keystore setup"),
    ("build/reports/physical_device_readiness.json", "Physical device readiness"),
    ("build/reports/artifact_provenance.json", "Artifact provenance"),
]

GROUPS = [
    {
        "id": "signing",
        "title": "Upload signing",
        "action": "Prepare or verify an upload keystore outside the repository, export SHAWARMA58_KEYSTORE, SHAWARMA58_KEYSTORE_PASSWORD, SHAWARMA58_KEY_ALIAS and SHAWARMA58_KEY_PASSWORD, rebuild bundleRelease, then rerun signing/artifact QA in strict mode.",
        "strictCommand": "python3 scripts/prepare_upload_keystore.py --strict && python3 scripts/signing_env_qa.py --strict && python3 scripts/artifact_provenance_qa.py --strict-signing",
    },
    {
        "id": "privacy_policy",
        "title": "Hosted privacy policy",
        "action": "Host privacy/hosting/privacy_policy.html from the Play handoff at a public, non-geofenced, non-PDF HTTPS URL, verify its SHA-256 against privacy/hosting/manifest.json, set SHAWARMA58_PRIVACY_POLICY_URL and verify the hosted page.",
        "strictCommand": "python3 scripts/privacy_policy_hosting_qa.py --strict --fetch-privacy-url && python3 scripts/play_external_readiness_qa.py --strict --fetch-privacy-url",
    },
    {
        "id": "play_console",
        "title": "Play Console access",
        "action": "Create the app in Play Console, keep forms ready from store/play_console_answers.md, and set SUPPLY_JSON_KEY to a service-account JSON outside the repository for fastlane.",
        "strictCommand": "python3 scripts/play_upload_auth_qa.py --strict && python3 scripts/play_external_readiness_qa.py --strict --fetch-privacy-url",
    },
    {
        "id": "fastlane_runtime",
        "title": "Fastlane runtime",
        "action": "Install a Ruby toolchain with matching development headers, run bundle install --path vendor/bundle, and verify bundle exec fastlane --version.",
        "strictCommand": "python3 scripts/fastlane_runtime_qa.py --strict && python3 scripts/play_external_readiness_qa.py --strict --fetch-privacy-url",
    },
    {
        "id": "physical_device",
        "title": "Physical-device sanity",
        "action": "Connect a real non-emulator Android phone, run the strict readiness script, then complete docs/physical_device_sanity.md before production rollout.",
        "strictCommand": "python3 scripts/physical_device_readiness_qa.py --strict",
    },
    {
        "id": "report_integrity",
        "title": "Report integrity",
        "action": "Regenerate the release gate so all required JSON reports exist and have a checks array.",
        "strictCommand": "python3 scripts/release_gate.py",
    },
    {
        "id": "other",
        "title": "Other blocker",
        "action": "Inspect the source QA report and resolve the remaining blocker before upload.",
        "strictCommand": "python3 scripts/release_gate.py",
    },
]
GROUP_BY_ID = {str(group["id"]): group for group in GROUPS}
ALLOWED_CHECK_STATUSES = {"PASS", "WARN", "PASS_WITH_WARNINGS", "EXTERNAL_BLOCKER", "FAIL"}


@dataclass(frozen=True)
class Issue:
    group: str
    source: str
    source_label: str
    name: str
    status: str
    detail: str


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def markdown_cell(value: object) -> str:
    return str(value).replace("\n", " ").replace("|", "\\|")


def classify_issue(source: str, name: str, detail: str) -> str:
    text = f"{source} {name} {detail}".lower()
    if "privacy" in text or "shawarma58_privacy_policy_url" in text:
        return "privacy_policy"
    if "service account" in text or "supply_json_key" in text or "play console" in text or "play_upload_auth" in text or "upload auth" in text:
        return "play_console"
    if "ruby" in text or "bundler" in text or "bundle check" in text or "vendor bundle" in text or "fastlane runtime" in text or "fastlane_runtime" in text:
        return "fastlane_runtime"
    if "physical" in text or "android phone" in text or "adb" in text:
        return "physical_device"
    if "signing" in text or "keystore" in text or "aab is unsigned" in text or "shawarma58_keystore" in text:
        return "signing"
    return "other"


def report_status_from_checks(checks: list[Any]) -> str:
    statuses = [
        str(check.get("status", "FAIL"))
        for check in checks
        if isinstance(check, dict)
    ]
    if any(status == "FAIL" for status in statuses):
        return "FAIL"
    if any(status == "EXTERNAL_BLOCKER" for status in statuses):
        return "EXTERNAL_BLOCKER"
    if any(status == "PASS_WITH_WARNINGS" for status in statuses):
        return "PASS_WITH_WARNINGS"
    return "PASS"


def load_source(relative: str, label: str) -> tuple[dict[str, object], list[Issue]]:
    path = ROOT / relative
    if not path.exists():
        return (
            {
                "path": relative,
                "label": label,
                "exists": False,
                "status": "FAIL",
                "generatedAt": "",
                "externalBlockers": 0,
                "failures": 1,
            },
            [
                Issue(
                    group="report_integrity",
                    source=relative,
                    source_label=label,
                    name="Required report",
                    status="FAIL",
                    detail="report file is missing",
                ),
            ],
        )
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return (
            {
                "path": relative,
                "label": label,
                "exists": True,
                "status": "FAIL",
                "generatedAt": "",
                "externalBlockers": 0,
                "failures": 1,
            },
            [
                Issue(
                    group="report_integrity",
                    source=relative,
                    source_label=label,
                    name="Report JSON",
                    status="FAIL",
                    detail=f"could not parse JSON: {exc}",
                ),
            ],
        )

    checks = report.get("checks")
    if not isinstance(checks, list):
        return (
            {
                "path": relative,
                "label": label,
                "exists": True,
                "status": "FAIL",
                "generatedAt": str(report.get("generatedAt", "")),
                "externalBlockers": 0,
                "failures": 1,
            },
            [
                Issue(
                    group="report_integrity",
                    source=relative,
                    source_label=label,
                    name="Report checks",
                    status="FAIL",
                    detail="report does not contain a checks array",
                ),
            ],
        )

    issues: list[Issue] = []
    invalid_status_count = 0
    for check in checks:
        if not isinstance(check, dict):
            invalid_status_count += 1
            continue
        name = str(check.get("name", "<unnamed>"))
        status = str(check.get("status", "FAIL"))
        detail = str(check.get("detail", ""))
        if status not in ALLOWED_CHECK_STATUSES:
            issues.append(
                Issue(
                    group="report_integrity",
                    source=relative,
                    source_label=label,
                    name=name,
                    status="FAIL",
                    detail=f"unknown status {status!r}",
                ),
            )
            continue
        if status in {"FAIL", "EXTERNAL_BLOCKER"}:
            issues.append(
                Issue(
                    group=classify_issue(relative, name, detail),
                    source=relative,
                    source_label=label,
                    name=name,
                    status=status,
                    detail=detail,
                ),
            )

    if invalid_status_count:
        issues.append(
            Issue(
                group="report_integrity",
                source=relative,
                source_label=label,
                name="Report checks",
                status="FAIL",
                detail=f"{invalid_status_count} check entries are not objects",
            ),
        )

    failures = len([issue for issue in issues if issue.status == "FAIL"])
    external = len([issue for issue in issues if issue.status == "EXTERNAL_BLOCKER"])
    summary = {
        "path": relative,
        "label": label,
        "exists": True,
        "status": report_status_from_checks(checks),
        "generatedAt": str(report.get("generatedAt", "")),
        "externalBlockers": external,
        "failures": failures,
    }
    return summary, issues


def dedupe_issues(issues: list[Issue]) -> list[Issue]:
    seen: set[tuple[str, str, str, str, str]] = set()
    unique: list[Issue] = []
    for issue in issues:
        key = (issue.group, issue.source, issue.name, issue.status, issue.detail)
        if key in seen:
            continue
        seen.add(key)
        unique.append(issue)
    return unique


def group_status(issues: list[Issue]) -> str:
    if any(issue.status == "FAIL" for issue in issues):
        return "FAIL"
    if any(issue.status == "EXTERNAL_BLOCKER" for issue in issues):
        return "EXTERNAL_BLOCKER"
    return "PASS"


def overall_status(issues: list[Issue], strict: bool) -> str:
    base = group_status(issues)
    if strict and base == "EXTERNAL_BLOCKER":
        return "FAIL"
    return base


def build_payload(strict: bool) -> dict[str, object]:
    sources: list[dict[str, object]] = []
    issues: list[Issue] = []
    for relative, label in SOURCE_REPORTS:
        source, source_issues = load_source(relative, label)
        sources.append(source)
        issues.extend(source_issues)
    issues = dedupe_issues(issues)
    grouped = []
    for group in GROUPS:
        group_id = str(group["id"])
        group_issues = [issue for issue in issues if issue.group == group_id]
        grouped.append(
            {
                "id": group_id,
                "title": group["title"],
                "status": group_status(group_issues),
                "action": group["action"],
                "strictCommand": group["strictCommand"],
                "items": [issue.__dict__ for issue in group_issues],
            },
        )
    payload = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": overall_status(issues, strict=strict),
        "baseStatus": group_status(issues),
        "strict": strict,
        "sources": sources,
        "blockerGroups": grouped,
        "issues": [issue.__dict__ for issue in issues],
    }
    return payload


def write_reports(payload: dict[str, object]) -> None:
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Pre-upload Blockers QA",
        "",
        f"Generated: {payload['generatedAt']}",
        f"Status: `{payload['status']}`",
        f"Base status: `{payload['baseStatus']}`",
        f"Strict mode: `{payload['strict']}`",
        "",
        "## Operator Actions",
        "| Area | Status | Next action | Strict check |",
        "|---|---|---|---|",
    ]
    groups = payload.get("blockerGroups")
    if isinstance(groups, list):
        for group in groups:
            if not isinstance(group, dict):
                continue
            if group.get("status") == "PASS":
                continue
            lines.append(
                "| {title} | {status} | {action} | `{strict}` |".format(
                    title=markdown_cell(group.get("title", "")),
                    status=markdown_cell(group.get("status", "")),
                    action=markdown_cell(group.get("action", "")),
                    strict=markdown_cell(group.get("strictCommand", "")),
                ),
            )
    if len(lines) == 10:
        lines.append("| None | PASS | No external upload blockers remain in the source reports. | `python3 scripts/package_release_candidate.py --strict-signing --fetch-privacy-url --fetch-target-api-policy --strict-screenshots --strict-physical-device --strict-pre-upload` |")

    lines.extend(
        [
            "",
            "## Source Reports",
            "| Source | Status | External blockers | Failures | Generated |",
            "|---|---|---:|---:|---|",
        ],
    )
    for source in payload.get("sources", []):
        if not isinstance(source, dict):
            continue
        lines.append(
            "| {source} | {status} | {external} | {failures} | {generated} |".format(
                source=markdown_cell(source.get("path", "")),
                status=markdown_cell(source.get("status", "")),
                external=markdown_cell(source.get("externalBlockers", "")),
                failures=markdown_cell(source.get("failures", "")),
                generated=markdown_cell(source.get("generatedAt", "")),
            ),
        )

    lines.extend(["", "## Blocking Items"])
    issues = payload.get("issues")
    if isinstance(issues, list) and issues:
        lines.extend(["| Area | Source | Check | Status | Detail |", "|---|---|---|---|---|"])
        for issue in issues:
            if not isinstance(issue, dict):
                continue
            group = GROUP_BY_ID.get(str(issue.get("group", "")), GROUP_BY_ID["other"])
            lines.append(
                "| {group} | {source} | {name} | {status} | {detail} |".format(
                    group=markdown_cell(group["title"]),
                    source=markdown_cell(issue.get("source", "")),
                    name=markdown_cell(issue.get("name", "")),
                    status=markdown_cell(issue.get("status", "")),
                    detail=markdown_cell(issue.get("detail", "")),
                ),
            )
    else:
        lines.append("No blocking items in the source reports.")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true", help="fail when any external upload blocker remains")
    args = parser.parse_args()

    payload = build_payload(strict=args.strict)
    write_reports(payload)

    status = str(payload["status"])
    if status == "FAIL":
        print(f"Pre-upload blockers QA failed ({rel(REPORT_MD)}, {rel(REPORT_JSON)})")
        for issue in payload.get("issues", []):
            if isinstance(issue, dict) and issue.get("status") in {"FAIL", "EXTERNAL_BLOCKER"}:
                print(f"- {issue.get('name')}: {issue.get('detail')}")
        raise SystemExit(1)
    if status == "EXTERNAL_BLOCKER":
        print(f"Pre-upload blockers QA EXTERNAL_BLOCKER ({rel(REPORT_MD)}, {rel(REPORT_JSON)})")
        for group in payload.get("blockerGroups", []):
            if isinstance(group, dict) and group.get("status") != "PASS":
                print(f"- {group.get('title')}: {group.get('action')}")
        return
    print(f"Pre-upload blockers QA PASS ({rel(REPORT_MD)}, {rel(REPORT_JSON)})")


if __name__ == "__main__":
    main()
