#!/usr/bin/env python3
from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HANDOFF_MANIFEST = ROOT / "build/play_handoff/shawarma58-v1.0.0/manifest.json"
HANDOFF_DIR = HANDOFF_MANIFEST.parent
ARCHIVE = ROOT / "build/play_handoff/shawarma58-v1.0.0.zip"
PACKAGE_REPORT = ROOT / "build/reports/release_candidate_package.json"
PACKAGE_REPORT_MD = ROOT / "build/reports/release_candidate_package.md"
ARCHIVE_REPORT = ROOT / "build/play_handoff/shawarma58-v1.0.0.zip.json"
ARCHIVE_PACKAGE_REPORT = ROOT / "build/play_handoff/shawarma58-v1.0.0.zip.package.json"
ARCHIVE_PACKAGE_REPORT_MD = ROOT / "build/play_handoff/shawarma58-v1.0.0.zip.package.md"
ARCHIVE_SHA_SIDECAR = ROOT / "build/play_handoff/shawarma58-v1.0.0.zip.sha256"
SECRET_SCAN_REPORT = ROOT / "build/reports/play_handoff_secret_scan.json"
FRESHNESS_REPORT = ROOT / "build/reports/release_freshness.json"
HANDOFF_QA_REPORT = ROOT / "build/reports/play_handoff_qa.json"
ARCHIVE_QA_REPORT = ROOT / "build/reports/play_handoff_archive_qa.json"
REPORT_MD = ROOT / "build/reports/post_package_validation.md"
REPORT_JSON = ROOT / "build/reports/post_package_validation.json"
PACKAGE_SCRIPT = ROOT / "scripts/package_release_candidate.py"


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def load_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def mtime_iso(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).replace(microsecond=0).isoformat()


def expected_sidecars() -> list[Path]:
    return [
        ARCHIVE_REPORT,
        ARCHIVE_PACKAGE_REPORT,
        ARCHIVE_PACKAGE_REPORT_MD,
        ARCHIVE_SHA_SIDECAR,
    ]


def check_transfer_artifacts_exist(sidecars: list[Path]) -> list[Check]:
    required = [ARCHIVE, *sidecars]
    missing = [rel(path) for path in required if not path.exists()]
    archive_detail = f"{rel(ARCHIVE)} present" if ARCHIVE.exists() else f"missing {rel(ARCHIVE)}"
    sidecar_detail = f"{len(sidecars)} sidecars present" if not missing else f"missing: {missing}"
    return [
        Check("Transfer archive exists", "PASS" if ARCHIVE.exists() else "FAIL", archive_detail),
        Check("Transfer sidecars exist", "FAIL" if missing else "PASS", sidecar_detail),
    ]


def check_transfer_file_set(sidecars: list[Path]) -> list[Check]:
    expected_files = {ARCHIVE, *sidecars}
    expected_directories = {HANDOFF_DIR}
    if not ARCHIVE.parent.exists():
        return [Check("Transfer file set exact", "FAIL", f"missing {rel(ARCHIVE.parent)}")]
    actual_files = {path for path in ARCHIVE.parent.iterdir() if path.is_file()}
    actual_directories = {path for path in ARCHIVE.parent.iterdir() if path.is_dir()}
    missing_files = sorted(rel(path) for path in expected_files - actual_files)
    unexpected_files = sorted(rel(path) for path in actual_files - expected_files)
    missing_directories = sorted(rel(path) for path in expected_directories - actual_directories)
    unexpected_directories = sorted(rel(path) for path in actual_directories - expected_directories)
    return [
        Check(
            "Transfer file set exact",
            "PASS"
            if not missing_files
            and not unexpected_files
            and not missing_directories
            and not unexpected_directories
            else "FAIL",
            f"{len(actual_files)} transfer files and {len(actual_directories)} transfer directory match expected set"
            if not missing_files
            and not unexpected_files
            and not missing_directories
            and not unexpected_directories
            else (
                f"missingFiles={missing_files}, unexpectedFiles={unexpected_files}, "
                f"missingDirs={missing_directories}, unexpectedDirs={unexpected_directories}"
            ),
        ),
    ]


