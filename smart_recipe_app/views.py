from django.contrib.auth.decorators import login_required

# Create your views here.

from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, redirect, get_object_or_404

from smart_recipe_app.forms import PantryItemForm,DailyPlanForm
from smart_recipe_app.models import Pantry, PantryItem, Wishlist, Recipe, DailyPlan


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
        'form': None,
        'mode': None,
        'editing_item': None,
    })


@login_required
def pantry_add_item(request):
    pantry = _get_user_pantry(request.user)
    items = pantry.items.select_related('ingredient').all()

    if request.method == 'POST':
        form = PantryItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.pantry = pantry
            item.source = PantryItem.Source.MANUAL
            item.save()
            return redirect('pantry_list')
    else:
        form = PantryItemForm()

    # ја користиме истата страница, но со "modal" за додавање
    return render(request, 'pantry/pantry.html', {
        'pantry': pantry,
        'items': items,
        'form': form,
        'mode': 'add',
        'editing_item': None,
    })


@login_required
def pantry_edit_item(request, item_id):
    pantry = _get_user_pantry(request.user)
    item = get_object_or_404(PantryItem, id=item_id, pantry=pantry)
    items = pantry.items.select_related('ingredient').all()

    if request.method == 'POST':
        form = PantryItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            return redirect('pantry_list')
    else:
        form = PantryItemForm(instance=item)

    return render(request, 'pantry/pantry.html', {
        'pantry': pantry,
        'items': items,
        'form': form,
        'mode': 'edit',
        'editing_item': item,
    })


@login_required
def pantry_delete_item(request, item_id):
    pantry = _get_user_pantry(request.user)
    item = get_object_or_404(PantryItem, id=item_id, pantry=pantry)

    if request.method == 'POST':
        item.delete()
        return redirect('pantry_list')

    # simple confirm страница
    return render(request, 'pantry/pantry_confirm_delete.html', {'item': item})

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


