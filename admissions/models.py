from django.db import models


class SpecUslov(models.Model):
    id_spec_uslov = models.AutoField(primary_key=True)
    opisan = models.TextField()

    class Meta:
        db_table = 'spec_uslov'
        managed = False


class Lgot(models.Model):
    id_lgot = models.AutoField(primary_key=True)
    opisan_lg = models.TextField()

    class Meta:
        # таблица в БД создана как Lgot (с заглавной)
        db_table = 'Lgot'
        managed = False


class TipObraz(models.Model):
    id_tip_obraz = models.AutoField(primary_key=True)
    tip_obr = models.CharField(max_length=10)

    class Meta:
        db_table = 'Tip_obraz'
        managed = False
    def __str__(self):
        # подбери нужные подписи под свою предметку
        return self.tip_obr 

class Program(models.Model):
    id_prog = models.AutoField(primary_key=True)
    kod = models.CharField(max_length=20)
    nazv = models.TextField()
    srok = models.SmallIntegerField()

    class Meta:
        db_table = 'programs'
        managed = False
        
    def __str__(self):
        # то, что будет отображаться в выпадающем списке
        return f"{self.kod} — {self.nazv}"

class Applicant(models.Model):
    id_abit = models.AutoField(primary_key=True)
    fam = models.CharField(max_length=50)
    imya = models.CharField(max_length=50)
    otch = models.CharField(max_length=50, null=True, blank=True)
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
    id_spec_uslov = models.ForeignKey(
        SpecUslov,
        models.RESTRICT,
        db_column='id_spec_uslov',
        null=True,
        blank=True
    )
    id_lgot = models.ForeignKey(
        Lgot,
        models.RESTRICT,
        db_column='id_lgot',
        null=True,
        blank=True
    )

    class Meta:
        db_table = 'applicants'
        managed = False

    def __str__(self):
        return f"{self.fam} {self.imya} {self.otch or ''}".strip()

    
class Achievement(models.Model):
    id_ach = models.AutoField(primary_key=True)
    tip = models.CharField(max_length=50)
    nazv = models.TextField()
    achiv_b = models.IntegerField()

    class Meta:
        db_table = 'achievements'
        managed = False


class ApplicantAchievement(models.Model):
    id_ach_ab = models.AutoField(primary_key=True)
    podtvr = models.BooleanField(default=False)
    fail = models.TextField()
    dobav = models.DateTimeField()
    god = models.IntegerField()
    id_ach = models.ForeignKey(Achievement, models.CASCADE, db_column='id_ach')
    id_abit = models.ForeignKey(Applicant, models.CASCADE, db_column='id_abit')

    class Meta:
        db_table = 'applicant_achievements'
        managed = False


class Application(models.Model):
    id_aplic = models.AutoField(primary_key=True)
    data = models.DateField()
    status = models.CharField(max_length=20)
    reg_num = models.CharField(max_length=20)
    forma = models.CharField(max_length=10)
    fin = models.CharField(max_length=10)
    id_abit = models.ForeignKey(Applicant, models.CASCADE, db_column='id_abit')

    class Meta:
        db_table = 'applications'
        managed = False
    def __str__(self):
        return f"Заявление #{self.id_aplic} от {self.data} ({self.status})"

class StrokiZayav(models.Model):
    stroki_id = models.AutoField(primary_key=True)
    description = models.TextField()
    priorit = models.SmallIntegerField()
    id_aplic = models.ForeignKey(Application, models.CASCADE, db_column='id_aplic')
    id_tip_obraz = models.ForeignKey(TipObraz, models.CASCADE, db_column='id_tip_obraz')
    id_abit = models.ForeignKey(Applicant, models.CASCADE, db_column='id_abit')
    id_prog = models.ForeignKey(Program, models.CASCADE, db_column='id_prog')

    class Meta:
        db_table = 'stroki_zayav'
        managed = False


# ==== Дополнительные таблицы для web-функционала (управляются Django) ====


class UploadedDocument(models.Model):
    DOC_TYPES = [
        ('main', 'Обязательный'),
        ('quota', 'Квота'),
        ('achievement', 'Достижение'),
        ('other', 'Дополнительный'),
    ]
    STATUS = [
        ('pending', 'На проверке'),
        ('approved', 'Подтвержден'),
        ('rejected', 'Отклонен'),
    ]

    applicant = models.ForeignKey(Applicant, on_delete=models.CASCADE)
    doc_type = models.CharField(max_length=20, choices=DOC_TYPES)
    file = models.FileField(upload_to='docs/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS, default='pending')

    class Meta:
        db_table = 'uploaded_documents'
        managed = True
