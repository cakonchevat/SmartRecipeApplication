from .models import Recipe, Pantry


def suggest_recipes(wanted_calories, diet=None, excluded_allergen_ids=None):
    """
    Unified greedy algorithm to suggest recipes based on:
    - wanted_calories: target calorie goal
    - diet: optional Diet object or diet_id to filter by
    - excluded_allergen_ids: list of allergen IDs to exclude

    Returns: list of Recipe objects that fit within calorie budget
    """
    excluded_allergen_ids = excluded_allergen_ids or []

    # Start with all recipes
    recipes = Recipe.objects.all()

    # Filter by diet if specified
    if diet is not None:
        diet_id = diet.id if hasattr(diet, "id") else diet
        recipes = Recipe.recipes_for_diet(diet_id)

    # Exclude recipes with specified allergens
    if excluded_allergen_ids:
        recipes = recipes.exclude(
            recipe_ingredients__ingredient__allergens__id__in=excluded_allergen_ids
        ).distinct()

    # Build list of (recipe, calories_per_serving) tuples
    recipes_with_cals = []
    for recipe in recipes:
        cals = recipe.calories_per_serving or 0
        if cals > 0:
            recipes_with_cals.append((recipe, cals))

    # Sort by calories (ascending) - greedy approach
    recipes_with_cals.sort(key=lambda t: t[1])

    # Select recipes until budget is reached
    selected = []
    total = 0

    for recipe, cals in recipes_with_cals:
        if total + cals <= wanted_calories:
            selected.append(recipe)
            total += cals

    return selected, total  # Return both recipes and total calories


def suggest_recipes_for_calories(user, wanted_calories, diet=None):
    """
    Backward-compatible wrapper for suggest_recipes
    """
    selected, _ = suggest_recipes(wanted_calories, diet=diet)
    return selected


def suggest_recipes_excluding_allergens(wanted_calories, excluded_allergen_ids=None):
    """
    Backward-compatible wrapper for suggest_recipes
    """
    selected, _ = suggest_recipes(wanted_calories, excluded_allergen_ids=excluded_allergen_ids)
    return selected


def can_cook_with_pantry(recipe, pantry):
    """
    Check if user has enough ingredients in pantry to cook a recipe

    Returns: (bool, list of missing ingredients)
    """
    missing = []

    for relation in recipe.recipe_ingredients.all():
        needed_ingredient = relation.ingredient
        needed_quantity = relation.quantity

        # Check if ingredient exists in pantry
        pantry_item = pantry.items.filter(ingredient=needed_ingredient).first()

        if not pantry_item:
            missing.append((needed_ingredient, needed_quantity, 0))
        elif pantry_item.quantity < needed_quantity:
            missing.append((needed_ingredient, needed_quantity, pantry_item.quantity))

    can_cook = len(missing) == 0
    return can_cook, missing


def get_cookable_recipes(user):
    """
    Get all recipes that user can cook with current pantry
    """
    pantry, _ = Pantry.objects.get_or_create(user=user)
    recipes = Recipe.objects.all()

    cookable = []
    for recipe in recipes:
        can_cook, _ = can_cook_with_pantry(recipe, pantry)
        if can_cook:
            cookable.append(recipe)

    return cookable