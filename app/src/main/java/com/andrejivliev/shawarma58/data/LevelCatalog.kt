package com.andrejivliev.shawarma58.data

object LevelCatalog {
    private val recipeTemplates = listOf(
        listOf(Ingredient.LAVASH, Ingredient.CHICKEN, Ingredient.GARLIC, Ingredient.GREENS),
        listOf(Ingredient.LAVASH, Ingredient.CHICKEN, Ingredient.TOMATO, Ingredient.GARLIC),
        listOf(Ingredient.LAVASH, Ingredient.CHICKEN, Ingredient.CUCUMBER, Ingredient.GREENS),
        listOf(Ingredient.LAVASH, Ingredient.CHICKEN, Ingredient.TOMATO, Ingredient.CUCUMBER, Ingredient.GARLIC),
        listOf(Ingredient.LAVASH, Ingredient.CHICKEN, Ingredient.SPICY, Ingredient.GREENS),
        listOf(Ingredient.LAVASH, Ingredient.CHICKEN, Ingredient.FRIES, Ingredient.GARLIC),
        listOf(Ingredient.LAVASH, Ingredient.CHICKEN, Ingredient.TOMATO, Ingredient.SPICY),
        listOf(Ingredient.LAVASH, Ingredient.CHICKEN, Ingredient.CUCUMBER, Ingredient.FRIES, Ingredient.GARLIC),
        listOf(Ingredient.LAVASH, Ingredient.CHICKEN, Ingredient.TOMATO, Ingredient.GREENS, Ingredient.SPICY),
        listOf(Ingredient.LAVASH, Ingredient.CHICKEN, Ingredient.TOMATO, Ingredient.CUCUMBER, Ingredient.FRIES),
    )

    private val orderTitles = listOf(
        "Классика района",
        "Свежий заворот",
        "Сочная смена",
        "Без очереди",
        "Острый поворот",
        "С фри внутри",
        "Красный акцент",
        "Двойной хруст",
        "Зелёный огонь",
        "Плотный заказ",
    )

    val levels: List<LevelConfig> = (1..24).map { id ->
        val chapter = (id - 1) / 8
        val target = 3 + (id + 1) / 3
        val duration = (78 - id).coerceAtLeast(52)
        LevelConfig(
            id = id,
            title = "Смена $id",
            subtitle = when (chapter) {
                0 -> "Тёплый старт у вокзала"
                1 -> "Обеденный наплыв"
                else -> "Вечерний пик"
            },
            durationSeconds = duration,
            targetOrders = target,
            maxMistakes = 3,
            speedLabel = when (chapter) {
                0 -> "спокойно"
                1 -> "быстро"
                else -> "жарко"
            },
        )
    }

    val endlessLevel = LevelConfig(
        id = 0,
        title = "Бесконечная смена",
        subtitle = "90 секунд без паузы",
        durationSeconds = 90,
        targetOrders = Int.MAX_VALUE,
        maxMistakes = 3,
        speedLabel = "жарко",
    )

    fun levelByIdOrNull(id: Int): LevelConfig? = levels.firstOrNull { it.id == id }

    fun levelById(id: Int): LevelConfig = requireNotNull(levelByIdOrNull(id)) {
        "Unknown level id: $id"
    }

    fun orderFor(level: LevelConfig, orderIndex: Int): RecipeOrder {
        val templateIndex = (level.id * 3 + orderIndex * 2).mod(recipeTemplates.size)
        val customer = CustomerType.entries[(level.id + orderIndex).mod(CustomerType.entries.size)]
        return RecipeOrder(
            id = orderIndex + 1,
            customer = customer,
            title = orderTitles[templateIndex],
            ingredients = recipeTemplates[templateIndex],
        )
    }
}
