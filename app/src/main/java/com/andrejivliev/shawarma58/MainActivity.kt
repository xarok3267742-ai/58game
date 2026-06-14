package com.andrejivliev.shawarma58

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import com.andrejivliev.shawarma58.data.ProgressStore
import com.andrejivliev.shawarma58.ui.Shawarma58App
import com.andrejivliev.shawarma58.ui.theme.Shawarma58Theme

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
