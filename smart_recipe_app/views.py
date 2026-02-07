from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from smart_recipe_app.forms import *
from smart_recipe_app.models import *
from smart_recipe_app.services import process_pantry_scan

# Custom decorator for restricting role access
def group_required(group_name):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if request.user.groups.filter(name=group_name).exists():
                return view_func(request, *args, **kwargs)
            return render(request, "page_not_found.html", status=403)

        return _wrapped
    return decorator

def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("login")
    else:
        form = RegisterForm()

    return render(request, "registration/register.html", {"form": form})


@login_required
def user_profile(request):
    return render(request, "registration/user_profile.html", {"user_obj": request.user})


@login_required
def index(request):
    latest_recipes = Recipe.objects.order_by("-id")[:8]

    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
    wishlist_recipes = wishlist.recipes.order_by("-id")[:4]
    wishlist_count = wishlist.recipes.count()

    today_plan, _ = DailyPlan.objects.get_or_create(
        user=request.user,
        date=date.today(),
        defaults={"wanted_calories": 2000}
    )
    today_recipes = today_plan.recipes.order_by("name")[:4]
    today_recipes_count = today_plan.recipes.count()

    total_recipes = Recipe.objects.count()

    pantry, _ = Pantry.objects.get_or_create(user=request.user)
    pantry_count = PantryItemRelation.objects.filter(pantry=pantry).count()

    return render(request, "common/index.html", {
        "latest_recipes": latest_recipes,
        "wishlist_recipes": wishlist_recipes,
        "today_recipes": today_recipes,
        "total_recipes": total_recipes,
        "pantry_count": pantry_count,
        "wishlist_count": wishlist_count,
        "today_recipes_count": today_recipes_count,
    })


# ===== ALLERGEN VIEWS =====
@login_required
@group_required("Admin")
def allergen_list(request):
    allergens = Allergen.objects.all().order_by("name")
    return render(request, "allergens/allergens.html", {"allergens": allergens})


@login_required
@group_required("Admin")
def allergen_create(request):
    if request.method == "POST":
        form = AllergenForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("allergen_list")
    else:
        form = AllergenForm()

    return render(request, "allergens/allergen_form.html", {"form": form})


@login_required
@group_required("Admin")
def allergen_edit(request, pk):
    allergen = get_object_or_404(Allergen, pk=pk)
    if request.method == "POST":
        form = AllergenForm(request.POST, instance=allergen)
        if form.is_valid():
            form.save()
            return redirect("allergen_list")
    else:
        form = AllergenForm(instance=allergen)

    return render(request, "allergens/allergen_form.html", {"form": form})


@login_required
@group_required("Admin")
def allergen_delete(request, pk):
    allergen = get_object_or_404(Allergen, pk=pk)

    if request.method == "POST":
        allergen.delete()
        messages.success(request, "Allergen deleted.")
        return redirect("allergen_list")

    return render(request, "common/confirm_delete.html", {
        "object_type": "Allergen",
        "object_name": allergen.name,
        "warning": "Deleting this allergen may affect recipe filtering for users.",
        "cancel_url": reverse("allergen_list"),
    })


# ===== DIET VIEWS =====
@login_required
@group_required("Admin")
def diet_list(request):
    diets = Diet.objects.all().order_by("name")
    return render(request, "diets/diets.html", {"diets": diets})


@login_required
@group_required("Admin")
def diet_create(request):
    if request.method == "POST":
        form = DietForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("diet_list")
    else:
        form = DietForm()
    return render(request, "diets/diet_form.html", {"form": form})


@login_required
@group_required("Admin")
def diet_edit(request, pk):
    diet = get_object_or_404(Diet, pk=pk)
    if request.method == "POST":
        form = DietForm(request.POST, instance=diet)
        if form.is_valid():
            form.save()
            return redirect("diet_list")
    else:
        form = DietForm(instance=diet)
    return render(request, "diets/diet_form.html", {"form": form})


@login_required
@group_required("Admin")
def diet_delete(request, pk):
    diet = get_object_or_404(Diet, pk=pk)

    if request.method == "POST":
        diet.delete()
        messages.success(request, "Diet deleted.")
        return redirect("diet_list")

    return render(request, "common/confirm_delete.html", {
        "object_type": "Diet",
        "object_name": diet.name,
        "warning": "Deleting this diet will remove diet compatibility info from ingredients.",
        "cancel_url": reverse("diet_list"),
    })


