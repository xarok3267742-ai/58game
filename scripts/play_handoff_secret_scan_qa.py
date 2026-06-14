#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HANDOFF = ROOT / "build/play_handoff/shawarma58-v1.0.0"
REPORT_MD = ROOT / "build/reports/play_handoff_secret_scan.md"
REPORT_JSON = ROOT / "build/reports/play_handoff_secret_scan.json"

SECRET_SUFFIXES = {".jks", ".keystore", ".p12", ".pfx", ".pem"}
SECRET_NAME_RE = re.compile(
    r"(google[-_]?play[-_]?service[-_]?account|service[-_]?account|private[-_]?key|upload[-_]?key|keystore)",
    re.IGNORECASE,
)
PRIVATE_KEY_BLOCK_RE = re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")
SERVICE_ACCOUNT_EMAIL_RE = re.compile(r'"client_email"\s*:\s*"[^"]+@[^"]+\.gserviceaccount\.com"')
PRIVATE_KEY_JSON_RE = re.compile(r'"private_key"\s*:\s*"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----')
TEXT_SUFFIXES = {
    ".cfg",
    ".gradle",
    ".html",
    ".json",
    ".kts",
    ".lock",
    ".md",
    ".pro",
    ".properties",
    ".rb",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}
TEXT_NAMES = {"Appfile", "Fastfile", "Gemfile", "README"}
MAX_TEXT_BYTES = 2_000_000
ALLOWED_SECRET_LIKE_NAMES = {
    "qa/upload_keystore_setup/upload_keystore_setup.json",
    "shawarma58-v1.0.0/qa/upload_keystore_setup/upload_keystore_setup.json",
}


@dataclass(frozen=True)
class Finding:
    scope: str
    path: str
    rule: str
    detail: str


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def archive_for(handoff: Path) -> Path:
    return handoff.parent / f"{handoff.name}.zip"


def sidecars_for(archive: Path) -> list[Path]:
    return [
        archive.with_suffix(archive.suffix + ".json"),
        archive.with_suffix(archive.suffix + ".package.json"),
        archive.with_suffix(archive.suffix + ".package.md"),
        archive.with_suffix(archive.suffix + ".sha256"),
    ]


