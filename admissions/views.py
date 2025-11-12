from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db.models import Q

from rest_framework import viewsets

from .models import (
    Applicant,
    Program,
    Achievement,
    ApplicantAchievement,
    Application,
    StrokiZayav,
    UploadedDocument,
)
from .serializers import (
    ApplicantSerializer,
    ProgramSerializer,
    AchievementSerializer,
    ApplicantAchievementSerializer,
    ApplicationSerializer,
    StrokiZayavSerializer,
)
from .forms import (
    UserRegisterForm,
    ApplicationForm,
    ApplicantVerificationForm,
    DocumentReviewForm,
    ApplicationStatusForm,
)

# ===== DRF API =====

class ApplicantViewSet(viewsets.ModelViewSet):
    queryset = Applicant.objects.all()
    serializer_class = ApplicantSerializer


class ProgramViewSet(viewsets.ModelViewSet):
    queryset = Program.objects.all()
    serializer_class = ProgramSerializer


class AchievementViewSet(viewsets.ModelViewSet):
    queryset = Achievement.objects.all()
    serializer_class = AchievementSerializer


class ApplicantAchievementViewSet(viewsets.ModelViewSet):
    queryset = ApplicantAchievement.objects.all()
    serializer_class = ApplicantAchievementSerializer


class ApplicationViewSet(viewsets.ModelViewSet):
    queryset = Application.objects.all()
    serializer_class = ApplicationSerializer


class StrokiZayavViewSet(viewsets.ModelViewSet):
    queryset = StrokiZayav.objects.all()
    serializer_class = StrokiZayavSerializer


# ===== Хелперы ролей =====

def get_applicant_for_user(user):
    if not user.is_authenticated:
        return None
    return Applicant.objects.filter(email=user.email).first()


def is_specialist(user):
    return user.is_authenticated and user.is_staff


specialist_required = user_passes_test(is_specialist, login_url='login')


# ===== Регистрация / Логин / Логаут =====

