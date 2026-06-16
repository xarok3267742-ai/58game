package com.shawarma58.game.data

const val MAX_STARS_PER_LEVEL = 3

enum class Ingredient(val title: String, val shortTitle: String) {
    LAVASH("Лаваш", "Лаваш"),
    CHICKEN("Курица", "Курица"),
    TOMATO("Томаты", "Томат"),
    CUCUMBER("Огурцы", "Огурец"),
    GREENS("Зелень", "Зелень"),
    GARLIC("Белый соус", "Белый"),
    SPICY("Острый соус", "Острый"),
    FRIES("Картофель", "Фри"),
}

enum class CustomerType(val title: String, val line: String) {
    OFFICE("Офисный перерыв", "Быстро, но аккуратно."),
    STUDENT("После пары", "Хочу сочно и без лишнего пафоса."),
    COURIER("Ночная доставка", "Мне в дорогу, заверни крепко."),
    NEIGHBOR("Сосед за углом", "Как обычно, только теплее."),
}

data class RecipeOrder(
    val id: Int,
    val customer: CustomerType,
    val title: String,
    val ingredients: List<Ingredient>,
)

data class LevelConfig(
    val id: Int,
    val title: String,
    val subtitle: String,
    val durationSeconds: Int,
    val targetOrders: Int,
    val maxMistakes: Int,
    val speedLabel: String,
)

data class ScoreResult(
    val levelId: Int,
    val levelTitle: String,
    val isEndless: Boolean,
    val isWin: Boolean,
    val score: Int,
    val stars: Int,
    val servedOrders: Int,
    val targetOrders: Int,
    val mistakes: Int,
    val bestStreak: Int,
    val remainingSeconds: Int,
    val durationSeconds: Int,
)

data class GameSettings(
    val soundEnabled: Boolean = true,
    val reducedMotion: Boolean = false,
)

data class PlayerProgress(
    val onboardingSeen: Boolean = false,
    val completedLevels: Set<Int> = emptySet(),
    val starsByLevel: Map<Int, Int> = emptyMap(),
    val bestEndlessScore: Int = 0,
    val settings: GameSettings = GameSettings(),
) {
    fun isLevelUnlocked(levelId: Int): Boolean {
        return levelId > 0 && (levelId == 1 || completedLevels.contains(levelId - 1))
    }

    fun completedLevelCount(levelCount: Int): Int {
        val safeLevelCount = levelCount.coerceAtLeast(0)
        return completedLevels.count { it in 1..safeLevelCount }.coerceAtMost(safeLevelCount)
    }

    fun starsFor(levelId: Int): Int = starsByLevel[levelId]?.coerceIn(0, MAX_STARS_PER_LEVEL) ?: 0

    fun totalStars(levelCount: Int): Int {
        val safeLevelCount = levelCount.coerceAtLeast(0)
        return starsByLevel
            .filterKeys { it in 1..safeLevelCount }
            .values
            .sumOf { it.coerceIn(0, MAX_STARS_PER_LEVEL) }
            .coerceAtMost(safeLevelCount * MAX_STARS_PER_LEVEL)
    }

    fun withCompletedLevel(levelId: Int, stars: Int): PlayerProgress {
        val safeStars = stars.coerceIn(0, MAX_STARS_PER_LEVEL)
        if (levelId <= 0 || safeStars == 0) return this
        val bestStars = maxOf(starsFor(levelId), safeStars)
        return copy(
            completedLevels = completedLevels + levelId,
            starsByLevel = starsByLevel + (levelId to bestStars),
        )
    }

    fun withBestEndlessScore(score: Int): PlayerProgress {
        val safeCurrent = safeBestEndlessScore()
        val safeScore = score.coerceAtLeast(0)
        return when {
            safeScore > safeCurrent -> copy(bestEndlessScore = safeScore)
            bestEndlessScore < 0 -> copy(bestEndlessScore = safeCurrent)
            else -> this
        }
    }

    fun safeBestEndlessScore(): Int = bestEndlessScore.coerceAtLeast(0)
}
