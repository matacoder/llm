#!/usr/bin/env python3
"""
Автоматическая синхронизация документов в Open WebUI Knowledge
Следит за папкой с документами и автоматически загружает их в коллекцию
"""
import hashlib
import json
import os
import queue
import threading
import time
import requests
import sqlite3
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Конфигурация из переменных окружения
BASE = os.environ.get("OWUI_BASE_URL", "http://open-webui:8080").rstrip("/")
TOKEN = os.environ.get("OWUI_TOKEN", "")
KNOW_ID = os.environ.get("OWUI_KNOWLEDGE_ID", "")
WATCH_DIR = os.environ.get("WATCH_DIR", "/data/docs")
INCLUDE = tuple(filter(None, map(str.strip, os.environ.get("INCLUDE_GLOBS", "*.pdf,*.docx,*.md,*.txt").split(","))))
EXCLUDE = tuple(filter(None, map(str.strip, os.environ.get("EXCLUDE_GLOBS", "*.tmp,~$*,*.part").split(","))))
CONCURRENCY = int(os.environ.get("CONCURRENCY", "2"))
RETRY_MAX = int(os.environ.get("RETRY_MAX", "5"))
RETRY_BASE = float(os.environ.get("RETRY_BASE_DELAY", "1.0"))

# Путь к базе данных
DB = "/data/state/state.db"
os.makedirs(os.path.dirname(DB) or ".", exist_ok=True)

# Инициализация SQLite для отслеживания загруженных файлов
conn = sqlite3.connect(DB, check_same_thread=False)
conn.execute("""CREATE TABLE IF NOT EXISTS files(
  path TEXT PRIMARY KEY,
  size INTEGER,
  mtime REAL,
  sha256 TEXT,
  uploaded_at REAL,
  owui_file_id TEXT,
  added_to_knowledge INTEGER DEFAULT 0
)""")
conn.commit()

