from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Pantry, Wishlist

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_pantry_and_wishlist(sender, instance, created, **kwargs):
    if created:
        Pantry.objects.create(user=instance)
        Wishlist.objects.create(user=instance)