def check_archive_integrity() -> list[Check]:
    package = load_json(PACKAGE_REPORT)
    sidecar_package = load_json(ARCHIVE_PACKAGE_REPORT)
    archive_report = load_json(ARCHIVE_REPORT)
    missing = [
        rel(path)
        for path in [ARCHIVE, HANDOFF_MANIFEST, ARCHIVE_REPORT, ARCHIVE_SHA_SIDECAR, PACKAGE_REPORT, ARCHIVE_PACKAGE_REPORT]
        if not path.exists()
    ]
    if missing:
        return [Check("Archive integrity inputs", "FAIL", f"missing: {missing}")]

    package_archive = package.get("archive") if isinstance(package.get("archive"), dict) else {}
    sidecar_package_archive = sidecar_package.get("archive") if isinstance(sidecar_package.get("archive"), dict) else {}
    actual_archive_sha = sha256(ARCHIVE)
    actual_manifest_sha = sha256(HANDOFF_MANIFEST)
    actual_archive_bytes = ARCHIVE.stat().st_size
    expected_verify = f"cd {rel(ARCHIVE.parent)} && shasum -a 256 -c {ARCHIVE_SHA_SIDECAR.name}"
    expected_sidecar_text = f"{actual_archive_sha}  {ARCHIVE.name}\n"

    checks = [
        Check(
            "Package archive SHA parity",
            "PASS" if package_archive.get("sha256") == actual_archive_sha else "FAIL",
            f"package {package_archive.get('sha256')}, actual {actual_archive_sha}",
        ),
        Check(
            "Archive report SHA parity",
            "PASS" if archive_report.get("sha256") == actual_archive_sha else "FAIL",
            f"archive report {archive_report.get('sha256')}, actual {actual_archive_sha}",
        ),
        Check(
            "Package archive byte parity",
            "PASS" if package_archive.get("bytes") == actual_archive_bytes else "FAIL",
            f"package {package_archive.get('bytes')}, actual {actual_archive_bytes}",
        ),
        Check(
            "Archive report byte parity",
            "PASS" if archive_report.get("bytes") == actual_archive_bytes else "FAIL",
            f"archive report {archive_report.get('bytes')}, actual {actual_archive_bytes}",
        ),
        Check(
            "Package manifest SHA parity",
            "PASS" if package_archive.get("manifestSha256") == actual_manifest_sha else "FAIL",
            f"package {package_archive.get('manifestSha256')}, actual {actual_manifest_sha}",
        ),
        Check(
            "Archive report manifest SHA parity",
            "PASS" if archive_report.get("manifestSha256") == actual_manifest_sha else "FAIL",
            f"archive report {archive_report.get('manifestSha256')}, actual {actual_manifest_sha}",
        ),
        Check(
            "Archive package sidecar archive parity",
            "PASS" if sidecar_package_archive == package_archive else "FAIL",
            "transfer package JSON archive section matches build/reports package JSON",
        ),
        Check(
            "Archive SHA sidecar exact text",
            "PASS" if ARCHIVE_SHA_SIDECAR.read_text(encoding="utf-8") == expected_sidecar_text else "FAIL",
            f"expected {expected_sidecar_text.strip()!r}",
        ),
        Check(
            "Package verify command",
            "PASS" if package_archive.get("verifyCommand") == expected_verify else "FAIL",
            f"package {package_archive.get('verifyCommand')!r}, expected {expected_verify!r}",
        ),
    ]
    return checks


def check_handoff_directory_integrity() -> list[Check]:
    manifest = load_json(HANDOFF_MANIFEST)
    files = manifest.get("files")
    if not isinstance(files, dict):
        return [Check("Handoff directory manifest files", "FAIL", "manifest.files is missing or not an object")]
    missing: list[str] = []
    checksum_mismatches: list[str] = []
    byte_mismatches: list[str] = []
    invalid_entries: list[str] = []
    for relative, metadata in sorted(files.items(), key=lambda item: str(item[0])):
        if not isinstance(relative, str) or not isinstance(metadata, dict):
            invalid_entries.append(str(relative))
            continue
        path = HANDOFF_DIR / relative
        if not path.is_file():
            missing.append(relative)
            continue
        expected_sha = metadata.get("sha256")
        if expected_sha != sha256(path):
            checksum_mismatches.append(relative)
        expected_bytes = metadata.get("bytes")
        if expected_bytes != path.stat().st_size:
            byte_mismatches.append(relative)
    return [
        Check(
            "Handoff directory manifest files",
            "PASS" if not missing and not invalid_entries else "FAIL",
            f"{len(files)} manifest files present"
            if not missing and not invalid_entries
            else f"missing={missing}, invalid={invalid_entries}",
        ),
        Check(
            "Handoff directory checksum parity",
            "PASS" if not checksum_mismatches else "FAIL",
            "all manifest-listed files match sha256" if not checksum_mismatches else f"mismatches={checksum_mismatches}",
        ),
        Check(
            "Handoff directory byte parity",
            "PASS" if not byte_mismatches else "FAIL",
            "all manifest-listed files match byte sizes" if not byte_mismatches else f"mismatches={byte_mismatches}",
        ),
    ]


