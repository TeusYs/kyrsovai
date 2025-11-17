# admissions/management/commands/export_fisgia_applications.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from pathlib import Path
import csv

from admissions.models import ApplicationRequest, StrokiZayav

class Command(BaseCommand):
    help = 'Формирует файл для ФИСГИА по новым заявлениям (status=new)'

    def handle(self, *args, **options):
        qs = (ApplicationRequest.objects
              .select_related('application', 'application__id_abit')
              .filter(status='new'))
        if not qs.exists():
            self.stdout.write('Новых заявлений на поступление нет.')
            return

        now = timezone.now()
        base_dir = Path('fisgia_exports')
        base_dir.mkdir(exist_ok=True)

        filename = base_dir / f'applications_{now:%Y%m%d_%H%M}.csv'

        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow([
                'id_aplic', 'id_abit', 'fam', 'imya',
                'data', 'status', 'forma', 'fin',
                'program_kod', 'program_nazv', 'tip_obraz'
            ])

            for req in qs:
                app = req.application
                abit = app.id_abit

                # берём первую строку заявления (обычно одна)
                line = (StrokiZayav.objects
                        .select_related('id_prog', 'id_tip_obraz')
                        .filter(id_aplic=app)
                        .first())

                prog_kod = line.id_prog.kod if line else ''
                prog_nazv = line.id_prog.nazv if line else ''
                tip_obraz = line.id_tip_obraz.tip_obr if line else ''

                writer.writerow([
                    app.id_aplic,
                    abit.id_abit,
                    abit.fam,
                    abit.imya,
                    app.data.isoformat(),
                    app.status,
                    app.forma,
                    app.fin,
                    prog_kod,
                    prog_nazv,
                    tip_obraz,
                ])

        qs.update(status='sent', sent_at=now)

        self.stdout.write(self.style.SUCCESS(
            f'Сформирован файл {filename} и помечены {qs.count()} заявок как sent'
        ))
