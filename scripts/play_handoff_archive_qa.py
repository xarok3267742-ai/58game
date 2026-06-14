#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HANDOFF = ROOT / "build/play_handoff/shawarma58-v1.0.0"
REPORT_MD = ROOT / "build/reports/play_handoff_archive_qa.md"
REPORT_JSON = ROOT / "build/reports/play_handoff_archive_qa.json"
SECRET_SUFFIXES = {".jks", ".keystore", ".p12", ".pem"}


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(handoff: Path) -> dict[str, object]:
    manifest_path = handoff / "manifest.json"
    if not manifest_path.exists():
        raise AssertionError(f"missing handoff manifest: {manifest_path}")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def parse_checksums(text: str) -> tuple[dict[str, str], list[str]]:
    entries: dict[str, str] = {}
    errors: list[str] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        if not raw_line.strip():
            continue
        digest, separator, relative = raw_line.partition("  ")
        if separator != "  " or not relative:
            errors.append(f"CHECKSUMS.txt line {line_number} must use '<sha256>  <path>'")
            continue
        if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
            errors.append(f"CHECKSUMS.txt line {line_number} has invalid SHA-256")
            continue
        if relative in entries:
            errors.append(f"CHECKSUMS.txt duplicates path: {relative}")
            continue
        entries[relative] = digest
    return entries, errors


