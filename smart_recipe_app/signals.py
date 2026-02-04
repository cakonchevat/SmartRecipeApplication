from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Pantry, Wishlist
from django.contrib.auth.models import Group

User = get_user_model()

@receiver(post_save, sender=User)
def create_user_pantry_and_wishlist(sender, instance, created, **kwargs):
    if created:
        Pantry.objects.create(user=instance)
        Wishlist.objects.create(user=instance)

@receiver(post_save, sender=User)
def on_user_created(sender, instance, created, **kwargs):
    if not created:
        return

    User.objects.get_or_create(user=instance)

    user_group = Group.objects.get(name="User")
    instance.groups.add(user_group)
