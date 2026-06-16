# Android Emulator Smoke

Use this connected smoke after `./gradlew assembleDebug` and before internal testing. It is intentionally outside `scripts/release_gate.py` because it requires a booted emulator or connected device.

## Command
List devices:

```bash
adb devices
```

Run the basic happy-path smoke on a chosen emulator:

```bash
python3 scripts/android_smoke_qa.py --serial <adb-serial>
```

Run the extended smoke for settings/error/endless coverage:

```bash
python3 scripts/android_smoke_qa.py --serial <adb-serial> --extended
```

The script installs `app/build/outputs/apk/debug/app-debug.apk`, verifies that `com.shawarma58.game.debug/com.shawarma58.game.MainActivity` resolves, clears only `com.shawarma58.game.debug` app data, launches `MainActivity`, verifies the app is foreground, and drives the selected flow. If a shared emulator reports install success but the activity does not resolve, the script uninstalls only `com.shawarma58.game.debug` and `com.shawarma58.game.debug.test`, then reinstalls with downgrade allowed.

Basic mode covers onboarding, menu, level select, level 1, three correct orders and result screen.

Extended mode covers settings toggle persistence after returning to menu, wrong-order state, Android Back opening pause before exit, Home/background opening pause on return and endless result.

## Evidence
The script writes evidence under `build/android_smoke/<timestamp>/`:
- screenshots for onboarding, menu, gameplay start and result;
- `logcat.txt`;
- `logcat_crash.txt`;
- `summary.md`.

Latest local pass:
- Date/time: June 14, 2026, 12:46 local time.
- Serial: `emulator-5586`.
- Basic evidence: `build/android_smoke/retry-basic-20260611-220848/summary.md`.
- Extended evidence: `build/android_smoke/20260614-124352/summary.md`.
- Covered: clean install/data clear, first launch/onboarding, menu, settings persistence, wrong-order state, Android Back opening pause before exit, Home/background opening pause on return, endless result and app crash-buffer check.
- Handoff: `python3 scripts/create_play_handoff.py` prefers the latest passing extended smoke evidence and copies it to `build/play_handoff/shawarma58-v1.0.0/qa/android_smoke/latest/`; `python3 scripts/play_handoff_qa.py` validates that copied evidence.

## Notes
- The script validates foreground package before and after taps to avoid false passes against another installed app.
- Debug APK install uses `adb install -r -d`, then checks package resolution and retries a clean reinstall of only this app if Android's package manager returns an inconsistent state.
- Text-navigation taps retry until the expected next screen text appears, which reduces false negatives from missed emulator `adb input tap` events.
- Ingredient taps use cached tile bounds from the gameplay UI tree to reduce `uiautomator` flakiness.
- `uiautomator` itself can write system crashes to the crash buffer on some emulator images; the pass/fail check only treats crashes for `com.shawarma58.game.debug` as app failures.
