package com.shawarma58.game.ui

import android.media.AudioManager
import android.media.ToneGenerator
import androidx.activity.compose.BackHandler
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.snap
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.systemBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.listSaver
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import com.shawarma58.game.R
import com.shawarma58.game.data.GameSettings
import com.shawarma58.game.data.Ingredient
import com.shawarma58.game.data.LevelCatalog
import com.shawarma58.game.data.LevelConfig
import com.shawarma58.game.data.MAX_STARS_PER_LEVEL
import com.shawarma58.game.data.PlayerProgress
import com.shawarma58.game.data.ProgressRepository
import com.shawarma58.game.data.RecipeOrder
import com.shawarma58.game.data.ScoreResult
import com.shawarma58.game.game.GameEngine
import com.shawarma58.game.game.GameRules
import com.shawarma58.game.game.GameSession
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

private sealed interface AppScreen {
    data object Splash : AppScreen
    data object Onboarding : AppScreen
    data object Menu : AppScreen
    data object Levels : AppScreen
    data object Settings : AppScreen
    data object About : AppScreen
    data class Game(val levelId: Int, val isEndless: Boolean) : AppScreen
    data class Result(val result: ScoreResult) : AppScreen
}

private val AppScreenSaver = listSaver<AppScreen, Any>(
    save = { screen ->
        when (screen) {
            AppScreen.Splash -> listOf("splash")
            AppScreen.Onboarding -> listOf("onboarding")
            AppScreen.Menu -> listOf("menu")
            AppScreen.Levels -> listOf("levels")
            AppScreen.Settings -> listOf("settings")
            AppScreen.About -> listOf("about")
            is AppScreen.Game -> listOf("game", screen.levelId, screen.isEndless)
            is AppScreen.Result -> listOf(
                "result",
                screen.result.levelId,
                screen.result.levelTitle,
                screen.result.isEndless,
                screen.result.isWin,
                screen.result.score,
                screen.result.stars,
                screen.result.servedOrders,
                screen.result.targetOrders,
                screen.result.mistakes,
                screen.result.bestStreak,
                screen.result.remainingSeconds,
                screen.result.durationSeconds,
            )
        }
    },
    restore = { values -> restoreScreenFromSaveableValues(values) ?: AppScreen.Splash },
)

private val GameSessionSaver = listSaver<GameSession, Any>(
    save = { session -> saveableValuesForSession(session) },
    restore = { values -> restoreSessionFromSaveableValues(values) },
)

private enum class ScreenMood {
    Warm,
    Hero,
    Levels,
    Gameplay,
    Result,
    Quiet,
}

internal fun canStartNextLevel(result: ScoreResult): Boolean {
    return result.isWin && !result.isEndless && result.levelId < LevelCatalog.levels.size
}

internal fun resultPrimaryActionText(result: ScoreResult): String {
    return if (canStartNextLevel(result)) "Следующая смена" else "Повторить"
}

internal fun orderCountLabel(orderCount: Int): String {
    val safeCount = orderCount.coerceAtLeast(0)
    val lastTwo = safeCount % 100
    val last = safeCount % 10
    val noun = when {
        lastTwo in 11..14 -> "заказов"
        last == 1 -> "заказ"
        last in 2..4 -> "заказа"
        else -> "заказов"
    }
    return "$safeCount $noun"
}

internal fun levelWorkloadLabel(level: LevelConfig): String {
    return "${orderCountLabel(level.targetOrders)} • ${level.durationSeconds.coerceAtLeast(0)} сек"
}

private fun levelAccessibilityWorkloadLabel(level: LevelConfig): String {
    return "${orderCountLabel(level.targetOrders)}, ${level.durationSeconds.coerceAtLeast(0)} секунд"
}

internal data class ServeFeedback(
    val title: String,
    val body: String,
    val positive: Boolean,
)

internal fun serveFeedback(correct: Boolean, before: GameSession, after: GameSession): ServeFeedback {
    return if (correct) {
        val gainedScore = (after.score - before.score).coerceAtLeast(0)
        val body = if (after.isFinished && !after.isEndless) {
            "Цель закрыта: ${after.servedOrders}/${after.level.targetOrders} заказов."
        } else {
            "Серия ${after.comboStreak} • +$gainedScore очков"
        }
        ServeFeedback(
            title = "Заказ выдан",
            body = body,
            positive = true,
        )
    } else {
        val mistakesLeft = (after.level.maxMistakes - after.mistakes).coerceAtLeast(0)
        val body = if (after.isFinished) {
            "Лимит ошибок достигнут. Смена закрывается."
        } else {
            "Состав сброшен. Осталось ошибок: $mistakesLeft."
        }
        ServeFeedback(
            title = "Состав не совпал",
            body = body,
            positive = false,
        )
    }
}

internal data class ResultFeedback(
    val title: String,
    val body: String,
)

internal fun resultFeedback(result: ScoreResult): ResultFeedback {
    if (result.isEndless) {
        return when {
            result.servedOrders == 0 -> ResultFeedback(
                title = "Разогрев не пошёл",
                body = "Начни с простых заказов и не отдавай пустой состав.",
            )
            result.mistakes >= 3 -> ResultFeedback(
                title = "Темп есть, чистоты не хватает",
                body = "Ошибки сбивают серию. Лучше сбросить состав, чем отдавать наугад.",
            )
            result.bestStreak >= 5 -> ResultFeedback(
                title = "Серия держит темп",
                body = "Дави на скорость, но сверяй состав перед подачей.",
            )
            else -> ResultFeedback(
                title = "Хороший разгон",
                body = "Держи серию и выбирай состав по строке заказа перед подачей.",
            )
        }
    }

    if (!result.isWin) {
        return if (result.remainingSeconds == 0) {
            ResultFeedback(
                title = "Не хватило времени",
                body = "Собирай знакомые сочетания быстрее и не держи заказ в руках.",
            )
        } else {
            ResultFeedback(
                title = "Ошибки сорвали смену",
                body = "Перед подачей проверь каждый ингредиент и сбрасывай спорный состав.",
            )
        }
    }

    return when (result.stars) {
        3 -> ResultFeedback(
            title = "Чистая работа",
            body = "Заказы ушли без лишних ошибок и с запасом по времени.",
        )
        2 -> ResultFeedback(
            title = "Смена принята",
            body = "Уже стабильно. Для трёх звёзд держи меньше ошибок и оставляй запас времени.",
        )
        else -> ResultFeedback(
            title = "Есть что докрутить",
            body = "Смена закрыта, но ошибки съели рейтинг. Перед подачей сверяй каждый ингредиент.",
        )
    }
}

internal fun shouldPlayOrderFeedback(settings: GameSettings): Boolean = settings.soundEnabled

internal fun orderFeedbackTone(correct: Boolean): Int {
    return if (correct) ToneGenerator.TONE_PROP_ACK else ToneGenerator.TONE_PROP_NACK
}

internal fun orderFeedbackHaptic(correct: Boolean): HapticFeedbackType {
    return if (correct) HapticFeedbackType.TextHandleMove else HapticFeedbackType.LongPress
}

internal fun ingredientToggleHaptic(): HapticFeedbackType = HapticFeedbackType.TextHandleMove

internal fun playableLevelFor(levelId: Int, isEndless: Boolean): LevelConfig {
    return if (isEndless) {
        LevelCatalog.endlessLevel
    } else {
        LevelCatalog.levelByIdOrNull(levelId) ?: LevelCatalog.levels.first()
    }
}

internal fun saveableValuesForSession(session: GameSession): List<Any> {
    return listOf(
        session.level.id,
        session.isEndless,
        session.selectedIngredients.joinToString(",") { it.name },
        session.servedOrders,
        session.mistakes,
        session.comboStreak,
        session.bestStreak,
        session.score,
        session.remainingSeconds,
        session.isFinished,
    )
}

internal fun restoreSessionFromSaveableValues(values: List<Any?>): GameSession? {
    if (values.size != 10) return null
    val levelId = values[0].asSaveableInt() ?: return null
    val isEndless = values[1] as? Boolean ?: return null
    val selectedNames = values[2] as? String ?: return null
    val servedOrders = values[3].asSaveableInt()?.coerceAtLeast(0) ?: return null
    val mistakes = values[4].asSaveableInt()?.coerceAtLeast(0) ?: return null
    val comboStreak = values[5].asSaveableInt()?.coerceAtLeast(0) ?: return null
    val bestStreak = values[6].asSaveableInt()?.coerceAtLeast(0) ?: return null
    val score = values[7].asSaveableInt()?.coerceAtLeast(0) ?: return null
    val remainingSeconds = values[8].asSaveableInt()?.coerceAtLeast(0) ?: return null
    val isFinished = values[9] as? Boolean ?: return null
    val selected = if (selectedNames.isBlank()) {
        emptyList()
    } else {
        selectedNames.split(",").map { name ->
            runCatching { Ingredient.valueOf(name) }.getOrNull() ?: return null
        }
    }
    val level = playableLevelFor(levelId = levelId, isEndless = isEndless)
    return GameSession(
        level = level,
        isEndless = isEndless,
        activeOrder = LevelCatalog.orderFor(level, servedOrders),
        selectedIngredients = selected,
        servedOrders = servedOrders,
        mistakes = mistakes,
        comboStreak = comboStreak,
        bestStreak = bestStreak,
        score = score,
        remainingSeconds = remainingSeconds,
        isFinished = isFinished,
    )
}

