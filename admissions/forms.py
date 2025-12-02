from django import forms
from datetime import date
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.crypto import get_random_string
from .models import Applicant  # <— импортируй вашу модель
from .models import (
    Program,
    TipObraz,
    Applicant,
    Application,
    StrokiZayav,
    UploadedDocument,
    ApplicationRequest,
)


# ===== Регистрация пользователя =====

class UserRegisterForm(forms.Form):
    ROLE_CHOICES = [
        ('applicant', 'Я абитуриент'),
        ('specialist', 'Я сотрудник приёмной комиссии'),
    ]

    role = forms.ChoiceField(choices=ROLE_CHOICES, widget=forms.RadioSelect)
    email = forms.EmailField(label='Email (логин)')
    password1 = forms.CharField(label='Пароль', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Повторите пароль', widget=forms.PasswordInput)

    # НЕОБЯЗАТЕЛЬНЫЕ поля для первичного заполнения
    fam  = forms.CharField(label='Фамилия', required=False)
    imya = forms.CharField(label='Имя', required=False)
    otch = forms.CharField(label='Отчество', required=False)
    tel  = forms.CharField(label='Телефон', required=False)
    pol  = forms.ChoiceField(label='Пол', required=False, choices=[('', '—'), ('M', 'М'), ('F', 'Ж')])
    dr   = forms.DateField(label='Дата рождения', required=False, widget=forms.DateInput(attrs={'type': 'date'}))

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('password1') != cleaned.get('password2'):
            raise forms.ValidationError('Пароли не совпадают.')
        return cleaned


    def save(self):
        data = self.cleaned_data
        user = User.objects.create_user(
            username=data['email'],
            email=data['email'],
            password=data['password1']
        )

        if data['role'] == 'specialist':
            user.is_staff = True
            user.save()

        # 2) если это абитуриент — гарантированно создаём запись в "applicants"
        if data['role'] == 'applicant':
            # Не попытаться создать дубликат, если такой email уже существует в applicants
            exists = Applicant.objects.filter(email=data['email']).exists()
            if not exists:
                # безопасные значения по умолчанию (NOT NULL → не NULL, а пустые строки / нули)
                fam  = data.get('fam')  or ''
                imya = data.get('imya') or ''
                otch = data.get('otch') or ''
                tel  = data.get('tel')  or ''
                pol  = data.get('pol')  or ''      # 'M' / 'F' или пусто
                dr   = data.get('dr')   or date(1900, 1, 1)

                Applicant.objects.create(
                    fam=fam,
                    imya=imya,
                    otch=otch,
                    pol=pol or 'M',             # пусть будет 'M' по умолчанию
                    dr=dr,
                    mr='',                      # место рождения
                    adr='',                     # адрес
                    tel=tel,
                    email=data['email'],
                    snils='',                   # будет загружен/заполнен при верификации
                    pasp_ser='',
                    pasp_num='',
                    pasp_kem='',
                    pasp_data=date(1900, 1, 1),
                    pasp_code='',
                    prev_level='',              # пред. образование
                    sred_bal=0.0,
                    obshag=False,
                    needs_spec=False,
                    id_spec_uslov=None,
                    id_lgot=None,
                )
        return user


# ===== Подача заявления абитуриентом =====

class ApplicationForm(forms.Form):
    program = forms.ModelChoiceField(
        queryset=Program.objects.all(),
        label='Направление подготовки',
        required=True,
    )
    forma = forms.ChoiceField(
        label='Форма обучения',
        required=True,
    )
    fin = forms.ChoiceField(
        label='Тип обучения',
        required=True,
    )
    tip_obraz = forms.ModelChoiceField(
        queryset=TipObraz.objects.all(),
        label='Тип образования (основание приёма)',
        required=True,
        to_field_name='id_tip_obraz',
    )
    priorit = forms.IntegerField(
        label='Приоритет',
        min_value=1,
        required=True,
    )
    description = forms.CharField(
        label='Комментарий',
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Получаем уникальные значения формы обучения из БД
        forma_choices = Application.objects.values_list('forma', flat=True).distinct()
        if forma_choices:
            # Преобразуем в список кортежей для ChoiceField
            self.fields['forma'].choices = [(val, val) for val in forma_choices if val]
        else:
            # Если в БД нет значений, используем значения по умолчанию
            self.fields['forma'].choices = [('очная', 'Очная'), ('заочная', 'Заочная')]
        
        # Получаем уникальные значения типа обучения из БД
        fin_choices = Application.objects.values_list('fin', flat=True).distinct()
        if fin_choices:
            # Преобразуем в список кортежей для ChoiceField
            self.fields['fin'].choices = [(val, val) for val in fin_choices if val]
        else:
            # Если в БД нет значений, используем значения по умолчанию
            self.fields['fin'].choices = [('бюджет', 'Бюджет'), ('контракт', 'Контракт')]

    def save(self, applicant: Applicant) -> Application:
        # создаём запись в applications
        app = Application.objects.create(
            data=timezone.now().date(),
            status='на проверке',  # строго по CHECK в БД
            reg_num=get_random_string(8),
            id_abit=applicant,
            forma=self.cleaned_data['forma'],
            fin=self.cleaned_data['fin'],
        )

        # создаём строку заявления
        StrokiZayav.objects.create(
            description=self.cleaned_data.get('description') or 'Заявление',
            priorit=self.cleaned_data['priorit'],
            id_aplic=app,
            id_tip_obraz=self.cleaned_data['tip_obraz'],
            id_abit=applicant,
            id_prog=self.cleaned_data['program'],
        )

        # добавляем заявку в очередь на ФИСГИА
        ApplicationRequest.objects.create(
            application=app,
            status='new',
        )

        return app


# ===== Верификация абитуриента =====

class ApplicantVerificationForm(forms.Form):
    passport = forms.FileField(
        label='Изображение паспорта',
        required=False
    )
    snils = forms.FileField(
        label='Изображение СНИЛС',
        required=False
    )
    education = forms.FileField(
        label='Документ об образовании (аттестат/диплом)',
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


# ===== Форма проверки документов (поля, которые переписываем в applicants) =====

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


# ===== Смена статуса заявления =====

class ApplicationStatusForm(forms.Form):
    STATUS_CHOICES = [
        ('на проверке', 'На проверке'),
        ('принято', 'Принято'),
        ('отклонено', 'Отклонено'),
    ]
    status = forms.ChoiceField(choices=STATUS_CHOICES, label='Статус заявления')


# ===== Запросы для специалиста =====

class ApplicantSearchForm(forms.Form):
    QUERY_TYPE_CHOICES = [
        ('all', 'Все абитуриенты, подавшие документы'),
        ('by_name', 'Поиск по ФИО/ID'),
        ('contacts', 'Контактные данные абитуриента'),
        ('by_period', 'По периоду подачи документов'),
        ('by_program', 'По специальности/направлению'),
        ('with_achievements', 'С достижениями (ГТО, волонтёрство)'),
    ]
    
    query_type = forms.ChoiceField(
        choices=QUERY_TYPE_CHOICES,
        label='Тип запроса',
        required=True,
        widget=forms.RadioSelect
    )
    
    # Поля для поиска по ФИО/ID
    search_text = forms.CharField(
        label='ФИО или ID',
        required=False,
        help_text='Введите ФИО или ID абитуриента'
    )
    
    # Поле для поиска контактных данных конкретного абитуриента
    contact_search_text = forms.CharField(
        label='ФИО или ID абитуриента',
        required=False,
        help_text='Введите ФИО или ID абитуриента для получения контактных данных'
    )
    
    # Поля для поиска по периоду
    date_from = forms.DateField(
        label='Дата начала',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    date_to = forms.DateField(
        label='Дата окончания',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    
    # Поле для поиска по специальности
    program = forms.ModelChoiceField(
        queryset=Program.objects.all(),
        label='Направление подготовки',
        required=False
    )
    
    def clean(self):
        cleaned = super().clean()
        query_type = cleaned.get('query_type')
        
        if query_type == 'by_name' and not cleaned.get('search_text'):
            raise forms.ValidationError('Для поиска по ФИО/ID необходимо указать значение.')
        
        if query_type == 'contacts' and not cleaned.get('contact_search_text'):
            raise forms.ValidationError('Для получения контактных данных необходимо указать ФИО или ID абитуриента.')
        
        if query_type == 'by_period':
            if not cleaned.get('date_from') or not cleaned.get('date_to'):
                raise forms.ValidationError('Для поиска по периоду необходимо указать обе даты.')
            if cleaned.get('date_from') and cleaned.get('date_to'):
                if cleaned['date_from'] > cleaned['date_to']:
                    raise forms.ValidationError('Дата начала не может быть позже даты окончания.')
        
        if query_type == 'by_program' and not cleaned.get('program'):
            raise forms.ValidationError('Для поиска по специальности необходимо выбрать направление.')
        
        return cleaned
