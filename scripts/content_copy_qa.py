#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_MD = ROOT / "build/reports/content_copy.md"
REPORT_JSON = ROOT / "build/reports/content_copy.json"

TARGET_FILES = [
    "app/src/main/java/com/shawarma58/game/data/Models.kt",
    "app/src/main/java/com/shawarma58/game/data/LevelCatalog.kt",
    "app/src/main/java/com/shawarma58/game/ui/Shawarma58App.kt",
    "app/src/main/res/values/strings.xml",
    "fastlane/metadata/android/ru-RU/title.txt",
    "fastlane/metadata/android/ru-RU/short_description.txt",
    "fastlane/metadata/android/ru-RU/full_description.txt",
    "fastlane/metadata/android/ru-RU/changelogs/1.txt",
    "store/play_listing_ru.md",
    "store/play_console_answers.md",
    "store/privacy_policy.html",
]
RUSSIAN_COPY_FILES = [
    "fastlane/metadata/android/ru-RU/title.txt",
    "fastlane/metadata/android/ru-RU/short_description.txt",
    "fastlane/metadata/android/ru-RU/full_description.txt",
    "fastlane/metadata/android/ru-RU/changelogs/1.txt",
    "store/play_listing_ru.md",
    "store/privacy_policy.html",
]
FORBIDDEN_TOKENS = [
    "TODO",
    "FIXME",
    "lorem",
    "placeholder",
    "CONCEPT_ONLY",
    "sample text",
    "dummy",
    "ipsum",
    "временный текст",
    "заглушка",
    "черновик",
]

APP_REQUIRED_TERMS = [
    "Шаурма 58",
    "Собирай заказы, держи темп",
    "Заверни смену без ошибок",
    "Начать смену",
    "Бесконечная смена",
    "О проекте и приватность",
    "Выбор смены",
    "Звуковые сигналы",
    "Меньше анимации",
    "Локальный прогресс",
    "Удалить прогресс",
    "Сбросить прогресс",
    "Приватность",
    "Пауза",
    "Продолжить",
    "Отдать заказ",
    "Состав пока пуст",
    "Серия",
    "Смена сорвалась",
    "Лучшая серия",
    "Чистая работа",
    "Смена принята",
    "Не хватило времени",
    "Разогрев не пошёл",
    "Заказ выдан",
    "Состав не совпал",
    "Состав сброшен",
]
DOMAIN_REQUIRED_TERMS = [
    "Лаваш",
    "Курица",
    "Томаты",
    "Огурцы",
    "Зелень",
    "Белый соус",
    "Острый соус",
    "Картофель",
    "Офисный перерыв",
    "После пары",
    "Ночная доставка",
    "Сосед за углом",
    "Классика района",
    "Свежий заворот",
    "Острый поворот",
    "Бесконечная смена",
    "спокойно",
    "быстро",
    "жарко",
]
STORE_REQUIRED_TERMS = [
    "Готовь шаурму на скорость",
    "24 смены",
    "8 ингредиентов",
    "4 типа клиентов",
    "офлайн",
    "не требует аккаунта и интернета",
    "нет рекламы, покупок",
    "Политика конфиденциальности",
    "не собирает",
    "не передаёт",
    "No data collected.",
    "Content Rating",
    "Target Audience",
]
POLICY_SENSITIVE_ALLOWED_ABSENT = [
    "INTERNET permission: absent",
    "Ads: No",
    "In-app purchases: No",
    "Accounts/login: No",
]


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def file_check(relative: str) -> Check:
    path = ROOT / relative
    if not path.exists():
        return Check(f"{relative} exists", "FAIL", "file is missing")
    if path.stat().st_size == 0:
        return Check(f"{relative} exists", "FAIL", "file is empty")
    return Check(f"{relative} exists", "PASS", f"{path.stat().st_size} bytes")


def forbidden_token_checks() -> list[Check]:
    checks: list[Check] = []
    for relative in TARGET_FILES:
        path = ROOT / relative
        if not path.exists():
            checks.append(Check(f"{relative} forbidden tokens", "FAIL", "file is missing"))
            continue
        text = path.read_text(encoding="utf-8")
        lowered = text.lower()
        found = [token for token in FORBIDDEN_TOKENS if token.lower() in lowered]
        status = "FAIL" if found else "PASS"
        detail = "none found" if not found else f"found: {', '.join(found)}"
        checks.append(Check(f"{relative} forbidden tokens", status, detail))
    return checks