def check_local_handoff_qa_reports() -> list[Check]:
    manifest = load_json(HANDOFF_MANIFEST)
    files = manifest.get("files")
    manifest_count = len(files) if isinstance(files, dict) else 0
    archive_report = load_json(ARCHIVE_REPORT)
    handoff_qa = load_json(HANDOFF_QA_REPORT)
    archive_qa = load_json(ARCHIVE_QA_REPORT)
    if not handoff_qa or not archive_qa:
        missing = [
            rel(path)
            for path, report in [(HANDOFF_QA_REPORT, handoff_qa), (ARCHIVE_QA_REPORT, archive_qa)]
            if not report
        ]
        return [Check("Local handoff QA reports", "FAIL", f"missing: {missing}")]
    handoff_errors = handoff_qa.get("errors")
    archive_errors = archive_qa.get("errors")
    return [
        Check(
            "Local handoff QA report status",
            "PASS" if handoff_qa.get("status") == "PASS" and handoff_errors == [] else "FAIL",
            f"status {handoff_qa.get('status')}, errors {len(handoff_errors) if isinstance(handoff_errors, list) else '<invalid>'}",
        ),
        Check(
            "Local handoff QA manifest count",
            "PASS" if handoff_qa.get("manifestFileCount") == manifest_count else "FAIL",
            f"report {handoff_qa.get('manifestFileCount')}, manifest {manifest_count}",
        ),
        Check(
            "Local handoff QA copy-map coverage",
            "PASS" if handoff_qa.get("copyMapTargetCount", 0) > 0 and handoff_qa.get("copyMapMissingInManifest") == [] else "FAIL",
            f"targets {handoff_qa.get('copyMapTargetCount')}, missing {handoff_qa.get('copyMapMissingInManifest')}",
        ),
        Check(
            "Local archive QA report status",
            "PASS" if archive_qa.get("status") == "PASS" and archive_errors == [] else "FAIL",
            f"status {archive_qa.get('status')}, errors {len(archive_errors) if isinstance(archive_errors, list) else '<invalid>'}",
        ),
        Check(
            "Local archive QA manifest count",
            "PASS" if archive_qa.get("manifestFileCount") == manifest_count else "FAIL",
            f"report {archive_qa.get('manifestFileCount')}, manifest {manifest_count}",
        ),
        Check(
            "Local archive QA archive count",
            "PASS" if archive_qa.get("archiveFileCount") == archive_report.get("fileCount") else "FAIL",
            f"report {archive_qa.get('archiveFileCount')}, archive report {archive_report.get('fileCount')}",
        ),
        Check(
            "Local archive QA package-report mode",
            "PASS" if archive_qa.get("requirePackageReport") is True and archive_qa.get("archive") == rel(ARCHIVE) else "FAIL",
            f"requirePackageReport={archive_qa.get('requirePackageReport')}, archive={archive_qa.get('archive')}",
        ),
    ]


