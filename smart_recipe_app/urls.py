from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # User
    path('', views.index, name='index'),
    path('register/', views.register, name='register'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # Recipes
    path("recipes/create/", views.recipe_create, name="recipe_create"),
    path("recipes/<int:pk>/edit/", views.recipe_edit, name="recipe_edit"),
    path("recipes/<int:pk>/delete/", views.recipe_delete, name="recipe_delete"),
    path("recipes/<int:pk>/", views.recipe_detail, name="recipe_detail"),
    path("recipes/", views.recipe_list, name="recipe_list"),

    # Ingredients
    path("ingredients/", views.ingredient_list, name="ingredient_list"),
    path("ingredients/create/", views.ingredient_create, name="ingredient_create"),
    path("ingredients/<int:pk>/edit/", views.ingredient_edit, name="ingredient_edit"),
    path("ingredients/<int:pk>/delete/", views.ingredient_delete, name="ingredient_delete"),

    # Diets
    path("diets/", views.diet_list, name="diet_list"),
    path("diets/create/", views.diet_create, name="diet_create"),
    path("diets/<int:pk>/edit/", views.diet_edit, name="diet_edit"),
    path("diets/<int:pk>/delete/", views.diet_delete, name="diet_delete"),

    # Pantry
    path('pantry/', views.pantry_list, name='pantry'),
    path('pantry/add/', views.pantry_add_item, name='pantry_add_item'),
    # path('pantry/<item_id>/edit/', views.pantry_edit_item, name='pantry_edit_item'),
    path('pantry/<int:item_id>/delete/', views.pantry_delete_item, name='pantry_delete_item'),

    # Wishlist
    path('wishlist/', views.wishlist_view, name='wishlist'),

    # Daily plans
    path('plans/', views.daily_plans_list, name='daily_plans'),
    path('plans/new/', views.daily_plan_create, name='daily_plan_create'),
    path('plans/<int:plan_id>/', views.daily_plan_detail, name='daily_plan_detail'),

]
