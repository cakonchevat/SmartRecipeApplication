from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from jsonschema import ValidationError

from .models import *
from django import forms

User = get_user_model()

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
        fields = ['name', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class IngredientForm(forms.ModelForm):
    diets = forms.ModelMultipleChoiceField(
        queryset=Diet.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple()
    )

    class Meta:
        model = Ingredient
        fields = ['name', 'base_unit', 'base_amount', 'calories_per_base_amount', 'allergens', 'diets']
        widgets = {
            'allergens': forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # preselect diets when editing
        if self.instance and self.instance.pk:
            self.fields['diets'].initial = self.instance.diets.all()

    def save(self, commit=True):
        ingredient = super().save(commit=commit)

        if ingredient.pk:
            ingredient.diets.clear()
            ingredient.diets.add(*self.cleaned_data.get('diets', []))

        return ingredient

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

    def clean_quantity(self):
        q = self.cleaned_data['quantity']
        if q <= 0:
            raise forms.ValidationError("Quantity must be greater than 0.")
        return q

class PantryItemForm(forms.ModelForm):
    class Meta:
        model = PantryItemRelation
        fields = ['ingredient', 'quantity', 'purchased_at', 'expires_at', 'is_opened',]
        widgets = {
            'ingredient': IngredientSelectWithUnit(attrs={'class': 'ingredient-select'}),
            'purchased_at': forms.DateInput(attrs={'type': 'date'}),
            'expires_at': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_quantity(self):
        q = self.cleaned_data['quantity']
        if q <= 0:
            raise forms.ValidationError("Quantity must be greater than 0.")
        return q

class DailyPlanForm(forms.ModelForm):
    class Meta:
        model = DailyPlan
        fields = ['date', 'wanted_calories']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

# ML model
class PantryScanForm(forms.ModelForm):
    class Meta:
        model = PantryScan
        fields = ['image']

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            # Validate file size (5MB limit)
            if image.size > 5 * 1024 * 1024:
                raise ValidationError("Image file too large (max 5MB)")

            # Validate file type
            if not image.content_type.startswith('image/'):
                raise ValidationError("File must be an image")

        return image

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=120, required=True)
    last_name = forms.CharField(max_length=120, required=True)

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Email already in use.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]

        if commit:
            user.save()
        return user