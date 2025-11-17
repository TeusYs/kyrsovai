from django.contrib import admin
from .models import Program, TipObraz, Applicant, Application, StrokiZayav, UploadedDocument, VerificationRequest, ApplicationRequest

admin.site.register(Program)
admin.site.register(TipObraz)
admin.site.register(Applicant)
admin.site.register(Application)
admin.site.register(StrokiZayav)
admin.site.register(UploadedDocument)
admin.site.register(VerificationRequest)
admin.site.register(ApplicationRequest)