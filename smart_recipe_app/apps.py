from django.apps import AppConfig


class SmartRecipeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'smart_recipe_app'

    def ready(self):
        import smart_recipe_app.signals