# ===== INGREDIENT VIEWS =====
@login_required
@group_required("Admin")
def ingredient_list(request):
    q = (request.GET.get("q") or "").strip()

    ingredients = (Ingredient.objects.prefetch_related("diets", "allergens").order_by("name"))

    if q:
        ingredients = ingredients.filter(name__icontains=q)

    return render(request, "ingredients/ingredients.html", {"ingredients": ingredients, "q": q, })


@login_required
@group_required("Admin")
def ingredient_create(request):
    next_url = request.GET.get("next") or request.POST.get("next")

    if request.method == "POST":
        form = IngredientForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect(next_url or "ingredient_list")
    else:
        form = IngredientForm()

    return render(request, "ingredients/ingredient_form.html", {
        "form": form,
        "next": next_url,
    })


@login_required
@group_required("Admin")
def ingredient_edit(request, pk):
    ingredient = get_object_or_404(Ingredient, pk=pk)

    if request.method == "POST":
        form = IngredientForm(request.POST, instance=ingredient)
        if form.is_valid():
            form.save()
            return redirect("ingredient_list")
    else:
        form = IngredientForm(instance=ingredient)

    return render(request, "ingredients/ingredient_form.html", {"form": form})


@login_required
@group_required("Admin")
def ingredient_delete(request, pk):
    ingredient = get_object_or_404(Ingredient, pk=pk)

    if request.method == "POST":
        ingredient.delete()
        messages.success(request, "Ingredient deleted.")
        return redirect("ingredient_list")

    return render(request, "common/confirm_delete.html", {
        "object_type": "Ingredient",
        "object_name": ingredient.name,
        "warning": "This may affect recipes and pantry items that use this ingredient.",
        "cancel_url": reverse("ingredient_list"),
    })


# ===== RECIPE VIEWS =====
@login_required
def recipe_list(request):
    qs = Recipe.objects.prefetch_related("recipe_ingredients__ingredient").order_by("name")
    qs = qs.exclude(recipe_ingredients__isnull=True).distinct()

    diet_id = request.GET.get("diet_id")
    allergen_id = request.GET.get("allergen_id")
    q = request.GET.get("q")

    if diet_id:
        qs = Recipe.recipes_for_diet(diet_id).prefetch_related("recipe_ingredients__ingredient").order_by("name")

    if allergen_id:
        qs = qs.exclude(recipe_ingredients__ingredient__allergens__id=allergen_id).distinct()

    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q)).distinct()

    diets = Diet.objects.all().order_by("name")
    allergens = Allergen.objects.all().order_by("name")

    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
    wishlist_recipe_ids = set(wishlist.recipes.values_list("id", flat=True))

    today_plan, _ = DailyPlan.objects.get_or_create(
        user=request.user,
        date=date.today(),
        defaults={"wanted_calories": 2000}
    )
    daily_plan_recipe_ids = set(today_plan.recipes.values_list("id", flat=True))

    return render(request, "recipes/recipes.html", {
        "recipes": qs,
        "diets": diets,
        "allergens": allergens,
        "selected_diet_id": diet_id,
        "selected_allergen_id": allergen_id,
        "q": q or "",
        "wishlist_recipe_ids": wishlist_recipe_ids,
        "daily_plan_recipe_ids": daily_plan_recipe_ids,
    })


@login_required
def recipe_detail(request, pk):
    recipe = get_object_or_404(
        Recipe.objects.prefetch_related(
            Prefetch(
                "recipe_ingredients",
                queryset=RecipeIngredientRelation.objects.select_related("ingredient")
            )
        ),
        pk=pk
    )

    relations = list(recipe.recipe_ingredients.all())

    total_calories = 0.0
    for rel in relations:
        ing = rel.ingredient

        base_amount = float(ing.base_amount or 1)
        calories_base = float(ing.calories_per_base_amount or 0)

        calories_per_unit = calories_base / base_amount

        rel.calories_calc = float(rel.quantity or 0) * calories_per_unit

        total_calories += rel.calories_calc

    calories_per_serving = None
    if recipe.no_of_servings:
        servings = float(recipe.no_of_servings)
        if servings > 0:
            calories_per_serving = total_calories / servings

    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
    is_in_wishlist = wishlist.recipes.filter(pk=recipe.pk).exists()

    today_plan, _ = DailyPlan.objects.get_or_create(
        user=request.user,
        date=date.today(),
        defaults={"wanted_calories": 2000}
    )
    is_in_today_plan = today_plan.recipes.filter(pk=recipe.pk).exists()

    return render(request, "recipes/recipe_detail.html", {
        "recipe": recipe,
        "relations": relations,
        "total_calories": total_calories,
        "calories_per_serving": calories_per_serving,
        "is_in_wishlist": is_in_wishlist,
        "is_in_today_plan": is_in_today_plan,
    })


