# Performance Notes

- No backend, network, WebView, maps, video, 3D, ads SDK or analytics SDK.
- Runtime bitmap assets were resized to 512-1200px max and optimized to WebP in `drawable-nodpi`.
- Release build uses R8 minification and Android resource shrinking.
- Android resource folder is ~3.13 MiB after optimization; `drawable-nodpi` is ~2.83 MiB after adding the screen-specific ImageGen backgrounds. Debug APK is 17.55 MiB and release AAB is 5.53 MiB in the current local environment.
- `python3 scripts/performance_budget_qa.py` enforces release budgets: AAB <= 8 MiB, debug APK <= 25 MiB, Android resources <= 4 MiB, runtime `drawable-nodpi` <= 3 MiB, base dex <= 2.5 MB, runtime native libs <= 128 KiB and no forbidden backend/network/ads/billing/analytics dependency markers.
- Compose UI uses a single activity, saveable in-memory game state and a lightweight `lifecycle-runtime-compose` observer to pause active gameplay when the app goes to background. Activity recreation restores the active screen/session through `rememberSaveable`; unfinished runs are not persisted to DataStore.
- Core gameplay uses one 1-second coroutine timer per active session.
- DataStore writes only on onboarding, settings changes, confirmed progress reset, level completion and endless record updates.
- Expected to run on mid-range and older Android devices supported by `minSdk 23`.
- Connected performance evidence is captured with `python3 scripts/connected_performance_qa.py --serial <adb-serial>`. Current emulator evidence after the June 14 screen-specific ImageGen background UI/UX pass on `emulator-5586`: total PSS 70,868 KB, crash buffer clean, evidence in `build/performance_connected/20260614-124355/summary.md`. Frame diagnostics are stored but treated as non-blocking WARN when the sample has too few frames or is emulator/cold-start dominated. When included in the Play handoff, raw `meminfo`, `gfxinfo`, framestats, logcat and crash-log artifacts are copied under `qa/connected_performance/artifacts/` and verified by SHA-256.
