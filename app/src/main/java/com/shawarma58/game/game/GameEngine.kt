package com.shawarma58.game.game

import com.shawarma58.game.data.Ingredient
import com.shawarma58.game.data.LevelCatalog
import com.shawarma58.game.data.LevelConfig
import com.shawarma58.game.data.RecipeOrder
import com.shawarma58.game.data.ScoreResult

data class GameSession(
    val level: LevelConfig,
    val isEndless: Boolean,
    val activeOrder: RecipeOrder,
    val selectedIngredients: List<Ingredient>,
    val servedOrders: Int,
    val mistakes: Int,
    val comboStreak: Int,
    val bestStreak: Int,
    val score: Int,
    val remainingSeconds: Int,
    val isFinished: Boolean,
)

object GameRules {
    fun matches(order: RecipeOrder, selected: List<Ingredient>): Boolean {
        return order.ingredients.toSet() == selected.toSet() && order.ingredients.size == selected.size
    }

    fun scoreGain(level: LevelConfig, remainingSeconds: Int, selectedCount: Int): Int {
        val paceBonus = when (level.speedLabel) {
            "жарко" -> 35
            "быстро" -> 20
            else -> 10
        }
        return 80 + selectedCount * 12 + remainingSeconds.coerceAtLeast(0) + paceBonus
    }

    fun streakBonus(streak: Int): Int {
        return ((streak - 1).coerceAtLeast(0) * 15).coerceAtMost(45)
    }

    fun starsFor(result: ScoreResult): Int {
        if (result.isEndless || !result.isWin) return 0
        return when {
            result.mistakes == 0 && result.remainingSeconds >= result.durationSeconds / 4 -> 3
            result.mistakes <= 1 -> 2
            else -> 1
        }
    }
}

object GameEngine {
    fun start(level: LevelConfig, isEndless: Boolean = false): GameSession {
        return GameSession(
            level = level,
            isEndless = isEndless,
            activeOrder = LevelCatalog.orderFor(level, 0),
            selectedIngredients = emptyList(),
            servedOrders = 0,
            mistakes = 0,
            comboStreak = 0,
            bestStreak = 0,
            score = 0,
            remainingSeconds = level.durationSeconds,
            isFinished = false,
        )
    }

    fun toggleIngredient(session: GameSession, ingredient: Ingredient): GameSession {
        if (session.isFinished) return session
        val next = if (session.selectedIngredients.contains(ingredient)) {
            session.selectedIngredients - ingredient
        } else {
            session.selectedIngredients + ingredient
        }
        return session.copy(selectedIngredients = next)
    }

    fun clear(session: GameSession): GameSession {
        return if (session.isFinished) session else session.copy(selectedIngredients = emptyList())
    }

    fun tick(session: GameSession): GameSession {
        if (session.isFinished) return session
        val nextTime = (session.remainingSeconds - 1).coerceAtLeast(0)
        return session.copy(
            remainingSeconds = nextTime,
            isFinished = nextTime == 0,
        )
    }

    fun serve(session: GameSession): GameSession {
        if (session.isFinished) return session
        val correct = GameRules.matches(session.activeOrder, session.selectedIngredients)
        if (!correct) {
            val nextMistakes = session.mistakes + 1
            return session.copy(
                mistakes = nextMistakes,
                comboStreak = 0,
                selectedIngredients = emptyList(),
                isFinished = nextMistakes >= session.level.maxMistakes,
            )
        }

        val nextServed = session.servedOrders + 1
        val nextStreak = session.comboStreak + 1
        val nextScore = session.score + GameRules.scoreGain(
            level = session.level,
            remainingSeconds = session.remainingSeconds,
            selectedCount = session.selectedIngredients.size,
        ) + GameRules.streakBonus(nextStreak)
        val completed = !session.isEndless && nextServed >= session.level.targetOrders
        return session.copy(
            servedOrders = nextServed,
            score = nextScore,
            comboStreak = nextStreak,
            bestStreak = maxOf(session.bestStreak, nextStreak),
            selectedIngredients = emptyList(),
            activeOrder = LevelCatalog.orderFor(session.level, nextServed),
            isFinished = completed,
        )
    }

    fun result(session: GameSession): ScoreResult {
        val win = session.isEndless || session.servedOrders >= session.level.targetOrders
        val base = ScoreResult(
            levelId = session.level.id,
            levelTitle = session.level.title,
            isEndless = session.isEndless,
            isWin = win,
            score = session.score,
            stars = 0,
            servedOrders = session.servedOrders,
            targetOrders = session.level.targetOrders,
            mistakes = session.mistakes,
            bestStreak = session.bestStreak,
            remainingSeconds = session.remainingSeconds,
            durationSeconds = session.level.durationSeconds,
        )
        return base.copy(stars = GameRules.starsFor(base))
    }
}
