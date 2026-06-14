# Release Candidate Package

Date: June 14, 2026.

Use this command as the normal local packaging path after code, asset, metadata or build changes:

```bash
python3 scripts/package_release_candidate.py
```

It runs, in order:
1. `python3 scripts/update_release_dates.py`
2. `python3 scripts/release_gate.py`
3. `python3 scripts/create_play_handoff.py`
4. `python3 scripts/play_handoff_qa.py`
5. `python3 scripts/create_play_handoff_archive.py`
6. `python3 scripts/play_handoff_archive_qa.py --require-package-report`
7. `python3 scripts/play_handoff_secret_scan_qa.py`
8. `python3 scripts/release_freshness_qa.py`
9. `python3 scripts/play_handoff_secret_scan_qa.py` again after final package sidecars are written
10. `python3 scripts/release_freshness_qa.py` again after the final sidecar scan
11. `python3 scripts/post_package_validation_qa.py`

The first step updates release-facing document dates to the current local date. The release gate includes `python3 scripts/asset_qa.py`, `python3 scripts/asset_manifest_qa.py`, `python3 scripts/content_copy_qa.py`, `python3 scripts/play_metadata_qa.py`, `python3 scripts/ui_behavior_qa.py`, `python3 scripts/completion_audit_qa.py`, `python3 scripts/store_visual_quality_qa.py`, `python3 scripts/store_screenshot_capture_guard_qa.py`, `python3 scripts/store_screenshot_freshness_qa.py`, `python3 scripts/store_screenshot_capture_qa.py`, `python3 scripts/play_console_forms_qa.py`, `python3 scripts/play_upload_auth_qa.py`, `python3 scripts/privacy_policy_hosting_qa.py`, `python3 scripts/fastlane_runtime_qa.py`, `python3 scripts/prepare_upload_keystore.py`, `python3 scripts/upload_operator_runbook_qa.py`, `python3 scripts/workspace_hygiene_qa.py` and `python3 scripts/pre_upload_blockers_qa.py`; screenshot checks verify candidate-screencap rejection, current PNG freshness and real capture evidence freshness against tracked UI/resource source, then `build/reports/release_gate.md` and JSON summarize the full gate. The package JSON carries a top-level `status` plus `releaseGate.status`, and the handoff manifest carries a compact `releaseGate` summary, so automation can distinguish local `EXTERNAL_BLOCKER` handoffs from fully signed/upload-ready packages without parsing markdown. The handoff includes root `CHECKSUMS.txt`, `privacy/hosting/`, `docs/upload_operator_runbook.md`, `qa/release_gate/`, `qa/asset/`, `qa/ui_behavior/`, `qa/completion_audit/`, `qa/asset_manifest/`, `qa/content_copy/`, `qa/play_metadata/`, `qa/store_visual_quality/`, `qa/store_screenshot_capture_guard/`, `qa/store_screenshot_freshness/`, `qa/store_screenshot_capture/`, `qa/play_console_forms/`, `qa/play_upload_auth/`, `qa/privacy_policy_hosting/`, `qa/fastlane_runtime/`, `qa/upload_keystore_setup/`, `qa/upload_operator_runbook/`, `qa/workspace_hygiene/` and `qa/pre_upload_blockers/` with generated markdown/JSON evidence. Connected smoke evidence is copied only when the latest passing run is fresh; otherwise `manifest.connectedSmoke.status` and `NEXT_ACTIONS.md` record the refresh command instead of presenting stale emulator evidence. Instrumentation smoke and connected-performance reports are optional evidence; fresh passing reports are copied, stale/missing reports are skipped with `manifest.optionalEvidence.*` status/detail/refresh commands. The archive is built from manifest-listed handoff files plus `manifest.json`, archive/package reports record `manifestSha256`, archive QA validates the archived manifest content, sidecar verification command and `releaseGate` summary parity, and the handoff secret scan checks manifest-listed handoff files, zip entries and transfer sidecars for key-like filenames, private-key blocks and Google service-account credential JSON. The package flow runs that secret scan again after the final package sidecars are written, then reruns freshness without changing those sidecars. The post-package validation report is written only under `build/reports/`; it proves the final sidecar scan ran after all transfer sidecars, final freshness ran after that scan, package sidecars match, archive SHA/byte counts match the zip, package/archive `manifestSha256` values match the current handoff manifest, the report is excluded from the handoff manifest and the package flow has no sidecar rewrite after the final scan. The final freshness QA checks current release-document dates, generated report dates including asset, UI-behavior, Play-metadata and completion-audit evidence, release-gate report freshness, privacy hosting handoff manifest freshness, exact archive checksum sidecar text, archive/package `manifestSha256` parity, package status/sidecar parity and optional evidence report status.

The generated reports are:

```text
build/reports/release_candidate_package.md
build/reports/release_candidate_package.json
build/reports/release_gate.md
build/reports/release_gate.json
build/reports/asset_manifest.md
build/reports/asset_manifest.json
build/reports/store_screenshot_freshness.md
build/reports/store_screenshot_freshness.json
build/reports/store_screenshot_capture_guard.md
build/reports/store_screenshot_capture_guard.json
build/reports/store_screenshot_capture.md
build/reports/store_screenshot_capture.json
build/reports/content_copy.md
build/reports/content_copy.json
build/reports/play_metadata.md
build/reports/play_metadata.json
build/reports/play_upload_packet.md
build/reports/play_upload_packet.json
build/reports/pre_upload_blockers.md
build/reports/pre_upload_blockers.json
build/reports/play_upload_auth.md
build/reports/play_upload_auth.json
build/reports/privacy_policy_hosting.md
build/reports/privacy_policy_hosting.json
build/reports/fastlane_runtime.md
build/reports/fastlane_runtime.json
build/reports/upload_keystore_setup.md
build/reports/upload_keystore_setup.json
build/reports/upload_operator_runbook.md
build/reports/upload_operator_runbook.json
build/reports/workspace_hygiene.md
build/reports/workspace_hygiene.json
build/reports/play_handoff_secret_scan.md
build/reports/play_handoff_secret_scan.json
build/reports/post_package_validation.md
build/reports/post_package_validation.json
```

The transferable archive remains:

```text
build/play_handoff/shawarma58-v1.0.0.zip
build/play_handoff/shawarma58-v1.0.0.zip.sha256
```

Verify the transfer sidecar from the repository root with:

```bash
cd build/play_handoff && shasum -a 256 -c shawarma58-v1.0.0.zip.sha256
```

After unpacking, verify the file set from the handoff root:

```bash
shasum -a 256 -c CHECKSUMS.txt
```

For the final upload environment, run:

```bash
python3 scripts/package_release_candidate.py --strict-signing --fetch-privacy-url --fetch-target-api-policy --strict-screenshots --strict-physical-device --strict-pre-upload
```

Add `--connected-tests --connected-performance --serial <adb-serial>` when a clean emulator or physical test device is available. Use `--serial` whenever more than one emulator/device is connected.
