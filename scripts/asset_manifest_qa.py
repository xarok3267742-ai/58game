#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSET_MANIFEST = ROOT / "docs/asset_manifest.md"
REJECTED_ASSETS = ROOT / "docs/rejected_assets.md"
REPORT_MD = ROOT / "build/reports/asset_manifest.md"
REPORT_JSON = ROOT / "build/reports/asset_manifest.json"

REQUIRED_MANIFEST_TERMS = [
    "store/app_icon_concept.png",
    "store/play_icon.png",
    "app/src/main/res/drawable-nodpi/ic_launcher_foreground.webp",
    "app/src/main/res/mipmap-*/ic_launcher.png",
    "app/src/main/res/mipmap-*/ic_launcher_round.png",
    "app/src/main/res/drawable-nodpi/bg_counter.webp",
    "app/src/main/res/drawable-nodpi/bg_route_map.webp",
    "app/src/main/res/drawable-nodpi/bg_prep_station.webp",
    "app/src/main/res/drawable-nodpi/bg_receipt_counter.webp",
    "app/src/main/res/drawable-nodpi/art_onboarding_prep.webp",
    "app/src/main/res/drawable-nodpi/ingredient_lavash.webp",
    "app/src/main/res/drawable-nodpi/ingredient_chicken.webp",
    "app/src/main/res/drawable-nodpi/ingredient_tomato.webp",
    "app/src/main/res/drawable-nodpi/ingredient_cucumber.webp",
    "app/src/main/res/drawable-nodpi/ingredient_greens.webp",
    "app/src/main/res/drawable-nodpi/ingredient_garlic.webp",
    "app/src/main/res/drawable-nodpi/ingredient_spicy.webp",
    "app/src/main/res/drawable-nodpi/ingredient_fries.webp",
    "app/src/main/res/drawable-nodpi/customer_office.webp",
    "app/src/main/res/drawable-nodpi/customer_student.webp",
    "app/src/main/res/drawable-nodpi/customer_courier.webp",
    "app/src/main/res/drawable-nodpi/customer_neighbor.webp",
    "store/feature_graphic_concept.png",
    "store/imagegen_contact_sheet.jpg",
    "store/launcher_icon_preview.png",
    "store/ingredient_alpha_contact_sheet.png",
    "store/screenshots/shawarma_onboarding.png",
    "store/screenshots/shawarma_menu.png",
    "store/screenshots/shawarma_levels.png",
    "store/screenshots/shawarma_gameplay.png",
    "store/screenshots/shawarma_result.png",
    "store/screenshots/shawarma_wrong_order.png",
    "store/screenshots/shawarma_endless_result.png",
]
APPROVED_RELEASE_TERMS = [
    "ImageGen app icon prompt",
    "ImageGen splash/background prompt",
    "ImageGen screen background prompt",
    "ImageGen onboarding prompt",
    "ImageGen ingredient prompt",
    "ImageGen portrait prompt",
    "ImageGen store prompt",
    "Real Android emulator screenshot",
    "APPROVED",
]
RELEASE_PATH_PREFIXES = [
    "app/src/main/res/",
    "fastlane/metadata/android/ru-RU/images/",
    "store/play_icon.png",
    "store/screenshots/",
    "store/feature_graphic_concept.png",
]


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def rejected_paths() -> list[str]:
    if not REJECTED_ASSETS.exists():
        return []
    text = read(REJECTED_ASSETS)
    paths: list[str] = []
    for part in text.split("`")[1::2]:
        if part.startswith("store/rejected_assets/"):
            paths.append(part)
    return sorted(set(paths))


def file_exists_for_term(term: str) -> bool:
    if "*" in term:
        return bool(list(ROOT.glob(term)))
    return (ROOT / term).exists()


