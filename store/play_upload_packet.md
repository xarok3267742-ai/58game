# Play Upload Packet

Date: June 14, 2026.

Use this packet for the first Google Play internal-test upload of "Шаурма 58". All paths are relative to the project root.

## Release identity
| Field | Value |
|---|---|
| App name | `Шаурма 58` |
| Package name | `com.andrejivliev.shawarma58` |
| Version code | `1` |
| Version name | `1.0.0` |
| Default language | `ru-RU` |
| App type | Game |
| Category | Casual |
| Price | Free |
| Ads | No |
| In-app purchases | No |

## Build artifact
Upload only a signed release AAB:

```text
app/build/outputs/bundle/release/app-release.aab
```

The current local AAB is allowed to be unsigned during local QA. Do not upload an unsigned AAB to Play Console.

Before Play upload, configure:

```bash
export SHAWARMA58_KEYSTORE=/absolute/path/shawarma58-upload.jks
export SHAWARMA58_KEYSTORE_PASSWORD=...
export SHAWARMA58_KEY_ALIAS=...
export SHAWARMA58_KEY_PASSWORD=...
python3 scripts/signing_env_qa.py --strict
python3 scripts/prepare_upload_keystore.py --strict
python3 scripts/upload_operator_runbook_qa.py
python3 scripts/workspace_hygiene_qa.py
python3 scripts/release_gate.py --strict-signing
python3 scripts/asset_manifest_qa.py
python3 scripts/content_copy_qa.py
python3 scripts/accessibility_source_qa.py
python3 scripts/privacy_data_safety_qa.py
python3 scripts/play_upload_auth_qa.py
python3 scripts/privacy_policy_hosting_qa.py
python3 scripts/fastlane_runtime_qa.py
python3 scripts/artifact_provenance_qa.py --strict-signing
python3 scripts/performance_budget_qa.py
python3 scripts/physical_device_readiness_qa.py
python3 scripts/prepare_upload_keystore.py
python3 scripts/pre_upload_blockers_qa.py --strict
python3 scripts/instrumentation_smoke_qa.py --require-device
python3 scripts/connected_performance_qa.py --serial <adb-serial>
shasum -a 256 app/build/outputs/bundle/release/app-release.aab
```

Keep the generated checksum with the release notes outside the repo or in the release management system.

## Deobfuscation mapping
Keep R8 mapping outputs with the uploaded AAB:

```text
app/build/outputs/mapping/release/
```

The generated handoff copies these files under:

```text
deobfuscation/release/
```

Use `docs/deobfuscation_notes.md` for handling notes. These files are internal release artifacts, not store graphics.

## Store listing files
| Play Console field | Source file | Limit |
|---|---|---:|
| App name | `fastlane/metadata/android/ru-RU/title.txt` | 30 chars |
| Short description | `fastlane/metadata/android/ru-RU/short_description.txt` | 80 chars |
| Full description | `fastlane/metadata/android/ru-RU/full_description.txt` | 4000 chars |
| Release notes | `fastlane/metadata/android/ru-RU/changelogs/1.txt` | 500 chars |

Copy/paste listing draft:

```text
store/play_listing_ru.md
```

## Fastlane/supply assets
Before using automated upload tooling, sync the curated store graphics into the fastlane metadata layout:

```bash
python3 scripts/asset_manifest_qa.py
python3 scripts/sync_fastlane_assets.py
python3 scripts/fastlane_assets_qa.py
python3 scripts/store_visual_quality_qa.py
python3 scripts/store_screenshot_freshness_qa.py
python3 scripts/store_screenshot_capture_qa.py
python3 scripts/play_console_forms_qa.py
python3 scripts/play_upload_auth_qa.py
python3 scripts/privacy_policy_hosting_qa.py
python3 scripts/fastlane_runtime_qa.py
python3 scripts/play_external_readiness_qa.py
python3 scripts/workspace_hygiene_qa.py
```

The generated Play graphics layout is:

```text
fastlane/metadata/android/ru-RU/images/icon.png
fastlane/metadata/android/ru-RU/images/featureGraphic.png
fastlane/metadata/android/ru-RU/images/phoneScreenshots/
```

Guarded fastlane config is prepared in `fastlane/Appfile` and `fastlane/Fastfile`. Validate it locally:

```bash
python3 scripts/fastlane_config_qa.py
```

Remote fastlane validation requires a Play service-account JSON and a hosted privacy-policy URL:

```bash
export SUPPLY_JSON_KEY=/absolute/path/google-play-service-account.json
export SHAWARMA58_PRIVACY_POLICY_URL=https://example.com/shawarma58/privacy
bundle install --path vendor/bundle
python3 scripts/prepare_upload_keystore.py --strict
python3 scripts/play_upload_auth_qa.py --strict
python3 scripts/fastlane_runtime_qa.py --strict
python3 scripts/upload_operator_runbook_qa.py
python3 scripts/pre_upload_blockers_qa.py --strict
python3 scripts/package_release_candidate.py --strict-signing --fetch-privacy-url --fetch-target-api-policy --strict-screenshots --strict-physical-device --strict-pre-upload
python3 scripts/workspace_hygiene_qa.py
python3 scripts/play_handoff_secret_scan_qa.py
python3 scripts/release_freshness_qa.py
python3 scripts/post_package_validation_qa.py
bundle exec fastlane android validate_internal
```

