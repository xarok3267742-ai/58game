# UI Audit

## Design system
- Colors: warm beige background, herb green primary, tomato red secondary, mustard stars, charcoal text.
- Typography: Material 3 defaults with heavier title weights for game identity.
- Spacing: 8dp base rhythm, 16-22dp screen padding.
- Radii: 16-28dp for game panels and image crops.
- States: selected ingredient uses a dark assembly rail plus text list; ingredient trays use color/category markers and a 2dp selected border; disabled level tickets are muted beige.
- Loading: splash screen lasts ~850ms before routing.
- Empty: selected ingredient panel says `Состав пока пуст`.
- Error: wrong order adds visible mistake count, resets selected ingredients and shows `Состав не совпал`.
- Success: result screen shows stars, score, served orders, best streak, post-shift coaching and next action.

## Screen checks
- June 14, 2026 UI refresh: menu now uses a dark storefront hero, a cashier-tape progress strip, perforated ticket actions and a two-button utility row instead of a plain vertical button/card list.
- June 14, 2026 UI/UX refresh: level select now reads as a shift route with `Маршрут 58`, chapter stops (`Вокзал`, `Обед`, `Вечер`), a large current-shift spotlight and smaller route tickets instead of a uniform grid.
- June 14, 2026 UI/UX refresh: gameplay now uses a darker shift console, receipt-like customer ticket, assembly rail (`Линия сборки`) and colored ingredient trays with category markers.
- June 14, 2026 UI refresh: result now uses a receipt-style `Чек смены` with row metrics, a level stamp and a coaching note instead of generic stats cards.
- June 14, 2026 ImageGen background pass: level select uses a route-map background, gameplay uses a dark prep-station background and result screens use a light receipt-counter background. Menu/onboarding keep the storefront/prep identity, so the main loop no longer reads as one repeated card stack.
- Screenshot status after the first June 14 refresh: all seven store/QA screenshots were recaptured from the current app on clean `emulator-5570`; strict screenshot freshness, capture and visual-quality gates passed at that point.
- Screenshot status after the June 14 screen-specific ImageGen background UI/UX pass: all seven store/QA screenshots were recaptured from the current app on `emulator-5586`; latest full evidence is `build/store_screenshot_capture/20260614-124029/summary.md`. Strict screenshot freshness, capture provenance and visual-quality gates pass.
- First launch: splash -> onboarding -> menu.
- Main flow: menu -> levels -> gameplay -> result -> next/retry/menu.
- Levels: the spotlight card shows the current shift, chapter, target order count, duration and star state; smaller route tickets show shift title, workload and lock/ready state.
- Gameplay: top bar shows current correct-order series and the next streak bonus; pause overlay stops interaction until `Продолжить` or `В меню`.
- Gameplay: serving an order shows a compact success/error feedback panel with score/streak or reset guidance.
- Gameplay: ingredient selection and serve actions provide platform haptic feedback without requiring vibration permissions.
- Settings: sound and reduced motion persist via DataStore; local progress reset requires a second confirmation tap and keeps settings intact.
- Back: sub-screens return to menu; gameplay back opens the pause overlay before the player can leave the run.
- Back on pause closes the pause overlay and resumes the shift screen.
- Background: leaving the app during gameplay opens the pause overlay before the timer continues on return.
- Configuration-change restore: the current screen and active gameplay session are saved with `rememberSaveable`, including selected ingredients, timer, score, mistakes, streak and pause state.
- Small screens: gameplay uses 4-column grid with fixed aspect tiles and max lines; level tiles keep one-line workload labels with ellipsis protection.
- Large screens: scrollable menu/settings/about prevent content clipping.
- Result: content is scrollable, so stars, stats, coaching copy and action buttons remain reachable on small screens.
- Emulator smoke: `shawarma58_api35` at 1080x2400 completed onboarding -> menu -> level select -> gameplay -> result on June 6, 2026.
- Extended emulator smoke: settings persistence, Android back navigation, wrong-order state and endless result were checked on June 6, 2026; Compose instrumentation now also covers the settings progress reset path.
- System bars: gameplay controls were checked after adding `systemBarsPadding()`; action buttons remain above the Android navigation bar.
- Result: last completed level shows `Повторить` instead of `Следующая смена`, because no next level exists in v1; feedback copy covers clean wins, two-star wins, timeouts and empty endless runs.

## Accessibility
Images have content descriptions where they carry meaning. Buttons are at least 52dp high, and the header back control has a 48dp target with `Назад` for TalkBack. Ingredient and level tiles expose semantic role/state text, and the game does not rely only on color: selected ingredients are also listed in text. Haptic feedback is supplemental; visible state and text remain the source of truth.
