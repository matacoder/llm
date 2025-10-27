from django.urls import path
from . import views

urlpatterns = [
    # Главная страница
    path('', views.dashboard, name='dashboard'),

    # Пациенты
    path('patients/', views.patient_list, name='patient_list'),
    path('patients/create/', views.patient_create, name='patient_create'),
    path('patients/<int:patient_id>/', views.patient_detail, name='patient_detail'),
    path('patients/<int:patient_id>/edit/', views.patient_update, name='patient_update'),

    # Медицинские карты
    path('patients/<int:patient_id>/records/create/', views.medical_record_create, name='medical_record_create'),
    path('records/<int:record_id>/', views.medical_record_detail, name='medical_record_detail'),
    path('records/<int:record_id>/edit/', views.medical_record_update, name='medical_record_update'),

    # AI проверка
    path('records/<int:record_id>/ai-check/', views.ai_check_decision, name='ai_check_decision'),
]
