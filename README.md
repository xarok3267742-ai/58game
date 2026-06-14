# Шаурма 58

«Шаурма 58» — офлайн Android-first casual игра для русскоязычной аудитории. Игрок собирает заказы шаурмы на коротких сменах: выбирает ингредиенты, отдаёт заказ до конца таймера, получает звёзды и открывает новые уровни.

## Почему эта идея
Игра понятна без длинного обучения, работает без интернета и аккаунтов, использует короткие сессии и хорошо раскрывается через единый ImageGen food-art стиль. Категория безопасна для Google Play: без gambling, финансов, политики, медицины, adult content и user-generated content.

## Стек
- Kotlin, Jetpack Compose, Material 3.
- DataStore Preferences для прогресса и настроек.
- `applicationId`: `com.andrejivliev.shawarma58`.
- `minSdk`: 23, `targetSdk`: 35, `versionName`: 1.0.0.

## Команды
```bash
./gradlew test
./gradlew lint
./gradlew assembleDebug
./gradlew bundleRelease
```

Full local release gate:
```bash
python3 scripts/release_gate.py
python3 scripts/package_release_candidate.py
```

External Play upload readiness:
```bash
python3 scripts/play_upload_auth_qa.py
python3 scripts/privacy_policy_hosting_qa.py
python3 scripts/fastlane_runtime_qa.py
python3 scripts/upload_operator_runbook_qa.py
python3 scripts/play_external_readiness_qa.py
python3 scripts/play_upload_auth_qa.py --strict
python3 scripts/privacy_policy_hosting_qa.py --strict --fetch-privacy-url
python3 scripts/fastlane_runtime_qa.py --strict
python3 scripts/play_external_readiness_qa.py --strict --fetch-privacy-url
```

Release signing настраивается через env vars:
```bash
export SHAWARMA58_KEYSTORE=/absolute/path/upload-key.jks
export SHAWARMA58_KEYSTORE_PASSWORD=...
export SHAWARMA58_KEY_ALIAS=...
export SHAWARMA58_KEY_PASSWORD=...
python3 scripts/prepare_upload_keystore.py --strict
./gradlew bundleRelease
python3 scripts/release_gate.py --strict-signing
```

Если env vars не заданы, Gradle всё равно может собрать release bundle для проверки, но перед загрузкой в Play Console нужно подписать релиз upload key.
Если upload key ещё не создан, задайте `SHAWARMA58_KEYSTORE*` env vars и выполните `python3 scripts/prepare_upload_keystore.py --generate`; helper откажется создавать ключ внутри репозитория.

## Структура
- `app/src/main/java/.../data` — модели, каталог уровней, DataStore.
- `app/src/main/java/.../game` — правила, scoring, session reducer.
- `app/src/main/java/.../ui` — Compose screens и asset mapping.
- `app/src/main/res/drawable-nodpi` — ImageGen assets.
- `docs` — product, QA, Play readiness и release report.
- `store` — Play listing draft, privacy policy HTML, app icon concept, feature graphic, real emulator screenshots and rejected/contact-sheet artifacts.
- `fastlane` — guarded Play internal-track upload config plus ru-RU metadata and generated Play graphics layout.
- `Gemfile` / `Gemfile.lock` — pinned fastlane runtime for guarded Play uploads.
- `app/build/outputs/mapping/release` — R8 mapping outputs copied into the generated handoff for release deobfuscation.

## Google Play
Проект не запрашивает permissions, не собирает персональные данные, не требует интернет и аккаунт. Play metadata готова в `fastlane/metadata/android/ru-RU`, copy/paste draft лежит в `store/play_listing_ru.md`, privacy policy HTML — `store/privacy_policy.html`, Play Console answers — `store/play_console_answers.md`. Перед публикацией проверьте Play service-account env через `python3 scripts/play_upload_auth_qa.py --strict`, а privacy URL — через `python3 scripts/privacy_policy_hosting_qa.py --strict --fetch-privacy-url`.

Основные Play screenshots: `store/screenshots/shawarma_onboarding.png`, `store/screenshots/shawarma_menu.png`, `store/screenshots/shawarma_levels.png`, `store/screenshots/shawarma_gameplay.png`, `store/screenshots/shawarma_result.png`; QA-only screenshots тоже лежат в `store/screenshots`. Финальный upload-machine checklist лежит в `docs/upload_operator_runbook.md` и проверяется `python3 scripts/upload_operator_runbook_qa.py`. Для automated upload в signing environment выполните `bundle install --path vendor/bundle`, затем `python3 scripts/prepare_upload_keystore.py --strict`, `python3 scripts/play_upload_auth_qa.py --strict`, `python3 scripts/fastlane_runtime_qa.py --strict`, `python3 scripts/privacy_policy_hosting_qa.py --strict --fetch-privacy-url`, `python3 scripts/upload_operator_runbook_qa.py`, `python3 scripts/pre_upload_blockers_qa.py --strict`, `python3 scripts/package_release_candidate.py --strict-signing --fetch-privacy-url --fetch-target-api-policy --strict-screenshots --strict-physical-device --strict-pre-upload`, `python3 scripts/post_package_validation_qa.py` и `bundle exec fastlane android validate_internal`; fastlane lane повторяет строгий package flow перед обращением к Google Play. Перед публикацией вручную нужны: Play Console app setup, upload signing, service-account JSON outside repo, content rating questionnaire, Data safety form, hosted privacy policy URL, upload-machine Fastlane runtime и release track rollout.
