# Completion Audit

Date: June 14, 2026.

## Status labels
- Verified Locally: evidence exists in the workspace and is covered by code, docs, assets, scripts or local command output.
- External Blocker: requires Play Console, signing secrets, hosting or a physical device outside this workspace.
- Manual Final Check: must be repeated by the release owner before production rollout.
- Intentional Non-goal: excluded from v1 by product decision.

## Executive summary
The Android game "Шаурма 58" is implemented as a local release candidate: Kotlin/Compose app, offline gameplay loop, local progress, ImageGen asset set, Play metadata, QA docs and automated gates are present. `python3 scripts/release_gate.py` passes local checks, including artifact provenance for APK/AAB/mapping outputs, writes `build/reports/release_gate.md`/JSON and writes a consolidated pre-upload blocker summary when upload-key, Play, hosting, fastlane runtime or physical-device inputs are absent.

Production Play upload is not fully complete inside this workspace because five operator areas remain external: upload signing, hosted privacy policy URL, Play Console/service-account setup, Fastlane Ruby/Bundler runtime on the upload machine, and one real-device sanity pass.

## Requirement matrix
| Requirement | Status | Evidence |
|---|---|---|
| Pick one product from 10 evaluated ideas and document why | Verified Locally | `docs/product_decision.md` evaluates all 10 ideas and selects "Шаурма 58". |
| Kotlin + Jetpack Compose + Material 3 Android project | Verified Locally | `app/build.gradle.kts`, `settings.gradle.kts`, `app/src/main/java/com/shawarma58/game/MainActivity.kt`. |
| `applicationId = "com.shawarma58.game"`, `minSdk = 23`, `targetSdk = 35`, `versionCode = 1`, `versionName = "1.0.0"` | Verified Locally | `app/build.gradle.kts`. |
| Single Activity app | Verified Locally | `app/src/main/AndroidManifest.xml`, `MainActivity.kt`, `ui/Shawarma58App.kt`. |
| Offline-first, no backend/accounts/internet/ads/IAP | Verified Locally | Manifest declares no permissions; `docs/privacy_and_permissions.md`, `docs/product_decision.md`, `app/build.gradle.kts` dependencies. |
| DataStore Preferences for local progress/settings | Verified Locally | `data/ProgressStore.kt` with `onboardingSeen`, `soundEnabled`, `reducedMotion`, `completedLevels`, `starsByLevel`, `bestEndlessScore`. |
| In-app local progress reset | Verified Locally | `data/ProgressStore.kt` `resetProgress`, `ui/Shawarma58App.kt`, `UiTestTags.kt`, `Shawarma58InstrumentedSmokeTest.kt`; settings screen confirms reset and clears onboarding, completed levels, stars and endless record while preserving settings. |
| Core gameplay loop: level -> assemble order -> pause/resume -> serve -> score/streak/stars/unlock | Verified Locally | `game/GameEngine.kt`, `data/LevelCatalog.kt`, `ui/Shawarma58App.kt`, `GameRulesTest.kt` and `Shawarma58InstrumentedSmokeTest.kt` with reducer, scoring, streak bonus, pause overlay, Android Back opens pause overlay before exit, lifecycle background pause on `ON_STOP`, configuration-change restore via `rememberSaveable`, star threshold, order generation, serve/result feedback, sound/haptic feedback helpers and completion tests including `gameplayBackOpensPauseOverlayBeforeLeavingShift` plus `activeSessionSaveableValuesRestoreCurrentShift`. |
| Screens: splash, onboarding, menu, level select, gameplay, result, settings, credits/privacy | Verified Locally | `ui/Shawarma58App.kt`, level workload labels, scrollable result feedback, real screenshots in `store/screenshots/`, `docs/ui_audit.md`. |
| MVP content: 24 levels, 8 ingredients, 4 customer types, 3 difficulty tempos | Verified Locally | `data/LevelCatalog.kt`, `data/Models.kt`, `GameRulesTest.kt`. |
| Russian final microcopy, no placeholder content | Verified Locally | `docs/content_audit.md`, `scripts/content_copy_qa.py`, `build/reports/content_copy.md`, `scripts/play_metadata_qa.py`, `build/reports/play_metadata.md`, app source copy. |
| ImageGen app icon/background/ingredients/customers/onboarding/store graphic | Verified Locally | `docs/asset_manifest.md`, `docs/asset_prompts.md`, `scripts/asset_manifest_qa.py`, `build/reports/asset_manifest.md`, `app/src/main/res/drawable-nodpi/`, `store/play_icon.png`, `store/feature_graphic_concept.png`. |
| Transparent ingredient sprites and local alpha QA | Verified Locally | `scripts/remove_sprite_background.py`, `scripts/asset_qa.py`, `build/reports/asset.md`, `build/reports/asset.json`, `build/play_handoff/shawarma58-v1.0.0/qa/asset/`, `store/ingredient_alpha_contact_sheet.png`. |
| Bad variants excluded and documented | Verified Locally | `docs/rejected_assets.md`, `store/rejected_assets/lavash_v1_rejected.png`, `scripts/asset_manifest_qa.py`; rejected filenames are checked against release asset paths. |
| Store screenshots are real emulator screenshots, not fake ImageGen UI | Verified Locally | `store/screenshots/*.png`, `docs/release_report.md`, `docs/qa_test_plan.md`. |
| Store screenshot visual quality and uniqueness | Verified Locally | `scripts/store_visual_quality_qa.py`, `build/reports/store_visual_quality.md`, `docs/google_play_checklist.md`. |
| Store screenshot freshness against current UI source | Verified Locally | `scripts/capture_store_screenshots.py`, `scripts/store_screenshot_freshness_qa.py` and `build/reports/store_screenshot_freshness.md`; after the June 14 screen-specific ImageGen background UI/UX pass, all seven store/QA screenshots were recaptured from the current APK on `emulator-5586`, and strict freshness passes. |
| Store screenshot bad-capture guard | Verified Locally | `scripts/capture_store_screenshots.py`, `scripts/store_screenshot_capture_guard_qa.py`, `build/reports/store_screenshot_capture_guard.md`; screencaps are written to candidate files first, current store PNGs pass validation and solid black/headless candidates are rejected before curated PNG overwrite. |
| Store screenshot capture provenance | Verified Locally | `scripts/store_screenshot_capture_qa.py`, `build/reports/store_screenshot_capture.md`, `build/store_screenshot_capture/20260614-124029/summary.md`; the latest seven-screen capture matches current `store/screenshots/` by SHA-256 and is newer than tracked UI/resource source. |
| Required product, QA, Play and release docs created | Verified Locally | `AGENTS.md`, `README.md`, `docs/product_spec.md`, `docs/google_play_checklist.md`, `docs/release_report.md` and related docs. |
| Google Play listing metadata prepared | Verified Locally | `fastlane/metadata/android/ru-RU/`, `store/play_listing_ru.md`, `store/play_console_answers.md`, `store/play_upload_packet.md`, `scripts/play_metadata_qa.py`, `scripts/play_upload_packet_qa.py`, `build/reports/play_metadata.md`, `build/reports/play_metadata.json`, `build/reports/play_upload_packet.md`, `build/reports/play_upload_packet.json`, `build/play_handoff/shawarma58-v1.0.0/qa/play_metadata/`, `build/play_handoff/shawarma58-v1.0.0/qa/play_upload_packet/`, `scripts/create_play_handoff.py`. |
| Play Console forms answer coverage | Verified Locally | `store/play_console_answers.md`, `scripts/play_console_forms_qa.py`, `build/reports/play_console_forms.md`; app details, app access, Data safety, permissions, content rating, other declarations, target audience and release path are checked. |
| Google Play target API policy gate | Verified Locally | `app/build.gradle.kts`, `docs/google_play_checklist.md`, `scripts/play_target_api_qa.py`, `build/reports/play_target_api.md`; confirms `targetSdk = 35` against the June 14, 2026 official Google Play mobile submission baseline and records official Help Center/Policy source URLs. |
| Fastlane/supply Play graphics prepared | Verified Locally | `scripts/sync_fastlane_assets.py`, `scripts/fastlane_assets_qa.py`, `fastlane/metadata/android/ru-RU/images/icon.png`, `fastlane/metadata/android/ru-RU/images/featureGraphic.png`, `fastlane/metadata/android/ru-RU/images/phoneScreenshots/`. |
| Fastlane internal-track upload guard prepared | Verified Locally | `fastlane/Appfile`, `fastlane/Fastfile`, `fastlane/README.md`, `docs/fastlane_upload.md`, `scripts/fastlane_config_qa.py`; lanes require strict signing, hosted privacy URL, service-account env var, strict release-candidate packaging, validate-only preflight, internal track and draft release status. |
| Fastlane runtime readiness guard | Verified Locally | `scripts/fastlane_runtime_qa.py`, `build/reports/fastlane_runtime.md`, `scripts/play_handoff_qa.py`; local mode records Ruby/header/bundle/fastlane runtime gaps as external blockers, strict mode fails until the upload machine is ready, and the report carries detected Ruby manager/remediation commands for the upload operator. |
| External Play upload readiness tracked | Verified Locally | `Gemfile`, `Gemfile.lock`, `scripts/play_external_readiness_qa.py`, `build/reports/play_external_readiness.md`; local mode reports missing signing/service-account/privacy URL/fastlane runtime as `EXTERNAL_BLOCKER`, strict mode fails until they are ready. |
| Play upload service-account auth guard | Verified Locally | `scripts/play_upload_auth_qa.py`, `build/reports/play_upload_auth.md`, `scripts/play_handoff_qa.py`; local mode records missing `SUPPLY_JSON_KEY` as an external blocker, strict mode validates a service-account JSON outside the repository. |
| Privacy policy ready for hosting | Verified Locally | `store/privacy_policy.html`, `docs/privacy_and_permissions.md`, `scripts/privacy_policy_hosting_qa.py`, `build/reports/privacy_policy_hosting.md`, `build/privacy_policy_handoff/`, `build/play_handoff/shawarma58-v1.0.0/privacy/hosting/`; handoff QA verifies SHA-256 parity for the host-ready HTML. |
| Privacy/Data safety consistency with no-collection/no-sharing claim | Verified Locally | `scripts/privacy_data_safety_qa.py`, `build/reports/privacy_data_safety.md`, `store/play_console_answers.md`, `store/privacy_policy.html`, manifests and in-app progress reset copy. |
| Privacy policy public URL | External Blocker | Must host `privacy/hosting/privacy_policy.html` from the Play handoff at a public HTTPS URL before Play upload. |
| Data safety/content rating/target audience forms | External Blocker | Draft answers exist in `store/play_console_answers.md`; final submission requires Play Console. |
| Release signing via env vars, no keystore committed | Verified Locally | `app/build.gradle.kts`, `.gitignore`, `docs/signing_setup.md`, `scripts/prepare_upload_keystore.py`, `build/reports/upload_keystore_setup.md`, `scripts/signing_env_qa.py`, `build/reports/signing_env.md`, `scripts/workspace_hygiene_qa.py`, `build/reports/workspace_hygiene.md`, `scripts/release_gate.py`. |
| Signed production AAB | External Blocker | Requires `SHAWARMA58_KEYSTORE`, `SHAWARMA58_KEYSTORE_PASSWORD`, `SHAWARMA58_KEY_ALIAS`, `SHAWARMA58_KEY_PASSWORD`; verify with `python3 scripts/release_gate.py --strict-signing`. |
| Unit tests, lint, debug APK and release AAB build | Verified Locally | `docs/release_report.md`, `scripts/release_gate.py`, expanded `GameRulesTest.kt`, Gradle test reports and build outputs. |
| UI/instrumentation smoke: onboarding, level workload copy, correct order, serve/result feedback, wrong order, level complete, back/background/restore, settings toggles and real DataStore reset | Verified Locally | `app/src/androidTest/java/com/shawarma58/game/Shawarma58InstrumentedSmokeTest.kt`, `app/src/androidTest/java/com/shawarma58/game/ProgressStoreInstrumentedTest.kt`, `app/src/main/java/com/shawarma58/game/ui/UiTestTags.kt`, `scripts/instrumentation_smoke_qa.py`, `scripts/play_handoff_qa.py`, `build/reports/instrumentation_smoke.md`, `build/reports/instrumentation_smoke.json`; current serial-scoped run on `emulator-5586` passed 9 tests with 0 failures including `gameplayStateSurvivesActivityRecreation`, and handoff QA rejects stale/class-filtered instrumentation evidence, report/source SHA drift, or a report that does not show the full current androidTest count. |
| Accessibility source guardrails: TalkBack labels/states and 48dp+ targets | Verified Locally | `scripts/accessibility_source_qa.py`, `build/reports/accessibility_source.md`, `docs/accessibility_notes.md`, `docs/ui_audit.md`. |
| Built artifact provenance: package/version/sdk, manifest privacy, AAB structure, embedded ProGuard map and mapping outputs | Verified Locally | `scripts/artifact_provenance_qa.py`, `build/reports/artifact_provenance.md`, `build/reports/artifact_provenance.json`, `scripts/release_gate.py`. |
| R8 mapping/deobfuscation handoff | Verified Locally | `docs/deobfuscation_notes.md`, `app/build/outputs/mapping/release/`, `build/play_handoff/shawarma58-v1.0.0/deobfuscation/release/`, `scripts/play_handoff_qa.py`. |
| Transferable Play handoff archive | Verified Locally | `scripts/create_play_handoff_archive.py`, `scripts/play_handoff_qa.py`, `scripts/play_handoff_archive_qa.py --require-package-report`, `build/reports/play_handoff_qa.md`, `build/reports/play_handoff_qa.json`, `build/reports/play_handoff_archive_qa.md`, `build/reports/play_handoff_archive_qa.json`, `build/play_handoff/shawarma58-v1.0.0.zip`, `build/play_handoff/shawarma58-v1.0.0.zip.sha256`; handoff QA verifies every non-generated manifest source matches copied bytes, records copy-map coverage as local evidence, and archive QA verifies archived `manifest.json` SHA/content parity, package-report sidecars, the transfer sidecar command and manifest summary parity. |
| Handoff archive secret scan | Verified Locally | `scripts/play_handoff_secret_scan_qa.py`, `build/reports/play_handoff_secret_scan.md`; checks manifest-listed handoff files, zip entries and transfer sidecars for key-like filenames, private-key blocks and service-account credential JSON. |
| Upload-keystore setup helper and handoff evidence | Verified Locally | `scripts/prepare_upload_keystore.py`, `build/reports/upload_keystore_setup.md`, `docs/signing_setup.md`, `scripts/play_handoff_qa.py`; validates/generates upload keys outside the repo after env vars are set. |
| Upload operator runbook and handoff evidence | Verified Locally | `docs/upload_operator_runbook.md`, `scripts/upload_operator_runbook_qa.py`, `build/reports/upload_operator_runbook.md`, `build/play_handoff/shawarma58-v1.0.0/qa/upload_operator_runbook/`; handoff QA validates report status, required env vars, strict commands including post-package validation and secret-like material exclusion. |
| Workspace hygiene guard for generated caches, duplicate reports/handoff artifacts and upload secrets | Verified Locally | `scripts/workspace_hygiene_qa.py`, `build/reports/workspace_hygiene.md`, `.gitignore`, `scripts/play_handoff_qa.py`; validates cache/secret ignore rules, stale duplicate report/Play handoff artifact cleanup, handoff exclusions and workspace-contained manifest source parity. |
| One-command release candidate packaging | Verified Locally | `scripts/package_release_candidate.py`, `docs/release_candidate_package.md`, `build/reports/release_candidate_package.md`, `build/play_handoff/shawarma58-v1.0.0.zip.package.md`; package reports surface release-gate, optional instrumentation-smoke and connected-performance status/detail from the handoff manifest, supports `--strict-pre-upload` for final upload machines, then the flow reruns secret scan/freshness and post-package validation after final transfer sidecars are written. |
| Asset QA report in handoff | Verified Locally | `scripts/asset_qa.py`, `build/reports/asset.md`, `build/reports/asset.json`, `build/play_handoff/shawarma58-v1.0.0/qa/asset/`, `scripts/play_handoff_qa.py`; the report records runtime drawable, launcher icon, transparent-alpha and screenshot dimensions. |
| UI behavior report in handoff | Verified Locally | `scripts/ui_behavior_qa.py`, `build/reports/ui_behavior.md`, `build/reports/ui_behavior.json`, `build/play_handoff/shawarma58-v1.0.0/qa/ui_behavior/`, `scripts/play_handoff_qa.py`; the report records UI behavior snippets, Russian copy, tags and test coverage markers. |
| Completion audit report in handoff | Verified Locally | `scripts/completion_audit_qa.py`, `build/reports/completion_audit.md`, `build/reports/completion_audit.json`, `build/play_handoff/shawarma58-v1.0.0/qa/completion_audit/`, `scripts/play_handoff_qa.py`; the report records required-file coverage and seven completion-audit check groups. |
| Play metadata report in handoff | Verified Locally | `scripts/play_metadata_qa.py`, `build/reports/play_metadata.md`, `build/reports/play_metadata.json`, `build/play_handoff/shawarma58-v1.0.0/qa/play_metadata/`, `scripts/play_handoff_qa.py`; the report records listing lengths, privacy terms, five upload screenshots, two QA-only screenshots and feature graphic dimensions. |
| Play upload packet report in handoff | Verified Locally | `scripts/play_upload_packet_qa.py`, `build/reports/play_upload_packet.md`, `build/reports/play_upload_packet.json`, `build/play_handoff/shawarma58-v1.0.0/qa/play_upload_packet/`, `scripts/play_handoff_qa.py`; the report records metadata/screenshot coverage, manifest privacy, signed-AAB warning and strict upload command ordering. |
| Consolidated release-gate report in handoff | Verified Locally | `scripts/release_gate.py`, `build/reports/release_gate.md`, `build/reports/release_gate.json`, `build/play_handoff/shawarma58-v1.0.0/qa/release_gate/release_gate.md`, `build/play_handoff/shawarma58-v1.0.0/manifest.json`, `scripts/play_handoff_qa.py`; handoff QA verifies report source/SHA parity and `manifest.releaseGate` summary parity. |
| Release freshness and post-package guards | Verified Locally | `scripts/release_freshness_qa.py`, `scripts/post_package_validation_qa.py`, `build/reports/release_freshness.md`, `build/reports/post_package_validation.md`, `scripts/package_release_candidate.py`; includes `build/reports/release_gate.json`, `build/reports/play_metadata.json`, `build/reports/release_candidate_package.json`, mandatory handoff QA JSON coverage/freshness, package status parity, exact transfer file/directory set, final secret-scan handoff/archive/sidecar coverage counts, post-package report timing after final scan/freshness, package JSON/markdown sidecar parity, package markdown status/SHA/verify-command content, exact archive checksum sidecar text, archive/package `manifestSha256` parity, unpacked handoff directory file/SHA/byte parity against `manifest.files`, local handoff/archive QA report status/count parity, final sidecar-scan/freshness ordering, final transfer sidecar scope, local-only post-package report placement, no sidecar rewrite after final scan and handoff `qa/release_gate/release_gate.json` plus `qa/play_metadata/play_metadata.json`. |
| Automatic release-date sync for package day | Verified Locally | `scripts/update_release_dates.py`, `build/reports/release_dates.md`, `scripts/package_release_candidate.py`. |
| Performance/dependency budget: no heavy SDKs, optimized resources and small release artifacts | Verified Locally | `scripts/performance_budget_qa.py`, `build/reports/performance_budget.md`, `build/reports/performance_budget.json`, `docs/performance_notes.md`. |
| Connected performance diagnostic: memory/crash evidence on emulator | Verified Locally | `scripts/connected_performance_qa.py`, `scripts/create_play_handoff.py`, `scripts/play_handoff_qa.py`, `build/reports/connected_performance.md`, `build/reports/connected_performance.json`, latest passing evidence in `build/performance_connected/20260614-124355/summary.md`; handoff QA rejects stale connected-performance evidence, verifies report source/SHA parity with `build/reports`, verifies raw artifact copies under `qa/connected_performance/artifacts/` when included, and requires `manifest.optionalEvidence.connectedPerformance` plus matching `NEXT_ACTIONS.md` status/detail/refresh copy when evidence is skipped or missing. |
| Connected smoke include/skip state | Verified Locally | `scripts/create_play_handoff.py`, `scripts/play_handoff_qa.py`, `scripts/android_smoke_qa.py`; fresh passing connected smoke is copied under `qa/android_smoke/latest/`, handoff QA verifies source/SHA parity against the latest passing `build/android_smoke/` directory, and stale or missing smoke records `manifest.connectedSmoke.status` plus a `NEXT_ACTIONS.md` refresh command instead of shipping stale evidence. |
| UI/emulator smoke and visual QA | Verified Locally | `docs/qa_test_plan.md`, `docs/android_emulator_smoke.md`, `docs/ui_audit.md`, screenshots in `store/screenshots/`, configuration-change restore source/JVM coverage, latest extended connected evidence in `build/android_smoke/20260614-124352/summary.md`, and latest full seven-screen store capture evidence in `build/store_screenshot_capture/20260614-124029/summary.md`. |
| Consolidated pre-upload blocker summary for the Play operator | Verified Locally | `scripts/pre_upload_blockers_qa.py`, `build/reports/pre_upload_blockers.md`, `build/play_handoff/shawarma58-v1.0.0/qa/pre_upload_blockers/pre_upload_blockers.md`; groups signing, privacy URL, service-account, fastlane runtime and physical-device actions. |
| Real physical-device sanity pass | Manual Final Check | Checklist exists in `docs/physical_device_sanity.md`; `scripts/physical_device_readiness_qa.py` writes readiness evidence and reports emulator-only local state as an external blocker until a real Android phone is connected. |
| Performance/release size notes | Verified Locally | `docs/performance_notes.md`, WebP runtime assets, R8/resource shrink in `app/build.gradle.kts`. |
| Accessibility notes | Verified Locally | `docs/accessibility_notes.md`, `docs/ui_audit.md`. |
| No ads/IAP/accounts/backend in v1 | Intentional Non-goal | `docs/product_decision.md`, `docs/privacy_and_permissions.md`, no related dependencies/permissions. |

