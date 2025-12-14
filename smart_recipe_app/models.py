from django.db import models
from datetime import date
from django.db.models import Q
from django.conf import settings

# TODO: Teona's tasks: Recipe, Ingredient, Diet

class Diet(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    UNIT_CHOICES = [
        ('g', 'grams (g)'),
        ('kg', 'kilograms (kg)'),
        ('ml', 'milliliters (ml)'),
        ('l', 'liters (l)'),
        ('piece', 'piece'),
        ('tsp', 'teaspoon'),
        ('tbsp', 'tablespoon'),
        ('cup', 'cup'),
    ]
    name = models.CharField(max_length=100, unique=True)
    allergens = models.CharField(max_length=255, blank=True)
    base_unit = models.CharField(max_length=20, choices=UNIT_CHOICES,
                                 help_text="Mass units like kilograms (kg), grams (g), liters (l) and etc.")
    base_amount = models.FloatField(
        help_text="Amount of base_unit used for calorie calculation (e.g. 100 g, 100 ml, 1 piece)"
    )
    calories_per_base_amount = models.FloatField(
        help_text="Calories for the base amount (e.g. kcal per 100 g)"
    )

    # the api to use the relationship in queries
    diets = models.ManyToManyField(
        Diet,
        through='IngredientDietRelation',
        related_name='ingredients'  # sets the reverse relationship from diet -> ingredient (diet.ingredients.all())
    )

    def calories_per_one_unit(self):
         # Example: if calories_per_base_amount = 78kcal for base_amount 100 and base_unit grams, the calories per one unit would be the value 78,
         # divided by the base amount 100, to get 0.78 kcal per gram
        return self.calories_per_base_amount / self.base_amount

    def __str__(self):
        return self.name


class IngredientDietRelation(models.Model):
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    diet = models.ForeignKey(Diet, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('ingredient', 'diet')


class Recipe(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    servings = models.PositiveIntegerField(default=1)
    preparation_time = models.PositiveIntegerField(help_text="Minutes")
    image = models.ImageField(
        upload_to='recipes/',
        blank=True,
        null=True
    )

    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredientRelation',
        related_name='recipes'
    )

    def __str__(self):
        return self.name

    # calculates total calories by accumulating the calories per Ingredient for that Recipe
    @property
    def total_calories(self):
        return sum(ingredient_per_recipe.calories for ingredient_per_recipe in self.made_of.all())

    @property
    def calories_per_serving(self):
        # Example: if the recipe has servings defined (like 4 servings / plates), divide the calories per servings (per person)
        if self.servings:
            return self.total_calories / self.servings
        return None

    # Set of recipes for a particular diet, based on their ingredients
    @classmethod
    def recipes_for_diet(cls, diet_id):
        query_set = cls.objects.all()
        query_set = query_set.exclude(made_of__isnull=True)  # remove recipes with 0 ingredients
        query_set = query_set.exclude(~Q(made_of__ingredient__diets__id=diet_id))  # exclude recipes that contain at least one ingredient that does NOT match the diet

        return query_set.distinct()


class RecipeIngredientRelation(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='made_of')
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    quantity = models.FloatField()  # how many of the base_units (like 4 bananas)

    class Meta:
        unique_together = ('recipe', 'ingredient')

    @property
    def calories(self):
        # Example: banana has 78kcal per 100 grams -> that is its calories_per_one_unit, if we want to add 4 bananas to the recipe we calculate the quantity * calories_per_one_unit
        return self.quantity * self.ingredient.calories_per_one_unit()


class Wishlist(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wishlist')
    recipes = models.ManyToManyField(Recipe, related_name='wishlists', blank=True)

    def __str__(self):
        return f"{self.user.username}'s wishlist"


class Pantry(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='pantry')

    def __str__(self):
        return f"{self.user.username}'s pantry"


class PantryItemRelation(models.Model):
    class Source(models.TextChoices):
        MANUAL = 'manual', 'Manual'
        ML_SCAN = 'ml_scan', 'ML scan'

    pantry = models.ForeignKey(Pantry, on_delete=models.CASCADE, related_name='items')
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    quantity = models.FloatField()
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.MANUAL)

    class Meta:
        # a pantry has one stock entry per ingredient (you can't have rows like banana with quantity 3, and banana with quantity 4)
        unique_together = ('pantry', 'ingredient')

    def __str__(self):
        # display the unit from the Ingredient
        return f"{self.quantity} {self.ingredient.base_unit} {self.ingredient.name}"


class DailyPlan(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='daily_plans')
    date = models.DateField(default=date.today)
    wanted_calories = models.PositiveIntegerField()
    recipes = models.ManyToManyField(Recipe, related_name='daily_plans', blank=True)

    class Meta:
        # only 1 plan for the same date (day)
        unique_together = ('user', 'date')

    def __str__(self):
        return f"{self.user.username} - {self.date}"

    @property
    def total_calories(self):
        return sum(r.total_calories for r in self.recipes.all())

    @property
    def remaining_calories(self):
        return self.wanted_calories - self.total_calories
