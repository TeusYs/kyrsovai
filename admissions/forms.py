from django import forms
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.crypto import get_random_string

from .models import (
    Program,
    Application,
    StrokiZayav,
    TipObraz,
    UploadedDocument,
    Applicant,
)


# ---------- Регистрация пользователя ----------

class UserRegisterForm(forms.Form):
    ROLE_CHOICES = [
        ('applicant', 'Я абитуриент'),
        ('specialist', 'Я сотрудник приёмной комиссии'),
    ]

    role = forms.ChoiceField(
        label='Кто вы?',
        choices=ROLE_CHOICES,
        widget=forms.RadioSelect
    )

    email = forms.EmailField(label='Email (логин)')
    password1 = forms.CharField(label='Пароль', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Повторите пароль', widget=forms.PasswordInput)

    # Поля абитуриента (обязательны только если выбрана роль "абитуриент")
    fam = forms.CharField(label='Фамилия', required=False)
    imya = forms.CharField(label='Имя', required=False)
    otch = forms.CharField(label='Отчество', required=False)
    tel = forms.CharField(label='Телефон', required=False)

    pol = forms.ChoiceField(
        label='Пол',
        choices=[('M', 'Мужской'), ('F', 'Женский')],
        required=False,
    )
    dr = forms.DateField(
        label='Дата рождения',
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False,
    )

    def clean(self):
        cleaned = super().clean()
        role = cleaned.get('role')
        email = cleaned.get('email')
        p1 = cleaned.get('password1')
        p2 = cleaned.get('password2')

        if User.objects.filter(username=email).exists():
            self.add_error('email', 'Пользователь с таким email уже существует.')

        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'Пароли не совпадают.')

        if role == 'applicant':
            required_fields = ['fam', 'imya', 'tel', 'pol', 'dr']
            for f in required_fields:
                if not cleaned.get(f):
                    self.add_error(f, 'Обязательное поле для абитуриента.')

        return cleaned

    def save(self):
        data = self.cleaned_data
        role = data['role']

        user = User.objects.create_user(
            username=data['email'],
            email=data['email'],
            password=data['password1'],
        )

        applicant = None

        if role == 'specialist':
            # Сотрудник приёмной комиссии
            user.is_staff = True
            user.save()
        else:
            # Абитуриент (минимальный профиль, можно расширить)
            applicant = Applicant.objects.create(
                fam=data['fam'],
                imya=data['imya'],
                otch=data.get('otch') or '',
                pol=data['pol'] or 'M',
                dr=data['dr'] or timezone.now().date(),
                mr='',
                adr='',
                tel=data['tel'] or '',
                email=data['email'],
                snils='',
                pasp_ser='',
                pasp_num='',
                pasp_kem='',
                pasp_data=timezone.now().date(),
                pasp_code='',
                prev_level='',
                sred_bal=0,
                obshag=False,
                needs_spec=False,
                id_spec_uslov=None,
                id_lgot=None,
            )

        return user, applicant


# ---------- Подача заявления ----------

class ApplicationForm(forms.Form):
    program = forms.ModelChoiceField(
        queryset=Program.objects.all(),
        label='Направление подготовки',
        required=True,
    )
    forma = forms.ChoiceField(
        label='Форма обучения',
        choices=[('очная', 'Очная'), ('заочная', 'Заочная')],
        required=True,
    )
    fin = forms.ChoiceField(
        label='Тип обучения',
        choices=[('бюджет', 'Бюджет'), ('контракт', 'Контракт')],
        required=True,
    )
    tip_obraz = forms.ModelChoiceField(
        queryset=TipObraz.objects.all(),
        label='Тип образования (основание приёма)',
        required=True,
    )
    priorit = forms.IntegerField(
        label='Приоритет',
        min_value=1,
        initial=1,
        required=True,
    )
    description = forms.CharField(
        label='Комментарий к заявлению',
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
    )

    def save(self, applicant: Applicant) -> Application:
        app = Application.objects.create(
            data=timezone.now().date(),
            status='на проверке',
            reg_num=get_random_string(8),
            forma=self.cleaned_data['forma'],
            fin=self.cleaned_data['fin'],
            id_abit=applicant,
        )

        StrokiZayav.objects.create(
            description=self.cleaned_data.get('description') or 'Заявление абитуриента',
            priorit=self.cleaned_data['priorit'],
            id_aplic=app,
            id_tip_obraz=self.cleaned_data['tip_obraz'],
            id_abit=applicant,
            id_prog=self.cleaned_data['program'],
        )

        return app


# ---------- Верификация: форма для абитуриента ----------

class ApplicantVerificationForm(forms.Form):
    passport = forms.FileField(
        label='Прикрепить изображение паспорта',
        required=False
    )
    snils = forms.FileField(
        label='Прикрепить изображение СНИЛС',
        required=False
    )
    education = forms.FileField(
        label='Прикрепить аттестат/диплом об образовании',
        required=False
    )
    quota = forms.FileField(
        label='Документ для квоты',
        required=False
    )
    achievement = forms.FileField(
        label='Документ о достижениях',
        required=False
    )

    def has_any_file(self):
        cd = self.cleaned_data
        return any([
            cd.get('passport'),
            cd.get('snils'),
            cd.get('education'),
            cd.get('quota'),
            cd.get('achievement'),
        ])


# ---------- Проверка документов: форма для сотрудника ----------

class DocumentReviewForm(forms.Form):
    snils = forms.CharField(label='СНИЛС', required=False)
    passport_series = forms.CharField(label='Серия паспорта', required=False)
    passport_number = forms.CharField(label='Номер паспорта', required=False)
    extra_points = forms.IntegerField(
        label='Дополнительные баллы',
        required=False,
        min_value=0,
        initial=0
    )