def check_secret_scan(sidecars: list[Path]) -> list[Check]:
    report = load_json(SECRET_SCAN_REPORT)
    manifest = load_json(HANDOFF_MANIFEST)
    manifest_files = manifest.get("files")
    manifest_count = len(manifest_files) if isinstance(manifest_files, dict) else 0
    archive_report = load_json(ARCHIVE_REPORT)
    if not report:
        return [Check("Final sidecar secret scan report", "FAIL", f"missing {rel(SECRET_SCAN_REPORT)}")]
    checks: list[Check] = []
    expected = [rel(path) for path in sidecars]
    scanned = report.get("sidecars")
    scan_scope = report.get("scanScope") if isinstance(report.get("scanScope"), dict) else {}
    checks.append(
        Check(
            "Final sidecar secret scan status",
            "PASS" if report.get("status") == "PASS" else "FAIL",
            f"status {report.get('status')}",
        ),
    )
    checks.append(
        Check(
            "Final sidecar secret scan scope",
            "PASS" if scanned == expected else "FAIL",
            f"scanned {scanned}, expected {expected}",
        ),
    )
    scan_checks = report.get("checks")
    transfer_check = None
    if isinstance(scan_checks, list):
        for item in scan_checks:
            if isinstance(item, dict) and item.get("name") == "Transfer sidecars":
                transfer_check = item
                break
    checks.append(
        Check(
            "Final sidecar secret scan check",
            "PASS" if isinstance(transfer_check, dict) and transfer_check.get("status") == "PASS" else "FAIL",
            str(transfer_check) if transfer_check is not None else "Transfer sidecars check missing",
        ),
    )
    checks.append(
        Check(
            "Final secret scan handoff coverage",
            "PASS" if scan_scope.get("handoffFileCount") == manifest_count + 1 else "FAIL",
            f"scan {scan_scope.get('handoffFileCount')}, expected manifest files plus manifest.json {manifest_count + 1}",
        ),
    )
    checks.append(
        Check(
            "Final secret scan archive coverage",
            "PASS" if scan_scope.get("archiveFileCount") == archive_report.get("fileCount") else "FAIL",
            f"scan {scan_scope.get('archiveFileCount')}, archive report {archive_report.get('fileCount')}",
        ),
    )
    checks.append(
        Check(
            "Final secret scan sidecar coverage",
            "PASS"
            if scan_scope.get("sidecarFileCount") == len(sidecars)
            and scan_scope.get("expectedSidecarFileCount") == len(sidecars)
            else "FAIL",
            f"scan {scan_scope.get('sidecarFileCount')}, expected {scan_scope.get('expectedSidecarFileCount')}, required {len(sidecars)}",
        ),
    )
    if all(path.exists() for path in sidecars):
        newest_sidecar_mtime = max(path.stat().st_mtime_ns for path in sidecars)
        scan_mtime = SECRET_SCAN_REPORT.stat().st_mtime_ns
        newest_sidecar = max(sidecars, key=lambda path: path.stat().st_mtime_ns)
        checks.append(
            Check(
                "Final sidecar secret scan ordering",
                "PASS" if scan_mtime >= newest_sidecar_mtime else "FAIL",
                f"scan {mtime_iso(SECRET_SCAN_REPORT)}, newest sidecar {rel(newest_sidecar)} at {mtime_iso(newest_sidecar)}",
            ),
        )
    return checks


def check_freshness_ordering() -> list[Check]:
    report = load_json(FRESHNESS_REPORT)
    if not report:
        return [Check("Final freshness report", "FAIL", f"missing {rel(FRESHNESS_REPORT)}")]
    report_checks = report.get("checks")
    checks_pass = (
        report.get("status") == "PASS"
        if report.get("status") is not None
        else isinstance(report_checks, list)
        and all(isinstance(item, dict) and item.get("status") != "FAIL" for item in report_checks)
    )
    checks = [
        Check(
            "Final freshness report present",
            "PASS",
            rel(FRESHNESS_REPORT),
        ),
        Check(
            "Final freshness report pass state",
            "PASS" if checks_pass else "FAIL",
            f"status {report.get('status', '<derived-from-checks>')}",
        ),
    ]
    if SECRET_SCAN_REPORT.exists():
        freshness_mtime = FRESHNESS_REPORT.stat().st_mtime_ns
        secret_scan_mtime = SECRET_SCAN_REPORT.stat().st_mtime_ns
        checks.append(
            Check(
                "Final freshness after sidecar scan",
                "PASS" if freshness_mtime >= secret_scan_mtime else "FAIL",
                f"freshness {mtime_iso(FRESHNESS_REPORT)}, secret scan {mtime_iso(SECRET_SCAN_REPORT)}",
            ),
        )
    return checks


