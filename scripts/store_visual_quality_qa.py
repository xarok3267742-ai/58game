#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

from PIL import Image, ImageStat


ROOT = Path(__file__).resolve().parents[1]
REPORT_MD = ROOT / "build/reports/store_visual_quality.md"
REPORT_JSON = ROOT / "build/reports/store_visual_quality.json"

SCREENSHOT_SIZE = (1080, 2400)
ICON_SIZE = (512, 512)
FEATURE_SIZE = (1024, 500)
MIN_SCREENSHOT_BYTES = 120_000
MIN_ICON_BYTES = 80_000
MIN_FEATURE_BYTES = 120_000
MIN_GRAY_STDDEV = 20.0
MIN_THUMB_COLORS = 450
MIN_UPLOAD_HASH_DISTANCE = 350

RESAMPLING = getattr(getattr(Image, "Resampling", Image), "LANCZOS")

UPLOAD_SCREENSHOTS = [
    ("Onboarding", ROOT / "fastlane/metadata/android/ru-RU/images/phoneScreenshots/01_onboarding.png"),
    ("Menu", ROOT / "fastlane/metadata/android/ru-RU/images/phoneScreenshots/02_menu.png"),
    ("Levels", ROOT / "fastlane/metadata/android/ru-RU/images/phoneScreenshots/03_levels.png"),
    ("Gameplay", ROOT / "fastlane/metadata/android/ru-RU/images/phoneScreenshots/04_gameplay.png"),
    ("Result", ROOT / "fastlane/metadata/android/ru-RU/images/phoneScreenshots/05_result.png"),
]
QA_SCREENSHOTS = [
    ("Wrong order", ROOT / "store/screenshots/shawarma_wrong_order.png"),
    ("Endless result", ROOT / "store/screenshots/shawarma_endless_result.png"),
]
PLAY_ICON = ("Play app icon", ROOT / "store/play_icon.png")
FEATURE_GRAPHIC = ("Feature graphic", ROOT / "store/feature_graphic_concept.png")


@dataclass
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


def average_hash(gray: Image.Image, size: tuple[int, int]) -> str:
    resized = gray.resize(size, RESAMPLING)
    values = list(resized.getdata())
    average = sum(values) / len(values)
    return "".join("1" if value >= average else "0" for value in values)


def hamming(left: str, right: str) -> int:
    return sum(1 for a, b in zip(left, right) if a != b)


def image_metrics(name: str, path: Path, hash_size: tuple[int, int]) -> dict[str, object]:
    if not path.exists():
        raise FileNotFoundError(rel(path))
    with Image.open(path) as source:
        rgb = source.convert("RGB")
        gray = source.convert("L")
        thumb = rgb.resize((64, 128), RESAMPLING)
        colors = thumb.getcolors(maxcolors=(64 * 128) + 1)
        return {
            "name": name,
            "path": rel(path),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "width": source.size[0],
            "height": source.size[1],
            "mode": source.mode,
            "grayStddev": round(float(ImageStat.Stat(gray).stddev[0]), 2),
            "thumbnailColors": len(colors) if colors is not None else 64 * 128,
            "averageHash": average_hash(gray, hash_size),
        }


def validate_image(
    metrics: dict[str, object],
    expected_size: tuple[int, int],
    min_bytes: int,
) -> list[Check]:
    name = str(metrics["name"])
    path = str(metrics["path"])
    checks: list[Check] = []
    actual_size = (metrics["width"], metrics["height"])
    size_status = "PASS" if actual_size == expected_size else "FAIL"
    checks.append(
        Check(
            name=f"{name} dimensions",
            status=size_status,
            detail=f"{path}: {actual_size[0]}x{actual_size[1]} expected {expected_size[0]}x{expected_size[1]}",
        ),
    )

    byte_count = int(metrics["bytes"])
    byte_status = "PASS" if byte_count >= min_bytes else "FAIL"
    checks.append(
        Check(
            name=f"{name} file size",
            status=byte_status,
            detail=f"{path}: {byte_count} bytes, minimum {min_bytes}",
        ),
    )

    stddev = float(metrics["grayStddev"])
    contrast_status = "PASS" if stddev >= MIN_GRAY_STDDEV else "FAIL"
    checks.append(
        Check(
            name=f"{name} contrast",
            status=contrast_status,
            detail=f"{path}: grayscale stddev {stddev:.2f}, minimum {MIN_GRAY_STDDEV:.2f}",
        ),
    )

    colors = int(metrics["thumbnailColors"])
    color_status = "PASS" if colors >= MIN_THUMB_COLORS else "FAIL"
    checks.append(
        Check(
            name=f"{name} color variety",
            status=color_status,
            detail=f"{path}: {colors} sampled colors, minimum {MIN_THUMB_COLORS}",
        ),
    )
    return checks


