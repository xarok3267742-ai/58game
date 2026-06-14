#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import fastlane_runtime_qa


ROOT = Path(__file__).resolve().parents[1]
REPORT_JSON = ROOT / "build/reports/play_external_readiness.json"
REPORT_MD = ROOT / "build/reports/play_external_readiness.md"
SIGNING_ENV = (
    "SHAWARMA58_KEYSTORE",
    "SHAWARMA58_KEYSTORE_PASSWORD",
    "SHAWARMA58_KEY_ALIAS",
    "SHAWARMA58_KEY_PASSWORD",
)
SERVICE_ACCOUNT_ENV = "SUPPLY_JSON_KEY"
PRIVACY_URL_ENV = "SHAWARMA58_PRIVACY_POLICY_URL"
SECRET_SUFFIXES = {".jks", ".keystore", ".p12", ".pem", ".json"}
IGNORED_ROOTS = {".bundle", ".gradle", ".idea", "build", "app/build", "vendor/bundle"}
LOCAL_PLACEHOLDER_HOSTS = {"example.com", "localhost", "127.0.0.1", "::1"}


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def is_ignored(relative: str) -> bool:
    return any(relative == root or relative.startswith(f"{root}/") for root in IGNORED_ROOTS)


def redact(value: str | None) -> str:
    if not value:
        return "<unset>"
    if len(value) <= 10:
        return "<set>"
    return f"{value[:4]}...{value[-4:]}"


def is_inside_root(path: Path) -> bool:
    try:
        resolved = path.resolve()
    except FileNotFoundError:
        resolved = path.absolute()
    root = ROOT.resolve()
    return resolved == root or root in resolved.parents


def status_for_absent(strict: bool) -> str:
    return "FAIL" if strict else "EXTERNAL_BLOCKER"


def check_signing_env(strict: bool) -> list[Check]:
    values = {name: os.environ.get(name, "") for name in SIGNING_ENV}
    set_names = [name for name, value in values.items() if value]
    missing = [name for name, value in values.items() if not value]
    if not set_names:
        return [Check("Upload signing env", status_for_absent(strict), "SHAWARMA58_KEYSTORE* env vars are not set")]
    checks: list[Check] = []
    if missing:
        checks.append(Check("Upload signing env", "FAIL", f"partial signing env; missing: {', '.join(missing)}"))
        return checks
    checks.append(Check("Upload signing env", "PASS", "all SHAWARMA58_KEYSTORE* env vars are set"))
    keystore = Path(values["SHAWARMA58_KEYSTORE"])
    if not keystore.is_absolute():
        checks.append(Check("Upload keystore path", "FAIL", "SHAWARMA58_KEYSTORE must be an absolute path"))
    elif is_inside_root(keystore):
        checks.append(Check("Upload keystore location", "FAIL", "keystore must be outside the project workspace"))
    elif not keystore.exists():
        checks.append(Check("Upload keystore file", "FAIL", "keystore file does not exist"))
    elif not keystore.is_file():
        checks.append(Check("Upload keystore file", "FAIL", "keystore path is not a file"))
    else:
        checks.append(Check("Upload keystore file", "PASS", "keystore exists outside the workspace"))
    return checks


def check_service_account(strict: bool) -> list[Check]:
    raw = os.environ.get(SERVICE_ACCOUNT_ENV, "")
    if not raw:
        return [Check("Play service account", status_for_absent(strict), "SUPPLY_JSON_KEY is not set")]
    path = Path(raw)
    checks: list[Check] = []
    if not path.is_absolute():
        checks.append(Check("Play service account path", "FAIL", "SUPPLY_JSON_KEY must be an absolute path"))
        return checks
    if is_inside_root(path):
        checks.append(Check("Play service account location", "FAIL", "service-account JSON must be outside the project workspace"))
    if not path.exists():
        checks.append(Check("Play service account file", "FAIL", "service-account JSON file does not exist"))
        return checks
    if not path.is_file():
        checks.append(Check("Play service account file", "FAIL", "SUPPLY_JSON_KEY path is not a file"))
        return checks
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        checks.append(Check("Play service account JSON", "FAIL", f"service-account file is not valid JSON: {exc}"))
        return checks
    required = ["type", "project_id", "private_key_id", "private_key", "client_email"]
    missing = [key for key in required if not payload.get(key)]
    if missing:
        checks.append(Check("Play service account JSON", "FAIL", f"missing required service-account fields: {', '.join(missing)}"))
    elif payload.get("type") != "service_account":
        checks.append(Check("Play service account JSON", "FAIL", "JSON key type must be service_account"))
    else:
        checks.append(Check("Play service account JSON", "PASS", f"service account parsed for {payload.get('client_email')}"))
    return checks


