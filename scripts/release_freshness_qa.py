#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_MD = ROOT / "build/reports/release_freshness.md"
REPORT_JSON = ROOT / "build/reports/release_freshness.json"
HANDOFF = ROOT / "build/play_handoff/shawarma58-v1.0.0"
ARCHIVE = ROOT / "build/play_handoff/shawarma58-v1.0.0.zip"
PACKAGE_REPORT = ROOT / "build/reports/release_candidate_package.json"
ARCHIVE_PACKAGE_REPORT = ROOT / "build/play_handoff/shawarma58-v1.0.0.zip.package.json"
RELEASE_GATE_REPORT = ROOT / "build/reports/release_gate.json"
PRE_UPLOAD_BLOCKERS_REPORT = ROOT / "build/reports/pre_upload_blockers.json"
CREATE_HANDOFF_SCRIPT = ROOT / "scripts/create_play_handoff.py"
ALLOWED_PACKAGE_STATUSES = {"PASS", "PASS_WITH_WARNINGS", "EXTERNAL_BLOCKER"}
HANDOFF_ROOT_RELATIVE = "build/play_handoff/shawarma58-v1.0.0"

JSON_REPORTS = [
    "build/reports/accessibility_source.json",
    "build/reports/asset.json",
    "build/reports/artifact_provenance.json",
    "build/reports/asset_manifest.json",
    "build/reports/content_copy.json",
    "build/reports/completion_audit.json",
    "build/reports/fastlane_assets.json",
    "build/reports/fastlane_config.json",
    "build/reports/fastlane_runtime.json",
    "build/reports/performance_budget.json",
    "build/reports/physical_device_readiness.json",
    "build/reports/pre_upload_blockers.json",
    "build/reports/play_console_forms.json",
    "build/reports/play_external_readiness.json",
    "build/reports/play_handoff_archive_qa.json",
    "build/reports/play_handoff_qa.json",
    "build/reports/play_metadata.json",
    "build/reports/play_upload_packet.json",
    "build/reports/play_upload_auth.json",
    "build/reports/privacy_policy_hosting.json",
    "build/reports/play_handoff_secret_scan.json",
    "build/reports/play_target_api.json",
    "build/reports/privacy_data_safety.json",
    "build/reports/release_candidate_package.json",
    "build/reports/release_dates.json",
    "build/reports/release_gate.json",
    "build/reports/signing_env.json",
    "build/reports/store_screenshot_capture.json",
    "build/reports/store_screenshot_capture_guard.json",
    "build/reports/store_screenshot_freshness.json",
    "build/reports/store_visual_quality.json",
    "build/reports/upload_keystore_setup.json",
    "build/reports/upload_operator_runbook.json",
    "build/reports/ui_behavior.json",
    "build/reports/workspace_hygiene.json",
    "build/play_handoff/shawarma58-v1.0.0/manifest.json",
    "build/play_handoff/shawarma58-v1.0.0/privacy/hosting/manifest.json",
    "build/play_handoff/shawarma58-v1.0.0/qa/accessibility_source/accessibility_source.json",
    "build/play_handoff/shawarma58-v1.0.0/qa/asset_manifest/asset_manifest.json",
    "build/play_handoff/shawarma58-v1.0.0/qa/asset/asset.json",
    "build/play_handoff/shawarma58-v1.0.0/qa/content_copy/content_copy.json",
    "build/play_handoff/shawarma58-v1.0.0/qa/ui_behavior/ui_behavior.json",
    "build/play_handoff/shawarma58-v1.0.0/qa/completion_audit/completion_audit.json",
    "build/play_handoff/shawarma58-v1.0.0/qa/fastlane_assets/fastlane_assets.json",
    "build/play_handoff/shawarma58-v1.0.0/qa/fastlane_config/fastlane_config.json",
    "build/play_handoff/shawarma58-v1.0.0/qa/fastlane_runtime/fastlane_runtime.json",
    "build/play_handoff/shawarma58-v1.0.0/qa/pre_upload_blockers/pre_upload_blockers.json",
    "build/play_handoff/shawarma58-v1.0.0/qa/release_gate/release_gate.json",
    "build/play_handoff/shawarma58-v1.0.0/qa/artifact_provenance/artifact_provenance.json",
    "build/play_handoff/shawarma58-v1.0.0/qa/performance_budget/performance_budget.json",
    "build/play_handoff/shawarma58-v1.0.0/qa/physical_device_readiness/physical_device_readiness.json",
    "build/play_handoff/shawarma58-v1.0.0/qa/play_metadata/play_metadata.json",
    "build/play_handoff/shawarma58-v1.0.0/qa/play_external_readiness/play_external_readiness.json",
    "build/play_handoff/shawarma58-v1.0.0/qa/play_upload_packet/play_upload_packet.json",
    "build/play_handoff/shawarma58-v1.0.0/qa/play_upload_auth/play_upload_auth.json",
    "build/play_handoff/shawarma58-v1.0.0/qa/play_console_forms/play_console_forms.json",
    "build/play_handoff/shawarma58-v1.0.0/qa/play_target_api/play_target_api.json",
    "build/play_handoff/shawarma58-v1.0.0/qa/privacy_data_safety/privacy_data_safety.json",
    "build/play_handoff/shawarma58-v1.0.0/qa/privacy_policy_hosting/privacy_policy_hosting.json",
    "build/play_handoff/shawarma58-v1.0.0/qa/signing_env/signing_env.json",
    "build/play_handoff/shawarma58-v1.0.0/qa/store_screenshot_capture/store_screenshot_capture.json",
    "build/play_handoff/shawarma58-v1.0.0/qa/store_screenshot_capture_guard/store_screenshot_capture_guard.json",
    "build/play_handoff/shawarma58-v1.0.0/qa/store_screenshot_freshness/store_screenshot_freshness.json",
    "build/play_handoff/shawarma58-v1.0.0/qa/store_visual_quality/store_visual_quality.json",
    "build/play_handoff/shawarma58-v1.0.0/qa/upload_keystore_setup/upload_keystore_setup.json",
    "build/play_handoff/shawarma58-v1.0.0/qa/upload_operator_runbook/upload_operator_runbook.json",
    "build/play_handoff/shawarma58-v1.0.0/qa/workspace_hygiene/workspace_hygiene.json",
    "build/play_handoff/shawarma58-v1.0.0.zip.json",
    "build/play_handoff/shawarma58-v1.0.0.zip.package.json",
]
DATED_DOCS = {
    "store/play_upload_packet.md": "Date: {label}.",
    "docs/completion_audit.md": "Date: {label}.",
    "docs/release_candidate_package.md": "Date: {label}.",
    "docs/fastlane_upload.md": "Date: {label}.",
    "docs/deobfuscation_notes.md": "Date: {label}.",
    "docs/google_play_checklist.md": "- Checked on {label}.",
}
OPTIONAL_HANDOFF_REPORTS = {
    "qa/instrumentation_smoke/instrumentation_smoke.json": {"PASS"},
    "qa/connected_performance/connected_performance.json": {"PASS", "PASS_WITH_WARNINGS"},
}