private fun restoreScreenFromSaveableValues(values: List<Any?>): AppScreen? {
    val tag = values.firstOrNull() as? String ?: return null
    return when (tag) {
        "splash" -> AppScreen.Splash
        "onboarding" -> AppScreen.Onboarding
        "menu" -> AppScreen.Menu
        "levels" -> AppScreen.Levels
        "settings" -> AppScreen.Settings
        "about" -> AppScreen.About
        "game" -> {
            if (values.size != 3) return null
            val levelId = values[1].asSaveableInt() ?: return null
            val isEndless = values[2] as? Boolean ?: return null
            AppScreen.Game(levelId = levelId, isEndless = isEndless)
        }
        "result" -> restoreResultScreenFromSaveableValues(values)
        else -> null
    }
}

private fun restoreResultScreenFromSaveableValues(values: List<Any?>): AppScreen.Result? {
    if (values.size != 13) return null
    val levelId = values[1].asSaveableInt() ?: return null
    val levelTitle = values[2] as? String ?: return null
    val isEndless = values[3] as? Boolean ?: return null
    val isWin = values[4] as? Boolean ?: return null
    val score = values[5].asSaveableInt() ?: return null
    val stars = values[6].asSaveableInt() ?: return null
    val servedOrders = values[7].asSaveableInt() ?: return null
    val targetOrders = values[8].asSaveableInt() ?: return null
    val mistakes = values[9].asSaveableInt() ?: return null
    val bestStreak = values[10].asSaveableInt() ?: return null
    val remainingSeconds = values[11].asSaveableInt() ?: return null
    val durationSeconds = values[12].asSaveableInt() ?: return null
    return AppScreen.Result(
        ScoreResult(
            levelId = levelId,
            levelTitle = levelTitle,
            isEndless = isEndless,
            isWin = isWin,
            score = score,
            stars = stars,
            servedOrders = servedOrders,
            targetOrders = targetOrders,
            mistakes = mistakes,
            bestStreak = bestStreak,
            remainingSeconds = remainingSeconds,
            durationSeconds = durationSeconds,
        ),
    )
}

private fun Any?.asSaveableInt(): Int? {
    return when (this) {
        is Int -> this
        is Number -> this.toInt()
        is String -> this.toIntOrNull()
        else -> null
    }
}

private fun starsAccessibilityLabel(stars: Int): String {
    return when (stars) {
        1 -> "1 звезда"
        2, 3, 4 -> "$stars звезды"
        else -> "без звёзд"
    }
}

@Composable
fun Shawarma58App(progressStore: ProgressRepository) {
    val scope = rememberCoroutineScope()
    val progress by progressStore.progressFlow.collectAsState(initial = PlayerProgress())
    var screen by rememberSaveable(stateSaver = AppScreenSaver) { mutableStateOf<AppScreen>(AppScreen.Splash) }
    var splashDone by rememberSaveable { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        delay(850)
        splashDone = true
    }
    LaunchedEffect(splashDone, progress.onboardingSeen) {
        if (splashDone && screen == AppScreen.Splash) {
            screen = if (progress.onboardingSeen) AppScreen.Menu else AppScreen.Onboarding
        }
    }

    fun finishGame(result: ScoreResult) {
        scope.launch {
            if (result.isEndless) {
                progressStore.updateBestEndlessScore(result.score)
            } else if (result.isWin) {
                progressStore.completeLevel(result.levelId, result.stars)
            }
        }
        screen = AppScreen.Result(result)
    }

    when (val current = screen) {
        AppScreen.Splash -> SplashScreen()
        AppScreen.Onboarding -> OnboardingScreen(
            onStart = {
                scope.launch { progressStore.setOnboardingSeen() }
                screen = AppScreen.Menu
            },
        )
        AppScreen.Menu -> MenuScreen(
            progress = progress,
            onPlay = { screen = AppScreen.Levels },
            onEndless = { screen = AppScreen.Game(levelId = 0, isEndless = true) },
            onSettings = { screen = AppScreen.Settings },
            onAbout = { screen = AppScreen.About },
        )
        AppScreen.Levels -> LevelSelectScreen(
            progress = progress,
            onBack = { screen = AppScreen.Menu },
            onLevel = { screen = AppScreen.Game(levelId = it.id, isEndless = false) },
        )
        AppScreen.Settings -> SettingsScreen(
            progress = progress,
            onBack = { screen = AppScreen.Menu },
            onSettings = { settings ->
                scope.launch { progressStore.updateSettings(settings) }
            },
            onResetProgress = {
                scope.launch { progressStore.resetProgress() }
            },
        )
        AppScreen.About -> AboutScreen(onBack = { screen = AppScreen.Menu })
        is AppScreen.Game -> GameplayScreen(
            level = playableLevelFor(levelId = current.levelId, isEndless = current.isEndless),
            isEndless = current.isEndless,
            settings = progress.settings,
            onExit = { screen = AppScreen.Menu },
            onFinished = ::finishGame,
        )
        is AppScreen.Result -> ResultScreen(
            result = current.result,
            onMenu = { screen = AppScreen.Menu },
            onRetry = {
                screen = AppScreen.Game(
                    levelId = current.result.levelId,
                    isEndless = current.result.isEndless,
                )
            },
            onNext = {
                val nextLevel = current.result.levelId + 1
                screen = AppScreen.Game(levelId = nextLevel, isEndless = false)
            },
        )
    }
}

@Composable
private fun AppBackground(
    mood: ScreenMood = ScreenMood.Warm,
    content: @Composable () -> Unit,
) {
    val backgroundRes = when (mood) {
        ScreenMood.Levels -> R.drawable.bg_route_map
        ScreenMood.Gameplay -> R.drawable.bg_prep_station
        ScreenMood.Result -> R.drawable.bg_receipt_counter
        ScreenMood.Hero,
        ScreenMood.Quiet,
        ScreenMood.Warm
        -> R.drawable.bg_counter
    }
    val gradient = when (mood) {
        ScreenMood.Hero -> listOf(Color(0xF5233D38), Color(0xF6415D50), Color(0xF8FFE7BC))
        ScreenMood.Levels -> listOf(Color(0xC8F4FBF7), Color(0xB8E8F2E7), Color(0xD2FFF0D1))
        ScreenMood.Gameplay -> listOf(Color(0xD8232A27), Color(0xBA435F50), Color(0xDAFFF3DC))
        ScreenMood.Result -> listOf(Color(0xA8FFF8EA), Color(0x92EEF4EA), Color(0xB8FFE1BD))
        ScreenMood.Quiet -> listOf(Color(0xFAF7F3EA), Color(0xF6EEF5F1))
        ScreenMood.Warm -> listOf(Color(0xF8FFF7EA), Color(0xF2FFF1D7))
    }
    val imageAlpha = when (mood) {
        ScreenMood.Hero -> 0.42f
        ScreenMood.Gameplay -> 0.78f
        ScreenMood.Levels -> 0.82f
        ScreenMood.Result -> 0.72f
        ScreenMood.Quiet -> 0.08f
        ScreenMood.Warm -> 0.24f
    }
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background),
    ) {
        Image(
            painter = painterResource(backgroundRes),
            contentDescription = null,
            modifier = Modifier.fillMaxSize(),
            contentScale = ContentScale.Crop,
            alpha = imageAlpha,
        )
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(Brush.verticalGradient(gradient)),
        )
        if (mood == ScreenMood.Hero || mood == ScreenMood.Gameplay) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(128.dp)
                    .align(Alignment.TopCenter)
                    .background(
                        Brush.verticalGradient(
                            listOf(Color(0xAA10201C), Color.Transparent),
                        ),
                    ),
            )
        }
        if (mood == ScreenMood.Levels) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(7.dp)
                    .align(Alignment.TopCenter)
                    .background(
                        Brush.horizontalGradient(
                            listOf(Color(0xFF2F5D50), Color(0xFFE1A528), Color(0xFFD94E2F)),
                        ),
                    ),
            )
        }
        Box(
            modifier = Modifier
                .fillMaxSize()
                .systemBarsPadding(),
        ) {
            content()
        }
    }
}