def write_report(
    *,
    handoff: Path,
    archive: Path,
    require_package_report: bool,
    manifest_file_count: int,
    archive_file_count: int,
    errors: list[str],
) -> None:
    status = "FAIL" if errors else "PASS"
    payload = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "handoff": rel(handoff),
        "archive": rel(archive),
        "requirePackageReport": require_package_report,
        "manifestFileCount": manifest_file_count,
        "archiveFileCount": archive_file_count,
        "errors": errors,
    }
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Play Handoff Archive QA",
        "",
        f"Generated: {payload['generatedAt']}",
        f"Status: `{status}`",
        f"Archive: `{payload['archive']}`",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Handoff | `{payload['handoff']}` |",
        f"| Require package report | `{str(require_package_report).lower()}` |",
        f"| Manifest files | `{manifest_file_count}` |",
        f"| Archive files | `{archive_file_count}` |",
    ]
    if errors:
        lines.extend(["", "## Errors"])
        lines.extend(f"- {error}" for error in errors)
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--handoff", default=str(DEFAULT_HANDOFF), help="handoff directory")
    parser.add_argument("--archive", default="", help="archive path")
    parser.add_argument("--require-package-report", action="store_true", help="require .zip.package.md/json sidecars")
    args = parser.parse_args()

    handoff = Path(args.handoff)
    if not handoff.is_absolute():
        handoff = ROOT / handoff
    archive = Path(args.archive) if args.archive else handoff.parent / f"{handoff.name}.zip"
    if not archive.is_absolute():
        archive = ROOT / archive
    sidecar = archive.with_suffix(archive.suffix + ".sha256")
    report_path = archive.with_suffix(archive.suffix + ".json")
    package_report_path = archive.with_suffix(archive.suffix + ".package.json")
    package_report_md = archive.with_suffix(archive.suffix + ".package.md")

    errors: list[str] = []
    if not archive.exists():
        errors.append(f"archive missing: {archive}")
    if not sidecar.exists():
        errors.append(f"archive SHA sidecar missing: {sidecar}")
    if not report_path.exists():
        errors.append(f"archive JSON report missing: {report_path}")
    if args.require_package_report and not package_report_path.exists():
        errors.append(f"archive package JSON report missing: {package_report_path}")
    if args.require_package_report and not package_report_md.exists():
        errors.append(f"archive package markdown report missing: {package_report_md}")
    if errors:
        write_report(
            handoff=handoff,
            archive=archive,
            require_package_report=args.require_package_report,
            manifest_file_count=0,
            archive_file_count=0,
            errors=errors,
        )
        print("Play handoff archive QA failed")
        for error in errors:
            print(f"- {error}")
        print(f"Report: {rel(REPORT_MD)}")
        raise SystemExit(1)

    try:
        manifest = load_manifest(handoff)
    except Exception as exc:
        errors.append(f"handoff manifest load failed: {exc}")
        write_report(
            handoff=handoff,
            archive=archive,
            require_package_report=args.require_package_report,
            manifest_file_count=0,
            archive_file_count=0,
            errors=errors,
        )
        print("Play handoff archive QA failed")
        for error in errors:
            print(f"- {error}")
        print(f"Report: {rel(REPORT_MD)}")
        raise SystemExit(1) from exc
    files = manifest.get("files")
    if not isinstance(files, dict):
        errors.append("handoff manifest.files must be an object")
        files = {}

    expected_relative = sorted(set(files.keys()) | {"manifest.json"})
    expected_archive_names = sorted(f"{handoff.name}/{name}" for name in expected_relative)
    manifest_sha = sha256(handoff / "manifest.json")
    archive_names: list[str] = []
    with zipfile.ZipFile(archive) as zf:
        archive_names = sorted(name for name in zf.namelist() if not name.endswith("/"))
        if archive_names != expected_archive_names:
            missing = sorted(set(expected_archive_names) - set(archive_names))
            extra = sorted(set(archive_names) - set(expected_archive_names))
            errors.append(f"archive file set mismatch; missing={missing}, extra={extra}")
        archived_manifest_name = f"{handoff.name}/manifest.json"
        if archived_manifest_name in archive_names:
            with zf.open(archived_manifest_name) as handle:
                archived_manifest_bytes = handle.read()
            archived_manifest_sha = hashlib.sha256(archived_manifest_bytes).hexdigest()
            if archived_manifest_sha != manifest_sha:
                errors.append("archived manifest.json sha does not match handoff manifest")
            try:
                archived_manifest = json.loads(archived_manifest_bytes.decode("utf-8"))
            except json.JSONDecodeError:
                errors.append("archived manifest.json is not valid JSON")
            else:
                if archived_manifest != manifest:
                    errors.append("archived manifest.json content does not match handoff manifest")
        else:
            errors.append("archive is missing manifest.json")
        for name in archive_names:
            if Path(name).suffix.lower() in SECRET_SUFFIXES:
                errors.append(f"archive contains forbidden secret-like file: {name}")
        for relative_name, info in files.items():
            archive_name = f"{handoff.name}/{relative_name}"
            if archive_name not in archive_names:
                continue
            with zf.open(archive_name) as handle:
                digest = hashlib.sha256(handle.read()).hexdigest()
            if isinstance(info, dict) and digest != info.get("sha256"):
                errors.append(f"archive content sha mismatch for {archive_name}")
        checksums_name = f"{handoff.name}/CHECKSUMS.txt"
        if checksums_name not in archive_names:
            errors.append("archive is missing CHECKSUMS.txt")
        else:
            with zf.open(checksums_name) as handle:
                checksum_text = handle.read().decode("utf-8")
            checksum_entries, checksum_errors = parse_checksums(checksum_text)
            errors.extend(checksum_errors)
            expected_entries = {
                relative_name: str(info.get("sha256"))
                for relative_name, info in files.items()
                if relative_name != "CHECKSUMS.txt" and isinstance(info, dict) and isinstance(info.get("sha256"), str)
            }
            if checksum_entries != expected_entries:
                missing = sorted(set(expected_entries) - set(checksum_entries))
                extra = sorted(set(checksum_entries) - set(expected_entries))
                mismatched = sorted(
                    relative_name
                    for relative_name in set(checksum_entries) & set(expected_entries)
                    if checksum_entries[relative_name] != expected_entries[relative_name]
                )
                errors.append(
                    "archived CHECKSUMS.txt does not match manifest file checksums; "
                    f"missing={missing}, extra={extra}, mismatched={mismatched}",
                )
            for relative_name, digest in checksum_entries.items():
                archive_name = f"{handoff.name}/{relative_name}"
                if archive_name not in archive_names:
                    continue
                with zf.open(archive_name) as handle:
                    actual_digest = hashlib.sha256(handle.read()).hexdigest()
                if actual_digest != digest:
                    errors.append(f"archived CHECKSUMS.txt digest does not match file bytes: {archive_name}")

    expected_sidecar = f"{sha256(archive)}  {archive.name}"
    actual_sidecar = sidecar.read_text(encoding="utf-8").strip()
    if actual_sidecar != expected_sidecar:
        errors.append("archive SHA sidecar does not match archive")

    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("sha256") != sha256(archive):
        errors.append("archive JSON report sha256 does not match archive")
    if report.get("manifestSha256") != manifest_sha:
        errors.append("archive JSON report manifestSha256 does not match handoff manifest")
    if report.get("fileCount") != len(expected_relative):
        errors.append("archive JSON report fileCount mismatch")
    if report.get("manifestFileCount") != len(files):
        errors.append("archive JSON report manifestFileCount mismatch")
    if report.get("archiveInput") != "manifest.files plus manifest.json":
        errors.append("archive JSON report archiveInput must be manifest.files plus manifest.json")
    if args.require_package_report:
        package_report = json.loads(package_report_path.read_text(encoding="utf-8"))
        if package_report.get("status") not in {"PASS", "PASS_WITH_WARNINGS", "EXTERNAL_BLOCKER"}:
            errors.append("archive package report status must be PASS, PASS_WITH_WARNINGS or EXTERNAL_BLOCKER")
        release_gate = package_report.get("releaseGate")
        if not isinstance(release_gate, dict):
            errors.append("archive package report missing releaseGate object")
        elif release_gate.get("status") not in {"PASS", "PASS_WITH_WARNINGS", "EXTERNAL_BLOCKER"}:
            errors.append("archive package report releaseGate status mismatch")
        archive_section = package_report.get("archive")
        if not isinstance(archive_section, dict):
            errors.append("archive package report missing archive object")
        else:
            if archive_section.get("sha256") != sha256(archive):
                errors.append("archive package report sha256 does not match archive")
            if archive_section.get("manifestSha256") != manifest_sha:
                errors.append("archive package report manifestSha256 does not match handoff manifest")
            if archive_section.get("path") != archive.relative_to(ROOT).as_posix():
                errors.append("archive package report path mismatch")
            expected_verify_command = (
                f"cd {archive.parent.relative_to(ROOT).as_posix()} "
                f"&& shasum -a 256 -c {sidecar.name}"
            )
            if archive_section.get("verifyCommand") != expected_verify_command:
                errors.append("archive package report verifyCommand mismatch")
        handoff_section = package_report.get("handoff")
        if not isinstance(handoff_section, dict) or handoff_section.get("fileCount") != len(files):
            errors.append("archive package report handoff fileCount mismatch")
        elif handoff_section.get("releaseGate") != manifest.get("releaseGate"):
            errors.append("archive package report releaseGate does not match handoff manifest")
        elif handoff_section.get("optionalEvidence") != manifest.get("optionalEvidence"):
            errors.append("archive package report optionalEvidence does not match handoff manifest")
        elif handoff_section.get("connectedSmoke") != manifest.get("connectedSmoke"):
            errors.append("archive package report connectedSmoke does not match handoff manifest")

    if errors:
        write_report(
            handoff=handoff,
            archive=archive,
            require_package_report=args.require_package_report,
            manifest_file_count=len(files),
            archive_file_count=len(archive_names),
            errors=errors,
        )
        print("Play handoff archive QA failed")
        for error in errors:
            print(f"- {error}")
        print(f"Report: {rel(REPORT_MD)}")
        raise SystemExit(1)

    write_report(
        handoff=handoff,
        archive=archive,
        require_package_report=args.require_package_report,
        manifest_file_count=len(files),
        archive_file_count=len(archive_names),
        errors=[],
    )
    print(f"Play handoff archive QA PASS ({rel(archive)}; {rel(REPORT_MD)})")


if __name__ == "__main__":
    main()
