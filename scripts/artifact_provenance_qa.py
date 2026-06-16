#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_GRADLE = ROOT / "app/build.gradle.kts"
SOURCE_MANIFEST = ROOT / "app/src/main/AndroidManifest.xml"
RELEASE_MANIFEST = ROOT / "app/build/intermediates/merged_manifests/release/processReleaseManifest/AndroidManifest.xml"
DEBUG_MANIFEST = ROOT / "app/build/intermediates/merged_manifests/debug/processDebugManifest/AndroidManifest.xml"
DEBUG_APK = ROOT / "app/build/outputs/apk/debug/app-debug.apk"
RELEASE_AAB = ROOT / "app/build/outputs/bundle/release/app-release.aab"
OUTPUT_METADATA = ROOT / "app/build/outputs/apk/debug/output-metadata.json"
MAPPING_DIR = ROOT / "app/build/outputs/mapping/release"
REPORT_JSON = ROOT / "build/reports/artifact_provenance.json"
REPORT_MD = ROOT / "build/reports/artifact_provenance.md"

EXPECTED_PACKAGE = "com.shawarma58.game"
EXPECTED_DEBUG_PACKAGE = f"{EXPECTED_PACKAGE}.debug"
EXPECTED_VERSION_CODE = "1"
EXPECTED_VERSION_NAME = "1.0.0"
EXPECTED_DEBUG_VERSION_NAME = "1.0.0-debug"
EXPECTED_MIN_SDK = "23"
EXPECTED_TARGET_SDK = "35"
EXPECTED_COMPILE_SDK = "35"
EXPECTED_ACTIVITY = "com.shawarma58.game.MainActivity"
REQUIRED_SIGNING_ENV = (
    "SHAWARMA58_KEYSTORE",
    "SHAWARMA58_KEYSTORE_PASSWORD",
    "SHAWARMA58_KEY_ALIAS",
    "SHAWARMA58_KEY_PASSWORD",
)
SECRET_SUFFIXES = {".jks", ".keystore", ".p12", ".pem"}
PROHIBITED_PERMISSION_STRINGS = (
    "android.permission.INTERNET",
    "android.permission.ACCESS_NETWORK_STATE",
    "android.permission.ACCESS_WIFI_STATE",
    "android.permission.READ_EXTERNAL_STORAGE",
    "android.permission.WRITE_EXTERNAL_STORAGE",
    "android.permission.READ_MEDIA_IMAGES",
    "android.permission.READ_MEDIA_VIDEO",
    "android.permission.CAMERA",
    "android.permission.RECORD_AUDIO",
    "android.permission.POST_NOTIFICATIONS",
    "com.android.vending.BILLING",
    "com.google.android.gms.permission.AD_ID",
)
EXPECTED_DRAWABLE_ASSETS = (
    "art_onboarding_prep.webp",
    "bg_counter.webp",
    "bg_prep_station.webp",
    "bg_receipt_counter.webp",
    "bg_route_map.webp",
    "customer_courier.webp",
    "customer_neighbor.webp",
    "customer_office.webp",
    "customer_student.webp",
    "ic_launcher_foreground.webp",
    "ingredient_chicken.webp",
    "ingredient_cucumber.webp",
    "ingredient_fries.webp",
    "ingredient_garlic.webp",
    "ingredient_greens.webp",
    "ingredient_lavash.webp",
    "ingredient_spicy.webp",
    "ingredient_tomato.webp",
)
EXPECTED_MAPPING_FILES = (
    "configuration.txt",
    "mapping.txt",
    "resources.txt",
    "seeds.txt",
    "usage.txt",
)
ANDROID_NS = "{http://schemas.android.com/apk/res/android}"


