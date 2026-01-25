from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from datetime import date
from django.db.models import Count, F, Q
from django.conf import settings

# TODO: Teona's tasks: Recipe, Ingredient, Diet

class Diet(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, help_text="Brief explanation of this diet (e.g., what foods are allowed/excluded)")

    def __str__(self):
        return self.name

class Allergen(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class Ingredient(models.Model):
    UNIT_CHOICES = [
        ('g', 'grams (g)'),
        ('ml', 'milliliters (ml)'),
        ('pcs', 'pieces'),
        ('tsp', 'teaspoon'),
        ('tbsp', 'tablespoon'),
        ('cup', 'cup'),
    ]
    name = models.CharField(max_length=100, unique=True)
    base_unit = models.CharField(max_length=20, choices=UNIT_CHOICES,
                                 help_text="Mass units like kilograms (kg), grams (g), liters (l) and etc.")
    base_amount = models.FloatField(validators=[MinValueValidator(0.000001)], help_text="Amount of base_unit used for calorie calculation (e.g. 100 g, 100 ml, 1 piece)")
    calories_per_base_amount = models.FloatField(validators=[MinValueValidator(0)], help_text="Calories for the base amount (e.g. kcal per 100 g)")

    allergens = models.ManyToManyField(Allergen, blank=True, related_name='ingredients')  # allergen.ingredients.all()
    diets = models.ManyToManyField(Diet, through='IngredientDietRelation', related_name='ingredients')  # diet.ingredients.all()


    @property
    def calories_per_one_unit(self):
         # Example: if calories_per_base_amount = 78kcal for base_amount 100 and base_unit grams, the calories per one unit would be the value 78,
         # divided by the base amount 100, to get 0.78 kcal per gram
        return self.calories_per_base_amount / self.base_amount

    def __str__(self):
        return self.name


class IngredientDietRelation(models.Model):
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name='ingredient_diets')  # ingredients.ingredient_diets.all()
    diet = models.ForeignKey(Diet, on_delete=models.CASCADE, related_name='diet_ingredients')  # diets.diet_ingredients.all()

    class Meta:
        unique_together = ('ingredient', 'diet')


class Recipe(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    no_of_servings = models.PositiveIntegerField(default=1)
    preparation_time = models.PositiveIntegerField(help_text="Minutes")
    image = models.ImageField(upload_to='recipes/', blank=True, null=True)

    ingredients = models.ManyToManyField(Ingredient, through='RecipeIngredientRelation', related_name='recipes')  # ingredient.recipes.all()

    def __str__(self):
        return self.name

    # calculates total calories by accumulating the calories per Ingredient for that Recipe
    @property
    def total_calories(self):
        return sum(ingredient_per_recipe.calories for ingredient_per_recipe in self.recipe_ingredients.all())

    @property
    def calories_per_serving(self):
        # Example: if the recipes has servings defined (like 4 servings / plates), divide the calories per servings (per person)
        if self.no_of_servings:
            return self.total_calories / self.no_of_servings
        return None

    # Set of recipes for a particular diets, based on their ingredients
    @classmethod
    def recipes_for_diet(cls, diet_id):
        qs = cls.objects.exclude(recipe_ingredients__isnull=True)
        qs = qs.annotate(
            ing_count=Count('recipe_ingredients', distinct=True),
            ing_in_diet=Count(
                'recipe_ingredients',
                filter=Q(recipe_ingredients__ingredient__diets__id=diet_id),
                distinct=True
            )
        ).filter(ing_count=F('ing_in_diet'))
        return qs

    # Set of recipes excluding a given allergen (recipes that do not contain ingredients with a given allergen)
    @classmethod
    def recipes_excluding_allergen(cls, allergen_id):
        qs = cls.objects.all()
        qs = qs.exclude(recipe_ingredients__isnull=True)  # optional: hide empty recipes
        qs = qs.exclude(recipe_ingredients__ingredient__allergens__id=allergen_id)
        return qs.distinct()


class RecipeIngredientRelation(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='recipe_ingredients')  # recipe.recipe_ingredients.all()
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name='ingredient_recipes')  # ingredients.ingredient_recipes.all()
    quantity = models.FloatField(validators=[MinValueValidator(0.000001)], help_text="Amount in ingredient.base_unit (e.g., 200 g, 2 piece)")    # how many of the base_units (like 4 bananas)

    class Meta:
        unique_together = ('recipe', 'ingredient')

    @property
    def calories(self):
        # Example: banana has 78kcal per 100 grams -> that is its calories_per_one_unit, if we want to add 4 bananas to the recipes we calculate the quantity * calories_per_one_unit
        return self.quantity * self.ingredient.calories_per_one_unit


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
    quantity = models.FloatField(validators=[MinValueValidator(0.000001)], help_text="Amount in ingredient.base_unit (e.g., 200 g, 2 piece)")
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.MANUAL)

    purchased_at = models.DateField(null=True, blank=True)
    expires_at = models.DateField(null=True, blank=True)
    is_opened = models.BooleanField(default=False)

    class Meta:
        # a pantry has one stock entry per ingredients (you can't have rows like banana with quantity 3, and banana with quantity 4)
        constraints = [models.UniqueConstraint(fields=['pantry', 'ingredient'], name='uniq_pantry_ingredient')]

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
        return sum((r.calories_per_serving or 0) for r in self.recipes.all())

    @property
    def remaining_calories(self):
        return self.wanted_calories - self.total_calories

# ML model
class PantryScan(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    image = models.ImageField(upload_to="pantry_scans/%Y/%m/%d/")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, default="")
    raw_output = models.JSONField(null=True, blank=True)
    ingredients_added_count = models.IntegerField(default=0)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Scan {self.id} - {self.user.username} - {self.status}"


class PantryScanDetection(models.Model):
    class ReviewStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"

    scan = models.ForeignKey(PantryScan, on_delete=models.CASCADE, related_name="detections")
    label = models.CharField(max_length=120)
    confidence = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])

    quantity_guess = models.FloatField(null=True, blank=True)

    matched_ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Ingredient you matched this detection to"
    )

    status = models.CharField(
        max_length=20,
        choices=ReviewStatus.choices,
        default=ReviewStatus.PENDING
    )

    class Meta:
        ordering = ["-confidence"]

    def __str__(self):
        return f"{self.label} ({self.confidence:.2f}) - {self.status}"