Use `docs/upload_operator_runbook.md` as the final upload-machine checklist. Use the checked-in `Gemfile.lock` for reproducible fastlane dependencies. The upload machine must use a Ruby runtime with native extension headers available; `python3 scripts/pre_upload_blockers_qa.py --strict` runs before packaging, and `python3 scripts/package_release_candidate.py --strict-signing --fetch-privacy-url --fetch-target-api-policy --strict-screenshots --strict-physical-device --strict-pre-upload` runs the strict release gate, official target API refresh, external readiness checks, upload operator runbook QA, handoff archive QA, secret scan, freshness guard and post-package validation before fastlane upload. The fastlane lanes repeat this package flow before contacting Google Play.

Only after validate-only succeeds and Play Console forms are ready:

```bash
bundle exec fastlane android upload_internal
```

## Graphics
| Asset | File | Required size |
|---|---|---:|
| Play app icon | `store/play_icon.png` | 512x512 |
| Feature graphic | `store/feature_graphic_concept.png` | 1024x500 |
| Android launcher icon | `app/src/main/res/mipmap-*` | 48-192px fallback |

Upload screenshots in this order:

1. `fastlane/metadata/android/ru-RU/images/phoneScreenshots/01_onboarding.png`
2. `fastlane/metadata/android/ru-RU/images/phoneScreenshots/02_menu.png`
3. `fastlane/metadata/android/ru-RU/images/phoneScreenshots/03_levels.png`
4. `fastlane/metadata/android/ru-RU/images/phoneScreenshots/04_gameplay.png`
5. `fastlane/metadata/android/ru-RU/images/phoneScreenshots/05_result.png`

The source captures are kept in `store/screenshots/` as real emulator screenshot evidence. The fastlane copies are RGB PNGs prepared for Play upload.

Keep these screenshots as QA evidence unless Play requests more:

- `store/screenshots/shawarma_wrong_order.png`
- `store/screenshots/shawarma_endless_result.png`

Before final upload, run:

```bash
python3 scripts/store_screenshot_freshness_qa.py --strict
```

If this fails, re-capture real screenshots from the current APK and rerun `python3 scripts/sync_fastlane_assets.py`.
After recapture, run `python3 scripts/store_screenshot_capture_qa.py` to verify the current store screenshots match the latest real app capture evidence by SHA-256.

## Privacy and policy
Host this file at a public, non-geofenced, non-PDF HTTPS URL:

```text
store/privacy_policy.html
```

The host-ready copy and checksum are generated under:

```text
build/privacy_policy_handoff/
build/play_handoff/shawarma58-v1.0.0/privacy/hosting/
```

Paste the hosted URL into Play Console. For the release handoff, host `privacy/hosting/privacy_policy.html` from `build/play_handoff/shawarma58-v1.0.0` and verify its SHA-256 against `privacy/hosting/manifest.json`.
After hosting, export `SHAWARMA58_PRIVACY_POLICY_URL` and run:

```bash
python3 scripts/privacy_policy_hosting_qa.py --strict --fetch-privacy-url
python3 scripts/play_external_readiness_qa.py --strict --fetch-privacy-url
```

Use the prepared answer sheet for Play Console:

```text
store/play_console_answers.md
```

Validate the answer sheet before copying it into Play Console:

```bash
python3 scripts/play_console_forms_qa.py
```

Required policy answers for v1:
- Data collected: No.
- Data shared: No.
- Data deletion: local progress can be reset in app settings; there is no server account data.
- Internet permission: absent.
- Dangerous permissions: none.
- Ads: No.
- Accounts/login: No.
- Payments/IAP: No.
- User-generated content: No.
- Target audience: not specifically directed at children; recommended age groups 13-15, 16-17, 18+.

## Pre-upload gate
Run in the final signing environment:

```bash
python3 scripts/pre_upload_blockers_qa.py --strict
python3 scripts/package_release_candidate.py --strict-signing --fetch-privacy-url --fetch-target-api-policy --strict-screenshots --strict-physical-device --strict-pre-upload
python3 scripts/prepare_upload_keystore.py --strict
python3 scripts/play_upload_auth_qa.py --strict
python3 scripts/privacy_policy_hosting_qa.py --strict --fetch-privacy-url
python3 scripts/fastlane_runtime_qa.py --strict
python3 scripts/upload_operator_runbook_qa.py
python3 scripts/play_handoff_secret_scan_qa.py
python3 scripts/release_freshness_qa.py
python3 scripts/post_package_validation_qa.py
python3 scripts/release_gate.py --strict-signing --fetch-target-api-policy --strict-screenshots --strict-physical-device --connected-tests --connected-performance --serial <adb-serial>
python3 scripts/workspace_hygiene_qa.py
python3 scripts/physical_device_readiness_qa.py --strict
python3 scripts/instrumentation_smoke_qa.py --require-device
python3 scripts/connected_performance_qa.py --serial <adb-serial>
```

