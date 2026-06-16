# Upload Operator Runbook

Use this checklist only on the final upload machine. Do not write real passwords, keystores or Google service-account JSON into this repository or the Play handoff archive.

## Required Inputs

Set these values in the shell session or in a private local environment file outside the repository:

```bash
export SHAWARMA58_KEYSTORE="/absolute/path/outside-repo/shawarma58-upload.jks"
export SHAWARMA58_KEYSTORE_PASSWORD="<private password in shell only>"
export SHAWARMA58_KEY_ALIAS="shawarma58"
export SHAWARMA58_KEY_PASSWORD="<private password in shell only>"
export SUPPLY_JSON_KEY="/absolute/path/outside-repo/google-play-service-account.json"
export SHAWARMA58_PRIVACY_POLICY_URL="https://your-public-domain.example/shawarma58/privacy_policy.html"
```

Rules:
- `SHAWARMA58_KEYSTORE` and `SUPPLY_JSON_KEY` must point outside `/Users/shawarma58/Desktop/58 game`.
- `SHAWARMA58_PRIVACY_POLICY_URL` must be public HTTPS, non-PDF and non-geofenced.
- The uploaded AAB must be rebuilt after signing env vars are set.
- The physical-device sanity pass must use a real non-emulator Android phone.

## Prepare Runtime

Use a Ruby runtime with matching development headers. Avoid continuing with system Ruby if `python3 scripts/fastlane_runtime_qa.py` reports that `RbConfig::CONFIG['rubyarchhdrdir']/ruby/config.h` is missing; native gems such as `json` will fail during `bundle install`. The runtime QA report includes a remediation block with detected `brew`/`rbenv`/`asdf`/`mise` options and exact commands for the upload machine.

```bash
bundle install --path vendor/bundle
python3 scripts/fastlane_runtime_qa.py --strict
```

If Ruby native headers or gems fail, install a Homebrew/rbenv/asdf/mise Ruby with headers or repair Xcode Command Line Tools before continuing.

## Verify External Inputs

```bash
python3 scripts/prepare_upload_keystore.py --strict
python3 scripts/signing_env_qa.py --strict
python3 scripts/play_upload_auth_qa.py --strict
python3 scripts/privacy_policy_hosting_qa.py --strict --fetch-privacy-url
python3 scripts/physical_device_readiness_qa.py --strict
python3 scripts/play_external_readiness_qa.py --strict --fetch-privacy-url
```

## Rebuild And Package

```bash
./gradlew bundleRelease
python3 scripts/artifact_provenance_qa.py --strict-signing
python3 scripts/pre_upload_blockers_qa.py --strict
python3 scripts/package_release_candidate.py --strict-signing --fetch-privacy-url --fetch-target-api-policy --strict-screenshots --strict-physical-device --strict-pre-upload
python3 scripts/post_package_validation_qa.py
```

From the repository root, verify the transferable archive sidecar:

```bash
cd build/play_handoff && shasum -a 256 -c shawarma58-v1.0.0.zip.sha256
```

From the generated handoff root, verify file integrity:

```bash
shasum -a 256 -c CHECKSUMS.txt
```

Confirm `manifest.json` reports:

```text
signing.status = signed
```

Confirm the local-only post-package report is `PASS`:

```text
build/reports/post_package_validation.md
```

## Validate Play Upload

Use the validate lane before any upload:

```bash
bundle exec fastlane android validate_internal
```

For internal testing upload:

```bash
bundle exec fastlane android upload_internal
```

Manual upload is also acceptable. Paths below are relative to the generated handoff root:
- Signed AAB: `upload/app-release.aab`
- Listing text: `metadata/ru-RU/`
- Play app icon: `fastlane/metadata/android/ru-RU/images/icon.png`
- Feature graphic: `fastlane/metadata/android/ru-RU/images/featureGraphic.png`
- Phone screenshots: `fastlane/metadata/android/ru-RU/images/phoneScreenshots/`
- Privacy page: hosted `privacy/hosting/privacy_policy.html`
- Play Console answers: `docs/play_console_answers.md`
- Deobfuscation files: `deobfuscation/release/`

## Stop Conditions

Do not upload when any of these are true:
- `manifest.json` reports `signing.status = external_blocker`.
- `python3 scripts/pre_upload_blockers_qa.py --strict` fails.
- `python3 scripts/post_package_validation_qa.py` fails.
- `python3 scripts/play_handoff_secret_scan_qa.py` reports a finding.
- A real Android phone sanity pass has not been completed.
- The privacy policy URL was not fetched and verified from the public internet.