def check_package_sidecar_parity() -> list[Check]:
    package = load_json(PACKAGE_REPORT)
    sidecar = load_json(ARCHIVE_PACKAGE_REPORT)
    if not package or not sidecar:
        return [Check("Package sidecar parity", "FAIL", "package report or archive package report missing")]
    checks = [
        Check(
            "Package JSON sidecar parity",
            "PASS" if package == sidecar else "FAIL",
            "build/reports package JSON matches transfer package JSON",
        ),
    ]
    if not PACKAGE_REPORT_MD.exists() or not ARCHIVE_PACKAGE_REPORT_MD.exists():
        missing = [
            rel(path)
            for path in [PACKAGE_REPORT_MD, ARCHIVE_PACKAGE_REPORT_MD]
            if not path.exists()
        ]
        checks.append(Check("Package markdown sidecar parity", "FAIL", f"missing: {missing}"))
        return checks
    checks.append(
        Check(
            "Package markdown sidecar parity",
            "PASS"
            if PACKAGE_REPORT_MD.read_text(encoding="utf-8")
            == ARCHIVE_PACKAGE_REPORT_MD.read_text(encoding="utf-8")
            else "FAIL",
            "build/reports package markdown matches transfer package markdown",
        ),
    )
    return checks


def check_package_markdown_content() -> list[Check]:
    package = load_json(PACKAGE_REPORT)
    if not package:
        return [Check("Package markdown content", "FAIL", f"missing {rel(PACKAGE_REPORT)}")]
    if not ARCHIVE_PACKAGE_REPORT_MD.exists():
        return [Check("Package markdown content", "FAIL", f"missing {rel(ARCHIVE_PACKAGE_REPORT_MD)}")]
    markdown = ARCHIVE_PACKAGE_REPORT_MD.read_text(encoding="utf-8")
    archive = package.get("archive") if isinstance(package.get("archive"), dict) else {}
    handoff = package.get("handoff") if isinstance(package.get("handoff"), dict) else {}
    handoff_release_gate = handoff.get("releaseGate") if isinstance(handoff.get("releaseGate"), dict) else {}
    expected_snippets = [
        f"Status: `{package.get('status')}`",
        f"- Directory: `{handoff.get('path')}`",
        f"- Files in manifest: `{handoff.get('fileCount')}`",
        f"- Release gate: `{handoff_release_gate.get('status')}`",
        f"- Archive: `{archive.get('path')}`",
        f"- SHA sidecar: `{archive.get('sha256File')}`",
        f"- Bytes: `{archive.get('bytes')}`",
        f"- Files: `{archive.get('fileCount')}`",
        f"- SHA-256: `{archive.get('sha256')}`",
        f"- Manifest SHA-256: `{archive.get('manifestSha256')}`",
        f"- Verify sidecar: `{archive.get('verifyCommand')}`",
    ]
    missing = [snippet for snippet in expected_snippets if snippet not in markdown]
    return [
        Check(
            "Package markdown content",
            "PASS" if not missing else "FAIL",
            "transfer package markdown contains status, handoff and archive values from JSON"
            if not missing
            else f"missing snippets: {missing}",
        ),
    ]


def check_report_is_non_transfer(sidecars: list[Path]) -> list[Check]:
    sidecar_rels = {rel(path) for path in sidecars}
    report_rels = {rel(REPORT_MD), rel(REPORT_JSON)}
    manifest = load_json(HANDOFF_MANIFEST)
    files = manifest.get("files")
    manifest_refs: list[str] = []
    if isinstance(files, dict):
        for relative, metadata in files.items():
            if "post_package_validation" in str(relative):
                manifest_refs.append(str(relative))
            if isinstance(metadata, dict) and "post_package_validation" in str(metadata.get("source", "")):
                manifest_refs.append(f"{relative} -> {metadata.get('source')}")
    report_under_handoff = [
        path
        for path in [REPORT_MD, REPORT_JSON]
        if ARCHIVE.parent in path.parents or path == ARCHIVE.parent
    ]
    return [
        Check(
            "Post-package report is not a transfer sidecar",
            "PASS" if report_rels.isdisjoint(sidecar_rels) else "FAIL",
            f"reports {sorted(report_rels)}, sidecars {sorted(sidecar_rels)}",
        ),
        Check(
            "Post-package report stays outside play_handoff",
            "PASS" if not report_under_handoff else "FAIL",
            "build/reports only" if not report_under_handoff else f"inside handoff tree: {[rel(path) for path in report_under_handoff]}",
        ),
        Check(
            "Post-package report excluded from handoff manifest",
            "PASS" if not manifest_refs else "FAIL",
            "no manifest references" if not manifest_refs else f"manifest refs: {manifest_refs}",
        ),
    ]