@dataclass
class Check:
    name: str
    status: str
    detail: str


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_info(path: Path) -> dict[str, object]:
    return {
        "path": relative(path),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def find_android_tool(name: str) -> str | None:
    candidates: list[Path] = []
    for env_name in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        sdk_root = os.environ.get(env_name)
        if sdk_root:
            candidates.extend(sorted((Path(sdk_root) / "build-tools").glob(f"*/{name}"), reverse=True))
    default_sdk = Path.home() / "Library/Android/sdk/build-tools"
    candidates.extend(sorted(default_sdk.glob(f"*/{name}"), reverse=True))
    path_candidate = shutil.which(name)
    if path_candidate:
        candidates.append(Path(path_candidate))
    for candidate in candidates:
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def jarsigner_path() -> str | None:
    candidates: list[Path] = []
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        candidates.append(Path(java_home) / "bin/jarsigner")
    path_candidate = shutil.which("jarsigner")
    if path_candidate:
        candidates.append(Path(path_candidate))
    candidates.append(Path("/Applications/Android Studio.app/Contents/jbr/Contents/Home/bin/jarsigner"))
    for candidate in candidates:
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def require_exists(paths: list[Path]) -> Check:
    missing = [relative(path) for path in paths if not path.exists()]
    if missing:
        return Check("Required build outputs", "FAIL", f"missing: {', '.join(missing)}")
    return Check("Required build outputs", "PASS", "APK, AAB, manifests, mapping and metadata exist")


def parse_manifest(path: Path) -> dict[str, object]:
    tree = ET.parse(path)
    root = tree.getroot()
    application = root.find("application")
    permissions = [
        node.attrib.get(f"{ANDROID_NS}name", "")
        for node in root.findall("uses-permission")
    ]
    declared_permissions = [
        {
            "name": node.attrib.get(f"{ANDROID_NS}name", ""),
            "protectionLevel": node.attrib.get(f"{ANDROID_NS}protectionLevel", ""),
        }
        for node in root.findall("permission")
    ]
    sdk = root.find("uses-sdk")
    activities: list[dict[str, object]] = []
    if application is not None:
        for activity in application.findall("activity"):
            actions = [
                node.attrib.get(f"{ANDROID_NS}name", "")
                for node in activity.findall("intent-filter/action")
            ]
            categories = [
                node.attrib.get(f"{ANDROID_NS}name", "")
                for node in activity.findall("intent-filter/category")
            ]
            activities.append(
                {
                    "name": activity.attrib.get(f"{ANDROID_NS}name", ""),
                    "exported": activity.attrib.get(f"{ANDROID_NS}exported", ""),
                    "screenOrientation": activity.attrib.get(f"{ANDROID_NS}screenOrientation", ""),
                    "actions": actions,
                    "categories": categories,
                }
            )
    return {
        "path": relative(path),
        "package": root.attrib.get("package", ""),
        "versionCode": root.attrib.get(f"{ANDROID_NS}versionCode", ""),
        "versionName": root.attrib.get(f"{ANDROID_NS}versionName", ""),
        "minSdk": sdk.attrib.get(f"{ANDROID_NS}minSdkVersion", "") if sdk is not None else "",
        "targetSdk": sdk.attrib.get(f"{ANDROID_NS}targetSdkVersion", "") if sdk is not None else "",
        "permissions": permissions,
        "declaredPermissions": declared_permissions,
        "application": dict(application.attrib) if application is not None else {},
        "activities": activities,
    }


def unexpected_permissions(permissions: list[str], package_name: str) -> list[str]:
    allowed_self_permission = f"{package_name}.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION"
    unexpected: list[str] = []
    for permission in permissions:
        if permission == allowed_self_permission:
            continue
        unexpected.append(permission)
    return unexpected


def check_source_manifest(info: dict[str, object]) -> Check:
    permissions = info["permissions"]
    if permissions:
        return Check("Source manifest privacy", "FAIL", f"source declares permissions: {permissions}")
    app = info["application"]
    if not isinstance(app, dict) or app.get(f"{ANDROID_NS}allowBackup") != "false":
        return Check("Source manifest privacy", "FAIL", "android:allowBackup must be false")
    return Check("Source manifest privacy", "PASS", "no permissions; allowBackup=false")


def check_release_manifest(info: dict[str, object]) -> Check:
    expected = {
        "package": EXPECTED_PACKAGE,
        "versionCode": EXPECTED_VERSION_CODE,
        "versionName": EXPECTED_VERSION_NAME,
        "minSdk": EXPECTED_MIN_SDK,
        "targetSdk": EXPECTED_TARGET_SDK,
    }
    mismatches = [
        f"{key}={info.get(key)!r}, expected {value!r}"
        for key, value in expected.items()
        if info.get(key) != value
    ]
    app = info["application"]
    if not isinstance(app, dict) or app.get(f"{ANDROID_NS}allowBackup") != "false":
        mismatches.append("application allowBackup must be false")
    permissions = info["permissions"]
    if isinstance(permissions, list):
        unexpected = unexpected_permissions([str(item) for item in permissions], EXPECTED_PACKAGE)
        if unexpected:
            mismatches.append(f"unexpected release permissions: {unexpected}")
    activities = info["activities"]
    launcher = None
    if isinstance(activities, list):
        for activity in activities:
            if (
                isinstance(activity, dict)
                and activity.get("name") == EXPECTED_ACTIVITY
                and "android.intent.action.MAIN" in activity.get("actions", [])
                and "android.intent.category.LAUNCHER" in activity.get("categories", [])
            ):
                launcher = activity
                break
    if launcher is None:
        mismatches.append("release launcher MainActivity not found")
    elif launcher.get("exported") != "true":
        mismatches.append("release MainActivity must be exported=true")
    for permission in PROHIBITED_PERMISSION_STRINGS:
        if permission in permissions:
            mismatches.append(f"prohibited permission present: {permission}")
    if mismatches:
        return Check("Merged release manifest", "FAIL", "; ".join(mismatches))
    return Check(
        "Merged release manifest",
        "PASS",
        "package/version/sdk/activity/privacy invariants match Play candidate",
    )


def check_debug_manifest(info: dict[str, object]) -> Check:
    mismatches = []
    if info.get("package") != EXPECTED_DEBUG_PACKAGE:
        mismatches.append(f"debug package is {info.get('package')!r}")
    if info.get("versionName") != EXPECTED_DEBUG_VERSION_NAME:
        mismatches.append(f"debug versionName is {info.get('versionName')!r}")
    app = info["application"]
    if not isinstance(app, dict) or app.get(f"{ANDROID_NS}debuggable") != "true":
        mismatches.append("debug application must be debuggable=true")
    permissions = info["permissions"]
    if isinstance(permissions, list):
        unexpected = unexpected_permissions([str(item) for item in permissions], EXPECTED_DEBUG_PACKAGE)
        if unexpected:
            mismatches.append(f"unexpected debug permissions: {unexpected}")
    if mismatches:
        return Check("Merged debug manifest", "FAIL", "; ".join(mismatches))
    return Check("Merged debug manifest", "PASS", "debug suffix/version/debuggable state are isolated")


def check_gradle_config() -> Check:
    script = APP_GRADLE.read_text(encoding="utf-8")
    required = {
        'namespace = "com.shawarma58.game"': "namespace",
        'applicationId = "com.shawarma58.game"': "applicationId",
        "compileSdk = 35": "compileSdk",
        "minSdk = 23": "minSdk",
        "targetSdk = 35": "targetSdk",
        "versionCode = 1": "versionCode",
        'versionName = "1.0.0"': "versionName",
        'applicationIdSuffix = ".debug"': "debug applicationId suffix",
        'versionNameSuffix = "-debug"': "debug version suffix",
        "isMinifyEnabled = true": "release R8 minification",
        "isShrinkResources = true": "release resource shrinking",
        "signingConfigs": "release signing config",
        "SHAWARMA58_KEYSTORE": "upload signing env var",
        "SHAWARMA58_KEYSTORE_PASSWORD": "upload signing env var",
        "SHAWARMA58_KEY_ALIAS": "upload signing env var",
        "SHAWARMA58_KEY_PASSWORD": "upload signing env var",
    }
    missing = [label for snippet, label in required.items() if snippet not in script]
    if missing:
        return Check("Gradle release config", "FAIL", f"missing: {', '.join(missing)}")
    return Check("Gradle release config", "PASS", "release identity, hardening and env signing are configured")


def parse_aapt_badging(output: str) -> dict[str, object]:
    package_match = re.search(r"package: name='([^']+)' versionCode='([^']+)' versionName='([^']+)'", output)
    sdk_match = re.search(r"sdkVersion:'([^']+)'", output)
    target_match = re.search(r"targetSdkVersion:'([^']+)'", output)
    compile_match = re.search(r"compileSdkVersion='([^']+)'", output)
    permissions = re.findall(r"uses-permission: name='([^']+)'", output)
    return {
        "package": package_match.group(1) if package_match else "",
        "versionCode": package_match.group(2) if package_match else "",
        "versionName": package_match.group(3) if package_match else "",
        "minSdk": sdk_match.group(1) if sdk_match else "",
        "targetSdk": target_match.group(1) if target_match else "",
        "compileSdk": compile_match.group(1) if compile_match else "",
        "permissions": permissions,
    }


def check_debug_apk() -> tuple[Check, dict[str, object]]:
    aapt = find_android_tool("aapt")
    if aapt is None:
        return Check("Debug APK badging", "FAIL", "aapt not found"), {}
    result = subprocess.run(
        [aapt, "dump", "badging", str(DEBUG_APK)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode != 0:
        return Check("Debug APK badging", "FAIL", result.stdout.strip()), {}
    badging = parse_aapt_badging(result.stdout)
    mismatches = []
    expected = {
        "package": EXPECTED_DEBUG_PACKAGE,
        "versionCode": EXPECTED_VERSION_CODE,
        "versionName": EXPECTED_DEBUG_VERSION_NAME,
        "minSdk": EXPECTED_MIN_SDK,
        "targetSdk": EXPECTED_TARGET_SDK,
        "compileSdk": EXPECTED_COMPILE_SDK,
    }
    for key, value in expected.items():
        if badging.get(key) != value:
            mismatches.append(f"{key}={badging.get(key)!r}, expected {value!r}")
    permissions = [str(item) for item in badging.get("permissions", [])]
    unexpected = unexpected_permissions(permissions, EXPECTED_DEBUG_PACKAGE)
    if unexpected:
        mismatches.append(f"unexpected permissions: {unexpected}")
    for permission in PROHIBITED_PERMISSION_STRINGS:
        if permission in permissions:
            mismatches.append(f"prohibited permission present: {permission}")
    if mismatches:
        return Check("Debug APK badging", "FAIL", "; ".join(mismatches)), badging
    return Check("Debug APK badging", "PASS", "debug package/version/sdk and permissions match"), badging


def check_debug_apk_signature() -> Check:
    apksigner = find_android_tool("apksigner")
    if apksigner is None:
        return Check("Debug APK signature", "FAIL", "apksigner not found")
    result = subprocess.run(
        [apksigner, "verify", "--print-certs", str(DEBUG_APK)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode != 0:
        return Check("Debug APK signature", "FAIL", result.stdout.strip())
    if "CN=Android Debug" not in result.stdout:
        return Check("Debug APK signature", "FAIL", "debug APK is not signed with Android Debug certificate")
    return Check("Debug APK signature", "PASS", "debug APK signature verifies with Android Debug certificate")


def check_aab_structure() -> tuple[Check, dict[str, object]]:
    with zipfile.ZipFile(RELEASE_AAB) as bundle:
        names = bundle.namelist()
        required_exact = [
            "BundleConfig.pb",
            "base/manifest/AndroidManifest.xml",
            "base/dex/classes.dex",
            "BUNDLE-METADATA/com.android.tools.build.gradle/app-metadata.properties",
            "BUNDLE-METADATA/com.android.tools.build.obfuscation/proguard.map",
            "base/res/mipmap-anydpi-v26/ic_launcher.xml",
            "base/res/mipmap-anydpi-v26/ic_launcher_round.xml",
        ]
        missing = [name for name in required_exact if name not in names]
        for asset in EXPECTED_DRAWABLE_ASSETS:
            if not any(name.endswith(f"/{asset}") for name in names):
                missing.append(f"*/{asset}")
        for suffix in SECRET_SUFFIXES:
            leaked = [name for name in names if name.lower().endswith(suffix)]
            missing.extend([f"forbidden secret entry {name}" for name in leaked])
        all_bytes = b"".join(bundle.read(name) for name in names if not name.endswith("/"))
        prohibited_hits = [
            value for value in PROHIBITED_PERMISSION_STRINGS if value.encode("utf-8") in all_bytes
        ]
        if EXPECTED_DEBUG_PACKAGE.encode("utf-8") in all_bytes:
            prohibited_hits.append(EXPECTED_DEBUG_PACKAGE)
        if prohibited_hits:
            missing.append(f"prohibited release string(s): {prohibited_hits}")
        metadata = bundle.read("BUNDLE-METADATA/com.android.tools.build.gradle/app-metadata.properties").decode("utf-8")
        embedded_map = bundle.read("BUNDLE-METADATA/com.android.tools.build.obfuscation/proguard.map")
    if missing:
        return Check("Release AAB structure", "FAIL", "; ".join(missing)), {}
    mapping_bytes = (MAPPING_DIR / "mapping.txt").read_bytes()
    if sha256_bytes(embedded_map) != sha256_bytes(mapping_bytes):
        return Check("Release AAB structure", "FAIL", "embedded proguard.map does not match mapping.txt"), {}
    info = {
        "entries": len(names),
        "containsBaseDex": True,
        "embeddedProguardMapSha256": sha256_bytes(embedded_map),
        "appMetadata": metadata.strip(),
    }
    return Check(
        "Release AAB structure",
        "PASS",
        "base module, runtime assets and embedded ProGuard map are present",
    ), info


def check_mapping_outputs() -> tuple[Check, dict[str, object]]:
    info: dict[str, object] = {}
    missing: list[str] = []
    for filename in EXPECTED_MAPPING_FILES:
        path = MAPPING_DIR / filename
        if not path.exists() or path.stat().st_size <= 0:
            missing.append(filename)
        elif path.stat().st_size < 100 and filename != "resources.txt":
            missing.append(f"{filename} unexpectedly small")
        else:
            info[filename] = {
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
    if missing:
        return Check("Release mapping outputs", "FAIL", f"missing/invalid: {', '.join(missing)}"), info
    return Check("Release mapping outputs", "PASS", "R8/resource shrink mapping artifacts are non-empty"), info


def check_output_metadata() -> tuple[Check, dict[str, object]]:
    if not OUTPUT_METADATA.exists():
        return Check("Debug APK output metadata", "FAIL", "output-metadata.json missing"), {}
    data = json.loads(OUTPUT_METADATA.read_text(encoding="utf-8"))
    elements = data.get("elements", [])
    if not elements:
        return Check("Debug APK output metadata", "FAIL", "no APK elements listed"), data
    first = elements[0]
    output_file = first.get("outputFile", "")
    if output_file != "app-debug.apk":
        return Check("Debug APK output metadata", "FAIL", f"unexpected output file {output_file!r}"), data
    return Check("Debug APK output metadata", "PASS", "debug APK metadata points to app-debug.apk"), data


def check_secret_files() -> Check:
    ignored_roots = {
        ".bundle",
        ".gradle",
        ".idea",
        "build",
        "app/build",
        "vendor/bundle",
    }

    def ignored(relative: str) -> bool:
        return any(relative == root or relative.startswith(f"{root}/") for root in ignored_roots)

    leaked: list[str] = []
    for current, dirs, filenames in os.walk(ROOT, onerror=lambda _error: None):
        current_path = Path(current)
        current_relative = "" if current_path == ROOT else relative(current_path)
        dirs[:] = [
            dirname
            for dirname in dirs
            if not ignored(f"{current_relative}/{dirname}".strip("/"))
        ]
        for filename in filenames:
            path = current_path / filename
            if path.suffix.lower() not in SECRET_SUFFIXES:
                continue
            leaked.append(relative(path))
    if leaked:
        return Check("Secret-like files", "FAIL", f"forbidden files in workspace: {', '.join(leaked)}")
    return Check("Secret-like files", "PASS", "no .jks/.keystore/.p12/.pem files under source workspace")


def signing_status(strict: bool) -> Check:
    missing_env = [name for name in REQUIRED_SIGNING_ENV if not os.environ.get(name)]
    signer = jarsigner_path()
    if signer is None:
        detail = "jarsigner unavailable"
        if strict:
            return Check("Release AAB signing", "FAIL", detail)
        return Check("Release AAB signing", "EXTERNAL_BLOCKER", detail)
    result = subprocess.run(
        [signer, "-verify", "-verbose", "-certs", str(RELEASE_AAB)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    output = result.stdout.lower()
    signed = "jar is unsigned" not in output and "signature was verified" in output
    if signed:
        return Check("Release AAB signing", "PASS", "AAB signature verified")
    detail = "AAB is unsigned"
    if missing_env:
        detail += f"; missing env vars: {', '.join(missing_env)}"
    if strict:
        return Check("Release AAB signing", "FAIL", detail)
    return Check("Release AAB signing", "EXTERNAL_BLOCKER", detail)


def write_reports(checks: list[Check], details: dict[str, object]) -> None:
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "project": "Шаурма 58",
        "packageName": EXPECTED_PACKAGE,
        "versionCode": int(EXPECTED_VERSION_CODE),
        "versionName": EXPECTED_VERSION_NAME,
        "checks": [check.__dict__ for check in checks],
        "artifacts": {
            "debugApk": file_info(DEBUG_APK),
            "releaseAab": file_info(RELEASE_AAB),
        },
        "details": details,
    }
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Artifact Provenance QA",
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
            "## Artifacts",
            f"- Debug APK: `{relative(DEBUG_APK)}` ({DEBUG_APK.stat().st_size} bytes, SHA-256 `{sha256_file(DEBUG_APK)}`)",
            f"- Release AAB: `{relative(RELEASE_AAB)}` ({RELEASE_AAB.stat().st_size} bytes, SHA-256 `{sha256_file(RELEASE_AAB)}`)",
            f"- Mapping directory: `{relative(MAPPING_DIR)}`",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict-signing", action="store_true", help="fail if the release AAB is unsigned")
    args = parser.parse_args()

    required_paths = [
        APP_GRADLE,
        SOURCE_MANIFEST,
        RELEASE_MANIFEST,
        DEBUG_MANIFEST,
        DEBUG_APK,
        RELEASE_AAB,
        OUTPUT_METADATA,
        MAPPING_DIR / "mapping.txt",
    ]
    checks: list[Check] = [require_exists(required_paths)]
    details: dict[str, object] = {}
    if checks[0].status == "FAIL":
        write_reports(checks, details)
        raise SystemExit(checks[0].detail)

    source_manifest = parse_manifest(SOURCE_MANIFEST)
    release_manifest = parse_manifest(RELEASE_MANIFEST)
    debug_manifest = parse_manifest(DEBUG_MANIFEST)
    details["sourceManifest"] = source_manifest
    details["releaseManifest"] = release_manifest
    details["debugManifest"] = debug_manifest

    checks.extend(
        [
            check_gradle_config(),
            check_source_manifest(source_manifest),
            check_release_manifest(release_manifest),
            check_debug_manifest(debug_manifest),
        ]
    )
    debug_apk_check, badging = check_debug_apk()
    checks.append(debug_apk_check)
    details["debugApkBadging"] = badging
    checks.append(check_debug_apk_signature())
    output_metadata_check, output_metadata = check_output_metadata()
    checks.append(output_metadata_check)
    details["debugOutputMetadata"] = output_metadata
    mapping_check, mapping_info = check_mapping_outputs()
    checks.append(mapping_check)
    details["mapping"] = mapping_info
    aab_check, aab_info = check_aab_structure()
    checks.append(aab_check)
    details["aab"] = aab_info
    checks.append(check_secret_files())
    checks.append(signing_status(strict=args.strict_signing))

    write_reports(checks, details)

    failures = [check for check in checks if check.status == "FAIL"]
    if failures:
        print("Artifact provenance QA failed")
        for check in failures:
            print(f"- {check.name}: {check.detail}")
        print(f"Report: {relative(REPORT_MD)}")
        raise SystemExit(1)

    print("Artifact provenance QA summary")
    print("| Check | Status | Detail |")
    print("|---|---|---|")
    for check in checks:
        print(f"| {check.name} | {check.status} | {check.detail} |")
    print(f"\nReports: {relative(REPORT_MD)}, {relative(REPORT_JSON)}")
    blockers = [check for check in checks if check.status == "EXTERNAL_BLOCKER"]
    if blockers:
        print("\nExternal blockers:")
        for check in blockers:
            print(f"- {check.detail}")
    else:
        print("\nArtifact provenance QA PASS")


if __name__ == "__main__":
    main()
