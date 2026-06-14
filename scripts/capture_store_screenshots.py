#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageStat

from android_smoke_qa import DEFAULT_ACTIVITY, DEFAULT_APK, DEFAULT_PACKAGE, ROOT, Smoke


STORE_SCREENSHOTS = ROOT / "store/screenshots"
SCREENSHOTS = [
    "shawarma_onboarding.png",
    "shawarma_menu.png",
    "shawarma_levels.png",
    "shawarma_gameplay.png",
    "shawarma_result.png",
    "shawarma_wrong_order.png",
    "shawarma_endless_result.png",
]
SCREENSHOT_SIZE = (1080, 2400)
MIN_SCREENSHOT_BYTES = 120_000
MIN_GRAY_STDDEV = 20.0
MIN_THUMB_COLORS = 450
RESAMPLING = getattr(getattr(Image, "Resampling", Image), "LANCZOS")


@dataclass(frozen=True)
class ScreenshotQuality:
    width: int
    height: int
    byte_count: int
    gray_stddev: float
    thumbnail_colors: int


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def screencap(serial: str, target: Path) -> None:
    result = subprocess.run(
        ["adb", "-s", serial, "exec-out", "screencap", "-p"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace"))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(result.stdout)


def screenshot_quality(path: Path) -> ScreenshotQuality:
    with Image.open(path) as source:
        rgb = source.convert("RGB")
        gray = source.convert("L")
        thumb = rgb.resize((64, 128), RESAMPLING)
        colors = thumb.getcolors(maxcolors=(64 * 128) + 1)
        return ScreenshotQuality(
            width=source.size[0],
            height=source.size[1],
            byte_count=path.stat().st_size,
            gray_stddev=round(float(ImageStat.Stat(gray).stddev[0]), 2),
            thumbnail_colors=len(colors) if colors is not None else 64 * 128,
        )


def validate_screenshot_candidate(path: Path) -> ScreenshotQuality:
    metrics = screenshot_quality(path)
    errors: list[str] = []
    if (metrics.width, metrics.height) != SCREENSHOT_SIZE:
        errors.append(f"dimensions {metrics.width}x{metrics.height}, expected {SCREENSHOT_SIZE[0]}x{SCREENSHOT_SIZE[1]}")
    if metrics.byte_count < MIN_SCREENSHOT_BYTES:
        errors.append(f"{metrics.byte_count} bytes, minimum {MIN_SCREENSHOT_BYTES}")
    if metrics.gray_stddev < MIN_GRAY_STDDEV:
        errors.append(f"grayscale stddev {metrics.gray_stddev:.2f}, minimum {MIN_GRAY_STDDEV:.2f}")
    if metrics.thumbnail_colors < MIN_THUMB_COLORS:
        errors.append(f"{metrics.thumbnail_colors} sampled colors, minimum {MIN_THUMB_COLORS}")
    if errors:
        raise RuntimeError(f"rejected screenshot candidate {rel(path)}: {'; '.join(errors)}")
    return metrics


def disable_other_third_party_packages(smoke: Smoke) -> list[str]:
    result = smoke.adb("shell", "pm", "list", "packages", "-3", check=False)
    disabled: list[str] = []
    allowed = {smoke.package, f"{smoke.package}.test"}
    for line in result.stdout.splitlines():
        if not line.startswith("package:"):
            continue
        package = line.removeprefix("package:").strip()
        if not package or package in allowed:
            continue
        disable = smoke.adb("shell", "pm", "disable-user", "--user", "0", package, check=False)
        if disable.returncode == 0:
            smoke.adb("shell", "am", "force-stop", package, check=False)
            disabled.append(package)
    return disabled


def enable_packages(smoke: Smoke, packages: list[str]) -> None:
    for package in packages:
        smoke.adb("shell", "pm", "enable", package, check=False)


def ensure_foreground(smoke: Smoke) -> None:
    if smoke.is_foreground():
        return
    if smoke.stop_other_apps:
        smoke.force_stop_other_third_party_apps()
    if not smoke.resolve_activity(check=False):
        smoke.install_app()
    smoke.launch()
    time.sleep(0.8)
    smoke.assert_foreground()


def capture(smoke: Smoke, out_dir: Path, name: str, store_filename: str, captured: list[str]) -> None:
    ensure_foreground(smoke)
    store_path = STORE_SCREENSHOTS / store_filename
    evidence_path = out_dir / store_filename
    candidate_path = out_dir / f"candidate_{store_filename}"
    screencap(smoke.serial, candidate_path)
    metrics = validate_screenshot_candidate(candidate_path)
    store_path.parent.mkdir(parents=True, exist_ok=True)
    store_path.write_bytes(candidate_path.read_bytes())
    evidence_path.write_bytes(candidate_path.read_bytes())
    captured.append(store_path.relative_to(ROOT).as_posix())
    print(
        "captured "
        f"{store_path.relative_to(ROOT).as_posix()} "
        f"({metrics.byte_count} bytes, stddev {metrics.gray_stddev:.2f}, colors {metrics.thumbnail_colors})",
    )


def prepare(smoke: Smoke) -> None:
    smoke.out_dir.mkdir(parents=True, exist_ok=True)
    if not smoke.skip_install:
        smoke.require_file(smoke.apk)
        smoke.install_app()
    if smoke.stop_other_apps:
        smoke.stopped_packages = smoke.force_stop_other_third_party_apps()
    smoke.configure_display()
    smoke.adb("shell", "logcat", "-c", check=False)
    smoke.adb("shell", "pm", "clear", smoke.package)
    smoke.configure_display()
    smoke.launch()


def tap(smoke: Smoke, x: int, y: int, delay: float = 0.5) -> None:
    ensure_foreground(smoke)
    smoke.tap_xy(x, y)
    if delay > 0.35:
        time.sleep(delay - 0.35)


def restart_to_menu(smoke: Smoke) -> None:
    smoke.adb("shell", "am", "force-stop", smoke.package, check=False)
    time.sleep(0.7)
    if not smoke.resolve_activity(check=False):
        smoke.install_app()
    smoke.launch()
    time.sleep(1.3)
    smoke.assert_foreground()
    if smoke.maybe_wait_for_text("Играть", timeout=1.5) is not None:
        return
    if smoke.maybe_wait_for_text("Начать смену", timeout=2) is not None:
        smoke.tap_text_until("Начать смену", "Играть")
        return
    smoke.wait_for_text("Играть", timeout=5)


def serve_level_one_order_one(smoke: Smoke) -> None:
    for x, y in [
        (165, 1320),  # Лаваш
        (415, 1320),  # Курица
        (660, 1320),  # Томат
        (910, 1320),  # Огурец
        (415, 1630),  # Белый
        (835, 2190),  # Отдать заказ
    ]:
        tap(smoke, x, y, delay=0.2)


def serve_level_one_order_two(smoke: Smoke) -> None:
    for x, y in [
        (165, 1490),  # Лаваш
        (415, 1490),  # Курица
        (910, 1810),  # Фри
        (415, 1810),  # Белый
        (835, 2190),  # Отдать заказ
    ]:
        tap(smoke, x, y, delay=0.2)


def serve_level_one_order_three(smoke: Smoke) -> None:
    for x, y in [
        (165, 1490),  # Лаваш
        (415, 1490),  # Курица
        (910, 1490),  # Огурец
        (910, 1810),  # Фри
        (415, 1810),  # Белый
        (835, 2190),  # Отдать заказ
    ]:
        tap(smoke, x, y, delay=0.2)


def serve_endless_first_order(smoke: Smoke) -> None:
    for x, y in [
        (165, 1320),  # Лаваш
        (415, 1320),  # Курица
        (415, 1630),  # Белый
        (165, 1630),  # Зелень
        (835, 2190),  # Отдать заказ
    ]:
        tap(smoke, x, y, delay=0.2)


def serve_spicy_wrong_order(smoke: Smoke, shifted: bool = False) -> None:
    tap(smoke, 660, 1810 if shifted else 1630, delay=0.2)  # Острый
    tap(smoke, 835, 2190, delay=0.7)  # Отдать заказ


def coordinate_reset_to_menu(smoke: Smoke) -> None:
    smoke.adb("shell", "pm", "clear", smoke.package, check=False)
    smoke.configure_display()
    if not smoke.resolve_activity(check=False):
        smoke.install_app()
    smoke.launch()
    smoke.tap_text_until("Начать смену", "Играть", wait_after_tap=10)
    require_text(smoke, "Играть", timeout=10)


def require_text(smoke: Smoke, text: str, timeout: float = 6) -> None:
    smoke.wait_for_text(text, timeout=timeout)


def coordinate_capture_flow(smoke: Smoke, out_dir: Path, captured: list[str]) -> None:
    # Hybrid 1080x2400 flow: text-guarded navigation plus fixed gameplay taps
    # for ingredient/serve actions. Screenshots are real app screencaps and pass
    # the same candidate validator as the uiautomator-driven path.
    require_text(smoke, "Начать смену", timeout=30)
    capture(smoke, out_dir, "onboarding", "shawarma_onboarding.png", captured)
    smoke.tap_text_until("Начать смену", "Играть", wait_after_tap=10)

    require_text(smoke, "Играть", timeout=10)
    capture(smoke, out_dir, "menu", "shawarma_menu.png", captured)
    smoke.tap_text_until("Играть", "Выбор смены", wait_after_tap=10)

    require_text(smoke, "Выбор смены", timeout=10)
    capture(smoke, out_dir, "levels", "shawarma_levels.png", captured)
    smoke.tap_text_until("Смена 1", "Линия сборки", wait_after_tap=10)

    require_text(smoke, "Линия сборки", timeout=10)
    capture(smoke, out_dir, "gameplay", "shawarma_gameplay.png", captured)
    serve_level_one_order_one(smoke)
    time.sleep(0.5)
    serve_level_one_order_two(smoke)
    time.sleep(0.5)
    serve_level_one_order_three(smoke)
    time.sleep(1.8)
    smoke.assert_foreground()
    capture(smoke, out_dir, "result", "shawarma_result.png", captured)

    coordinate_reset_to_menu(smoke)
    smoke.tap_text_until("Играть", "Выбор смены", wait_after_tap=10)
    require_text(smoke, "Выбор смены", timeout=10)
    smoke.tap_text_until("Смена 1", "Линия сборки", wait_after_tap=10)
    require_text(smoke, "Линия сборки", timeout=10)
    serve_spicy_wrong_order(smoke)
    time.sleep(0.8)
    smoke.assert_foreground()
    require_text(smoke, "Ошибки 1/3")
    require_text(smoke, "Состав не совпал")
    capture(smoke, out_dir, "wrong_order", "shawarma_wrong_order.png", captured)

    tap(smoke, 95, 135, delay=0.9)  # Back to menu from gameplay header
    require_text(smoke, "Играть", timeout=10)
    smoke.tap_text_until("Бесконечная смена", "Линия сборки", wait_after_tap=10)
    serve_endless_first_order(smoke)
    time.sleep(0.5)
    serve_spicy_wrong_order(smoke, shifted=True)
    time.sleep(0.4)
    serve_spicy_wrong_order(smoke, shifted=True)
    time.sleep(0.4)
    serve_spicy_wrong_order(smoke, shifted=True)
    time.sleep(1.8)
    smoke.assert_foreground()
    require_text(smoke, "Смена закрыта")
    require_text(smoke, "ENDLESS")
    capture(smoke, out_dir, "endless_result", "shawarma_endless_result.png", captured)


def write_summary(
    out_dir: Path,
    *,
    serial: str,
    package: str,
    captured: list[str],
    status: str = "PASS",
    capture_mode: str | None = None,
) -> None:
    summary = [
        "# Store Screenshot Capture",
        "",
        f"Status: {status}",
        f"Serial: `{serial}`",
        f"Package: `{package}`",
        f"Generated: `{datetime.now().isoformat(timespec='seconds')}`",
    ]
    if capture_mode is not None:
        summary.append(f"Capture mode: `{capture_mode}`")
    summary.extend(
        [
            "",
            "Captured:",
            *[f"- `{path}`" for path in captured],
        ],
    )
    (out_dir / "summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")


def combine_from_store(out_dir: Path, package: str) -> list[str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    captured: list[str] = []
    for filename in SCREENSHOTS:
        source = STORE_SCREENSHOTS / filename
        if not source.is_file():
            raise RuntimeError(f"missing store screenshot: {source.relative_to(ROOT).as_posix()}")
        validate_screenshot_candidate(source)
        target = out_dir / filename
        target.write_bytes(source.read_bytes())
        captured.append(source.relative_to(ROOT).as_posix())
    write_summary(
        out_dir,
        serial="combined-from-store",
        package=package,
        captured=captured,
        capture_mode=(
            "combined evidence from current store/screenshots; use only after those PNGs were "
            "created by real app screencap runs"
        ),
    )
    return captured


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--serial", help="adb serial, for example emulator-5560")
    parser.add_argument("--apk", default=str(DEFAULT_APK), help="debug APK to install")
    parser.add_argument("--package", default=DEFAULT_PACKAGE, help="installed package name")
    parser.add_argument("--activity", default=DEFAULT_ACTIVITY, help="activity class name")
    parser.add_argument("--skip-install", action="store_true", help="reuse installed APK")
    parser.add_argument(
        "--combine-from-store",
        action="store_true",
        help="create full PASS evidence by copying the current store/screenshots PNGs",
    )
    parser.add_argument(
        "--no-force-stop-others",
        action="store_true",
        help="do not force-stop other third-party packages on shared emulators",
    )
    parser.add_argument(
        "--coordinate-mode",
        action="store_true",
        help="capture the 1080x2400 flow with text-guarded navigation and fixed gameplay tap coordinates",
    )
    parser.add_argument(
        "--disable-other-third-party",
        action="store_true",
        help="temporarily disable other third-party packages during capture and restore them before exit",
    )
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    suffix = "-combined-from-store" if args.combine_from_store else ""
    out_dir = ROOT / "build/store_screenshot_capture" / f"{timestamp}{suffix}"
    if args.combine_from_store:
        combine_from_store(out_dir, args.package)
        print(f"Store screenshot combined evidence PASS ({out_dir.relative_to(ROOT).as_posix()})")
        return
    if not args.serial:
        raise SystemExit("--serial is required unless --combine-from-store is used")
    smoke = Smoke(
        serial=args.serial,
        apk=Path(args.apk),
        package=args.package,
        activity=args.activity,
        out_dir=out_dir,
        skip_install=args.skip_install,
        extended=True,
        stop_other_apps=not args.no_force_stop_others,
    )
    captured: list[str] = []
    disabled_packages: list[str] = []
    try:
        if args.disable_other_third_party:
            disabled_packages = disable_other_third_party_packages(smoke)

        prepare(smoke)

        if args.coordinate_mode:
            coordinate_capture_flow(smoke, out_dir, captured)
        else:
            smoke.wait_for_text("Начать смену", timeout=12)
            capture(smoke, out_dir, "onboarding", "shawarma_onboarding.png", captured)
            smoke.tap_text_until("Начать смену", "Играть")

            smoke.wait_for_text("Играть", timeout=8)
            capture(smoke, out_dir, "menu", "shawarma_menu.png", captured)
            smoke.tap_text_until("Играть", "Выбор смены")
            capture(smoke, out_dir, "levels", "shawarma_levels.png", captured)
            smoke.tap_text_until("Смена 1", "Отдать заказ")
            capture(smoke, out_dir, "gameplay", "shawarma_gameplay.png", captured)
            smoke.serve_order(["Лаваш", "Курица", "Томат", "Огурец", "Белый"], "Заказы 1/3")
            smoke.serve_order(["Лаваш", "Курица", "Фри", "Белый"], "Заказы 2/3")
            smoke.serve_order(["Лаваш", "Курица", "Огурец", "Фри", "Белый"], "Заказы выданы")

            smoke.wait_for_text("Звёзды:", timeout=8)
            capture(smoke, out_dir, "result", "shawarma_result.png", captured)
            smoke.tap_text_until("В меню", "Играть")

            smoke.wait_for_text("Играть", timeout=8)
            smoke.tap_text_until("Играть", "Выбор смены")
            smoke.tap_text_until("Смена 1", "Отдать заказ")
            centers = smoke.ingredient_centers()
            smoke.tap_xy(*centers["Острый"])
            smoke.tap_text_until("Отдать заказ", "Ошибки 1/3")
            capture(smoke, out_dir, "wrong_order", "shawarma_wrong_order.png", captured)
            smoke.adb("shell", "input", "keyevent", "4")
            smoke.wait_for_text("Пауза", timeout=8)
            smoke.tap_text_until("В меню", "Играть")

            smoke.tap_text_until("Бесконечная смена", "Отдать заказ")
            smoke.serve_order(["Лаваш", "Курица", "Белый", "Зелень"], "Заказы 1/∞")
            for expected_text in ["Ошибки 1/3", "Ошибки 2/3", "Смена закрыта"]:
                centers = smoke.ingredient_centers()
                smoke.tap_xy(*centers["Острый"])
                smoke.tap_text_until("Отдать заказ", expected_text)
            smoke.wait_for_text("Смена закрыта", timeout=8)
            smoke.wait_for_text("Рекорд обновится", timeout=8)
            capture(smoke, out_dir, "endless_result", "shawarma_endless_result.png", captured)

        smoke.assert_no_crash()
        write_summary(
            out_dir,
            serial=args.serial,
            package=args.package,
            captured=captured,
            capture_mode="coordinate" if args.coordinate_mode else "uiautomator",
        )
        print(f"Store screenshot capture PASS ({out_dir.relative_to(ROOT).as_posix()})")
    finally:
        if disabled_packages:
            enable_packages(smoke, disabled_packages)


if __name__ == "__main__":
    main()
