#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_APK = ROOT / "app/build/outputs/apk/debug/app-debug.apk"
DEFAULT_PACKAGE = "com.shawarma58.game.debug"
DEFAULT_ACTIVITY = "com.shawarma58.game.MainActivity"


@dataclass(frozen=True)
class NodeMatch:
    text: str
    bounds: tuple[int, int, int, int]
    class_name: str
    checked: bool | None
    clickable: bool

    @property
    def center(self) -> tuple[int, int]:
        left, top, right, bottom = self.bounds
        return ((left + right) // 2, (top + bottom) // 2)

    @property
    def center_y(self) -> int:
        return self.center[1]


class Smoke:
    def __init__(
        self,
        serial: str,
        apk: Path,
        package: str,
        activity: str,
        out_dir: Path,
        skip_install: bool,
        extended: bool,
        stop_other_apps: bool = True,
    ) -> None:
        self.serial = serial
        self.apk = apk
        self.package = package
        self.activity = activity
        self.out_dir = out_dir
        self.skip_install = skip_install
        self.extended = extended
        self.stop_other_apps = stop_other_apps
        self.step = 0
        self.stopped_packages: list[str] = []

    def adb(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            ["adb", "-s", self.serial, *args],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if check and result.returncode != 0:
            raise RuntimeError(f"adb {' '.join(args)} failed:\n{result.stdout}")
        return result

    def run(self) -> None:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        if not self.skip_install:
            self.require_file(self.apk)
            self.install_app()
        if self.stop_other_apps:
            self.stopped_packages = self.force_stop_other_third_party_apps()
        self.configure_display()
        self.adb("shell", "logcat", "-c", check=False)
        self.adb("shell", "pm", "clear", self.package)
        self.configure_display()
        self.launch()
        self.complete_onboarding_to_menu()

        if self.extended:
            self.run_extended_from_menu()
        else:
            self.run_basic_from_menu()

        self.assert_no_crash()
        self.write_summary()

    def complete_onboarding_to_menu(self) -> None:
        if self.maybe_wait_for_text("Начать смену", timeout=12) is None:
            self.swipe_up()
            self.wait_for_text("Начать смену", timeout=6)
        self.screenshot("01_onboarding")
        self.tap_text_until("Начать смену", "Играть")

        self.wait_for_text("Играть", timeout=8)
        self.screenshot("02_menu")

    def run_basic_from_menu(self) -> None:
        self.tap_text_until("Играть", "Выбор смены")
        self.tap_level_until(1, "Отдать заказ")
        self.screenshot("03_gameplay_start")
        self.serve_order(["Лаваш", "Курица", "Томат", "Огурец", "Белый"], "Заказы 1/3")
        self.serve_order(["Лаваш", "Курица", "Фри", "Белый"], "Заказы 2/3")
        self.serve_order(["Лаваш", "Курица", "Огурец", "Фри", "Белый"], "Заказы выданы")

        self.wait_for_text("Звёзды:", timeout=8)
        self.screenshot("04_result")

    def run_extended_from_menu(self) -> None:
        self.ensure_menu()
        self.verify_settings_persistence()
        self.ensure_menu()
        self.verify_wrong_order_and_back()
        self.ensure_menu()
        self.verify_background_pause()
        self.ensure_menu()
        self.verify_endless_result()

    def force_stop_other_third_party_apps(self) -> list[str]:
        result = self.adb("shell", "pm", "list", "packages", "-3", check=False)
        stopped: list[str] = []
        allowed_prefixes = {self.package, f"{self.package}.test"}
        for line in result.stdout.splitlines():
            if not line.startswith("package:"):
                continue
            package = line.removeprefix("package:").strip()
            if not package or package in allowed_prefixes:
                continue
            self.adb("shell", "am", "force-stop", package, check=False)
            stopped.append(package)
        return stopped

    def install_app(self) -> None:
        first = self.adb("install", "-r", "-d", str(self.apk), check=False)
        if first.returncode != 0:
            raise RuntimeError(f"adb install failed:\n{first.stdout}")
        if self.resolve_activity(check=False):
            return

        self.adb("uninstall", f"{self.package}.test", check=False)
        self.adb("uninstall", self.package, check=False)
        second = self.adb("install", "-r", "-d", str(self.apk), check=False)
        if second.returncode != 0:
            raise RuntimeError(
                "adb install failed after package-manager retry; "
                f"first output:\n{first.stdout}\nsecond output:\n{second.stdout}",
            )
        if not self.resolve_activity(check=False):
            raise RuntimeError(
                f"{self.package}/{self.activity} did not resolve after install; "
                f"install output:\n{second.stdout}",
            )

    def resolve_activity(self, check: bool = True) -> bool:
        result = self.adb("shell", "cmd", "package", "resolve-activity", "--brief", self.package, check=False)
        resolved = f"{self.package}/{self.activity}" in result.stdout
        if check and not resolved:
            raise RuntimeError(f"Activity did not resolve for {self.package}:\n{result.stdout}")
        return resolved

    def configure_display(self) -> None:
        self.adb("shell", "wm", "size", "1080x2400", check=False)
        self.adb("shell", "wm", "density", "420", check=False)

    def verify_settings_persistence(self) -> None:
        self.tap_text_until("Настройки", "Звуковые сигналы")
        self.assert_switch("Звуковые сигналы", True)
        self.assert_switch("Меньше анимации", False)
        self.tap_switch("Звуковые сигналы")
        self.tap_switch("Меньше анимации")
        self.assert_switch("Звуковые сигналы", False)
        self.assert_switch("Меньше анимации", True)
        self.screenshot("03_settings_toggled")

        self.ensure_menu()
        self.tap_text_until("Настройки", "Звуковые сигналы")
        self.assert_switch("Звуковые сигналы", False)
        self.assert_switch("Меньше анимации", True)
        self.screenshot("04_settings_persisted")
        self.ensure_menu()

    def verify_wrong_order_and_back(self) -> None:
        self.tap_text_until("Играть", "Выбор смены")
        self.tap_level_until(1, "Отдать заказ")
        centers = self.ingredient_centers()
        self.tap_xy(*centers["Острый"])
        self.tap_text_until("Отдать заказ", "Ошибки 1/3")
        self.screenshot("05_wrong_order")
        self.adb("shell", "input", "keyevent", "4")
        time.sleep(0.5)
        self.wait_for_text("Пауза", timeout=8)
        self.tap_text_until("В меню", "Играть")

    def verify_background_pause(self) -> None:
        self.tap_text_until("Играть", "Выбор смены")
        self.tap_level_until(1, "Отдать заказ")
        self.adb("shell", "input", "keyevent", "3")
        time.sleep(1.0)
        self.launch()
        self.wait_for_text("Пауза", timeout=8)
        self.screenshot("06_background_pause")
        self.tap_text_until("В меню", "Играть")

    def verify_endless_result(self) -> None:
        self.tap_text_until("Бесконечная смена", "Отдать заказ")
        self.serve_order(["Лаваш", "Курица", "Белый", "Зелень"], "Заказы 1/∞")
        for index, expected_text in enumerate(["Ошибки 1/3", "Ошибки 2/3", "Смена закрыта"]):
            centers = self.ingredient_centers()
            self.tap_xy(*centers["Острый"])
            self.tap_text_until("Отдать заказ", expected_text)
            if index < 2:
                time.sleep(0.3)
        self.wait_for_text("Смена закрыта", timeout=8)
        self.wait_for_text("Рекорд обновится", timeout=8)
        self.screenshot("07_endless_result")

    def back_to_menu(self) -> None:
        self.adb("shell", "input", "keyevent", "4")
        time.sleep(0.5)
        self.assert_foreground()
        self.wait_for_text("Играть", timeout=8)

    def ensure_menu(self) -> None:
        if self.is_foreground() and self.maybe_wait_for_text("Играть", timeout=1.5) is not None:
            return

        if self.stop_other_apps:
            self.force_stop_other_third_party_apps()
        self.adb("shell", "am", "force-stop", self.package, check=False)
        time.sleep(0.4)
        self.launch()
        if self.maybe_wait_for_text("Играть", timeout=5) is not None:
            return
        if self.maybe_wait_for_text("Начать смену", timeout=2) is not None:
            self.tap_text_until("Начать смену", "Играть")
            return
        self.wait_for_text("Играть", timeout=8)

    def launch(self) -> None:
        component = f"{self.package}/{self.activity}"
        result = self.adb("shell", "am", "start", "-n", component)
        if "Error" in result.stdout or "Exception" in result.stdout:
            raise RuntimeError(f"Failed to start {component}:\n{result.stdout}")
        self.wait_for_foreground(timeout=30)

    def wait_for_foreground(self, timeout: float) -> None:
        deadline = time.monotonic() + timeout
        last = ""
        while time.monotonic() < deadline:
            result = self.adb("shell", "dumpsys", "window", check=False)
            last = result.stdout
            focus_lines = [
                line for line in last.splitlines()
                if "mCurrentFocus" in line or "mFocusedApp" in line
            ]
            if any(self.package in line for line in focus_lines):
                return
            time.sleep(0.5)
        raise RuntimeError(f"{self.package} did not become foreground after launch")

    def ensure_foreground(self) -> None:
        if self.is_foreground():
            return
        if not self.resolve_activity(check=False):
            self.install_app()
        self.launch()

    def serve_order(
        self,
        ingredients: list[str],
        expected_text: str,
        ingredient_centers: dict[str, tuple[int, int]] | None = None,
    ) -> None:
        centers = ingredient_centers or self.ingredient_centers()
        for ingredient in ingredients:
            self.tap_xy(*centers[ingredient])
        self.tap_text_until("Отдать заказ", expected_text)

    def ingredient_centers(self) -> dict[str, tuple[int, int]]:
        expected = {"Лаваш", "Курица", "Томат", "Огурец", "Зелень", "Белый", "Острый", "Фри"}
        centers: dict[str, tuple[int, int]] = {}
        for node in self.parse_nodes():
            if node.text in expected:
                previous = centers.get(node.text)
                if previous is None or node.center_y > previous[1]:
                    centers[node.text] = node.center
        missing = sorted(expected - centers.keys())
        if missing:
            raise RuntimeError(f"Missing ingredient tiles in UI tree: {missing}")
        return centers

    def dump_xml(self) -> str:
        self.assert_foreground()
        output = ""
        for attempt in range(4):
            try:
                result = subprocess.run(
                    ["adb", "-s", self.serial, "exec-out", "uiautomator", "dump", "/dev/tty"],
                    cwd=ROOT,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    timeout=10,
                )
                output = result.stdout
            except subprocess.TimeoutExpired:
                output = ""
            if "<hierarchy" in output and "</hierarchy>" in output:
                break
            time.sleep(0.8)
        start = output.find("<hierarchy")
        if start < 0:
            raise RuntimeError(f"uiautomator output did not contain XML:\n{output[:400]}")
        end = output.rfind("</hierarchy>")
        if end < 0:
            raise RuntimeError(f"uiautomator output did not contain closing hierarchy:\n{output[-400:]}")
        return output[start:end + len("</hierarchy>")]

    def parse_nodes(self) -> list[NodeMatch]:
        self.assert_foreground()
        xml = self.dump_xml()
        root = ET.fromstring(xml)
        matches: list[NodeMatch] = []
        for element in root.iter("node"):
            text = element.attrib.get("text") or element.attrib.get("content-desc") or ""
            bounds = parse_bounds(element.attrib.get("bounds", ""))
            if text and bounds:
                matches.append(
                    NodeMatch(
                        text=text,
                        bounds=bounds,
                        class_name=element.attrib.get("class", ""),
                        checked=parse_bool(element.attrib.get("checked")),
                        clickable=element.attrib.get("clickable") == "true",
                    ),
                )
            elif bounds:
                matches.append(
                    NodeMatch(
                        text=text,
                        bounds=bounds,
                        class_name=element.attrib.get("class", ""),
                        checked=parse_bool(element.attrib.get("checked")),
                        clickable=element.attrib.get("clickable") == "true",
                    ),
                )
        return matches

    def find_text(self, text: str, prefer: str = "first") -> NodeMatch | None:
        nodes = [
            node for node in self.parse_nodes()
            if node.text == text or text in node.text
        ]
        if not nodes:
            return None
        if prefer == "bottom":
            return max(nodes, key=lambda node: node.center_y)
        if prefer == "top":
            return min(nodes, key=lambda node: node.center_y)
        return nodes[0]

    def switch_for_label(self, label: str) -> NodeMatch:
        nodes = self.parse_nodes()
        label_node = next((node for node in nodes if node.text == label), None)
        if label_node is None:
            raise RuntimeError(f"Switch label not found: {label}")
        candidates = [
            node for node in nodes
            if node.clickable
            and node.checked is not None
            and node.text == ""
            and node.center[0] > label_node.center[0]
            and abs(node.center_y - label_node.center_y) < 120
        ]
        if not candidates:
            raise RuntimeError(f"Switch node not found for {label}")
        return min(candidates, key=lambda node: abs(node.center_y - label_node.center_y))

    def assert_switch(self, label: str, expected: bool) -> None:
        actual = self.switch_for_label(label).checked
        if actual != expected:
            raise RuntimeError(f"Switch {label!r} expected {expected}, got {actual}")

    def tap_switch(self, label: str) -> None:
        x, y = self.switch_for_label(label).center
        self.tap_xy(x, y)

    def wait_for_text(self, text: str, timeout: float) -> NodeMatch:
        match = self.maybe_wait_for_text(text, timeout=timeout)
        if match is not None:
            return match
        self.capture_failure(f"missing_{safe_name(text)}")
        raise RuntimeError(f"Timed out waiting for {text!r}")

    def maybe_wait_for_text(self, text: str, timeout: float) -> NodeMatch | None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                match = self.find_text(text)
                if match is not None:
                    return match
            except Exception:
                pass
            time.sleep(0.85)
        return None

    def tap_text(self, text: str, prefer: str = "first") -> None:
        self.ensure_foreground()
        match = self.wait_for_text(text, timeout=6)
        if prefer != "first":
            preferred = self.find_text(text, prefer=prefer)
            if preferred is not None:
                match = preferred
        x, y = match.center
        self.tap_xy(x, y)

    def tap_text_until(
        self,
        text: str,
        expected_text: str,
        prefer: str = "first",
        attempts: int = 3,
        wait_after_tap: float = 3.0,
    ) -> None:
        last_error: Exception | None = None
        for attempt in range(attempts):
            try:
                self.ensure_foreground()
                self.tap_text(text, prefer=prefer)
            except Exception as error:
                last_error = error
            self.ensure_foreground()
            if self.maybe_wait_for_text(expected_text, timeout=wait_after_tap) is not None:
                return
            if attempt < attempts - 1:
                time.sleep(0.5)

        self.capture_failure(f"after_tap_{safe_name(text)}_missing_{safe_name(expected_text)}")
        detail = f"Timed out waiting for {expected_text!r} after tapping {text!r}"
        if last_error is not None:
            detail += f"; last tap error: {last_error}"
        raise RuntimeError(detail)

    def tap_level_until(self, level: int, expected_text: str) -> None:
        self.tap_text_until(f"Смена {level}", expected_text)

    def tap_xy(self, x: int, y: int) -> None:
        self.assert_foreground()
        self.adb("shell", "input", "tap", str(x), str(y))
        time.sleep(0.35)
        self.assert_foreground()

    def swipe_up(self) -> None:
        width, height = self.display_size()
        self.adb(
            "shell",
            "input",
            "swipe",
            str(width // 2),
            str(int(height * 0.82)),
            str(width // 2),
            str(int(height * 0.35)),
            "350",
        )
        time.sleep(0.5)

    def display_size(self) -> tuple[int, int]:
        result = self.adb("shell", "wm", "size", check=False)
        sizes = re.findall(r"(?:Physical|Override) size: (\d+)x(\d+)", result.stdout)
        if not sizes:
            return (1080, 2400)
        width, height = sizes[-1]
        return int(width), int(height)

    def screenshot(self, name: str) -> None:
        self.step += 1
        target = self.out_dir / f"{self.step:02d}_{name}.png"
        result = subprocess.run(
            ["adb", "-s", self.serial, "exec-out", "screencap", "-p"],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.decode("utf-8", errors="replace"))
        target.write_bytes(result.stdout)

    def capture_failure(self, name: str) -> None:
        try:
            self.screenshot(f"failure_{name}")
        except Exception:
            pass
        try:
            (self.out_dir / f"failure_{name}.xml").write_text(self.dump_xml(), encoding="utf-8")
        except Exception:
            pass
        self.save_logcat()

    def save_logcat(self) -> None:
        result = self.adb("shell", "logcat", "-d", check=False)
        (self.out_dir / "logcat.txt").write_text(result.stdout, encoding="utf-8", errors="replace")
        crash = self.adb("shell", "logcat", "-b", "crash", "-d", check=False)
        (self.out_dir / "logcat_crash.txt").write_text(crash.stdout, encoding="utf-8", errors="replace")

    def assert_no_crash(self) -> None:
        self.save_logcat()
        crash = (self.out_dir / "logcat_crash.txt").read_text(encoding="utf-8", errors="replace")
        if self.package in crash:
            raise RuntimeError(f"Crash buffer contains app crash. See {self.out_dir / 'logcat_crash.txt'}")

    def assert_foreground(self) -> None:
        focus_lines = self.foreground_focus_lines()
        if not any(self.package in line for line in focus_lines):
            raise RuntimeError(f"Foreground app is not {self.package}: {' | '.join(focus_lines[:4])}")

    def is_foreground(self) -> bool:
        focus_lines = self.foreground_focus_lines()
        return any(self.package in line for line in focus_lines)

    def foreground_focus_lines(self) -> list[str]:
        result = self.adb("shell", "dumpsys", "window", check=False)
        return [
            line for line in result.stdout.splitlines()
            if "mCurrentFocus" in line or "mFocusedApp" in line
        ]

    def write_summary(self) -> None:
        summary = f"""# Android Smoke QA

Status: PASS
Mode: `{"extended" if self.extended else "basic"}`
Serial: `{self.serial}`
Package: `{self.package}`
APK: `{self.apk.relative_to(ROOT).as_posix()}`
Generated: `{datetime.now().isoformat(timespec="seconds")}`
Stopped third-party packages: `{len(self.stopped_packages)}`
Third-party force-stop enabled: `{self.stop_other_apps}`

Covered flow:
- clean install/data clear
- first launch and onboarding
- menu
{self.covered_flow_summary()}
"""
        (self.out_dir / "summary.md").write_text(summary, encoding="utf-8")

    def covered_flow_summary(self) -> str:
        if self.extended:
            return """- settings toggles and persistence after returning to menu
- wrong order state
- Android Back from gameplay opens pause before exit
- Home/background from gameplay opens pause on return
- endless mode result
- crash buffer check"""
        return """- level select
- level 1 gameplay
- three correct orders
- result screen
- crash buffer check"""

    @staticmethod
    def require_file(path: Path) -> None:
        if not path.exists():
            raise RuntimeError(f"missing file: {path}")


def parse_bounds(raw: str) -> tuple[int, int, int, int] | None:
    match = re.fullmatch(r"\[(\d+),(\d+)]\[(\d+),(\d+)]", raw)
    if not match:
        return None
    return tuple(int(group) for group in match.groups())  # type: ignore[return-value]


def parse_bool(raw: str | None) -> bool | None:
    if raw == "true":
        return True
    if raw == "false":
        return False
    return None


def safe_name(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", text).strip("_") or "text"


def pick_serial(explicit: str | None) -> str:
    if explicit:
        return explicit
    result = subprocess.run(
        ["adb", "devices"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stdout)
    devices = [
        line.split()[0]
        for line in result.stdout.splitlines()
        if line.startswith("emulator-") and "\tdevice" in line
    ]
    if not devices:
        raise RuntimeError("No booted emulator found. Pass --serial for a connected device.")
    return devices[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--serial", help="adb serial. Defaults to the first booted emulator.")
    parser.add_argument("--apk", default=str(DEFAULT_APK), help="debug APK path")
    parser.add_argument("--package", default=DEFAULT_PACKAGE, help="installed application id")
    parser.add_argument("--activity", default=DEFAULT_ACTIVITY, help="fully qualified Activity class")
    parser.add_argument("--skip-install", action="store_true", help="reuse installed APK")
    parser.add_argument("--extended", action="store_true", help="run settings/wrong-order/endless smoke")
    parser.add_argument(
        "--no-force-stop-others",
        action="store_true",
        help="do not force-stop other third-party packages on shared emulators",
    )
    parser.add_argument(
        "--out",
        default=f"build/android_smoke/{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        help="output directory under the project root",
    )
    args = parser.parse_args()

    serial = pick_serial(args.serial)
    out_dir = ROOT / args.out if not Path(args.out).is_absolute() else Path(args.out)
    smoke = Smoke(
        serial=serial,
        apk=(ROOT / args.apk if not Path(args.apk).is_absolute() else Path(args.apk)),
        package=args.package,
        activity=args.activity,
        out_dir=out_dir,
        skip_install=args.skip_install,
        extended=args.extended,
        stop_other_apps=not args.no_force_stop_others,
    )
    try:
        smoke.run()
    except Exception as error:
        print(f"Android smoke QA failed: {error}", file=sys.stderr)
        print(f"Evidence: {out_dir}", file=sys.stderr)
        raise SystemExit(1)
    print(f"Android smoke QA PASS: {out_dir.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
