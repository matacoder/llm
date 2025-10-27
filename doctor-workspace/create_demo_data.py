"""
Скрипт для создания демо-данных
Запуск: docker compose exec doctor-workspace python create_demo_data.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from datetime import datetime, date
from django.contrib.auth.models import User
from medical.models import Doctor, Patient, MedicalRecord

print("Создание демо-данных...")

# Получаем пользователя admin
admin_user = User.objects.get(username='admin')

# Создаем профиль врача для admin
doctor, created = Doctor.objects.get_or_create(
    user=admin_user,
    defaults={
        'full_name': 'Петрова Анна Сергеевна',
        'specialty': 'Терапевт',
        'license_number': 'ЛИЦ-12345-ТЕР'
    }
)
if created:
    print(f"✓ Создан врач: {doctor.full_name}")
else:
    print(f"✓ Врач уже существует: {doctor.full_name}")

# Создаем тестового пациента
patient, created = Patient.objects.get_or_create(
    snils='123-456-789-00',
    defaults={
        'last_name': 'Иванов',
        'first_name': 'Иван',
        'middle_name': 'Иванович',
        'birth_date': date(1980, 5, 15),
        'gender': 'M',
        'address': 'г. Москва, ул. Ленина, д. 10, кв. 25',
        'phone': '+7 (999) 123-45-67',
        'policy_number': '1234567890123456'
    }
)
if created:
    print(f"✓ Создан пациент: {patient.full_name}")
else:
    print(f"✓ Пациент уже существует: {patient.full_name}")

# Создаем медицинскую запись
record, created = MedicalRecord.objects.get_or_create(
    patient=patient,
    doctor=doctor,
    visit_date=datetime(2025, 10, 26, 10, 30),
    defaults={
        'complaints': 'Повышение температуры тела до 38.5°C, боль в горле, слабость, головная боль в течение 2 дней.',

        'anamnesis': '''Заболел остро 2 дня назад, когда появилось першение в горле и субфебрильная температура.
На следующий день температура поднялась до 38.5°C, присоединилась выраженная слабость, головная боль.
Самостоятельно принимал парацетамол 500мг - температура снижалась до 37.5°C на 3-4 часа.
Контакт с больными ОРВИ отрицает.''',

        'anamnesis_vitae': 'Хронические заболевания отрицает. Аллергологический анамнез не отягощен. Операций не было.',

        'objective_status': '''Общее состояние средней тяжести. Кожные покровы обычной окраски, чистые.
Зев гиперемирован, миндалины увеличены, рыхлые, налетов нет.
Периферические лимфоузлы: подчелюстные увеличены до 1 см, безболезненные.
В легких: дыхание везикулярное, хрипов нет. ЧДД 18 в мин.
Сердце: тоны ясные, ритмичные. ЧСС 88 уд/мин. АД 125/80 мм рт.ст.
Живот мягкий, безболезненный.''',

        'temperature': 38.2,
        'blood_pressure': '125/80',
        'pulse': 88,
        'respiratory_rate': 18,

        'preliminary_diagnosis': 'Острая респираторная вирусная инфекция, острый фарингит',
        'icd10_code': 'J06.9',
        'final_diagnosis': '',

        'examination_plan': '''1. Общий анализ крови
2. Общий анализ мочи
3. Экспресс-тест на COVID-19 (по показаниям)
4. Консультация ЛОР-врача при сохранении симптомов > 5 дней''',

        'treatment_plan': '''1. Режим домашний, постельный в период лихорадки
2. Обильное теплое питье до 2-2.5 литров в сутки
3. Парацетамол 500 мг при температуре > 38.5°C, не более 4 раз в сутки
4. Полоскание горла раствором фурацилина 3-4 раза в день
5. Аскорбиновая кислота 500 мг 2 раза в день - 5 дней''',

        'prescriptions': '''Rp: Tab. Paracetamoli 0.5 N 10
D.S. По 1 таблетке при температуре выше 38.5°C, не более 4 раз в сутки

Rp: Acidi ascorbinici 0.5 N 10
D.S. По 1 таблетке 2 раза в день после еды, 5 дней''',

        'recommendations': '''1. Соблюдать постельный режим до нормализации температуры
2. Обильное питье (чай с лимоном, морс, компот)
3. Измерять температуру 3 раза в день, вести дневник
4. При сохранении/усилении симптомов > 3 дней - повторная консультация
5. При температуре > 39.5°C, одышке, боли в груди - вызов скорой помощи
6. Освобождение от работы на 5 дней'''
    }
)

if created:
    print(f"✓ Создана медицинская запись от {record.visit_date.strftime('%d.%m.%Y')}")
else:
    print(f"✓ Медицинская запись уже существует")

print("\n" + "="*60)
print("Демо-данные созданы успешно!")
print("="*60)
print("\n📋 Данные для входа:")
print("   URL: http://localhost:8000")
print("   Username: admin")
print("   Password: admin123")
print("\n📝 Тестовый пациент:")
print(f"   {patient.full_name}")
print(f"   Запись от {record.visit_date.strftime('%d.%m.%Y %H:%M')}")
print("\n💡 Попробуйте:")
print("   1. Войдите в систему")
print("   2. Откройте карточку пациента 'Иванов Иван Иванович'")
print("   3. Откройте медицинскую запись")
print("   4. Нажмите 'Поддержка принятия решения' для AI-проверки")
print("\n" + "="*60)