@Composable
private fun SplashScreen() {
    AppBackground(ScreenMood.Hero) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(28.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
        ) {
            Image(
                painter = painterResource(R.drawable.ic_launcher_foreground),
                contentDescription = "Иконка Шаурма 58",
                modifier = Modifier
                    .size(148.dp)
                    .clip(RoundedCornerShape(32.dp)),
            )
            Spacer(Modifier.height(20.dp))
            Text(
                text = "Шаурма 58",
                style = MaterialTheme.typography.headlineLarge,
                fontWeight = FontWeight.Black,
                color = MaterialTheme.colorScheme.primary,
            )
            Text(
                text = "Собирай заказы, держи темп",
                style = MaterialTheme.typography.titleMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun OnboardingScreen(onStart: () -> Unit) {
    AppBackground(ScreenMood.Warm) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .testTag(UiTestTags.SCREEN_ONBOARDING)
                .verticalScroll(rememberScrollState())
                .padding(22.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Spacer(Modifier.height(16.dp))
            Image(
                painter = painterResource(R.drawable.art_onboarding_prep),
                contentDescription = "Подготовка заказа",
                modifier = Modifier
                    .fillMaxWidth()
                    .aspectRatio(1f)
                    .clip(RoundedCornerShape(28.dp)),
                contentScale = ContentScale.Crop,
            )
            Spacer(Modifier.height(22.dp))
            Text(
                text = "Заверни смену без ошибок",
                style = MaterialTheme.typography.headlineMedium,
                fontWeight = FontWeight.Black,
                textAlign = TextAlign.Center,
            )
            Spacer(Modifier.height(10.dp))
            Text(
                text = "Смотри состав заказа, выбирай ингредиенты и отдавай шаурму до конца таймера. Чем чище смена, тем больше звёзд.",
                style = MaterialTheme.typography.bodyLarge,
                textAlign = TextAlign.Center,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Spacer(Modifier.height(24.dp))
            PrimaryButton(text = "Начать смену", onClick = onStart)
        }
    }
}

@Composable
private fun MenuScreen(
    progress: PlayerProgress,
    onPlay: () -> Unit,
    onEndless: () -> Unit,
    onSettings: () -> Unit,
    onAbout: () -> Unit,
) {
    AppBackground(ScreenMood.Hero) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .testTag(UiTestTags.SCREEN_MENU)
                .verticalScroll(rememberScrollState())
                .padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            Spacer(Modifier.height(4.dp))
            MenuHero(progress = progress)
            StatPanel(progress = progress)
            MenuActionCard(
                title = "Играть",
                subtitle = "Продолжить карту смен",
                badge = "58",
                accent = MaterialTheme.colorScheme.primary,
                onClick = onPlay,
                modifier = Modifier.testTag(UiTestTags.MENU_PLAY),
            )
            MenuActionCard(
                title = "Бесконечная смена",
                subtitle = "90 секунд на чистую серию",
                badge = "∞",
                accent = MaterialTheme.colorScheme.secondary,
                onClick = onEndless,
                modifier = Modifier.testTag(UiTestTags.MENU_ENDLESS),
            )
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                UtilityMenuButton(
                    text = "Настройки",
                    onClick = onSettings,
                    modifier = Modifier
                        .weight(1f)
                        .testTag(UiTestTags.MENU_SETTINGS),
                )
                UtilityMenuButton(
                    text = "О проекте и приватность",
                    onClick = onAbout,
                    modifier = Modifier.weight(1f),
                )
            }
        }
    }
}

@Composable
private fun MenuHero(progress: PlayerProgress) {
    val levelCount = LevelCatalog.levels.size
    val completed = progress.completedLevelCount(levelCount)
    val completionProgress = completed / levelCount.toFloat()
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .height(214.dp)
            .clip(RoundedCornerShape(26.dp))
            .background(Color(0xFF203B34)),
    ) {
        Image(
            painter = painterResource(R.drawable.bg_counter),
            contentDescription = null,
            modifier = Modifier.fillMaxSize(),
            contentScale = ContentScale.Crop,
            alpha = 0.72f,
        )
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(
                    Brush.verticalGradient(
                        listOf(Color(0x3310201C), Color(0xEE10201C)),
                    ),
                ),
        )
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(18.dp),
            verticalArrangement = Arrangement.SpaceBetween,
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Surface(
                    color = Color.White.copy(alpha = 0.9f),
                    shape = CircleShape,
                    modifier = Modifier.size(58.dp),
                ) {
                    Image(
                        painter = painterResource(R.drawable.ic_launcher_foreground),
                        contentDescription = "Иконка Шаурма 58",
                        modifier = Modifier.padding(4.dp),
                    )
                }
                Spacer(Modifier.width(12.dp))
                Column {
                    Text(
                        text = "Шаурма 58",
                        style = MaterialTheme.typography.headlineMedium,
                        fontWeight = FontWeight.Black,
                        color = Color.White,
                    )
                    Text(
                        text = "Точка открыта",
                        style = MaterialTheme.typography.labelLarge,
                        color = Color(0xFFFFD677),
                        fontWeight = FontWeight.Bold,
                    )
                }
            }
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(
                    text = "Собрано смен: $completed/$levelCount",
                    style = MaterialTheme.typography.titleMedium,
                    color = Color.White,
                    fontWeight = FontWeight.Black,
                )
                LinearProgressIndicator(
                    progress = { completionProgress.coerceIn(0f, 1f) },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(9.dp)
                        .clip(RoundedCornerShape(20.dp)),
                    color = Color(0xFFFFC447),
                    trackColor = Color.White.copy(alpha = 0.26f),
                )
            }
        }
    }
}

@Composable
private fun StatPanel(progress: PlayerProgress) {
    val levelCount = LevelCatalog.levels.size
    val maxStars = levelCount * MAX_STARS_PER_LEVEL
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(10.dp),
        color = Color(0xFF152822),
        border = BorderStroke(1.dp, Color.White.copy(alpha = 0.14f)),
    ) {
        Column(
            modifier = Modifier.padding(horizontal = 14.dp, vertical = 12.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    text = "Касса сегодня",
                    style = MaterialTheme.typography.labelLarge,
                    color = Color(0xFFFFD677),
                    fontWeight = FontWeight.Black,
                    modifier = Modifier.weight(1f),
                )
                Text(
                    text = "${progress.completedLevelCount(levelCount)}/$levelCount смен",
                    style = MaterialTheme.typography.labelLarge,
                    color = Color.White,
                    fontWeight = FontWeight.Bold,
                )
            }
            ReceiptDivider(color = Color.White.copy(alpha = 0.24f))
            Row(
                horizontalArrangement = Arrangement.spacedBy(10.dp),
                modifier = Modifier.fillMaxWidth(),
            ) {
                CashStat(
                    label = "Смены",
                    value = "${progress.completedLevelCount(levelCount)}/$levelCount",
                    accent = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.weight(1f),
                )
                CashStat(
                    label = "Звёзды",
                    value = "${progress.totalStars(levelCount)}/$maxStars",
                    accent = MaterialTheme.colorScheme.tertiary,
                    modifier = Modifier.weight(1f),
                )
                CashStat(
                    label = "Рекорд",
                    value = progress.safeBestEndlessScore().toString(),
                    accent = MaterialTheme.colorScheme.secondary,
                    modifier = Modifier.weight(1f),
                )
            }
        }
    }
}