Expected result: every blocking check passes, including AAB signing, artifact provenance, performance budget, connected instrumentation smoke and connected performance memory/crash checks. Frame metrics in connected performance can be `WARN` on emulators when sample size is tiny; `FAIL` is blocking.

## Local handoff bundle
After a passing local gate, build a copy-only handoff directory for the Play Console operator:

```bash
python3 scripts/update_release_dates.py
python3 scripts/package_release_candidate.py
python3 scripts/play_handoff_secret_scan_qa.py
python3 scripts/release_freshness_qa.py
```

The directory is created under `build/play_handoff/shawarma58-v1.0.0` and includes metadata, fastlane/supply config and image layout, screenshots, feature graphic, privacy HTML plus the checksumed `privacy/hosting/` publish bundle, Play Console answers, QA docs, APK/AAB copies, R8 deobfuscation mapping outputs, release-gate reports, asset manifest/rejected asset docs and reports, content copy reports, accessibility source reports, fastlane asset/config/runtime reports, store visual quality/freshness/capture-provenance reports, Play upload auth reports, privacy policy hosting reports, Play external readiness reports, upload keystore setup reports, upload operator runbook reports, workspace hygiene reports, artifact provenance reports, performance budget reports, physical-device readiness reports, pre-upload blocker summary reports, connected performance reports and raw artifacts when available, instrumentation smoke reports when available, latest passing connected-smoke evidence when available and `manifest.json` with checksums. The package flow also writes `build/reports/play_handoff_secret_scan.md` after checking manifest-listed handoff files and zip entries for key files, private-key blocks and service-account credential JSON. In the final signing environment, use:

```bash
python3 scripts/create_play_handoff.py --strict-signing --fetch-privacy-url
```

Only use the handoff AAB for upload when `manifest.json` reports `signing.status = signed`.

The archive is created as:

```text
build/play_handoff/shawarma58-v1.0.0.zip
build/play_handoff/shawarma58-v1.0.0.zip.sha256
build/play_handoff/shawarma58-v1.0.0.zip.package.md
```

The zip contains the handoff `manifest.files` set plus `manifest.json`.

Use the `.sha256` sidecar to verify transfer integrity before upload or handoff:

```bash
cd build/play_handoff && shasum -a 256 -c shawarma58-v1.0.0.zip.sha256
```

The package command writes an operator summary to:

```text
build/reports/release_candidate_package.md
build/reports/release_dates.md
build/reports/release_gate.md
build/reports/release_freshness.md
build/reports/asset_manifest.md
build/reports/content_copy.md
build/reports/store_screenshot_freshness.md
build/reports/store_screenshot_capture.md
build/reports/physical_device_readiness.md
build/reports/play_upload_auth.md
build/reports/privacy_policy_hosting.md
build/reports/fastlane_runtime.md
build/reports/upload_keystore_setup.md
build/reports/upload_operator_runbook.md
build/reports/pre_upload_blockers.md
build/reports/workspace_hygiene.md
build/reports/play_handoff_secret_scan.md
```

## First rollout
1. Create the app in Play Console with package `com.andrejivliev.shawarma58`.
2. Fill the store listing from `fastlane/metadata/android/ru-RU`.
3. Prepare upload signing, `SUPPLY_JSON_KEY`, `SHAWARMA58_PRIVACY_POLICY_URL` and the upload-machine Fastlane runtime outside the repository.
4. Follow `docs/upload_operator_runbook.md` and run `python3 scripts/upload_operator_runbook_qa.py`.
5. Run `python3 scripts/pre_upload_blockers_qa.py --strict`, then `python3 scripts/package_release_candidate.py --strict-signing --fetch-privacy-url --fetch-target-api-policy --strict-screenshots --strict-physical-device --strict-pre-upload`, then `python3 scripts/post_package_validation_qa.py`.
6. Upload the signed AAB to internal testing, either manually or with `bundle exec fastlane android upload_internal`.
7. Upload the curated screenshots and feature graphic manually if fastlane is not used.
8. Paste the hosted privacy policy URL.
9. Complete Data safety, content rating, target audience and app-access forms from `store/play_console_answers.md`.
10. Run connected emulator smoke with `python3 scripts/android_smoke_qa.py --serial <adb-serial>` and `python3 scripts/android_smoke_qa.py --serial <adb-serial> --extended`.
11. Run Play pre-review checks.
12. Test the internal track build on a real device with `docs/physical_device_sanity.md`.
13. Move to closed testing or staged production only after the internal build passes.
