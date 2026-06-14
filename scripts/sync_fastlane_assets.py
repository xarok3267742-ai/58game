#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
LOCALE = "ru-RU"
IMAGES = ROOT / f"fastlane/metadata/android/{LOCALE}/images"
PHONE_SCREENSHOTS = IMAGES / "phoneScreenshots"
REPORT_MD = ROOT / "build/reports/fastlane_assets.md"
REPORT_JSON = ROOT / "build/reports/fastlane_assets.json"

ICON_SOURCE = ROOT / "store/play_icon.png"
ICON_TARGET = IMAGES / "icon.png"
FEATURE_SOURCE = ROOT / "store/feature_graphic_concept.png"
FEATURE_TARGET = IMAGES / "featureGraphic.png"
SCREENSHOTS = [
    ("01_onboarding.png", ROOT / "store/screenshots/shawarma_onboarding.png"),
    ("02_menu.png", ROOT / "store/screenshots/shawarma_menu.png"),
    ("03_levels.png", ROOT / "store/screenshots/shawarma_levels.png"),
    ("04_gameplay.png", ROOT / "store/screenshots/shawarma_gameplay.png"),
    ("05_result.png", ROOT / "store/screenshots/shawarma_result.png"),
]


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def image_size(path: Path) -> tuple[int, int]:
    image = Image.open(path)
    return image.size


def save_rgb_png(source: Path, target: Path) -> None:
    image = Image.open(source).convert("RGB")
    image.save(target, "PNG", optimize=True, compress_level=9)


def validate_sources() -> None:
    missing = [path for path in [ICON_SOURCE, FEATURE_SOURCE, *[source for _, source in SCREENSHOTS]] if not path.exists()]
    if missing:
        joined = ", ".join(rel(path) for path in missing)
        raise SystemExit(f"Missing fastlane asset source files: {joined}")
    if image_size(ICON_SOURCE) != (512, 512):
        raise SystemExit(f"{rel(ICON_SOURCE)} must be 512x512")
    if image_size(FEATURE_SOURCE) != (1024, 500):
        raise SystemExit(f"{rel(FEATURE_SOURCE)} must be 1024x500")
    for _, source in SCREENSHOTS:
        if image_size(source) != (1080, 2400):
            raise SystemExit(f"{rel(source)} must be 1080x2400")


def copy_assets() -> list[dict[str, object]]:
    IMAGES.mkdir(parents=True, exist_ok=True)
    if PHONE_SCREENSHOTS.exists():
        shutil.rmtree(PHONE_SCREENSHOTS)
    PHONE_SCREENSHOTS.mkdir(parents=True, exist_ok=True)

    copied: list[dict[str, object]] = []
    assets = [(ICON_SOURCE, ICON_TARGET), (FEATURE_SOURCE, FEATURE_TARGET)]
    for source, target in assets:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied.append(
            {
                "source": rel(source),
                "target": rel(target),
                "bytes": target.stat().st_size,
                "sha256": sha256(target),
                "width": image_size(target)[0],
                "height": image_size(target)[1],
            },
        )
    for name, source in SCREENSHOTS:
        target = PHONE_SCREENSHOTS / name
        target.parent.mkdir(parents=True, exist_ok=True)
        save_rgb_png(source, target)
        copied.append(
            {
                "source": rel(source),
                "target": rel(target),
                "bytes": target.stat().st_size,
                "sha256": sha256(target),
                "width": image_size(target)[0],
                "height": image_size(target)[1],
            },
        )
    return copied


def write_report(copied: list[dict[str, object]]) -> None:
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    report = {
        "generatedAt": generated_at,
        "locale": LOCALE,
        "fastlaneImagesDir": rel(IMAGES),
        "files": copied,
    }
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Fastlane Asset Sync",
        "",
        f"Generated: {generated_at}",
        "",
        "| Source | Target | Size | SHA-256 |",
        "|---|---|---:|---|",
    ]
    for item in copied:
        lines.append(
            f"| `{item['source']}` | `{item['target']}` | {item['width']}x{item['height']} | `{str(item['sha256'])[:16]}...` |",
        )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    validate_sources()
    copied = copy_assets()
    write_report(copied)
    print(f"Fastlane assets synced: {len(copied)} files -> {rel(IMAGES)}")
    print(f"Report: {rel(REPORT_MD)}")


if __name__ == "__main__":
    main()
