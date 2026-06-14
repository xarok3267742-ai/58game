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
REPORT_JSON = ROOT / "build/reports/upload_keystore_setup.json"
REPORT_MD = ROOT / "build/reports/upload_keystore_setup.md"
DEFAULT_KEYSTORE = Path.home() / "shawarma58-upload/shawarma58-upload.jks"
DEFAULT_ALIAS = "shawarma58"
REQUIRED_ENV = (
    "SHAWARMA58_KEYSTORE",
    "SHAWARMA58_KEYSTORE_PASSWORD",
    "SHAWARMA58_KEY_ALIAS",
    "SHAWARMA58_KEY_PASSWORD",
)


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def redact(value: str | None) -> str:
    if not value:
        return "<unset>"
    if len(value) <= 4:
        return "<set>"
    return f"{value[:2]}...{value[-2:]}"


def status_for_absent(strict: bool) -> str:
    return "FAIL" if strict else "EXTERNAL_BLOCKER"


def is_inside_root(path: Path) -> bool:
    try:
        resolved = path.resolve()
    except FileNotFoundError:
        resolved = path.absolute()
    root = ROOT.resolve()
    return resolved == root or root in resolved.parents


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


def target_keystore(raw: str | None) -> Path:
    if raw:
        return Path(raw).expanduser()
    env_path = os.environ.get("SHAWARMA58_KEYSTORE", "").strip()
    if env_path:
        return Path(env_path).expanduser()
    return DEFAULT_KEYSTORE


def target_alias(raw: str | None) -> str:
    if raw:
        return raw
    return os.environ.get("SHAWARMA58_KEY_ALIAS", "").strip() or DEFAULT_ALIAS


def check_keytool(strict: bool) -> tuple[Check, str | None]:
    tool = keytool_path()
    if tool is None:
        return Check("keytool runtime", status_for_absent(strict), "keytool is not available"), None
    return Check("keytool runtime", "PASS", tool), tool


def check_path(path: Path, generate: bool, strict: bool) -> list[Check]:
    checks: list[Check] = []
    if not path.is_absolute():
        checks.append(Check("Keystore path", "FAIL", "keystore path must be absolute"))
        return checks
    if is_inside_root(path):
        checks.append(Check("Keystore location", "FAIL", "keystore must be outside the project workspace"))
    else:
        checks.append(Check("Keystore location", "PASS", "keystore path is outside the project workspace"))
    parent = path.parent
    if parent.exists() and parent.is_dir():
        checks.append(Check("Keystore parent", "PASS", "parent directory exists"))
    elif generate:
        checks.append(Check("Keystore parent", "PASS", "parent directory will be created outside the workspace"))
    else:
        checks.append(Check("Keystore parent", status_for_absent(strict), "parent directory is missing; rerun with --generate after setting env vars"))
    return checks


def check_password_env(strict: bool) -> Check:
    missing = [name for name in ("SHAWARMA58_KEYSTORE_PASSWORD", "SHAWARMA58_KEY_PASSWORD") if not os.environ.get(name)]
    if missing:
        return Check("Keystore password env", status_for_absent(strict), f"missing: {', '.join(missing)}")
    return Check("Keystore password env", "PASS", "store/key password env vars are set")


def check_gradle_env(path: Path, alias: str, strict: bool) -> list[Check]:
    checks: list[Check] = []
    raw_store = os.environ.get("SHAWARMA58_KEYSTORE", "").strip()
    raw_alias = os.environ.get("SHAWARMA58_KEY_ALIAS", "").strip()
    if not raw_store:
        checks.append(Check("Gradle keystore env", status_for_absent(strict), f"export SHAWARMA58_KEYSTORE={path}"))
    elif Path(raw_store).expanduser().resolve() != path.resolve():
        checks.append(Check("Gradle keystore env", "FAIL", "SHAWARMA58_KEYSTORE does not match the target keystore path"))
    else:
        checks.append(Check("Gradle keystore env", "PASS", "SHAWARMA58_KEYSTORE matches the target keystore"))
    if not raw_alias:
        checks.append(Check("Gradle key alias env", status_for_absent(strict), f"export SHAWARMA58_KEY_ALIAS={alias}"))
    elif raw_alias != alias:
        checks.append(Check("Gradle key alias env", "FAIL", "SHAWARMA58_KEY_ALIAS does not match the target alias"))
    else:
        checks.append(Check("Gradle key alias env", "PASS", "SHAWARMA58_KEY_ALIAS matches the target alias"))
    return checks


