from .ml_scan import detect_ingredients_local_yolo
from .models import Recipe, Pantry, PantryScan, PantryScanDetection, PantryItemRelation, Ingredient
import base64
import json
import os
from django.utils import timezone

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


def _guess_media_type(image_path: str) -> str:
    lower = image_path.lower()
    if lower.endswith(".jpg") or lower.endswith(".jpeg"):
        return "image/jpeg"
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith(".gif"):
        return "image/gif"
    if lower.endswith(".webp"):
        return "image/webp"
    return "image/jpeg"


def _b64_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def detect_ingredients_with_claude(image_path: str):
    """
    Returns list of dicts:
    [{"label": "banana", "confidence": 0.82, "quantity_guess": 3}, ...]
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("Missing ANTHROPIC_API_KEY in environment (.env).")

    try:
        from anthropic import Anthropic
    except Exception as e:
        raise RuntimeError("Missing package 'anthropic'. Install with: pip install anthropic") from e

    client = Anthropic(api_key=api_key)

    media_type = _guess_media_type(image_path)
    img_b64 = _b64_image(image_path)

    prompt = """
Return ONLY valid JSON (no markdown, no extra text).

Identify FOOD ingredients/items visible in the image (fridge/pantry photo).
Use short common names in English, lowercase. Avoid brands.

Output must be a JSON array, each element:
{
  "label": "banana",
  "confidence": 0.0-1.0,
  "quantity_guess": number or null
}
"""

    resp = client.messages.create(
        model="claude-3-5-sonnet-latest",
        max_tokens=600,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": img_b64,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )

    text_out = ""
    for block in resp.content:
        if getattr(block, "type", None) == "text":
            text_out += block.text

    text_out = text_out.strip()

    try:
        data = json.loads(text_out)
    except json.JSONDecodeError:
        # fallback: extract JSON array if extra text was returned
        start = text_out.find("[")
        end = text_out.rfind("]")
        if start != -1 and end != -1 and end > start:
            data = json.loads(text_out[start:end + 1])
        else:
            raise RuntimeError(f"Claude did not return valid JSON. Output was: {text_out[:500]}")

    normalized = []
    if isinstance(data, list):
        for item in data:
            label = str(item.get("label", "")).strip().lower()
            if not label:
                continue

            try:
                confidence = float(item.get("confidence", 0.5) or 0.5)
            except Exception:
                confidence = 0.5
            confidence = max(0.0, min(1.0, confidence))

            qg = item.get("quantity_guess", None)
            try:
                qg = float(qg) if qg is not None else None
            except Exception:
                qg = None

            normalized.append(
                {"label": label, "confidence": confidence, "quantity_guess": qg}
            )

    # dedupe by label (keep highest confidence)
    best = {}
    for item in normalized:
        lbl = item["label"]
        if lbl not in best or item["confidence"] > best[lbl]["confidence"]:
            best[lbl] = item
    normalized = list(best.values())

    return normalized


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
