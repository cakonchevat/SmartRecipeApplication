from django.contrib import admin
from django.db.models import Count

from smart_recipe_app.models import Diet, Ingredient, IngredientDietRelation, Recipe, RecipeIngredientRelation, PantryItemRelation, Pantry, Wishlist
# Register your models here.

# Diet
@admin.register(Diet)
class DietAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

# Ingredient
class IngredientDietInline(admin.TabularInline):
    model = IngredientDietRelation
    extra = 1

@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'base_unit', 'base_amount', 'calories_per_base_amount', 'allergens', 'diets_list',)
    search_fields = ('name',)
    inlines = [IngredientDietInline]

    def diets_list(self, obj):  # what diets the ingredient belongs in
        return ", ".join(d.name for d in obj.diets.all())

    diets_list.short_description = "Diets"

@admin.register(IngredientDietRelation)
class IngredientDietRelationAdmin(admin.ModelAdmin):
    list_display = ("ingredient", "diet")
    search_fields = ("ingredient__name", "diet__name")
    list_filter = ("diet",)


# Recipe
class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredientRelation
    extra = 1

@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ("name", "servings", "preparation_time", "total_calories", "calories_per_serving", 'ingredient_count')
    search_fields = ("name",)
    inlines = [RecipeIngredientInline]

    def get_queryset(self, request):  # injecting ingredient count column to each recipe (so that we can later filter recipes by number of ingredients) ** additional performance
        qs = super().get_queryset(request)
        return qs.annotate(ingredient_count_db=Count("made_of"))

    def ingredient_count(self, obj):  # reads the value, exposes it in a column
        return obj.ingredient_count_db

    ingredient_count.short_description = "Ingredients"
    ingredient_count.admin_order_field = "ingredient_count_db"  # allows sorting recipes by number of ingredients

# ----- PANTRY -----
class PantryItemInline(admin.TabularInline):
    model = PantryItemRelation
    extra = 1

@admin.register(Pantry)
class PantryAdmin(admin.ModelAdmin):
    list_display = ('user',)
    inlines = [PantryItemInline]


@admin.register(PantryItemRelation)
class PantryItemAdmin(admin.ModelAdmin):
    list_display = ('pantry', 'ingredient', 'quantity', 'source')

# ----- WISHLIST -----
@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('user',)
    filter_horizontal = ('recipes',)