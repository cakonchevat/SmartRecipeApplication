from .models import Recipe


def suggest_recipes_for_calories(user, wanted_calories, diet=None):
    """
    Едноставен greedy алгоритам:
    - ги зема сите рецепти (или филтрирани по diets)
    - ги сортира по calories_per_serving
    - додава се додека не ја наполни целта
    """
    recipes = Recipe.objects.all()

    if diet is not None:
        diet_id = diet.id if hasattr(diet, "id") else diet
        recipes = Recipe.recipes_for_diet(diet_id)  # call on the recipes_for_diet function, that matches recipes where ALL INGREDIENTS match the diet

    recipes_with_cals = []
    for recipe in recipes:
        cals = recipe.calories_per_serving or 0
        if cals > 0:
            recipes_with_cals.append((recipe, cals))

    recipes_with_cals.sort(key=lambda t: t[1])  # од помал кон поголем

    selected = []
    total = 0

    for recipe, cals in recipes_with_cals:
        if total + cals <= wanted_calories:
            selected.append(recipe)
            total += cals

    return selected


def suggest_recipes_excluding_allergens(wanted_calories, excluded_allergen_ids=None):
    """
    Greedy suggestion:
    - return recipes that do NOT contain ingredients with excluded allergens
    - select recipes until wanted_calories is reached
    """
    excluded_allergen_ids = excluded_allergen_ids or []

    recipes = Recipe.objects.all()

    # Exclude recipes that contain at least one ingredient with a blocked allergen
    if excluded_allergen_ids:
        recipes = recipes.exclude(
            recipe_ingredients__ingredient__allergens__id__in=excluded_allergen_ids
        ).distinct()

    recipes_with_cals = []
    for recipe in recipes:
        cals = recipe.calories_per_serving or 0
        if cals > 0:
            recipes_with_cals.append((recipe, cals))

    # Sort by calories per serving (ascending)
    recipes_with_cals.sort(key=lambda t: t[1])

    selected = []
    total = 0

    for recipe, cals in recipes_with_cals:
        if total + cals <= wanted_calories:
            selected.append(recipe)
            total += cals

    return selected
