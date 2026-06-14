#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import stat
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT_JSON = ROOT / "build/reports/play_upload_auth.json"
REPORT_MD = ROOT / "build/reports/play_upload_auth.md"
SERVICE_ACCOUNT_ENV = "SUPPLY_JSON_KEY"
IGNORED_ROOTS = {
    ".bundle",
    ".gradle",
    ".idea",
    "app/build",
    "build",
    "vendor/bundle",
}
SERVICE_ACCOUNT_REQUIRED_FIELDS = {
    "type",
    "project_id",
    "private_key_id",
    "private_key",
    "client_email",
    "client_id",
    "auth_uri",
    "token_uri",
}
PRIVATE_KEY_RE = re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*-----END [A-Z0-9 ]*PRIVATE KEY-----", re.DOTALL)
SERVICE_ACCOUNT_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.gserviceaccount\.com$")


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def status_for_absent(strict: bool) -> str:
    return "FAIL" if strict else "EXTERNAL_BLOCKER"


def redact_path(raw: str) -> str:
    if not raw:
        return "<unset>"
    path = Path(raw)
    if path.name:
        return f".../{path.name}"
    return "<set>"


def redact_email(value: str) -> str:
    if "@" not in value:
        return "<set>"
    local, domain = value.split("@", 1)
    visible = local[:3] if len(local) > 3 else local[:1]
    return f"{visible}...@{domain}"


def is_inside_root(path: Path) -> bool:
    try:
        resolved = path.resolve()
    except FileNotFoundError:
        resolved = path.absolute()
    root = ROOT.resolve()
    return resolved == root or root in resolved.parents


def is_ignored(relative: str) -> bool:
    return any(relative == root or relative.startswith(f"{root}/") for root in IGNORED_ROOTS)


def service_account_json_payload(path: Path) -> dict[str, Any] | None:
    if path.suffix.lower() != ".json":
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    required_minimum = {"type", "project_id", "private_key_id", "private_key", "client_email"}
    if payload.get("type") == "service_account" and required_minimum.issubset(payload.keys()):
        return payload
    return None


def source_service_account_findings() -> list[str]:
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
            if not filename.endswith(".json"):
                continue
            path = current_path / filename
            relative = rel(path)
            if is_ignored(relative):
                continue
            if service_account_json_payload(path) is not None:
                findings.append(relative)
    return sorted(set(findings))

def check_source_workspace() -> Check:
    findings = source_service_account_findings()
    if findings:
        return Check("Source workspace service-account files", "FAIL", f"credential JSON found: {', '.join(findings)}")
    return Check("Source workspace service-account files", "PASS", "no Google service-account credential JSON outside ignored/generated paths")


