#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
CAPTURE_ROOT = ROOT / "build/store_screenshot_capture"
REPORT_MD = ROOT / "build/reports/store_screenshot_capture.md"
REPORT_JSON = ROOT / "build/reports/store_screenshot_capture.json"
EXPECTED_PACKAGE = "com.andrejivliev.shawarma58.debug"
EXPECTED_SIZE = (1080, 2400)
SCREENSHOTS = [
    "shawarma_onboarding.png",
    "shawarma_menu.png",
    "shawarma_levels.png",
    "shawarma_gameplay.png",
    "shawarma_result.png",
    "shawarma_wrong_order.png",
    "shawarma_endless_result.png",
]
SOURCE_GLOBS = [
    "app/src/main/AndroidManifest.xml",
    "app/src/main/java/**/*.kt",
    "app/src/main/res/drawable/**/*",
    "app/src/main/res/drawable-nodpi/**/*",
    "app/src/main/res/mipmap-*/*",
    "app/src/main/res/values/**/*.xml",
    "app/src/main/res/xml/**/*.xml",
]


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iso_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).replace(microsecond=0).isoformat()


def file_info(path: Path) -> dict[str, object]:
    return {
        "path": rel(path),
        "modifiedAt": iso_mtime(path),
        "mtime": path.stat().st_mtime,
        "bytes": path.stat().st_size,
    }


def discover_sources() -> list[Path]:
    sources: set[Path] = set()
    for pattern in SOURCE_GLOBS:
        for path in ROOT.glob(pattern):
            if path.is_file():
                sources.add(path)
    return sorted(sources)


def parse_summary(summary: str) -> dict[str, object]:
    serial_match = re.search(r"Serial: `([^`]+)`", summary)
    package_match = re.search(r"Package: `([^`]+)`", summary)
    generated_match = re.search(r"Generated: `([^`]+)`", summary)
    captured = re.findall(r"- `([^`]+)`", summary)
    return {
        "serial": serial_match.group(1) if serial_match else "",
        "package": package_match.group(1) if package_match else "",
        "generatedAt": generated_match.group(1) if generated_match else "",
        "captured": captured,
    }


def summary_generated_epoch(summary_info: dict[str, object], summary_path: Path) -> float:
    generated = summary_info.get("generatedAt")
    if isinstance(generated, str) and generated:
        try:
            return datetime.fromisoformat(generated).timestamp()
        except ValueError:
            pass
    return summary_path.stat().st_mtime


def latest_passing_capture_dir() -> Path | None:
    if not CAPTURE_ROOT.exists():
        return None
    candidates: list[tuple[Path, float]] = []
    for directory in sorted(CAPTURE_ROOT.iterdir()):
        summary = directory / "summary.md"
        if not directory.is_dir() or not summary.exists():
            continue
        text = summary.read_text(encoding="utf-8")
        if "Status: PASS" not in text:
            continue
        summary_info = parse_summary(text)
        if not is_complete_capture(directory, summary_info):
            continue
        candidates.append((directory, summary_generated_epoch(summary_info, summary)))
    if not candidates:
        return None
    return max(candidates, key=lambda candidate: (candidate[1], candidate[0].name))[0]


def is_complete_capture(capture_dir: Path, summary_info: dict[str, object]) -> bool:
    captured_paths = set(summary_info.get("captured", []))
    expected_captured = {f"store/screenshots/{filename}" for filename in SCREENSHOTS}
    if summary_info.get("package") != EXPECTED_PACKAGE or captured_paths != expected_captured:
        return False
    return all((capture_dir / filename).is_file() for filename in SCREENSHOTS)


def capture_freshness_checks(capture_dir: Path, summary_info: dict[str, object]) -> tuple[list[Check], dict[str, object] | None]:
    sources = discover_sources()
    if not sources:
        return [Check("Capture freshness baseline", "FAIL", "no UI/resource source files found")], None
    newest_source = max(sources, key=lambda path: path.stat().st_mtime)
    capture_epoch = summary_generated_epoch(summary_info, capture_dir / "summary.md")
    baseline = Check("Capture freshness baseline", "PASS", f"{len(sources)} UI/resource source files tracked")
    if capture_epoch < newest_source.stat().st_mtime:
        return [
            baseline,
            Check("Capture evidence freshness", "FAIL", f"latest passing capture is older than {rel(newest_source)}"),
        ], file_info(newest_source)
    return [
        baseline,
        Check("Capture evidence freshness", "PASS", "latest passing capture is newer than tracked UI source"),
    ], file_info(newest_source)


