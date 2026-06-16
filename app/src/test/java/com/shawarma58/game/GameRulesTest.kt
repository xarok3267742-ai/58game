package com.shawarma58.game

import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import com.shawarma58.game.data.Ingredient
import com.shawarma58.game.data.LevelCatalog
import com.shawarma58.game.data.LevelConfig
import com.shawarma58.game.data.MAX_STARS_PER_LEVEL
import com.shawarma58.game.data.PlayerProgress
import com.shawarma58.game.data.RecipeOrder
import com.shawarma58.game.data.ScoreResult
import com.shawarma58.game.game.GameEngine
import com.shawarma58.game.game.GameRules
import com.shawarma58.game.ui.canStartNextLevel
import com.shawarma58.game.ui.ingredientToggleHaptic
import com.shawarma58.game.ui.levelWorkloadLabel
import com.shawarma58.game.ui.orderCountLabel
import com.shawarma58.game.ui.orderFeedbackHaptic
import com.shawarma58.game.ui.orderFeedbackTone
import com.shawarma58.game.ui.playableLevelFor
import com.shawarma58.game.ui.restoreSessionFromSaveableValues
import com.shawarma58.game.ui.resultFeedback
import com.shawarma58.game.ui.resultPrimaryActionText
import com.shawarma58.game.ui.saveableValuesForSession
import com.shawarma58.game.ui.serveFeedback
import com.shawarma58.game.ui.shouldPlayOrderFeedback
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class GameRulesTest {
    @Test
    fun exactIngredientSetMatchesOrder() {
        val order = RecipeOrder(
            id = 1,
            customer = com.shawarma58.game.data.CustomerType.OFFICE,
            title = "Тест",
            ingredients = listOf(Ingredient.LAVASH, Ingredient.CHICKEN, Ingredient.GARLIC),
        )

        assertTrue(GameRules.matches(order, listOf(Ingredient.GARLIC, Ingredient.LAVASH, Ingredient.CHICKEN)))
        assertFalse(GameRules.matches(order, listOf(Ingredient.LAVASH, Ingredient.CHICKEN)))
        assertFalse(GameRules.matches(order, listOf(Ingredient.LAVASH, Ingredient.CHICKEN, Ingredient.SPICY)))
        assertFalse(GameRules.matches(order, listOf(Ingredient.LAVASH, Ingredient.CHICKEN, Ingredient.GARLIC, Ingredient.SPICY)))
        assertFalse(GameRules.matches(order, listOf(Ingredient.LAVASH, Ingredient.CHICKEN, Ingredient.GARLIC, Ingredient.GARLIC)))
    }

    @Test
    fun correctOrderAddsScoreAndMovesToNextOrder() {
        val level = LevelCatalog.levelById(1)
        val session = GameEngine.start(level)
        val ready = session.copy(selectedIngredients = session.activeOrder.ingredients)

        val served = GameEngine.serve(ready)

        assertEquals(1, served.servedOrders)
        assertTrue(served.score > 0)
        assertTrue(served.selectedIngredients.isEmpty())
        assertFalse(served.isFinished)
    }

    @Test
    fun scoreGainUsesIngredientCountRemainingTimeAndPaceBonus() {
        val calm = LevelConfig(1, "Test", "Test", 60, 3, 3, "спокойно")
        val fast = calm.copy(speedLabel = "быстро")
        val hot = calm.copy(speedLabel = "жарко")

        assertEquals(80 + 4 * 12 + 30 + 10, GameRules.scoreGain(calm, remainingSeconds = 30, selectedCount = 4))
        assertEquals(80 + 4 * 12 + 30 + 20, GameRules.scoreGain(fast, remainingSeconds = 30, selectedCount = 4))
        assertEquals(80 + 4 * 12 + 30 + 35, GameRules.scoreGain(hot, remainingSeconds = 30, selectedCount = 4))
        assertEquals(80 + 4 * 12 + 0 + 10, GameRules.scoreGain(calm, remainingSeconds = -5, selectedCount = 4))
    }

    @Test
    fun streakBonusStartsOnSecondCorrectOrderAndCaps() {
        assertEquals(0, GameRules.streakBonus(0))
        assertEquals(0, GameRules.streakBonus(1))
        assertEquals(15, GameRules.streakBonus(2))
        assertEquals(30, GameRules.streakBonus(3))
        assertEquals(45, GameRules.streakBonus(4))
        assertEquals(45, GameRules.streakBonus(8))
    }

    @Test
    fun toggleIngredientSelectsAndDeselectsWithoutDuplicates() {
        val session = GameEngine.start(LevelCatalog.levelById(1))

        val selected = GameEngine.toggleIngredient(session, Ingredient.LAVASH)
        val deselected = GameEngine.toggleIngredient(selected, Ingredient.LAVASH)

        assertEquals(listOf(Ingredient.LAVASH), selected.selectedIngredients)
        assertTrue(deselected.selectedIngredients.isEmpty())
    }

    @Test
    fun clearRemovesSelectedIngredientsOnlyBeforeFinish() {
        val session = GameEngine.start(LevelCatalog.levelById(1))
            .copy(selectedIngredients = listOf(Ingredient.LAVASH, Ingredient.CHICKEN))
        val finished = session.copy(isFinished = true)

        assertTrue(GameEngine.clear(session).selectedIngredients.isEmpty())
        assertEquals(finished, GameEngine.clear(finished))
    }

    @Test
    fun wrongOrderAddsMistakeClearsSelectionAndDoesNotScore() {
        val level = LevelCatalog.levelById(1)
        val session = GameEngine.start(level)

        val served = GameEngine.serve(session.copy(selectedIngredients = listOf(Ingredient.SPICY)))

        assertEquals(1, served.mistakes)
        assertEquals(0, served.servedOrders)
        assertEquals(0, served.score)
        assertTrue(served.selectedIngredients.isEmpty())
        assertFalse(served.isFinished)
    }

    @Test
    fun correctOrdersBuildStreakScoreBonusAndBestStreak() {
        val level = LevelCatalog.levelById(1)
        val start = GameEngine.start(level)

        val first = GameEngine.serve(start.copy(selectedIngredients = start.activeOrder.ingredients))
        val second = GameEngine.serve(first.copy(selectedIngredients = first.activeOrder.ingredients))

        val firstGain = GameRules.scoreGain(level, start.remainingSeconds, start.activeOrder.ingredients.size)
        val secondGain = GameRules.scoreGain(level, first.remainingSeconds, first.activeOrder.ingredients.size) +
            GameRules.streakBonus(2)

        assertEquals(1, first.comboStreak)
        assertEquals(1, first.bestStreak)
        assertEquals(firstGain, first.score)
        assertEquals(2, second.comboStreak)
        assertEquals(2, second.bestStreak)
        assertEquals(first.score + secondGain, second.score)
    }

    @Test
    fun wrongOrderBreaksCurrentStreakButKeepsBestStreak() {
        val level = LevelCatalog.levelById(1)
        val start = GameEngine.start(level)
        val first = GameEngine.serve(start.copy(selectedIngredients = start.activeOrder.ingredients))

        val wrong = GameEngine.serve(first.copy(selectedIngredients = listOf(Ingredient.SPICY)))

        assertEquals(0, wrong.comboStreak)
        assertEquals(1, wrong.bestStreak)
    }

    @Test
    fun serveFeedbackExplainsCorrectOrderScoreGain() {
        val before = GameEngine.start(LevelCatalog.levelById(1))
        val after = GameEngine.serve(before.copy(selectedIngredients = before.activeOrder.ingredients))

        val feedback = serveFeedback(correct = true, before = before, after = after)

        assertEquals("Заказ выдан", feedback.title)
        assertTrue(feedback.positive)
        assertTrue(feedback.body.contains("Серия 1"))
        assertTrue(feedback.body.contains("+"))
    }

    @Test
    fun serveFeedbackExplainsWrongOrderReset() {
        val before = GameEngine.start(LevelCatalog.levelById(1))
            .copy(selectedIngredients = listOf(Ingredient.SPICY))
        val after = GameEngine.serve(before)

        val feedback = serveFeedback(correct = false, before = before, after = after)

        assertEquals("Состав не совпал", feedback.title)
        assertFalse(feedback.positive)
        assertTrue(feedback.body.contains("Состав сброшен"))
        assertTrue(feedback.body.contains("2"))
    }

    @Test
    fun tooManyMistakesFinishSession() {
        val level = LevelCatalog.levelById(1)
        var session = GameEngine.start(level)

        repeat(level.maxMistakes) {
            session = GameEngine.serve(session.copy(selectedIngredients = listOf(Ingredient.SPICY)))
        }

        assertTrue(session.isFinished)
        assertEquals(level.maxMistakes, session.mistakes)
    }

    @Test
    fun timerReachingZeroFinishesAsLossWithoutStars() {
        val level = LevelCatalog.levelById(1)
        var session = GameEngine.start(level)

        repeat(level.durationSeconds) {
            session = GameEngine.tick(session)
        }

        val result = GameEngine.result(session)

        assertTrue(session.isFinished)
        assertFalse(result.isWin)
        assertEquals(0, result.stars)
    }

    @Test
    fun completedLevelGetsThreeStarsWhenCleanAndFast() {
        val level = LevelCatalog.levelById(1)
        var session = GameEngine.start(level)

        repeat(level.targetOrders) {
            session = GameEngine.serve(session.copy(selectedIngredients = session.activeOrder.ingredients))
        }

        val result = GameEngine.result(session)

        assertTrue(result.isWin)
        assertEquals(3, result.stars)
    }

    @Test
    fun starThresholdsAwardTwoForOneMistakeAndOneForTwoMistakes() {
        val level = LevelCatalog.levelById(1)

        val oneMistake = resultFor(
            level = level,
            mistakes = 1,
            remainingSeconds = level.durationSeconds,
        )
        val twoMistakes = resultFor(
            level = level,
            mistakes = 2,
            remainingSeconds = level.durationSeconds,
        )

        assertEquals(2, GameRules.starsFor(oneMistake))
        assertEquals(1, GameRules.starsFor(twoMistakes))
    }

    @Test
    fun cleanWinBelowTimeThresholdGetsTwoStars() {
        val level = LevelCatalog.levelById(1)
        val justBelowQuarterTime = level.durationSeconds / 4 - 1

        val result = resultFor(
            level = level,
            mistakes = 0,
            remainingSeconds = justBelowQuarterTime,
        )

        assertEquals(2, GameRules.starsFor(result))
    }

    @Test
    fun finalTargetOrderFinishesNonEndlessLevel() {
        val level = LevelCatalog.levelById(1)
        var session = GameEngine.start(level)

        repeat(level.targetOrders) {
            session = GameEngine.serve(session.copy(selectedIngredients = session.activeOrder.ingredients))
        }

        assertTrue(session.isFinished)
        assertEquals(level.targetOrders, session.servedOrders)
    }

    @Test
    fun finishedSessionIgnoresFurtherTicksTogglesAndServes() {
        val level = LevelCatalog.levelById(1)
        val finished = GameEngine.start(level).copy(
            selectedIngredients = listOf(Ingredient.LAVASH),
            isFinished = true,
        )

        assertEquals(finished, GameEngine.tick(finished))
        assertEquals(finished, GameEngine.toggleIngredient(finished, Ingredient.CHICKEN))
        assertEquals(finished, GameEngine.serve(finished))
    }

    @Test
    fun endlessResultDoesNotAwardStarsOrStartNextLevel() {
        val level = LevelCatalog.endlessLevel
        var session = GameEngine.start(level, isEndless = true)
        session = GameEngine.serve(session.copy(selectedIngredients = session.activeOrder.ingredients))

        val result = GameEngine.result(session.copy(isFinished = true))

        assertTrue(result.isEndless)
        assertEquals(0, result.stars)
        assertEquals(1, result.bestStreak)
        assertFalse(canStartNextLevel(result))
        assertEquals("Повторить", resultPrimaryActionText(result))
    }

    @Test
    fun orderFeedbackFollowsSoundSettingAndCorrectness() {
        assertTrue(shouldPlayOrderFeedback(com.shawarma58.game.data.GameSettings(soundEnabled = true)))
        assertFalse(shouldPlayOrderFeedback(com.shawarma58.game.data.GameSettings(soundEnabled = false)))
        assertTrue(orderFeedbackTone(correct = true) != orderFeedbackTone(correct = false))
    }

    @Test
    fun gameplayHapticsDistinguishSelectionAndWrongOrder() {
        assertEquals(HapticFeedbackType.TextHandleMove, ingredientToggleHaptic())
        assertEquals(HapticFeedbackType.TextHandleMove, orderFeedbackHaptic(correct = true))
        assertEquals(HapticFeedbackType.LongPress, orderFeedbackHaptic(correct = false))
    }

    @Test
    fun progressUnlocksOnlyNextLevel() {
        val progress = PlayerProgress(completedLevels = setOf(1, 2), starsByLevel = mapOf(1 to 3, 2 to 2))

        assertFalse(progress.isLevelUnlocked(0))
        assertTrue(progress.isLevelUnlocked(1))
        assertTrue(progress.isLevelUnlocked(2))
        assertTrue(progress.isLevelUnlocked(3))
        assertFalse(progress.isLevelUnlocked(4))
        assertEquals(2, progress.starsFor(2))
    }

    @Test
    fun completedLevelCountIgnoresInvalidLevels() {
        val progress = PlayerProgress(completedLevels = setOf(-1, 0, 1, 2, 24, 25, 99))

        assertEquals(3, progress.completedLevelCount(levelCount = 24))
        assertEquals(0, progress.completedLevelCount(levelCount = -1))
    }

    @Test
    fun progressStarsAreClampedAndTotalIgnoresInvalidLevels() {
        val progress = PlayerProgress(
            starsByLevel = mapOf(
                1 to 5,
                2 to -1,
                3 to 2,
                99 to 3,
            ),
        )

        assertEquals(3, progress.starsFor(1))
        assertEquals(0, progress.starsFor(2))
        assertEquals(5, progress.totalStars(levelCount = 24))
        assertEquals(0, progress.totalStars(levelCount = -1))
    }

    @Test
    fun progressCompletionNeverLowersStarsOrStoresInvalidLevel() {
        val initial = PlayerProgress(
            completedLevels = setOf(1),
            starsByLevel = mapOf(1 to 3),
        )

        val lowerReplay = initial.withCompletedLevel(levelId = 1, stars = 1)
        val clampedWin = lowerReplay.withCompletedLevel(levelId = 2, stars = 9)
        val invalidLevel = clampedWin.withCompletedLevel(levelId = 0, stars = 3)
        val zeroStars = invalidLevel.withCompletedLevel(levelId = 3, stars = 0)

        assertEquals(3, lowerReplay.starsFor(1))
        assertTrue(2 in clampedWin.completedLevels)
        assertEquals(3, clampedWin.starsFor(2))
        assertEquals(clampedWin, invalidLevel)
        assertEquals(invalidLevel, zeroStars)
    }

    @Test
    fun bestEndlessScoreOnlyImproves() {
        val progress = PlayerProgress(bestEndlessScore = 250)
        val damagedProgress = PlayerProgress(bestEndlessScore = -8)

        assertEquals(250, progress.withBestEndlessScore(120).bestEndlessScore)
        assertEquals(251, progress.withBestEndlessScore(251).bestEndlessScore)
        assertEquals(0, damagedProgress.safeBestEndlessScore())
        assertEquals(0, damagedProgress.withBestEndlessScore(-1).bestEndlessScore)
    }

    @Test
    fun resultPrimaryActionAdvancesOnlyWhenNextLevelExists() {
        val midGameWin = GameEngine.result(
            GameEngine.start(LevelCatalog.levelById(1)).copy(
                servedOrders = LevelCatalog.levelById(1).targetOrders,
                isFinished = true,
            ),
        )
        val finalLevelWin = GameEngine.result(
            GameEngine.start(LevelCatalog.levelById(LevelCatalog.levels.size)).copy(
                servedOrders = LevelCatalog.levelById(LevelCatalog.levels.size).targetOrders,
                isFinished = true,
            ),
        )

        assertTrue(canStartNextLevel(midGameWin))
        assertEquals("Следующая смена", resultPrimaryActionText(midGameWin))
        assertFalse(canStartNextLevel(finalLevelWin))
        assertEquals("Повторить", resultPrimaryActionText(finalLevelWin))
    }

    @Test
    fun resultFeedbackHighlightsCleanWin() {
        val level = LevelCatalog.levelById(1)
        val feedback = resultFeedback(
            resultFor(
                level = level,
                mistakes = 0,
                remainingSeconds = level.durationSeconds,
            ).copy(stars = 3),
        )

        assertEquals("Чистая работа", feedback.title)
        assertTrue(feedback.body.contains("запасом по времени"))
    }

    @Test
    fun resultFeedbackCoachesTwoStarWin() {
        val feedback = resultFeedback(
            resultFor(
                level = LevelCatalog.levelById(1),
                mistakes = 1,
                remainingSeconds = 10,
            ).copy(stars = 2),
        )

        assertEquals("Смена принята", feedback.title)
        assertTrue(feedback.body.contains("трёх звёзд"))
    }

    @Test
    fun resultFeedbackExplainsTimeoutLoss() {
        val level = LevelCatalog.levelById(1)
        val feedback = resultFeedback(
            ScoreResult(
                levelId = level.id,
                levelTitle = level.title,
                isEndless = false,
                isWin = false,
                score = 80,
                stars = 0,
                servedOrders = 1,
                targetOrders = level.targetOrders,
                mistakes = 0,
                bestStreak = 1,
                remainingSeconds = 0,
                durationSeconds = level.durationSeconds,
            ),
        )

        assertEquals("Не хватило времени", feedback.title)
        assertTrue(feedback.body.contains("быстрее"))
    }

    @Test
    fun resultFeedbackSeparatesEndlessCases() {
        val emptyEndless = ScoreResult(
            levelId = LevelCatalog.endlessLevel.id,
            levelTitle = LevelCatalog.endlessLevel.title,
            isEndless = true,
            isWin = true,
            score = 0,
            stars = 0,
            servedOrders = 0,
            targetOrders = LevelCatalog.endlessLevel.targetOrders,
            mistakes = 0,
            bestStreak = 0,
            remainingSeconds = 0,
            durationSeconds = LevelCatalog.endlessLevel.durationSeconds,
        )
        val streakEndless = emptyEndless.copy(servedOrders = 8, score = 900, bestStreak = 5)

        assertEquals("Разогрев не пошёл", resultFeedback(emptyEndless).title)
        assertEquals("Серия держит темп", resultFeedback(streakEndless).title)
    }

    @Test
    fun playableLevelFallbackKeepsInvalidNavigationFromCrashing() {
        assertEquals(LevelCatalog.levelById(1), playableLevelFor(levelId = -10, isEndless = false))
        assertEquals(LevelCatalog.levelById(1), playableLevelFor(levelId = 99, isEndless = false))
        assertEquals(LevelCatalog.endlessLevel, playableLevelFor(levelId = 99, isEndless = true))
        assertEquals(LevelCatalog.levelById(7), LevelCatalog.levelByIdOrNull(7))
        assertEquals(null, LevelCatalog.levelByIdOrNull(99))
    }

    @Test
    fun activeSessionSaveableValuesRestoreCurrentShift() {
        val level = LevelCatalog.levelById(4)
        val session = GameEngine.start(level).copy(
            activeOrder = LevelCatalog.orderFor(level, 2),
            selectedIngredients = listOf(Ingredient.LAVASH, Ingredient.CHICKEN, Ingredient.GARLIC),
            servedOrders = 2,
            mistakes = 1,
            comboStreak = 2,
            bestStreak = 3,
            score = 560,
            remainingSeconds = 41,
            isFinished = false,
        )

        val restored = restoreSessionFromSaveableValues(saveableValuesForSession(session))

        assertEquals(session, restored)
    }

    @Test
    fun invalidSessionSaveableValuesAreRejected() {
        val malformedIngredient = listOf(1, false, "LAVASH,NOT_REAL", 0, 0, 0, 0, 0, 77, false)

        assertEquals(null, restoreSessionFromSaveableValues(emptyList()))
        assertEquals(null, restoreSessionFromSaveableValues(malformedIngredient))
    }

    @Test
    fun corruptNegativeSessionSaveableCountersRestoreSafely() {
        val restored = restoreSessionFromSaveableValues(
            listOf(
                1,
                false,
                "",
                -8,
                -3,
                -2,
                -5,
                -120,
                -1,
                false,
            ),
        )

        requireNotNull(restored)
        assertEquals(0, restored.servedOrders)
        assertEquals(0, restored.mistakes)
        assertEquals(0, restored.comboStreak)
        assertEquals(0, restored.bestStreak)
        assertEquals(0, restored.score)
        assertEquals(0, restored.remainingSeconds)
    }

    @Test
    fun catalogHasExpectedMvpContentShape() {
        assertEquals(24, LevelCatalog.levels.size)
        assertEquals(72, LevelCatalog.levels.size * MAX_STARS_PER_LEVEL)
        assertEquals(8, Ingredient.entries.size)
        assertEquals(4, com.shawarma58.game.data.CustomerType.entries.size)
        assertTrue(LevelCatalog.levels.all { it.targetOrders >= 3 })
        assertTrue(LevelCatalog.levels.all { it.durationSeconds >= 52 })
    }

    @Test
    fun levelWorkloadLabelUsesRussianOrderForms() {
        assertEquals("1 заказ", orderCountLabel(1))
        assertEquals("2 заказа", orderCountLabel(2))
        assertEquals("5 заказов", orderCountLabel(5))
        assertEquals("11 заказов", orderCountLabel(11))
        assertEquals("22 заказа", orderCountLabel(22))
        assertEquals("0 заказов", orderCountLabel(-4))
        assertEquals("3 заказа • 77 сек", levelWorkloadLabel(LevelCatalog.levelById(1)))
    }

    @Test
    fun orderGenerationIsDeterministicAndCyclesCustomers() {
        val level = LevelCatalog.levelById(7)

        val first = LevelCatalog.orderFor(level, 0)
        val firstAgain = LevelCatalog.orderFor(level, 0)
        val second = LevelCatalog.orderFor(level, 1)

        assertEquals(first, firstAgain)
        assertEquals(1, first.id)
        assertEquals(2, second.id)
        assertTrue(first.ingredients.contains(Ingredient.LAVASH))
        assertTrue(first.ingredients.contains(Ingredient.CHICKEN))
        assertTrue(first.customer != second.customer)
    }

    private fun resultFor(
        level: LevelConfig,
        mistakes: Int,
        remainingSeconds: Int,
    ): ScoreResult {
        return ScoreResult(
            levelId = level.id,
            levelTitle = level.title,
            isEndless = false,
            isWin = true,
            score = 100,
            stars = 0,
            servedOrders = level.targetOrders,
            targetOrders = level.targetOrders,
            mistakes = mistakes,
            bestStreak = level.targetOrders,
            remainingSeconds = remainingSeconds,
            durationSeconds = level.durationSeconds,
        )
    }
}