def upload_uniqueness(upload_metrics: list[dict[str, object]]) -> tuple[Check, list[dict[str, object]]]:
    distances: list[dict[str, object]] = []
    for left, right in combinations(upload_metrics, 2):
        distance = hamming(str(left["averageHash"]), str(right["averageHash"]))
        distances.append(
            {
                "left": left["path"],
                "right": right["path"],
                "distance": distance,
            },
        )
    minimum = min(item["distance"] for item in distances) if distances else 0
    status = "PASS" if minimum >= MIN_UPLOAD_HASH_DISTANCE else "FAIL"
    detail = f"minimum pair distance {minimum}, threshold {MIN_UPLOAD_HASH_DISTANCE}"
    return Check("Upload screenshot uniqueness", status, detail), distances


def write_reports(
    checks: list[Check],
    images: list[dict[str, object]],
    pair_distances: list[dict[str, object]],
) -> None:
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "thresholds": {
            "screenshotSize": SCREENSHOT_SIZE,
            "iconSize": ICON_SIZE,
            "featureSize": FEATURE_SIZE,
            "minScreenshotBytes": MIN_SCREENSHOT_BYTES,
            "minIconBytes": MIN_ICON_BYTES,
            "minFeatureBytes": MIN_FEATURE_BYTES,
            "minGrayStddev": MIN_GRAY_STDDEV,
            "minThumbnailColors": MIN_THUMB_COLORS,
            "minUploadHashDistance": MIN_UPLOAD_HASH_DISTANCE,
        },
        "checks": [check.__dict__ for check in checks],
        "images": images,
        "pairDistances": pair_distances,
    }
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Store Visual Quality QA",
        "",
        f"Generated: {report['generatedAt']}",
        "",
        "## Checks",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for check in checks:
        lines.append(f"| {check.name} | {check.status} | {check.detail} |")
    lines.extend(
        [
            "",
            "## Image Metrics",
            "| Image | Path | Size | Bytes | Gray Stddev | Sampled Colors | SHA-256 |",
            "|---|---|---:|---:|---:|---:|---|",
        ],
    )
    for item in images:
        lines.append(
            "| {name} | `{path}` | {width}x{height} | {bytes} | {grayStddev} | {thumbnailColors} | `{sha256}` |".format(
                **item,
            ),
        )
    lines.extend(
        [
            "",
            "## Upload Screenshot Hash Distances",
            "| Left | Right | Distance |",
            "|---|---|---:|",
        ],
    )
    for item in pair_distances:
        lines.append(f"| `{item['left']}` | `{item['right']}` | {item['distance']} |")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    checks: list[Check] = []
    upload_metrics = [
        image_metrics(name, path, hash_size=(32, 64))
        for name, path in UPLOAD_SCREENSHOTS
    ]
    qa_metrics = [
        image_metrics(name, path, hash_size=(32, 64))
        for name, path in QA_SCREENSHOTS
    ]
    icon_metrics = [image_metrics(PLAY_ICON[0], PLAY_ICON[1], hash_size=(32, 32))]
    feature_metrics = [image_metrics(FEATURE_GRAPHIC[0], FEATURE_GRAPHIC[1], hash_size=(32, 16))]

    for metrics in upload_metrics:
        checks.extend(validate_image(metrics, SCREENSHOT_SIZE, MIN_SCREENSHOT_BYTES))
    for metrics in qa_metrics:
        checks.extend(validate_image(metrics, SCREENSHOT_SIZE, MIN_SCREENSHOT_BYTES))
    checks.extend(validate_image(icon_metrics[0], ICON_SIZE, MIN_ICON_BYTES))
    checks.extend(validate_image(feature_metrics[0], FEATURE_SIZE, MIN_FEATURE_BYTES))

    uniqueness_check, pair_distances = upload_uniqueness(upload_metrics)
    checks.append(uniqueness_check)

    images = [*upload_metrics, *qa_metrics, *icon_metrics, *feature_metrics]
    write_reports(checks, images, pair_distances)

    failures = [check for check in checks if check.status == "FAIL"]
    if failures:
        print("Store visual quality QA failed")
        for failure in failures:
            print(f"- {failure.name}: {failure.detail}")
        raise SystemExit(1)

    print(f"Store visual quality QA PASS ({rel(REPORT_MD)}, {rel(REPORT_JSON)})")


if __name__ == "__main__":
    main()
