from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from datetime import datetime
import json

from .models import Patient, MedicalRecord, Doctor
from .forms import PatientForm, MedicalRecordForm
from .services import openwebui_service


@login_required
def dashboard(request):
    """Главная страница - список пациентов"""
    patients = Patient.objects.all().order_by('-created_at')[:50]
    return render(request, 'medical/dashboard.html', {
        'patients': patients
    })


@login_required
def patient_list(request):
    """Список всех пациентов"""
    patients = Patient.objects.all()
    return render(request, 'medical/patient_list.html', {
        'patients': patients
    })


@login_required
def records_table(request):
    """Таблица всех медицинских записей"""
    records = MedicalRecord.objects.select_related('patient', 'doctor').all().order_by('-visit_date')

    # Статистика
    total_records = records.count()
    checked_records = records.filter(ai_check_performed=True).count()
    unique_patients = records.values('patient').distinct().count()

    return render(request, 'medical/records_table.html', {
        'records': records,
        'total_records': total_records,
        'checked_records': checked_records,
        'unique_patients': unique_patients,
    })


@login_required
def patient_detail(request, patient_id):
    """Карточка пациента с историей болезни"""
    patient = get_object_or_404(Patient, id=patient_id)
    medical_records = patient.medical_records.all().order_by('-visit_date')

    return render(request, 'medical/patient_detail.html', {
        'patient': patient,
        'medical_records': medical_records
    })


@login_required
def patient_create(request):
    """Создание нового пациента"""
    if request.method == 'POST':
        form = PatientForm(request.POST)
        if form.is_valid():
            patient = form.save()
            messages.success(request, f'Пациент {patient.full_name} успешно создан')
            return redirect('patient_detail', patient_id=patient.id)
    else:
        form = PatientForm()

    return render(request, 'medical/patient_form.html', {
        'form': form,
        'title': 'Новый пациент'
    })


@login_required
def patient_update(request, patient_id):
    """Редактирование пациента"""
    patient = get_object_or_404(Patient, id=patient_id)

    if request.method == 'POST':
        form = PatientForm(request.POST, instance=patient)
        if form.is_valid():
            patient = form.save()
            messages.success(request, f'Данные пациента {patient.full_name} обновлены')
            return redirect('patient_detail', patient_id=patient.id)
    else:
        form = PatientForm(instance=patient)

    return render(request, 'medical/patient_form.html', {
        'form': form,
        'patient': patient,
        'title': f'Редактирование: {patient.full_name}'
    })


@login_required
def medical_record_create(request, patient_id):
    """Создание новой медицинской карты для пациента"""
    patient = get_object_or_404(Patient, id=patient_id)

    # Получаем или создаем профиль врача для текущего пользователя
    doctor, created = Doctor.objects.get_or_create(
        user=request.user,
        defaults={
            'full_name': request.user.get_full_name() or request.user.username,
            'specialty': 'Терапевт',
            'license_number': f'TMP-{request.user.id}'
        }
    )

    if request.method == 'POST':
        form = MedicalRecordForm(request.POST, doctor=doctor)
        if form.is_valid():
            medical_record = form.save()
            messages.success(request, 'Медицинская карта успешно создана')
            return redirect('medical_record_detail', record_id=medical_record.id)
    else:
        # Устанавливаем начальные значения
        initial = {
            'patient': patient,
            'visit_date': timezone.now()
        }
        form = MedicalRecordForm(initial=initial, doctor=doctor)

    return render(request, 'medical/medical_record_form.html', {
        'form': form,
        'patient': patient,
        'title': f'Новый прием: {patient.full_name}'
    })


@login_required
def medical_record_detail(request, record_id):
    """Просмотр медицинской карты"""
    medical_record = get_object_or_404(MedicalRecord, id=record_id)

    return render(request, 'medical/medical_record_detail.html', {
        'record': medical_record
    })


@login_required
def medical_record_update(request, record_id):
    """Редактирование медицинской карты"""
    medical_record = get_object_or_404(MedicalRecord, id=record_id)

    if request.method == 'POST':
        form = MedicalRecordForm(request.POST, instance=medical_record)
        if form.is_valid():
            medical_record = form.save()
            messages.success(request, 'Медицинская карта обновлена')
            return redirect('medical_record_detail', record_id=medical_record.id)
    else:
        form = MedicalRecordForm(instance=medical_record)

    return render(request, 'medical/medical_record_form.html', {
        'form': form,
        'patient': medical_record.patient,
        'record': medical_record,
        'title': f'Редактирование приема от {medical_record.visit_date.strftime("%d.%m.%Y")}'
    })


@login_required
@require_http_methods(["POST"])
def ai_check_decision(request, record_id):
    """
    Стриминг проверки медицинского заключения через AI
    """
    medical_record = get_object_or_404(MedicalRecord, id=record_id)

    def stream_response():
        """Генератор для стриминга ответа"""
        full_response = []

        try:
            # Стримим токены от AI
            for token in openwebui_service.stream_check_medical_decision(medical_record):
                full_response.append(token)
                # Отправляем каждый токен клиенту
                yield f"data: {json.dumps({'token': token})}\n\n"

            # Когда стриминг завершен, сохраняем результат
            final_result = ''.join(full_response)
            medical_record.ai_check_performed = True
            medical_record.ai_check_result = final_result
            medical_record.ai_check_timestamp = timezone.now()
            medical_record.save()

            # Отправляем сигнал завершения
            yield f"data: {json.dumps({'done': True})}\n\n"

        except Exception as e:
            # В случае ошибки отправляем сообщение об ошибке
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    response = StreamingHttpResponse(stream_response(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'  # Отключаем буферизацию для nginx
    return response
