#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DRAWABLE = ROOT / "app/src/main/res/drawable-nodpi"


def has_alpha(image: Image.Image) -> bool:
    return image.mode in ("RGBA", "LA") or "transparency" in image.info


def convert_png_to_webp(path: Path) -> None:
    image = Image.open(path)
    target = path.with_suffix(".webp")
    if has_alpha(image):
        image.convert("RGBA").save(target, "WEBP", lossless=True, method=6)
    else:
        image.convert("RGB").save(target, "WEBP", quality=92, method=6)
    path.unlink()
    print(f"{path.name} -> {target.name} ({target.stat().st_size} bytes)")


def main() -> None:
    for path in sorted(DRAWABLE.glob("*.png")):
        convert_png_to_webp(path)


if __name__ == "__main__":
    main()
