#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_MD = ROOT / "build/reports/store_screenshot_freshness.md"
REPORT_JSON = ROOT / "build/reports/store_screenshot_freshness.json"

UPLOAD_SCREENSHOTS = [
    ROOT / "store/screenshots/shawarma_onboarding.png",
    ROOT / "store/screenshots/shawarma_menu.png",
    ROOT / "store/screenshots/shawarma_levels.png",
    ROOT / "store/screenshots/shawarma_gameplay.png",
    ROOT / "store/screenshots/shawarma_result.png",
]
QA_SCREENSHOTS = [
    ROOT / "store/screenshots/shawarma_wrong_order.png",
    ROOT / "store/screenshots/shawarma_endless_result.png",
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


@dataclass
class Check:
    name: str
    status: str
    detail: str


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def iso_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).replace(microsecond=0).isoformat()


def discover_sources() -> list[Path]:
    sources: set[Path] = set()
    for pattern in SOURCE_GLOBS:
        for path in ROOT.glob(pattern):
            if path.is_file():
                sources.add(path)
    return sorted(sources)


def file_info(path: Path) -> dict[str, object]:
    return {
        "path": rel(path),
        "modifiedAt": iso_mtime(path),
        "mtime": path.stat().st_mtime,
        "bytes": path.stat().st_size,
    }


def stale_since(paths: list[Path], newest_source_mtime: float) -> list[dict[str, object]]:
    return [file_info(path) for path in paths if path.exists() and path.stat().st_mtime < newest_source_mtime]


def write_reports(
    *,
    strict: bool,
    status: str,
    checks: list[Check],
    sources: list[Path],
    upload_stale: list[dict[str, object]],
    qa_stale: list[dict[str, object]],
) -> None:
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    newest_source = max(sources, key=lambda path: path.stat().st_mtime) if sources else None
    payload = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "strict": strict,
        "sourceGlobs": SOURCE_GLOBS,
        "newestSource": file_info(newest_source) if newest_source else None,
        "screenshots": {
            "upload": [file_info(path) for path in UPLOAD_SCREENSHOTS if path.exists()],
            "qa": [file_info(path) for path in QA_SCREENSHOTS if path.exists()],
        },
        "staleScreenshots": {
            "upload": upload_stale,
            "qa": qa_stale,
        },
        "checks": [check.__dict__ for check in checks],
    }
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Store Screenshot Freshness QA",
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
    if newest_source:
        newest_info = file_info(newest_source)
        lines.extend(
            [
                "",
                "## Newest UI Source",
                f"- `{newest_info['path']}` at `{newest_info['modifiedAt']}`",
            ],
        )
    if upload_stale or qa_stale:
        lines.extend(
            [
                "",
                "## Recapture Required",
                "Re-capture real app screenshots from the current APK before final Google Play upload.",
            ],
        )
        for label, stale in [("Upload screenshots", upload_stale), ("QA screenshots", qa_stale)]:
            if not stale:
                continue
            lines.append("")
            lines.append(f"### {label}")
            for item in stale:
                lines.append(f"- `{item['path']}` at `{item['modifiedAt']}`")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--strict",
        action="store_true",
        help="fail when upload screenshots are older than UI/gameplay source files",
    )
    args = parser.parse_args()

    checks: list[Check] = []
    required = [*UPLOAD_SCREENSHOTS, *QA_SCREENSHOTS]
    missing = [rel(path) for path in required if not path.exists()]
    checks.append(
        Check(
            "Required screenshot files",
            "PASS" if not missing else "FAIL",
            f"{len(required) - len(missing)}/{len(required)} present" if not missing else ", ".join(missing),
        ),
    )

    sources = discover_sources()
    checks.append(
        Check(
            "UI source baseline",
            "PASS" if sources else "FAIL",
            f"{len(sources)} UI/resource source files tracked" if sources else "no source files found",
        ),
    )

    newest_source_mtime = max((path.stat().st_mtime for path in sources), default=0.0)
    upload_stale = stale_since(UPLOAD_SCREENSHOTS, newest_source_mtime)
    qa_stale = stale_since(QA_SCREENSHOTS, newest_source_mtime)

    upload_status = "PASS"
    if upload_stale:
        upload_status = "FAIL" if args.strict else "PASS_WITH_WARNINGS"
    checks.append(
        Check(
            "Upload screenshot freshness",
            upload_status,
            "all upload screenshots are newer than tracked UI source"
            if not upload_stale
            else f"{len(upload_stale)} upload screenshots are older than current UI source",
        ),
    )

    qa_status = "PASS"
    if qa_stale:
        qa_status = "FAIL" if args.strict else "PASS_WITH_WARNINGS"
    checks.append(
        Check(
            "QA screenshot freshness",
            qa_status,
            "all QA screenshots are newer than tracked UI source"
            if not qa_stale
            else f"{len(qa_stale)} QA screenshots are older than current UI source",
        ),
    )

    failures = [check for check in checks if check.status == "FAIL"]
    warnings = [check for check in checks if check.status == "PASS_WITH_WARNINGS"]
    status = "FAIL" if failures else "PASS_WITH_WARNINGS" if warnings else "PASS"
    write_reports(
        strict=args.strict,
        status=status,
        checks=checks,
        sources=sources,
        upload_stale=upload_stale,
        qa_stale=qa_stale,
    )

    if failures:
        print("Store screenshot freshness QA failed")
        for failure in failures:
            print(f"- {failure.name}: {failure.detail}")
        raise SystemExit(1)
    if warnings:
        print(f"Store screenshot freshness QA {status} ({rel(REPORT_MD)}, {rel(REPORT_JSON)})")
        for warning in warnings:
            print(f"- {warning.name}: {warning.detail}")
        return
    print(f"Store screenshot freshness QA PASS ({rel(REPORT_MD)}, {rel(REPORT_JSON)})")


if __name__ == "__main__":
    main()
