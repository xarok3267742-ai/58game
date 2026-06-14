# Accessibility Notes

- Primary buttons are 52-54dp high.
- Header back control has a 48dp tap target and the `Назад` accessibility label.
- Ingredient tiles expose semantic role, ingredient name and selected/not-selected state.
- Level tiles expose semantic role, shift number, tempo, stars and locked/unlocked state.
- Customer portraits include customer type descriptions.
- Selected ingredients are shown as text, not only by tile border color.
- Serve feedback is visible as text after submission, so correct and wrong orders are not communicated only through haptics, sound or counters.
- Ingredient taps and served-order actions use platform haptic feedback in addition to visible text/state changes.
- Reduced motion setting disables smooth timer progress animation.
- No timed onboarding or required gesture beyond taps.
- Known limitation: gameplay is timer-based by design; future accessibility mode could add relaxed untimed levels.
