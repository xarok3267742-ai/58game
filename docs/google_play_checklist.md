# Google Play Checklist

## App metadata
- App name: Шаурма 58
- Short description: Готовь шаурму на скорость: заказы, смены и звёзды офлайн.
- Full description: «Шаурма 58» — лёгкая casual игра для Android. Собирайте заказы из ингредиентов, следите за таймером, избегайте ошибок и открывайте новые смены. Игра работает без интернета, аккаунта и платежей.
- Release notes v1.0.0: Первый релиз: 24 смены, бесконечный режим, локальный прогресс, настройки звука и уменьшения анимации.
- Play-ready files: `fastlane/metadata/android/ru-RU/title.txt`, `short_description.txt`, `full_description.txt`, `changelogs/1.txt`.
- Copy/paste listing draft: `store/play_listing_ru.md`.
- Upload packet: `store/play_upload_packet.md`.
- Upload operator runbook: `docs/upload_operator_runbook.md`; validate it with `python3 scripts/upload_operator_runbook_qa.py` before transferring the final handoff to the upload machine.
- Generated handoff directory: run `python3 scripts/create_play_handoff.py` after release gate.
- Release dates: `python3 scripts/package_release_candidate.py` runs `python3 scripts/update_release_dates.py` before the gate.
- Freshness guard: run `python3 scripts/release_freshness_qa.py` after `python3 scripts/package_release_candidate.py` to verify current-dated docs/reports, package status parity and archive sidecars.
- Handoff secret scan: run `python3 scripts/play_handoff_secret_scan_qa.py` after packaging to verify the directory and zip do not contain key files, private-key blocks or service-account credential JSON.
- Post-package guard: run `python3 scripts/post_package_validation_qa.py` after the final sidecar scan and freshness checks; it verifies final transfer sidecar scope/order, archive SHA/manifest SHA parity and that the post-package report stays local-only under `build/reports/`.
- Deobfuscation mapping: keep `deobfuscation/release/` from the handoff with the uploaded AAB.
- Asset manifest QA: run `python3 scripts/asset_manifest_qa.py`; accepted app/store assets must be documented and rejected variants must remain outside release paths.
- Fastlane graphics: run `python3 scripts/sync_fastlane_assets.py` and `python3 scripts/fastlane_assets_qa.py`; upload-ready images live under `fastlane/metadata/android/ru-RU/images`.
- Store visual quality: run `python3 scripts/store_visual_quality_qa.py`; screenshots and feature graphic must pass size, contrast, color-variety and uniqueness checks.
- Store screenshot freshness: run `python3 scripts/store_screenshot_freshness_qa.py`; `PASS_WITH_WARNINGS` means re-capture real app screenshots before final Play upload. Fastlane upload runs it in strict mode through `--strict-screenshots`.
- Store screenshot capture provenance: run `python3 scripts/store_screenshot_capture_qa.py`; every current store screenshot must match the latest real app capture evidence by SHA-256. The capture helper validates candidate screencaps before replacing curated store PNGs.
- Play Console forms: run `python3 scripts/play_console_forms_qa.py`; the answer sheet must cover app details, app access, Data safety, permissions, content rating, other declarations, target audience and release path.
- Target API policy: run `python3 scripts/play_target_api_qa.py`; use `python3 scripts/play_target_api_qa.py --fetch-policy` when re-checking the official Google Play Help Center before a final upload window.
- Privacy policy hosting: run `python3 scripts/privacy_policy_hosting_qa.py`; before Play upload run `python3 scripts/privacy_policy_hosting_qa.py --strict --fetch-privacy-url` after setting `SHAWARMA58_PRIVACY_POLICY_URL`.
- Content copy QA: run `python3 scripts/content_copy_qa.py`; app/domain/listing/privacy copy must remain final, Russian-facing and free of placeholder/dev wording.
- Accessibility source QA: run `python3 scripts/accessibility_source_qa.py`; custom controls must keep TalkBack labels/states and 48dp+ tap targets.
- Fastlane upload guard: run `python3 scripts/fastlane_config_qa.py`; optional remote validation is `bundle exec fastlane android validate_internal` after signing, service-account setup and physical-device sanity. The lane runs `python3 scripts/pre_upload_blockers_qa.py --strict` before packaging, then repeats `python3 scripts/package_release_candidate.py --strict-signing --fetch-privacy-url --fetch-target-api-policy --strict-screenshots --strict-physical-device --strict-pre-upload` before contacting Google Play.
- Play upload auth: run `python3 scripts/play_upload_auth_qa.py`; before fastlane validation run `python3 scripts/play_upload_auth_qa.py --strict` with `SUPPLY_JSON_KEY` pointing to a service-account JSON outside the repository.
- Fastlane runtime: run `python3 scripts/fastlane_runtime_qa.py`; before fastlane validation run `python3 scripts/fastlane_runtime_qa.py --strict` after installing Ruby development headers and `bundle install --path vendor/bundle`.
- External readiness: run `python3 scripts/play_external_readiness_qa.py --strict --fetch-privacy-url` in the final upload environment.
- Upload keystore setup: run `python3 scripts/prepare_upload_keystore.py --strict`; if the upload key does not exist yet, set `SHAWARMA58_KEYSTORE*` env vars and run `python3 scripts/prepare_upload_keystore.py --generate` with the path outside this repository.
- Upload operator runbook QA: run `python3 scripts/upload_operator_runbook_qa.py`; the Play handoff includes `docs/upload_operator_runbook.md` and `qa/upload_operator_runbook/`.
- Workspace hygiene: run `python3 scripts/workspace_hygiene_qa.py`; local caches, upload-secret-like files and stale duplicate reports must stay out of source and handoff release paths.
- Physical-device readiness: run `python3 scripts/physical_device_readiness_qa.py`; before production rollout run `python3 scripts/physical_device_readiness_qa.py --strict` with a real Android phone connected and complete `docs/physical_device_sanity.md`.
- Pre-upload blocker summary: run `python3 scripts/pre_upload_blockers_qa.py`; before Play upload run `python3 scripts/pre_upload_blockers_qa.py --strict` and resolve every listed operator action.
- Connected smoke: run `python3 scripts/android_smoke_qa.py --serial <adb-serial>` and `python3 scripts/android_smoke_qa.py --serial <adb-serial> --extended` before internal testing.

