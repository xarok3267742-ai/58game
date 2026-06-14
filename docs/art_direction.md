# Art Direction

## Стиль
Warm illustrated street-food mobile game: чистые формы, читаемая еда, мягкие тени, без детского мультяшного шума.

## Палитра
- Lavash beige: `#FFF1D7`
- Herb green: `#2F5D50`
- Tomato red: `#D94E2F`
- Mustard accent: `#E1A528`
- Charcoal text: `#2A211B`

## Композиция
Еда и клиенты всегда крупные, с простым светлым фоном. Store graphics без встроенного текста; текст добавляется в Play Console или native UI.

Экранные фоны должны различать сценарии: карта уровней похожа на маршрут на бумаге, gameplay — на тёмную рабочую станцию, result — на светлый чек на прилавке. В каждом фоне центральная зона спокойная, потому что нативный Compose UI остаётся главным слоем.

## Нельзя использовать
Чужие бренды, реальные логотипы, известные персонажи, fake UI, мелкий текст, случайные бейджи, неон ради неона, перегруженные фоны.

## Хороший результат
Ассет читается на маленьком размере, выглядит частью одной игры, не спорит с UI, не содержит лишних деталей.

## QA
Launcher foreground should be `RGBA` with transparent corners and checked through `store/launcher_icon_preview.png`.
Ingredient sprites должны быть transparent WebP/PNG (`RGBA`, alpha range includes `0`) и проверяются на шахматном фоне в `store/ingredient_alpha_contact_sheet.png`. Store screenshots должны быть реальными кадрами приложения, не ImageGen/fake UI.

Screen-specific backgrounds keep 1080x2400 PNG source copies under `store/imagegen_backgrounds/`, while runtime assets are downscaled to 720x1600 WebP in `drawable-nodpi` for faster cold-start decode. They are checked by `scripts/asset_qa.py` and must not contain readable text, fake UI, logos or brand marks.

## Плохой результат
Ассет выглядит как случайная AI-картинка, содержит нечитаемые элементы, меняет стиль, отвлекает от gameplay или похож на store fake screenshot.
