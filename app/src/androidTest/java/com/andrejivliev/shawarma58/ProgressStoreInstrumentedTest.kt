package com.andrejivliev.shawarma58

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.andrejivliev.shawarma58.data.GameSettings
import com.andrejivliev.shawarma58.data.ProgressStore
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class ProgressStoreInstrumentedTest {
    @Test
    fun realDataStoreResetClearsProgressButKeepsSettings() = runBlocking {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val store = ProgressStore(context)

        try {
            store.updateSettings(GameSettings(soundEnabled = false, reducedMotion = true))
            store.setOnboardingSeen()
            store.completeLevel(levelId = 1, stars = 3)
            store.updateBestEndlessScore(score = 251)

            val beforeReset = store.progressFlow.first()
            assertTrue(beforeReset.onboardingSeen)
            assertTrue(1 in beforeReset.completedLevels)
            assertEquals(3, beforeReset.starsByLevel[1])
            assertEquals(251, beforeReset.bestEndlessScore)
            assertFalse(beforeReset.settings.soundEnabled)
            assertTrue(beforeReset.settings.reducedMotion)

            store.resetProgress()

            val afterReset = store.progressFlow.first()
            assertFalse(afterReset.onboardingSeen)
            assertTrue(afterReset.completedLevels.isEmpty())
            assertTrue(afterReset.starsByLevel.isEmpty())
            assertEquals(0, afterReset.bestEndlessScore)
            assertFalse(afterReset.settings.soundEnabled)
            assertTrue(afterReset.settings.reducedMotion)
        } finally {
            store.resetProgress()
            store.updateSettings(GameSettings())
        }
    }
}
