#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DRAWABLE = ROOT / "app/src/main/res/drawable-nodpi"
SCREENSHOTS = ROOT / "store/screenshots"
REPORT_MD = ROOT / "build/reports/asset.md"
REPORT_JSON = ROOT / "build/reports/asset.json"
MIPMAP_SIZES = {
    "mipmap-mdpi": 48,
    "mipmap-hdpi": 72,
    "mipmap-xhdpi": 96,
    "mipmap-xxhdpi": 144,
    "mipmap-xxxhdpi": 192,
}


@dataclass
class Check:
    name: str
    status: str
    detail: str
    path: str
    width: int | None = None
    height: int | None = None
    mode: str = ""
    alpha: tuple[int, int] | None = None
    bytes: int = 0


def alpha_range(image: Image.Image) -> tuple[int, int] | None:
    if image.mode not in ("RGBA", "LA") and "transparency" not in image.info:
        return None
    return image.convert("RGBA").getchannel("A").getextrema()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def inspect_image(path: Path, expected_size: tuple[int, int] | None = None, require_alpha: bool = False) -> Check:
    name = rel(path)
    if not path.exists():
        return Check(name=name, status="FAIL", detail="missing", path=name)
    try:
        image = Image.open(path)
        size = image.size
        alpha = alpha_range(image)
        detail_parts: list[str] = []
        if expected_size and size != expected_size:
            detail_parts.append(f"expected {expected_size[0]}x{expected_size[1]}, got {size[0]}x{size[1]}")
        if require_alpha and (alpha is None or alpha[0] >= 255):
            detail_parts.append(f"expected transparent alpha, got {alpha}")
        status = "FAIL" if detail_parts else "PASS"
        detail = "; ".join(detail_parts) if detail_parts else (
            f"{size[0]}x{size[1]} mode={image.mode} alpha={alpha} bytes={path.stat().st_size}"
        )
        return Check(
            name=name,
            status=status,
            detail=detail,
            path=name,
            width=size[0],
            height=size[1],
            mode=image.mode,
            alpha=alpha,
            bytes=path.stat().st_size,
        )
    except Exception as error:
        return Check(name=name, status="FAIL", detail=str(error), path=name)


def drawable_image(stem: str) -> Path:
    matches = sorted(DRAWABLE.glob(f"{stem}.*"))
    matches = [path for path in matches if path.suffix.lower() in {".png", ".webp", ".jpg", ".jpeg"}]
    if len(matches) != 1:
        raise AssertionError(f"expected exactly one image for {stem}, got {[p.name for p in matches]}")
    return matches[0]


def add_drawable_check(checks: list[Check], stem: str, expected_size: tuple[int, int], require_alpha: bool = False) -> None:
    try:
        checks.append(inspect_image(drawable_image(stem), expected_size, require_alpha))
    except AssertionError as error:
        checks.append(Check(name=f"drawable {stem}", status="FAIL", detail=str(error), path=f"{DRAWABLE.relative_to(ROOT).as_posix()}/{stem}.*"))


def write_reports(checks: list[Check]) -> None:
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    status = "FAIL" if any(check.status == "FAIL" for check in checks) else "PASS"
    payload = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "runtimeDrawableDir": DRAWABLE.relative_to(ROOT).as_posix(),
        "screenshotsDir": SCREENSHOTS.relative_to(ROOT).as_posix(),
        "checks": [asdict(check) for check in checks],
        "summary": {
            "total": len(checks),
            "runtimeDrawableCount": len([check for check in checks if check.path.startswith("app/src/main/res/drawable-nodpi/")]),
            "launcherIconCount": len([check for check in checks if "/mipmap-" in check.path]),
            "screenshotCount": len([check for check in checks if check.path.startswith("store/screenshots/")]),
            "transparentAlphaRequiredCount": len([check for check in checks if check.alpha is not None and check.alpha[0] == 0]),
        },
    }
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Asset QA",
        "",
        f"Generated: {payload['generatedAt']}",
        f"Status: `{status}`",
        "",
        "| Asset | Status | Detail |",
        "|---|---|---|",
    ]
    for check in checks:
        lines.append(f"| `{check.path}` | {check.status} | {check.detail} |")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    checks: list[Check] = []
    add_drawable_check(checks, "ic_launcher_foreground", (768, 768), require_alpha=True)
    for folder, size in MIPMAP_SIZES.items():
        checks.append(inspect_image(ROOT / "app/src/main/res" / folder / "ic_launcher.png", (size, size), require_alpha=True))
        checks.append(inspect_image(ROOT / "app/src/main/res" / folder / "ic_launcher_round.png", (size, size), require_alpha=True))
    add_drawable_check(checks, "bg_counter", (1200, 800))
    add_drawable_check(checks, "bg_route_map", (720, 1600))
    add_drawable_check(checks, "bg_prep_station", (720, 1600))
    add_drawable_check(checks, "bg_receipt_counter", (720, 1600))
    add_drawable_check(checks, "art_onboarding_prep", (768, 768))

    for path in sorted(DRAWABLE.glob("ingredient_*.*")):
        if path.suffix.lower() not in {".png", ".webp"}:
            continue
        checks.append(inspect_image(path, (512, 512), require_alpha=True))

    for path in sorted(DRAWABLE.glob("customer_*.*")):
        if path.suffix.lower() not in {".png", ".webp"}:
            continue
        checks.append(inspect_image(path, (512, 512)))

    for path in sorted(SCREENSHOTS.glob("shawarma_*.png")):
        checks.append(inspect_image(path, (1080, 2400)))

    write_reports(checks)
    for check in checks:
        print(f"{check.path} {check.detail}")
    failures = [check for check in checks if check.status == "FAIL"]
    if failures:
        raise SystemExit(1)
    print(f"Asset QA PASS ({rel(REPORT_MD)}, {rel(REPORT_JSON)})")


if __name__ == "__main__":
    main()
