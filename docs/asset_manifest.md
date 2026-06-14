# Asset Manifest

| Asset | Path | Purpose | Size | Source | Status | Used |
|---|---|---|---:|---|---|---|
| App icon concept | `store/app_icon_concept.png` | Source concept for launcher-safe icon | 1254x1254 PNG | ImageGen app icon prompt | APPROVED | Source/QA |
| Play app icon | `store/play_icon.png` | Google Play high-res app icon candidate | 512x512 RGBA PNG | ImageGen app icon prompt + local resize | APPROVED | Store prep/Fastlane |
| App icon foreground | `app/src/main/res/drawable-nodpi/ic_launcher_foreground.webp` | Adaptive icon foreground and splash mark | 768x768 RGBA WebP | ImageGen app icon prompt + local launcher prep + WebP optimization | APPROVED | Launcher, splash |
| Legacy launcher icons | `app/src/main/res/mipmap-*/ic_launcher.png`, `app/src/main/res/mipmap-*/ic_launcher_round.png` | Pre-API 26 launcher fallback | 48-192px RGBA | Resized prepared icon | APPROVED | Launcher |
| Counter background | `app/src/main/res/drawable-nodpi/bg_counter.webp` | Storefront/menu fallback background | 1200x800 WebP | ImageGen splash/background prompt + WebP optimization | APPROVED | Splash, menu, onboarding/settings/about fallback |
| Route map background | `app/src/main/res/drawable-nodpi/bg_route_map.webp` | Level select background | 720x1600 WebP | ImageGen screen background prompt + runtime resize + WebP optimization | APPROVED | Level select |
| Prep station background | `app/src/main/res/drawable-nodpi/bg_prep_station.webp` | Gameplay background | 720x1600 WebP | ImageGen screen background prompt + runtime resize + WebP optimization | APPROVED | Gameplay |
| Receipt counter background | `app/src/main/res/drawable-nodpi/bg_receipt_counter.webp` | Result background | 720x1600 WebP | ImageGen screen background prompt + runtime resize + WebP optimization | APPROVED | Result |
| Route map source | `store/imagegen_backgrounds/bg_route_map_source.png` | Source PNG for level background | 1080x2400 PNG | ImageGen screen background prompt + source resize | APPROVED | Source/QA |
| Prep station source | `store/imagegen_backgrounds/bg_prep_station_source.png` | Source PNG for gameplay background | 1080x2400 PNG | ImageGen screen background prompt + source resize | APPROVED | Source/QA |
| Receipt counter source | `store/imagegen_backgrounds/bg_receipt_counter_source.png` | Source PNG for result background | 1080x2400 PNG | ImageGen screen background prompt + source resize | APPROVED | Source/QA |
| Onboarding prep | `app/src/main/res/drawable-nodpi/art_onboarding_prep.webp` | Onboarding art | 768x768 WebP | ImageGen onboarding prompt + WebP optimization | APPROVED | Onboarding |
| Ingredient lavash | `app/src/main/res/drawable-nodpi/ingredient_lavash.webp` | Transparent ingredient tile | 512x512 RGBA WebP | ImageGen ingredient prompt + local alpha pass + WebP optimization | APPROVED | Gameplay |
| Ingredient chicken | `app/src/main/res/drawable-nodpi/ingredient_chicken.webp` | Transparent ingredient tile | 512x512 RGBA WebP | ImageGen ingredient prompt + local alpha pass + WebP optimization | APPROVED | Gameplay |
| Ingredient tomato | `app/src/main/res/drawable-nodpi/ingredient_tomato.webp` | Transparent ingredient tile | 512x512 RGBA WebP | ImageGen ingredient prompt + local alpha pass + WebP optimization | APPROVED | Gameplay |
| Ingredient cucumber | `app/src/main/res/drawable-nodpi/ingredient_cucumber.webp` | Transparent ingredient tile | 512x512 RGBA WebP | ImageGen ingredient prompt + local alpha pass + WebP optimization | APPROVED | Gameplay |
| Ingredient greens | `app/src/main/res/drawable-nodpi/ingredient_greens.webp` | Transparent ingredient tile | 512x512 RGBA WebP | ImageGen ingredient prompt + local alpha pass + WebP optimization | APPROVED | Gameplay |
| Ingredient garlic | `app/src/main/res/drawable-nodpi/ingredient_garlic.webp` | Transparent ingredient tile | 512x512 RGBA WebP | ImageGen ingredient prompt + local alpha pass + WebP optimization | APPROVED | Gameplay |
| Ingredient spicy | `app/src/main/res/drawable-nodpi/ingredient_spicy.webp` | Transparent ingredient tile | 512x512 RGBA WebP | ImageGen ingredient prompt + local alpha pass + WebP optimization | APPROVED | Gameplay |
| Ingredient fries | `app/src/main/res/drawable-nodpi/ingredient_fries.webp` | Transparent ingredient tile | 512x512 RGBA WebP | ImageGen ingredient prompt + local alpha pass + WebP optimization | APPROVED | Gameplay |
| Customer office | `app/src/main/res/drawable-nodpi/customer_office.webp` | Customer portrait | 512x512 WebP | ImageGen portrait prompt + WebP optimization | APPROVED | Gameplay |
| Customer student | `app/src/main/res/drawable-nodpi/customer_student.webp` | Customer portrait | 512x512 WebP | ImageGen portrait prompt + WebP optimization | APPROVED | Gameplay |
| Customer courier | `app/src/main/res/drawable-nodpi/customer_courier.webp` | Customer portrait | 512x512 WebP | ImageGen portrait prompt + WebP optimization | APPROVED | Gameplay |
| Customer neighbor | `app/src/main/res/drawable-nodpi/customer_neighbor.webp` | Customer portrait | 512x512 WebP | ImageGen portrait prompt + WebP optimization | APPROVED | Gameplay |
| Feature graphic | `store/feature_graphic_concept.png` | Play feature graphic candidate | 1024x500 | ImageGen store prompt | APPROVED | Store prep |
| Contact sheet | `store/imagegen_contact_sheet.jpg` | Visual QA contact sheet | 800x1150 | Local QA composite | INTERNAL | Docs/QA |
| Launcher icon preview | `store/launcher_icon_preview.png` | Adaptive icon mask QA | 800x310 | Local QA composite | INTERNAL | Docs/QA |
| Ingredient alpha contact sheet | `store/ingredient_alpha_contact_sheet.png` | Transparent sprite edge QA | 880x520 | Local QA composite | INTERNAL | Docs/QA |
| Onboarding screenshot | `store/screenshots/shawarma_onboarding.png` | Play/QA screenshot | 1080x2400 | Real Android emulator screenshot | APPROVED | QA evidence |
| Menu screenshot | `store/screenshots/shawarma_menu.png` | Play/QA screenshot | 1080x2400 | Real Android emulator screenshot | APPROVED | QA evidence |
| Level select screenshot | `store/screenshots/shawarma_levels.png` | Play/QA screenshot | 1080x2400 | Real Android emulator screenshot | APPROVED | QA evidence |
| Gameplay screenshot | `store/screenshots/shawarma_gameplay.png` | Play/QA screenshot | 1080x2400 | Real Android emulator screenshot | APPROVED | QA evidence |
| Result screenshot | `store/screenshots/shawarma_result.png` | Play/QA screenshot | 1080x2400 | Real Android emulator screenshot | APPROVED | QA evidence |
| Wrong-order screenshot | `store/screenshots/shawarma_wrong_order.png` | QA screenshot for mistake state | 1080x2400 | Real Android emulator screenshot | APPROVED | QA evidence |
| Endless result screenshot | `store/screenshots/shawarma_endless_result.png` | QA screenshot for endless score state | 1080x2400 | Real Android emulator screenshot | APPROVED | QA evidence |

## Asset QA
- `python3 scripts/prepare_launcher_icons.py` removes dark connected launcher corners, keeps the ImageGen icon composition, and regenerates legacy mipmap PNGs.
- `python3 scripts/remove_sprite_background.py app/src/main/res/drawable-nodpi/ingredient_*.webp` removes the connected light ImageGen background from ingredient sprites.
- `python3 scripts/optimize_res_bitmaps.py` converts runtime `drawable-nodpi` bitmap assets to optimized WebP.
- `python3 scripts/asset_qa.py` verifies key image dimensions, including the screen-specific backgrounds, and requires transparent alpha for launcher foreground and all `ingredient_*` files.
- Rejected variants are kept under `store/rejected_assets/` and documented in `docs/rejected_assets.md`; they must not appear in app resources, fastlane upload graphics or the Play handoff.
- Last run: launcher foreground and all 8 ingredient sprites have transparent alpha range `(0, 255)`.
