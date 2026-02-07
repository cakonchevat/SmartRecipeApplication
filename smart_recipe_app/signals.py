from django.conf import settings
from django.db.models.signals import post_save, post_delete, pre_delete
from django.dispatch import receiver
from .models import RecipeIngredientRelation, Pantry, Wishlist
from .services import generate_recipe_image_if_missing

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_pantry_and_wishlist(sender, instance, created, **kwargs):
    if created:
        Pantry.objects.create(user=instance)
        Wishlist.objects.create(user=instance)

@receiver(post_save, sender=RecipeIngredientRelation)
def auto_image_on_add_or_edit(sender, instance, **kwargs):
    generate_recipe_image_if_missing(instance.recipe)


@receiver(pre_delete, sender=RecipeIngredientRelation)
def auto_image_on_remove(sender, instance, **kwargs):
    generate_recipe_image_if_missing(instance.recipe)