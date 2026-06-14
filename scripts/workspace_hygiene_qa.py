#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_MD = ROOT / "build/reports/workspace_hygiene.md"
REPORT_JSON = ROOT / "build/reports/workspace_hygiene.json"
HANDOFF = ROOT / "build/play_handoff/shawarma58-v1.0.0"

REQUIRED_GITIGNORE_PATTERNS = [
    ".bundle/",
    "vendor/bundle/",
    "build/",
    "app/build/",
    "local.properties",
    "*.jks",
    "*.keystore",
    "fastlane/.env*",
    "fastlane/*.json",
]
IGNORED_ROOTS = {
    ".bundle",
    ".gradle",
    ".idea",
    "build",
    "app/build",
    "vendor/bundle",
}
SECRET_SUFFIXES = {".jks", ".keystore", ".p12", ".pfx", ".pem"}
SECRET_NAME_RE = re.compile(
    r"(google[-_]?play[-_]?service[-_]?account|service[-_]?account|private[-_]?key|upload[-_]?key|keystore)",
    re.IGNORECASE,
)
ALLOWED_HANDOFF_SECRET_LIKE_REPORTS = {
    "qa/upload_keystore_setup/upload_keystore_setup.json",
    "qa/upload_keystore_setup/upload_keystore_setup.md",
}
GENERATED_REPORT_DUPLICATE_RE = re.compile(r" \d+\.(json|md)$")
PLAY_HANDOFF_DUPLICATE_RE = re.compile(r" \d+(?:$|\.)")


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def is_ignored(relative: str) -> bool:
    return any(relative == root or relative.startswith(f"{root}/") for root in IGNORED_ROOTS)


def check_gitignore() -> list[Check]:
    gitignore = ROOT / ".gitignore"
    if not gitignore.exists():
        return [Check(".gitignore", "FAIL", "file is missing")]
    lines = {
        line.strip()
        for line in gitignore.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }
    checks: list[Check] = []
    for pattern in REQUIRED_GITIGNORE_PATTERNS:
        checks.append(
            Check(
                f".gitignore contains {pattern}",
                "PASS" if pattern in lines else "FAIL",
                "present" if pattern in lines else "missing",
            ),
        )
    return checks


def service_account_json(path: Path) -> bool:
    if path.suffix.lower() != ".json":
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False
    if not isinstance(payload, dict):
        return False
    required = {"type", "project_id", "private_key_id", "private_key", "client_email"}
    return payload.get("type") == "service_account" and required.issubset(payload.keys())


def source_secret_findings() -> list[str]:
    findings: list[str] = []
    for current, dirs, filenames in os.walk(ROOT, onerror=lambda _error: None):
        current_path = Path(current)
        current_relative = "" if current_path == ROOT else rel(current_path)
        dirs[:] = [
            dirname
            for dirname in dirs
            if not is_ignored(f"{current_relative}/{dirname}".strip("/"))
        ]
        for filename in filenames:
            path = current_path / filename
            relative = rel(path)
            if is_ignored(relative):
                continue
            suffix = path.suffix.lower()
            if suffix in SECRET_SUFFIXES:
                findings.append(relative)
                continue
            if suffix in {".json", ".txt", ""} and SECRET_NAME_RE.search(path.name):
                findings.append(relative)
                continue
            if service_account_json(path):
                findings.append(relative)
    return sorted(set(findings))


def check_source_secrets() -> Check:
    findings = source_secret_findings()
    if findings:
        return Check("Source workspace secret-like files", "FAIL", f"found: {', '.join(findings)}")
    return Check(
        "Source workspace secret-like files",
        "PASS",
        "no keystore, private-key or service-account files outside ignored/generated paths",
    )


def check_dependency_cache_policy() -> list[Check]:
    checks: list[Check] = []
    for relative in [".bundle", "vendor/bundle"]:
        path = ROOT / relative
        exists = path.exists()
        checks.append(
            Check(
                f"{relative} cache policy",
                "PASS",
                "exists but is ignored/generated" if exists else "absent and ignored if created",
            ),
        )
    return checks


