package com.andrejivliev.shawarma58.ui

import com.andrejivliev.shawarma58.R
import com.andrejivliev.shawarma58.data.CustomerType
import com.andrejivliev.shawarma58.data.Ingredient

fun imageFor(ingredient: Ingredient): Int = when (ingredient) {
    Ingredient.LAVASH -> R.drawable.ingredient_lavash
    Ingredient.CHICKEN -> R.drawable.ingredient_chicken
    Ingredient.TOMATO -> R.drawable.ingredient_tomato
    Ingredient.CUCUMBER -> R.drawable.ingredient_cucumber
    Ingredient.GREENS -> R.drawable.ingredient_greens
    Ingredient.GARLIC -> R.drawable.ingredient_garlic
    Ingredient.SPICY -> R.drawable.ingredient_spicy
    Ingredient.FRIES -> R.drawable.ingredient_fries
}

fun imageFor(customer: CustomerType): Int = when (customer) {
    CustomerType.OFFICE -> R.drawable.customer_office
    CustomerType.STUDENT -> R.drawable.customer_student
    CustomerType.COURIER -> R.drawable.customer_courier
    CustomerType.NEIGHBOR -> R.drawable.customer_neighbor
}