def check_env(strict: bool) -> list[Check]:
    raw = os.environ.get(SERVICE_ACCOUNT_ENV, "").strip()
    if not raw:
        return [Check("Play upload auth env", status_for_absent(strict), "SUPPLY_JSON_KEY is not set")]

    path = Path(raw)
    checks: list[Check] = []
    if not path.is_absolute():
        checks.append(Check("Play upload auth path", "FAIL", "SUPPLY_JSON_KEY must be an absolute path"))
        return checks
    checks.append(Check("Play upload auth path", "PASS", "SUPPLY_JSON_KEY is absolute"))

    if is_inside_root(path):
        checks.append(Check("Play upload auth location", "FAIL", "service-account JSON must be outside the project workspace"))
    else:
        checks.append(Check("Play upload auth location", "PASS", "service-account JSON path is outside the project workspace"))

    if not path.exists():
        checks.append(Check("Play upload auth file", "FAIL", "service-account JSON file does not exist"))
        return checks
    if not path.is_file():
        checks.append(Check("Play upload auth file", "FAIL", "SUPPLY_JSON_KEY path is not a file"))
        return checks
    checks.append(Check("Play upload auth file", "PASS", "service-account JSON file exists"))

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        checks.append(Check("Play upload auth JSON", "FAIL", f"service-account file is not valid JSON: {exc}"))
        return checks
    if not isinstance(payload, dict):
        checks.append(Check("Play upload auth JSON", "FAIL", "service-account JSON root must be an object"))
        return checks

    missing = sorted(field for field in SERVICE_ACCOUNT_REQUIRED_FIELDS if not payload.get(field))
    if missing:
        checks.append(Check("Play upload auth JSON fields", "FAIL", f"missing required fields: {', '.join(missing)}"))
    elif payload.get("type") != "service_account":
        checks.append(Check("Play upload auth JSON fields", "FAIL", "type must be service_account"))
    else:
        checks.append(Check("Play upload auth JSON fields", "PASS", "required service-account fields are present"))

    private_key = str(payload.get("private_key", ""))
    if PRIVATE_KEY_RE.search(private_key):
        checks.append(Check("Play upload auth private key", "PASS", "private key PEM shape is present outside the workspace"))
    else:
        checks.append(Check("Play upload auth private key", "FAIL", "private_key does not look like a PEM private key"))

    client_email = str(payload.get("client_email", ""))
    if SERVICE_ACCOUNT_EMAIL_RE.match(client_email):
        checks.append(Check("Play upload auth client email", "PASS", f"client email shape is valid: {redact_email(client_email)}"))
    else:
        checks.append(Check("Play upload auth client email", "FAIL", "client_email must be a gserviceaccount.com address"))

    token_uri = str(payload.get("token_uri", ""))
    if token_uri == "https://oauth2.googleapis.com/token":
        checks.append(Check("Play upload auth token URI", "PASS", "token_uri matches Google OAuth token endpoint"))
    elif token_uri.startswith("https://"):
        checks.append(Check("Play upload auth token URI", "PASS", "token_uri is HTTPS"))
    else:
        checks.append(Check("Play upload auth token URI", "FAIL", "token_uri must be HTTPS"))

    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & stat.S_IWOTH:
        checks.append(Check("Play upload auth file mode", "FAIL", "service-account JSON must not be world-writable"))
    else:
        checks.append(Check("Play upload auth file mode", "PASS", "service-account JSON is not world-writable"))

    return checks


def write_reports(checks: list[Check], strict: bool) -> None:
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    statuses = [check.status for check in checks]
    if "FAIL" in statuses:
        status = "FAIL"
    elif "EXTERNAL_BLOCKER" in statuses:
        status = "EXTERNAL_BLOCKER"
    else:
        status = "PASS"
    payload = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "strict": strict,
        "env": {
            SERVICE_ACCOUNT_ENV: redact_path(os.environ.get(SERVICE_ACCOUNT_ENV, "")),
        },
        "checks": [check.__dict__ for check in checks],
    }
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Play Upload Auth QA",
        "",
        f"Generated: {payload['generatedAt']}",
        f"Status: `{status}`",
        f"Strict mode: `{strict}`",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for check in checks:
        lines.append(f"| {check.name} | {check.status} | {check.detail} |")
    lines.extend(
        [
            "",
            "## Environment",
            f"- `SUPPLY_JSON_KEY`: `{payload['env'][SERVICE_ACCOUNT_ENV]}`",
        ],
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true", help="fail when SUPPLY_JSON_KEY is absent")
    args = parser.parse_args()

    checks = [
        *check_env(strict=args.strict),
        check_source_workspace(),
    ]
    write_reports(checks, strict=args.strict)

    failures = [check for check in checks if check.status == "FAIL"]
    if failures:
        print("Play upload auth QA failed")
        for check in failures:
            print(f"- {check.name}: {check.detail}")
        print(f"Report: {rel(REPORT_MD)}")
        raise SystemExit(1)

    print("Play upload auth QA summary")
    print("| Check | Status | Detail |")
    print("|---|---|---|")
    for check in checks:
        print(f"| {check.name} | {check.status} | {check.detail} |")
    print(f"\nReports: {rel(REPORT_MD)}, {rel(REPORT_JSON)}")


if __name__ == "__main__":
    main()
