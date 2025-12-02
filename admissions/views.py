from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test

from rest_framework import viewsets

from .models import (
    Applicant,
    Program,
    Achievement,
    ApplicantAchievement,
    Application,
    StrokiZayav,
    UploadedDocument,
    VerificationRequest,      # <--- добавить
    ApplicationRequest, 
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
    ApplicantSearchForm,
)


# ===== DRF ViewSets (если нужно API) =====

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


# ===== Хелперы =====

# views.py
def get_applicant_for_user(user):
    if not user.is_authenticated:
        return None
    return Applicant.objects.filter(email__iexact=user.email).first()


def is_verified(applicant):
    """
    Проверяет, прошёл ли абитуриент верификацию.
    Верификация считается пройденной, если все три обязательных документа
    (passport, snils, education) имеют статус 'approved'.
    """
    if not applicant:
        return False
    
    required_doc_types = ['passport', 'snils', 'education']
    docs = UploadedDocument.objects.filter(applicant=applicant)
    
    for doc_type in required_doc_types:
        if not docs.filter(doc_type=doc_type, status='approved').exists():
            return False
    
    return True


def compute_verification_state(applicant):
    """
    Возвращает строку-состояние верификации для абитуриента.
    Возможные значения:
      - 'none'             — нет документов и нет заявки верификации
      - 'awaiting_export'  — есть документы, но VerificationRequest.new
      - 'awaiting_fisgia'  — VerificationRequest.sent
      - 'fisgia_rejected'  — VerificationRequest.rejected
      - 'awaiting_staff'   — ФИСГИА приняла, но сотрудник ещё не подтвердил
      - 'verified'         — документы подтверждены сотрудником
    """

    docs = UploadedDocument.objects.filter(applicant=applicant)
    has_docs = docs.exists()

    # Если все обязательные документы имеют статус 'approved', верификация пройдена
    if is_verified(applicant):
        return 'verified'

    vr = (VerificationRequest.objects
          .filter(applicant=applicant)
          .order_by('-created_at')
          .first())

    # если вообще ничего нет
    if not has_docs and not vr:
        return 'none'

    # если есть документы, но ещё не создавали VerificationRequest (или он new)
    if vr is None or vr.status == 'new':
        return 'awaiting_export'

    if vr.status == 'sent':
        return 'awaiting_fisgia'

    if vr.status == 'rejected':
        return 'fisgia_rejected'

    if vr.status == 'accepted':
        # ФИСГИА приняла, но сотрудник ещё не подтвердил
        return 'awaiting_staff'

    return 'none'

def is_specialist(user):
    return user.is_authenticated and user.is_staff


specialist_required = user_passes_test(is_specialist, login_url='login')


# ===== Аутентификация =====

