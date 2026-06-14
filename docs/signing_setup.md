# Signing Setup

Do not commit keystores or passwords.

## Environment Variables
Set these before building the upload-ready AAB:

```bash
export SHAWARMA58_KEYSTORE=/absolute/path/shawarma58-upload.jks
export SHAWARMA58_KEYSTORE_PASSWORD=...
export SHAWARMA58_KEY_ALIAS=...
export SHAWARMA58_KEY_PASSWORD=...
```

Then run:

```bash
python3 scripts/prepare_upload_keystore.py --strict
python3 scripts/signing_env_qa.py --strict
./gradlew bundleRelease
python3 scripts/release_gate.py --strict-signing
```

## Generate Upload Key
If Play Console does not provide an upload key yet, generate one locally and register it in Play Console. The helper refuses paths inside this repository and reads passwords only from env vars:

```bash
export SHAWARMA58_KEYSTORE=/absolute/path/shawarma58-upload.jks
export SHAWARMA58_KEYSTORE_PASSWORD=...
export SHAWARMA58_KEY_ALIAS=shawarma58
export SHAWARMA58_KEY_PASSWORD=...
python3 scripts/prepare_upload_keystore.py --generate
```

Keep the keystore outside the repository. The repository `.gitignore` excludes `*.jks` and `*.keystore`, but that is only a guardrail.

## Verify
`python3 scripts/prepare_upload_keystore.py --strict` validates the upload-keystore path, keytool availability, env alignment and alias before a strict signed build.

`python3 scripts/signing_env_qa.py` validates signing env completeness, absolute keystore path, keystore location outside the repository, secret-file absence in the workspace and, when `keytool` is available, the configured alias.

`scripts/release_gate.py --strict-signing` fails unless the signing env is complete and the AAB signature verifies. Without signing env vars, the scripts report `EXTERNAL_BLOCKER` for signing while keeping local QA checks passing.