def check_privacy_url(strict: bool, fetch: bool) -> list[Check]:
    raw = os.environ.get(PRIVACY_URL_ENV, "").strip()
    if not raw:
        return [Check("Hosted privacy policy URL", status_for_absent(strict), "SHAWARMA58_PRIVACY_POLICY_URL is not set")]
    parsed = urlparse(raw)
    checks: list[Check] = []
    if parsed.scheme != "https":
        checks.append(Check("Hosted privacy policy URL", "FAIL", "privacy policy URL must use https"))
    host = parsed.hostname or ""
    if host.lower() in LOCAL_PLACEHOLDER_HOSTS:
        checks.append(Check("Hosted privacy policy URL", "FAIL", "privacy policy URL must not use placeholder/local host"))
    if parsed.path.lower().endswith(".pdf"):
        checks.append(Check("Hosted privacy policy URL", "FAIL", "privacy policy URL must be a web page, not a PDF"))
    if not checks:
        checks.append(Check("Hosted privacy policy URL", "PASS", "URL shape is HTTPS and non-PDF"))
    if fetch and not any(check.status == "FAIL" for check in checks):
        request = urllib.request.Request(raw, method="GET", headers={"User-Agent": "Shawarma58ReleaseQa/1.0"})
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                body = response.read(128_000).decode("utf-8", errors="ignore")
                content_type = response.headers.get("content-type", "")
                if response.status >= 400:
                    checks.append(Check("Hosted privacy policy fetch", "FAIL", f"HTTP status {response.status}"))
                elif "Шаурма 58" not in body or "не собирает" not in body:
                    checks.append(Check("Hosted privacy policy fetch", "FAIL", "hosted page does not contain expected app/privacy terms"))
                elif "pdf" in content_type.lower():
                    checks.append(Check("Hosted privacy policy fetch", "FAIL", f"content-type must not be PDF: {content_type}"))
                else:
                    checks.append(Check("Hosted privacy policy fetch", "PASS", f"HTTP {response.status}; expected terms found"))
        except (urllib.error.URLError, TimeoutError) as exc:
            checks.append(Check("Hosted privacy policy fetch", "FAIL", f"could not fetch privacy policy URL: {exc}"))
    return checks


def check_fastlane_runtime(strict: bool) -> list[Check]:
    runtime_checks = [
        fastlane_runtime_qa.check_gemfile(),
        *fastlane_runtime_qa.check_lockfile(),
        fastlane_runtime_qa.check_bundle_config(),
        *fastlane_runtime_qa.check_ruby(strict=strict),
        fastlane_runtime_qa.check_ruby_toolchain_options(),
        *fastlane_runtime_qa.check_bundler(strict=strict),
        fastlane_runtime_qa.check_vendor_bundle(strict=strict),
        fastlane_runtime_qa.check_fastlane(strict=strict),
    ]
    return [Check(check.name, check.status, check.detail) for check in runtime_checks]


def check_workspace_secret_files() -> Check:
    leaked: list[str] = []
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
            if path.suffix.lower() not in SECRET_SUFFIXES:
                continue
            leaked.append(rel(path))
    if leaked:
        return Check("Workspace secret files", "FAIL", f"secret-like files found: {', '.join(sorted(leaked))}")
    return Check("Workspace secret files", "PASS", "no keystore/service-account-like files under source workspace")


def write_reports(checks: list[Check]) -> None:
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "checks": [check.__dict__ for check in checks],
        "env": {
            "SUPPLY_JSON_KEY": os.environ.get(SERVICE_ACCOUNT_ENV, "") or "<unset>",
            "SHAWARMA58_PRIVACY_POLICY_URL": os.environ.get(PRIVACY_URL_ENV, "") or "<unset>",
            "SHAWARMA58_KEYSTORE": os.environ.get("SHAWARMA58_KEYSTORE", "") or "<unset>",
            "SHAWARMA58_KEYSTORE_PASSWORD": redact(os.environ.get("SHAWARMA58_KEYSTORE_PASSWORD")),
            "SHAWARMA58_KEY_ALIAS": redact(os.environ.get("SHAWARMA58_KEY_ALIAS")),
            "SHAWARMA58_KEY_PASSWORD": redact(os.environ.get("SHAWARMA58_KEY_PASSWORD")),
        },
    }
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Play External Readiness QA",
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
            "## Environment",
            f"- `SUPPLY_JSON_KEY`: `{payload['env']['SUPPLY_JSON_KEY']}`",
            f"- `SHAWARMA58_PRIVACY_POLICY_URL`: `{payload['env']['SHAWARMA58_PRIVACY_POLICY_URL']}`",
            f"- `SHAWARMA58_KEYSTORE`: `{payload['env']['SHAWARMA58_KEYSTORE']}`",
            f"- `SHAWARMA58_KEYSTORE_PASSWORD`: `{payload['env']['SHAWARMA58_KEYSTORE_PASSWORD']}`",
            f"- `SHAWARMA58_KEY_ALIAS`: `{payload['env']['SHAWARMA58_KEY_ALIAS']}`",
            f"- `SHAWARMA58_KEY_PASSWORD`: `{payload['env']['SHAWARMA58_KEY_PASSWORD']}`",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true", help="fail when external Play upload inputs are absent")
    parser.add_argument("--fetch-privacy-url", action="store_true", help="fetch and inspect the hosted privacy policy URL")
    args = parser.parse_args()

    checks: list[Check] = []
    checks.extend(check_signing_env(strict=args.strict))
    checks.extend(check_service_account(strict=args.strict))
    checks.extend(check_privacy_url(strict=args.strict, fetch=args.fetch_privacy_url))
    checks.extend(check_fastlane_runtime(strict=args.strict))
    checks.append(check_workspace_secret_files())
    write_reports(checks)

    failures = [check for check in checks if check.status == "FAIL"]
    if failures:
        print("Play external readiness QA failed")
        for check in failures:
            print(f"- {check.name}: {check.detail}")
        print(f"Report: {rel(REPORT_MD)}")
        raise SystemExit(1)

    print("Play external readiness QA summary")
    print("| Check | Status | Detail |")
    print("|---|---|---|")
    for check in checks:
        print(f"| {check.name} | {check.status} | {check.detail} |")
    print(f"\nReports: {rel(REPORT_MD)}, {rel(REPORT_JSON)}")


if __name__ == "__main__":
    main()