def register_view(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user, applicant = form.save()
            login(request, user)
            if is_specialist(user):
                return redirect('specialist_unverified')
            return redirect('applicant_my_applications')
    else:
        form = UserRegisterForm()
    return render(request, 'auth/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        if is_specialist(request.user):
            return redirect('specialist_unverified')
        return redirect('applicant_my_applications')

    error = None
    if request.method == 'POST':
        role = request.POST.get('role', 'applicant')
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        user = authenticate(request, username=username, password=password)

        if user is None:
            error = 'Неверный логин или пароль.'
        else:
            if role == 'specialist' and not is_specialist(user):
                error = 'Эта учётная запись не является сотрудником приёмной комиссии.'
            elif role == 'applicant' and is_specialist(user):
                error = 'Эта учётная запись относится к сотруднику. Выберите роль сотрудника.'
            else:
                login(request, user)
                if is_specialist(user):
                    return redirect('specialist_unverified')
                return redirect('applicant_my_applications')

    return render(request, 'auth/login.html', {'error': error})


def logout_view(request):
    logout(request)
    return redirect('login')


# ===== Кабинет абитуриента =====

@login_required
def applicant_my_applications(request):
    applicant = get_applicant_for_user(request.user)

    if applicant:
        applications = (
            Application.objects
            .filter(id_abit=applicant)
            .prefetch_related('stroki_zayav_set')
            .order_by('-data', '-id_aplic')
        )
        docs = UploadedDocument.objects.filter(applicant=applicant)
        verified = docs.filter(status='approved').exists()
    else:
        applications = Application.objects.none()
        verified = False

    return render(request, 'applicant/my_applications.html', {
        'menu_active': 'my_applications',
        'applicant': applicant,
        'applications': applications,
        'verified': verified,
    })


@login_required
def applicant_apply(request):
    applicant = get_applicant_for_user(request.user)
    if not applicant:
        return render(request, 'applicant/error.html', {
            'message': 'Профиль абитуриента не найден.',
        })

    docs_verified = UploadedDocument.objects.filter(
        applicant=applicant,
        status='approved'
    ).exists()

    if not docs_verified:
        return render(request, 'applicant/apply_blocked.html', {
            'menu_active': 'apply',
            'applicant': applicant,
        })

    if request.method == 'POST':
        form = ApplicationForm(request.POST)
        if form.is_valid():
            form.save(applicant)
            return redirect('applicant_my_applications')
    else:
        form = ApplicationForm()

    return render(request, 'applicant/apply.html', {
        'menu_active': 'apply',
        'applicant': applicant,
        'form': form,
    })


@login_required
def applicant_verification(request):
    """
    Верификация:
    - нет документов → "Вы не подали документы..."
    - есть pending → "Ваши документы находятся на проверке."
    - есть approved → "Ваши документы подтверждены."
    - есть rejected и нет pending → "Ваши документы были отклонены."
    """
    applicant = get_applicant_for_user(request.user)
    if not applicant:
        return render(request, 'applicant/error.html', {
            'message': 'Профиль абитуриента не найден.',
        })

    if request.method == 'POST':
        form = ApplicantVerificationForm(request.POST, request.FILES)
        if form.is_valid():
            cd = form.cleaned_data

            if cd.get('passport'):
                UploadedDocument.objects.create(
                    applicant=applicant,
                    doc_type='passport',
                    file=cd['passport'],
                    status='pending',
                )
            if cd.get('snils'):
                UploadedDocument.objects.create(
                    applicant=applicant,
                    doc_type='snils',
                    file=cd['snils'],
                    status='pending',
                )
            if cd.get('education'):
                UploadedDocument.objects.create(
                    applicant=applicant,
                    doc_type='education',
                    file=cd['education'],
                    status='pending',
                )
            if cd.get('quota'):
                UploadedDocument.objects.create(
                    applicant=applicant,
                    doc_type='quota',
                    file=cd['quota'],
                    status='pending',
                )
            if cd.get('achievement'):
                UploadedDocument.objects.create(
                    applicant=applicant,
                    doc_type='achievement',
                    file=cd['achievement'],
                    status='pending',
                )

            return redirect('applicant_verification')
    else:
        form = ApplicantVerificationForm()

    docs = UploadedDocument.objects.filter(applicant=applicant).order_by('-uploaded_at')

    if not docs.exists():
        status = 'no_docs'
    elif docs.filter(status='pending').exists():
        status = 'pending'
    elif docs.filter(status='approved').exists():
        status = 'approved'
    elif docs.filter(status='rejected').exists():
        status = 'rejected'
    else:
        status = 'no_docs'

    return render(request, 'applicant/verification.html', {
        'menu_active': 'verification',
        'applicant': applicant,
        'form': form,
        'docs': docs,
        'status': status,
    })


@login_required
def applicant_lists(request):
    programs = Program.objects.all()
    return render(request, 'applicant/lists.html', {
        'menu_active': 'lists',
        'programs': programs,
    })


@login_required
def applicant_settings(request):
    applicant = get_applicant_for_user(request.user)
    return render(request, 'applicant/settings.html', {
        'menu_active': 'settings',
        'applicant': applicant,
    })


@login_required
def program_detail(request, prog_id):
    program = get_object_or_404(Program, id_prog=prog_id)
    lines = StrokiZayav.objects.filter(id_prog=program).select_related('id_abit', 'id_aplic')
    return render(request, 'applicant/program_detail.html', {
        'program': program,
        'lines': lines,
    })


# ===== Кабинет специалиста =====

@specialist_required
def specialist_unverified(request):
    """
    Неподтвержденные абитуриенты:
    есть документы в статусе pending.
    """
    applicants = (
        Applicant.objects
        .filter(uploadeddocument__status='pending')
        .distinct()
        .order_by('fam', 'imya')
    )
    return render(request, 'specialist/unverified.html', {
        'menu_active': 'unverified',
        'applicants': applicants,
    })

@specialist_required
def specialist_verified(request):
    """
    Подтвержденные абитуриенты:
    есть approved и нет pending/rejected.
    """
    applicants = (
        Applicant.objects
        .filter(uploadeddocument__status='approved')
        .exclude(uploadeddocument__status__in=['pending', 'rejected'])
        .distinct()
        .order_by('fam', 'imya')
    )
    return render(request, 'specialist/verified.html', {
        'menu_active': 'verified',
        'applicants': applicants,
    })

@specialist_required
def specialist_invalid(request):
    """
    Абитуриенты с неправильными документами:
    есть документы в статусе rejected.
    """
    applicants = (
        Applicant.objects
        .filter(uploadeddocument__status='rejected')
        .distinct()
        .order_by('fam', 'imya')
    )
    return render(request, 'specialist/invalid.html', {
        'menu_active': 'invalid',
        'applicants': applicants,
    })


@specialist_required
def specialist_documents(request):
    """
    Раздел «Проверка документов»:
    общий список всех документов для первичного просмотра.
    Из таблицы можно перейти к проверке конкретного абитуриента.
    """
    docs = (
        UploadedDocument.objects
        .select_related('applicant')
        .order_by('-uploaded_at')
    )
    return render(request, 'specialist/documents_list.html', {
        'menu_active': 'documents',
        'docs': docs,
    })

@specialist_required
def specialist_check_documents(request, applicant_id):
    applicant = get_object_or_404(Applicant, pk=applicant_id)
    docs = UploadedDocument.objects.filter(applicant=applicant).order_by('-uploaded_at')

    if request.method == 'POST':
        action = request.POST.get('action')

        # Одобрить / отклонить ОДИН документ c указанием причины
        if action in ('approve_doc', 'reject_doc'):
            doc_id = request.POST.get('doc_id')
            doc = get_object_or_404(UploadedDocument, pk=doc_id, applicant=applicant)

            if action == 'approve_doc':
                doc.status = 'approved'
                doc.reason = ''
            else:
                doc.status = 'rejected'
                doc.reason = request.POST.get('reason', '').strip()
            doc.save()

            return redirect('specialist_check_documents', applicant_id=applicant.id_abit)

        # Сохранение общих полей (СНИЛС, паспорт и т.п.)
        form = DocumentReviewForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            if cd.get('snils'):
                applicant.snils = cd['snils']
            if cd.get('passport_series'):
                applicant.pasp_ser = cd['passport_series']
            if cd.get('passport_number'):
                applicant.pasp_num = cd['passport_number']
            applicant.save()
            return redirect('specialist_check_documents', applicant_id=applicant.id_abit)
    else:
        form = DocumentReviewForm(initial={
            'snils': applicant.snils,
            'passport_series': applicant.pasp_ser,
            'passport_number': applicant.pasp_num,
            'extra_points': 0,
        })

    return render(request, 'specialist/documents.html', {
        'menu_active': 'documents',
        'applicant': applicant,
        'docs': docs,
        'form': form,
    })





@specialist_required
def specialist_applications(request):
    """
    Список всех заявлений с быстрым обзором статусов.
    """
    apps = (
        Application.objects
        .select_related('id_abit')
        .order_by('-data', '-id_aplic')
    )
    return render(request, 'specialist/applications.html', {
        'menu_active': 'applications',
        'apps': apps,
    })


@specialist_required
def specialist_application_detail(request, app_id):
    """
    Детальный просмотр заявления + смена статуса.
    """
    app = get_object_or_404(
        Application.objects.select_related('id_abit'),
        pk=app_id
    )
    lines = StrokiZayav.objects.filter(id_aplic=app).select_related('id_prog')

    if request.method == 'POST':
        form = ApplicationStatusForm(request.POST)
        if form.is_valid():
            app.status = form.cleaned_data['status']
            app.save()
            return redirect('specialist_application_detail', app_id=app.id_aplic)
    else:
        form = ApplicationStatusForm(initial={'status': app.status})

    return render(request, 'specialist/application_detail.html', {
        'menu_active': 'applications',
        'app': app,
        'lines': lines,
        'form': form,
    })
    
@specialist_required
def specialist_settings(request):
    return render(request, 'specialist/settings.html', {
        'menu_active': 'settings',
    })