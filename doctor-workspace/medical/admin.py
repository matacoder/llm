from django.contrib import admin
from .models import Doctor, Patient, MedicalRecord


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'specialty', 'license_number']
    search_fields = ['full_name', 'specialty', 'license_number']


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ['last_name', 'first_name', 'middle_name', 'birth_date', 'gender', 'phone']
    search_fields = ['last_name', 'first_name', 'middle_name', 'snils', 'policy_number']
    list_filter = ['gender']


@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = ['patient', 'doctor', 'visit_date', 'preliminary_diagnosis', 'ai_check_performed']
    list_filter = ['visit_date', 'ai_check_performed', 'doctor']
    search_fields = ['patient__last_name', 'patient__first_name', 'preliminary_diagnosis', 'icd10_code']
    date_hierarchy = 'visit_date'
    readonly_fields = ['ai_check_result', 'ai_check_timestamp', 'created_at', 'updated_at']