@dataclass
class Check:
    name: str
    status: str
    detail: str


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def load_json(relative: str) -> dict[str, object]:
    path = ROOT / relative
    if not path.exists():
        raise FileNotFoundError(relative)
    return json.loads(path.read_text(encoding="utf-8"))


def parse_generated_date(value: object) -> date | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value).astimezone().date()
    except ValueError:
        return None


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def mandatory_handoff_json_reports() -> list[str]:
    spec = importlib.util.spec_from_file_location(
        "create_play_handoff_for_freshness",
        CREATE_HANDOFF_SCRIPT,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {rel(CREATE_HANDOFF_SCRIPT)}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    files = getattr(module, "FILES", None)
    if not isinstance(files, dict):
        raise RuntimeError("create_play_handoff.FILES is not a dict")
    return sorted(
        f"{HANDOFF_ROOT_RELATIVE}/{target}"
        for target in files
        if isinstance(target, str) and target.startswith("qa/") and target.endswith(".json")
    )


def check_mandatory_handoff_json_coverage() -> list[Check]:
    try:
        expected_reports = set(mandatory_handoff_json_reports())
    except Exception as exc:
        return [Check("Mandatory handoff QA JSON coverage", "FAIL", str(exc))]
    covered_reports = set(JSON_REPORTS)
    missing = sorted(expected_reports - covered_reports)
    status = "PASS" if not missing else "FAIL"
    detail = (
        f"{len(expected_reports)} mandatory handoff QA JSON reports covered"
        if not missing
        else f"missing freshness coverage: {', '.join(missing)}"
    )
    return [Check("Mandatory handoff QA JSON coverage", status, detail)]


def check_dated_docs(today_label: str) -> list[Check]:
    checks: list[Check] = []
    for relative, template in DATED_DOCS.items():
        path = ROOT / relative
        expected = template.format(label=today_label)
        if not path.exists():
            checks.append(Check(f"{relative} date", "FAIL", "file is missing"))
            continue
        text = path.read_text(encoding="utf-8")
        status = "PASS" if expected in text else "FAIL"
        checks.append(Check(f"{relative} date", status, f"expected {expected!r}"))
    return checks


def check_json_freshness(today: date) -> list[Check]:
    checks: list[Check] = []
    for relative in JSON_REPORTS:
        try:
            report = load_json(relative)
        except FileNotFoundError:
            checks.append(Check(f"{relative} generatedAt", "FAIL", "file is missing"))
            continue
        generated = parse_generated_date(report.get("generatedAt"))
        status = "PASS" if generated == today else "FAIL"
        checks.append(
            Check(
                f"{relative} generatedAt",
                status,
                f"generated date {generated}, expected {today}",
            ),
        )
    return checks


def check_archive_sidecars() -> list[Check]:
    checks: list[Check] = []
    report_path = ARCHIVE.with_suffix(ARCHIVE.suffix + ".json")
    sidecar_path = ARCHIVE.with_suffix(ARCHIVE.suffix + ".sha256")
    manifest_path = HANDOFF / "manifest.json"
    if not ARCHIVE.exists():
        return [Check("Archive exists", "FAIL", f"missing {rel(ARCHIVE)}")]
    actual_sha = sha256(ARCHIVE)
    manifest_sha = sha256(manifest_path) if manifest_path.exists() else ""
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
    report_sha = report.get("sha256")
    checks.append(
        Check(
            "Archive JSON checksum",
            "PASS" if report_sha == actual_sha else "FAIL",
            f"json sha {report_sha}, actual {actual_sha}",
        ),
    )
    checks.append(
        Check(
            "Archive JSON manifest checksum",
            "PASS" if report.get("manifestSha256") == manifest_sha else "FAIL",
            f"json manifest sha {report.get('manifestSha256')}, actual {manifest_sha}",
        ),
    )
    if not sidecar_path.exists():
        checks.append(Check("Archive SHA sidecar", "FAIL", f"missing {rel(sidecar_path)}"))
    else:
        sidecar = sidecar_path.read_text(encoding="utf-8").strip()
        expected_sidecar = f"{actual_sha}  {ARCHIVE.name}"
        checks.append(
            Check(
                "Archive SHA sidecar",
                "PASS" if sidecar == expected_sidecar else "FAIL",
                f"sidecar {sidecar!r}, expected {expected_sidecar!r}",
            ),
        )
    return checks


def expected_package_status(package: dict[str, object], release_gate: dict[str, object]) -> str:
    steps = package.get("steps")
    if isinstance(steps, list):
        for step in steps:
            if isinstance(step, dict) and step.get("status") == "FAIL":
                return "FAIL"
    release_gate_status = release_gate.get("status")
    if release_gate_status in {"FAIL", "EXTERNAL_BLOCKER", "PASS_WITH_WARNINGS"}:
        return str(release_gate_status)
    return "PASS"


def markdown_status(path: Path) -> str:
    if not path.exists():
        return ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("Status: `") and line.endswith("`"):
            return line.removeprefix("Status: `").removesuffix("`")
    return ""


def check_package_report_status() -> list[Check]:
    checks: list[Check] = []
    required_paths = [
        PACKAGE_REPORT,
        ARCHIVE_PACKAGE_REPORT,
        RELEASE_GATE_REPORT,
        PRE_UPLOAD_BLOCKERS_REPORT,
    ]
    missing = [rel(path) for path in required_paths if not path.exists()]
    if missing:
        return [Check("Package status parity", "FAIL", f"missing files: {', '.join(missing)}")]

    package = json.loads(PACKAGE_REPORT.read_text(encoding="utf-8"))
    archive_package = json.loads(ARCHIVE_PACKAGE_REPORT.read_text(encoding="utf-8"))
    release_gate = json.loads(RELEASE_GATE_REPORT.read_text(encoding="utf-8"))
    pre_upload = json.loads(PRE_UPLOAD_BLOCKERS_REPORT.read_text(encoding="utf-8"))

    package_status = package.get("status")
    sidecar_status = archive_package.get("status")
    expected_status = expected_package_status(package, release_gate)
    checks.append(
        Check(
            "Package status value",
            "PASS" if package_status in ALLOWED_PACKAGE_STATUSES else "FAIL",
            f"status {package_status}, allowed {sorted(ALLOWED_PACKAGE_STATUSES)}",
        ),
    )
    checks.append(
        Check(
            "Package status derivation",
            "PASS" if package_status == expected_status else "FAIL",
            f"package {package_status}, expected {expected_status} from release gate",
        ),
    )
    checks.append(
        Check(
            "Package sidecar parity",
            "PASS" if archive_package == package else "FAIL",
            "zip package JSON matches build/reports package JSON",
        ),
    )
    checks.append(
        Check(
            "Package sidecar status",
            "PASS" if sidecar_status == package_status else "FAIL",
            f"sidecar {sidecar_status}, root {package_status}",
        ),
    )

    release_gate_section = package.get("releaseGate")
    release_gate_status = release_gate.get("status")
    if not isinstance(release_gate_section, dict):
        checks.append(Check("Package releaseGate section", "FAIL", "releaseGate is missing or not an object"))
    else:
        checks.append(
            Check(
                "Package releaseGate status",
                "PASS" if release_gate_section.get("status") == release_gate_status else "FAIL",
                f"package {release_gate_section.get('status')}, release gate {release_gate_status}",
            ),
        )

    pre_upload_section = package.get("preUploadBlockers")
    if not isinstance(pre_upload_section, dict):
        checks.append(Check("Package pre-upload section", "FAIL", "preUploadBlockers is missing or not an object"))
    else:
        checks.append(
            Check(
                "Package pre-upload status",
                "PASS" if pre_upload_section.get("status") == pre_upload.get("status") else "FAIL",
                f"package {pre_upload_section.get('status')}, source {pre_upload.get('status')}",
            ),
        )
        checks.append(
            Check(
                "Package pre-upload base status",
                "PASS" if pre_upload_section.get("baseStatus") == pre_upload.get("baseStatus") else "FAIL",
                f"package {pre_upload_section.get('baseStatus')}, source {pre_upload.get('baseStatus')}",
            ),
        )

    archive_section = package.get("archive")
    actual_sha = sha256(ARCHIVE) if ARCHIVE.exists() else ""
    manifest_path = HANDOFF / "manifest.json"
    manifest_sha = sha256(manifest_path) if manifest_path.exists() else ""
    if not isinstance(archive_section, dict):
        checks.append(Check("Package archive section", "FAIL", "archive is missing or not an object"))
    else:
        checks.append(
            Check(
                "Package archive SHA",
                "PASS" if archive_section.get("sha256") == actual_sha else "FAIL",
                f"package {archive_section.get('sha256')}, actual {actual_sha}",
            ),
        )
        checks.append(
            Check(
                "Package archive manifest SHA",
                "PASS" if archive_section.get("manifestSha256") == manifest_sha else "FAIL",
                f"package {archive_section.get('manifestSha256')}, actual {manifest_sha}",
            ),
        )
        checks.append(
            Check(
                "Package archive SHA sidecar path",
                "PASS" if archive_section.get("sha256File") == rel(ARCHIVE.with_suffix(ARCHIVE.suffix + ".sha256")) else "FAIL",
                f"package {archive_section.get('sha256File')}, expected {rel(ARCHIVE.with_suffix(ARCHIVE.suffix + '.sha256'))}",
            ),
        )
        expected_verify_command = (
            f"cd {ARCHIVE.parent.relative_to(ROOT).as_posix()} "
            f"&& shasum -a 256 -c {ARCHIVE.with_suffix(ARCHIVE.suffix + '.sha256').name}"
        )
        checks.append(
            Check(
                "Package archive verify command",
                "PASS" if archive_section.get("verifyCommand") == expected_verify_command else "FAIL",
                f"package {archive_section.get('verifyCommand')}, expected {expected_verify_command}",
            ),
        )
        checks.append(
            Check(
                "Package archive path",
                "PASS" if archive_section.get("path") == rel(ARCHIVE) else "FAIL",
                f"package {archive_section.get('path')}, expected {rel(ARCHIVE)}",
            ),
        )

    md_status = markdown_status(PACKAGE_REPORT.with_suffix(".md"))
    sidecar_md_status = markdown_status(ARCHIVE_PACKAGE_REPORT.with_suffix(".md"))
    checks.append(
        Check(
            "Package markdown status",
            "PASS" if md_status == package_status else "FAIL",
            f"markdown {md_status}, JSON {package_status}",
        ),
    )
    checks.append(
        Check(
            "Package sidecar markdown status",
            "PASS" if sidecar_md_status == package_status else "FAIL",
            f"sidecar markdown {sidecar_md_status}, JSON {package_status}",
        ),
    )

    external_blockers = package.get("externalBlockers")
    pending_actions = pre_upload_section.get("pendingActions") if isinstance(pre_upload_section, dict) else []
    if package_status == "EXTERNAL_BLOCKER":
        has_blockers = (
            isinstance(external_blockers, list)
            and len(external_blockers) > 0
            and isinstance(pending_actions, list)
            and len(pending_actions) > 0
        )
        checks.append(
            Check(
                "Package external-blocker detail",
                "PASS" if has_blockers else "FAIL",
                "EXTERNAL_BLOCKER packages must carry raw blockers and pending actions",
            ),
        )
    return checks


def check_optional_handoff_reports(today: date) -> list[Check]:
    manifest_path = HANDOFF / "manifest.json"
    if not manifest_path.exists():
        return [Check("Optional handoff reports", "FAIL", "handoff manifest is missing")]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = manifest.get("files")
    if not isinstance(files, dict):
        return [Check("Optional handoff reports", "FAIL", "manifest.files is not an object")]
    checks: list[Check] = []
    for relative, allowed_statuses in OPTIONAL_HANDOFF_REPORTS.items():
        if relative not in files:
            checks.append(
                Check(
                    f"{relative} optional status",
                    "PASS",
                    "not included; optional report absent or not passing",
                ),
            )
            continue
        report_path = HANDOFF / relative
        report = json.loads(report_path.read_text(encoding="utf-8"))
        status_value = report.get("status")
        generated = parse_generated_date(report.get("generatedAt"))
        checks.append(
            Check(
                f"{relative} optional status",
                "PASS" if status_value in allowed_statuses else "FAIL",
                f"status {status_value}, allowed {sorted(allowed_statuses)}",
            ),
        )
        checks.append(
            Check(
                f"{relative} optional generatedAt",
                "PASS" if generated == today else "FAIL",
                f"generated date {generated}, expected {today}",
            ),
        )
    return checks


def write_reports(checks: list[Check]) -> None:
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    status = "FAIL" if any(check.status == "FAIL" for check in checks) else "PASS"
    payload = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "checks": [check.__dict__ for check in checks],
    }
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Release Freshness QA",
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


def today_label(today: date) -> str:
    return f"{today.strftime('%B')} {today.day}, {today.year}"


def main() -> None:
    today = date.today()
    checks = [
        *check_dated_docs(today_label(today)),
        *check_mandatory_handoff_json_coverage(),
        *check_json_freshness(today),
        *check_archive_sidecars(),
        *check_package_report_status(),
        *check_optional_handoff_reports(today),
    ]
    write_reports(checks)
    failures = [check for check in checks if check.status == "FAIL"]
    if failures:
        print("Release freshness QA failed")
        for failure in failures:
            print(f"- {failure.name}: {failure.detail}")
        raise SystemExit(1)
    print("Release freshness QA PASS")


if __name__ == "__main__":
    main()
