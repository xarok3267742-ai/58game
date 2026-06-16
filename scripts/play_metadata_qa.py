#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "fastlane/metadata/android/ru-RU"
STORE = ROOT / "store"
FASTLANE_IMAGES = META / "images"
REPORT_MD = ROOT / "build/reports/play_metadata.md"
REPORT_JSON = ROOT / "build/reports/play_metadata.json"
SCREENSHOTS = [
    FASTLANE_IMAGES / "phoneScreenshots/01_onboarding.png",
    FASTLANE_IMAGES / "phoneScreenshots/02_menu.png",
    FASTLANE_IMAGES / "phoneScreenshots/03_levels.png",
    FASTLANE_IMAGES / "phoneScreenshots/04_gameplay.png",
    FASTLANE_IMAGES / "phoneScreenshots/05_result.png",
]
PLAY_ICON = STORE / "play_icon.png"
QA_ONLY_SCREENSHOTS = [
    STORE / "screenshots/shawarma_wrong_order.png",
    STORE / "screenshots/shawarma_endless_result.png",
]
FORBIDDEN = ("TODO", "FIXME", "lorem", "placeholder", "CONCEPT_ONLY")
TEXT_LIMITS = {
    "fastlane/metadata/android/ru-RU/title.txt": 30,
    "fastlane/metadata/android/ru-RU/short_description.txt": 80,
    "fastlane/metadata/android/ru-RU/full_description.txt": 4000,
    "fastlane/metadata/android/ru-RU/changelogs/1.txt": 500,
}
REQUIRED_PRIVACY_TERMS = [
    "Политика конфиденциальности",
    "Шаурма 58",
    "командой проекта «Шаурма 58»",
    "не собирает",
    "не передаёт",
    "удалит приложение",
    "INTERNET",
    "Google Play",
]


@dataclass
class Check:
    name: str
    status: str
    detail: str


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read(path: Path) -> str:
    if not path.exists():
        raise AssertionError(f"missing file: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8").strip()


def check_file_exists(path: Path) -> Check:
    return Check(
        name=f"{rel(path)} exists",
        status="PASS" if path.exists() else "FAIL",
        detail="exists" if path.exists() else "missing",
    )


def check_no_forbidden(path: Path, text: str) -> Check:
    lowered = text.lower()
    hits: list[str] = []
    for token in FORBIDDEN:
        if token.lower() in lowered:
            hits.append(token)
    return Check(
        name=f"{rel(path)} forbidden tokens",
        status="PASS" if not hits else "FAIL",
        detail="none" if not hits else ", ".join(hits),
    )


def check_len(path: Path, text: str, max_len: int) -> Check:
    actual = len(text)
    return Check(
        name=f"{rel(path)} length",
        status="PASS" if actual <= max_len and actual > 0 else "FAIL",
        detail=f"{actual}/{max_len}",
    )


def check_png_size(path: Path, expected: tuple[int, int]) -> Check:
    if not path.exists():
        return Check(name=f"{rel(path)} dimensions", status="FAIL", detail="missing")
    size = Image.open(path).size
    return Check(
        name=f"{rel(path)} dimensions",
        status="PASS" if size == expected else "FAIL",
        detail=f"{size[0]}x{size[1]}, expected {expected[0]}x{expected[1]}",
    )


def check_required_terms(path: Path, text: str, terms: list[str]) -> Check:
    missing = [term for term in terms if term not in text]
    return Check(
        name=f"{rel(path)} required terms",
        status="PASS" if not missing else "FAIL",
        detail=f"{len(terms)} terms present" if not missing else ", ".join(missing),
    )


def write_reports(checks: list[Check], lengths: dict[str, int]) -> None:
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    status = "FAIL" if any(check.status == "FAIL" for check in checks) else "PASS"
    payload = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "metadataDir": META.relative_to(ROOT).as_posix(),
        "textLimits": TEXT_LIMITS,
        "lengths": lengths,
        "requiredPrivacyTerms": REQUIRED_PRIVACY_TERMS,
        "screenshots": [rel(path) for path in SCREENSHOTS],
        "qaOnlyScreenshots": [rel(path) for path in QA_ONLY_SCREENSHOTS],
        "playIcon": "store/play_icon.png",
        "featureGraphic": "store/feature_graphic_concept.png",
        "checks": [asdict(check) for check in checks],
    }
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Play Metadata QA",
        "",
        f"Generated: {payload['generatedAt']}",
        f"Status: `{status}`",
        "",
        "## Lengths",
        "",
        "| File | Length | Limit |",
        "|---|---:|---:|",
    ]
    for relative, limit in TEXT_LIMITS.items():
        lines.append(f"| `{relative}` | {lengths.get(relative, 0)} | {limit} |")
    lines.extend(["", "## Checks", "", "| Check | Status | Detail |", "|---|---|---|"])
    for check in checks:
        lines.append(f"| {check.name} | {check.status} | {check.detail} |")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    checks: list[Check] = []
    text_files = [
        META / "title.txt",
        META / "short_description.txt",
        META / "full_description.txt",
        META / "changelogs/1.txt",
        STORE / "play_listing_ru.md",
        STORE / "privacy_policy.html",
        STORE / "play_console_answers.md",
    ]
    texts: dict[Path, str] = {}
    for path in text_files:
        checks.append(check_file_exists(path))
        if path.exists():
            texts[path] = read(path)

    lengths: dict[str, int] = {}
    for relative, limit in TEXT_LIMITS.items():
        path = ROOT / relative
        text = texts.get(path, "")
        lengths[relative] = len(text)
        checks.append(check_len(path, text, limit))

    for path, text in texts.items():
        checks.append(check_no_forbidden(path, text))

    privacy_path = STORE / "privacy_policy.html"
    checks.append(check_required_terms(privacy_path, texts.get(privacy_path, ""), REQUIRED_PRIVACY_TERMS))

    for screenshot in SCREENSHOTS + QA_ONLY_SCREENSHOTS:
        checks.append(check_png_size(screenshot, (1080, 2400)))

    checks.append(check_png_size(PLAY_ICON, (512, 512)))
    checks.append(check_png_size(STORE / "feature_graphic_concept.png", (1024, 500)))
    write_reports(checks, lengths)

    for relative, limit in TEXT_LIMITS.items():
        print(f"{Path(relative).name} length: {lengths.get(relative, 0)}/{limit}")
    failures = [check for check in checks if check.status == "FAIL"]
    if failures:
        print("Play metadata QA failed")
        for failure in failures:
            print(f"- {failure.name}: {failure.detail}")
        raise SystemExit(1)
    print(f"Play metadata QA PASS ({rel(REPORT_MD)}, {rel(REPORT_JSON)})")


if __name__ == "__main__":
    main()
