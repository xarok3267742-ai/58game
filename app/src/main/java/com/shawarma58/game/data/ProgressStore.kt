package com.shawarma58.game.data

import android.content.Context
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.emptyPreferences
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.core.stringSetPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.map
import java.io.IOException

private val Context.progressDataStore by preferencesDataStore(name = "shawarma58_progress")

interface ProgressRepository {
    val progressFlow: Flow<PlayerProgress>

    suspend fun setOnboardingSeen()

    suspend fun updateSettings(settings: GameSettings)

    suspend fun resetProgress()

    suspend fun completeLevel(levelId: Int, stars: Int)

    suspend fun updateBestEndlessScore(score: Int)
}

class ProgressStore(private val context: Context) : ProgressRepository {
    override val progressFlow: Flow<PlayerProgress> = context.progressDataStore.data
        .catch { error ->
            if (error is IOException) {
                emit(emptyPreferences())
            } else {
                throw error
            }
        }
        .map { preferences ->
            PlayerProgress(
                onboardingSeen = preferences[Keys.onboardingSeen] ?: false,
                completedLevels = preferences[Keys.completedLevels]
                    ?.mapNotNull { it.toIntOrNull() }
                    ?.filter { it > 0 }
                    ?.toSet()
                    ?: emptySet(),
                starsByLevel = decodeStars(preferences[Keys.starsByLevel]),
                bestEndlessScore = (preferences[Keys.bestEndlessScore] ?: 0).coerceAtLeast(0),
                settings = GameSettings(
                    soundEnabled = preferences[Keys.soundEnabled] ?: true,
                    reducedMotion = preferences[Keys.reducedMotion] ?: false,
                ),
            )
        }

    override suspend fun setOnboardingSeen() {
        context.progressDataStore.edit { preferences ->
            preferences[Keys.onboardingSeen] = true
        }
    }

    override suspend fun updateSettings(settings: GameSettings) {
        context.progressDataStore.edit { preferences ->
            preferences[Keys.soundEnabled] = settings.soundEnabled
            preferences[Keys.reducedMotion] = settings.reducedMotion
        }
    }

    override suspend fun resetProgress() {
        context.progressDataStore.edit { preferences ->
            preferences.remove(Keys.onboardingSeen)
            preferences.remove(Keys.completedLevels)
            preferences.remove(Keys.starsByLevel)
            preferences.remove(Keys.bestEndlessScore)
        }
    }

    override suspend fun completeLevel(levelId: Int, stars: Int) {
        val safeStars = stars.coerceIn(0, MAX_STARS_PER_LEVEL)
        if (levelId <= 0 || safeStars == 0) return
        context.progressDataStore.edit { preferences ->
            val completed = preferences[Keys.completedLevels].orEmpty().toMutableSet()
            completed += levelId.toString()
            preferences[Keys.completedLevels] = completed

            val currentStars = decodeStars(preferences[Keys.starsByLevel]).toMutableMap()
            currentStars[levelId] = maxOf(currentStars[levelId] ?: 0, safeStars)
            preferences[Keys.starsByLevel] = encodeStars(currentStars)
        }
    }

    override suspend fun updateBestEndlessScore(score: Int) {
        val safeScore = score.coerceAtLeast(0)
        context.progressDataStore.edit { preferences ->
            val currentBest = (preferences[Keys.bestEndlessScore] ?: 0).coerceAtLeast(0)
            if (safeScore > currentBest) {
                preferences[Keys.bestEndlessScore] = safeScore
            }
        }
    }

    private object Keys {
        val onboardingSeen = booleanPreferencesKey("onboardingSeen")
        val soundEnabled = booleanPreferencesKey("soundEnabled")
        val reducedMotion = booleanPreferencesKey("reducedMotion")
        val completedLevels = stringSetPreferencesKey("completedLevels")
        val starsByLevel = stringPreferencesKey("starsByLevel")
        val bestEndlessScore = intPreferencesKey("bestEndlessScore")
    }
}

private fun decodeStars(raw: String?): Map<Int, Int> {
    if (raw.isNullOrBlank()) return emptyMap()
    return raw.split(",")
        .mapNotNull { entry ->
            val parts = entry.split(":")
            val level = parts.getOrNull(0)?.toIntOrNull()
            val stars = parts.getOrNull(1)?.toIntOrNull()?.coerceIn(0, MAX_STARS_PER_LEVEL)
            if (level != null && level > 0 && stars != null && stars > 0) level to stars else null
        }
        .toMap()
}

private fun encodeStars(stars: Map<Int, Int>): String {
    return stars
        .mapNotNull { (level, value) ->
            val safeStars = value.coerceIn(0, MAX_STARS_PER_LEVEL)
            if (level > 0 && safeStars > 0) level to safeStars else null
        }
        .toMap()
        .toSortedMap()
        .entries
        .joinToString(",") { (level, value) -> "$level:$value" }
}
