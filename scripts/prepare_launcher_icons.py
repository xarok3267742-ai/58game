#!/usr/bin/env python3
from __future__ import annotations

from collections import deque
from pathlib import Path

from PIL import Image, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
DRAWABLE = ROOT / "app/src/main/res/drawable-nodpi"
MIPMAP_SIZES = {
    "mipmap-mdpi": 48,
    "mipmap-hdpi": 72,
    "mipmap-xhdpi": 96,
    "mipmap-xxhdpi": 144,
    "mipmap-xxxhdpi": 192,
}


def luminance(pixel: tuple[int, int, int, int]) -> float:
    r, g, b, _ = pixel
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def remove_dark_corners(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    width, height = rgba.size
    pixels = rgba.load()
    visited = bytearray(width * height)
    corner_mask = Image.new("L", (width, height), 0)
    mask_pixels = corner_mask.load()

    seeds = [
        (0, 0),
        (width - 1, 0),
        (0, height - 1),
        (width - 1, height - 1),
    ]
    queue: deque[tuple[int, int]] = deque()

    def index(x: int, y: int) -> int:
        return y * width + x

    for x, y in seeds:
        if luminance(pixels[x, y]) <= 32:
            visited[index(x, y)] = 1
            queue.append((x, y))

    while queue:
        x, y = queue.popleft()
        mask_pixels[x, y] = 255
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if nx < 0 or nx >= width or ny < 0 or ny >= height:
                continue
            idx = index(nx, ny)
            if visited[idx] or luminance(pixels[nx, ny]) > 32:
                continue
            visited[idx] = 1
            queue.append((nx, ny))

    feathered = corner_mask.filter(ImageFilter.GaussianBlur(radius=0.8))
    alpha = rgba.getchannel("A")
    next_alpha = Image.eval(feathered, lambda value: 255 - value)
    alpha = Image.composite(next_alpha, alpha, feathered)
    rgba.putalpha(alpha)
    return rgba


def foreground_path() -> Path:
    matches = sorted(DRAWABLE.glob("ic_launcher_foreground.*"))
    matches = [path for path in matches if path.suffix.lower() in {".png", ".webp"}]
    if len(matches) != 1:
        raise SystemExit(f"expected one launcher foreground, got {[p.name for p in matches]}")
    return matches[0]


def save_image(image: Image.Image, path: Path) -> None:
    if path.suffix.lower() == ".webp":
        image.save(path, "WEBP", lossless=True, method=6)
    else:
        image.save(path)


def save_mipmap_icons(foreground: Image.Image) -> None:
    for folder, size in MIPMAP_SIZES.items():
        target_dir = ROOT / "app/src/main/res" / folder
        target_dir.mkdir(parents=True, exist_ok=True)
        icon = foreground.resize((size, size), Image.Resampling.LANCZOS)
        icon.save(target_dir / "ic_launcher.png")
        icon.save(target_dir / "ic_launcher_round.png")


def main() -> None:
    target = foreground_path()
    foreground = remove_dark_corners(Image.open(target))
    save_image(foreground, target)
    save_mipmap_icons(foreground)
    print("launcher icons prepared")


if __name__ == "__main__":
    main()
