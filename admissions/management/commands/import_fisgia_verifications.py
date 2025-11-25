from django.core.management.base import BaseCommand
from django.utils import timezone
from pathlib import Path
import csv

from admissions.models import Applicant, VerificationRequest

class Command(BaseCommand):
    help = "Импорт результата проверки документов из ФИСГИА (по файлу CSV)."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str, help="Путь к CSV файлу с результатами")

    def handle(self, *args, **options):
        path = Path(options["csv_path"])
        if not path.exists():
            self.stderr.write(self.style.ERROR(f"Файл {path} не найден"))
            return

        updated = 0

        with path.open("r", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter=";")
            header = next(reader, None)

            # проверим, есть ли заголовки, если нет — считаем первую строку данными
            def is_header(row):
                if not row:
                    return False
                return "id_abit" in row[0].lower()

            if header and not is_header(header):
                # первая строка — данные, вернём её в поток
                f.seek(0)
                reader = csv.reader(f, delimiter=";")

            for row in reader:
                if len(row) < 2:
                    continue
                try:
                    abit_id = int(row[0])
                except ValueError:
                    continue

                result = row[1].strip().lower()
                comment = row[2].strip() if len(row) > 2 else ""

                try:
                    applicant = Applicant.objects.get(pk=abit_id)
                except Applicant.DoesNotExist:
                    self.stderr.write(f"Абитуриент id_abit={abit_id} не найден, пропускаю.")
                    continue

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

        self.stdout.write(self.style.SUCCESS(
            f"Успешно обновлено {updated} заявок на верификацию."
        ))