## Build
- Format: Android App Bundle `.aab`.
- `targetSdk`: 35, соответствует текущей опубликованной Google Play mobile submission baseline for new apps/app updates from August 31, 2025.
- `minSdk`: 23.
- `versionCode`: 1.
- `applicationId`: `com.andrejivliev.shawarma58`.

## Store graphics
- Play app icon: `store/play_icon.png`, 512x512 RGBA PNG; local adaptive preview remains saved at `store/launcher_icon_preview.png` for launcher QA.
- Feature graphic: `store/feature_graphic_concept.png`, ImageGen graphic approved as store candidate.
- Screenshots: upload-ready RGB PNGs live under `fastlane/metadata/android/ru-RU/images/phoneScreenshots/`; real emulator source captures are kept in `store/screenshots/`.
- Visual QA evidence: `build/reports/store_visual_quality.md` after running `python3 scripts/store_visual_quality_qa.py`.
- Freshness QA evidence: `build/reports/store_screenshot_freshness.md` after running `python3 scripts/store_screenshot_freshness_qa.py`.
- Fastlane/supply layout: `fastlane/metadata/android/ru-RU/images/icon.png`, `fastlane/metadata/android/ru-RU/images/featureGraphic.png` and `fastlane/metadata/android/ru-RU/images/phoneScreenshots/` are generated from the curated files above.

## Privacy and policy
- Permissions: none.
- Data safety: no data collected/shared; Android app backup is disabled in the manifest/rules for v1.
- Privacy policy: host `store/privacy_policy.html` on a public non-PDF HTTPS URL, verify it with `python3 scripts/privacy_policy_hosting_qa.py --strict --fetch-privacy-url`, then paste that URL into Play Console.
- Play Console answer sheet: `store/play_console_answers.md`.
- Content rating: casual game, no gambling, no violence, no user-generated content.
- Target audience: general casual Android users; not specifically directed at children. Recommended target age selection for v1: 13-15, 16-17, 18+.

## Manual Play Console actions
Create app, complete store listing from `fastlane/metadata/android/ru-RU`, upload hosted privacy policy URL, complete Data safety/content rating/target audience forms from `store/play_console_answers.md`, upload screenshots/feature graphic/icon manually or with guarded fastlane internal draft lanes, run pre-review checks, publish to internal testing first.

## Sources checked
- Checked on June 14, 2026.
- Google Play target API requirements: https://support.google.com/googleplay/android-developer/answer/11926878
- Google Play target API policy: https://support.google.com/googleplay/android-developer/answer/16561298
- Android App Bundles: https://developer.android.com/guide/app-bundle
- Data safety: https://support.google.com/googleplay/android-developer/answer/10787469
- User Data policy: https://support.google.com/googleplay/android-developer/answer/10144311