def check_package_flow_source_order() -> list[Check]:
    if not PACKAGE_SCRIPT.exists():
        return [Check("Package flow source", "FAIL", f"missing {rel(PACKAGE_SCRIPT)}")]
    text = PACKAGE_SCRIPT.read_text(encoding="utf-8")
    final_secret = 'run_step("Final transfer sidecar secret scan QA"'
    final_freshness = 'run_step("Final release freshness QA"'
    post_validation = 'run_step("Post-package validation QA"'
    final_secret_index = text.find(final_secret)
    final_freshness_index = text.find(final_freshness)
    post_validation_index = text.find(post_validation)
    last_sidecar_write_index = text.rfind("write_report(steps)")
    missing = [
        marker
        for marker, index in [
            ("Final transfer sidecar secret scan QA", final_secret_index),
            ("Final release freshness QA", final_freshness_index),
            ("Post-package validation QA", post_validation_index),
            ("write_report(steps)", last_sidecar_write_index),
        ]
        if index < 0
    ]
    if missing:
        return [Check("Package flow final source order", "FAIL", f"missing markers: {missing}")]
    ordered = last_sidecar_write_index < final_secret_index < final_freshness_index < post_validation_index
    sidecar_rewrite_after_final_scan = text.find("write_report(steps)", final_secret_index) >= 0
    return [
        Check(
            "Package flow final source order",
            "PASS" if ordered else "FAIL",
            "write_report -> final sidecar scan -> final freshness -> post-package validation",
        ),
        Check(
            "Package flow no sidecar rewrite after final scan",
            "PASS" if not sidecar_rewrite_after_final_scan else "FAIL",
            "no write_report(steps) after final sidecar scan",
        ),
    ]


def check_post_package_report_timing(generated_at: datetime) -> list[Check]:
    checks: list[Check] = []
    generated_epoch = generated_at.timestamp()
    for name, path in [
        ("Post-package generated after final sidecar scan", SECRET_SCAN_REPORT),
        ("Post-package generated after final freshness", FRESHNESS_REPORT),
    ]:
        if not path.exists():
            checks.append(Check(name, "FAIL", f"missing {rel(path)}"))
            continue
        checks.append(
            Check(
                name,
                "PASS" if generated_epoch >= path.stat().st_mtime else "FAIL",
                f"post-package generated {generated_at.isoformat()}, source {mtime_iso(path)}",
            ),
        )
    return checks


def write_reports(checks: list[Check], generated_at: datetime) -> None:
    status = "FAIL" if any(check.status == "FAIL" for check in checks) else "PASS"
    payload = {
        "generatedAt": generated_at.isoformat(),
        "status": status,
        "checks": [check.__dict__ for check in checks],
        "transferSidecars": [rel(path) for path in expected_sidecars()],
        "nonTransferReports": [rel(REPORT_MD), rel(REPORT_JSON)],
        "secretScanReport": rel(SECRET_SCAN_REPORT),
        "freshnessReport": rel(FRESHNESS_REPORT),
        "localQaReports": [rel(HANDOFF_QA_REPORT), rel(ARCHIVE_QA_REPORT)],
        "validatedSequence": [
            "python3 scripts/play_handoff_secret_scan_qa.py",
            "python3 scripts/release_freshness_qa.py",
            "python3 scripts/post_package_validation_qa.py",
        ],
        "packageFlowSource": rel(PACKAGE_SCRIPT),
    }
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Post-package Validation QA",
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
    generated_at = datetime.now(timezone.utc)
    sidecars = expected_sidecars()
    checks: list[Check] = [
        *check_transfer_artifacts_exist(sidecars),
        *check_transfer_file_set(sidecars),
        *check_archive_integrity(),
        *check_handoff_directory_integrity(),
        *check_local_handoff_qa_reports(),
        *check_secret_scan(sidecars),
        *check_freshness_ordering(),
        *check_package_sidecar_parity(),
        *check_package_markdown_content(),
        *check_report_is_non_transfer(sidecars),
        *check_package_flow_source_order(),
        *check_post_package_report_timing(generated_at),
    ]
    write_reports(checks, generated_at)
    failures = [check for check in checks if check.status == "FAIL"]
    if failures:
        print("Post-package validation QA failed")
        for failure in failures:
            print(f"- {failure.name}: {failure.detail}")
        print(f"Report: {rel(REPORT_MD)}")
        raise SystemExit(1)
    print(f"Post-package validation QA PASS ({rel(REPORT_MD)}, {rel(REPORT_JSON)})")


if __name__ == "__main__":
    main()
