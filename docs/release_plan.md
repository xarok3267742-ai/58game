# Release Plan

## v1.0.0 candidate
1. Run unit tests, lint, debug build and release bundle.
2. Install debug APK on emulator/device and complete manual smoke plan.
3. Capture real screenshots from the running app.
4. Review adaptive icon at launcher sizes.
5. Replace feature graphic if final Play Console preview marks it below release quality.
6. Configure upload signing through Play Console and local env vars.
7. Upload `.aab` to internal testing.
8. Fix Play pre-review findings before production rollout.

## Current status
- Steps 1-3 are complete for the release candidate.
- Step 4 has a local launcher preview at `store/launcher_icon_preview.png`; final Play Console preview remains manual.
- Step 5 is complete for the current ImageGen feature graphic candidate.
- Store listing metadata, Data safety draft and privacy policy HTML are prepared locally.
- Asset manifest/rejected asset coverage is checked with `python3 scripts/asset_manifest_qa.py`; rejected variants must stay outside release asset paths.
- Play Console form coverage is checked with `python3 scripts/play_console_forms_qa.py` for app details, app access, Data safety, content rating, other declarations, target audience and release path.
- Accessibility source guardrails are checked with `python3 scripts/accessibility_source_qa.py`; custom controls keep TalkBack labels/states and 48dp+ tap targets.
- Final visible/app/store/privacy copy is checked with `python3 scripts/content_copy_qa.py`; it guards required Russian microcopy and placeholder/dev wording.
- Google Play target API readiness is checked with `python3 scripts/play_target_api_qa.py`; run `python3 scripts/play_target_api_qa.py --fetch-policy` when refreshing official Help Center/Policy evidence before final upload.
- Fastlane/supply image layout is generated and checked with `python3 scripts/sync_fastlane_assets.py` and `python3 scripts/fastlane_assets_qa.py`.
- Store screenshot/feature visual quality is checked with `python3 scripts/store_visual_quality_qa.py`; upload screenshots must remain readable and distinct.
- Store screenshot freshness is checked with `python3 scripts/store_screenshot_freshness_qa.py`; final fastlane/upload packaging must pass `--strict-screenshots` after screenshots are recaptured from the current APK.
- Store screenshot capture provenance is checked with `python3 scripts/store_screenshot_capture_qa.py`; it verifies the latest passing real capture evidence and SHA parity with current store screenshots.
- Store screenshot recapture is automated with `python3 scripts/capture_store_screenshots.py --serial <adb-serial>` when a 1080x2400 emulator/device is available. The helper validates each candidate screencap for size, file weight, contrast and color variety before replacing `store/screenshots/`, so black/headless captures cannot overwrite curated store assets. If the local AVD shuts down during a split real-capture session, `python3 scripts/capture_store_screenshots.py --combine-from-store` can create one full evidence directory only after every `store/screenshots/` PNG was produced by real app screencaps and passes the same candidate checks.
- Fastlane validate/upload config is prepared and checked with `python3 scripts/fastlane_config_qa.py`; lanes are limited to internal track and draft release status, run the strict release candidate package flow before contacting Google Play, and `Gemfile.lock` pins fastlane 2.230.0.
- Play upload auth readiness is checked with `python3 scripts/play_upload_auth_qa.py`; strict mode verifies `SUPPLY_JSON_KEY` points to a service-account JSON outside the repository.
- Fastlane runtime readiness is checked with `python3 scripts/fastlane_runtime_qa.py`; strict mode verifies Ruby headers, `bundle check` and `bundle exec fastlane --version`.
- External Play upload readiness is tracked with `python3 scripts/play_external_readiness_qa.py`; strict mode verifies signing env, service-account JSON, hosted privacy URL and the shared Gemfile/Ruby/Bundler/vendor bundle/Fastlane runtime checks.
- Privacy policy hosting readiness is checked with `python3 scripts/privacy_policy_hosting_qa.py`; it validates static host-ready HTML, writes the checksumed `privacy/hosting/` publish bundle into the Play handoff and strict mode fetches `SHAWARMA58_PRIVACY_POLICY_URL`.
- Play Console upload packet is prepared at `store/play_upload_packet.md`.
- `python3 scripts/update_release_dates.py` updates release-facing document dates before packaging.
- `python3 scripts/release_freshness_qa.py` validates current release-document dates, generated report dates, package status derivation/sidecar parity, archive checksum sidecars and included optional evidence report status/date; `python3 scripts/play_handoff_qa.py` also verifies included optional report source/SHA parity against `build/reports`.
- `python3 scripts/play_handoff_secret_scan_qa.py` checks the generated handoff directory and zip for secret-like files, private-key blocks and service-account credential JSON before transfer.
- `python3 scripts/post_package_validation_qa.py` validates the final post-sidecar state after packaging: transfer sidecars exist and were scanned, final freshness is newer than the scan, archive/package checksum and manifest SHA values match, no sidecar rewrite happens after the final scan and the post-package report stays outside the transfer package.
- `docs/completion_audit.md` records the original plan against current evidence and external blockers.
- `python3 scripts/signing_env_qa.py` validates signing env guardrails and writes `build/reports/signing_env.md`.
- `python3 scripts/prepare_upload_keystore.py` validates upload-key setup and can generate the upload keystore outside this repository with `--generate` after `SHAWARMA58_KEYSTORE*` env vars are set.
- `python3 scripts/upload_operator_runbook_qa.py` validates `docs/upload_operator_runbook.md`, which is the final upload-machine checklist for signing, Play auth, privacy URL, physical-device sanity, strict packaging and fastlane validation.
- `python3 scripts/privacy_data_safety_qa.py` validates no-permission/no-data/no-sharing policy consistency and writes `build/reports/privacy_data_safety.md`.
- `python3 scripts/artifact_provenance_qa.py` validates the current APK/AAB/mapping outputs and writes `build/reports/artifact_provenance.md`.
- `python3 scripts/create_play_handoff.py` copies R8 mapping outputs to `deobfuscation/release/`; `python3 scripts/play_handoff_qa.py` verifies SHA-256 parity with current Gradle outputs.
- `python3 scripts/performance_budget_qa.py` validates artifact/resource/dependency budgets and writes `build/reports/performance_budget.md`.
- `python3 scripts/physical_device_readiness_qa.py` records whether a non-emulator Android phone is connected for the required final physical-device sanity pass.
- `python3 scripts/pre_upload_blockers_qa.py` consolidates upload signing, hosted privacy URL, Play service-account, fastlane runtime and physical-device blockers into `build/reports/pre_upload_blockers.md`.
- `python3 scripts/instrumentation_smoke_qa.py --require-device` validates Compose UI flows with serial-scoped `adb am instrument` and writes `build/reports/instrumentation_smoke.md`.
- `python3 scripts/connected_performance_qa.py --serial <adb-serial>` captures serial-scoped emulator memory/frame/crash diagnostics and writes `build/reports/connected_performance.md`; the Play handoff copies report files plus raw performance artifacts when included, and handoff QA checks source/SHA parity.
- `python3 scripts/release_gate.py` passes all local checks, verifies the Play upload packet, completion audit, fastlane config, external Play readiness report, artifact provenance, release minify/resource shrinking, writes `build/reports/release_gate.md`/JSON and reports signing as an external blocker until upload key env vars are set.
- `python3 scripts/release_gate.py` also regenerates and verifies `fastlane/metadata/android/ru-RU/images`.
- Steps 4 and 6-8 remain manual Play Console / device tasks.

