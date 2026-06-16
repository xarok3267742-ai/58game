# Tech Stack Decision

## Выбранный стек
Kotlin + Jetpack Compose + Material 3, Android Gradle Plugin 8.10.1, Kotlin 2.0.21, Compose BOM 2025.01.01, DataStore Preferences 1.2.1.

## Почему
Стек нативный для Android, подходит для production release candidate, хорошо работает offline-first, не требует webview/backend и позволяет сделать аккуратный UI без тяжёлого игрового движка.

## Альтернативы
- Flutter: быстрый UI, но в пустом Android-first проекте добавляет лишний runtime и tooling.
- React Native/Expo: не нужен для простой offline game и усложняет release.
- Godot: уместен для более графической 2D-игры, но здесь core loop проще и хорошо ложится в Compose.

## Команды
```bash
./gradlew test
./gradlew lint
./gradlew assembleDebug
./gradlew bundleRelease
```

## Ограничения окружения
Android SDK установлен локально в `/Users/shawarma58/Library/Android/sdk`. При первой проверке Gradle не смог скачать часть lifecycle 2.8.3 из-за TLS handshake с `dl.google.com`, поэтому dependencies закреплены на доступном cached lifecycle 2.8.7.
