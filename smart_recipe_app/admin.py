from django.contrib import admin

from smart_recipe_app.models import PantryItem, Pantry, Wishlist, Recipe, Ingredient, RecipeIngredient


# Register your models here.

# ----- INGREDIENT -----
@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'base_unit', 'base_amount', 'calories_per_base_amount', 'allergens')
    search_fields = ('name',)


# ----- RECIPE -----
class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1

@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'servings', 'preparation_time')
    search_fields = ('name',)
    inlines = [RecipeIngredientInline]

# ----- PANTRY -----
class PantryItemInline(admin.TabularInline):
    model = PantryItem
    extra = 1

@admin.register(Pantry)
class PantryAdmin(admin.ModelAdmin):
    list_display = ('user',)
    inlines = [PantryItemInline]


@admin.register(PantryItem)
class PantryItemAdmin(admin.ModelAdmin):
    list_display = ('pantry', 'ingredient', 'quantity', 'base_unit', 'source')

# ----- WISHLIST -----
@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('user',)
    filter_horizontal = ('recipes',)