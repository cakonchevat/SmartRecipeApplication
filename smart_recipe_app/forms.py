from django import forms
from .models import *

# Forms check whether the input is valid

class DietForm(forms.ModelForm):
    class Meta:
        model = Diet
        fields = ['name']

class IngredientForm(forms.ModelForm):
    class Meta:
        model = Ingredient
        fields = ['name', 'base_unit', 'base_amount', 'calories_per_base_amount', 'allergens']

class RecipeForm(forms.ModelForm):
    class Meta:
        model = Recipe
        fields = ['name', 'description', 'no_of_servings', 'preparation_time', 'image']

class RecipeIngredientRelationForm(forms.ModelForm):
    class Meta:
        model = RecipeIngredientRelation
        fields = ["ingredient", "quantity"]

class AddRecipeWithIngredientForm(forms.Form):
    recipe_name = forms.CharField(max_length=200)
    recipe_description = forms.CharField(required=False, widget=forms.Textarea)
    no_of_servings = forms.IntegerField(min_value=1, initial=1)
    preparation_time = forms.IntegerField(min_value=0)

    # choose an existing ingredient
    ingredient = forms.ModelChoiceField(queryset=Ingredient.objects.all())
    quantity = forms.FloatField(min_value=0.0)

class PantryItemForm(forms.ModelForm):
    class Meta:
        model = PantryItemRelation
        fields = ['ingredient', 'quantity']

class DailyPlanForm(forms.ModelForm):
    class Meta:
        model = DailyPlan
        fields = ['date', 'wanted_calories', 'recipes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'recipes': forms.CheckboxSelectMultiple,
        }

class AddPantryWithIngredientForm(forms.Form):
    ingredient_name = forms.CharField(max_length=100)
    ingredient_base_unit = forms.ChoiceField(choices=Ingredient.UNIT_CHOICES)
    ingredient_base_amount = forms.FloatField()
    ingredient_calories_per_base_amount = forms.FloatField()

    quantity = forms.FloatField()

