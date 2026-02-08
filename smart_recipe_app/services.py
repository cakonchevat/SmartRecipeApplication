from .ml_scan import detect_ingredients_local_yolo
from .models import Recipe, Pantry, PantryScan, PantryScanDetection, PantryItemRelation, Ingredient, RecipeIngredientRelation
from django.utils import timezone
import os
import re
import requests
from django.core.files.base import ContentFile
from .models import RecipeIngredientRelation

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


def process_pantry_scan(scan: PantryScan) -> None:
    """
    Runs Claude scan, stores raw_output, and creates PantryScanDetection rows (PENDING).
    User later reviews, matches to Ingredient, edits quantity, accepts/rejects.
    """
    scan.status = PantryScan.Status.PROCESSING
    scan.error_message = ""
    scan.save(update_fields=["status", "error_message"])

    try:
        results = detect_ingredients_local_yolo(scan.image.path)

        scan.raw_output = results
        scan.status = PantryScan.Status.DONE
        scan.processed_at = timezone.now()
        scan.save(update_fields=["raw_output", "status", "processed_at"])

        scan.detections.all().delete()
        for r in results:
            PantryScanDetection.objects.create(
                scan=scan,
                label=r["label"],
                confidence=float(r.get("confidence", 0.6)),
                quantity_guess=r.get("quantity_guess", None),
                status=PantryScanDetection.ReviewStatus.PENDING,
            )

    except Exception as e:
        scan.status = PantryScan.Status.FAILED
        scan.error_message = str(e)
        scan.save(update_fields=["status", "error_message"])


def apply_detection_to_pantry(pantry, ingredient: Ingredient, quantity: float):
    """
    Add/update pantry item after user review.
    Quantity is in ingredient.base_unit.
    """
    if quantity is None or quantity <= 0:
        quantity = 1

    obj, created = PantryItemRelation.objects.get_or_create(
        pantry=pantry,
        ingredient=ingredient,
        defaults={"quantity": quantity, "source": PantryItemRelation.Source.ML_SCAN},
    )
    if not created:
        obj.quantity += quantity
        obj.source = PantryItemRelation.Source.ML_SCAN
        obj.save(update_fields=["quantity", "source"])

    return obj


def build_unsplash_query(recipe):
    """
    Build focused search queries prioritizing recipe name.
    Simpler queries = better matches with website search.
    """
    name = recipe.name.strip()

    queries = []

    # Strategy 1: Just the recipe name (simplest, often best!)
    queries.append(name)

    # Strategy 2: Recipe name + "recipe"
    queries.append(f"{name} recipe")

    # Strategy 3: Recipe name + "dish"
    queries.append(f"{name} dish")

    # Strategy 4: Recipe name + "food" (last resort)
    queries.append(f"{name} food")

    return queries


def _get_single_key_ingredient(recipe):
    """
    Get ONE most important ingredient (not generic).
    This is only used for generic recipe names like 'soup' or 'salad'.
    """
    GENERIC_INGREDIENTS = {
        'salt', 'pepper', 'water', 'oil', 'olive oil', 'vegetable oil',
        'butter', 'sugar', 'flour', 'black pepper', 'white pepper',
        'egg', 'eggs', 'milk', 'cream'  # Added common baking ingredients
    }

    relations = (RecipeIngredientRelation.objects
                 .select_related("ingredient")
                 .filter(recipe_id=recipe.pk)
                 .order_by("-quantity"))

    for rel in relations:
        ing_name = rel.ingredient.name.lower().strip()

        # Return first non-generic ingredient
        if ing_name not in GENERIC_INGREDIENTS:
            return ing_name

    return ""


def _safe_name_for_file(text: str) -> str:
    text = text.strip().lower().replace(" ", "_")
    text = re.sub(r"[^a-z0-9_]+", "", text)
    return text[:40] if text else "recipe"


def _search_unsplash(query, access_key):
    """
    Search Unsplash with a single query.
    Returns photo dict or None.
    """
    search_url = "https://api.unsplash.com/search/photos"
    headers = {"Authorization": f"Client-ID {access_key}"}
    params = {
        "query": query,
        "per_page": 5,  # Get top 5 instead of just 1
        "orientation": "landscape",
        "content_filter": "high",
        "order_by": "relevant"
    }

    try:
        r = requests.get(search_url, params=params, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        results = data.get("results", [])

        if results:
            # return the first (most relevant)
            return results[0]

        return None

    except Exception as e:
        print(f"Search failed for '{query}': {repr(e)}")
        return None


def generate_recipe_image_if_missing(recipe, force_regenerate=False) -> bool:
    print("\nUNSPLASH GENERATOR START")
    print(f"Recipe: {recipe.pk} - {recipe.name}")

    if recipe.image and not force_regenerate:
        print("✓ Recipe already has image")
        return False

    # Delete old image if forcing regeneration
    if force_regenerate and recipe.image:
        print("Forcing regeneration - deleting old image")
        recipe.image.delete(save=False)

    has_ingredients = RecipeIngredientRelation.objects.filter(recipe_id=recipe.pk).exists()
    if not has_ingredients:
        print("✗ No ingredients yet - skipping image generation")
        return False

    access_key = os.getenv("UNSPLASH_ACCESS_KEY")
    if not access_key:
        print("✗ UNSPLASH_ACCESS_KEY not set in environment")
        return False

    # Get query strategies
    queries = build_unsplash_query(recipe)
    print(f"Generated {len(queries)} search strategies:")
    for i, q in enumerate(queries, 1):
        print(f"  {i}. '{q}'")

    photo = None
    successful_query = None

    # Try each query until one succeeds
    for query in queries:
        print(f"\nTrying: '{query}'")
        photo = _search_unsplash(query, access_key)

        if photo:
            successful_query = query
            print(f"✓ Found match with: '{query}'")
            break
        else:
            print(f"✗ No results for: '{query}'")

    if not photo:
        print("✗ No images found with any strategy")
        return False

    # Download and save the image
    try:
        # Track download for Unsplash API guidelines
        download_location = photo["links"]["download_location"]
        headers = {"Authorization": f"Client-ID {access_key}"}
        requests.get(download_location, headers=headers, timeout=5)

        # Get the image
        image_url = photo["urls"]["regular"]
        img_resp = requests.get(image_url, timeout=15)
        img_resp.raise_for_status()

        # Determine file extension
        content_type = (img_resp.headers.get("Content-Type") or "").lower()
        ext = "jpg"
        if "png" in content_type:
            ext = "png"
        elif "webp" in content_type:
            ext = "webp"

        filename = f"auto_{_safe_name_for_file(recipe.name)}_{recipe.pk}.{ext}"
        recipe.image.save(filename, ContentFile(img_resp.content), save=True)

        print(f"✓ Image saved: {recipe.image.name}")
        print(f"✓ Source query: '{successful_query}'")
        print("=== UNSPLASH GENERATOR SUCCESS ===\n")
        return True

    except Exception as e:
        print(f"✗ Error downloading image: {repr(e)}")
        print("=== UNSPLASH GENERATOR FAIL ===\n")
        return False