def register_view(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
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
            # проверяем роль
            if role == 'specialist' and not is_specialist(user):
                error = 'Эта учётная запись не является сотрудником.'
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
    if not applicant:
        return render(request, 'applicant/no_profile.html')

    if request.method == 'POST' and 'delete_application' in request.POST:
        # Отзыв заявления
        app_id = request.POST.get('app_id')
        try:
            app = Application.objects.get(id_aplic=app_id, id_abit=applicant)
            # Удаляем связанные записи
            StrokiZayav.objects.filter(id_aplic=app).delete()
            ApplicationRequest.objects.filter(application=app).delete()
            app.delete()
            return redirect('applicant_my_applications')
        except Application.DoesNotExist:
            pass

    applications = (Application.objects
                    .filter(id_abit=applicant)
                    .order_by('-data'))
    
    # Получаем строки заявлений для всех заявлений и группируем по заявлениям
    app_ids = [app.id_aplic for app in applications]
    lines_dict = {}
    if app_ids:
        lines = StrokiZayav.objects.filter(id_aplic__in=app_ids).select_related('id_prog', 'id_aplic')
        for line in lines:
            app_id = line.id_aplic.id_aplic
            if app_id not in lines_dict:
                lines_dict[app_id] = []
            lines_dict[app_id].append(line)
    
    # Создаем список кортежей (application, lines) для удобства в шаблоне
    applications_with_lines = []
    for app in applications:
        applications_with_lines.append({
            'application': app,
            'lines': lines_dict.get(app.id_aplic, [])
        })

    verification_state = compute_verification_state(applicant)
    verified = (verification_state == 'verified')

    return render(request, 'applicant/my_applications.html', {
        'applicant': applicant,
        'applications_with_lines': applications_with_lines,
        'verification_state': verification_state,
        'verified': verified,
    })



@login_required
def applicant_apply(request):
    applicant = get_applicant_for_user(request.user)
    if not applicant:
        return render(request, 'applicant/error.html', {
            'message': 'Профиль абитуриента не найден. Обратитесь в приёмную комиссию.',
        })

    # Подавать заявление можно только если все обязательные документы подтверждены
    docs_ok = is_verified(applicant)

    if not docs_ok:
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
        # Предзаполняем форму данными из последнего заявления абитуриента (если есть)
        last_application = (Application.objects
                           .filter(id_abit=applicant)
                           .order_by('-data', '-id_aplic')
                           .first())
        
        initial_data = {}
        if last_application:
            initial_data['forma'] = last_application.forma
            initial_data['fin'] = last_application.fin
            
            # Получаем последнюю строку заявления для program и tip_obraz
            last_stroka = (StrokiZayav.objects
                          .filter(id_aplic=last_application)
                          .order_by('-priorit')
                          .first())
            if last_stroka:
                initial_data['program'] = last_stroka.id_prog
                initial_data['tip_obraz'] = last_stroka.id_tip_obraz
        
        form = ApplicationForm(initial=initial_data)

    return render(request, 'applicant/apply.html', {
        'menu_active': 'apply',
        'applicant': applicant,
        'form': form,
    })


@login_required
def applicant_verification(request):
    applicant = get_applicant_for_user(request.user)
    if not applicant:
        return render(request, 'applicant/error.html', {
            'message': 'Профиль абитуриента не найден. Обратитесь в приёмную комиссию.',
        })

    if request.method == 'POST':
        form = ApplicantVerificationForm(request.POST, request.FILES)
        if form.is_valid():
            cd = form.cleaned_data
            any_file = False

            if cd.get('passport'):
                UploadedDocument.objects.create(
                    applicant=applicant,
                    doc_type='passport',
                    file=cd['passport'],
                    status='pending'
                )
                any_file = True
            if cd.get('snils'):
                UploadedDocument.objects.create(
                    applicant=applicant,
                    doc_type='snils',
                    file=cd['snils'],
                    status='pending'
                )
                any_file = True
            if cd.get('education'):
                UploadedDocument.objects.create(
                    applicant=applicant,
                    doc_type='education',
                    file=cd['education'],
                    status='pending'
                )
                any_file = True
            if cd.get('quota'):
                UploadedDocument.objects.create(
                    applicant=applicant,
                    doc_type='quota',
                    file=cd['quota'],
                    status='pending'
                )
                any_file = True
            if cd.get('achievement'):
                UploadedDocument.objects.create(
                    applicant=applicant,
                    doc_type='achievement',
                    file=cd['achievement'],
                    status='pending'
                )
                any_file = True

            # если хотя бы один файл был загружен — ставим в очередь на ФИСГИА
            if any_file:
                VerificationRequest.objects.get_or_create(
                    applicant=applicant,
                    status='new',
                )

            return redirect('applicant_verification')
    else:
        form = ApplicantVerificationForm()

    docs = UploadedDocument.objects.filter(applicant=applicant).order_by('-uploaded_at')

    # Находим только актуальные отклоненные документы (последние для каждого типа)
    # Если для типа есть более новая approved/pending версия, старую rejected не показываем
    all_docs = UploadedDocument.objects.filter(applicant=applicant).order_by('-uploaded_at')
    latest_by_type = {}
    for doc in all_docs:
        if doc.doc_type not in latest_by_type:
            latest_by_type[doc.doc_type] = doc
    
    # Фильтруем только те rejected документы, которые являются последними для своего типа
    current_rejected = [doc for doc in latest_by_type.values() if doc.status == 'rejected']

    if not docs.exists():
        status = 'no_docs'
    elif docs.filter(status='pending').exists():
        status = 'pending'
    elif docs.filter(status='rejected').exists():
        status = 'rejected'
    elif docs.filter(status='approved').exists():
        status = 'approved'
    else:
        status = 'no_docs'

    return render(request, 'applicant/verification.html', {
        'menu_active': 'verification',
        'applicant': applicant,
        'form': form,
        'docs': docs,
        'status': status,
        'current_rejected': current_rejected,
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
    program = get_object_or_404(Program, pk=prog_id)
    # Показываем только абитуриентов со статусом "принято"
    lines = (StrokiZayav.objects
             .filter(id_prog=program, id_aplic__status='принято')
             .select_related('id_abit', 'id_aplic'))
    return render(request, 'applicant/program_detail.html', {
        'program': program,
        'lines': lines,
    })


# ===== Кабинет специалиста =====

@specialist_required
def specialist_unverified(request):
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
    # Получаем только последний документ каждого типа для этого абитуриента
    all_docs = UploadedDocument.objects.filter(applicant=applicant).order_by('-uploaded_at')
    
    # Группируем по типу документа и берем только последний (самый свежий) для каждого типа
    docs_dict = {}
    for doc in all_docs:
        if doc.doc_type not in docs_dict:
            docs_dict[doc.doc_type] = doc
    
    # Преобразуем обратно в список, отсортированный по дате загрузки
    docs = sorted(docs_dict.values(), key=lambda x: x.uploaded_at, reverse=True)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action in ('approve_doc', 'reject_doc'):
            doc = get_object_or_404(UploadedDocument, pk=request.POST.get('doc_id'), applicant=applicant)
            if action == 'approve_doc':
                doc.status = 'approved'
                doc.reason = ''
            else:
                doc.status = 'rejected'
                doc.reason = request.POST.get('reason', '').strip()
            doc.save()
            return redirect('specialist_check_documents', applicant_id=applicant.id_abit)

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
def specialist_applications(request, prog_id=None):
    if prog_id is None:
        # Показываем список направлений, по которым есть заявления
        programs_with_apps = Program.objects.filter(
            strokizayav__id_aplic__isnull=False
        ).distinct().order_by('nazv')
        
        return render(request, 'specialist/applications_list.html', {
            'menu_active': 'applications',
            'programs': programs_with_apps,
        })
    else:
        # Показываем заявления по выбранному направлению
        program = get_object_or_404(Program, pk=prog_id)
        
        # Получаем заявления через StrokiZayav для этого направления
        # Сначала те, которые нужно подтвердить (статус "на проверке"), потом остальные
        lines = StrokiZayav.objects.filter(
            id_prog=program
        ).select_related('id_aplic', 'id_abit', 'id_prog')
        
        # Группируем по заявлениям и сортируем: сначала "на проверке", потом остальные
        apps_dict = {}
        for line in lines:
            app_id = line.id_aplic.id_aplic
            if app_id not in apps_dict:
                apps_dict[app_id] = {
                    'application': line.id_aplic,
                    'lines': []
                }
            apps_dict[app_id]['lines'].append(line)
        
        # Сортируем: сначала заявления со статусом "на проверке", потом остальные
        # Для "на проверке" первый элемент кортежа будет False (0), для остальных True (1)
        # reverse=True означает, что False будет после True, поэтому используем reverse=False
        apps_list = sorted(
            apps_dict.values(),
            key=lambda x: (
                0 if x['application'].status == 'на проверке' else 1,  # Сначала "на проверке"
                -x['application'].data.toordinal() if hasattr(x['application'].data, 'toordinal') else 0,  # Потом по дате (новые первыми)
                -x['application'].id_aplic  # Потом по ID (новые первыми)
            )
        )
        
        return render(request, 'specialist/applications.html', {
            'menu_active': 'applications',
            'program': program,
            'apps_list': apps_list,
        })


@specialist_required
def specialist_application_detail(request, app_id):
    app = get_object_or_404(
        Application.objects.select_related('id_abit'),
        pk=app_id
    )
    lines = StrokiZayav.objects.filter(id_aplic=app).select_related('id_prog', 'id_tip_obraz')

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
def specialist_queries(request):
    """
    Обработка всех типов запросов для специалиста:
    1. Список всех абитуриентов, подавших документы
    2. Поиск по ФИО/ID
    3. Контактные данные абитуриента
    4. Список по периоду
    5. По специальности/направлению
    6. С достижениями
    """
    results = None
    query_type = None
    
    if request.method == 'POST':
        form = ApplicantSearchForm(request.POST)
        if form.is_valid():
            query_type = form.cleaned_data['query_type']
            
            if query_type == 'all':
                # 1. Все абитуриенты, подавшие документы
                applicants = Applicant.objects.filter(
                    uploadeddocument__isnull=False
                ).distinct().order_by('fam', 'imya', 'otch')
                results = applicants
                
            elif query_type == 'by_name':
                # 2. Поиск по ФИО/ID
                search_text = form.cleaned_data['search_text'].strip()
                applicants = []
                
                # Попытка найти по ID
                try:
                    app_id = int(search_text)
                    applicant = Applicant.objects.filter(id_abit=app_id).first()
                    if applicant:
                        applicants = [applicant]
                except ValueError:
                    pass
                
                # Поиск по ФИО
                if not applicants:
                    parts = search_text.split()
                    if len(parts) >= 1:
                        applicants = Applicant.objects.filter(fam__icontains=parts[0])
                        if len(parts) >= 2:
                            applicants = applicants.filter(imya__icontains=parts[1])
                        if len(parts) >= 3:
                            applicants = applicants.filter(otch__icontains=parts[2])
                        applicants = applicants.order_by('fam', 'imya', 'otch')
                
                results = applicants
                
            elif query_type == 'contacts':
                # 3. Контактные данные конкретного абитуриента
                search_text = form.cleaned_data['contact_search_text'].strip()
                applicant = None
                
                # Попытка найти по ID
                try:
                    app_id = int(search_text)
                    applicant = Applicant.objects.filter(id_abit=app_id).first()
                except ValueError:
                    pass
                
                # Поиск по ФИО
                if not applicant:
                    parts = search_text.split()
                    if len(parts) >= 1:
                        query = Applicant.objects.filter(fam__icontains=parts[0])
                        if len(parts) >= 2:
                            query = query.filter(imya__icontains=parts[1])
                        if len(parts) >= 3:
                            query = query.filter(otch__icontains=parts[2])
                        applicant = query.first()
                
                # Возвращаем список с одним абитуриентом или пустой список
                if applicant:
                    results = [applicant]
                else:
                    results = []
                
            elif query_type == 'by_period':
                # 4. По периоду подачи документов
                date_from = form.cleaned_data['date_from']
                date_to = form.cleaned_data['date_to']
                
                applicants = Applicant.objects.filter(
                    uploadeddocument__uploaded_at__date__gte=date_from,
                    uploadeddocument__uploaded_at__date__lte=date_to
                ).distinct().order_by('fam', 'imya', 'otch')
                results = applicants
                
            elif query_type == 'by_program':
                # 5. По специальности/направлению
                program = form.cleaned_data['program']
                
                applicants = Applicant.objects.filter(
                    strokizayav__id_prog=program
                ).distinct().order_by('fam', 'imya', 'otch')
                results = applicants
                
            elif query_type == 'with_achievements':
                # 6. С достижениями (ГТО, волонтёрство)
                # Ищем абитуриентов, у которых есть загруженные документы о достижениях
                # Достижения могут быть как в UploadedDocument (загруженные файлы),
                # так и в ApplicantAchievement (зарегистрированные достижения)
                
                # Собираем ID абитуриентов из обоих источников
                applicant_ids = set()
                
                # 1. По загруженным документам типа 'achievement'
                applicant_ids_from_docs = Applicant.objects.filter(
                    uploadeddocument__doc_type='achievement'
                ).values_list('id_abit', flat=True).distinct()
                applicant_ids.update(applicant_ids_from_docs)
                
                # 2. По таблице ApplicantAchievement (если есть зарегистрированные достижения)
                # Ищем достижения, связанные с ГТО или волонтёрством
                achievements = Achievement.objects.filter(
                    tip__icontains='ГТО'
                ) | Achievement.objects.filter(
                    tip__icontains='волонт'
                ) | Achievement.objects.filter(
                    nazv__icontains='ГТО'
                ) | Achievement.objects.filter(
                    nazv__icontains='волонт'
                )
                
                applicant_ids_from_ach = ApplicantAchievement.objects.filter(
                    id_ach__in=achievements
                ).values_list('id_abit', flat=True).distinct()
                applicant_ids.update(applicant_ids_from_ach)
                
                # Получаем абитуриентов по собранным ID
                if applicant_ids:
                    applicants = Applicant.objects.filter(
                        id_abit__in=list(applicant_ids)
                    ).order_by('fam', 'imya', 'otch')
                else:
                    applicants = Applicant.objects.none()
                
                results = applicants
    else:
        form = ApplicantSearchForm()
    
    return render(request, 'specialist/queries.html', {
        'menu_active': 'queries',
        'form': form,
        'results': results,
        'query_type': query_type,
    })


@specialist_required
def specialist_settings(request):
    return render(request, 'specialist/settings.html', {
        'menu_active': 'settings',
    })
