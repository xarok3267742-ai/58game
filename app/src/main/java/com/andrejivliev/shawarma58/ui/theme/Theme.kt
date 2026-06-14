package com.andrejivliev.shawarma58.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val ShawarmaColors = lightColorScheme(
    primary = Color(0xFF2F5D50),
    onPrimary = Color.White,
    secondary = Color(0xFFD94E2F),
    onSecondary = Color.White,
    tertiary = Color(0xFFE1A528),
    background = Color(0xFFFFF7EA),
    onBackground = Color(0xFF2A211B),
    surface = Color(0xFFFFF1D7),
    onSurface = Color(0xFF2A211B),
    surfaceVariant = Color(0xFFF3E1C5),
    onSurfaceVariant = Color(0xFF5A4C3F),
    error = Color(0xFFB3261E),
)

@Composable
fun Shawarma58Theme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = ShawarmaColors,
        typography = MaterialTheme.typography,
        content = content,
    )
}
