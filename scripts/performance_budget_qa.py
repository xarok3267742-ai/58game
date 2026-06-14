#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_GRADLE = ROOT / "app/build.gradle.kts"
DEBUG_APK = ROOT / "app/build/outputs/apk/debug/app-debug.apk"
RELEASE_AAB = ROOT / "app/build/outputs/bundle/release/app-release.aab"
RES_DIR = ROOT / "app/src/main/res"
DRAWABLE_NODPI = RES_DIR / "drawable-nodpi"
SOURCE_DIR = ROOT / "app/src/main/java"
REPORT_JSON = ROOT / "build/reports/performance_budget.json"
REPORT_MD = ROOT / "build/reports/performance_budget.md"

MAX_RELEASE_AAB_BYTES = 8 * 1024 * 1024
MAX_DEBUG_APK_BYTES = 25 * 1024 * 1024
MAX_RES_DIR_BYTES = 4 * 1024 * 1024
MAX_DRAWABLE_NODPI_BYTES = 3 * 1024 * 1024
MAX_SINGLE_RUNTIME_IMAGE_BYTES = 900 * 1024
MAX_BASE_DEX_BYTES = 2_500_000
MAX_RUNTIME_NATIVE_LIB_BYTES = 128 * 1024
MAX_RUNTIME_NATIVE_LIB_COUNT = 8

