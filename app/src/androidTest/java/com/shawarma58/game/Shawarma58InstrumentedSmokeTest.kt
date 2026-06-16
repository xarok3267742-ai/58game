package com.shawarma58.game

import android.view.KeyEvent
import androidx.compose.ui.semantics.SemanticsProperties
import androidx.compose.ui.test.SemanticsMatcher
import androidx.compose.ui.test.assert
import androidx.compose.ui.test.assertHasClickAction
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsOff
import androidx.compose.ui.test.assertIsOn
import androidx.compose.ui.test.hasTestTag
import androidx.compose.ui.test.junit4.StateRestorationTester
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onAllNodesWithTag
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollToNode
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.shawarma58.game.data.GameSettings
import com.shawarma58.game.data.Ingredient
import com.shawarma58.game.data.PlayerProgress
import com.shawarma58.game.data.ProgressRepository
import com.shawarma58.game.ui.Shawarma58App
import com.shawarma58.game.ui.UiTestTags
import com.shawarma58.game.ui.theme.Shawarma58Theme
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class Shawarma58InstrumentedSmokeTest {
    @get:Rule
    val compose = createComposeRule()

    @Test
    fun onboardingToLevelResultCompletesLevelAndShowsStars() {
        val progress = renderApp(
            PlayerProgress(
                onboardingSeen = false,
                settings = GameSettings(soundEnabled = false, reducedMotion = true),
            ),
        )

        waitForTag(UiTestTags.SCREEN_ONBOARDING)
        compose.onNodeWithText("Начать смену").performClick()

        waitForTag(UiTestTags.SCREEN_MENU)
        compose.onNodeWithTag(UiTestTags.MENU_PLAY).performClick()

        waitForTag(UiTestTags.SCREEN_LEVELS)
        compose.onNodeWithText("3 заказа • 77 сек").assertIsDisplayed()
        compose.onNodeWithTag(UiTestTags.levelTile(1)).performClick()

        waitForTag(UiTestTags.SCREEN_GAMEPLAY)
        serveOrder(
            Ingredient.LAVASH,
            Ingredient.CHICKEN,
            Ingredient.TOMATO,
            Ingredient.CUCUMBER,
            Ingredient.GARLIC,
        )
        compose.onNodeWithText("Заказы 1/3").assertIsDisplayed()

        serveOrder(
            Ingredient.LAVASH,
            Ingredient.CHICKEN,
            Ingredient.FRIES,
            Ingredient.GARLIC,
        )
        compose.onNodeWithText("Заказы 2/3").assertIsDisplayed()

        serveOrder(
            Ingredient.LAVASH,
            Ingredient.CHICKEN,
            Ingredient.CUCUMBER,
            Ingredient.FRIES,
            Ingredient.GARLIC,
        )

        waitForTag(UiTestTags.SCREEN_RESULT)
        compose.onNodeWithText("Заказы выданы").assertIsDisplayed()
        compose.onNodeWithText("Звёзды: ★★★").assertIsDisplayed()
        compose.onNodeWithTag(UiTestTags.RESULT_FEEDBACK).assertIsDisplayed()
        compose.onNodeWithText("Чистая работа").assertIsDisplayed()
        compose.waitUntil(timeoutMillis = 5_000) {
            1 in progress.current.completedLevels &&
                progress.current.starsByLevel[1] == 3 &&
                progress.completeLevelCalls == 1
        }
        assertEquals(0, progress.bestEndlessScoreCalls)
    }

    @Test
    fun endlessResultPersistsBestScoreOnceWhenShiftEnds() {
        val progress = renderApp(
            PlayerProgress(
                onboardingSeen = true,
                settings = GameSettings(soundEnabled = false, reducedMotion = true),
            ),
        )

        waitForTag(UiTestTags.SCREEN_MENU)
        compose.onNodeWithTag(UiTestTags.MENU_ENDLESS).performClick()
        waitForTag(UiTestTags.SCREEN_GAMEPLAY)

        repeat(3) {
            serveOrder(Ingredient.SPICY)
        }

        waitForTag(UiTestTags.SCREEN_RESULT)
        compose.onNodeWithText("Смена закрыта").assertIsDisplayed()
        compose.waitUntil(timeoutMillis = 5_000) {
            progress.bestEndlessScoreCalls == 1
        }
        assertEquals(0, progress.completeLevelCalls)
    }

    @Test
    fun wrongOrderShowsMistakeAndClearsSelection() {
        renderApp(
            PlayerProgress(
                onboardingSeen = true,
                settings = GameSettings(soundEnabled = false, reducedMotion = true),
            ),
        )

        waitForTag(UiTestTags.SCREEN_MENU)
        compose.onNodeWithTag(UiTestTags.MENU_PLAY).performClick()
        waitForTag(UiTestTags.SCREEN_LEVELS)
        compose.onNodeWithTag(UiTestTags.levelTile(1)).performClick()

        waitForTag(UiTestTags.SCREEN_GAMEPLAY)
        tapIngredient(Ingredient.SPICY)
        compose.onNodeWithTag(UiTestTags.SERVE_ORDER).performClick()

        compose.onNodeWithText("Ошибки 1/3").assertIsDisplayed()
        compose.onNodeWithText("Состав пока пуст").assertIsDisplayed()
        compose.onNodeWithTag(UiTestTags.SERVE_FEEDBACK).assertIsDisplayed()
        compose.onNodeWithText("Состав не совпал").assertIsDisplayed()
    }

    @Test
    fun gameplayPauseOverlayCanResumeShift() {
        renderApp(
            PlayerProgress(
                onboardingSeen = true,
                settings = GameSettings(soundEnabled = false, reducedMotion = true),
            ),
        )

        waitForTag(UiTestTags.SCREEN_MENU)
        compose.onNodeWithTag(UiTestTags.MENU_PLAY).performClick()
        waitForTag(UiTestTags.SCREEN_LEVELS)
        compose.onNodeWithTag(UiTestTags.levelTile(1)).performClick()
        waitForTag(UiTestTags.SCREEN_GAMEPLAY)

        compose.onNodeWithTag(UiTestTags.PAUSE_GAME).performClick()
        compose.onNodeWithTag(UiTestTags.PAUSE_OVERLAY).assertIsDisplayed()
        compose.onNodeWithText("Таймер остановлен. Можно продолжить смену или выйти в меню.").assertIsDisplayed()
        compose.onNodeWithTag(UiTestTags.RESUME_GAME).performClick()

        serveOrder(
            Ingredient.LAVASH,
            Ingredient.CHICKEN,
            Ingredient.TOMATO,
            Ingredient.CUCUMBER,
            Ingredient.GARLIC,
        )
        compose.onNodeWithText("Заказы 1/3").assertIsDisplayed()
    }

    @Test
    fun gameplayBackOpensPauseOverlayBeforeLeavingShift() {
        renderApp(
            PlayerProgress(
                onboardingSeen = true,
                settings = GameSettings(soundEnabled = false, reducedMotion = true),
            ),
        )

        waitForTag(UiTestTags.SCREEN_MENU)
        compose.onNodeWithTag(UiTestTags.MENU_PLAY).performClick()
        waitForTag(UiTestTags.SCREEN_LEVELS)
        compose.onNodeWithTag(UiTestTags.levelTile(1)).performClick()
        waitForTag(UiTestTags.SCREEN_GAMEPLAY)

        pressSystemBack()
        compose.onNodeWithTag(UiTestTags.PAUSE_OVERLAY).assertIsDisplayed()
        compose.onNodeWithTag(UiTestTags.SCREEN_GAMEPLAY).assertIsDisplayed()

        pressSystemBack()
        waitForNoTag(UiTestTags.PAUSE_OVERLAY)
        compose.onNodeWithTag(UiTestTags.SCREEN_GAMEPLAY).assertIsDisplayed()

        serveOrder(
            Ingredient.LAVASH,
            Ingredient.CHICKEN,
            Ingredient.TOMATO,
            Ingredient.CUCUMBER,
            Ingredient.GARLIC,
        )
        compose.onNodeWithText("Заказы 1/3").assertIsDisplayed()
    }

    @Test
    fun gameplayStateSurvivesActivityRecreation() {
        val restorationTester = renderRestorableApp(
            PlayerProgress(
                onboardingSeen = true,
                settings = GameSettings(soundEnabled = false, reducedMotion = true),
            ),
        )

        waitForTag(UiTestTags.SCREEN_MENU)
        compose.onNodeWithTag(UiTestTags.MENU_PLAY).performClick()
        waitForTag(UiTestTags.SCREEN_LEVELS)
        compose.onNodeWithTag(UiTestTags.levelTile(1)).performClick()
        waitForTag(UiTestTags.SCREEN_GAMEPLAY)

        tapIngredient(Ingredient.LAVASH)
        assertIngredientSelected(Ingredient.LAVASH)

        restorationTester.emulateSavedInstanceStateRestore()
        waitForTag(UiTestTags.SCREEN_GAMEPLAY)
        assertIngredientSelected(Ingredient.LAVASH)

        serveOrder(
            Ingredient.CHICKEN,
            Ingredient.TOMATO,
            Ingredient.CUCUMBER,
            Ingredient.GARLIC,
        )
        compose.onNodeWithText("Заказы 1/3").assertIsDisplayed()

        tapIngredient(Ingredient.LAVASH)
        assertIngredientSelected(Ingredient.LAVASH)

        restorationTester.emulateSavedInstanceStateRestore()
        waitForTag(UiTestTags.SCREEN_GAMEPLAY)
        compose.onNodeWithText("Заказы 1/3").assertIsDisplayed()
        assertIngredientSelected(Ingredient.LAVASH)
    }

    @Test
    fun settingsTogglesUpdateRepositoryState() {
        val progress = renderApp(
            PlayerProgress(
                onboardingSeen = true,
                settings = GameSettings(soundEnabled = true, reducedMotion = false),
            ),
        )

        waitForTag(UiTestTags.SCREEN_MENU)
        compose.onNodeWithTag(UiTestTags.MENU_SETTINGS).performClick()
        waitForTag(UiTestTags.SCREEN_SETTINGS)
        compose.onNodeWithContentDescription("Назад").assertHasClickAction()

        compose.onNodeWithTag(UiTestTags.SOUND_SWITCH).assertIsOn()
        compose.onNodeWithTag(UiTestTags.REDUCED_MOTION_SWITCH).assertIsOff()

        compose.onNodeWithTag(UiTestTags.SOUND_SWITCH).performClick()
        compose.onNodeWithTag(UiTestTags.REDUCED_MOTION_SWITCH).performClick()

        compose.waitUntil(timeoutMillis = 5_000) {
            !progress.current.settings.soundEnabled && progress.current.settings.reducedMotion
        }
        compose.onNodeWithTag(UiTestTags.SOUND_SWITCH).assertIsOff()
        compose.onNodeWithTag(UiTestTags.REDUCED_MOTION_SWITCH).assertIsOn()
    }

    @Test
    fun settingsResetProgressClearsLocalProgressButKeepsSettings() {
        val progress = renderApp(
            PlayerProgress(
                onboardingSeen = true,
                completedLevels = setOf(1, 2, 3),
                starsByLevel = mapOf(1 to 3, 2 to 2, 3 to 1),
                bestEndlessScore = 251,
                settings = GameSettings(soundEnabled = false, reducedMotion = true),
            ),
        )

        waitForTag(UiTestTags.SCREEN_MENU)
        compose.onNodeWithTag(UiTestTags.MENU_SETTINGS).performClick()
        waitForTag(UiTestTags.SCREEN_SETTINGS)

        compose.onNodeWithTag(UiTestTags.RESET_PROGRESS).performClick()
        compose.onNodeWithText("Удалить прогресс").assertIsDisplayed()
        compose.onNodeWithTag(UiTestTags.CONFIRM_RESET_PROGRESS).performClick()

        compose.waitUntil(timeoutMillis = 5_000) {
            !progress.current.onboardingSeen &&
                progress.current.completedLevels.isEmpty() &&
                progress.current.starsByLevel.isEmpty() &&
                progress.current.bestEndlessScore == 0 &&
                !progress.current.settings.soundEnabled &&
                progress.current.settings.reducedMotion
        }
    }

    private fun renderApp(initialProgress: PlayerProgress): FakeProgressRepository {
        val progress = FakeProgressRepository(initialProgress)
        compose.setContent {
            Shawarma58Theme {
                Shawarma58App(progressStore = progress)
            }
        }
        return progress
    }

    private fun renderRestorableApp(initialProgress: PlayerProgress): StateRestorationTester {
        val progress = FakeProgressRepository(initialProgress)
        return StateRestorationTester(compose).also { restorationTester ->
            restorationTester.setContent {
                Shawarma58Theme {
                    Shawarma58App(progressStore = progress)
                }
            }
        }
    }

    private fun waitForTag(tag: String) {
        compose.waitUntil(timeoutMillis = 5_000) {
            runCatching {
                compose.onAllNodesWithTag(tag).fetchSemanticsNodes().isNotEmpty()
            }.getOrDefault(false)
        }
        compose.onNodeWithTag(tag).assertIsDisplayed()
    }

    private fun waitForNoTag(tag: String) {
        compose.waitUntil(timeoutMillis = 5_000) {
            runCatching {
                compose.onAllNodesWithTag(tag).fetchSemanticsNodes().isEmpty()
            }.getOrDefault(false)
        }
    }

    private fun pressSystemBack() {
        InstrumentationRegistry.getInstrumentation().sendKeyDownUpSync(KeyEvent.KEYCODE_BACK)
        compose.waitForIdle()
    }

    private fun serveOrder(vararg ingredients: Ingredient) {
        ingredients.forEach { ingredient ->
            tapIngredient(ingredient)
        }
        compose.onNodeWithTag(UiTestTags.SERVE_ORDER).performClick()
    }

    private fun tapIngredient(ingredient: Ingredient) {
        val tag = UiTestTags.ingredientTile(ingredient)
        runCatching {
            compose.onNodeWithTag(UiTestTags.INGREDIENT_GRID)
                .performScrollToNode(hasTestTag(tag))
        }
        compose.onNodeWithTag(tag).performClick()
    }

    private fun assertIngredientSelected(ingredient: Ingredient) {
        compose.onNodeWithTag(UiTestTags.ingredientTile(ingredient))
            .assert(SemanticsMatcher.expectValue(SemanticsProperties.StateDescription, "Выбран"))
    }
}

private class FakeProgressRepository(initialProgress: PlayerProgress) : ProgressRepository {
    private val progress = MutableStateFlow(initialProgress)

    override val progressFlow: Flow<PlayerProgress> = progress

    var completeLevelCalls: Int = 0
        private set

    var bestEndlessScoreCalls: Int = 0
        private set

    val current: PlayerProgress
        get() = progress.value

    override suspend fun setOnboardingSeen() {
        progress.value = progress.value.copy(onboardingSeen = true)
    }

    override suspend fun updateSettings(settings: GameSettings) {
        progress.value = progress.value.copy(settings = settings)
    }

    override suspend fun resetProgress() {
        progress.value = progress.value.copy(
            onboardingSeen = false,
            completedLevels = emptySet(),
            starsByLevel = emptyMap(),
            bestEndlessScore = 0,
        )
    }

    override suspend fun completeLevel(levelId: Int, stars: Int) {
        completeLevelCalls += 1
        progress.value = progress.value.withCompletedLevel(levelId, stars)
    }

    override suspend fun updateBestEndlessScore(score: Int) {
        bestEndlessScoreCalls += 1
        progress.value = progress.value.withBestEndlessScore(score)
    }
}
