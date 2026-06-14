#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_JSON = ROOT / "build/reports/signing_env.json"
REPORT_MD = ROOT / "build/reports/signing_env.md"
REQUIRED_ENV = (
    "SHAWARMA58_KEYSTORE",
    "SHAWARMA58_KEYSTORE_PASSWORD",
    "SHAWARMA58_KEY_ALIAS",
    "SHAWARMA58_KEY_PASSWORD",
)
SECRET_SUFFIXES = {".jks", ".keystore", ".p12", ".pem"}
IGNORED_ROOTS = {".bundle", ".gradle", ".idea", "build", "app/build", "vendor/bundle"}


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def redact(value: str | None) -> str:
    if not value:
        return "<unset>"
    if len(value) <= 4:
        return "<set>"
    return f"{value[:2]}...{value[-2:]}"


def is_inside_root(path: Path) -> bool:
    try:
        resolved = path.resolve()
    except FileNotFoundError:
        resolved = path.absolute()
    root = ROOT.resolve()
    return resolved == root or root in resolved.parents


def is_ignored(relative: str) -> bool:
    return any(relative == root or relative.startswith(f"{root}/") for root in IGNORED_ROOTS)


def workspace_secret_files() -> list[str]:
    leaked: list[str] = []
    for current, dirs, filenames in os.walk(ROOT, onerror=lambda _error: None):
        current_path = Path(current)
        current_relative = "" if current_path == ROOT else relative(current_path)
        dirs[:] = [
            dirname
            for dirname in dirs
            if not is_ignored(f"{current_relative}/{dirname}".strip("/"))
        ]
        for filename in filenames:
            path = current_path / filename
            if path.suffix.lower() not in SECRET_SUFFIXES:
                continue
            leaked.append(relative(path))
    return sorted(leaked)


def keytool_path() -> str | None:
    candidates: list[Path] = []
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        candidates.append(Path(java_home) / "bin/keytool")
    path_candidate = shutil.which("keytool")
    if path_candidate:
        candidates.append(Path(path_candidate))
    candidates.append(Path("/Applications/Android Studio.app/Contents/jbr/Contents/Home/bin/keytool"))
    for candidate in candidates:
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def check_env_shape(strict: bool) -> tuple[Check, dict[str, str]]:
    values = {name: os.environ.get(name, "") for name in REQUIRED_ENV}
    set_names = [name for name, value in values.items() if value]
    missing = [name for name, value in values.items() if not value]
    if not set_names:
        status = "FAIL" if strict else "EXTERNAL_BLOCKER"
        detail = "upload signing env vars are not set"
        return Check("Signing env completeness", status, detail), values
    if missing:
        return Check("Signing env completeness", "FAIL", f"partial signing env; missing: {', '.join(missing)}"), values
    return Check("Signing env completeness", "PASS", "all upload signing env vars are set"), values


def check_keystore(values: dict[str, str]) -> list[Check]:
    store = values.get("SHAWARMA58_KEYSTORE", "")
    if not store:
        return []
    path = Path(store)
    checks: list[Check] = []
    if not path.is_absolute():
        checks.append(Check("Keystore path", "FAIL", "SHAWARMA58_KEYSTORE must be an absolute path"))
        return checks
    if is_inside_root(path):
        checks.append(Check("Keystore location", "FAIL", "keystore must be outside the project workspace"))
    else:
        checks.append(Check("Keystore location", "PASS", "keystore path is outside the project workspace"))
    if not path.exists():
        checks.append(Check("Keystore file", "FAIL", "keystore file does not exist"))
    elif not path.is_file():
        checks.append(Check("Keystore file", "FAIL", "keystore path is not a file"))
    else:
        checks.append(Check("Keystore file", "PASS", "keystore file exists"))
    return checks


def check_alias(values: dict[str, str]) -> Check | None:
    store = values.get("SHAWARMA58_KEYSTORE", "")
    store_password = values.get("SHAWARMA58_KEYSTORE_PASSWORD", "")
    alias = values.get("SHAWARMA58_KEY_ALIAS", "")
    if not store or not store_password or not alias:
        return None
    path = Path(store)
    if not path.exists() or not path.is_file():
        return None
    tool = keytool_path()
    if tool is None:
        return Check("Keystore alias", "WARN", "keytool unavailable; alias not verified")
    result = subprocess.run(
        [
            tool,
            "-list",
            "-keystore",
            str(path),
            "-storepass",
            store_password,
            "-alias",
            alias,
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode != 0:
        return Check("Keystore alias", "FAIL", "keytool could not verify alias with provided store password")
    return Check("Keystore alias", "PASS", "keytool verified alias with provided store password")


def write_reports(checks: list[Check], values: dict[str, str]) -> None:
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "checks": [check.__dict__ for check in checks],
        "env": {
            "SHAWARMA58_KEYSTORE": values.get("SHAWARMA58_KEYSTORE", ""),
            "SHAWARMA58_KEYSTORE_PASSWORD": redact(values.get("SHAWARMA58_KEYSTORE_PASSWORD")),
            "SHAWARMA58_KEY_ALIAS": redact(values.get("SHAWARMA58_KEY_ALIAS")),
            "SHAWARMA58_KEY_PASSWORD": redact(values.get("SHAWARMA58_KEY_PASSWORD")),
        },
    }
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Signing Environment QA",
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
            f"- `SHAWARMA58_KEYSTORE`: `{payload['env']['SHAWARMA58_KEYSTORE'] or '<unset>'}`",
            f"- `SHAWARMA58_KEYSTORE_PASSWORD`: `{payload['env']['SHAWARMA58_KEYSTORE_PASSWORD']}`",
            f"- `SHAWARMA58_KEY_ALIAS`: `{payload['env']['SHAWARMA58_KEY_ALIAS']}`",
            f"- `SHAWARMA58_KEY_PASSWORD`: `{payload['env']['SHAWARMA58_KEY_PASSWORD']}`",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true", help="fail when signing env is absent")
    args = parser.parse_args()

    checks: list[Check] = []
    env_check, values = check_env_shape(strict=args.strict)
    checks.append(env_check)
    checks.extend(check_keystore(values))
    alias_check = check_alias(values)
    if alias_check is not None:
        checks.append(alias_check)

    leaked = workspace_secret_files()
    if leaked:
        checks.append(Check("Workspace secret files", "FAIL", f"secret-like files found: {', '.join(leaked)}"))
    else:
        checks.append(Check("Workspace secret files", "PASS", "no .jks/.keystore/.p12/.pem files under source workspace"))

    write_reports(checks, values)

    failures = [check for check in checks if check.status == "FAIL"]
    if failures:
        print("Signing environment QA failed")
        for check in failures:
            print(f"- {check.name}: {check.detail}")
        print(f"Report: {relative(REPORT_MD)}")
        raise SystemExit(1)

    print("Signing environment QA summary")
    print("| Check | Status | Detail |")
    print("|---|---|---|")
    for check in checks:
        print(f"| {check.name} | {check.status} | {check.detail} |")
    print(f"\nReports: {relative(REPORT_MD)}, {relative(REPORT_JSON)}")


if __name__ == "__main__":
    main()
