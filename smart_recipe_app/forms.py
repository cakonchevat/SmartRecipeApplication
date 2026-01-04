from django import forms
from .models import *
from django import forms

class IngredientSelectWithUnit(forms.Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)

        if value and hasattr(value, "instance"):
            option["attrs"]["data-unit"] = value.instance.base_unit

        return option


class AllergenForm(forms.ModelForm):
    class Meta:
        model = Allergen
        fields = ['name']

class DietForm(forms.ModelForm):
    class Meta:
        model = Diet
        fields = ['name']

class IngredientForm(forms.ModelForm):
    class Meta:
        model = Ingredient
        fields = ['name', 'base_unit', 'base_amount', 'calories_per_base_amount', 'allergens', 'diets']
        widgets = {
            'allergens': forms.CheckboxSelectMultiple(),
            'diets': forms.CheckboxSelectMultiple(),
        }

class RecipeForm(forms.ModelForm):
    class Meta:
        model = Recipe
        fields = ['name', 'description', 'no_of_servings', 'preparation_time', 'image']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

class RecipeIngredientRelationForm(forms.ModelForm):
    class Meta:
        model = RecipeIngredientRelation
        fields = ["ingredient", "quantity"]
        widgets = {
            'ingredient': IngredientSelectWithUnit(attrs={'class': 'ingredient-select'}),
        }

class PantryItemForm(forms.ModelForm):
    class Meta:
        model = PantryItemRelation
        fields = ['ingredient', 'quantity', 'purchased_at', 'expires_at', 'is_opened',]
        widgets = {
            'ingredient': IngredientSelectWithUnit(attrs={'class': 'ingredient-select'}),
            'purchased_at': forms.DateInput(attrs={'type': 'date'}),
            'expires_at': forms.DateInput(attrs={'type': 'date'}),
        }

class DailyPlanForm(forms.ModelForm):
    class Meta:
        model = DailyPlan
        fields = ['date', 'wanted_calories', 'recipes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'recipes': forms.CheckboxSelectMultiple(),
        }