def check_required_terms(manifest: str) -> list[Check]:
    checks: list[Check] = []
    for term in REQUIRED_MANIFEST_TERMS:
        checks.append(
            Check(
                f"Manifest documents {term}",
                "PASS" if term in manifest else "FAIL",
                "documented" if term in manifest else "missing from docs/asset_manifest.md",
            ),
        )
        checks.append(
            Check(
                f"Asset exists {term}",
                "PASS" if file_exists_for_term(term) else "FAIL",
                "exists" if file_exists_for_term(term) else "missing from workspace",
            ),
        )
    return checks


def check_manifest_status_terms(manifest: str) -> list[Check]:
    checks: list[Check] = []
    for term in APPROVED_RELEASE_TERMS:
        checks.append(
            Check(
                f"Manifest term {term}",
                "PASS" if term in manifest else "FAIL",
                "present" if term in manifest else "missing",
            ),
        )
    return checks


def release_paths() -> list[str]:
    paths: list[str] = []
    for prefix in RELEASE_PATH_PREFIXES:
        if prefix.endswith("/"):
            root = ROOT / prefix
            if root.exists():
                paths.extend(rel(path) for path in root.rglob("*") if path.is_file())
        else:
            path = ROOT / prefix
            if path.exists():
                paths.append(rel(path))
    return sorted(set(paths))


def check_rejected_assets(manifest: str) -> list[Check]:
    checks: list[Check] = []
    rejected = rejected_paths()
    checks.append(
        Check(
            "Rejected asset documentation",
            "PASS" if rejected else "FAIL",
            f"{len(rejected)} rejected asset(s) documented" if rejected else "no rejected assets documented",
        ),
    )
    all_release_paths = release_paths()
    for rejected_path in rejected:
        checks.append(
            Check(
                f"Rejected asset exists {rejected_path}",
                "PASS" if (ROOT / rejected_path).exists() else "FAIL",
                "exists outside release path" if (ROOT / rejected_path).exists() else "missing",
            ),
        )
        filename = Path(rejected_path).name
        release_hits = [
            path
            for path in all_release_paths
            if Path(path).name == filename and not path.startswith("store/rejected_assets/")
        ]
        checks.append(
            Check(
                f"Rejected asset excluded {filename}",
                "PASS" if not release_hits else "FAIL",
                "not present in release asset paths" if not release_hits else ", ".join(release_hits),
            ),
        )
    if "store/rejected_assets/" not in manifest:
        checks.append(Check("Manifest references rejected asset docs", "FAIL", "asset manifest should mention rejected assets location"))
    else:
        checks.append(Check("Manifest references rejected asset docs", "PASS", "rejected assets location referenced"))
    return checks


def write_reports(checks: list[Check]) -> None:
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    status = "FAIL" if any(check.status == "FAIL" for check in checks) else "PASS"
    payload = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "checks": [check.__dict__ for check in checks],
        "requiredManifestTerms": REQUIRED_MANIFEST_TERMS,
        "rejectedAssets": rejected_paths(),
    }
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Asset Manifest QA",
        "",
        f"Generated: {payload['generatedAt']}",
        f"Status: `{status}`",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for check in checks:
        lines.append(f"| {check.name} | {check.status} | {check.detail} |")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    manifest = read(ASSET_MANIFEST)
    checks = [
        Check("Asset manifest file", "PASS" if ASSET_MANIFEST.exists() else "FAIL", rel(ASSET_MANIFEST)),
        Check("Rejected assets file", "PASS" if REJECTED_ASSETS.exists() else "FAIL", rel(REJECTED_ASSETS)),
        *check_required_terms(manifest),
        *check_manifest_status_terms(manifest),
        *check_rejected_assets(manifest),
    ]
    write_reports(checks)
    failures = [check for check in checks if check.status == "FAIL"]
    if failures:
        print("Asset manifest QA failed")
        for failure in failures:
            print(f"- {failure.name}: {failure.detail}")
        raise SystemExit(1)
    print(f"Asset manifest QA PASS ({rel(REPORT_MD)}, {rel(REPORT_JSON)})")


if __name__ == "__main__":
    main()