def log(msg, level="INFO"):
    """Простое логирование с временной меткой"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {msg}", flush=True)

def glob_match(path, patterns):
    """Проверка соответствия имени файла паттернам glob"""
    import fnmatch
    name = os.path.basename(path)
    return any(fnmatch.fnmatch(name, p) for p in patterns if p)

def sha256_file(p):
    """Вычисление SHA-256 хеша файла"""
    h = hashlib.sha256()
    try:
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1024*1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        log(f"Ошибка при вычислении хеша {p}: {e}", "ERROR")
        return None

def post_with_retry(url, **kw):
    """HTTP POST с повторными попытками при ошибках"""
    for attempt in range(1, RETRY_MAX + 1):
        try:
            r = requests.post(url, timeout=60, **kw)
            if r.status_code < 400:
                return r
            if r.status_code in (429, 500, 502, 503, 504):
                delay = RETRY_BASE * (2 ** (attempt - 1))
                log(f"Ошибка {r.status_code}, повтор через {delay:.1f}с (попытка {attempt}/{RETRY_MAX})", "WARN")
                log(f"Ответ сервера: {r.text[:500]}", "DEBUG")
                time.sleep(delay)
                continue
            # Возвращаем ответ даже с ошибкой для дальнейшего анализа
            log(f"HTTP {r.status_code} для {url}", "DEBUG")
            log(f"Ответ: {r.text[:500]}", "DEBUG")
            return r
        except requests.exceptions.RequestException as e:
            delay = RETRY_BASE * (2 ** (attempt - 1))
            log(f"Сетевая ошибка: {e}, повтор через {delay:.1f}с (попытка {attempt}/{RETRY_MAX})", "WARN")
            if attempt < RETRY_MAX:
                time.sleep(delay)
            else:
                log(f"Превышено максимальное количество попыток для {url}: {e}", "ERROR")
                return None
    return None

def upload_and_attach(path):
    """Загрузка файла в Open WebUI и прикрепление к коллекции"""
    try:
        if not os.path.exists(path):
            log(f"Файл не существует: {path}", "WARN")
            return

        # Получаем метаданные файла
        st = os.stat(path)
        digest = sha256_file(path)
        if not digest:
            return

        # Проверяем, был ли файл уже загружен
        cur = conn.execute(
            "SELECT sha256, owui_file_id, added_to_knowledge FROM files WHERE path=?",
            (path,)
        ).fetchone()

        if cur and cur[0] == digest and cur[2] == 1:
            log(f"Файл уже загружен и не изменился: {os.path.basename(path)}")
            return

        log(f"Загрузка файла: {os.path.basename(path)} ({st.st_size} байт)")

        # 1) Загрузка файла через API
        with open(path, "rb") as f:
            files = {"file": (os.path.basename(path), f)}
            headers = {"Authorization": f"Bearer {TOKEN}"}
            r = post_with_retry(f"{BASE}/api/v1/files/", headers=headers, files=files)

        if not r:
            log(f"Не удалось загрузить файл {path}", "ERROR")
            return

        if r.status_code >= 400:
            if r.status_code == 400 and "Duplicate" in r.text:
                log(f"Файл уже существует в системе: {os.path.basename(path)}", "INFO")
                file_id = None
            else:
                log(f"Ошибка при загрузке файла {path}: {r.status_code} {r.text}", "ERROR")
                return
        else:
            try:
                data = r.json()
                file_id = data.get("id") or data.get("data", {}).get("id")
                api_hash = data.get("hash") or data.get("data", {}).get("hash")
                log(f"Файл загружен, ID: {file_id}, API hash: {api_hash if api_hash else 'N/A'}")
            except Exception as e:
                log(f"Ошибка при разборе ответа API: {e}", "ERROR")
                return

        # 2) Прикрепление файла к коллекции Knowledge
        if file_id and KNOW_ID:
            # Используем блокировку для предотвращения race conditions с cleanup
            with collection_lock:
                # Сначала получаем текущий список файлов в коллекции
                get_url = f"{BASE}/api/v1/knowledge/{KNOW_ID}"
                r_get = requests.get(get_url, headers=headers, timeout=30)

                if r_get.status_code != 200:
                    log(f"Не удалось получить информацию о коллекции: {r_get.status_code}", "ERROR")
                    log(f"Ответ: {r_get.text[:500]}", "ERROR")
                    return

                knowledge_data = r_get.json()
                current_file_ids = knowledge_data.get("data", {}).get("file_ids", [])

                # Используем set для уникальности и избежания дубликатов
                current_file_ids_set = set(current_file_ids) if current_file_ids else set()

                # Проверяем, есть ли уже этот файл в коллекции
                if file_id in current_file_ids_set:
                    log(f"Файл уже есть в коллекции: {os.path.basename(path)}", "INFO")
                else:
                    # Добавляем новый file_id в set, затем конвертируем обратно в list
                    current_file_ids_set.add(file_id)
                    current_file_ids = list(current_file_ids_set)

                    # Обновляем коллекцию
                    update_url = f"{BASE}/api/v1/knowledge/{KNOW_ID}/update"
                    body = {
                        "name": knowledge_data.get("name"),
                        "description": knowledge_data.get("description", ""),
                        "data": {"file_ids": current_file_ids}
                    }

                    log(f"Прикрепление к коллекции через update endpoint", "DEBUG")

                    r2 = post_with_retry(
                        update_url,
                        headers={**headers, "Content-Type": "application/json"},
                        data=json.dumps(body)
                    )

                    if not r2:
                        log(f"Не удалось прикрепить файл к коллекции (нет ответа от API)", "ERROR")
                        # Сохраняем file_id для повторной попытки позже
                        conn.execute("""INSERT INTO files(path,size,mtime,sha256,uploaded_at,owui_file_id,added_to_knowledge)
                                        VALUES(?,?,?,?,strftime('%s','now'),?,0)
                                        ON CONFLICT(path) DO UPDATE SET
                                          size=excluded.size, mtime=excluded.mtime, sha256=excluded.sha256,
                                          uploaded_at=excluded.uploaded_at, owui_file_id=excluded.owui_file_id,
                                          added_to_knowledge=0""",
                                     (path, st.st_size, st.st_mtime, digest, file_id))
                        conn.commit()
                        return

                    if r2.status_code >= 400:
                        log(f"Ошибка при обновлении коллекции: {r2.status_code}", "ERROR")
                        log(f"Ответ API: {r2.text[:1000]}", "ERROR")
                        return
                    else:
                        log(f"Файл успешно добавлен в коллекцию: {os.path.basename(path)}", "INFO")

        # Сохраняем информацию о файле в БД
        conn.execute("""INSERT INTO files(path,size,mtime,sha256,uploaded_at,owui_file_id,added_to_knowledge)
                        VALUES(?,?,?,?,strftime('%s','now'),?,1)
                        ON CONFLICT(path) DO UPDATE SET
                          size=excluded.size, mtime=excluded.mtime, sha256=excluded.sha256,
                          uploaded_at=excluded.uploaded_at, owui_file_id=COALESCE(excluded.owui_file_id, owui_file_id),
                          added_to_knowledge=1""",
                     (path, st.st_size, st.st_mtime, digest, file_id))
        conn.commit()

    except Exception as e:
        log(f"Неожиданная ошибка при обработке {path}: {e}", "ERROR")

# Очередь для обработки файлов
q = queue.Queue()

# Блокировка для операций с коллекцией (предотвращение race conditions)
collection_lock = threading.Lock()

class DocumentEventHandler(FileSystemEventHandler):
    """Обработчик событий файловой системы"""

    def __init__(self):
        super().__init__()
        self.last_events = {}  # path -> timestamp
        self.debounce_seconds = 2.0  # Минимальная задержка между обработками одного файла

    def on_created(self, event):
        """Обработка создания файла"""
        if event.is_directory:
            return
        self._handle_file_event(event.src_path)

    def on_modified(self, event):
        """Обработка изменения файла"""
        if event.is_directory:
            return
        self._handle_file_event(event.src_path)

    def on_moved(self, event):
        """Обработка перемещения файла"""
        if event.is_directory:
            return
        self._handle_file_event(event.dest_path)

    def _handle_file_event(self, path):
        """Обработка события файла с debounce"""
        # Проверка фильтров
        if EXCLUDE and glob_match(path, EXCLUDE):
            return
        if INCLUDE and not glob_match(path, INCLUDE):
            return

        # Debounce - пропускаем если файл обрабатывался недавно
        now = time.time()
        last_time = self.last_events.get(path, 0)

        if now - last_time < self.debounce_seconds:
            return  # Слишком рано, пропускаем

        self.last_events[path] = now

        # Ждём чтобы файл точно закончил записываться
        time.sleep(0.5)

        log(f"Обнаружено изменение: {os.path.basename(path)}")
        q.put(path)

def worker():
    """Рабочий поток для обработки очереди файлов"""
    while True:
        p = q.get()
        try:
            if os.path.exists(p):
                upload_and_attach(p)
        except Exception as e:
            log(f"Ошибка в worker для {p}: {e}", "ERROR")
        finally:
            q.task_done()

def get_local_files():
    """Получить список локальных файлов с их хешами"""
    local_files = {}

    for root, dirs, files in os.walk(WATCH_DIR):
        for name in files:
            p = os.path.join(root, name)

            # Проверка фильтров
            if EXCLUDE and glob_match(p, EXCLUDE):
                continue
            if INCLUDE and not glob_match(p, INCLUDE):
                continue

            # Вычисляем хеш файла
            digest = sha256_file(p)
            if digest:
                local_files[p] = {
                    'path': p,
                    'name': os.path.basename(p),
                    'sha256': digest
                }

    return local_files

def get_collection_files():
    """Получить список файлов из коллекции Knowledge"""
    if not KNOW_ID or not TOKEN:
        return {}

    try:
        headers = {"Authorization": f"Bearer {TOKEN}"}
        get_url = f"{BASE}/api/v1/knowledge/{KNOW_ID}"
        r = requests.get(get_url, headers=headers, timeout=30)

        if r.status_code != 200:
            log(f"Не удалось получить список файлов из коллекции: {r.status_code}", "ERROR")
            return {}

        knowledge_data = r.json()
        files = knowledge_data.get("files", [])

        # Создаем словарь: file_id -> file_info
        collection_files = {}
        for f in files:
            file_id = f.get("id")
            file_hash = f.get("hash")
            file_name = f.get("meta", {}).get("name", "")

            if file_id:
                collection_files[file_id] = {
                    'id': file_id,
                    'hash': file_hash,
                    'name': file_name
                }

        return collection_files

    except Exception as e:
        log(f"Ошибка при получении списка файлов из коллекции: {e}", "ERROR")
        return {}

def cleanup_deleted_files():
    """Удалить из коллекции файлы, которых нет локально"""
    if not KNOW_ID or not TOKEN:
        return

    # Используем блокировку для предотвращения race condition с upload_and_attach
    with collection_lock:
        try:
            log("Проверка на удаленные файлы...", "DEBUG")

            # Получаем локальные файлы
            local_files = get_local_files()
            local_paths = set(local_files.keys())

            # Получаем file_id'ы из нашей БД для локальных файлов
            # Это файлы, которые МЫ загрузили и которые существуют локально
            cursor = conn.execute("""
                SELECT owui_file_id, path
                FROM files
                WHERE added_to_knowledge = 1 AND owui_file_id IS NOT NULL
            """)
            our_file_ids = {}
            for row in cursor.fetchall():
                file_id, path = row
                # Проверяем, существует ли файл локально
                if path in local_paths:
                    our_file_ids[file_id] = path

            # Получаем файлы из коллекции
            collection_files = get_collection_files()

            if not collection_files:
                log("Коллекция пуста или недоступна", "DEBUG")
                return

            # Находим файлы, которые есть в коллекции, но не должны там быть
            files_to_remove = []
            for file_id, file_info in collection_files.items():
                file_name = file_info['name']

                # Если этот file_id НЕ в нашей БД или файл не существует локально
                if file_id not in our_file_ids:
                    files_to_remove.append(file_id)
                    log(f"Файл для удаления из коллекции: {file_name} (не отслеживается или удален локально)", "INFO")

            if not files_to_remove:
                log("Нет файлов для удаления", "DEBUG")
                return

            log(f"Найдено {len(files_to_remove)} файл(ов) для удаления из коллекции", "INFO")

            # Получаем текущий список file_ids
            headers = {"Authorization": f"Bearer {TOKEN}"}
            get_url = f"{BASE}/api/v1/knowledge/{KNOW_ID}"
            r = requests.get(get_url, headers=headers, timeout=30)

            if r.status_code != 200:
                log(f"Не удалось получить коллекцию для обновления: {r.status_code}", "ERROR")
                return

            knowledge_data = r.json()
            current_file_ids = knowledge_data.get("data", {}).get("file_ids", [])

            # Удаляем файлы из списка
            updated_file_ids = [fid for fid in current_file_ids if fid not in files_to_remove]

            # Обновляем коллекцию
            update_url = f"{BASE}/api/v1/knowledge/{KNOW_ID}/update"
            body = {
                "name": knowledge_data.get("name"),
                "description": knowledge_data.get("description", ""),
                "data": {"file_ids": updated_file_ids}
            }

            r2 = post_with_retry(
                update_url,
                headers={**headers, "Content-Type": "application/json"},
                data=json.dumps(body)
            )

            if not r2 or r2.status_code >= 400:
                log(f"Не удалось обновить коллекцию после удаления: {r2.status_code if r2 else 'no response'}", "ERROR")
                return

            # Удаляем записи из SQLite
            for file_id in files_to_remove:
                file_name = collection_files[file_id]['name']
                conn.execute("DELETE FROM files WHERE owui_file_id=?", (file_id,))
                log(f"Удален из коллекции: {file_name}", "INFO")

            conn.commit()
            log(f"Успешно удалено {len(files_to_remove)} файл(ов) из коллекции", "INFO")

        except Exception as e:
            log(f"Ошибка при очистке удаленных файлов: {e}", "ERROR")

def reconcile_missing_files():
    """
    Инвентаризация: находит локальные файлы, которые отсутствуют в коллекции,
    и загружает их. Полезно для восстановления после сбоев или race conditions.
    """
    if not KNOW_ID or not TOKEN:
        return

    try:
        log("Инвентаризация: проверка отсутствующих файлов в коллекции...", "DEBUG")

        # Получаем локальные файлы
        local_files = get_local_files()
        if not local_files:
            log("Нет локальных файлов для инвентаризации", "DEBUG")
            return

        # Получаем file_id'ы из коллекции
        collection_files = get_collection_files()
        collection_file_ids = set(collection_files.keys())

        # Находим файлы, которые есть локально, но отсутствуют в коллекции
        files_to_upload = []
        for path in local_files.keys():
            # Проверяем, есть ли запись в БД для этого файла
            cursor = conn.execute("""
                SELECT owui_file_id, added_to_knowledge
                FROM files
                WHERE path = ?
            """, (path,))
            row = cursor.fetchone()

            if not row:
                # Файл не загружался никогда
                log(f"Файл не был загружен: {os.path.basename(path)}", "INFO")
                files_to_upload.append(path)
            else:
                file_id, added_to_knowledge = row
                if added_to_knowledge == 1 and file_id:
                    # Мы его загружали и добавляли в коллекцию
                    if file_id not in collection_file_ids:
                        # Но его нет в коллекции - восстанавливаем
                        log(f"Файл отсутствует в коллекции (восстановление): {os.path.basename(path)}", "WARNING")
                        files_to_upload.append(path)
                else:
                    # Загружали, но не добавили в коллекцию
                    log(f"Файл не был добавлен в коллекцию: {os.path.basename(path)}", "INFO")
                    files_to_upload.append(path)

        if not files_to_upload:
            log("Все локальные файлы присутствуют в коллекции", "DEBUG")
            return

        log(f"Найдено {len(files_to_upload)} файл(ов) для загрузки в коллекцию", "INFO")

        # Добавляем файлы в очередь на загрузку (используем существующий механизм)
        for path in files_to_upload:
            q.put(path)

    except Exception as e:
        log(f"Ошибка при инвентаризации файлов: {e}", "ERROR")

def cleanup_worker():
    """Периодический запуск очистки удаленных файлов и инвентаризации"""
    cleanup_interval = int(os.environ.get("CLEANUP_INTERVAL", "300"))  # 5 минут по умолчанию

    while True:
        try:
            time.sleep(cleanup_interval)
            log("=== Начало периодической синхронизации ===", "INFO")

            # Сначала удаляем файлы, которых нет локально
            cleanup_deleted_files()

            # Затем добавляем файлы, которые есть локально, но отсутствуют в коллекции
            reconcile_missing_files()

            log("=== Периодическая синхронизация завершена ===", "INFO")
        except Exception as e:
            log(f"Ошибка в cleanup_worker: {e}", "ERROR")

def main():
    """Основная функция"""
    log("=== Запуск синхронизации документов ===")
    log(f"Open WebUI URL: {BASE}")
    log(f"Папка для отслеживания: {WATCH_DIR}")
    log(f"Фильтры INCLUDE: {INCLUDE}")
    log(f"Фильтры EXCLUDE: {EXCLUDE}")

    # Проверка конфигурации
    if not TOKEN:
        log("ОШИБКА: не установлена переменная OWUI_TOKEN", "ERROR")
        sys.exit(1)

    if not KNOW_ID:
        log("ПРЕДУПРЕЖДЕНИЕ: не установлена переменная OWUI_KNOWLEDGE_ID", "WARN")
        log("Файлы будут загружаться, но не будут прикрепляться к коллекции", "WARN")

    if not os.path.exists(WATCH_DIR):
        log(f"ОШИБКА: папка {WATCH_DIR} не существует", "ERROR")
        sys.exit(1)

    # Запуск рабочих потоков
    log(f"Запуск {CONCURRENCY} рабочих потоков")
    for _ in range(CONCURRENCY):
        threading.Thread(target=worker, daemon=True).start()

    # Запуск потока периодической очистки
    cleanup_interval = int(os.environ.get("CLEANUP_INTERVAL", "300"))
    log(f"Запуск потока очистки (интервал: {cleanup_interval}с)")
    threading.Thread(target=cleanup_worker, daemon=True).start()

    # Первичная синхронизация существующих файлов
    log("Выполнение первичной синхронизации существующих файлов...")
    for root, dirs, files in os.walk(WATCH_DIR):
        for name in files:
            p = os.path.join(root, name)
            if EXCLUDE and glob_match(p, EXCLUDE):
                continue
            if INCLUDE and not glob_match(p, INCLUDE):
                continue
            q.put(p)

    # Ждем завершения первичной синхронизации
    q.join()

    # Первичная очистка удаленных файлов
    log("Выполнение первичной очистки удаленных файлов из коллекции...")
    cleanup_deleted_files()

    # Проверка и восстановление отсутствующих файлов
    log("Проверка наличия всех локальных файлов в коллекции...")
    reconcile_missing_files()

    # Запуск наблюдателя за файловой системой
    log("Запуск наблюдателя за изменениями файлов...")
    observer = Observer()
    observer.schedule(DocumentEventHandler(), WATCH_DIR, recursive=True)
    observer.start()

    log("Синхронизация запущена. Нажмите Ctrl+C для остановки.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log("Получен сигнал остановки, завершение работы...")
        observer.stop()

    observer.join()
    log("Синхронизация остановлена")

if __name__ == "__main__":
    main()