def create_keystore(path: Path, alias: str, dname: str, tool: str) -> Check:
    storepass = os.environ.get("SHAWARMA58_KEYSTORE_PASSWORD", "")
    keypass = os.environ.get("SHAWARMA58_KEY_PASSWORD", "")
    if path.exists():
        return Check("Keystore generation", "PASS", "keystore already exists; not overwritten")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.parent.chmod(0o700)
    except OSError:
        pass
    result = subprocess.run(
        [
            tool,
            "-genkeypair",
            "-v",
            "-keystore",
            str(path),
            "-storetype",
            "JKS",
            "-keyalg",
            "RSA",
            "-keysize",
            "4096",
            "-validity",
            "10000",
            "-alias",
            alias,
            "-storepass",
            storepass,
            "-keypass",
            keypass,
            "-dname",
            dname,
            "-noprompt",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode != 0:
        return Check("Keystore generation", "FAIL", "keytool failed to generate the upload keystore")
    return Check("Keystore generation", "PASS", "created upload keystore outside the workspace")


def check_keystore_file(path: Path, strict: bool) -> Check:
    if not path.exists():
        return Check("Keystore file", status_for_absent(strict), "keystore file is missing")
    if not path.is_file():
        return Check("Keystore file", "FAIL", "keystore path is not a file")
    return Check("Keystore file", "PASS", "keystore file exists")


def check_alias(path: Path, alias: str, tool: str | None, strict: bool) -> Check:
    if not path.exists() or not path.is_file():
        return Check("Keystore alias", status_for_absent(strict), "alias can be verified after keystore creation")
    storepass = os.environ.get("SHAWARMA58_KEYSTORE_PASSWORD", "")
    if not storepass:
        return Check("Keystore alias", status_for_absent(strict), "alias verification requires SHAWARMA58_KEYSTORE_PASSWORD")
    if tool is None:
        return Check("Keystore alias", status_for_absent(strict), "keytool is not available")
    result = subprocess.run(
        [
            tool,
            "-list",
            "-keystore",
            str(path),
            "-storepass",
            storepass,
            "-alias",
            alias,
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode != 0:
        return Check("Keystore alias", "FAIL", "keytool could not verify the alias with the provided store password")
    return Check("Keystore alias", "PASS", "keytool verified the upload-key alias")


def write_reports(path: Path, alias: str, generate: bool, checks: list[Check]) -> None:
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    status = "FAIL" if any(check.status == "FAIL" for check in checks) else (
        "EXTERNAL_BLOCKER" if any(check.status == "EXTERNAL_BLOCKER" for check in checks) else "PASS"
    )
    payload = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "generate": generate,
        "keystorePath": str(path),
        "alias": alias,
        "checks": [check.__dict__ for check in checks],
        "env": {
            "SHAWARMA58_KEYSTORE": os.environ.get("SHAWARMA58_KEYSTORE", "") or "<unset>",
            "SHAWARMA58_KEYSTORE_PASSWORD": redact(os.environ.get("SHAWARMA58_KEYSTORE_PASSWORD")),
            "SHAWARMA58_KEY_ALIAS": os.environ.get("SHAWARMA58_KEY_ALIAS", "") or "<unset>",
            "SHAWARMA58_KEY_PASSWORD": redact(os.environ.get("SHAWARMA58_KEY_PASSWORD")),
        },
    }
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Upload Keystore Setup",
        "",
        f"Generated: {payload['generatedAt']}",
        f"Status: `{status}`",
        f"Generate mode: `{generate}`",
        f"Keystore path: `{path}`",
        f"Alias: `{alias}`",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for check in checks:
        lines.append(f"| {check.name} | {check.status} | {check.detail} |")
    lines.extend(
        [
            "",
            "## Safe Usage",
            "Set passwords in the shell or CI secret store, not on the command line and not in the repository.",
            "",
            "```bash",
            f"export SHAWARMA58_KEYSTORE={path}",
            "export SHAWARMA58_KEYSTORE_PASSWORD=...",
            f"export SHAWARMA58_KEY_ALIAS={alias}",
            "export SHAWARMA58_KEY_PASSWORD=...",
            "python3 scripts/prepare_upload_keystore.py --generate",
            "python3 scripts/signing_env_qa.py --strict",
            "./gradlew bundleRelease",
            "python3 scripts/release_gate.py --strict-signing",
            "```",
        ],
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--keystore", default="", help="absolute upload keystore path; defaults to env or ~/shawarma58-upload/shawarma58-upload.jks")
    parser.add_argument("--alias", default="", help="upload key alias; defaults to env or shawarma58")
    parser.add_argument("--dname", default="CN=Shawarma 58 Upload, OU=Release, O=Shawarma 58, L=Almaty, ST=Almaty, C=KZ")
    parser.add_argument("--generate", action="store_true", help="create the keystore when missing; requires password env vars")
    parser.add_argument("--strict", action="store_true", help="fail when setup is incomplete")
    args = parser.parse_args()

    path = target_keystore(args.keystore or None)
    alias = target_alias(args.alias or None)
    checks: list[Check] = []
    keytool_check, tool = check_keytool(strict=args.strict)
    checks.append(keytool_check)
    checks.extend(check_path(path, generate=args.generate, strict=args.strict))
    checks.append(check_password_env(strict=args.strict))
    checks.extend(check_gradle_env(path, alias, strict=args.strict))
    can_generate = (
        args.generate
        and tool is not None
        and path.is_absolute()
        and not is_inside_root(path)
        and os.environ.get("SHAWARMA58_KEYSTORE_PASSWORD")
        and os.environ.get("SHAWARMA58_KEY_PASSWORD")
    )
    if args.generate and can_generate:
        checks.append(create_keystore(path, alias, args.dname, tool))
    elif args.generate:
        checks.append(Check("Keystore generation", status_for_absent(args.strict), "generation requires keytool, an absolute path outside the workspace and password env vars"))
    checks.append(check_keystore_file(path, strict=args.strict))
    checks.append(check_alias(path, alias, tool, strict=args.strict))
    write_reports(path, alias, generate=args.generate, checks=checks)

    failures = [check for check in checks if check.status == "FAIL"]
    blockers = [check for check in checks if check.status == "EXTERNAL_BLOCKER"]
    if failures or (args.strict and blockers):
        print("Upload keystore setup is not ready")
        for check in [*failures, *blockers]:
            print(f"- {check.name}: {check.detail}")
        print(f"Report: {rel(REPORT_MD)}")
        raise SystemExit(1)
    status = "EXTERNAL_BLOCKER" if blockers else "PASS"
    print(f"Upload keystore setup {status} ({rel(REPORT_MD)}, {rel(REPORT_JSON)})")


if __name__ == "__main__":
    main()
