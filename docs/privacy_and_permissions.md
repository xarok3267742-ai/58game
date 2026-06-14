# Privacy And Permissions

## Permissions
The manifest declares no dangerous permissions and no `INTERNET` permission.

## Data
Stored locally on device:
- `onboardingSeen`
- `soundEnabled`
- `reducedMotion`
- `completedLevels`
- `starsByLevel`
- `bestEndlessScore`

The app does not collect, transmit or sell personal data. There is no account, no ads SDK, no analytics SDK and no third-party login.

Android cloud backup and device-transfer backup are disabled for this release candidate with `android:allowBackup="false"` plus backup/data-extraction exclude rules, so local progress stays on the device unless the user explicitly resets progress in app settings, exports device data through system tools or clears app data.

Ready-to-host policy file: `store/privacy_policy.html`. It must be hosted as a public non-PDF URL before production Play upload.

## Google Play Data safety draft
- Data collected: No.
- Data shared: No.
- Security practices: no data in transit because there is no network transfer.
- User deletion request: not applicable for server data; the in-app settings screen can reset local progress, and clearing app storage removes all local app data.

Detailed Play Console answer sheet: `store/play_console_answers.md`.

## Automated consistency gate
Run:

```bash
python3 scripts/play_target_api_qa.py
python3 scripts/privacy_data_safety_qa.py
python3 scripts/play_console_forms_qa.py
```

This verifies the standalone Google Play target API gate (`targetSdk >= 35` as of the June 14, 2026 official source check), source and merged release manifest permissions, backup/data-extraction exclusion rules, absence of backend/network/ads/billing/analytics markers, privacy policy wording, Play Console Data safety answers and broader App content form coverage. Current policy source checks are recorded in `build/reports/play_target_api.md`, `build/reports/privacy_data_safety.md` and `build/reports/play_console_forms.md`.