## Local gate evidence
The local release gate is `python3 scripts/release_gate.py`. It runs asset QA, UI behavior QA with `build/reports/ui_behavior.md`/JSON evidence, accessibility source QA, Play metadata QA with `build/reports/play_metadata.md`/JSON evidence, Play target API QA, store visual quality QA, store screenshot freshness QA, fastlane asset sync/QA, fastlane config QA, Fastlane runtime QA, Play upload packet QA, privacy/data-safety QA, Play upload auth QA, privacy policy hosting QA, completion audit QA with `build/reports/completion_audit.md`/JSON evidence, Play external readiness QA, signing environment QA, upload keystore setup QA, upload operator runbook QA, workspace hygiene QA, Gradle tests/lint/builds including `assembleDebugAndroidTest`, artifact provenance QA, performance budget QA, pre-upload blocker summary QA, manifest privacy invariants, release minify/resource-shrink checks, artifact checks and AAB signing verification, then writes `build/reports/release_gate.md` and `build/reports/release_gate.json`. When an emulator/device is connected, `python3 scripts/release_gate.py --connected-tests --serial <adb-serial>` also runs `python3 scripts/instrumentation_smoke_qa.py --serial <adb-serial> --require-device`; `python3 scripts/release_gate.py --connected-performance --serial <adb-serial>` also runs `python3 scripts/connected_performance_qa.py --serial <adb-serial>`.

