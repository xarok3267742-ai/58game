#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "app/src/main/java/com/andrejivliev/shawarma58/ui/Shawarma58App.kt"
UI_TAGS = ROOT / "app/src/main/java/com/andrejivliev/shawarma58/ui/UiTestTags.kt"
ANDROID_TEST = ROOT / "app/src/androidTest/java/com/andrejivliev/shawarma58/Shawarma58InstrumentedSmokeTest.kt"
REPORT_MD = ROOT / "build/reports/ui_behavior.md"
REPORT_JSON = ROOT / "build/reports/ui_behavior.json"
FORBIDDEN = ["TODO", "FIXME", "lorem", "placeholder", "CONCEPT_ONLY"]
REQUIRED_SNIPPETS = [
    "runCatching { ToneGenerator",
    "shouldPlayOrderFeedback(settings)",
    "orderFeedbackTone(correct)",
    "LocalHapticFeedback.current",
    "performHapticFeedback(ingredientToggleHaptic())",
    "performHapticFeedback(orderFeedbackHaptic(correct))",
    "settings.reducedMotion",
    "snap()",
    "tween(durationMillis = 360)",
    "systemBarsPadding()",
    "testTag(UiTestTags.SCREEN_ONBOARDING)",
    "testTag(UiTestTags.SCREEN_MENU)",
    "testTag(UiTestTags.SCREEN_GAMEPLAY)",
    "testTag(UiTestTags.SCREEN_RESULT)",
    "testTag(UiTestTags.RESULT_FEEDBACK)",
    "resultFeedback(result)",
    "levelWorkloadLabel(level)",
    "testTag(UiTestTags.SERVE_FEEDBACK)",
    "serveFeedback(correct = correct, before = beforeServe, after = afterServe)",
    "BackHandler(onBack = { if (isPaused) isPaused = false else isPaused = true })",
    "LocalLifecycleOwner.current",
    "LifecycleEventObserver",
    "Lifecycle.Event.ON_STOP",
    "rememberSaveable(stateSaver = AppScreenSaver)",
    "rememberSaveable(level.id, isEndless, stateSaver = GameSessionSaver)",
    "saveableValuesForSession(session)",
    "restoreSessionFromSaveableValues",
]
REQUIRED_COPY = [
    "Звуковые сигналы",
    "Меньше анимации",
    "Отдать заказ",
    "Сбросить",
    "Состав пока пуст",
    "Бесконечная смена",
    "Сбросить прогресс",
    "Удалить прогресс",
    "Локальный прогресс",
    "Серия",
    "следующий бонус",
    "Лучшая серия",
    "Чистая работа",
    "Смена принята",
    "Не хватило времени",
    "Разогрев не пошёл",
    "заказа",
    "сек",
    "Заказ выдан",
    "Состав не совпал",
    "Состав сброшен",
    "Пауза",
    "Продолжить",
    "Таймер остановлен",
]
REQUIRED_TAGS = [
    "SCREEN_ONBOARDING",
    "SCREEN_MENU",
    "SCREEN_LEVELS",
    "SCREEN_GAMEPLAY",
    "SCREEN_RESULT",
    "SCREEN_SETTINGS",
    "RESULT_FEEDBACK",
    "MENU_PLAY",
    "SERVE_ORDER",
    "SERVE_FEEDBACK",
    "PAUSE_GAME",
    "PAUSE_OVERLAY",
    "RESUME_GAME",
    "INGREDIENT_GRID",
    "SOUND_SWITCH",
    "REDUCED_MOTION_SWITCH",
    "RESET_PROGRESS",
    "CONFIRM_RESET_PROGRESS",
]
REQUIRED_TEST_COVERAGE = [
    "onboardingToLevelResultCompletesLevelAndShowsStars",
    "3 заказа • 77 сек",
    "wrongOrderShowsMistakeAndClearsSelection",
    "gameplayPauseOverlayCanResumeShift",
    "gameplayBackOpensPauseOverlayBeforeLeavingShift",
    "gameplayStateSurvivesActivityRecreation",
    "settingsTogglesUpdateRepositoryState",
    "settingsResetProgressClearsLocalProgressButKeepsSettings",
    "activeSessionSaveableValuesRestoreCurrentShift",
]
errors: list[str] = []


