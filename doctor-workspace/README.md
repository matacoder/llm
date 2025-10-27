# Рабочее место врача - Django приложение

Эмулятор рабочего места врача с AI-поддержкой принятия решений на базе клинических рекомендаций.

## Возможности

- Управление картами пациентов (ФИО, дата рождения, СНИЛС, полис ОМС)
- Создание медицинских записей приемов
- Заполнение стандартной формы медицинской карты РФ:
  - Жалобы
  - Анамнез заболевания и жизни
  - Объективный осмотр (витальные показатели)
  - Диагноз по МКБ-10
  - План обследования
  - План лечения и назначения
  - Рекомендации пациенту

- **AI-поддержка принятия решения:**
  - Проверка соответствия диагноза клиническим рекомендациям
  - Валидация плана обследования
  - Проверка назначений и лечения
  - Ссылки на источники (клинические рекомендации)

## Архитектура

- **Frontend:** Django Templates + Bootstrap 5
- **Backend:** Django 5.1
- **AI:** Open WebUI API + RAG (векторная база с клиническими рекомендациями)
- **База данных:** SQLite (для разработки)

## Быстрый старт

### 1. Запуск через Docker Compose

```bash
# Из корневой директории проекта
cd /media/denis/Games\ I2/Dev/llm

# Собрать и запустить все сервисы
docker compose up -d

# Django приложение будет доступно на http://localhost:8000
```

### 2. Создание суперпользователя

```bash
docker compose exec doctor-workspace python manage.py createsuperuser
```

Введите:
- Username: admin
- Email: admin@example.com
- Password: (ваш пароль)

### 3. Вход в систему

1. Откройте http://localhost:8000
2. Войдите под созданной учетной записью
3. Создайте нового пациента
4. Создайте прием для пациента
5. Заполните медицинскую карту
6. Нажмите "Поддержка принятия решения" для AI-проверки

## Конфигурация

Настройки для Open WebUI API находятся в `.env`:

```bash
OPENWEBUI_API_KEY=your-api-key
OPENWEBUI_KNOWLEDGE_ID=your-knowledge-collection-id
```

## API Open WebUI

Django приложение интегрируется с Open WebUI через REST API:

- **Endpoint:** `http://open-webui:8080/api/chat/completions`
- **Knowledge Collection:** Используется для RAG с клиническими рекомендациями
- **Модель:** qwen2.5:7b (настраивается в `medical/services.py`)

## Структура проекта

```
doctor-workspace/
├── config/              # Настройки Django
│   ├── settings.py
│   └── urls.py
├── medical/             # Основное приложение
│   ├── models.py        # Модели: Doctor, Patient, MedicalRecord
│   ├── forms.py         # Формы для работы с данными
│   ├── views.py         # Views для обработки запросов
│   ├── services.py      # Интеграция с Open WebUI API
│   ├── admin.py         # Настройка админ-панели
│   └── templates/       # HTML шаблоны
├── Dockerfile
└── requirements.txt
```

## Разработка

### Локальный запуск (без Docker)

```bash
cd doctor-workspace

# Создать виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# Установить зависимости
pip install -r requirements.txt

# Применить миграции
python manage.py migrate

# Создать суперпользователя
python manage.py createsuperuser

# Запустить сервер
python manage.py runserver
```

### Создание миграций после изменения моделей

```bash
docker compose exec doctor-workspace python manage.py makemigrations
docker compose exec doctor-workspace python manage.py migrate
```

## Тестовые данные

Для демонстрации можно создать тестовые данные через Django shell:

```bash
docker compose exec doctor-workspace python manage.py shell
```

```python
from medical.models import Patient
from datetime import date

patient = Patient.objects.create(
    last_name="Иванов",
    first_name="Иван",
    middle_name="Иванович",
    birth_date=date(1980, 5, 15),
    gender="M",
    address="г. Москва, ул. Ленина, д. 1",
    phone="+7 (999) 123-45-67",
    snils="123-456-789 00",
    policy_number="1234567890123456"
)
```

## Безопасность

⚠️ Это демонстрационное приложение для разработки:

- `DEBUG = True` - отключите в продакшене
- `SECRET_KEY` - сгенерируйте уникальный ключ для продакшена
- `ALLOWED_HOSTS = ['*']` - укажите конкретные хосты в продакшене
- SQLite - используйте PostgreSQL для продакшена

## Лицензия

MIT
