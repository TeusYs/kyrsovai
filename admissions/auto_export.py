# admissions/auto_export.py
import threading
import time
from django.core.management import call_command
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Флаги для отслеживания запуска
_auto_export_started = False
_auto_import_started = False

def start_auto_export():
    global _auto_export_started
    
    if _auto_export_started:
        return
        
    _auto_export_started = True
    
    def export_worker():
        # Первый запуск через 30 секунд
        time.sleep(30)
        
        while True:
            # Запускаем обе команды экспорта
            for command_name in ['export_fisgia_applications', 'export_fisgia_verifications']:
                try:
                    print(f"{datetime.now()} - Автозапуск {command_name}...")
                    call_command(command_name)
                except Exception as e:
                    logger.error(f"Ошибка {command_name}: {e}")
                    print(f"❌ Ошибка {command_name}: {e}")
            
            # Ожидание 5 минут
            time.sleep(300)
    
    thread = threading.Thread(target=export_worker, daemon=True)
    thread.start()
    print("✅ Автоэкспорт ФИСГИА запущен (каждые 5 минут)")

def start_auto_import():
    """Запускает автоматический импорт файлов из fisgia_responses"""
    global _auto_import_started
    
    if _auto_import_started:
        return
        
    _auto_import_started = True
    
    def import_worker():
        # Первый запуск через 60 секунд (после экспорта)
        time.sleep(60)
        
        while True:
            try:
                print(f"{datetime.now()} - Автоимпорт из fisgia_responses...")
                call_command('import_fisgia_verifications')
            except Exception as e:
                logger.error(f"Ошибка импорта: {e}")
                print(f"❌ Ошибка импорта: {e}")
            
            # Ожидание 5 минут
            time.sleep(300)
    
    thread = threading.Thread(target=import_worker, daemon=True)
    thread.start()
    print("✅ Автоимпорт ФИСГИА запущен (каждые 5 минут)")