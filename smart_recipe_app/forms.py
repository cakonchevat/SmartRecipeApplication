from django import forms
from .models import PantryItem, DailyPlan


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