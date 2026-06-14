# Fastlane Upload Guard

This folder contains guarded Google Play upload configuration for the v1.0.0 internal-test candidate.
Use the checked-in `Gemfile.lock` so fastlane and supply dependencies stay reproducible across upload machines.

Required env vars before running a lane:

```bash
export SUPPLY_JSON_KEY=/absolute/path/google-play-service-account.json
export SHAWARMA58_PRIVACY_POLICY_URL=https://example.com/shawarma58/privacy
export SHAWARMA58_KEYSTORE=/absolute/path/shawarma58-upload.jks
export SHAWARMA58_KEYSTORE_PASSWORD=...
export SHAWARMA58_KEY_ALIAS=...
export SHAWARMA58_KEY_PASSWORD=...
```

Run validation first:

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
bundle exec fastlane android validate_internal
```

Upload only after validation and Play Console forms are ready:

```bash
bundle exec fastlane android upload_internal
```

Both lanes are restricted to the Google Play internal track and draft release status.
Each lane also verifies the upload keystore setup, runs the consolidated strict pre-upload blocker summary before packaging, then runs the strict release candidate package flow before contacting Google Play, including upload operator runbook QA, strict screenshot freshness, physical-device readiness, final sidecar secret scan, release freshness and post-package validation.