def require_terms(name: str, text: str, terms: list[str]) -> Check:
    missing = [term for term in terms if term not in text]
    if missing:
        return Check(name, "FAIL", f"missing terms: {', '.join(missing)}")
    return Check(name, "PASS", f"{len(terms)} required terms present")


def cyrillic_ratio(text: str) -> float:
    letters = re.findall(r"[A-Za-zА-Яа-яЁё]", text)
    if not letters:
        return 0.0
    cyrillic = [letter for letter in letters if re.match(r"[А-Яа-яЁё]", letter)]
    return len(cyrillic) / len(letters)


def russian_density_checks() -> list[Check]:
    checks: list[Check] = []
    minimums = {
        "fastlane/metadata/android/ru-RU/title.txt": 1.0,
        "fastlane/metadata/android/ru-RU/short_description.txt": 1.0,
        "fastlane/metadata/android/ru-RU/full_description.txt": 0.78,
        "fastlane/metadata/android/ru-RU/changelogs/1.txt": 1.0,
        "store/play_listing_ru.md": 0.50,
        "store/privacy_policy.html": 0.60,
    }
    for relative in RUSSIAN_COPY_FILES:
        text = read(relative)
        ratio = cyrillic_ratio(text)
        minimum = minimums[relative]
        checks.append(
            Check(
                f"{relative} Russian copy density",
                "PASS" if ratio >= minimum else "FAIL",
                f"{ratio:.2f}, minimum {minimum:.2f}",
            ),
        )
    return checks


def metadata_length_checks() -> list[Check]:
    limits = {
        "fastlane/metadata/android/ru-RU/title.txt": 30,
        "fastlane/metadata/android/ru-RU/short_description.txt": 80,
        "fastlane/metadata/android/ru-RU/full_description.txt": 4000,
        "fastlane/metadata/android/ru-RU/changelogs/1.txt": 500,
    }
    checks: list[Check] = []
    for relative, limit in limits.items():
        text = read(relative).strip()
        checks.append(
            Check(
                f"{relative} length",
                "PASS" if 0 < len(text) <= limit else "FAIL",
                f"{len(text)}/{limit}",
            ),
        )
    return checks


def policy_alignment_checks() -> list[Check]:
    answers = read("store/play_console_answers.md")
    checks: list[Check] = []
    for term in POLICY_SENSITIVE_ALLOWED_ABSENT:
        checks.append(
            Check(
                f"Play answer term {term}",
                "PASS" if term in answers else "FAIL",
                "present" if term in answers else "missing",
            ),
        )
    return checks


def write_reports(checks: list[Check]) -> None:
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    status = "FAIL" if any(check.status == "FAIL" for check in checks) else "PASS"
    payload = {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "checks": [check.__dict__ for check in checks],
        "targetFiles": TARGET_FILES,
    }
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Content Copy QA",
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
    app_text = "\n".join(
        [
            read("app/src/main/java/com/shawarma58/game/ui/Shawarma58App.kt"),
            read("app/src/main/res/values/strings.xml"),
        ],
    )
    domain_text = "\n".join(
        [
            read("app/src/main/java/com/shawarma58/game/data/Models.kt"),
            read("app/src/main/java/com/shawarma58/game/data/LevelCatalog.kt"),
        ],
    )
    store_text = "\n".join(
        [
            read("fastlane/metadata/android/ru-RU/title.txt"),
            read("fastlane/metadata/android/ru-RU/short_description.txt"),
            read("fastlane/metadata/android/ru-RU/full_description.txt"),
            read("fastlane/metadata/android/ru-RU/changelogs/1.txt"),
            read("store/play_listing_ru.md"),
            read("store/play_console_answers.md"),
            read("store/privacy_policy.html"),
        ],
    )
    checks = [
        *[file_check(relative) for relative in TARGET_FILES],
        *forbidden_token_checks(),
        require_terms("App visible Russian copy", app_text, APP_REQUIRED_TERMS),
        require_terms("Domain catalog Russian copy", domain_text, DOMAIN_REQUIRED_TERMS),
        require_terms("Store and policy copy", store_text, STORE_REQUIRED_TERMS),
        *metadata_length_checks(),
        *russian_density_checks(),
        *policy_alignment_checks(),
    ]
    write_reports(checks)
    failures = [check for check in checks if check.status == "FAIL"]
    if failures:
        print("Content copy QA failed")
        for failure in failures:
            print(f"- {failure.name}: {failure.detail}")
        raise SystemExit(1)
    print(f"Content copy QA PASS ({rel(REPORT_MD)}, {rel(REPORT_JSON)})")


if __name__ == "__main__":
    main()
