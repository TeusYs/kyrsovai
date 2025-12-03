from django.apps import AppConfig
import os

class AdmissionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'admissions'
    
    def ready(self):
        # Запускаем только в основном процессе
        if os.environ.get('RUN_MAIN') == 'true':
            from .auto_export import start_auto_export, start_auto_import
            start_auto_export()
            start_auto_import()