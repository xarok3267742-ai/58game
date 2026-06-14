# Fastlane Upload

Date: June 14, 2026.

## Purpose
Use fastlane only after the local release candidate has passed strict signing and Play metadata checks. The configuration is intentionally limited to the Google Play internal track and draft release status.
The checked-in `Gemfile.lock` pins the audited fastlane dependency graph.

## Required environment
```bash
export SUPPLY_JSON_KEY=/absolute/path/google-play-service-account.json
export SHAWARMA58_PRIVACY_POLICY_URL=https://example.com/shawarma58/privacy
export SHAWARMA58_KEYSTORE=/absolute/path/shawarma58-upload.jks
export SHAWARMA58_KEYSTORE_PASSWORD=...
export SHAWARMA58_KEY_ALIAS=...
export SHAWARMA58_KEY_PASSWORD=...
```

Do not put the service-account JSON, keystore or passwords in the repository. The upload machine must use a Ruby runtime with matching development headers available; otherwise native gems such as `json` cannot be installed. On this local Mac, system Ruby reports `rubyarchhdrdir` under `universal-darwin24` while `ruby/config.h` is present only under `universal-darwin25`; `bundle install --path vendor/bundle` therefore fails at the `json` native extension. Use a Homebrew/rbenv/asdf/mise Ruby or repair Command Line Tools before fastlane upload. `python3 scripts/fastlane_runtime_qa.py` writes a machine-readable remediation block with detected Ruby managers and exact follow-up commands.

## Preflight
```bash
bundle install --path vendor/bundle
python3 scripts/prepare_upload_keystore.py --strict
python3 scripts/play_upload_auth_qa.py --strict
python3 scripts/privacy_policy_hosting_qa.py --strict --fetch-privacy-url
python3 scripts/fastlane_runtime_qa.py --strict
python3 scripts/upload_operator_runbook_qa.py
python3 scripts/pre_upload_blockers_qa.py --strict
python3 scripts/package_release_candidate.py --strict-signing --fetch-privacy-url --fetch-target-api-policy --strict-screenshots --strict-physical-device --strict-pre-upload
python3 scripts/play_handoff_secret_scan_qa.py
python3 scripts/release_freshness_qa.py
python3 scripts/post_package_validation_qa.py
```

Upload keystore setup, the upload operator runbook, strict screenshot freshness, physical-device readiness, the consolidated pre-upload blocker summary and post-package validation are part of the fastlane preflight. The strict blocker summary runs before packaging so the handoff can include the final blocker report; after packaging, only the sidecar secret scan, release freshness and post-package validation run. If app UI code or runtime assets are newer than the store screenshots, re-capture real screenshots from the current APK before running the lane. If no real Android phone is connected, finish `docs/physical_device_sanity.md` before contacting Google Play.

## Validate only
```bash
bundle exec fastlane android validate_internal
```

This calls Google Play with `validate_only: true`; it should be the first remote fastlane command for every candidate.

## Internal draft upload
```bash
bundle exec fastlane android upload_internal
```

The lane uploads:
- signed AAB: `app/build/outputs/bundle/release/app-release.aab`
- listing metadata: `fastlane/metadata/android/ru-RU`
- feature graphic and screenshots: `fastlane/metadata/android/ru-RU/images`

The lane does not submit production rollout. Finish Data safety, content rating, target audience, app access and the hosted privacy policy URL in Play Console.