def file_record(capture_dir: Path, filename: str) -> tuple[dict[str, object], list[Check]]:
    checks: list[Check] = []
    capture_path = capture_dir / filename
    store_path = ROOT / "store/screenshots" / filename
    record: dict[str, object] = {
        "filename": filename,
        "capturePath": rel(capture_path),
        "storePath": rel(store_path),
    }
    if not capture_path.exists():
        checks.append(Check(f"{filename} capture file", "FAIL", "capture PNG is missing"))
        return record, checks
    if not store_path.exists():
        checks.append(Check(f"{filename} store file", "FAIL", "store screenshot is missing"))
        return record, checks
    capture_sha = sha256(capture_path)
    store_sha = sha256(store_path)
    capture_size = Image.open(capture_path).size
    store_size = Image.open(store_path).size
    record.update(
        {
            "captureSha256": capture_sha,
            "storeSha256": store_sha,
            "captureBytes": capture_path.stat().st_size,
            "storeBytes": store_path.stat().st_size,
            "captureSize": list(capture_size),
            "storeSize": list(store_size),
        },
    )
    checks.append(
        Check(
            f"{filename} SHA parity",
            "PASS" if capture_sha == store_sha else "FAIL",
            "capture PNG matches current store screenshot" if capture_sha == store_sha else "capture/store SHA mismatch",
        ),
    )
    checks.append(
        Check(
            f"{filename} dimensions",
            "PASS" if capture_size == EXPECTED_SIZE and store_size == EXPECTED_SIZE else "FAIL",
            f"capture {capture_size}, store {store_size}, expected {EXPECTED_SIZE}",
        ),
    )
    return record, checks


def write_reports(
    *,
    capture_dir: Path | None,
    summary_info: dict[str, object],
    newest_source: dict[str, object] | None,
    screenshot_records: list[dict[str, object]],
    checks: list[Check],
) -> None:
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    status = "FAIL" if any(check.status == "FAIL" for check in checks) else "PASS"
    payload = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "captureDir": rel(capture_dir) if capture_dir else "",
        "sourceGlobs": SOURCE_GLOBS,
        "newestSource": newest_source,
        "summary": summary_info,
        "screenshots": screenshot_records,
        "checks": [check.__dict__ for check in checks],
    }
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Store Screenshot Capture QA",
        "",
        f"Generated: {payload['generatedAt']}",
        f"Status: `{status}`",
        f"Capture directory: `{payload['captureDir']}`",
        f"Serial: `{summary_info.get('serial', '')}`",
        f"Package: `{summary_info.get('package', '')}`",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for check in checks:
        lines.append(f"| {check.name} | {check.status} | {check.detail} |")
    if newest_source:
        lines.extend(
            [
                "",
                "## Newest UI Source",
                f"- `{newest_source['path']}` at `{newest_source['modifiedAt']}`",
            ],
        )
    lines.extend(["", "## Screenshot SHA Evidence", "| File | Store SHA-256 | Capture SHA-256 |", "|---|---|---|"])
    for record in screenshot_records:
        lines.append(
            "| {file} | `{store}` | `{capture}` |".format(
                file=record.get("filename", ""),
                store=record.get("storeSha256", ""),
                capture=record.get("captureSha256", ""),
            ),
        )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    checks: list[Check] = []
    capture_dir = latest_passing_capture_dir()
    if capture_dir is None:
        checks.append(Check("Latest passing capture", "FAIL", "no PASS summary under build/store_screenshot_capture"))
        write_reports(capture_dir=None, summary_info={}, newest_source=None, screenshot_records=[], checks=checks)
        raise SystemExit("Store screenshot capture QA failed: no passing capture evidence")

    summary_path = capture_dir / "summary.md"
    summary = summary_path.read_text(encoding="utf-8")
    summary_info = parse_summary(summary)
    checks.append(Check("Latest passing capture", "PASS", rel(capture_dir)))
    freshness_checks, newest_source = capture_freshness_checks(capture_dir, summary_info)
    checks.extend(freshness_checks)
    checks.append(
        Check(
            "Capture package",
            "PASS" if summary_info.get("package") == EXPECTED_PACKAGE else "FAIL",
            str(summary_info.get("package", "")),
        ),
    )
    captured_paths = set(summary_info.get("captured", []))
    expected_captured = {f"store/screenshots/{filename}" for filename in SCREENSHOTS}
    missing_summary_entries = sorted(expected_captured - captured_paths)
    checks.append(
        Check(
            "Summary captured list",
            "PASS" if not missing_summary_entries else "FAIL",
            "all seven screenshots listed" if not missing_summary_entries else ", ".join(missing_summary_entries),
        ),
    )

    screenshot_records: list[dict[str, object]] = []
    for filename in SCREENSHOTS:
        record, file_checks = file_record(capture_dir, filename)
        screenshot_records.append(record)
        checks.extend(file_checks)

    write_reports(
        capture_dir=capture_dir,
        summary_info=summary_info,
        newest_source=newest_source,
        screenshot_records=screenshot_records,
        checks=checks,
    )

    failures = [check for check in checks if check.status == "FAIL"]
    if failures:
        print("Store screenshot capture QA failed")
        for failure in failures:
            print(f"- {failure.name}: {failure.detail}")
        raise SystemExit(1)
    print(f"Store screenshot capture QA PASS ({rel(REPORT_MD)}, {rel(REPORT_JSON)})")


if __name__ == "__main__":
    main()
