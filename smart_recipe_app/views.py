from datetime import date

from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, redirect, get_object_or_404
from smart_recipe_app.forms import DietForm, IngredientForm, RecipeForm, RecipeIngredientRelationForm, DailyPlanForm, PantryItemForm, AllergenForm
from smart_recipe_app.models import Diet, RecipeIngredientRelation, Pantry, PantryItemRelation, Wishlist, Recipe, DailyPlan, Ingredient, Allergen
from django.db.models import Q
from django.urls import reverse


def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = UserCreationForm()

    return render(request, 'registration/register.html', {'form': form})


@login_required
def index(request):
    return render(request, 'common/index.html')


# ===== ALLERGEN VIEWS =====
@login_required
def allergen_list(request):
    allergens = Allergen.objects.all().order_by("name")
    return render(request, "allergens/allergens.html", {"allergens": allergens})


@login_required
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
def allergen_delete(request, pk):
    allergen = get_object_or_404(Allergen, pk=pk)

    if request.method == "POST":
        allergen.delete()
        return redirect("allergen_list")

    return render(request, "common/confirm_delete.html", {
        "object_type": "Allergen",
        "object_name": allergen.name,
        "warning": "Deleting this allergen may affect recipe filtering for users.",
        "cancel_url": reverse("allergen_list"),
    })


# ===== DIET VIEWS =====
@login_required
def diet_list(request):
    diets = Diet.objects.all().order_by("name")
    return render(request, "diets/diets.html", {"diets": diets})


@login_required
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
def diet_delete(request, pk):
    diet = get_object_or_404(Diet, pk=pk)

    if request.method == "POST":
        diet.delete()
        return redirect("diet_list")

    return render(request, "common/confirm_delete.html", {
        "object_type": "Diet",
        "object_name": diet.name,
        "warning": "Deleting this diet will remove diet compatibility info from ingredients.",
        "cancel_url": reverse("diet_list"),
    })


# ===== INGREDIENT VIEWS =====
@login_required
def ingredient_list(request):
    ingredients = Ingredient.objects.prefetch_related("diets", "allergens").order_by("name")
    return render(request, "ingredients/ingredients.html", {"ingredients": ingredients})


@login_required
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
def ingredient_delete(request, pk):
    ingredient = get_object_or_404(Ingredient, pk=pk)

    if request.method == "POST":
        ingredient.delete()
        return redirect("ingredient_list")

    return render(request, "common/confirm_delete.html", {
        "object_type": "Ingredient",
        "object_name": ingredient.name,
        "warning": "This may affect recipes and pantry items that use this ingredient.",
        "cancel_url":  reverse("ingredient_list"),
    })


# ===== RECIPE VIEWS =====
@login_required
def recipe_list(request):
    qs = Recipe.objects.prefetch_related("recipe_ingredients__ingredient").order_by("name")

    # optional: ignore recipes with 0 ingredients
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

    return render(request, "recipes/recipes.html", {
        "recipes": qs,
        "diets": diets,
        "allergens": allergens,
        "selected_diet_id": diet_id,
        "selected_allergen_id": allergen_id,
        "q": q or "",
    })


@login_required
def recipe_detail(request, pk):
    recipe = get_object_or_404(
        Recipe.objects.prefetch_related("recipe_ingredients__ingredient"),
        pk=pk
    )
    relations = recipe.recipe_ingredients.all()
    return render(request, "recipes/recipe_detail.html", {"recipe": recipe, "relations": relations})


@login_required
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
@login_required
def recipe_edit(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)

    recipe_form = RecipeForm(request.POST or None, request.FILES or None, instance=recipe)
    ingredient_form = RecipeIngredientRelationForm(request.POST or None)

    # Save recipe fields
    if request.method == "POST" and "save_recipe" in request.POST:
        if recipe_form.is_valid():
            recipe_form.save()
            return redirect("recipe_edit", pk=pk)

    # Add ingredient
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
def recipe_edit_ingredients(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)

    if request.method == "POST":
        form = RecipeIngredientRelationForm(request.POST)
        if form.is_valid():
            rel = form.save(commit=False)
            rel.recipe = recipe
            rel.save()
            return redirect("recipe_edit_ingredients", pk=pk)
    else:
        form = RecipeIngredientRelationForm()

    relations = recipe.recipe_ingredients.select_related('ingredient').all()

    return render(request, "recipes/recipe_edit_ingredients.html", {
        "recipe": recipe,
        "form": form,
        "relations": relations
    })


@login_required
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
def recipe_delete(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)
    if request.method == "POST":
        recipe.delete()
    return redirect("recipe_list")


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

    if request.method == 'POST':
        recipe_id = request.POST.get('recipe_id')
        recipe = get_object_or_404(Recipe, id=recipe_id)

        if 'add' in request.POST:
            wishlist.recipes.add(recipe)
        elif 'remove' in request.POST:
            wishlist.recipes.remove(recipe)

        return redirect('wishlist')

    wishlist_recipes = wishlist.recipes.all()
    all_recipes = Recipe.objects.all()

    return render(request, 'wishlist/wishlist.html', {
        'wishlist': wishlist,
        'wishlist_recipes': wishlist_recipes,
        'all_recipes': all_recipes,
    })


# ===== DAILY PLAN VIEWS =====
@login_required
def daily_plans_list(request):
    plans = DailyPlan.objects.filter(user=request.user).order_by('-date')
    return render(request, 'daily_plan/daily_plans.html', {'plans': plans})


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
            form.save_m2m()
            return redirect('daily_plan_detail', plan_id=plan.id)
    else:
        form = DailyPlanForm()

    return render(request, 'daily_plan/daily_plan_form.html', {'form': form})


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