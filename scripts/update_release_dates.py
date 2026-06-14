#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_MD = ROOT / "build/reports/release_dates.md"
REPORT_JSON = ROOT / "build/reports/release_dates.json"
DATED_DOCS = {
    "store/play_upload_packet.md": (r"^Date: .+$", "Date: {label}."),
    "docs/completion_audit.md": (r"^Date: .+$", "Date: {label}."),
    "docs/release_candidate_package.md": (r"^Date: .+$", "Date: {label}."),
    "docs/fastlane_upload.md": (r"^Date: .+$", "Date: {label}."),
    "docs/deobfuscation_notes.md": (r"^Date: .+$", "Date: {label}."),
    "docs/google_play_checklist.md": (r"^- Checked on .+$", "- Checked on {label}."),
}


@dataclass
class Update:
    path: str
    status: str
    detail: str


def today_label(today: date) -> str:
    return f"{today.strftime('%B')} {today.day}, {today.year}"


def update_file(relative: str, pattern: str, replacement_template: str, label: str) -> Update:
    path = ROOT / relative
    if not path.exists():
        return Update(relative, "FAIL", "file is missing")
    text = path.read_text(encoding="utf-8")
    replacement = replacement_template.format(label=label)
    new_text, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE)
    if count != 1:
        return Update(relative, "FAIL", f"date marker not found for pattern {pattern!r}")
    if new_text == text:
        return Update(relative, "PASS", f"already {replacement!r}")
    path.write_text(new_text, encoding="utf-8")
    return Update(relative, "PASS", f"updated to {replacement!r}")


def write_report(updates: list[Update]) -> None:
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "updates": [update.__dict__ for update in updates],
    }
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Release Date Update",
        "",
        f"Generated: {payload['generatedAt']}",
        "",
        "| File | Status | Detail |",
        "|---|---|---|",
    ]
    for update in updates:
        lines.append(f"| `{update.path}` | {update.status} | {update.detail} |")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    label = today_label(date.today())
    updates = [
        update_file(relative, pattern, template, label)
        for relative, (pattern, template) in DATED_DOCS.items()
    ]
    write_report(updates)
    failures = [update for update in updates if update.status == "FAIL"]
    if failures:
        print("Release date update failed")
        for failure in failures:
            print(f"- {failure.path}: {failure.detail}")
        raise SystemExit(1)
    print(f"Release date update PASS ({label})")


if __name__ == "__main__":
    main()