def handoff_manifest_files() -> dict[str, object] | None:
    manifest = HANDOFF / "manifest.json"
    if not manifest.exists():
        return None
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    files = payload.get("files")
    return files if isinstance(files, dict) else None


def check_handoff_exclusions() -> list[Check]:
    files = handoff_manifest_files()
    if files is None:
        return [Check("Handoff manifest hygiene", "PASS", "handoff not present yet; checked after packaging")]
    forbidden_prefixes = (".bundle/", "vendor/", "local.properties", "fastlane/.env")
    forbidden: list[str] = []
    for relative in files:
        if relative in ALLOWED_HANDOFF_SECRET_LIKE_REPORTS:
            continue
        path = Path(relative)
        suffix = path.suffix.lower()
        if relative.startswith(forbidden_prefixes) or suffix in SECRET_SUFFIXES:
            forbidden.append(relative)
        if path.suffix.lower() == ".json" and SECRET_NAME_RE.search(path.name):
            forbidden.append(relative)
    if forbidden:
        return [Check("Handoff manifest hygiene", "FAIL", f"forbidden entries: {', '.join(sorted(forbidden))}")]
    return [Check("Handoff manifest hygiene", "PASS", f"{len(files)} manifest entries exclude local caches and secrets")]


def check_generated_report_duplicates() -> Check:
    reports_dir = ROOT / "build/reports"
    if not reports_dir.exists():
        return Check("Generated report duplicates", "PASS", "build/reports is absent before first package run")
    duplicates = sorted(
        rel(path)
        for path in reports_dir.iterdir()
        if path.is_file() and GENERATED_REPORT_DUPLICATE_RE.search(path.name)
    )
    if duplicates:
        return Check("Generated report duplicates", "FAIL", f"remove stale duplicate reports: {', '.join(duplicates)}")
    return Check("Generated report duplicates", "PASS", "no numbered duplicate report files under build/reports")


def check_play_handoff_duplicate_artifacts() -> Check:
    handoff_root = ROOT / "build/play_handoff"
    if not handoff_root.exists():
        return Check("Play handoff duplicate artifacts", "PASS", "build/play_handoff is absent before first package run")
    transfer_duplicates = sorted(
        rel(path)
        for path in handoff_root.iterdir()
        if PLAY_HANDOFF_DUPLICATE_RE.search(path.name)
    )
    handoff_duplicates: list[str] = []
    if HANDOFF.exists() and HANDOFF.is_dir():
        handoff_duplicates = sorted(
            rel(path)
            for path in HANDOFF.iterdir()
            if PLAY_HANDOFF_DUPLICATE_RE.search(path.name)
        )
    duplicates = [*transfer_duplicates, *handoff_duplicates]
    if duplicates:
        return Check("Play handoff duplicate artifacts", "FAIL", f"remove stale duplicate artifacts: {', '.join(duplicates)}")
    return Check(
        "Play handoff duplicate artifacts",
        "PASS",
        "no numbered duplicate artifacts in transfer root or current handoff root",
    )


def write_reports(checks: list[Check]) -> None:
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    status = "FAIL" if any(check.status == "FAIL" for check in checks) else "PASS"
    payload = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "checks": [check.__dict__ for check in checks],
        "ignoredRoots": sorted(IGNORED_ROOTS),
        "requiredGitignorePatterns": REQUIRED_GITIGNORE_PATTERNS,
    }
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Workspace Hygiene QA",
        "",
        f"Generated: {payload['generatedAt']}",
        f"Status: `{status}`",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for check in checks:
        lines.append(f"| {check.name} | {check.status} | {check.detail} |")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    checks = [
        *check_gitignore(),
        check_source_secrets(),
        *check_dependency_cache_policy(),
        *check_handoff_exclusions(),
        check_generated_report_duplicates(),
        check_play_handoff_duplicate_artifacts(),
    ]
    write_reports(checks)
    failures = [check for check in checks if check.status == "FAIL"]
    if failures:
        print("Workspace hygiene QA failed")
        for check in failures:
            print(f"- {check.name}: {check.detail}")
        print(f"Report: {rel(REPORT_MD)}")
        raise SystemExit(1)
    print(f"Workspace hygiene QA PASS ({rel(REPORT_MD)})")


if __name__ == "__main__":
    main()