@login_required
@group_required("Admin")
def recipe_create(request):
    if request.method == "POST":
        form = RecipeForm(request.POST, request.FILES)
        if form.is_valid():
            recipe = form.save()
            return redirect("recipe_edit_ingredients", pk=recipe.pk)
    else:
        form = RecipeForm()

    return render(request, "recipes/recipe_form.html", {"form": form})


@login_required
@group_required("Admin")
def recipe_edit(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)

    recipe_form = RecipeForm(request.POST or None, request.FILES or None, instance=recipe)
    ingredient_form = RecipeIngredientRelationForm(request.POST or None)

    if request.method == "POST" and "save_recipe" in request.POST:
        if recipe_form.is_valid():
            recipe_form.save()
            return redirect("recipe_list")

    if request.method == "POST" and "add_ingredient" in request.POST:
        if ingredient_form.is_valid():
            rel = ingredient_form.save(commit=False)
            rel.recipe = recipe
            rel.save()
            return redirect("recipe_edit", pk=pk)

    relations = recipe.recipe_ingredients.select_related("ingredient").all()

    return render(request, "recipes/recipe_edit.html", {
        "recipe": recipe,
        "recipe_form": recipe_form,
        "ingredient_form": ingredient_form,
        "relations": relations,
    })


@login_required
@group_required("Admin")
def recipe_edit_ingredients(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)

    relations = recipe.recipe_ingredients.select_related("ingredient").all()

    edit_id = request.GET.get("edit")
    editing_rel = None
    if edit_id:
        editing_rel = get_object_or_404(
            RecipeIngredientRelation,
            pk=edit_id,
            recipe=recipe
        )

    if request.method == "POST":
        # if editing_rel exists -> update that row
        if editing_rel:
            form = RecipeIngredientRelationForm(request.POST, instance=editing_rel)
        else:
            form = RecipeIngredientRelationForm(request.POST)

        if form.is_valid():
            rel = form.save(commit=False)
            rel.recipe = recipe
            rel.save()
            return redirect("recipe_edit_ingredients", pk=pk)  # clears ?edit
    else:
        # prefill when editing
        if editing_rel:
            form = RecipeIngredientRelationForm(instance=editing_rel)
        else:
            form = RecipeIngredientRelationForm()

    return render(request, "recipes/recipe_edit_ingredients.html", {
        "recipe": recipe,
        "form": form,
        "relations": relations,
        "editing_rel": editing_rel,
    })


@login_required
@group_required("Admin")
def recipe_remove_ingredient(request, pk, relation_id):
    recipe = get_object_or_404(Recipe, pk=pk)
    relation = get_object_or_404(
        RecipeIngredientRelation,
        id=relation_id,
        recipe=recipe
    )

    if request.method == "POST":
        relation.delete()
        return redirect("recipe_edit_ingredients", pk=pk)

    return render(request, "common/confirm_delete.html", {
        "object_type": "Ingredient from recipe",
        "object_name": relation.ingredient.name,
        "warning": f"This will remove '{relation.ingredient.name}' from '{recipe.name}'.",
        "cancel_url": reverse("recipe_edit_ingredients", args=[pk]),
    })


@login_required
@group_required("Admin")
def recipe_delete(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)

    next_url = request.GET.get("next") or request.POST.get("next") or reverse("recipe_list")

    if request.method == "POST":
        recipe.delete()
        messages.success(request, "Recipe deleted.")
        return redirect(next_url)

    return render(request, "common/confirm_delete.html", {
        "object_type": "Recipe",
        "object_name": recipe.name,
        "warning": "Deleting this recipe will also remove its ingredient relations.",
        "cancel_url": next_url,
        "next": next_url,
    })


