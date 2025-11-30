from django.db import models
from django.contrib.auth import get_user_model
from datetime import date

User = get_user_model()


# ----- DIET -----
class Diet(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


# ----- INGREDIENT -----
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
    name = models.CharField(max_length=100)
    allergens = models.CharField(max_length=255, blank=True)
    base_unit = models.CharField(max_length=20, choices=UNIT_CHOICES)  # g, kg, ml, l, piece, cup

    base_amount = models.FloatField(
        help_text="Amount of base_unit used for calorie calculation (e.g. 100 g, 100 ml, 1 piece)"
    )
    calories_per_base_amount = models.FloatField(
        help_text="Calories for the base amount (e.g. kcal per 100 g)"
    )

    diets = models.ManyToManyField(
        Diet,
        through='IngredientDiet',
        related_name='ingredients'  # sets the reverse relatioship from diet --> ingredient (diet.ingredients.all())
    )

    def calories_per_one_unit(self):
        """
        Returns kcal per 1 base_unit.
        Example: if calories_per_base_amount=364 per base_amount=100g => 3.64 kcal per 1g
        """
        return self.calories_per_base_amount / self.base_amount

    def __str__(self):
        return self.name


class IngredientDiet(models.Model):
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    diet = models.ForeignKey(Diet, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('ingredient', 'diet')


# ----- RECIPE -----
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

    # calculates total calories by accumulating the calories
    # for each RecipeIngredient connected to the specified recipe
    @property
    def total_calories(self):
        total = 0
        for ri in self.recipeingredient_set.all():
            total += ri.calories
        return total

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
        kcal_per_one_unit = self.ingredient.calories_per_one_unit()
        return self.quantity * kcal_per_one_unit;


# ----- WISHLIST -----
class Wishlist(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wishlist')
    recipes = models.ManyToManyField(Recipe, related_name='wishlists', blank=True)

    def __str__(self):
        return f"{self.user.username}'s wishlist"


# ----- PANTRY -----
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
    base_unit = models.CharField(max_length=20)
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.MANUAL)

    class Meta:
        unique_together = ('pantry', 'ingredient')

    def __str__(self):
        return f"{self.quantity} {self.base_unit} {self.ingredient.name}"


# ----- DAILY PLAN -----
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
