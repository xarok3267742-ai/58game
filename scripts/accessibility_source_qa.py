#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "app/src/main/java/com/shawarma58/game/ui/Shawarma58App.kt"
ANDROID_TEST = ROOT / "app/src/androidTest/java/com/shawarma58/game/Shawarma58InstrumentedSmokeTest.kt"
ACCESSIBILITY_DOC = ROOT / "docs/accessibility_notes.md"
UI_AUDIT = ROOT / "docs/ui_audit.md"
REPORT_MD = ROOT / "build/reports/accessibility_source.md"
REPORT_JSON = ROOT / "build/reports/accessibility_source.json"


@dataclass
class Check:
    name: str
    status: str
    detail: str


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def check_contains(name: str, source: str, snippet: str, detail: str) -> Check:
    status = "PASS" if snippet in source else "FAIL"
    return Check(name=name, status=status, detail=detail)


def write_reports(checks: list[Check]) -> None:
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "checks": [check.__dict__ for check in checks],
    }
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Accessibility Source QA",
        "",
        f"Generated: {payload['generatedAt']}",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for check in checks:
        lines.append(f"| {check.name} | {check.status} | {check.detail} |")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ui = read(UI)
    android_test = read(ANDROID_TEST)
    accessibility_doc = read(ACCESSIBILITY_DOC)
    ui_audit = read(UI_AUDIT)
    checks = [
        check_contains(
            "Back button accessible label",
            ui,
            'contentDescription = "Назад"',
            "Header back control exposes a Russian TalkBack label instead of only a symbol",
        ),
        check_contains(
            "Back button role",
            ui,
            "role = Role.Button",
            "Interactive custom surfaces expose button role semantics",
        ),
        check_contains(
            "Back button tap target",
            ui,
            ".size(48.dp)",
            "Header back control has an explicit 48dp tap target",
        ),
        check_contains(
            "Ingredient tile semantics",
            ui,
            'contentDescription = "Ингредиент ${ingredient.title}"',
            "Ingredient tiles expose actionable ingredient names",
        ),
        check_contains(
            "Ingredient selected state",
            ui,
            'val selectedState = if (selected) "Выбран" else "Не выбран"',
            "Ingredient tile state is available to accessibility services",
        ),
        check_contains(
            "Level tile semantics",
            ui,
            'contentDescription = "Смена ${level.id}, ${level.speedLabel}, ${levelAccessibilityWorkloadLabel(level)}, $starsLabel"',
            "Level tiles expose shift number, tempo, workload and stars",
        ),
        check_contains(
            "Level locked state",
            ui,
            'stateDescription = if (unlocked) "Доступна" else "Закрыта"',
            "Locked and unlocked level states are explicit",
        ),
        check_contains(
            "Stars grammar helper",
            ui,
            "starsAccessibilityLabel",
            "Russian star count accessibility text is generated centrally",
        ),
        check_contains(
            "Primary button target",
            ui,
            ".height(54.dp)",
            "Primary buttons exceed 48dp minimum tap target height",
        ),
        check_contains(
            "Secondary button target",
            ui,
            ".height(52.dp)",
            "Secondary buttons exceed 48dp minimum tap target height",
        ),
        check_contains(
            "Meaningful customer image label",
            ui,
            "contentDescription = order.customer.title",
            "Customer portraits keep meaningful labels",
        ),
        check_contains(
            "Decorative background hidden",
            ui,
            "contentDescription = null",
            "Decorative images can be hidden from accessibility services",
        ),
        check_contains(
            "Instrumentation accessibility assertion",
            android_test,
            'onNodeWithContentDescription("Назад").assertHasClickAction()',
            "Instrumentation smoke protects the back button label",
        ),
        check_contains(
            "Accessibility docs mention semantics",
            accessibility_doc,
            "semantic role",
            "Accessibility notes document custom control semantics",
        ),
        check_contains(
            "UI audit mentions TalkBack",
            ui_audit,
            "TalkBack",
            "UI audit records screen-reader behavior checks",
        ),
    ]

    write_reports(checks)
    failures = [check for check in checks if check.status == "FAIL"]
    if failures:
        print("Accessibility source QA failed")
        for failure in failures:
            print(f"- {failure.name}: {failure.detail}")
        raise SystemExit(1)

    print("Accessibility source QA PASS")


if __name__ == "__main__":
    main()
