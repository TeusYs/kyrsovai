# admissions/auto_export.py
import threading
import time
from django.core.management import call_command
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Флаг для отслеживания запуска
_auto_export_started = False

def start_auto_export():
    global _auto_export_started
    
    if _auto_export_started:
        return
        
    _auto_export_started = True
    
    def export_worker():
        # Первый запуск через 30 секунд
        time.sleep(30)
        
        while True:
            # Запускаем обе команды
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