## Local Gate
Run before every release candidate handoff:

```bash
python3 scripts/update_release_dates.py
python3 scripts/release_gate.py
python3 scripts/package_release_candidate.py
python3 scripts/release_freshness_qa.py
python3 scripts/post_package_validation_qa.py
python3 scripts/asset_manifest_qa.py
python3 scripts/accessibility_source_qa.py
python3 scripts/content_copy_qa.py
python3 scripts/sync_fastlane_assets.py
python3 scripts/fastlane_assets_qa.py
python3 scripts/store_visual_quality_qa.py
python3 scripts/store_screenshot_freshness_qa.py
python3 scripts/store_screenshot_capture_qa.py
python3 scripts/fastlane_config_qa.py
python3 scripts/play_console_forms_qa.py
python3 scripts/play_upload_auth_qa.py
python3 scripts/privacy_policy_hosting_qa.py
python3 scripts/fastlane_runtime_qa.py
python3 scripts/play_external_readiness_qa.py
python3 scripts/privacy_data_safety_qa.py
python3 scripts/signing_env_qa.py
python3 scripts/prepare_upload_keystore.py
python3 scripts/upload_operator_runbook_qa.py
python3 scripts/artifact_provenance_qa.py
python3 scripts/performance_budget_qa.py
python3 scripts/physical_device_readiness_qa.py
python3 scripts/pre_upload_blockers_qa.py
python3 scripts/instrumentation_smoke_qa.py --require-device
python3 scripts/connected_performance_qa.py --serial <adb-serial>
python3 scripts/capture_store_screenshots.py --serial <adb-serial>
python3 scripts/capture_store_screenshots.py --combine-from-store
python3 scripts/create_play_handoff.py
python3 scripts/play_handoff_qa.py
python3 scripts/create_play_handoff_archive.py
python3 scripts/play_handoff_archive_qa.py
python3 scripts/play_handoff_secret_scan_qa.py
python3 scripts/android_smoke_qa.py --serial <adb-serial>
python3 scripts/android_smoke_qa.py --serial <adb-serial> --extended
```

Run in the production signing environment:

```bash
python3 scripts/release_gate.py --strict-signing --fetch-target-api-policy --strict-screenshots --strict-physical-device --strict-pre-upload
python3 scripts/prepare_upload_keystore.py --strict
python3 scripts/signing_env_qa.py --strict
python3 scripts/play_upload_auth_qa.py --strict
python3 scripts/privacy_policy_hosting_qa.py --strict --fetch-privacy-url
python3 scripts/fastlane_runtime_qa.py --strict
python3 scripts/upload_operator_runbook_qa.py
python3 scripts/play_external_readiness_qa.py --strict --fetch-privacy-url
python3 scripts/physical_device_readiness_qa.py --strict
python3 scripts/pre_upload_blockers_qa.py --strict
python3 scripts/package_release_candidate.py --strict-signing --fetch-privacy-url --fetch-target-api-policy --strict-screenshots --strict-physical-device --strict-pre-upload
python3 scripts/release_gate.py --strict-signing --fetch-target-api-policy --strict-screenshots --strict-physical-device --strict-pre-upload --connected-tests --connected-performance --serial <adb-serial>
python3 scripts/play_handoff_secret_scan_qa.py
python3 scripts/release_freshness_qa.py
python3 scripts/post_package_validation_qa.py
bundle install --path vendor/bundle
bundle exec fastlane android validate_internal
```

## Rollout
Start with internal testing, then closed testing if required by account status, then staged production rollout.

## Rollback
If v1.0.0 has a blocker, halt rollout in Play Console and upload a fixed higher `versionCode`.
