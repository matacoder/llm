#!/bin/bash

# Скрипт для автоматической проверки и загрузки моделей Ollama

set -e

echo "=== Проверка и установка моделей Ollama ==="

# Ожидаем запуска Ollama (максимум 30 секунд)
echo "Ожидание запуска Ollama..."
for i in {1..30}; do
    if docker exec ollama ollama list > /dev/null 2>&1; then
        echo "✓ Ollama запущен"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "✗ Ollama не запустился за 30 секунд"
        exit 1
    fi
    sleep 1
done

# Функция проверки наличия модели
check_model() {
    local model_name=$1
    docker exec ollama ollama list | grep -q "^$model_name"
}

# Функция загрузки модели
download_model() {
    local model_name=$1
    echo "Загрузка модели $model_name..."
    docker exec ollama ollama pull "$model_name"
    echo "✓ Модель $model_name загружена"
}

# Проверка и загрузка основной модели
echo ""
echo "Проверка основной модели (qwen2.5:7b)..."
if check_model "qwen2.5:7b"; then
    echo "✓ Модель qwen2.5:7b уже установлена"
else
    echo "✗ Модель qwen2.5:7b не найдена"
    download_model "qwen2.5:7b"
fi

# Проверка и загрузка модели для эмбеддингов
echo ""
echo "Проверка модели для документов (nomic-embed-text)..."
if check_model "nomic-embed-text"; then
    echo "✓ Модель nomic-embed-text уже установлена"
else
    echo "✗ Модель nomic-embed-text не найдена"
    download_model "nomic-embed-text:latest"
fi

echo ""
echo "=== Все модели готовы к работе ==="
echo ""
docker exec ollama ollama list
