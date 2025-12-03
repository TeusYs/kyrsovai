from django.core.management.base import BaseCommand
from django.utils import timezone
from pathlib import Path
import csv
import shutil
from datetime import datetime

from admissions.models import Applicant, VerificationRequest

class Command(BaseCommand):
    help = "Импорт результата проверки документов из ФИСГИА. Может работать с файлом или сканировать папку fisgia_responses."

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_path",
            type=str,
            nargs='?',
            default=None,
            help="Путь к CSV файлу с результатами (опционально, если не указан - сканирует fisgia_responses/)"
        )

    def handle(self, *args, **options):
        csv_path = options.get("csv_path")
        
        if csv_path:
            # Работа с конкретным файлом
            self.process_file(Path(csv_path))
        else:
            # Автоматическое сканирование папки fisgia_responses
            responses_dir = Path("fisgia_responses")
            if not responses_dir.exists():
                self.stdout.write("Папка fisgia_responses не найдена.")
                return
            
            # Ищем все CSV файлы
            csv_files = list(responses_dir.glob("*.csv"))
            if not csv_files:
                self.stdout.write("Нет CSV файлов в папке fisgia_responses.")
                return
            
            processed_count = 0
            for csv_file in csv_files:
                if self.process_file(csv_file):
                    processed_count += 1
            
            if processed_count > 0:
                self.stdout.write(self.style.SUCCESS(
                    f"Обработано файлов: {processed_count}"
                ))

    def process_file(self, path: Path) -> bool:
        """Обрабатывает один CSV файл. Возвращает True если файл был обработан."""
        if not path.exists():
            self.stderr.write(self.style.ERROR(f"Файл {path} не найден"))
            return False

        updated = 0
        processed_dir = path.parent / "processed"
        processed_dir.mkdir(exist_ok=True)

        try:
            with path.open("r", encoding="utf-8") as f:
                reader = csv.reader(f, delimiter=";")
                header = next(reader, None)

                # Определяем индексы колонок
                if not header:
                    self.stderr.write(self.style.ERROR(f"Файл {path} пустой или неверный формат"))
                    return False

                # Нормализуем заголовки
                header = [h.strip().lower() for h in header]
                
                # Определяем индексы
                try:
                    idx_id = header.index('id_abit')
                    idx_result = header.index('result')
                    idx_comment = header.index('comment') if 'comment' in header else None
                    idx_snils = header.index('snils') if 'snils' in header else None
                    idx_pasp_ser = header.index('pasp_ser') if 'pasp_ser' in header else None
                    idx_pasp_num = header.index('pasp_num') if 'pasp_num' in header else None
                except ValueError as e:
                    self.stderr.write(self.style.ERROR(f"Неверный формат заголовков в {path}: {e}"))
                    return False

                for row_num, row in enumerate(reader, start=2):
                    if len(row) <= idx_result:
                        continue
                    
                    try:
                        abit_id = int(row[idx_id])
                    except (ValueError, IndexError):
                        continue

                    result = row[idx_result].strip().lower() if idx_result < len(row) else ""
                    comment = row[idx_comment].strip() if idx_comment and idx_comment < len(row) else ""
                    
                    # Получаем данные паспорта и СНИЛС, если они есть
                    snils = row[idx_snils].strip() if idx_snils and idx_snils < len(row) and row[idx_snils] else None
                    pasp_ser = row[idx_pasp_ser].strip() if idx_pasp_ser and idx_pasp_ser < len(row) and row[idx_pasp_ser] else None
                    pasp_num = row[idx_pasp_num].strip() if idx_pasp_num and idx_pasp_num < len(row) and row[idx_pasp_num] else None

                    try:
                        applicant = Applicant.objects.get(pk=abit_id)
                    except Applicant.DoesNotExist:
                        self.stderr.write(f"Абитуриент id_abit={abit_id} не найден, пропускаю.")
                        continue

                    # Обновляем данные абитуриента (паспорт и СНИЛС), если они предоставлены
                    updated_applicant = False
                    if snils:
                        applicant.snils = snils
                        updated_applicant = True
                    if pasp_ser:
                        applicant.pasp_ser = pasp_ser
                        updated_applicant = True
                    if pasp_num:
                        applicant.pasp_num = pasp_num
                        updated_applicant = True
                    
                    if updated_applicant:
                        applicant.save()
                        self.stdout.write(f"Обновлены данные абитуриента {abit_id} (СНИЛС/паспорт)")

                    # Обновляем VerificationRequest
                    vr = (VerificationRequest.objects
                          .filter(applicant=applicant)
                          .order_by('-created_at')
                          .first())
                    if not vr:
                        self.stderr.write(f"Для абитуриента {abit_id} нет VerificationRequest, пропускаю.")
                        continue

                    if result == "accepted":
                        vr.status = "accepted"
                    elif result == "rejected":
                        vr.status = "rejected"
                    else:
                        self.stderr.write(f"Неизвестный result='{result}' для id_abit={abit_id}, пропускаю.")
                        continue

                    vr.message = comment
                    vr.save()
                    updated += 1

            # Перемещаем обработанный файл в папку processed
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            processed_file = processed_dir / f"{path.stem}_{timestamp}{path.suffix}"
            shutil.move(str(path), str(processed_file))
            
            self.stdout.write(self.style.SUCCESS(
                f"Файл {path.name} обработан. Обновлено {updated} заявок. Файл перемещён в processed/"
            ))
            return True

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Ошибка при обработке {path}: {e}"))
            return False
