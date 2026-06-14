#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_JSON = ROOT / "build/reports/fastlane_runtime.json"
REPORT_MD = ROOT / "build/reports/fastlane_runtime.md"
GEMFILE = ROOT / "Gemfile"
LOCKFILE = ROOT / "Gemfile.lock"
BUNDLE_CONFIG = ROOT / ".bundle/config"
EXPECTED_FASTLANE = "2.230.0"
EXPECTED_BUNDLED_WITH = "1.17.2"
RUBY_TOOLCHAIN_MANAGERS = ("brew", "rbenv", "asdf", "mise", "chruby", "ruby-install")


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def status_for_absent(strict: bool) -> str:
    return "FAIL" if strict else "EXTERNAL_BLOCKER"


def run(command: list[str], timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )


def first_line(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[0] if lines else ""


def check_gemfile() -> Check:
    if not GEMFILE.exists():
        return Check("Fastlane Gemfile", "FAIL", "Gemfile is missing")
    text = GEMFILE.read_text(encoding="utf-8")
    if 'gem "fastlane"' not in text:
        return Check("Fastlane Gemfile", "FAIL", 'Gemfile must declare gem "fastlane"')
    return Check("Fastlane Gemfile", "PASS", "Gemfile declares fastlane")


def check_lockfile() -> list[Check]:
    if not LOCKFILE.exists():
        return [Check("Fastlane lockfile", "FAIL", "Gemfile.lock is missing")]
    text = LOCKFILE.read_text(encoding="utf-8")
    checks: list[Check] = []
    if f"fastlane ({EXPECTED_FASTLANE})" in text:
        checks.append(Check("Fastlane lockfile version", "PASS", f"fastlane {EXPECTED_FASTLANE} is pinned"))
    else:
        checks.append(Check("Fastlane lockfile version", "FAIL", f"Gemfile.lock must pin fastlane {EXPECTED_FASTLANE}"))
    bundled_match = re.search(r"BUNDLED WITH\s+([0-9.]+)", text)
    bundled = bundled_match.group(1) if bundled_match else ""
    if bundled == EXPECTED_BUNDLED_WITH:
        checks.append(Check("Bundler lockfile version", "PASS", f"BUNDLED WITH {bundled}"))
    elif bundled:
        checks.append(Check("Bundler lockfile version", "FAIL", f"expected {EXPECTED_BUNDLED_WITH}, got {bundled}"))
    else:
        checks.append(Check("Bundler lockfile version", "FAIL", "Gemfile.lock missing BUNDLED WITH"))
    return checks


def check_bundle_config() -> Check:
    if not BUNDLE_CONFIG.exists():
        return Check("Bundler local config", "FAIL", ".bundle/config is missing")
    text = BUNDLE_CONFIG.read_text(encoding="utf-8")
    if 'BUNDLE_PATH: "vendor/bundle"' not in text and "BUNDLE_PATH: vendor/bundle" not in text:
        return Check("Bundler local config", "FAIL", ".bundle/config must point BUNDLE_PATH to vendor/bundle")
    return Check("Bundler local config", "PASS", "BUNDLE_PATH points to vendor/bundle")


def check_ruby(strict: bool) -> list[Check]:
    ruby = shutil.which("ruby")
    if ruby is None:
        return [Check("Ruby runtime", status_for_absent(strict), "ruby command is not available")]
    checks = []
    version = run(["ruby", "--version"])
    if version.returncode == 0:
        checks.append(Check("Ruby runtime", "PASS", first_line(version.stdout)))
    else:
        checks.append(Check("Ruby runtime", status_for_absent(strict), first_line(version.stdout) or "ruby --version failed"))
        return checks

    headers = run(
        [
            "ruby",
            "-rrbconfig",
            "-e",
            "require 'json'; puts JSON.generate({rubyhdrdir: RbConfig::CONFIG['rubyhdrdir'], rubyarchhdrdir: RbConfig::CONFIG['rubyarchhdrdir']})",
        ],
    )
    if headers.returncode != 0:
        checks.append(Check("Ruby native extension headers", status_for_absent(strict), "could not inspect Ruby header paths"))
        return checks
    try:
        payload = json.loads(headers.stdout)
    except json.JSONDecodeError:
        checks.append(Check("Ruby native extension headers", status_for_absent(strict), "Ruby header path output was not JSON"))
        return checks
    configured = [
        Path(str(payload.get("rubyarchhdrdir", ""))),
        Path(str(payload.get("rubyhdrdir", ""))),
    ]
    arch_header_dir = configured[0]
    configured_hits = [path / "ruby/config.h" for path in configured if (path / "ruby/config.h").exists()]
    if configured_hits:
        checks.append(Check("Ruby native extension headers", "PASS", f"ruby/config.h found at {configured_hits[0]}"))
        return checks

    nearby_hits: list[str] = []
    for path in configured:
        if not path.exists():
            continue
        for hit in sorted(path.rglob("config.h")):
            if hit.name == "config.h" and hit.parent.name == "ruby":
                nearby_hits.append(str(hit))
    detail = (
        "ruby/config.h is not present under Ruby configured header dirs; "
        f"RbConfig rubyarchhdrdir={arch_header_dir}"
    )
    if nearby_hits:
        detail += (
            f"; nearby config.h exists at {nearby_hits[0]}; "
            "native gems can still fail because generated Makefiles depend on the configured arch header path"
        )
    else:
        detail += "; native gems such as json cannot build until Ruby development headers are repaired"
    checks.append(Check("Ruby native extension headers", status_for_absent(strict), detail))
    return checks


def detect_ruby_toolchain_managers() -> dict[str, str]:
    detected: dict[str, str] = {}
    for manager in RUBY_TOOLCHAIN_MANAGERS:
        path = shutil.which(manager)
        if path:
            detected[manager] = path
    return detected


def check_ruby_toolchain_options() -> Check:
    detected = detect_ruby_toolchain_managers()
    if detected:
        formatted = ", ".join(f"{name}={path}" for name, path in sorted(detected.items()))
        return Check("Ruby toolchain manager options", "PASS", formatted)
    return Check(
        "Ruby toolchain manager options",
        "WARN",
        "no Homebrew/rbenv/asdf/mise/chruby/ruby-install command found in PATH; final upload machine needs one working Ruby runtime with matching headers",
    )


def check_bundler(strict: bool) -> list[Check]:
    bundle = shutil.which("bundle")
    if bundle is None:
        return [Check("Bundler runtime", status_for_absent(strict), "bundle command is not available")]
    checks: list[Check] = []
    version = run([bundle, "--version"])
    if version.returncode == 0:
        checks.append(Check("Bundler runtime", "PASS", first_line(version.stdout)))
    else:
        checks.append(Check("Bundler runtime", status_for_absent(strict), first_line(version.stdout) or "bundle --version failed"))
        return checks

    bundle_check = run([bundle, "check"])
    if bundle_check.returncode == 0:
        checks.append(Check("Bundler dependency set", "PASS", first_line(bundle_check.stdout) or "bundle check passed"))
    else:
        missing = [line.strip(" *") for line in bundle_check.stdout.splitlines() if line.strip().startswith("*")]
        sample = ", ".join(missing[:5])
        suffix = f"; first missing: {sample}" if sample else ""
        checks.append(
            Check(
                "Bundler dependency set",
                status_for_absent(strict),
                f"bundle check reports {len(missing)} missing gem(s){suffix}",
            )
        )
    return checks


def check_fastlane(strict: bool) -> Check:
    bundle = shutil.which("bundle")
    if bundle is None:
        return Check("Fastlane runtime", status_for_absent(strict), "bundle command is not available")
    result = run([bundle, "exec", "fastlane", "--version"])
    if result.returncode == 0:
        output = result.stdout.strip()
        if EXPECTED_FASTLANE in output:
            return Check("Fastlane runtime", "PASS", first_line(output))
        return Check("Fastlane runtime", "FAIL", f"expected fastlane {EXPECTED_FASTLANE}, got: {first_line(output)}")
    return Check(
        "Fastlane runtime",
        status_for_absent(strict),
        first_line(result.stdout) or "bundle exec fastlane --version failed",
    )


def check_vendor_bundle(strict: bool) -> Check:
    vendor = ROOT / "vendor/bundle"
    if not vendor.exists():
        return Check("Vendor bundle directory", status_for_absent(strict), "vendor/bundle is absent; run bundle install --path vendor/bundle on upload machine")
    fastlane_dirs = list(vendor.rglob("fastlane-2.230.0"))
    if fastlane_dirs:
        return Check("Vendor bundle directory", "PASS", f"fastlane gem directory present under {rel(fastlane_dirs[0])}")
    return Check("Vendor bundle directory", status_for_absent(strict), "vendor/bundle exists but fastlane 2.230.0 gem directory is missing")


def remediation_plan() -> dict[str, object]:
    detected = detect_ruby_toolchain_managers()
    manager_names = sorted(detected)
    commands_by_manager = {
        "brew": [
            "brew install ruby",
            'export PATH="$(brew --prefix ruby)/bin:$PATH"',
            "gem install bundler -v 1.17.2",
            "bundle install --path vendor/bundle",
            "python3 scripts/fastlane_runtime_qa.py --strict",
        ],
        "rbenv": [
            "rbenv install 3.3.6",
            "rbenv local 3.3.6",
            "gem install bundler -v 1.17.2",
            "bundle install --path vendor/bundle",
            "python3 scripts/fastlane_runtime_qa.py --strict",
        ],
        "asdf": [
            "asdf plugin add ruby || true",
            "asdf install ruby 3.3.6",
            "asdf local ruby 3.3.6",
            "gem install bundler -v 1.17.2",
            "bundle install --path vendor/bundle",
            "python3 scripts/fastlane_runtime_qa.py --strict",
        ],
        "mise": [
            "mise use ruby@3.3.6",
            "gem install bundler -v 1.17.2",
            "bundle install --path vendor/bundle",
            "python3 scripts/fastlane_runtime_qa.py --strict",
        ],
    }
    recommended_manager = next((name for name in ("brew", "rbenv", "asdf", "mise") if name in detected), "")
    if recommended_manager:
        commands = commands_by_manager[recommended_manager]
        summary = f"use detected {recommended_manager} Ruby instead of macOS system Ruby"
    else:
        commands = [
            "# Install Homebrew, rbenv, asdf or mise on the upload machine.",
            "# Install Ruby 3.3.x with development headers through that tool.",
            "gem install bundler -v 1.17.2",
            "bundle install --path vendor/bundle",
            "python3 scripts/fastlane_runtime_qa.py --strict",
        ]
        summary = "install a non-system Ruby with matching development headers"
    return {
        "detectedManagers": detected,
        "recommendedManager": recommended_manager or "<none detected>",
        "summary": summary,
        "commands": commands,
        "avoid": [
            "Do not keep using macOS system Ruby when RbConfig rubyarchhdrdir does not contain ruby/config.h.",
            "Do not copy generated native gems between different Ruby architectures.",
        ],
    }


def write_reports(checks: list[Check], strict: bool) -> None:
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    statuses = [check.status for check in checks]
    if "FAIL" in statuses:
        status = "FAIL"
    elif "EXTERNAL_BLOCKER" in statuses:
        status = "EXTERNAL_BLOCKER"
    else:
        status = "PASS"
    payload = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "strict": strict,
        "checks": [check.__dict__ for check in checks],
        "expected": {
            "fastlane": EXPECTED_FASTLANE,
            "bundler": EXPECTED_BUNDLED_WITH,
            "bundlePath": "vendor/bundle",
        },
        "remediation": remediation_plan(),
    }
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Fastlane Runtime QA",
        "",
        f"Generated: {payload['generatedAt']}",
        f"Status: `{status}`",
        f"Strict mode: `{strict}`",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for check in checks:
        lines.append(f"| {check.name} | {check.status} | {check.detail} |")
    lines.extend(
        [
            "",
            "## Upload Machine Action",
            "Use a Ruby runtime with matching development headers, such as Homebrew/rbenv/asdf/mise Ruby, or repair Xcode Command Line Tools so `RbConfig::CONFIG['rubyarchhdrdir']/ruby/config.h` exists. Then run `bundle install --path vendor/bundle` and rerun `python3 scripts/fastlane_runtime_qa.py --strict`.",
            "",
            "## Remediation Plan",
            f"Summary: {payload['remediation']['summary']}",
            f"Recommended manager: `{payload['remediation']['recommendedManager']}`",
            "",
            "Commands:",
            "",
            "```bash",
            *payload["remediation"]["commands"],
            "```",
            "",
            "Avoid:",
            *[f"- {item}" for item in payload["remediation"]["avoid"]],
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true", help="fail when fastlane runtime is not upload-ready")
    args = parser.parse_args()

    checks = [
        check_gemfile(),
        *check_lockfile(),
        check_bundle_config(),
        *check_ruby(strict=args.strict),
        check_ruby_toolchain_options(),
        *check_bundler(strict=args.strict),
        check_vendor_bundle(strict=args.strict),
        check_fastlane(strict=args.strict),
    ]
    write_reports(checks, strict=args.strict)

    failures = [check for check in checks if check.status == "FAIL"]
    if failures:
        print("Fastlane runtime QA failed")
        for check in failures:
            print(f"- {check.name}: {check.detail}")
        print(f"Report: {rel(REPORT_MD)}")
        raise SystemExit(1)

    print("Fastlane runtime QA summary")
    print("| Check | Status | Detail |")
    print("|---|---|---|")
    for check in checks:
        print(f"| {check.name} | {check.status} | {check.detail} |")
    print(f"\nReports: {rel(REPORT_MD)}, {rel(REPORT_JSON)}")


if __name__ == "__main__":
    main()
