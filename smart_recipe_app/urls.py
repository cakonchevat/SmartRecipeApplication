from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('register/', views.register, name='register'),
    path('logout/', views.register, name='logout'),

    # Pantry
    path('pantry/', views.pantry_list, name='pantry_list'),
    path('pantry/add/', views.pantry_add_item, name='pantry_add_item'),
    path('pantry/<item_id>/edit/', views.pantry_edit_item, name='pantry_edit_item'),
    path('pantry/<item_id>/delete/', views.pantry_delete_item, name='pantry_delete_item'),

    # Wishlist
    path('wishlist/', views.wishlist_view, name='wishlist'),

    # Daily plans
    path('plans/', views.daily_plans_list, name='daily_plans'),
    path('plans/new/', views.daily_plan_create, name='daily_plan_create'),
    path('plans/<plan_id>/', views.daily_plan_detail, name='daily_plan_detail'),

]
