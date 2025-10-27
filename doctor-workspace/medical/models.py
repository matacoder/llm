from django.db import models
from django.contrib.auth.models import User


class Doctor(models.Model):
    """Модель врача"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='doctor_profile')
    full_name = models.CharField(max_length=200, verbose_name='ФИО')
    specialty = models.CharField(max_length=100, verbose_name='Специальность')
    license_number = models.CharField(max_length=50, verbose_name='Номер лицензии', unique=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Врач'
        verbose_name_plural = 'Врачи'

    def __str__(self):
        return f"{self.full_name} ({self.specialty})"


class Patient(models.Model):
    """Модель пациента"""
    GENDER_CHOICES = [
        ('M', 'Мужской'),
        ('F', 'Женский'),
    ]

    last_name = models.CharField(max_length=100, verbose_name='Фамилия')
    first_name = models.CharField(max_length=100, verbose_name='Имя')
    middle_name = models.CharField(max_length=100, verbose_name='Отчество', blank=True)

    birth_date = models.DateField(verbose_name='Дата рождения')
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, verbose_name='Пол')

    address = models.TextField(verbose_name='Адрес регистрации')
    phone = models.CharField(max_length=20, verbose_name='Телефон')
    snils = models.CharField(max_length=14, verbose_name='СНИЛС', unique=True)
    policy_number = models.CharField(max_length=16, verbose_name='Номер полиса ОМС')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Пациент'
        verbose_name_plural = 'Пациенты'
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.last_name} {self.first_name} {self.middle_name}"

    @property
    def full_name(self):
        return f"{self.last_name} {self.first_name} {self.middle_name}".strip()


class MedicalRecord(models.Model):
    """Модель медицинской карты / записи приема"""

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='medical_records')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='medical_records')

    # Дата и время приема
    visit_date = models.DateTimeField(verbose_name='Дата и время приема')

    # Основная часть медкарты (согласно стандарту РФ)
    complaints = models.TextField(verbose_name='Жалобы', help_text='Описание текущих симптомов')
    anamnesis = models.TextField(verbose_name='Анамнез заболевания', help_text='История текущего заболевания')
    anamnesis_vitae = models.TextField(verbose_name='Анамнез жизни', blank=True, help_text='Общая история здоровья')

    # Объективный осмотр
    objective_status = models.TextField(verbose_name='Объективный статус', help_text='Данные физикального осмотра')

    # Витальные показатели
    temperature = models.DecimalField(max_digits=4, decimal_places=1, verbose_name='Температура (°C)', null=True, blank=True)
    blood_pressure = models.CharField(max_length=10, verbose_name='АД (мм рт.ст.)', blank=True, help_text='Например: 120/80')
    pulse = models.IntegerField(verbose_name='Пульс (уд/мин)', null=True, blank=True)
    respiratory_rate = models.IntegerField(verbose_name='ЧДД (в мин)', null=True, blank=True)

    # Диагноз
    preliminary_diagnosis = models.CharField(max_length=200, verbose_name='Предварительный диагноз')
    icd10_code = models.CharField(max_length=10, verbose_name='Код по МКБ-10', help_text='Например: J06.9')
    final_diagnosis = models.CharField(max_length=200, verbose_name='Окончательный диагноз', blank=True)

    # План обследования и лечения
    examination_plan = models.TextField(verbose_name='План обследования', help_text='Назначенные анализы и исследования')
    treatment_plan = models.TextField(verbose_name='План лечения', help_text='Назначения, рекомендации')
    prescriptions = models.TextField(verbose_name='Рецепты/Назначения', blank=True)

    # Рекомендации
    recommendations = models.TextField(verbose_name='Рекомендации пациенту', blank=True)

    # AI-проверка
    ai_check_performed = models.BooleanField(default=False, verbose_name='Проверка AI выполнена')
    ai_check_result = models.TextField(verbose_name='Результат проверки AI', blank=True)
    ai_check_timestamp = models.DateTimeField(verbose_name='Время проверки AI', null=True, blank=True)

    # Служебные поля
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Медицинская карта'
        verbose_name_plural = 'Медицинские карты'
        ordering = ['-visit_date']

    def __str__(self):
        return f"Прием {self.patient.full_name} от {self.visit_date.strftime('%d.%m.%Y')}"