ALLOWED_RUNTIME_IMPLEMENTATIONS = {
    'platform("androidx.compose:compose-bom:2025.01.01")',
    '"androidx.activity:activity-compose:1.10.1"',
    '"androidx.compose.foundation:foundation"',
    '"androidx.compose.material3:material3"',
    '"androidx.compose.ui:ui"',
    '"androidx.compose.ui:ui-tooling-preview"',
    '"androidx.datastore:datastore-preferences:1.2.1"',
    '"androidx.lifecycle:lifecycle-runtime-compose:2.8.7"',
}
FORBIDDEN_DEPENDENCY_PATTERNS = {
    r"com\.google\.firebase": "Firebase",
    r"firebase[-:]": "Firebase",
    r"com\.google\.android\.gms": "Google Play Services",
    r"play-services": "Google Play Services",
    r"com\.android\.billingclient": "Google Play Billing",
    r"billingclient": "Google Play Billing",
    r"play-services-ads|admob|google.*ads": "Ads SDK",
    r"adjust|appsflyer|amplitude|segment|mixpanel": "Analytics/attribution SDK",
    r"facebook-android-sdk|facebook-core": "Facebook SDK",
    r"sentry|crashlytics|bugsnag": "Crash/error reporting SDK",
    r"retrofit2|okhttp3|ktor-client": "Network client",
    r"coil-kt|glide|picasso": "Image loading SDK",
    r"androidx\.webkit|androidx\.browser": "Web/browser SDK",
    r"media3|exoplayer": "Media playback SDK",
    r"tensorflow|mlkit": "ML SDK",
    r"supabase|realm-android|room-runtime": "Backend/database SDK",
}
FORBIDDEN_SOURCE_PATTERNS = {
    r"\bWebView\b": "WebView",
    r"\bHttpURLConnection\b|\bURL\(": "network API",
    r"\bokhttp3\b|\bRetrofit\b|\bKtor\b": "network client",
    r"\bFirebase\b|\bBillingClient\b|\bAdView\b": "backend/ads/billing API",
}


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def dir_size(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def mib(value: int) -> str:
    return f"{value / (1024 * 1024):.2f} MiB"


def budget_check(name: str, actual: int, limit: int) -> Check:
    if actual > limit:
        return Check(name, "FAIL", f"{actual} bytes ({mib(actual)}) exceeds {limit} bytes ({mib(limit)})")
    return Check(name, "PASS", f"{actual} bytes ({mib(actual)}) <= {limit} bytes ({mib(limit)})")


def direct_runtime_implementations() -> list[str]:
    source = APP_GRADLE.read_text(encoding="utf-8")
    dependencies_match = re.search(r"dependencies\s*\{([\s\S]*?)\n\}", source)
    if not dependencies_match:
        return []
    body = dependencies_match.group(1)
    implementations: list[str] = []
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("implementation("):
            implementations.append(stripped.removeprefix("implementation(").removesuffix(")"))
    return implementations


def check_direct_dependencies() -> tuple[Check, list[str]]:
    implementations = direct_runtime_implementations()
    unexpected = sorted(set(implementations) - ALLOWED_RUNTIME_IMPLEMENTATIONS)
    missing = sorted(ALLOWED_RUNTIME_IMPLEMENTATIONS - set(implementations))
    if unexpected or missing:
        detail_parts = []
        if unexpected:
            detail_parts.append(f"unexpected runtime deps: {unexpected}")
        if missing:
            detail_parts.append(f"missing expected runtime deps: {missing}")
        return Check("Direct runtime dependencies", "FAIL", "; ".join(detail_parts)), implementations
    return Check("Direct runtime dependencies", "PASS", "runtime dependencies match lightweight offline allowlist"), implementations


def release_dependencies_output() -> str:
    result = subprocess.run(
        ["./gradlew", ":app:dependencies", "--configuration", "releaseRuntimeClasspath", "--console=plain"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stdout)
    return result.stdout


def check_forbidden_dependency_markers(dependencies: str) -> Check:
    lower = dependencies.lower()
    hits: list[str] = []
    for pattern, label in FORBIDDEN_DEPENDENCY_PATTERNS.items():
        if re.search(pattern, lower):
            hits.append(label)
    if hits:
        return Check("Forbidden dependency markers", "FAIL", f"found: {sorted(set(hits))}")
    return Check("Forbidden dependency markers", "PASS", "no backend/network/ads/billing/analytics SDK markers in release classpath")


def check_source_markers() -> Check:
    hits: list[str] = []
    for path in SOURCE_DIR.rglob("*.kt"):
        source = path.read_text(encoding="utf-8")
        for pattern, label in FORBIDDEN_SOURCE_PATTERNS.items():
            if re.search(pattern, source):
                hits.append(f"{relative(path)}: {label}")
    if hits:
        return Check("Forbidden source API markers", "FAIL", "; ".join(hits))
    return Check("Forbidden source API markers", "PASS", "no network/webview/backend/ads/billing API markers in app source")


def aab_stats() -> tuple[dict[str, object], list[Check]]:
    checks: list[Check] = []
    with zipfile.ZipFile(RELEASE_AAB) as bundle:
        entries = bundle.infolist()
        base_dex = sum(info.file_size for info in entries if info.filename.startswith("base/dex/") and info.filename.endswith(".dex"))
        runtime_native = [
            info for info in entries
            if info.filename.startswith("base/lib/") and info.filename.endswith(".so")
        ]
        native_bytes = sum(info.file_size for info in runtime_native)
        runtime_images = [
            info for info in entries
            if info.filename.startswith("base/res/")
            and info.filename.lower().endswith((".png", ".webp", ".jpg", ".jpeg"))
        ]
        largest_images = sorted(runtime_images, key=lambda info: info.file_size, reverse=True)[:8]
    checks.append(budget_check("Release base dex budget", base_dex, MAX_BASE_DEX_BYTES))
    checks.append(budget_check("Runtime native lib byte budget", native_bytes, MAX_RUNTIME_NATIVE_LIB_BYTES))
    if len(runtime_native) > MAX_RUNTIME_NATIVE_LIB_COUNT:
        checks.append(Check("Runtime native lib count", "FAIL", f"{len(runtime_native)} > {MAX_RUNTIME_NATIVE_LIB_COUNT}"))
    else:
        checks.append(Check("Runtime native lib count", "PASS", f"{len(runtime_native)} <= {MAX_RUNTIME_NATIVE_LIB_COUNT}"))
    oversized = [info.filename for info in runtime_images if info.file_size > MAX_SINGLE_RUNTIME_IMAGE_BYTES]
    if oversized:
        checks.append(Check("Runtime image per-file budget", "FAIL", f"oversized runtime images: {oversized}"))
    else:
        checks.append(Check("Runtime image per-file budget", "PASS", f"all runtime images <= {MAX_SINGLE_RUNTIME_IMAGE_BYTES} bytes"))
    return {
        "baseDexBytes": base_dex,
        "runtimeNativeLibBytes": native_bytes,
        "runtimeNativeLibCount": len(runtime_native),
        "largestRuntimeImages": [
            {"path": info.filename, "bytes": info.file_size}
            for info in largest_images
        ],
    }, checks


def write_reports(checks: list[Check], details: dict[str, object]) -> None:
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "checks": [check.__dict__ for check in checks],
        "budgets": {
            "releaseAabBytes": MAX_RELEASE_AAB_BYTES,
            "debugApkBytes": MAX_DEBUG_APK_BYTES,
            "resDirBytes": MAX_RES_DIR_BYTES,
            "drawableNodpiBytes": MAX_DRAWABLE_NODPI_BYTES,
            "singleRuntimeImageBytes": MAX_SINGLE_RUNTIME_IMAGE_BYTES,
            "baseDexBytes": MAX_BASE_DEX_BYTES,
            "runtimeNativeLibBytes": MAX_RUNTIME_NATIVE_LIB_BYTES,
            "runtimeNativeLibCount": MAX_RUNTIME_NATIVE_LIB_COUNT,
        },
        "details": details,
    }
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Performance Budget QA",
        "",
        f"Generated: {payload['generatedAt']}",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for check in checks:
        lines.append(f"| {check.name} | {check.status} | {check.detail} |")
    lines.extend(
        [
            "",
            "## Sizes",
            f"- Debug APK: `{relative(DEBUG_APK)}` = {DEBUG_APK.stat().st_size} bytes ({mib(DEBUG_APK.stat().st_size)})",
            f"- Release AAB: `{relative(RELEASE_AAB)}` = {RELEASE_AAB.stat().st_size} bytes ({mib(RELEASE_AAB.stat().st_size)})",
            f"- Android resources: `{relative(RES_DIR)}` = {dir_size(RES_DIR)} bytes ({mib(dir_size(RES_DIR))})",
            f"- Runtime drawable-nodpi: `{relative(DRAWABLE_NODPI)}` = {dir_size(DRAWABLE_NODPI)} bytes ({mib(dir_size(DRAWABLE_NODPI))})",
            "",
            "## Direct Runtime Dependencies",
        ]
    )
    for dependency in details.get("directRuntimeDependencies", []):
        lines.append(f"- `{dependency}`")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    required = [DEBUG_APK, RELEASE_AAB, APP_GRADLE, RES_DIR, DRAWABLE_NODPI]
    missing = [relative(path) for path in required if not path.exists()]
    if missing:
        raise SystemExit(f"Missing performance budget inputs: {missing}")

    checks: list[Check] = [
        budget_check("Debug APK size budget", DEBUG_APK.stat().st_size, MAX_DEBUG_APK_BYTES),
        budget_check("Release AAB size budget", RELEASE_AAB.stat().st_size, MAX_RELEASE_AAB_BYTES),
        budget_check("Android resource size budget", dir_size(RES_DIR), MAX_RES_DIR_BYTES),
        budget_check("Runtime drawable-nodpi size budget", dir_size(DRAWABLE_NODPI), MAX_DRAWABLE_NODPI_BYTES),
    ]

    dependency_check, implementations = check_direct_dependencies()
    checks.append(dependency_check)
    dependencies = release_dependencies_output()
    checks.append(check_forbidden_dependency_markers(dependencies))
    checks.append(check_source_markers())
    aab_detail, aab_checks = aab_stats()
    checks.extend(aab_checks)

    details = {
        "directRuntimeDependencies": implementations,
        "dependencyOutputLineCount": len(dependencies.splitlines()),
        "aab": aab_detail,
    }
    write_reports(checks, details)

    failures = [check for check in checks if check.status == "FAIL"]
    if failures:
        print("Performance budget QA failed")
        for check in failures:
            print(f"- {check.name}: {check.detail}")
        print(f"Report: {relative(REPORT_MD)}")
        raise SystemExit(1)

    print("Performance budget QA summary")
    print("| Check | Status | Detail |")
    print("|---|---|---|")
    for check in checks:
        print(f"| {check.name} | {check.status} | {check.detail} |")
    print(f"\nReports: {relative(REPORT_MD)}, {relative(REPORT_JSON)}")


if __name__ == "__main__":
    main()
