#!/bin/bash
# Скрипт для остановки локальной LLM системы

echo "🛑 Остановка локальной LLM системы..."
echo ""

docker compose stop

echo ""
echo "✅ Система остановлена!"
echo ""
echo "💡 Для перезапуска используйте: ./start.sh"
echo "🗑️  Для полного удаления: docker compose down"
