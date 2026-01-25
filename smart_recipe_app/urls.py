from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # User
    path('', views.index, name='index'),
    path('register/', views.register, name='register'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # Allergens
    path("allergens/", views.allergen_list, name="allergen_list"),
    path("allergens/create/", views.allergen_create, name="allergen_create"),
    path("allergens/<int:pk>/edit/", views.allergen_edit, name="allergen_edit"),
    path("allergens/<int:pk>/delete/", views.allergen_delete, name="allergen_delete"),

    # Diets
    path("diets/", views.diet_list, name="diet_list"),
    path("diets/create/", views.diet_create, name="diet_create"),
    path("diets/<int:pk>/edit/", views.diet_edit, name="diet_edit"),
    path("diets/<int:pk>/delete/", views.diet_delete, name="diet_delete"),

    # Ingredients
    path("ingredients/", views.ingredient_list, name="ingredient_list"),
    path("ingredients/create/", views.ingredient_create, name="ingredient_create"),
    path("ingredients/<int:pk>/edit/", views.ingredient_edit, name="ingredient_edit"),
    path("ingredients/<int:pk>/delete/", views.ingredient_delete, name="ingredient_delete"),

    # Recipes
    path("recipes/", views.recipe_list, name="recipe_list"),
    path("recipes/create/", views.recipe_create, name="recipe_create"),
    path("recipes/<int:pk>/", views.recipe_detail, name="recipe_detail"),

    path("recipes/<int:pk>/edit/", views.recipe_edit, name="recipe_edit"),
    path("recipes/<int:pk>/edit-ingredients/", views.recipe_edit_ingredients, name="recipe_edit_ingredients"),
    path("recipes/<int:pk>/remove-ingredient/<int:relation_id>/", views.recipe_remove_ingredient, name="recipe_remove_ingredient"),
    path("recipes/<int:pk>/delete/", views.recipe_delete, name="recipe_delete"),

    path("recipes/<int:pk>/wishlist-toggle/", views.toggle_wishlist, name="toggle_wishlist"),
    path("recipes/<int:pk>/add-to-today/", views.add_recipe_to_today_plan, name="add_recipe_to_today_plan"),

    # Pantry
    path('pantry/', views.pantry_list, name='pantry'),
    path('pantry/add/', views.pantry_add_item, name='pantry_add_item'),
    path('pantry/<int:item_id>/edit/', views.pantry_edit_item, name='pantry_edit_item'),
    path('pantry/<int:item_id>/delete/', views.pantry_delete_item, name='pantry_delete_item'),

    # Wishlist
    path('wishlist/', views.wishlist_view, name='wishlist'),

    # Daily plans
    path('plans/', views.daily_plans_list, name='daily_plans'),
    path('plans/new/', views.daily_plan_create, name='daily_plan_create'),
    path('plans/<int:plan_id>/', views.daily_plan_detail, name='daily_plan_detail'),

    # Urls for service-implemented views
    path('plans/suggest/', views.suggest_daily_plan, name='suggest_daily_plan'),
    path('recipes/cookable/', views.cookable_recipes, name='cookable_recipes'),

    # Pantry scan URLs
    path("pantry/scan/", views.pantry_scan_create, name="pantry_scan"),
    path("pantry/scan/<int:scan_id>/processing/", views.pantry_scan_processing, name="pantry_scan_processing"),
    path("pantry/scan/<int:scan_id>/review/", views.pantry_scan_review, name="pantry_scan_review"),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)