@login_required
@require_POST
def toggle_wishlist(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)
    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)

    if wishlist.recipes.filter(pk=recipe.pk).exists():
        wishlist.recipes.remove(recipe)
        messages.success(request, "Removed from wishlist.")
    else:
        wishlist.recipes.add(recipe)
        messages.success(request, "Added to wishlist.")

    return redirect("recipe_detail", pk=pk)


@login_required
@require_POST
def add_recipe_to_today_plan(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)

    plan, _ = DailyPlan.objects.get_or_create(
        user=request.user,
        date=date.today(),
        defaults={"wanted_calories": 2000},
    )

    if plan.recipes.filter(pk=recipe.pk).exists():
        plan.recipes.remove(recipe)
        messages.success(request, "Removed from today’s plan.")
    else:
        plan.recipes.add(recipe)
        messages.success(request, "Added to today’s plan.")

    return redirect("recipe_detail", pk=pk)


# ===== PANTRY VIEWS =====
def _get_user_pantry(user):
    pantry, _ = Pantry.objects.get_or_create(user=user)
    return pantry


@login_required
def pantry_list(request):
    pantry = _get_user_pantry(request.user)
    items = pantry.items.select_related('ingredient').all()

    return render(request, 'pantry/pantry.html', {
        'pantry': pantry,
        'items': items,
        'today': date.today(),
    })


@login_required
def pantry_add_item(request):
    pantry = _get_user_pantry(request.user)

    if request.method == "POST":
        form = PantryItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.pantry = pantry
            item.source = PantryItemRelation.Source.MANUAL

            # Check if ingredient already exists in pantry
            existing = PantryItemRelation.objects.filter(
                pantry=pantry,
                ingredient=item.ingredient
            ).first()

            if existing:
                # Update quantity instead of creating duplicate
                existing.quantity += item.quantity
                existing.save()
            else:
                item.save()

            return redirect('pantry')
    else:
        form = PantryItemForm()

    return render(request, 'pantry/pantry_item_form.html', {'form': form})


@login_required
def pantry_edit_item(request, item_id):
    pantry = _get_user_pantry(request.user)
    item = get_object_or_404(PantryItemRelation, id=item_id, pantry=pantry)

    if request.method == "POST":
        form = PantryItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            return redirect("pantry")
    else:
        form = PantryItemForm(instance=item)

    return render(request, 'pantry/pantry_item_form.html', {'form': form, 'item': item})


@login_required
def pantry_delete_item(request, item_id):
    pantry = _get_user_pantry(request.user)
    item = get_object_or_404(PantryItemRelation, id=item_id, pantry=pantry)

    if request.method == "POST":
        item.delete()
        return redirect("pantry")

    return render(request, "common/confirm_delete.html", {
        "object_type": "Pantry item",
        "object_name": item.ingredient.name,
        "warning": "This will remove the item from your pantry.",
        "cancel_url": reverse("pantry"),
    })


# ===== WISHLIST VIEWS =====
@login_required
def wishlist_view(request):
    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)

    if request.method == "POST":
        recipe_id = request.POST.get("recipe_id")
        recipe = get_object_or_404(Recipe, id=recipe_id)

        if "add" in request.POST:
            wishlist.recipes.add(recipe)
            messages.success(request, "Added to wishlist.")
        elif "remove" in request.POST:
            wishlist.recipes.remove(recipe)
            messages.success(request, "Removed from wishlist.")

        return redirect("wishlist")

    wishlist_recipes = wishlist.recipes.all().order_by("name")
    all_recipes = Recipe.objects.all().order_by("name")

    wishlist_recipe_ids = set(wishlist_recipes.values_list("id", flat=True))

    return render(request, "wishlist/wishlist.html", {
        "wishlist": wishlist,
        "wishlist_recipes": wishlist_recipes,
        "all_recipes": all_recipes,
        "wishlist_recipe_ids": wishlist_recipe_ids,
    })


