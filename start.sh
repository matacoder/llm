#!/bin/bash
# Скрипт для запуска локальной LLM системы

echo "🚀 Запуск локальной LLM системы..."
echo ""

# Проверка Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен!"
    exit 1
fi

# Проверка NVIDIA GPU
if ! nvidia-smi &> /dev/null; then
    echo "⚠️  Предупреждение: nvidia-smi не найден. GPU может не работать."
fi

# Запуск контейнеров
echo "📦 Запуск контейнеров Docker..."
docker compose up -d

# Ожидание запуска
echo ""
echo "⏳ Ожидание запуска сервисов..."
sleep 5

# Проверка статуса
echo ""
echo "📊 Статус сервисов:"
docker compose ps

# Автоматическая проверка и загрузка моделей
echo ""
./setup-models.sh

echo ""
echo "✅ Система полностью готова к работе!"
echo ""
echo "🌐 Доступ к интерфейсу: http://localhost:3000"
echo ""
echo "📝 Следующие шаги:"
echo "   1. Откройте http://localhost:3000 в браузере"
echo "   2. Создайте учетную запись (если первый запуск)"
echo "   3. Выберите модель qwen2.5:7b в выпадающем списке"
echo "   4. Начните работу!"
echo ""
echo "💡 Полезные команды:"
echo "   🔍 Мониторинг GPU: watch -n 1 nvidia-smi"
echo "   📋 Логи: docker compose logs -f"
echo "   📖 Инструкция: README.md"
