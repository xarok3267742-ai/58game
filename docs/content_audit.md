# Content Audit

## Content blocks
- 24 level titles/subtitles: final Russian copy.
- 10 recipe names: final Russian copy.
- 4 customer lines: final Russian copy.
- Onboarding/menu/settings/about/result microcopy: final Russian copy, including post-shift coaching labels such as `Чистая работа`, `Смена принята`, `Не хватило времени` and `Разогрев не пошёл`.
- Level select workload copy: final Russian copy for target orders and shift duration, for example `3 заказа • 77 сек`.
- Gameplay serve feedback copy: final Russian copy for correct and wrong submissions, including `Заказ выдан`, `Состав не совпал` and `Состав сброшен`.
- Settings reset flow copy: final Russian copy for local progress reset and confirmation.
- Streak/bonus gameplay copy: final Russian copy for current series, next bonus and best series on results.
- Pause/resume copy: final Russian copy for stopping the shift timer, continuing or returning to menu.
- Store listing draft: in `store/play_listing_ru.md` and `fastlane/metadata/android/ru-RU`.
- Privacy policy draft: `store/privacy_policy.html`.
- Play Console answers: `store/play_console_answers.md`.

## Issues fixed
- No lorem ipsum.
- No temporary dev labels.
- No copyrighted brands or real shop names.
- No political/medical/financial/adult/gambling content.
- `python3 scripts/content_copy_qa.py` passes app/domain/listing/privacy copy checks, required Russian microcopy checks and placeholder/dev wording checks.
- `python3 scripts/play_metadata_qa.py` passes Play length checks and placeholder checks for metadata/privacy artifacts.
- In-app progress deletion copy is aligned with `store/privacy_policy.html`, `store/play_console_answers.md` and `docs/privacy_and_permissions.md`.

## Remaining risks
No placeholder or policy-sensitive content remains in the app copy. After the June 14 screen-specific ImageGen background UI/UX pass, all seven store/QA screenshots were recaptured from the current app on `emulator-5586`; strict screenshot freshness, capture provenance and visual-quality QA pass.