# ===== DAILY PLAN VIEWS =====
@login_required
def daily_plans_list(request):
    plans = DailyPlan.objects.filter(user=request.user).order_by('-date')

    today_plan = plans.filter(date=date.today()).first()
    past_plans = plans.exclude(date=date.today())

    return render(request, 'daily_plan/daily_plans.html', {
        'plans': plans,
        'today_plan': today_plan,
        'past_plans': past_plans,
    })


@login_required
def daily_plan_detail(request, plan_id):
    plan = get_object_or_404(DailyPlan, id=plan_id, user=request.user)
    return render(request, 'daily_plan/daily_plan_detail.html', {'plan': plan})


@login_required
def daily_plan_create(request):
    if request.method == 'POST':
        form = DailyPlanForm(request.POST)
        if form.is_valid():
            plan = form.save(commit=False)
            plan.user = request.user
            plan.save()
            return redirect('daily_plan_detail', plan_id=plan.id)
    else:
        form = DailyPlanForm()

    return render(request, 'daily_plan/daily_plan_form.html', {'form': form})


@login_required
@require_POST
def daily_plan_update(request, plan_id):
    plan = get_object_or_404(DailyPlan, id=plan_id, user=request.user)

    try:
        new_calories = int(request.POST.get('wanted_calories', 2000))
        if 500 <= new_calories <= 10000:
            plan.wanted_calories = new_calories
            plan.save()
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'error': 'Calories must be between 500 and 10000'}, status=400)
    except ValueError:
        return JsonResponse({'error': 'Invalid value'}, status=400)


@login_required
def daily_plan_remove_recipe(request, plan_id, recipe_id):
    plan = get_object_or_404(DailyPlan, id=plan_id, user=request.user)
    recipe = get_object_or_404(Recipe, id=recipe_id)

    if request.method == "POST":
        plan.recipes.remove(recipe)
        messages.success(request, f'"{recipe.name}" removed from the plan.')
        return redirect("daily_plans")  # stays on daily plans page

    # GET -> show confirm delete form
    return render(request, "common/confirm_delete.html", {
        "object_type": "Meal",
        "object_name": recipe.name,
        "warning": f"This will remove the recipe from {plan.date.strftime('%d %b %Y')}. The recipe itself will NOT be deleted.",
        "cancel_url": reverse("daily_plans"),
        "action_url": reverse("daily_plan_remove_recipe", args=[plan.id, recipe.id]),
        "confirm_text": "Remove",
    })


@login_required
def daily_plan_delete(request, plan_id):
    plan = get_object_or_404(DailyPlan, id=plan_id, user=request.user)

    # block deleting today's plan
    if plan.date == timezone.now().date():
        messages.error(request, "You cannot delete today's plan.")
        return redirect("daily_plans")

    if request.method == "POST":
        plan.delete()
        messages.success(request, "Daily plan deleted.")
        return redirect("daily_plans")

    # GET -> show confirm delete form
    return render(request, "common/confirm_delete.html", {
        "object_type": "Daily Plan",
        "object_name": plan.date.strftime("%d %b %Y"),
        "warning": "Deleting this plan will remove all recipes saved in it (for that day).",
        "cancel_url": reverse("daily_plans"),
        "action_url": reverse("daily_plan_delete", args=[plan.id]),
        "confirm_text": "Delete",
    })


# Views from services
# Add to views.py

@login_required
def suggest_daily_plan(request):
    """
    View to suggest recipes based on user's dietary preferences
    """
    if request.method == "POST":
        wanted_calories = int(request.POST.get('wanted_calories', 2000))
        diet_id = request.POST.get('diet_id')
        allergen_ids = request.POST.getlist('allergen_ids')

        diet = Diet.objects.get(pk=diet_id) if diet_id else None

        from smart_recipe_app.services import suggest_recipes
        suggested, total = suggest_recipes(
            wanted_calories=wanted_calories,
            diet=diet,
            excluded_allergen_ids=allergen_ids
        )

        return render(request, 'daily_plan/suggestions.html', {
            'suggested_recipes': suggested,
            'total_calories': total,
            'wanted_calories': wanted_calories,
        })

    diets = Diet.objects.all()
    allergens = Allergen.objects.all()

    return render(request, 'daily_plan/suggest_form.html', {
        'diets': diets,
        'allergens': allergens,
    })


