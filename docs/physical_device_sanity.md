# Physical Device Sanity

Run this once on a real Android phone before production rollout.

Before the manual pass, run:

```bash
python3 scripts/physical_device_readiness_qa.py
```

Local emulator-only runs may report `EXTERNAL_BLOCKER`; this is expected until a non-emulator Android phone is connected. In the final production-readiness environment, use:

```bash
python3 scripts/physical_device_readiness_qa.py --strict
```

## Setup
1. Build/install debug APK or a signed internal-test build.
2. Start with app data cleared.
3. Enable airplane mode before launch.

## Checks
1. Launch app and confirm onboarding appears.
2. Tap `Начать смену`, reach the main menu.
3. Open `Настройки`, toggle both switches, press Android Back, relaunch app and confirm toggles persist.
4. Open `Играть`, start level 1, submit one wrong order and confirm `Ошибки 1/3`.
5. Tap `Пауза`, confirm the timer overlay appears, tap `Продолжить` and confirm the same shift remains playable.
6. Press Android Back from gameplay and confirm the pause overlay appears; tap `В меню` and confirm return to menu.
7. Start gameplay again, press Home, reopen the app and confirm the pause overlay is visible before the timer continues.
8. Start level 1 again and complete all 3 orders correctly.
9. Confirm result screen shows `Заказы выданы`, score, `3/3` orders, best streak and stars.
10. Tap `Следующая смена`, confirm level 2 gameplay opens.
11. Return to menu, start `Бесконечная смена`, serve one order, force three mistakes and confirm score/result then menu record update.
12. Open `Настройки`, tap `Сбросить прогресс`, then `Удалить прогресс`; confirm menu stats return to zero while sound/reduced-motion settings stay as selected.
13. Rotate device if possible; app should stay portrait and remain stable.

## Pass Criteria
- No crash, blank screen, clipped primary text or blocked tap target.
- App remains usable offline.
- System bars do not cover gameplay action buttons.
- Pause overlay blocks gameplay controls and resumes cleanly.
- Backgrounding during gameplay opens pause before time continues.
- Progress/settings persist after app relaunch.
- Confirmed progress reset clears local gameplay data without needing internet or an account.

## Evidence To Keep
- Device model, Android version and build variant.
- One photo or screenshot of gameplay and result screen.
- Any crash/logcat excerpt if a blocker appears.
