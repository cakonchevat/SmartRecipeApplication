from django.contrib.auth.decorators import login_required

# Create your views here -> views define WHAT happens, they get the HTTP message, decide what happens and return an answer

from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, redirect, get_object_or_404
from smart_recipe_app.forms import DietForm, IngredientForm, RecipeForm, IngredientDietRelationForm, RecipeIngredientRelationForm, PantryItemForm, DailyPlanForm, AddPantryWithIngredientForm
from smart_recipe_app.models import Ingredient, Diet, IngredientDietRelation, RecipeIngredientRelation, Pantry, PantryItemRelation, Wishlist, Recipe, DailyPlan, Ingredient
from django.forms import inlineformset_factory


IngredientDietFormSet = inlineformset_factory(
    Ingredient,
    Ingredient.diets.through,
    form=IngredientDietRelationForm,
    extra=1,
    can_delete=True
)

RecipeIngredientFormSet = inlineformset_factory(
    Recipe,
    Recipe.ingredients.through,
    form=RecipeIngredientRelationForm,
    extra=1,
    can_delete=True
)

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')  # 'login' доаѓа од django.contrib.registration.urls
    else:
        form = UserCreationForm()

    return render(request, 'registration/register.html', {'form': form})

@login_required
def index(request):
    return render(request, 'index.html')

# Diet views
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


# Ingredient views
@login_required
def ingredient_list(request):
    ingredients = Ingredient.objects.prefetch_related("diets").order_by("name")
    return render(request, "ingredients/ingredients.html", {"ingredients": ingredients})

@login_required
def ingredient_create(request):
    if request.method == "POST":
        form = IngredientForm(request.POST)
        formset = IngredientDietFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            ingredient = form.save()
            formset.instance = ingredient
            formset.save()
            return redirect("ingredient_list")
    else:
        form = IngredientForm()
        formset = IngredientDietFormSet()

    return render(request, "ingredients/ingredient_form.html", {"form": form, "formset": formset})

@login_required
def ingredient_edit(request, pk):
    ingredient = get_object_or_404(Ingredient, pk=pk)

    if request.method == "POST":
        form = IngredientForm(request.POST, instance=ingredient)
        formset = IngredientDietFormSet(request.POST, instance=ingredient)

        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            return redirect("ingredient_list")
    else:
        form = IngredientForm(instance=ingredient)
        formset = IngredientDietFormSet(instance=ingredient)

    return render(request,"ingredients/ingredient_form.html",{"form": form, "formset": formset})

@login_required
def ingredient_delete(request, pk):
    ingredient = get_object_or_404(Ingredient, pk=pk)
    if request.method == "POST":
        ingredient.delete()
    return redirect("ingredient_list")


# Recipe views
@login_required
def recipe_list(request):
    recipes = Recipe.objects.order_by("name")
    return render(request, "recipes/recipes.html", {"recipes": recipes})


@login_required
def recipe_detail(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)
    relations = recipe.made_of.select_related("ingredient").all()
    return render(request, "recipes/recipe_detail.html", {"recipe": recipe, "relations": relations})


@login_required
def recipe_create(request):
    if request.method == "POST":
        form = RecipeForm(request.POST, request.FILES)
        formset = RecipeIngredientFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            recipe = form.save()
            formset.instance = recipe
            formset.save()
            return redirect("recipe_detail", pk=recipe.pk)
    else:
        form = RecipeForm()
        formset = RecipeIngredientFormSet()

    return render(request, "recipes/recipe_form.html", {"form": form, "formset": formset})


@login_required
def recipe_edit(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)

    if request.method == "POST":
        form = RecipeForm(request.POST, request.FILES, instance=recipe)
        formset = RecipeIngredientFormSet(request.POST, instance=recipe)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            return redirect("recipe_detail", pk=recipe.pk)
    else:
        form = RecipeForm(instance=recipe)
        formset = RecipeIngredientFormSet(instance=recipe)

    return render(request, "recipes/recipe_form.html", {"form": form, "formset": formset})


@login_required
def recipe_delete(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)
    if request.method == "POST":
        recipe.delete()
        return redirect("recipe_list")
    return render(request, "recipes/recipe_confirm_delete.html", {"recipe": recipe})


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
        'Ingredient': Ingredient,  # ← за UNIT_CHOICES во template
    })


# POST:
@login_required
def pantry_add_item(request):
    pantry = _get_user_pantry(request.user)

    if request.method == "POST":
        form = AddPantryWithIngredientForm(request.POST)
        if form.is_valid():

            # 1. CREATE INGREDIENT
            ingredient = Ingredient.objects.create(
                name=form.cleaned_data['ingredient_name'],
                base_unit=form.cleaned_data['ingredient_base_unit'],
                base_amount=form.cleaned_data['ingredient_base_amount'],
                calories_per_base_amount=form.cleaned_data['ingredient_calories_per_base_amount'],
            )

            # 2. CREATE PANTRY ITEM
            PantryItemRelation.objects.create(
                pantry=pantry,
                ingredient=ingredient,
                quantity=form.cleaned_data['quantity'],
                source=PantryItemRelation.Source.MANUAL
            )

            return redirect('pantry')

    return redirect('pantry')



# @login_required
# def pantry_edit_item(request, item_id):
#     pantry = _get_user_pantry(request.user)
#     item = get_object_or_404(PantryItem, id=item_id, pantry=pantry)
#
#     if request.method == "POST":
#         item.quantity = request.POST.get("quantity")
#         item.base_unit = request.POST.get("base_unit")
#         item.save()
#
#     return redirect("pantry")


@login_required
def pantry_delete_item(request, item_id):
    pantry = _get_user_pantry(request.user)
    item = get_object_or_404(PantryItemRelation, id=item_id, pantry=pantry)

    if request.method == "POST":
        item.delete()

    return redirect("pantry")


@login_required
def wishlist_view(request):
    # земи или креирај wishlist за тековниот user
    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        recipe_id = request.POST.get('recipe_id')
        recipe = get_object_or_404(Recipe, id=recipe_id)

        if 'add' in request.POST:
            wishlist.recipes.add(recipe)
        elif 'remove' in request.POST:
            wishlist.recipes.remove(recipe)

        return redirect('wishlist')

    # рецепти во wishlist
    wishlist_recipes = wishlist.recipes.all()

    # сите рецепти (за да можеш да додадеш од нив)
    all_recipes = Recipe.objects.all()

    return render(request, 'wishlist/wishlist.html', {
        'wishlist': wishlist,
        'wishlist_recipes': wishlist_recipes,
        'all_recipes': all_recipes,
    })

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
            form.save_m2m()  # за да се снимат recipes во M2M табелата
            return redirect('daily_plan_detail', plan_id=plan.id)
    else:
        form = DailyPlanForm()

    return render(request, 'daily_plan/daily_plan_form.html', {'form': form})


