from django.db import models

# Таблица абитуриентов
class Applicant(models.Model):
    id_abit = models.AutoField(primary_key=True)
    fam = models.CharField(max_length=50)
    imya = models.CharField(max_length=50)
    otch = models.CharField(max_length=50, blank=True, null=True)
    pol = models.CharField(max_length=1)
    dr = models.DateField()
    mr = models.TextField()
    adr = models.TextField()
    tel = models.CharField(max_length=20)
    email = models.TextField()
    snils = models.CharField(max_length=14)
    pasp_ser = models.CharField(max_length=10)
    pasp_num = models.CharField(max_length=10)
    pasp_kem = models.TextField()
    pasp_data = models.DateField()
    pasp_code = models.CharField(max_length=10)
    prev_level = models.CharField(max_length=20)
    sred_bal = models.FloatField()
    obshag = models.BooleanField()
    needs_spec = models.BooleanField()
    id_spec_uslov = models.IntegerField(blank=True, null=True)
    id_lgot = models.IntegerField(blank=True, null=True)

    class Meta:
        db_table = 'applicants'
        managed = False  # Не управляем этой таблицей

    def __str__(self):
        return f"{self.fam} {self.imya} {self.otch or ''}".strip()


# Направления подготовки
class Program(models.Model):
    id_prog = models.AutoField(primary_key=True)
    kod = models.CharField(max_length=20)
    nazv = models.TextField()
    srok = models.SmallIntegerField()

    class Meta:
        db_table = 'programs'
        managed = False  # Не управляем этой таблицей

    def __str__(self):
        return f"{self.kod} — {self.nazv}"


# Достижения абитуриента
class Achievement(models.Model):
    id_ach = models.AutoField(primary_key=True)
    tip = models.CharField(max_length=50)
    nazv = models.TextField()
    achiv_b = models.IntegerField()

    class Meta:
        db_table = 'achievements'
        managed = False  # Не управляем этой таблицей


# Достижения абитуриента с привилегиями
class ApplicantAchievement(models.Model):
    id_ach_ab = models.AutoField(primary_key=True)  # Устанавливаем id_ach_ab как PRIMARY KEY
    podtvr = models.BooleanField(default=False)
    fail = models.TextField()
    dobav = models.DateTimeField()
    god = models.IntegerField()
    id_ach = models.ForeignKey(Achievement, db_column='id_ach', on_delete=models.CASCADE)
    id_abit = models.ForeignKey(Applicant, db_column='id_abit', on_delete=models.CASCADE)

    class Meta:
        db_table = 'applicant_achievements'
        managed = False  # Не управляем этой таблицей
        unique_together = ('id_ach_ab', 'id_ach', 'id_abit')


# Заявления абитуриентов
class Application(models.Model):
    id_aplic = models.AutoField(primary_key=True)
    data = models.DateField()
    status = models.CharField(max_length=20, default='На проверке')  # Статус заявления
    reg_num = models.CharField(max_length=20)
    id_abit = models.ForeignKey(Applicant, db_column='id_abit', on_delete=models.CASCADE)
    forma = models.CharField(max_length=20)
    fin = models.CharField(max_length=20)

    class Meta:
        db_table = 'applications'
        managed = False  # Не управляем этой таблицей
        unique_together = ('id_aplic', 'id_abit')


# Строки заявлений (все связанные данные, напр. тип образования)
class StrokiZayav(models.Model):
    stroki_id = models.AutoField(primary_key=True)  # Устанавливаем stroki_id как PRIMARY KEY
    description = models.TextField()
    priorit = models.SmallIntegerField()
    id_aplic = models.ForeignKey(Application, db_column='id_aplic', on_delete=models.CASCADE)
    id_tip_obraz = models.ForeignKey('TipObraz', db_column='id_tip_obraz', on_delete=models.RESTRICT)
    id_abit = models.ForeignKey(Applicant, db_column='id_abit', on_delete=models.CASCADE)
    id_prog = models.ForeignKey(Program, db_column='id_prog', on_delete=models.RESTRICT)

    class Meta:
        db_table = 'stroki_zayav'
        managed = False  # Не управляем этой таблицей
        unique_together = ('stroki_id', 'id_aplic', 'id_tip_obraz', 'id_abit', 'id_prog')


# Типы образования
class TipObraz(models.Model):
    id_tip_obraz = models.AutoField(primary_key=True)
    tip_obr = models.CharField(max_length=50)  # изменено с BooleanField на CharField

    class Meta:
        db_table = 'Tip_obraz'
        managed = False  # Не управляем этой таблицей


# Таблица для документов абитуриента (связываем их с заявлением)
class UploadedDocument(models.Model):
    DOC_TYPES = [
        ('passport', 'Паспорт'),
        ('snils', 'СНИЛС'),
        ('education', 'Документ об образовании'),
        ('quota', 'Квота'),
        ('achievement', 'Достижение'),
    ]

    STATUS_TYPES = [
        ('pending', 'На проверке'),
        ('approved', 'Подтверждён'),
        ('rejected', 'Отклонён'),
    ]

    applicant = models.ForeignKey(Applicant, on_delete=models.CASCADE)
    doc_type = models.CharField(max_length=20, choices=DOC_TYPES)
    file = models.FileField(upload_to='docs/')
    status = models.CharField(max_length=20, choices=STATUS_TYPES, default='pending')
    reason = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'uploaded_documents'
        managed = True  # Создаём миграцией, управляем только этой моделью

    def __str__(self):
        return f"{self.get_doc_type_display()} — {self.status}"


# Таблица для Льгот
class Lgot(models.Model):
    id_lgot = models.AutoField(primary_key=True)
    Opisan_lg = models.TextField()

    class Meta:
        db_table = 'Lgot'
        managed = False  # Не управляем этой таблицей


# Таблица для Специальных условий
class SpecUslov(models.Model):
    id_spec_uslov = models.AutoField(primary_key=True)
    opisan = models.TextField()

    class Meta:
        db_table = 'spec_uslov'
        managed = False  # Не управляем этой таблицей

# ===== Очередь на отправку в ФИСГИА =====

class VerificationRequest(models.Model):
    STATUS_CHOICES = [
        ('new', 'Новая (ещё не выгружена)'),
        ('sent', 'Отправлена в ФИСГИА'),
        ('accepted', 'ФИСГИА подтвердила'),
        ('rejected', 'ФИСГИА отклонила'),
    ]

    applicant = models.ForeignKey(Applicant, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    message = models.TextField(blank=True)

    class Meta:
        db_table = 'verification_requests'
        managed = True

    def __str__(self):
        return f"Верификация абитуриента {self.applicant_id} ({self.status})"


class ApplicationRequest(models.Model):
    STATUS_CHOICES = [
        ('new', 'Новая (ещё не выгружена в файл)'),
        ('sent', 'Файл отправлен в ФИСГИА'),
        ('accepted', 'Принято ФИСГИА'),
        ('rejected', 'Отклонено ФИСГИА'),
    ]

    application = models.ForeignKey(
        Application,
        db_column='id_aplic',
        on_delete=models.CASCADE,
        db_constraint=False,          # <--- вот это главное
        related_name='fisgia_requests',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    message = models.TextField(blank=True)

    class Meta:
        db_table = 'application_requests'
        managed = True

    def __str__(self):
        return f"Заявка {self.application_id} — {self.status}"
