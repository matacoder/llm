"""
Сервис для интеграции с Open WebUI API
"""
import requests
from django.conf import settings
from typing import Dict, Any, Generator
import logging
import json
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# Путь к файлу с промптом
PROMPT_FILE = Path(settings.BASE_DIR) / 'prompt.md'


class OpenWebUIService:
    """Класс для работы с Open WebUI API"""

    def __init__(self):
        self.api_url = settings.OPENWEBUI_API_URL
        self.api_key = settings.OPENWEBUI_API_KEY
        self.knowledge_id = settings.OPENWEBUI_KNOWLEDGE_ID

    def check_medical_decision(self, medical_record) -> Dict[str, Any]:
        """
        Проверяет медицинское заключение на соответствие клиническим рекомендациям

        Args:
            medical_record: Объект MedicalRecord

        Returns:
            Dict с результатами проверки:
            {
                'success': bool,
                'result': str,  # Результат проверки от AI
                'error': str,   # Сообщение об ошибке (если есть)
            }
        """

        # Формируем промпт для AI
        prompt = self._build_prompt(medical_record)

        # Отправляем запрос к Open WebUI
        try:
            response = self._send_request(prompt)
            return {
                'success': True,
                'result': response,
                'error': None
            }
        except Exception as e:
            logger.error(f"Ошибка при обращении к Open WebUI API: {str(e)}")
            return {
                'success': False,
                'result': None,
                'error': str(e)
            }

    def _build_prompt(self, medical_record) -> str:
        """Формирует промпт для проверки медицинского заключения"""

        # Читаем шаблон промпта из файла
        try:
            with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
                prompt_template = f.read()
        except FileNotFoundError:
            logger.warning(f"Файл промпта не найден: {PROMPT_FILE}, использую дефолтный")
            prompt_template = "Проверь медицинское заключение:\n{age} лет, {gender}\n{complaints}\n{diagnosis}"

        # Подставляем данные в шаблон (без ФИО для анонимности)
        prompt = prompt_template.format(
            age=self._calculate_age(medical_record.patient.birth_date),
            gender=medical_record.patient.get_gender_display(),
            complaints=medical_record.complaints,
            anamnesis=medical_record.anamnesis,
            objective_status=medical_record.objective_status,
            temperature=medical_record.temperature,
            blood_pressure=medical_record.blood_pressure,
            pulse=medical_record.pulse,
            respiratory_rate=medical_record.respiratory_rate,
            diagnosis=medical_record.preliminary_diagnosis,
            icd10_code=medical_record.icd10_code,
            examination_plan=medical_record.examination_plan,
            treatment_plan=medical_record.treatment_plan,
            prescriptions=medical_record.prescriptions
        )

        return prompt

    def _calculate_age(self, birth_date) -> int:
        """Вычисляет возраст по дате рождения"""
        from datetime import date
        today = date.today()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        return age

    def _send_request(self, prompt: str) -> str:
        """
        Отправляет запрос к Ollama API напрямую

        Args:
            prompt: Текст запроса

        Returns:
            Ответ от AI
        """

        # Используем Ollama API напрямую - надежнее
        ollama_url = "http://ollama:11434/api/generate"

        headers = {
            'Content-Type': 'application/json'
        }

        # Добавляем контекст из Knowledge collection в промпт
        enhanced_prompt = f"""Ты - медицинский ассистент, который помогает врачам проверять соответствие их решений клиническим рекомендациям.

Используй свои знания о медицине и клинических рекомендациях для ответа.

{prompt}"""

        payload = {
            "model": "qwen2.5:7b",
            "prompt": enhanced_prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,  # Более консервативные ответы для медицины
                "num_predict": 2000  # Больше токенов для более детального анализа
            }
        }

        logger.info(f"Отправка запроса к Ollama: {ollama_url}")

        response = requests.post(
            ollama_url,
            headers=headers,
            json=payload,
            timeout=120  # Увеличиваем timeout для длинных ответов
        )

        response.raise_for_status()

        data = response.json()

        # Извлекаем ответ из структуры Ollama
        if 'response' in data:
            return data['response']
        else:
            raise ValueError("Неожиданный формат ответа от Ollama API")

    def stream_check_medical_decision(self, medical_record) -> Generator[str, None, None]:
        """
        Стримит проверку медицинского заключения токен за токеном

        Args:
            medical_record: Объект MedicalRecord

        Yields:
            Токены ответа от AI по мере генерации
        """
        # Формируем промпт для AI
        prompt = self._build_prompt(medical_record)

        # Добавляем контекст
        enhanced_prompt = f"""Ты - медицинский ассистент, который помогает врачам проверять соответствие их решений клиническим рекомендациям.

Используй свои знания о медицине и клинических рекомендациях для ответа.

{prompt}"""

        # Используем Ollama API со стримингом
        ollama_url = "http://ollama:11434/api/generate"

        headers = {
            'Content-Type': 'application/json'
        }

        payload = {
            "model": "gpt-oss:20b",
            "prompt": enhanced_prompt,
            "stream": True,  # Включаем стриминг
            "keep_alive": "10m",  # Держим модель в памяти 10 минут
            "options": {
                "temperature": 0.3,
                "num_predict": -1,  # -1 = генерировать до EOS токена, а не фиксированное количество
                "num_ctx": 2048,  # Контекст для баланса скорости и качества
                "top_p": 0.9,  # Nucleus sampling для более естественного текста
                "repeat_penalty": 1.1  # Предотвращает повторения
            }
        }

        # Логируем с UUID пациента для анонимности
        patient_uuid = medical_record.patient.id
        logger.info(f"Начинаем стриминг запроса к Ollama для пациента UUID={patient_uuid}")
        logger.info(f"Размер промпта: {len(enhanced_prompt)} символов (~{len(enhanced_prompt.split())} слов)")

        try:
            response = requests.post(
                ollama_url,
                headers=headers,
                json=payload,
                stream=True,  # Важно для стриминга
                timeout=300  # Увеличим timeout
            )

            response.raise_for_status()

            # Читаем ответ построчно
            start_time = time.time()
            token_count = 0
            first_token_time = None

            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        if 'response' in data:
                            token = data['response']
                            if token:
                                token_count += 1
                                if first_token_time is None:
                                    first_token_time = time.time()
                                    ttft = first_token_time - start_time  # Time To First Token
                                    logger.info(f"Время до первого токена (TTFT): {ttft:.2f}s")
                                yield token
                    except json.JSONDecodeError:
                        logger.warning(f"Не удалось распарсить строку: {line}")
                        continue

            # Логируем финальную статистику
            total_time = time.time() - start_time
            if token_count > 0 and first_token_time:
                generation_time = time.time() - first_token_time
                tokens_per_second = token_count / generation_time if generation_time > 0 else 0
                logger.info(f"Генерация завершена для UUID={patient_uuid}: {token_count} токенов за {total_time:.2f}s ({tokens_per_second:.1f} токенов/сек)")

        except Exception as e:
            logger.error(f"Ошибка при стриминге от Ollama для UUID={patient_uuid}: {str(e)}")
            yield f"\n\nОшибка: {str(e)}"


# Singleton instance
openwebui_service = OpenWebUIService()
