# Product Spec

## Название
Шаурма 58.

## Тип и жанр
Android game, casual time-management / cooking assembly.

## Pitch
Собирай заказы шаурмы на коротких сменах, держи темп и открывай новые уровни без интернета.

## Core loop
1. Игрок выбирает смену.
2. Видит заказ клиента и список ингредиентов.
3. Тапает ингредиенты, отдаёт заказ.
4. Может поставить смену на паузу, затем продолжить без потери текущего заказа.
5. Получает score, серию правильных заказов, явную обратную связь по подаче, ошибку или следующий заказ.
6. Закрывает смену, получает 1-3 звезды, короткую подсказку по результату и открывает следующий уровень.

Active gameplay state is saveable across Android Activity recreation such as rotation: current screen, selected ingredients, timer, score, mistakes, streak and pause state are restored without writing unfinished runs to DataStore.

## Экраны
Splash, onboarding, main menu, level select, gameplay, result, settings, about/privacy.

Level select tiles show stars, tempo, target order count and shift duration before the player starts a run.

Result screen shows stars, score, served orders, best streak, next action and a short post-shift coaching card for wins, losses and endless mode.

## Settings and privacy controls
- Sound feedback and reduced motion are local settings.
- Ingredient taps and served orders use lightweight system haptic feedback without adding app permissions.
- The settings screen includes a two-step local progress reset. It clears onboarding, completed shifts, stars and endless best score while keeping sound/reduced-motion preferences.

## Игровые правила
- У заказа есть уникальный набор ингредиентов.
- Порядок выбора не важен; состав должен совпасть точно.
- Неверный заказ добавляет ошибку и сбрасывает текущий состав.
- Правильные заказы подряд собирают серию и дают бонус к score; ошибка сбрасывает текущую серию.
- После подачи игрок видит короткий feedback: `Заказ выдан` или `Состав не совпал`.
- Пауза останавливает таймер и закрывает управление сменой до продолжения или выхода в меню.
- При пересоздании Activity активная смена восстанавливается с текущим составом, таймером, счётом, ошибками, серией и состоянием паузы.
- Уровень завершается победой при выполнении целевого числа заказов.
- Уровень завершается поражением по таймеру или по лимиту ошибок.
- Бесконечная смена длится 90 секунд и сохраняет лучший score.

## Прогрессия
24 смены в трёх темпах: спокойный старт, обеденный наплыв, вечерний пик. Следующий уровень открывается после победы на предыдущем.

## UI style
Тёплый street-food стиль: lavash beige, herb green, tomato red, mustard accents, charcoal text. ImageGen используется для food-art, клиентов и store concepts; UI-текст остаётся native Compose.

## Tone of voice
Короткие русские фразы без сленговой перегрузки: «Смена закрыта», «Отдать заказ», «Классика района», «Чистая работа».

## First launch
Splash -> onboarding с иллюстрацией и объяснением одного действия -> main menu.

## Success criteria
Пользователь без подсказок запускает смену, собирает заказ, понимает ошибку, видит результат, получает понятный совет по смене и может открыть следующий уровень.
