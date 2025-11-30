from .models import Recipe


def suggest_recipes_for_calories(user, wanted_calories, diet=None):
    """
    Едноставен greedy алгоритам:
    - ги зема сите рецепти (или филтрирани по diet)
    - ги сортира по calories_per_serving
    - додава се додека не ја наполни целта
    """
    recipes = Recipe.objects.all()

    if diet is not None:
        recipes = recipes.filter(ingredients__diets=diet).distinct()

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
