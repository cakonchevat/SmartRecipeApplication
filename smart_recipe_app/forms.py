from django import forms
from .models import PantryItem, DailyPlan, Ingredient


class PantryItemForm(forms.ModelForm):
    class Meta:
        model = PantryItem
        fields = ['ingredient', 'quantity', 'base_unit']

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