def load_manifest_file_list(handoff: Path) -> tuple[list[str], Check | None]:
    manifest_path = handoff / "manifest.json"
    if not manifest_path.exists():
        return [], Check("Handoff manifest", "FAIL", f"missing {rel(manifest_path)}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [], Check("Handoff manifest", "FAIL", f"could not parse manifest JSON: {exc}")
    files = manifest.get("files")
    if not isinstance(files, dict):
        return [], Check("Handoff manifest", "FAIL", "manifest.files must be an object")
    return sorted(set(str(relative) for relative in files) | {"manifest.json"}), None


def should_scan_text(name: str, size: int) -> bool:
    path = Path(name)
    if size > MAX_TEXT_BYTES:
        return False
    return path.suffix.lower() in TEXT_SUFFIXES or path.name in TEXT_NAMES


def secret_name_finding(scope: str, name: str) -> Finding | None:
    if name in ALLOWED_SECRET_LIKE_NAMES:
        return None
    path = Path(name)
    suffix = path.suffix.lower()
    if suffix in SECRET_SUFFIXES:
        return Finding(scope, name, "secret-like file extension", f"forbidden suffix {suffix}")
    if suffix in {".json", ".txt", ""} and SECRET_NAME_RE.search(path.name):
        return Finding(scope, name, "secret-like filename", "name looks like a key, keystore or service-account file")
    return None


def service_account_json_finding(scope: str, name: str, text: str) -> Finding | None:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = None
    if isinstance(payload, dict):
        required = {"type", "project_id", "private_key_id", "private_key", "client_email"}
        if payload.get("type") == "service_account" and required.issubset(payload.keys()):
            return Finding(scope, name, "service-account JSON", "Google Play service-account credential JSON is present")
    has_key_material = PRIVATE_KEY_JSON_RE.search(text) is not None
    has_service_account_email = SERVICE_ACCOUNT_EMAIL_RE.search(text) is not None
    if has_key_material and has_service_account_email:
        return Finding(scope, name, "service-account JSON fragment", "private key and gserviceaccount email appear together")
    return None


def content_findings(scope: str, name: str, data: bytes) -> list[Finding]:
    if not should_scan_text(name, len(data)):
        return []
    text = data.decode("utf-8", errors="replace")
    findings: list[Finding] = []
    if PRIVATE_KEY_BLOCK_RE.search(text):
        findings.append(Finding(scope, name, "private-key block", "PEM private-key block is present"))
    service_account = service_account_json_finding(scope, name, text)
    if service_account is not None:
        findings.append(service_account)
    return findings


def scan_handoff(handoff: Path) -> tuple[list[Finding], Check]:
    if not handoff.is_dir():
        return [], Check("Handoff directory", "FAIL", f"missing {rel(handoff)}")
    findings: list[Finding] = []
    relative_names, manifest_error = load_manifest_file_list(handoff)
    if manifest_error is not None:
        return [], manifest_error
    missing: list[str] = []
    scanned = 0
    for name in relative_names:
        path = handoff / name
        if not path.is_file():
            missing.append(name)
            continue
        name_finding = secret_name_finding("handoff", name)
        if name_finding is not None:
            findings.append(name_finding)
        findings.extend(content_findings("handoff", name, path.read_bytes()))
        scanned += 1
    if missing:
        return findings, Check("Handoff directory", "FAIL", f"missing manifest files: {', '.join(missing)}")
    return findings, Check("Handoff directory", "PASS", f"scanned {scanned} manifest-listed files")


def scan_archive(archive: Path) -> tuple[list[Finding], Check]:
    if not archive.exists():
        return [], Check("Handoff archive", "FAIL", f"missing {rel(archive)}")
    findings: list[Finding] = []
    with zipfile.ZipFile(archive) as zf:
        infos = [info for info in zf.infolist() if not info.is_dir()]
        for info in infos:
            name = info.filename
            name_finding = secret_name_finding("archive", name)
            if name_finding is not None:
                findings.append(name_finding)
            if should_scan_text(name, info.file_size):
                findings.extend(content_findings("archive", name, zf.read(info)))
    return findings, Check("Handoff archive", "PASS", f"scanned {len(infos)} files")


def scan_sidecars(archive: Path) -> tuple[list[Finding], Check]:
    sidecars = sidecars_for(archive)
    missing = [rel(path) for path in sidecars if not path.exists()]
    findings: list[Finding] = []
    scanned = 0
    for path in sidecars:
        if not path.exists():
            continue
        name = rel(path)
        name_finding = secret_name_finding("transfer-sidecar", name)
        if name_finding is not None:
            findings.append(name_finding)
        findings.extend(content_findings("transfer-sidecar", name, path.read_bytes()))
        scanned += 1
    if missing:
        return findings, Check("Transfer sidecars", "FAIL", f"missing sidecars: {', '.join(missing)}")
    return findings, Check("Transfer sidecars", "PASS", f"scanned {scanned} sidecar files")


def scan_scope_counts(handoff: Path, archive: Path) -> dict[str, object]:
    handoff_names, manifest_error = load_manifest_file_list(handoff)
    archive_count = 0
    if archive.exists():
        try:
            with zipfile.ZipFile(archive) as zf:
                archive_count = len([info for info in zf.infolist() if not info.is_dir()])
        except zipfile.BadZipFile:
            archive_count = 0
    sidecars = sidecars_for(archive)
    return {
        "handoffFileCount": len(handoff_names) if manifest_error is None else 0,
        "archiveFileCount": archive_count,
        "sidecarFileCount": len([path for path in sidecars if path.exists()]),
        "expectedSidecarFileCount": len(sidecars),
    }


def summarize_findings(findings: list[Finding]) -> list[Check]:
    checks: list[Check] = []
    by_rule: dict[str, int] = {}
    for finding in findings:
        by_rule[finding.rule] = by_rule.get(finding.rule, 0) + 1
    for rule in [
        "secret-like file extension",
        "secret-like filename",
        "private-key block",
        "service-account JSON",
        "service-account JSON fragment",
    ]:
        count = by_rule.get(rule, 0)
        checks.append(Check(rule, "FAIL" if count else "PASS", f"{count} finding(s)"))
    return checks


def write_reports(handoff: Path, archive: Path, checks: list[Check], findings: list[Finding]) -> None:
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    status = "FAIL" if any(check.status == "FAIL" for check in checks) else "PASS"
    payload = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "handoff": rel(handoff),
        "archive": rel(archive),
        "sidecars": [rel(path) for path in sidecars_for(archive)],
        "scanScope": scan_scope_counts(handoff, archive),
        "checks": [check.__dict__ for check in checks],
        "findings": [finding.__dict__ for finding in findings],
    }
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Play Handoff Secret Scan QA",
        "",
        f"Generated: {payload['generatedAt']}",
        f"Status: {status}",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for check in checks:
        lines.append(f"| {check.name} | {check.status} | {check.detail} |")
    lines.extend(["", "## Findings"])
    if findings:
        lines.extend(["", "| Scope | Path | Rule | Detail |", "|---|---|---|---|"])
        for finding in findings:
            lines.append(f"| {finding.scope} | `{finding.path}` | {finding.rule} | {finding.detail} |")
    else:
        lines.append("")
        lines.append("No secret-like handoff files, private-key blocks or service-account JSON credentials found.")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--handoff", default=str(DEFAULT_HANDOFF), help="handoff directory")
    parser.add_argument("--archive", default="", help="handoff zip archive")
    args = parser.parse_args()

    handoff = Path(args.handoff)
    if not handoff.is_absolute():
        handoff = ROOT / handoff
    archive = Path(args.archive) if args.archive else archive_for(handoff)
    if not archive.is_absolute():
        archive = ROOT / archive

    handoff_findings, handoff_check = scan_handoff(handoff)
    archive_findings, archive_check = scan_archive(archive)
    sidecar_findings, sidecar_check = scan_sidecars(archive)
    findings = [*handoff_findings, *archive_findings, *sidecar_findings]
    checks = [handoff_check, archive_check, sidecar_check, *summarize_findings(findings)]
    write_reports(handoff, archive, checks, findings)

    failures = [check for check in checks if check.status == "FAIL"]
    if failures:
        print("Play handoff secret scan QA failed")
        for check in failures:
            print(f"- {check.name}: {check.detail}")
        print(f"Report: {rel(REPORT_MD)}")
        raise SystemExit(1)
    print(f"Play handoff secret scan QA PASS ({rel(REPORT_MD)})")


if __name__ == "__main__":
    main()
