from django.contrib import admin
from django.db.models import Count
from smart_recipe_app.models import Diet, Allergen, Ingredient, IngredientDietRelation, Recipe, RecipeIngredientRelation, PantryItemRelation, Pantry, Wishlist
# Register your models here.

# Diet
@admin.register(Diet)
class DietAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

# IngredientAllergens
@admin.register(Allergen)
class AllergenAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'base_unit', 'base_amount', 'calories_per_base_amount', 'diets_list', 'allergens_list')
    search_fields = ('name',)
    list_filter = ('base_unit', 'diets', 'allergens')
    filter_horizontal = ('allergens',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related('diets', 'allergens')

    def diets_list(self, obj):
        return ", ".join(d.name for d in obj.diets.all())

    def allergens_list(self, obj):
        return ", ".join(a.name for a in obj.allergens.all())

    diets_list.short_description = "Diets"
    allergens_list.short_description = "Allergens"

@admin.register(IngredientDietRelation)
class IngredientDietRelationAdmin(admin.ModelAdmin):
    list_display = ("ingredient", "diet")
    search_fields = ("ingredient__name", "diet__name")
    list_filter = ("diet",)

# Recipe
class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredientRelation
    extra = 1
    readonly_fields = ('calories',)  # Show calculated calories
    fields = ('ingredient', 'quantity', 'calories')  # Explicit field order

@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ("name", "no_of_servings", "preparation_time", "total_calories", "calories_per_serving",
                    'ingredient_count')
    search_fields = ("name", "description")  # Add description search
    list_filter = ("no_of_servings",)  # Add filter
    inlines = [RecipeIngredientInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related("recipe_ingredients__ingredient").annotate(
            ingredient_count_db=Count("recipe_ingredients", distinct=True))

    def ingredient_count(self, obj):
        return obj.ingredient_count_db

    ingredient_count.short_description = "Ingredients"
    ingredient_count.admin_order_field = "ingredient_count_db"

# ----- PANTRY -----
class PantryItemInline(admin.TabularInline):
    model = PantryItemRelation
    extra = 1
    fields = (
        'ingredient',
        'quantity',
        'is_opened',
        'purchased_at',
        'expires_at',
        'source',
    )

@admin.register(Pantry)
class PantryAdmin(admin.ModelAdmin):
    list_display = ('user',)
    inlines = [PantryItemInline]

@admin.register(PantryItemRelation)
class PantryItemAdmin(admin.ModelAdmin):
    list_display = ('pantry', 'ingredient', 'quantity', 'is_opened', 'purchased_at', 'expires_at', 'source',)
    list_filter = ('is_opened', 'source', 'expires_at',)
    search_fields = ('ingredient__name',)
    date_hierarchy = 'expires_at'

# ----- WISHLIST -----
@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('user',)
    filter_horizontal = ('recipes',)