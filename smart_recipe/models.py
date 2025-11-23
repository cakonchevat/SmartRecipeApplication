from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Diet(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    name = models.CharField(max_length=100)
    allergens = models.CharField(max_length=255, blank=True)
    base_unit = models.CharField(max_length=20)  # 'g', 'ml', 'piece'
    calories_per_unit = models.FloatField()      # kcal per base_unit

    diets = models.ManyToManyField(
        Diet,
        through='IngredientDiet',
        related_name='ingredients'
    )

    def __str__(self):
        return self.name


class IngredientDiet(models.Model):
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
        through='RecipeIngredient',
        related_name='recipes'
    )

    def __str__(self):
        return self.name

    @property
    def total_calories(self):
        return sum(ri.calories for ri in self.recipeingredient_set.all())

    @property
    def calories_per_serving(self):
        if self.servings:
            return self.total_calories / self.servings
        return None


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    quantity = models.FloatField()  # how many base_units

    @property
    def calories(self):
        return self.quantity * self.ingredient.calories_per_unit

class Wishlist(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wishlist')
    recipes = models.ManyToManyField(Recipe, related_name='wishlists', blank=True)

    def __str__(self):
        return f"{self.user.username}'s wishlist"

class Pantry(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='pantry')

    def __str__(self):
        return f"{self.user.username}'s pantry"


class PantryItem(models.Model):
    class Source(models.TextChoices):
        MANUAL = 'manual', 'Manual'
        ML_SCAN = 'ml_scan', 'ML scan'

    pantry = models.ForeignKey(Pantry, on_delete=models.CASCADE, related_name='items')
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    quantity = models.FloatField()
    unit = models.CharField(max_length=20)  # you can enforce same as ingredient.base_unit later
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.MANUAL)

    class Meta:
        unique_together = ('pantry', 'ingredient')

    def __str__(self):
        return f"{self.quantity} {self.unit} {self.ingredient.name}"

from datetime import date


class DailyPlan(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='daily_plans')
    date = models.DateField(default=date.today)
    wanted_calories = models.PositiveIntegerField()
    recipes = models.ManyToManyField(Recipe, related_name='daily_plans', blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.date}"

    @property
    def total_calories(self):
        return sum(r.total_calories for r in self.recipes.all())

    @property
    def remaining_calories(self):
        return self.wanted_calories - self.total_calories

