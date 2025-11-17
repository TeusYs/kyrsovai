# admissions/management/commands/export_fisgia_verifications.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from pathlib import Path
import csv

from admissions.models import VerificationRequest

class Command(BaseCommand):
    help = 'Формирует файл для ФИСГИА по новым верификациям (status=new)'

    def handle(self, *args, **options):
        qs = VerificationRequest.objects.select_related('applicant').filter(status='new')
        if not qs.exists():
            self.stdout.write('Новых заявок на верификацию нет.')
            return

        now = timezone.now()
        base_dir = Path('fisgia_exports')
        base_dir.mkdir(exist_ok=True)

        filename = base_dir / f'verifications_{now:%Y%m%d_%H%M}.csv'

        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter=';')
            # заголовки — все поля берём из БД applicants
            writer.writerow([
                'id_abit', 'fam', 'imya', 'otch', 'email', 'tel',
                'snils', 'pasp_ser', 'pasp_num', 'pasp_code', 'dr'
            ])
            for req in qs:
                a = req.applicant
                writer.writerow([
                    a.id_abit,
                    a.fam,
                    a.imya,
                    a.otch or '',
                    a.email,
                    a.tel,
                    a.snils,
                    a.pasp_ser,
                    a.pasp_num,
                    a.pasp_code,
                    a.dr.isoformat(),
                ])

        # помечаем как отправленные
        qs.update(status='sent', sent_at=now)

        self.stdout.write(self.style.SUCCESS(
            f'Сформирован файл {filename} и помечены {qs.count()} заявок как sent'
        ))