Expected local result without signing env vars: all local checks pass and AAB signing is reported as `EXTERNAL_BLOCKER`.

Strict production command:

```bash
python3 scripts/release_gate.py --strict-signing
```

## External blockers
1. Configure upload signing outside the repository and export `SHAWARMA58_KEYSTORE`, `SHAWARMA58_KEYSTORE_PASSWORD`, `SHAWARMA58_KEY_ALIAS`, `SHAWARMA58_KEY_PASSWORD`.
2. Host `store/privacy_policy.html` at a public non-PDF HTTPS URL and export `SHAWARMA58_PRIVACY_POLICY_URL`.
3. Complete Play Console setup and provide `SUPPLY_JSON_KEY` outside the repository for guarded fastlane upload.
4. Prepare the upload machine Ruby/Fastlane runtime with matching native headers and `bundle install --path vendor/bundle`.
5. Run `docs/physical_device_sanity.md` on a real Android phone before production rollout.

## Handoff checklist
1. Run `python3 scripts/completion_audit_qa.py`.
2. Run `python3 scripts/play_upload_packet_qa.py`.
3. Run `python3 scripts/asset_manifest_qa.py`.
4. Run `python3 scripts/content_copy_qa.py`.
5. Run `python3 scripts/accessibility_source_qa.py`.
6. Run `python3 scripts/store_visual_quality_qa.py`.
7. Run `python3 scripts/store_screenshot_freshness_qa.py`.
8. Run `python3 scripts/store_screenshot_capture_qa.py`.
9. Run `python3 scripts/sync_fastlane_assets.py`.
10. Run `python3 scripts/fastlane_assets_qa.py`.
11. Run `python3 scripts/fastlane_config_qa.py`.
12. Run `python3 scripts/play_external_readiness_qa.py`.
13. Run `python3 scripts/play_console_forms_qa.py`.
14. Run `python3 scripts/privacy_data_safety_qa.py`.
15. Run `python3 scripts/play_upload_auth_qa.py`.
16. Run `python3 scripts/privacy_policy_hosting_qa.py`.
17. Run `python3 scripts/fastlane_runtime_qa.py`.
18. Run `python3 scripts/artifact_provenance_qa.py`.
19. Run `python3 scripts/signing_env_qa.py`.
20. Run `python3 scripts/prepare_upload_keystore.py`.
21. Run `python3 scripts/upload_operator_runbook_qa.py`.
22. Run `python3 scripts/workspace_hygiene_qa.py`.
23. Run `python3 scripts/performance_budget_qa.py`.
24. Run `python3 scripts/physical_device_readiness_qa.py`.
25. Run `python3 scripts/pre_upload_blockers_qa.py`.
26. Run `python3 scripts/instrumentation_smoke_qa.py --require-device` on a booted emulator/device.
27. Run `python3 scripts/connected_performance_qa.py --serial <adb-serial>`.
28. Run `python3 scripts/update_release_dates.py`.
29. Run `python3 scripts/release_gate.py`.
30. Run `python3 scripts/package_release_candidate.py`.
31. Run `python3 scripts/release_freshness_qa.py`.
32. Run `python3 scripts/post_package_validation_qa.py`.
33. Run `python3 scripts/create_play_handoff.py`.
34. Run `python3 scripts/play_handoff_qa.py`.
35. Run `python3 scripts/create_play_handoff_archive.py`.
36. Run `python3 scripts/play_handoff_archive_qa.py`.
37. Run `python3 scripts/play_handoff_secret_scan_qa.py`.
38. Run `python3 scripts/android_smoke_qa.py --serial <adb-serial>` and `python3 scripts/android_smoke_qa.py --serial <adb-serial> --extended` on a booted emulator/device.
39. In the signing environment, run `python3 scripts/prepare_upload_keystore.py --strict`.
40. In the signing environment, run `python3 scripts/signing_env_qa.py --strict`.
41. In the signing environment, run `python3 scripts/play_upload_auth_qa.py --strict`.
42. In the signing environment, run `python3 scripts/privacy_policy_hosting_qa.py --strict --fetch-privacy-url`.
43. In the signing environment, run `python3 scripts/fastlane_runtime_qa.py --strict`.
44. In the signing environment, run `python3 scripts/upload_operator_runbook_qa.py`.
45. In the signing environment, run `python3 scripts/play_external_readiness_qa.py --strict --fetch-privacy-url`.
46. In the signing environment, run `python3 scripts/physical_device_readiness_qa.py --strict`.
47. In the signing environment, run `python3 scripts/pre_upload_blockers_qa.py --strict`.
48. In the signing environment, run `python3 scripts/release_gate.py --strict-signing --fetch-privacy-url --strict-screenshots --strict-physical-device --strict-pre-upload`.
49. In the signing environment, run `python3 scripts/package_release_candidate.py --strict-signing --fetch-privacy-url --fetch-target-api-policy --strict-screenshots --strict-physical-device --strict-pre-upload`.
50. In the signing environment, run `python3 scripts/post_package_validation_qa.py`.
51. Optional fastlane validation: `bundle exec fastlane android validate_internal`.
52. Upload the signed AAB plus curated screenshots from `fastlane/metadata/android/ru-RU/images` or manual copies from `store/screenshots/`; optional lane: `bundle exec fastlane android upload_internal`.
53. Keep `app/build/outputs/mapping/release/` for crash deobfuscation after release.
