package com.shawarma58.game

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import com.shawarma58.game.data.ProgressStore
import com.shawarma58.game.ui.Shawarma58App
import com.shawarma58.game.ui.theme.Shawarma58Theme

class MainActivity : ComponentActivity() {
    private val progressStore by lazy { ProgressStore(applicationContext) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            Shawarma58Theme {
                Shawarma58App(progressStore = progressStore)
            }
        }
    }
}
