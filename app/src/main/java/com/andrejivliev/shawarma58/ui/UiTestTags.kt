package com.andrejivliev.shawarma58.ui

import com.andrejivliev.shawarma58.data.Ingredient

object UiTestTags {
    const val SCREEN_ONBOARDING = "screen_onboarding"
    const val SCREEN_MENU = "screen_menu"
    const val SCREEN_LEVELS = "screen_levels"
    const val SCREEN_GAMEPLAY = "screen_gameplay"
    const val SCREEN_RESULT = "screen_result"
    const val SCREEN_SETTINGS = "screen_settings"
    const val RESULT_FEEDBACK = "result_feedback"

    const val MENU_PLAY = "menu_play"
    const val MENU_ENDLESS = "menu_endless"
    const val MENU_SETTINGS = "menu_settings"

    const val SERVE_ORDER = "serve_order"
    const val SERVE_FEEDBACK = "serve_feedback"
    const val CLEAR_ORDER = "clear_order"
    const val PAUSE_GAME = "pause_game"
    const val PAUSE_OVERLAY = "pause_overlay"
    const val RESUME_GAME = "resume_game"
    const val SELECTED_PANEL = "selected_panel"
    const val INGREDIENT_GRID = "ingredient_grid"
    const val SOUND_SWITCH = "sound_switch"
    const val REDUCED_MOTION_SWITCH = "reduced_motion_switch"
    const val RESET_PROGRESS = "reset_progress"
    const val CONFIRM_RESET_PROGRESS = "confirm_reset_progress"

    fun levelTile(levelId: Int): String = "level_tile_$levelId"

    fun ingredientTile(ingredient: Ingredient): String = "ingredient_${ingredient.name.lowercase()}"
}