@dataclass
class Check:
    name: str
    status: str
    detail: str


def add_check(checks: list[Check], name: str, before_error_count: int, pass_detail: str) -> None:
    new_errors = len(errors) - before_error_count
    checks.append(
        Check(
            name=name,
            status="PASS" if new_errors == 0 else "FAIL",
            detail=pass_detail if new_errors == 0 else f"{new_errors} issue(s)",
        ),
    )


def write_reports(checks: list[Check], errors: list[str]) -> None:
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    status = "FAIL" if errors or any(check.status == "FAIL" for check in checks) else "PASS"
    payload = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "sourceFiles": [
            UI.relative_to(ROOT).as_posix(),
            UI_TAGS.relative_to(ROOT).as_posix(),
            ANDROID_TEST.relative_to(ROOT).as_posix(),
            "app/src/test/java/com/andrejivliev/shawarma58/GameRulesTest.kt",
        ],
        "requiredSnippets": REQUIRED_SNIPPETS,
        "requiredCopy": REQUIRED_COPY,
        "requiredTags": REQUIRED_TAGS,
        "requiredTestCoverage": REQUIRED_TEST_COVERAGE,
        "checks": [asdict(check) for check in checks],
        "errors": errors,
    }
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# UI Behavior QA",
        "",
        f"Generated: {payload['generatedAt']}",
        f"Status: `{status}`",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for check in checks:
        lines.append(f"| {check.name} | {check.status} | {check.detail} |")
    if errors:
        lines.extend(["", "## Errors"])
        lines.extend(f"- {error}" for error in errors)
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    global errors
    errors = []
    checks: list[Check] = []
    source = UI.read_text(encoding="utf-8")
    tags = UI_TAGS.read_text(encoding="utf-8") if UI_TAGS.exists() else ""
    android_test = ANDROID_TEST.read_text(encoding="utf-8") if ANDROID_TEST.exists() else ""

    before = len(errors)
    for token in FORBIDDEN:
        if token.lower() in source.lower():
            errors.append(f"UI source contains forbidden token {token!r}")
    add_check(checks, "Forbidden UI tokens", before, f"{len(FORBIDDEN)} forbidden tokens absent")

    before = len(errors)
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in source:
            errors.append(f"UI behavior guard missing snippet: {snippet}")
    add_check(checks, "UI behavior source snippets", before, f"{len(REQUIRED_SNIPPETS)} snippets present")

    before = len(errors)
    for text in REQUIRED_COPY:
        if text not in source:
            errors.append(f"UI copy missing required text: {text}")
    add_check(checks, "Required Russian UI copy", before, f"{len(REQUIRED_COPY)} copy terms present")

    before = len(errors)
    for tag_name in REQUIRED_TAGS:
        if tag_name not in tags:
            errors.append(f"UiTestTags.kt is missing {tag_name}")
    add_check(checks, "UI test tags", before, f"{len(REQUIRED_TAGS)} tags present")

    before = len(errors)
    for test_name in REQUIRED_TEST_COVERAGE:
        test_source = android_test
        if test_name == "activeSessionSaveableValuesRestoreCurrentShift":
            unit_test = ROOT / "app/src/test/java/com/andrejivliev/shawarma58/GameRulesTest.kt"
            test_source = unit_test.read_text(encoding="utf-8") if unit_test.exists() else ""
        if test_name not in test_source:
            errors.append(f"test coverage missing {test_name}")
    add_check(checks, "UI behavior test coverage", before, f"{len(REQUIRED_TEST_COVERAGE)} coverage markers present")

    before = len(errors)
    if "ToneGenerator(" in source and "runCatching { ToneGenerator" not in source:
        errors.append("ToneGenerator must be created through runCatching")

    if "startTone(" in source and "runCatching { tone?.startTone" not in source:
        errors.append("Tone playback must be guarded with runCatching")
    add_check(checks, "Sound safety guard", before, "ToneGenerator creation/playback guarded")

    write_reports(checks, errors)

    if errors:
        print("UI behavior QA failed")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print(f"UI behavior QA PASS ({REPORT_MD.relative_to(ROOT)}, {REPORT_JSON.relative_to(ROOT)})")


if __name__ == "__main__":
    main()