@Composable
private fun CashStat(
    label: String,
    value: String,
    accent: Color,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier,
        verticalArrangement = Arrangement.spacedBy(4.dp),
        horizontalAlignment = Alignment.Start,
    ) {
        Box(
            modifier = Modifier
                .width(28.dp)
                .height(4.dp)
                .clip(RoundedCornerShape(8.dp))
                .background(accent),
        )
        Text(
            text = value,
            style = MaterialTheme.typography.titleLarge,
            fontWeight = FontWeight.Black,
            color = Color.White,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
        Text(
            text = label,
            style = MaterialTheme.typography.labelSmall,
            color = Color.White.copy(alpha = 0.72f),
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

@Composable
private fun MenuActionCard(
    title: String,
    subtitle: String,
    badge: String,
    accent: Color,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Surface(
        modifier = modifier
            .fillMaxWidth()
            .height(98.dp)
            .clip(RoundedCornerShape(10.dp))
            .semantics {
                role = Role.Button
                contentDescription = "$title. $subtitle"
            }
            .clickable(onClick = onClick),
        shape = RoundedCornerShape(10.dp),
        color = Color(0xFFFFFBF2),
        border = BorderStroke(1.dp, accent.copy(alpha = 0.46f)),
    ) {
        Box {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .background(
                        Brush.horizontalGradient(
                            listOf(accent.copy(alpha = 0.16f), Color.Transparent, Color.Transparent),
                        ),
                    ),
            )
            Row(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(end = 14.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Box(
                    modifier = Modifier
                        .width(10.dp)
                        .fillMaxSize()
                        .background(accent),
                )
                TicketPunchRail(color = accent.copy(alpha = 0.42f))
                Column(
                    modifier = Modifier
                        .weight(1f)
                        .padding(start = 10.dp, end = 10.dp),
                    verticalArrangement = Arrangement.Center,
                ) {
                    Surface(
                        color = accent.copy(alpha = 0.14f),
                        shape = RoundedCornerShape(50),
                    ) {
                        Text(
                            text = if (badge == "∞") "Режим $badge" else "Маршрут $badge",
                            modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp),
                            style = MaterialTheme.typography.labelMedium,
                            color = accent,
                            fontWeight = FontWeight.Black,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                        )
                    }
                    Spacer(Modifier.height(6.dp))
                    Text(
                        text = title,
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.Black,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                    Text(
                        text = subtitle,
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
                Surface(
                    color = accent,
                    shape = CircleShape,
                    modifier = Modifier.size(44.dp),
                ) {
                    Box(contentAlignment = Alignment.Center) {
                        Text(
                            text = "›",
                            style = MaterialTheme.typography.headlineSmall,
                            color = Color.White,
                            fontWeight = FontWeight.Black,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun TicketPunchRail(color: Color) {
    Column(
        modifier = Modifier
            .width(24.dp)
            .height(98.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.SpaceEvenly,
    ) {
        repeat(4) {
            Box(
                modifier = Modifier
                    .size(7.dp)
                    .clip(CircleShape)
                    .background(color),
            )
        }
    }
}

@Composable
private fun UtilityMenuButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    OutlinedButton(
        onClick = onClick,
        modifier = modifier.height(60.dp),
        shape = RoundedCornerShape(16.dp),
        contentPadding = PaddingValues(horizontal = 10.dp),
    ) {
        Text(
            text = text,
            fontWeight = FontWeight.Bold,
            textAlign = TextAlign.Center,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

@Composable
private fun LevelSelectScreen(
    progress: PlayerProgress,
    onBack: () -> Unit,
    onLevel: (LevelConfig) -> Unit,
) {
    BackHandler(onBack = onBack)
    val levelCount = LevelCatalog.levels.size
    val completed = progress.completedLevelCount(levelCount)
    val spotlightLevelId = (completed + 1).coerceAtMost(levelCount).coerceAtLeast(1)
    val spotlightLevel = LevelCatalog.levelById(spotlightLevelId)
    AppBackground(ScreenMood.Levels) {
        Column(
            Modifier
                .fillMaxSize()
                .testTag(UiTestTags.SCREEN_LEVELS),
        ) {
            Header(title = "Выбор смены", onBack = onBack)
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .verticalScroll(rememberScrollState())
                    .padding(horizontal = 16.dp),
                verticalArrangement = Arrangement.spacedBy(14.dp),
            ) {
                LevelMapProgress(progress = progress)
                SpotlightLevelCard(
                    level = spotlightLevel,
                    stars = progress.starsFor(spotlightLevel.id),
                    unlocked = progress.isLevelUnlocked(spotlightLevel.id),
                    completed = progress.completedLevels.contains(spotlightLevel.id),
                    onClick = { onLevel(spotlightLevel) },
                )
                LevelCatalog.levels.chunked(8).forEachIndexed { chapterIndex, levels ->
                    ChapterHeader(chapterIndex = chapterIndex, progress = progress)
                    levels
                        .filterNot { it.id == spotlightLevel.id }
                        .chunked(2)
                        .forEach { rowLevels ->
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.spacedBy(12.dp),
                            ) {
                                rowLevels.forEach { level ->
                                    val unlocked = progress.isLevelUnlocked(level.id)
                                    LevelTile(
                                        level = level,
                                        unlocked = unlocked,
                                        stars = progress.starsFor(level.id),
                                        completed = progress.completedLevels.contains(level.id),
                                        onClick = { if (unlocked) onLevel(level) },
                                        modifier = Modifier.weight(1f),
                                    )
                                }
                                if (rowLevels.size == 1) {
                                    Spacer(Modifier.weight(1f))
                                }
                            }
                        }
                }
                Spacer(Modifier.height(18.dp))
            }
        }
    }
}

@Composable
private fun LevelMapProgress(progress: PlayerProgress) {
    val levelCount = LevelCatalog.levels.size
    val completed = progress.completedLevelCount(levelCount)
    val opened = (completed + 1).coerceAtMost(levelCount)
    val currentChapter = ((opened - 1).coerceAtLeast(0) / 8).coerceIn(0, 2)
    Surface(
        color = Color(0xFF213E36),
        shape = RoundedCornerShape(24.dp),
        border = BorderStroke(1.dp, Color.White.copy(alpha = 0.14f)),
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = 4.dp),
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = "Маршрут 58",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Black,
                    color = Color.White,
                )
                Text(
                    text = "Открыто $opened/$levelCount",
                    style = MaterialTheme.typography.labelLarge,
                    color = Color(0xFFFFD467),
                    fontWeight = FontWeight.Bold,
                )
            }
            LinearProgressIndicator(
                progress = { (completed / levelCount.toFloat()).coerceIn(0f, 1f) },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(8.dp)
                    .clip(RoundedCornerShape(20.dp)),
                color = Color(0xFFFFC447),
                trackColor = Color.White.copy(alpha = 0.18f),
            )
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                listOf("Вокзал", "Обед", "Вечер").forEachIndexed { index, label ->
                    RouteStopChip(
                        label = label,
                        active = index <= currentChapter,
                        accent = when (index) {
                            0 -> Color(0xFF79C98F)
                            1 -> Color(0xFFFFC447)
                            else -> Color(0xFFFF8A63)
                        },
                        modifier = Modifier.weight(1f),
                    )
                }
            }
        }
    }
}

@Composable
private fun RouteStopChip(
    label: String,
    active: Boolean,
    accent: Color,
    modifier: Modifier = Modifier,
) {
    Surface(
        color = if (active) accent.copy(alpha = 0.2f) else Color.White.copy(alpha = 0.08f),
        shape = RoundedCornerShape(14.dp),
        border = BorderStroke(1.dp, if (active) accent.copy(alpha = 0.52f) else Color.White.copy(alpha = 0.1f)),
        modifier = modifier.height(36.dp),
    ) {
        Box(contentAlignment = Alignment.Center) {
            Text(
                text = label,
                style = MaterialTheme.typography.labelMedium,
                color = if (active) Color.White else Color.White.copy(alpha = 0.62f),
                fontWeight = FontWeight.Black,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
    }
}

@Composable
private fun SpotlightLevelCard(
    level: LevelConfig,
    stars: Int,
    unlocked: Boolean,
    completed: Boolean,
    onClick: () -> Unit,
) {
    val starsLabel = starsAccessibilityLabel(stars)
    val accent = levelAccent(level)
    val status = levelStatusText(unlocked = unlocked, completed = completed, stars = stars)
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .height(168.dp)
            .clip(RoundedCornerShape(28.dp))
            .semantics {
                contentDescription = "Смена ${level.id}, ${level.speedLabel}, ${levelAccessibilityWorkloadLabel(level)}, $starsLabel"
                stateDescription = if (unlocked) "Доступна" else "Закрыта"
                if (unlocked) role = Role.Button
            }
            .clickable(enabled = unlocked, onClick = onClick)
            .testTag(UiTestTags.levelTile(level.id)),
        shape = RoundedCornerShape(28.dp),
        color = Color.Transparent,
        border = BorderStroke(1.dp, accent.copy(alpha = 0.42f)),
        tonalElevation = 3.dp,
    ) {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(
                    Brush.horizontalGradient(
                        listOf(accent, Color(0xFF243D36)),
                    ),
                ),
        ) {
            Box(
                modifier = Modifier
                    .size(144.dp)
                    .align(Alignment.CenterEnd)
                    .background(Color.White.copy(alpha = 0.06f), CircleShape),
            )
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(18.dp),
                verticalArrangement = Arrangement.SpaceBetween,
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        text = if (completed) "Повтор смены" else "Сейчас на линии",
                        style = MaterialTheme.typography.labelLarge,
                        color = Color.White.copy(alpha = 0.84f),
                        fontWeight = FontWeight.Bold,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                    Surface(
                        color = Color.White.copy(alpha = 0.16f),
                        shape = RoundedCornerShape(14.dp),
                    ) {
                        Text(
                            text = status,
                            modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp),
                            style = MaterialTheme.typography.labelMedium,
                            color = Color.White,
                            fontWeight = FontWeight.Black,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                        )
                    }
                }
                Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text(
                        text = level.title,
                        style = MaterialTheme.typography.headlineLarge,
                        fontWeight = FontWeight.Black,
                        color = Color.White,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                    Text(
                        text = level.subtitle,
                        style = MaterialTheme.typography.bodyLarge,
                        color = Color.White.copy(alpha = 0.84f),
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        text = levelWorkloadLabel(level),
                        style = MaterialTheme.typography.titleMedium,
                        color = Color(0xFFFFF1D7),
                        fontWeight = FontWeight.Black,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                    Text(
                        text = "★".repeat(stars).ifBlank { "без звёзд" },
                        style = MaterialTheme.typography.labelLarge,
                        color = Color(0xFFFFD467),
                        fontWeight = FontWeight.Black,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
            }
        }
    }
}

@Composable
private fun ChapterHeader(chapterIndex: Int, progress: PlayerProgress) {
    val chapterLevels = LevelCatalog.levels.drop(chapterIndex * 8).take(8)
    val completedInChapter = chapterLevels.count { it.id in progress.completedLevels }
    val accent = when (chapterIndex) {
        0 -> Color(0xFF2F5D50)
        1 -> Color(0xFFB68113)
        else -> Color(0xFFD94E2F)
    }
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = 4.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.Bottom,
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = levelChapterLabel(chapterIndex * 8 + 1),
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Black,
                color = MaterialTheme.colorScheme.onSurface,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Text(
                text = levelChapterSubtitle(chapterIndex),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
        Surface(
            color = accent.copy(alpha = 0.14f),
            shape = RoundedCornerShape(14.dp),
        ) {
            Text(
                text = "$completedInChapter/8",
                modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp),
                style = MaterialTheme.typography.labelLarge,
                color = accent,
                fontWeight = FontWeight.Black,
            )
        }
    }
}

@Composable
private fun LevelTile(
    level: LevelConfig,
    unlocked: Boolean,
    stars: Int,
    completed: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val starsLabel = starsAccessibilityLabel(stars)
    val workloadLabel = levelWorkloadLabel(level)
    val accent = levelAccent(level)
    val mutedAccent = accent.copy(alpha = if (unlocked) 1f else 0.34f)
    val status = levelStatusText(unlocked = unlocked, completed = completed, stars = stars)
    Surface(
        modifier = modifier
            .height(134.dp)
            .clip(RoundedCornerShape(20.dp))
            .semantics {
                contentDescription = "Смена ${level.id}, ${level.speedLabel}, ${levelAccessibilityWorkloadLabel(level)}, $starsLabel"
                stateDescription = if (unlocked) "Доступна" else "Закрыта"
                if (unlocked) role = Role.Button
            }
            .clickable(enabled = unlocked, onClick = onClick)
            .testTag(UiTestTags.levelTile(level.id)),
        color = if (unlocked) Color(0xFFFFFCF6) else Color(0xFFE4E1DA),
        shape = RoundedCornerShape(20.dp),
        border = BorderStroke(1.dp, mutedAccent.copy(alpha = 0.42f)),
        tonalElevation = if (unlocked) 3.dp else 0.dp,
    ) {
        Box(modifier = Modifier.fillMaxSize()) {
            Row(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(10.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Box(
                    modifier = Modifier
                        .width(26.dp)
                        .height(98.dp),
                ) {
                    Box(
                        modifier = Modifier
                            .width(3.dp)
                            .height(92.dp)
                            .align(Alignment.Center)
                            .clip(RoundedCornerShape(8.dp))
                            .background(mutedAccent.copy(alpha = 0.34f)),
                    )
                    Box(
                        modifier = Modifier
                            .size(18.dp)
                            .align(Alignment.Center)
                            .clip(CircleShape)
                            .background(if (unlocked) mutedAccent else Color(0xFFBEB8AD)),
                    )
                }
                Spacer(Modifier.width(8.dp))
                Column(
                    modifier = Modifier.weight(1f),
                    verticalArrangement = Arrangement.SpaceBetween,
                ) {
                    Text(
                        text = levelChapterLabel(level.id),
                        style = MaterialTheme.typography.labelSmall,
                        color = if (unlocked) mutedAccent else MaterialTheme.colorScheme.onSurfaceVariant,
                        fontWeight = FontWeight.Black,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                    Text(
                        text = level.title,
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.Black,
                        color = if (unlocked) MaterialTheme.colorScheme.onSurface else MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                    Text(
                        text = workloadLabel,
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Surface(
                            color = mutedAccent.copy(alpha = if (unlocked) 0.14f else 0.08f),
                            shape = RoundedCornerShape(10.dp),
                        ) {
                            Text(
                                text = status,
                                modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp),
                                style = MaterialTheme.typography.labelSmall,
                                color = if (unlocked) mutedAccent else MaterialTheme.colorScheme.onSurfaceVariant,
                                fontWeight = FontWeight.Bold,
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis,
                            )
                        }
                        Text(
                            text = if (unlocked) "★".repeat(stars).ifBlank { "—" } else "—",
                            style = MaterialTheme.typography.labelMedium,
                            color = if (stars > 0) MaterialTheme.colorScheme.tertiary else MaterialTheme.colorScheme.onSurfaceVariant,
                            textAlign = TextAlign.End,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                        )
                    }
                }
            }
        }
    }
}

private fun levelChapterSubtitle(chapterIndex: Int): String {
    return when (chapterIndex) {
        0 -> "разогрев и короткие заказы"
        1 -> "наплыв в обеденное окно"
        else -> "вечерний темп и серия"
    }
}

private fun levelChapterLabel(levelId: Int): String {
    return when ((levelId - 1).coerceAtLeast(0) / 8) {
        0 -> "Вокзал"
        1 -> "Обед"
        else -> "Вечер"
    }
}

private fun levelAccent(level: LevelConfig): Color {
    return when ((level.id - 1).coerceAtLeast(0) / 8) {
        0 -> Color(0xFF2F5D50)
        1 -> Color(0xFFB68113)
        else -> Color(0xFFD94E2F)
    }
}

private fun levelStatusText(
    unlocked: Boolean,
    completed: Boolean,
    stars: Int,
): String {
    return when {
        !unlocked -> "закрыто"
        completed || stars > 0 -> "готово"
        else -> "на линии"
    }
}

@Composable
private fun SettingsScreen(
    progress: PlayerProgress,
    onBack: () -> Unit,
    onSettings: (GameSettings) -> Unit,
    onResetProgress: () -> Unit,
) {
    var resetArmed by rememberSaveable { mutableStateOf(false) }
    BackHandler(onBack = onBack)
    AppBackground(ScreenMood.Quiet) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .testTag(UiTestTags.SCREEN_SETTINGS)
                .verticalScroll(rememberScrollState()),
        ) {
            Header(title = "Настройки", onBack = onBack)
            Column(
                modifier = Modifier.padding(20.dp),
                verticalArrangement = Arrangement.spacedBy(14.dp),
            ) {
                SettingRow(
                    title = "Звуковые сигналы",
                    subtitle = "Короткий отклик на правильный или неверный заказ",
                    checked = progress.settings.soundEnabled,
                    switchTag = UiTestTags.SOUND_SWITCH,
                    onChecked = { onSettings(progress.settings.copy(soundEnabled = it)) },
                )
                SettingRow(
                    title = "Меньше анимации",
                    subtitle = "Таймер обновляется без плавного перехода",
                    checked = progress.settings.reducedMotion,
                    switchTag = UiTestTags.REDUCED_MOTION_SWITCH,
                    onChecked = { onSettings(progress.settings.copy(reducedMotion = it)) },
                )
                InfoPanel(
                    title = "Локальный прогресс",
                    body = "Сброс удалит пройденные смены, звёзды, рекорд и обучение на этом устройстве. Настройки звука и анимации останутся как сейчас.",
                )
                if (resetArmed) {
                    PrimaryButton(
                        text = "Удалить прогресс",
                        onClick = {
                            onResetProgress()
                            resetArmed = false
                        },
                        modifier = Modifier.testTag(UiTestTags.CONFIRM_RESET_PROGRESS),
                    )
                    SecondaryButton(text = "Оставить как есть", onClick = { resetArmed = false })
                } else {
                    SecondaryButton(
                        text = "Сбросить прогресс",
                        onClick = { resetArmed = true },
                        modifier = Modifier.testTag(UiTestTags.RESET_PROGRESS),
                    )
                }
                InfoPanel(
                    title = "Приватность",
                    body = "Игра работает офлайн, не просит разрешения, не использует аккаунт и не передаёт персональные данные.",
                )
            }
        }
    }
}

@Composable
private fun SettingRow(
    title: String,
    subtitle: String,
    checked: Boolean,
    switchTag: String,
    onChecked: (Boolean) -> Unit,
) {
    Surface(
        color = MaterialTheme.colorScheme.surface,
        shape = RoundedCornerShape(18.dp),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Row(
            modifier = Modifier.padding(16.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(text = title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                Text(text = subtitle, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            Switch(
                checked = checked,
                onCheckedChange = onChecked,
                modifier = Modifier.testTag(switchTag),
            )
        }
    }
}

@Composable
private fun AboutScreen(onBack: () -> Unit) {
    BackHandler(onBack = onBack)
    AppBackground(ScreenMood.Quiet) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState()),
        ) {
            Header(title = "О проекте", onBack = onBack)
            Column(
                modifier = Modifier.padding(20.dp),
                verticalArrangement = Arrangement.spacedBy(14.dp),
            ) {
                InfoPanel(
                    title = "Шаурма 58",
                    body = "Короткая офлайн-игра для Android: собирай заказы, следи за таймером и открывай новые смены.",
                )
                InfoPanel(
                    title = "Данные",
                    body = "На устройстве сохраняются только прогресс уровней, настройки и рекорд бесконечной смены. Интернет и аккаунт не нужны.",
                )
                InfoPanel(
                    title = "Контент",
                    body = "Иллюстрации созданы через ImageGen специально для этого проекта. В игре нет чужих брендов, персонажей или рекламных интеграций.",
                )
            }
        }
    }
}

@Composable
private fun GameplayScreen(
    level: LevelConfig,
    isEndless: Boolean,
    settings: GameSettings,
    onExit: () -> Unit,
    onFinished: (ScoreResult) -> Unit,
) {
    var isPaused by rememberSaveable(level.id, isEndless) { mutableStateOf(false) }
    BackHandler(onBack = { if (isPaused) isPaused = false else isPaused = true })
    var session by rememberSaveable(level.id, isEndless, stateSaver = GameSessionSaver) {
        mutableStateOf(GameEngine.start(level = level, isEndless = isEndless))
    }
    var lastServeFeedback by remember(level.id, isEndless) { mutableStateOf<ServeFeedback?>(null) }
    var finishHandled by rememberSaveable(level.id, isEndless) { mutableStateOf(false) }
    val haptics = LocalHapticFeedback.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val tone = remember {
        runCatching { ToneGenerator(AudioManager.STREAM_MUSIC, 55) }.getOrNull()
    }
    DisposableEffect(tone) {
        onDispose { tone?.release() }
    }
    DisposableEffect(lifecycleOwner, session.isFinished) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_STOP && !session.isFinished) {
                isPaused = true
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }

    LaunchedEffect(level.id, isEndless, isPaused) {
        while (!session.isFinished && !isPaused) {
            delay(1_000)
            session = GameEngine.tick(session)
        }
    }
    LaunchedEffect(session.isFinished, finishHandled) {
        if (session.isFinished && !finishHandled) {
            finishHandled = true
            onFinished(GameEngine.result(session))
        }
    }

    AppBackground(ScreenMood.Gameplay) {
        Box(modifier = Modifier.fillMaxSize()) {
            Column(
                Modifier
                    .fillMaxSize()
                    .testTag(UiTestTags.SCREEN_GAMEPLAY),
            ) {
                Header(title = if (isEndless) "Бесконечная смена" else level.title, onBack = onExit, inverted = true)
                GameTopBar(session = session, settings = settings)
                OrderPanel(order = session.activeOrder)
                SelectedPanel(selected = session.selectedIngredients)
                ServeFeedbackPanel(feedback = lastServeFeedback)
                IngredientGrid(
                    selected = session.selectedIngredients,
                    onToggle = {
                        if (!isPaused) {
                            haptics.performHapticFeedback(ingredientToggleHaptic())
                            session = GameEngine.toggleIngredient(session, it)
                        }
                    },
                    modifier = Modifier.weight(1f),
                )
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp, vertical = 10.dp),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    OutlinedButton(
                        onClick = { isPaused = true },
                        modifier = Modifier
                            .weight(0.9f)
                            .height(52.dp)
                            .testTag(UiTestTags.PAUSE_GAME),
                        enabled = !session.isFinished,
                    ) {
                        Text("Пауза")
                    }
                    OutlinedButton(
                        onClick = {
                            session = GameEngine.clear(session)
                        },
                        modifier = Modifier
                            .weight(1f)
                            .height(52.dp)
                            .testTag(UiTestTags.CLEAR_ORDER),
                        enabled = session.selectedIngredients.isNotEmpty() && !isPaused && !session.isFinished,
                    ) {
                        Text("Сбросить")
                    }
                    Button(
                        onClick = {
                            val correct = GameRules.matches(session.activeOrder, session.selectedIngredients)
                            val beforeServe = session
                            haptics.performHapticFeedback(orderFeedbackHaptic(correct))
                            if (shouldPlayOrderFeedback(settings)) {
                                runCatching { tone?.startTone(orderFeedbackTone(correct), 90) }
                            }
                            val afterServe = GameEngine.serve(beforeServe)
                            lastServeFeedback = serveFeedback(correct = correct, before = beforeServe, after = afterServe)
                            session = afterServe
                        },
                        modifier = Modifier
                            .weight(1.35f)
                            .height(52.dp)
                            .testTag(UiTestTags.SERVE_ORDER),
                        enabled = session.selectedIngredients.isNotEmpty() && !isPaused && !session.isFinished,
                    ) {
                        Text("Отдать заказ")
                    }
                }
            }
            if (isPaused) {
                PauseOverlay(
                    onResume = { isPaused = false },
                    onExit = onExit,
                )
            }
        }
    }
}

@Composable
private fun PauseOverlay(
    onResume: () -> Unit,
    onExit: () -> Unit,
) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0x99000000))
            .testTag(UiTestTags.PAUSE_OVERLAY),
        contentAlignment = Alignment.Center,
    ) {
        Surface(
            color = MaterialTheme.colorScheme.surface,
            shape = RoundedCornerShape(22.dp),
            modifier = Modifier
                .fillMaxWidth()
                .padding(24.dp),
        ) {
            Column(
                modifier = Modifier.padding(18.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Text("Пауза", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Black)
                Text(
                    text = "Таймер остановлен. Можно продолжить смену или выйти в меню.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    textAlign = TextAlign.Center,
                )
                PrimaryButton(
                    text = "Продолжить",
                    onClick = onResume,
                    modifier = Modifier.testTag(UiTestTags.RESUME_GAME),
                )
                SecondaryButton(text = "В меню", onClick = onExit)
            }
        }
    }
}

@Composable
private fun GameTopBar(session: GameSession, settings: GameSettings) {
    val targetProgress = session.remainingSeconds / session.level.durationSeconds.toFloat()
    val timerProgress by animateFloatAsState(
        targetValue = targetProgress.coerceIn(0f, 1f),
        animationSpec = if (settings.reducedMotion) snap() else tween(durationMillis = 360),
        label = "timerProgress",
    )
    Surface(
        color = Color(0xFF1F332E),
        shape = RoundedCornerShape(20.dp),
        border = BorderStroke(1.dp, Color.White.copy(alpha = 0.12f)),
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 8.dp),
    ) {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(9.dp),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                ConsoleMetric(
                    text = "⏱ ${session.remainingSeconds}с",
                    accent = Color(0xFFFFC447),
                    modifier = Modifier.weight(0.78f),
                )
                ConsoleMetric(
                    text = "Заказы ${session.servedOrders}/${if (session.isEndless) "∞" else session.level.targetOrders}",
                    accent = Color(0xFF79C98F),
                    modifier = Modifier.weight(1.15f),
                )
                ConsoleMetric(
                    text = "Ошибки ${session.mistakes}/${session.level.maxMistakes}",
                    accent = Color(0xFFFF8A63),
                    modifier = Modifier.weight(1f),
                )
            }
            LinearProgressIndicator(
                progress = { timerProgress },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(10.dp)
                    .clip(RoundedCornerShape(20.dp)),
                color = if (timerProgress < 0.28f) Color(0xFFFF7A55) else Color(0xFFFFC447),
                trackColor = Color.White.copy(alpha = 0.18f),
            )
            Text(
                text = "Серия ${session.comboStreak} · следующий бонус +${GameRules.streakBonus(session.comboStreak + 1)}",
                style = MaterialTheme.typography.labelLarge,
                color = Color(0xFFEAF7EF),
                fontWeight = FontWeight.Bold,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
    }
}