@login_required
def cookable_recipes(request):
    """
    Show recipes user can cook with current pantry
    """
    from smart_recipe_app.services import get_cookable_recipes

    cookable = get_cookable_recipes(request.user)

    return render(request, 'recipes/cookable.html', {
        'recipes': cookable,
    })


# ML model
@login_required
def pantry_scan_create(request):
    if request.method == "POST":
        form = PantryScanForm(request.POST, request.FILES)
        if form.is_valid():
            scan = form.save(commit=False)
            scan.user = request.user
            scan.status = PantryScan.Status.PROCESSING
            scan.save()

            return redirect("pantry_scan_processing", scan_id=scan.id)
        else:
            messages.error(request, "Upload failed. Please choose an image file.")
    else:
        form = PantryScanForm()

    return render(request, "pantry/ml_model/pantry_scan_upload.html", {"form": form})


@login_required
def pantry_scan_review(request, scan_id):
    scan = get_object_or_404(PantryScan, id=scan_id, user=request.user)
    detections = scan.detections.all()

    if request.method == "POST":
        pantry = _get_user_pantry(request.user)

        # ---- MANUAL ITEMS ----
        manual_products = request.POST.getlist("manual_product[]")
        manual_quantities = request.POST.getlist("manual_quantity[]")

        for product, qty in zip(manual_products, manual_quantities):
            ingredient = _get_or_create_ingredient(product)
            if ingredient is None:
                continue

            try:
                quantity = int(qty) if qty else 1
            except ValueError:
                quantity = 1

            _add_to_pantry(pantry, ingredient, quantity, PantryItemRelation.Source.MANUAL)

        # ---- DETECTIONS ----
        for d in detections:
            action = request.POST.get(f"action_{d.id}")

            qty_str = request.POST.get(f"quantity_{d.id}")
            try:
                qty = int(qty_str) if qty_str else 1
            except ValueError:
                qty = 1
            qty = max(1, qty)

            if action == "accept":
                ingredient = _get_or_create_ingredient(d.label)
                if ingredient is None:
                    d.status = PantryScanDetection.ReviewStatus.REJECTED
                    d.save(update_fields=["status"])
                    continue

                _add_to_pantry(pantry, ingredient, qty, PantryItemRelation.Source.ML_SCAN)

                d.matched_ingredient = ingredient
                d.status = PantryScanDetection.ReviewStatus.ACCEPTED
                d.save(update_fields=["matched_ingredient", "status"])
            else:
                d.status = PantryScanDetection.ReviewStatus.REJECTED
                d.save(update_fields=["status"])

        return redirect("pantry")

    return render(request, "pantry/ml_model/pantry_scan_review.html", {
        "scan": scan,
        "detections": detections,
    })
def _get_or_create_ingredient(label: str) -> Ingredient | None:
    label = (label or "").strip().lower()
    if not label:
        return None

    ingredient = Ingredient.objects.filter(name__iexact=label).first()
    if ingredient is None:
        ingredient = Ingredient.objects.create(
            name=label,
            base_unit="pcs",
            base_amount=1,
            calories_per_base_amount=0
        )
    return ingredient


def _add_to_pantry(pantry: Pantry, ingredient: Ingredient, quantity: int, source) -> PantryItemRelation:
    quantity = max(1, int(quantity or 1))

    obj, created = PantryItemRelation.objects.get_or_create(
        pantry=pantry,
        ingredient=ingredient,
        defaults={"quantity": quantity, "source": source},
    )
    if not created:
        obj.quantity += quantity
        obj.source = source
        obj.save(update_fields=["quantity", "source"])
    return obj

@login_required
def pantry_scan_processing(request, scan_id):
    scan = get_object_or_404(PantryScan, id=scan_id, user=request.user)

    # If already done/failed, jump away
    if scan.status == PantryScan.Status.DONE:
        return redirect("pantry_scan_review", scan_id=scan.id)

    if scan.status == PantryScan.Status.FAILED:
        messages.error(request, f"Scan failed: {scan.error_message}")
        return redirect("pantry_scan")

    # RUN THE SCAN NOW (SYNC)
    process_pantry_scan(scan)

    if scan.status == PantryScan.Status.FAILED:
        messages.error(request, f"Scan failed: {scan.error_message}")
        return redirect("pantry_scan")

    return redirect("pantry_scan_review", scan_id=scan.id)
