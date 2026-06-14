#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import deque
from pathlib import Path

from PIL import Image, ImageFilter


def is_background_candidate(pixel: tuple[int, int, int, int]) -> bool:
    r, g, b, a = pixel
    if a < 8:
        return True
    max_c = max(r, g, b)
    min_c = min(r, g, b)
    saturation = 0 if max_c == 0 else (max_c - min_c) / max_c
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return luminance >= 202 and saturation <= 0.32


def edge_points(width: int, height: int) -> list[tuple[int, int]]:
    points: list[tuple[int, int]] = []
    for x in range(width):
        points.append((x, 0))
        points.append((x, height - 1))
    for y in range(1, height - 1):
        points.append((0, y))
        points.append((width - 1, y))
    return points


def remove_connected_background(path: Path) -> None:
    image = Image.open(path).convert("RGBA")
    width, height = image.size
    pixels = image.load()
    visited = bytearray(width * height)
    background = Image.new("L", (width, height), 0)
    bg_pixels = background.load()
    queue: deque[tuple[int, int]] = deque()

    def index(x: int, y: int) -> int:
        return y * width + x

    for x, y in edge_points(width, height):
        idx = index(x, y)
        if not visited[idx] and is_background_candidate(pixels[x, y]):
            visited[idx] = 1
            queue.append((x, y))

    while queue:
        x, y = queue.popleft()
        bg_pixels[x, y] = 255
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if nx < 0 or nx >= width or ny < 0 or ny >= height:
                continue
            idx = index(nx, ny)
            if visited[idx] or not is_background_candidate(pixels[nx, ny]):
                continue
            visited[idx] = 1
            queue.append((nx, ny))

    feathered = background.filter(ImageFilter.GaussianBlur(radius=1.2))
    alpha = Image.eval(feathered, lambda value: 255 - value)
    image.putalpha(alpha)
    if path.suffix.lower() == ".webp":
        image.save(path, "WEBP", lossless=True, method=6)
    else:
        image.save(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args()
    for file_path in args.files:
        remove_connected_background(file_path)
        print(f"processed {file_path}")


if __name__ == "__main__":
    main()
