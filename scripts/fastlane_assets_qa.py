#!/usr/bin/env python3
from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
LOCALE = "ru-RU"
IMAGES = ROOT / f"fastlane/metadata/android/{LOCALE}/images"
PHONE_SCREENSHOTS = IMAGES / "phoneScreenshots"
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
QA_ONLY_NAMES = {"wrong_order", "endless"}


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_image(
    path: Path,
    expected_size: tuple[int, int],
    errors: list[str],
    *,
    expected_mode: str | None = None,
    max_bytes: int | None = None,
) -> None:
    if not path.exists():
        errors.append(f"missing image: {rel(path)}")
        return
    try:
        image = Image.open(path)
        if image.size != expected_size:
            errors.append(f"{rel(path)} expected {expected_size}, got {image.size}")
        if expected_mode and image.mode != expected_mode:
            errors.append(f"{rel(path)} expected mode {expected_mode}, got {image.mode}")
        if max_bytes and path.stat().st_size > max_bytes:
            errors.append(f"{rel(path)} expected <= {max_bytes} bytes, got {path.stat().st_size}")
    except OSError as exc:
        errors.append(f"{rel(path)} is not readable as an image: {exc}")


def check_same_file(source: Path, target: Path, expected_size: tuple[int, int], errors: list[str]) -> None:
    check_image(source, expected_size, errors)
    check_image(target, expected_size, errors)
    if source.exists() and target.exists() and sha256(source) != sha256(target):
        errors.append(f"{rel(target)} does not match source {rel(source)}")


def check_same_rgb_pixels(source: Path, target: Path, expected_size: tuple[int, int], errors: list[str]) -> None:
    check_image(source, expected_size, errors)
    check_image(target, expected_size, errors, expected_mode="RGB")
    if not source.exists() or not target.exists():
        return
    source_rgb = Image.open(source).convert("RGB")
    target_rgb = Image.open(target).convert("RGB")
    if source_rgb.tobytes() != target_rgb.tobytes():
        errors.append(f"{rel(target)} RGB pixels do not match source {rel(source)}")


def main() -> None:
    errors: list[str] = []
    check_same_file(ICON_SOURCE, ICON_TARGET, (512, 512), errors)
    check_image(ICON_TARGET, (512, 512), errors, expected_mode="RGBA", max_bytes=1024 * 1024)
    check_same_file(FEATURE_SOURCE, FEATURE_TARGET, (1024, 500), errors)

    expected_names = {name for name, _ in SCREENSHOTS}
    if not PHONE_SCREENSHOTS.exists():
        errors.append(f"missing screenshots directory: {rel(PHONE_SCREENSHOTS)}")
    else:
        actual_names = {path.name for path in PHONE_SCREENSHOTS.iterdir() if path.is_file()}
        if actual_names != expected_names:
            errors.append(
                f"{rel(PHONE_SCREENSHOTS)} must contain exactly {sorted(expected_names)}, got {sorted(actual_names)}",
            )
        for actual_name in actual_names:
            lowered = actual_name.lower()
            if any(token in lowered for token in QA_ONLY_NAMES):
                errors.append(f"QA-only screenshot leaked into upload set: {rel(PHONE_SCREENSHOTS / actual_name)}")

    for name, source in SCREENSHOTS:
        check_same_rgb_pixels(source, PHONE_SCREENSHOTS / name, (1080, 2400), errors)

    if errors:
        print("Fastlane assets QA failed")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print(f"Fastlane assets QA PASS ({rel(IMAGES)})")


if __name__ == "__main__":
    main()
