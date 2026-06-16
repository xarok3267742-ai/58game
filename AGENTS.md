# Шаурма 58

## Проект
Offline-first Android casual time-management игра для русскоязычной аудитории. Игрок собирает заказы шаурмы из ингредиентов, закрывает короткие смены, получает звёзды и открывает уровни.

## Стек
- Kotlin + Jetpack Compose + Material 3.
- Single Activity: `com.shawarma58.game.MainActivity`.
- Локальное состояние: DataStore Preferences.
- Backend, аккаунты, интернет, реклама и платежи в v1 отсутствуют.

## Команды
- Установка wrapper: уже создан `./gradlew`.
- Unit tests: `./gradlew test`.
- Lint: `./gradlew lint`.
- Debug APK: `./gradlew assembleDebug`.
- Release bundle: `./gradlew bundleRelease`.

## Структура
- `app/src/main/java/com/shawarma58/game/data` — модели, уровни, прогресс.
- `app/src/main/java/com/shawarma58/game/game` — чистая игровая логика.
- `app/src/main/java/com/shawarma58/game/ui` — Compose UI и mapping ассетов.
- `app/src/main/res/drawable-nodpi` — ImageGen gameplay/store-facing bitmap assets.
- `docs` — продуктовые, QA, Play и release документы.
- `store` — store creatives concepts и audit artifacts.

## Правила кода
- Core game logic держать без Android-зависимостей, чтобы её можно было тестировать JVM-тестами.
- Не добавлять backend, сеть, аккаунты, рекламу или платежи без отдельной продуктовой причины.
- Не добавлять тяжёлые зависимости ради маленького UI-эффекта.
- Все видимые тексты должны быть финальными русскими микротекстами, без lorem ipsum и dev wording.

## UI/UX
- Первый экран — сам продукт, не landing page.
- Tap targets не меньше 48dp.
- Тексты должны помещаться на маленьких экранах; длинные списки ингредиентов ограничивать строками.
- Карточки использовать только для игровых панелей, уровней и настроек.
- Визуальный стиль: тёплый street-food, чистый, без перегруженного неона и fake UI.

## Ассеты
- Финальные bitmap-ассеты должны быть ImageGen/Figma/design-tool quality или помечены неготовыми.
- Не использовать чужие бренды, персонажей, UI, мелкий текст в картинках.
- Плохие варианты исключать из release path и фиксировать в `docs/rejected_assets.md`.

## Done
1. Приложение запускается.
2. MVP-цикл работает: уровни, заказы, таймер, ошибки, звёзды, прогресс.
3. UI выглядит законченным mobile product.
4. Нет placeholder-контента.
5. Ассеты консистентны и задокументированы.
6. Доступные tests/lint/build выполнены.
7. Google Play checklist и release report обновлены.
