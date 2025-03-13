from django.apps import AppConfig
from django.db.models.signals import post_migrate

class ContentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'contents'
    
    def ready(self):
        import contents.signals