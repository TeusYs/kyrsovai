from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from admissions.views import (
    ApplicantViewSet,
    ProgramViewSet,
    AchievementViewSet,
    ApplicantAchievementViewSet,
    ApplicationViewSet,
    StrokiZayavViewSet,

    register_view,
    login_view,
    logout_view,

    applicant_my_applications,
    applicant_apply,
    applicant_verification,
    applicant_lists,
    applicant_settings,
    program_detail,

    specialist_unverified,
    specialist_verified,
    specialist_invalid,
    specialist_documents,
    specialist_check_documents,
    specialist_applications,
    specialist_application_detail,
    specialist_settings,
)

from django.conf import settings
from django.conf.urls.static import static

router = DefaultRouter()
router.register(r'applicants', ApplicantViewSet)
router.register(r'programs', ProgramViewSet)
router.register(r'achievements', AchievementViewSet)
router.register(r'applicant_achievements', ApplicantAchievementViewSet)
router.register(r'applications', ApplicationViewSet)
router.register(r'stroki_zayav', StrokiZayavViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),

    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('register/', register_view, name='register'),

    # Абитуриент
    path('', applicant_my_applications, name='applicant_my_applications'),
    path('applicant/my-applications/', applicant_my_applications, name='applicant_my_applications'),
    path('applicant/apply/', applicant_apply, name='applicant_apply'),
    path('applicant/verification/', applicant_verification, name='applicant_verification'),
    path('applicant/lists/', applicant_lists, name='applicant_lists'),
    path('applicant/settings/', applicant_settings, name='applicant_settings'),
    path('list/<int:prog_id>/', program_detail, name='program_detail'),

    # Специалист
    path('specialist/unverified/', specialist_unverified, name='specialist_unverified'),
    path('specialist/verified/', specialist_verified, name='specialist_verified'),
    path('specialist/invalid/', specialist_invalid, name='specialist_invalid'),
    path('specialist/documents/', specialist_documents, name='specialist_documents'),
    path('specialist/documents/<int:applicant_id>/', specialist_check_documents, name='specialist_check_documents'),
    path('specialist/applications/', specialist_applications, name='specialist_applications'),
    path('specialist/applications/<int:app_id>/', specialist_application_detail, name='specialist_application_detail'),
    path('specialist/settings/', specialist_settings, name='specialist_settings'),

    # API
    path('api/', include(router.urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