@Composable
private fun ConsoleMetric(
    text: String,
    accent: Color,
    modifier: Modifier = Modifier,
) {
    Surface(
        color = Color.White.copy(alpha = 0.09f),
        shape = RoundedCornerShape(13.dp),
        border = BorderStroke(1.dp, accent.copy(alpha = 0.28f)),
        modifier = modifier.height(38.dp),
    ) {
        Text(
            text = text,
            modifier = Modifier.padding(horizontal = 7.dp, vertical = 9.dp),
            style = MaterialTheme.typography.labelMedium,
            color = Color.White,
            fontWeight = FontWeight.Bold,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

@Composable
private fun OrderPanel(order: RecipeOrder) {
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 8.dp),
        shape = RoundedCornerShape(24.dp),
        color = Color(0xFFFFFCF6),
        border = BorderStroke(1.dp, Color(0x332F5D50)),
        tonalElevation = 3.dp,
    ) {
        Row(
            modifier = Modifier.padding(12.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(
                modifier = Modifier
                    .width(22.dp)
                    .height(116.dp),
            ) {
                Box(
                    modifier = Modifier
                        .width(4.dp)
                        .height(112.dp)
                        .align(Alignment.Center)
                        .clip(RoundedCornerShape(12.dp))
                        .background(MaterialTheme.colorScheme.secondary.copy(alpha = 0.42f)),
                )
                repeat(4) { index ->
                    Box(
                        modifier = Modifier
                            .padding(top = (index * 31).dp)
                            .size(10.dp)
                            .align(Alignment.TopCenter)
                            .clip(CircleShape)
                            .background(MaterialTheme.colorScheme.secondary),
                    )
                }
            }
            Spacer(Modifier.width(10.dp))
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Image(
                    painter = painterResource(imageFor(order.customer)),
                    contentDescription = order.customer.title,
                    modifier = Modifier
                        .size(82.dp)
                        .clip(RoundedCornerShape(20.dp)),
                    contentScale = ContentScale.Crop,
                )
                Spacer(Modifier.height(6.dp))
                Surface(
                    color = Color(0xFFEAF4E8),
                    shape = RoundedCornerShape(11.dp),
                ) {
                    Text(
                        text = "Заказ #${order.id}",
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp),
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.primary,
                        fontWeight = FontWeight.Black,
                        maxLines = 1,
                    )
                }
            }
            Spacer(Modifier.width(13.dp))
            Column(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(7.dp),
            ) {
                Text(
                    order.customer.title,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Black,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                Text(
                    order.customer.line,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(16.dp))
                        .background(Color(0xFFEAF4E8)),
                ) {
                    Column(
                        modifier = Modifier.padding(horizontal = 11.dp, vertical = 8.dp),
                        verticalArrangement = Arrangement.spacedBy(3.dp),
                    ) {
                        Text(
                            order.title,
                            style = MaterialTheme.typography.titleSmall,
                            fontWeight = FontWeight.Black,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                        )
                        Text(
                            order.ingredients.joinToString(" · ") { it.title },
                            style = MaterialTheme.typography.bodyMedium,
                            maxLines = 2,
                            overflow = TextOverflow.Ellipsis,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun SelectedPanel(selected: List<Ingredient>) {
    val hasSelection = selected.isNotEmpty()
    Surface(
        color = if (hasSelection) Color(0xFF233C35) else Color(0xFFFFE7C6),
        shape = RoundedCornerShape(20.dp),
        modifier = Modifier
            .fillMaxWidth()
            .testTag(UiTestTags.SELECTED_PANEL)
            .padding(horizontal = 16.dp, vertical = 4.dp),
        border = BorderStroke(
            1.dp,
            if (hasSelection) Color.White.copy(alpha = 0.14f) else Color(0x55D94E2F),
        ),
    ) {
        Column(
            modifier = Modifier.padding(horizontal = 13.dp, vertical = 10.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier
                            .size(10.dp)
                            .clip(CircleShape)
                            .background(if (hasSelection) Color(0xFFFFD467) else MaterialTheme.colorScheme.secondary),
                    )
                    Spacer(Modifier.width(8.dp))
                    Text(
                        text = "Линия сборки",
                        style = MaterialTheme.typography.labelLarge,
                        color = if (hasSelection) Color.White else MaterialTheme.colorScheme.onSurfaceVariant,
                        fontWeight = FontWeight.Black,
                        maxLines = 1,
                    )
                }
                Text(
                    text = "${selected.size}/5",
                    style = MaterialTheme.typography.labelMedium,
                    color = if (hasSelection) Color(0xFFFFD467) else MaterialTheme.colorScheme.secondary,
                    fontWeight = FontWeight.Black,
                    maxLines = 1,
                )
            }
            Text(
                text = if (selected.isEmpty()) "Состав пока пуст" else selected.joinToString(" · ") { it.shortTitle },
                style = MaterialTheme.typography.bodyMedium,
                color = if (hasSelection) Color.White else MaterialTheme.colorScheme.onSurface,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
        }
    }
}

@Composable
private fun ServeFeedbackPanel(feedback: ServeFeedback?) {
    if (feedback == null) return
    val accent = if (feedback.positive) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.secondary
    Surface(
        color = if (feedback.positive) Color(0xFFE5F3DE) else Color(0xFFFFE0CE),
        shape = RoundedCornerShape(18.dp),
        modifier = Modifier
            .fillMaxWidth()
            .testTag(UiTestTags.SERVE_FEEDBACK)
            .padding(horizontal = 16.dp, vertical = 4.dp),
        border = BorderStroke(1.dp, accent.copy(alpha = 0.28f)),
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 9.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(
                modifier = Modifier
                    .width(5.dp)
                    .height(42.dp)
                    .clip(RoundedCornerShape(8.dp))
                    .background(accent),
            )
            Spacer(Modifier.width(10.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = feedback.title,
                    style = MaterialTheme.typography.labelLarge,
                    fontWeight = FontWeight.Black,
                    color = accent,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                Text(
                    text = feedback.body,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
        }
    }
}

@Composable
private fun IngredientGrid(
    selected: List<Ingredient>,
    onToggle: (Ingredient) -> Unit,
    modifier: Modifier = Modifier,
) {
    LazyVerticalGrid(
        columns = GridCells.Fixed(4),
        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
        modifier = modifier
            .fillMaxWidth()
            .testTag(UiTestTags.INGREDIENT_GRID)
    ) {
        items(Ingredient.entries.toList()) { ingredient ->
            IngredientTile(
                ingredient = ingredient,
                selected = selected.contains(ingredient),
                onClick = { onToggle(ingredient) },
            )
        }
    }
}

@Composable
private fun IngredientTile(
    ingredient: Ingredient,
    selected: Boolean,
    onClick: () -> Unit,
) {
    val selectedState = if (selected) "Выбран" else "Не выбран"
    val accent = ingredientAccent(ingredient)
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .aspectRatio(0.78f)
            .clip(RoundedCornerShape(18.dp))
            .semantics {
                contentDescription = "Ингредиент ${ingredient.title}"
                stateDescription = selectedState
                role = Role.Button
            }
            .clickable(onClick = onClick)
            .testTag(UiTestTags.ingredientTile(ingredient)),
        color = if (selected) accent.copy(alpha = 0.18f) else Color(0xFFFFFCF6),
        shape = RoundedCornerShape(18.dp),
        border = BorderStroke(2.dp, if (selected) accent else Color(0x202A211B)),
        tonalElevation = if (selected) 4.dp else 1.dp,
    ) {
        Box(modifier = Modifier.fillMaxSize()) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(7.dp)
                    .align(Alignment.TopCenter)
                    .background(accent),
            )
            Surface(
                color = if (selected) accent else accent.copy(alpha = 0.12f),
                shape = RoundedCornerShape(11.dp),
                modifier = Modifier
                    .align(Alignment.TopEnd)
                    .padding(top = 12.dp, end = 8.dp),
            ) {
                Text(
                    text = if (selected) "✓" else ingredientSlotLabel(ingredient),
                    modifier = Modifier.padding(horizontal = 7.dp, vertical = 3.dp),
                    style = MaterialTheme.typography.labelSmall,
                    color = if (selected) Color.White else accent,
                    fontWeight = FontWeight.Black,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(start = 6.dp, top = 20.dp, end = 6.dp, bottom = 8.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.SpaceBetween,
            ) {
                Image(
                    painter = painterResource(imageFor(ingredient)),
                    contentDescription = null,
                    modifier = Modifier
                        .size(if (selected) 64.dp else 56.dp)
                        .clip(RoundedCornerShape(14.dp)),
                    contentScale = ContentScale.Fit,
                )
                Text(
                    text = ingredient.shortTitle,
                    style = MaterialTheme.typography.labelMedium,
                    fontWeight = FontWeight.Black,
                    textAlign = TextAlign.Center,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
        }
    }
}

private fun ingredientAccent(ingredient: Ingredient): Color {
    return when (ingredient) {
        Ingredient.LAVASH -> Color(0xFFB68113)
        Ingredient.CHICKEN -> Color(0xFFD7672A)
        Ingredient.TOMATO -> Color(0xFFD94E2F)
        Ingredient.CUCUMBER -> Color(0xFF3F8B55)
        Ingredient.GREENS -> Color(0xFF2F7B4A)
        Ingredient.GARLIC -> Color(0xFF9A7B2F)
        Ingredient.SPICY -> Color(0xFFC43324)
        Ingredient.FRIES -> Color(0xFFE1A528)
    }
}

private fun ingredientSlotLabel(ingredient: Ingredient): String {
    return when (ingredient) {
        Ingredient.LAVASH -> "база"
        Ingredient.CHICKEN -> "жар"
        Ingredient.TOMATO,
        Ingredient.CUCUMBER,
        Ingredient.GREENS -> "свеж"
        Ingredient.GARLIC,
        Ingredient.SPICY -> "соус"
        Ingredient.FRIES -> "хруст"
    }
}

@Composable
private fun ResultScreen(
    result: ScoreResult,
    onMenu: () -> Unit,
    onRetry: () -> Unit,
    onNext: () -> Unit,
) {
    val feedback = resultFeedback(result)
    AppBackground(ScreenMood.Result) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .testTag(UiTestTags.SCREEN_RESULT)
                .verticalScroll(rememberScrollState())
                .padding(22.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            Spacer(Modifier.height(8.dp))
            ResultReceipt(result = result, feedback = feedback)
            Spacer(Modifier.height(4.dp))
            PrimaryButton(text = resultPrimaryActionText(result), onClick = {
                if (canStartNextLevel(result)) {
                    onNext()
                } else {
                    onRetry()
                }
            })
            SecondaryButton(text = "В меню", onClick = onMenu)
        }
    }
}

@Composable
private fun ResultReceipt(
    result: ScoreResult,
    feedback: ResultFeedback,
) {
    val status = when {
        result.isEndless -> "Смена закрыта"
        result.isWin -> "Заказы выданы"
        else -> "Смена сорвалась"
    }
    val accent = when {
        result.isEndless -> MaterialTheme.colorScheme.primary
        result.isWin -> Color(0xFF2F5D50)
        else -> MaterialTheme.colorScheme.secondary
    }
    Surface(
        color = Color(0xFFFFFBF2),
        shape = RoundedCornerShape(10.dp),
        border = BorderStroke(1.dp, accent.copy(alpha = 0.5f)),
        modifier = Modifier.fillMaxWidth(),
        tonalElevation = 2.dp,
    ) {
        Column(
            modifier = Modifier.padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = "Чек смены",
                        style = MaterialTheme.typography.labelLarge,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        fontWeight = FontWeight.Bold,
                    )
                    Text(
                        text = status,
                        style = MaterialTheme.typography.headlineMedium,
                        fontWeight = FontWeight.Black,
                        color = Color(0xFF1E2D29),
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
                Surface(
                    color = accent.copy(alpha = 0.16f),
                    shape = RoundedCornerShape(8.dp),
                    border = BorderStroke(1.dp, accent.copy(alpha = 0.5f)),
                ) {
                    Text(
                        text = if (result.isEndless) "ENDLESS" else "LV ${result.levelId}",
                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 8.dp),
                        style = MaterialTheme.typography.labelLarge,
                        color = accent,
                        fontWeight = FontWeight.Black,
                        maxLines = 1,
                    )
                }
            }
            ReceiptDivider(color = Color(0x332F5D50))
            Text(
                text = if (result.isEndless) {
                    "Рекорд обновится, если счёт выше прошлого."
                } else {
                    "Звёзды: ${"★".repeat(result.stars).ifBlank { "—" }}"
                },
                style = MaterialTheme.typography.titleMedium,
                color = if (result.stars > 0 || result.isEndless) Color(0xFFB68113) else MaterialTheme.colorScheme.onSurfaceVariant,
                fontWeight = FontWeight.Black,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
            ResultReceiptRow(label = "Счёт", value = result.score.toString(), accent = accent)
            ResultReceiptRow(
                label = "Заказы",
                value = if (result.isEndless) result.servedOrders.toString() else "${result.servedOrders}/${result.targetOrders}",
                accent = accent,
            )
            ResultReceiptRow(label = "Ошибки", value = result.mistakes.toString(), accent = accent)
            ResultReceiptRow(label = "Лучшая серия", value = result.bestStreak.toString(), accent = accent)
            ResultReceiptRow(label = "Осталось", value = "${result.remainingSeconds}с", accent = accent)
            Surface(
                color = accent.copy(alpha = 0.1f),
                shape = RoundedCornerShape(8.dp),
                modifier = Modifier
                    .fillMaxWidth()
                    .testTag(UiTestTags.RESULT_FEEDBACK),
            ) {
                Column(
                    modifier = Modifier.padding(12.dp),
                    verticalArrangement = Arrangement.spacedBy(4.dp),
                ) {
                    Text(
                        text = feedback.title,
                        style = MaterialTheme.typography.titleSmall,
                        color = accent,
                        fontWeight = FontWeight.Black,
                    )
                    Text(
                        text = feedback.body,
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
        }
    }
}

@Composable
private fun ResultReceiptRow(
    label: String,
    value: String,
    accent: Color,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 2.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(
            text = label,
            style = MaterialTheme.typography.bodyLarge,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            modifier = Modifier.weight(1f),
        )
        Box(
            modifier = Modifier
                .width(42.dp)
                .height(1.dp)
                .background(accent.copy(alpha = 0.24f)),
        )
        Text(
            text = value,
            style = MaterialTheme.typography.titleMedium,
            color = Color(0xFF1E2D29),
            fontWeight = FontWeight.Black,
            textAlign = TextAlign.End,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            modifier = Modifier
                .width(96.dp)
                .padding(start = 10.dp),
        )
    }
}

@Composable
private fun ReceiptDivider(color: Color) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        repeat(28) {
            Box(
                modifier = Modifier
                    .width(5.dp)
                    .height(2.dp)
                    .clip(RoundedCornerShape(2.dp))
                    .background(color),
            )
        }
    }
}

@Composable
private fun Header(
    title: String,
    onBack: () -> Unit,
    inverted: Boolean = false,
) {
    val titleColor = if (inverted) Color.White else MaterialTheme.colorScheme.onSurface
    val buttonContentColor = if (inverted) Color.White else MaterialTheme.colorScheme.primary
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 12.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        OutlinedButton(
            onClick = onBack,
            modifier = Modifier
                .size(48.dp)
                .semantics {
                    contentDescription = "Назад"
                    role = Role.Button
                },
            colors = ButtonDefaults.outlinedButtonColors(
                containerColor = if (inverted) Color.White.copy(alpha = 0.12f) else Color.Transparent,
                contentColor = buttonContentColor,
            ),
            contentPadding = PaddingValues(0.dp),
        ) {
            Text("‹", color = buttonContentColor)
        }
        Text(
            text = title,
            modifier = Modifier
                .weight(1f)
                .padding(horizontal = 10.dp),
            style = MaterialTheme.typography.titleLarge,
            fontWeight = FontWeight.Black,
            color = titleColor,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

@Composable
private fun InfoPanel(
    title: String,
    body: String,
    modifier: Modifier = Modifier,
) {
    Surface(
        color = MaterialTheme.colorScheme.surface,
        shape = RoundedCornerShape(18.dp),
        modifier = modifier.fillMaxWidth(),
    ) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Black)
            Text(body, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
private fun PrimaryButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Button(
        onClick = onClick,
        modifier = modifier
            .fillMaxWidth()
            .height(54.dp),
        shape = RoundedCornerShape(16.dp),
        colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary),
    ) {
        Text(text = text, fontSize = 17.sp, fontWeight = FontWeight.Black)
    }
}

@Composable
private fun SecondaryButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    OutlinedButton(
        onClick = onClick,
        modifier = modifier
            .fillMaxWidth()
            .height(52.dp),
        shape = RoundedCornerShape(16.dp),
    ) {
        Text(text = text, fontWeight = FontWeight.Bold)
    }
}
