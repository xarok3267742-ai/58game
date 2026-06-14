#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from capture_store_screenshots import SCREENSHOTS, STORE_SCREENSHOTS, validate_screenshot_candidate  # noqa: E402


REPORT_MD = ROOT / "build/reports/store_screenshot_capture_guard.md"
REPORT_JSON = ROOT / "build/reports/store_screenshot_capture_guard.json"
TMP_DIR = ROOT / "build/tmp/store_screenshot_capture_guard"
CAPTURE_HELPER = ROOT / "scripts/capture_store_screenshots.py"


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def validate_current_store_screenshots() -> Check:
    details: list[str] = []
    for filename in SCREENSHOTS:
        path = STORE_SCREENSHOTS / filename
        if not path.is_file():
            return Check("Current store screenshots", "FAIL", f"missing {rel(path)}")
        metrics = validate_screenshot_candidate(path)
        details.append(f"{filename}: {metrics.byte_count} bytes, stddev {metrics.gray_stddev}, colors {metrics.thumbnail_colors}")
    return Check("Current store screenshots", "PASS", "; ".join(details))


def validate_black_candidate_rejection() -> Check:
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    black = TMP_DIR / "black_candidate.png"
    Image.new("RGB", (1080, 2400), (0, 0, 0)).save(black)
    try:
        validate_screenshot_candidate(black)
    except RuntimeError as error:
        message = str(error)
        required_terms = ["minimum 120000", "grayscale stddev", "sampled colors"]
        missing = [term for term in required_terms if term not in message]
        if missing:
            return Check("Black candidate rejection", "FAIL", f"rejection missing terms: {missing}; message={message}")
        return Check("Black candidate rejection", "PASS", message)
    return Check("Black candidate rejection", "FAIL", "solid black 1080x2400 PNG was accepted")


def validate_pre_overwrite_wiring() -> Check:
    source = CAPTURE_HELPER.read_text(encoding="utf-8")
    required = [
        'candidate_path = out_dir / f"candidate_{store_filename}"',
        "screencap(smoke.serial, candidate_path)",
        "metrics = validate_screenshot_candidate(candidate_path)",
        "store_path.write_bytes(candidate_path.read_bytes())",
    ]
    missing = [snippet for snippet in required if snippet not in source]
    if missing:
        return Check("Pre-overwrite capture wiring", "FAIL", f"missing snippets: {missing}")
    forbidden = "screencap(smoke.serial, store_path)"
    if forbidden in source:
        return Check("Pre-overwrite capture wiring", "FAIL", f"helper still writes screencap directly to store path: {forbidden}")
    return Check("Pre-overwrite capture wiring", "PASS", "screencap writes candidate first and store overwrite happens after validation")


def write_reports(checks: list[Check]) -> None:
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    status = "FAIL" if any(check.status == "FAIL" for check in checks) else "PASS"
    payload = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "checks": [check.__dict__ for check in checks],
        "candidateThresholds": {
            "size": [1080, 2400],
            "minBytes": 120000,
            "minGrayStddev": 20.0,
            "minThumbnailColors": 450,
        },
    }
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Store Screenshot Capture Guard QA",
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
        validate_current_store_screenshots(),
        validate_black_candidate_rejection(),
        validate_pre_overwrite_wiring(),
    ]
    write_reports(checks)
    failures = [check for check in checks if check.status == "FAIL"]
    if failures:
        print("Store screenshot capture guard QA failed")
        for failure in failures:
            print(f"- {failure.name}: {failure.detail}")
        raise SystemExit(1)
    print(f"Store screenshot capture guard QA PASS ({rel(REPORT_MD)}, {rel(REPORT_JSON)})")


if __name__ == "__main__":
    main()
