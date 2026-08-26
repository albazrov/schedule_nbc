#!/bin/bash

# Пути к файлам и папкам
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE}")" && pwd)"
BOT_SCRIPT="bot_schedule_nbc.py"

ENV_NAME=$(basename "$PROJECT_DIR")

# Читаем аргументы: если передан путь вторым параметром, приоритетно разворачиваем структуру там
if [ -n "$2" ]; then
    SHM_DIR="$2"
    EXTRA_ARGS="--shm-dir $2"
    LOG_DIR="$2/logs"
else
    if [ -f "$PROJECT_DIR/config.json" ]; then
        DEFAULT_SHM=$(grep -o '"shm_dir": "[^"]*' "$PROJECT_DIR/config.json" | cut -d'"' -f4)
    fi
    SHM_DIR=${DEFAULT_SHM:-"/dev/shm/schedule_nbc"}
    EXTRA_ARGS=""
    LOG_DIR="/dev/shm/schedule_nbc_tasks/${ENV_NAME}/logs"
fi

LOG_FILE="$LOG_DIR/bot.log"

case "$1" in
    start)
        echo "🚀 Запуск бота..."
        mkdir -p "$LOG_DIR"
        chmod -R 775 "$SHM_DIR" 2>/dev/null || true
        
        if pgrep -f "python3.*$PROJECT_DIR/$BOT_SCRIPT" > /dev/null; then
            echo "⚠️ Бот уже запущен!"
            exit 1
        fi
        
        if [ -f "$PROJECT_DIR/.venv/bin/python3" ]; then
            PYTHON_EXEC="$PROJECT_DIR/.venv/bin/python3"
        elif [ -f "$HOME/.venv/bin/python3" ]; then
            PYTHON_EXEC="$HOME/.venv/bin/python3"
        else
            PYTHON_EXEC="python3"
        fi

        nohup "$PYTHON_EXEC" "$PROJECT_DIR/$BOT_SCRIPT" $EXTRA_ARGS > "$LOG_FILE" 2>&1 &
        
        sleep 1.5
        if pgrep -f "python3.*$PROJECT_DIR/$BOT_SCRIPT" > /dev/null; then
            echo "✅ Бот успешно запущен в фоне."
            echo "📄 Логи пишутся в: $LOG_FILE"
        else
            echo "❌ Ошибка старта! Проверьте логи командой: ./manage.sh logs"
        fi
        ;;
        
    stop)
        echo "🛑 Остановка бота..."
        BOT_PID=$(pgrep -f "python3.*$PROJECT_DIR/$BOT_SCRIPT")
        if [ -n "$BOT_PID" ]; then
            kill $BOT_PID
            echo "✅ Бот успешно остановлен."
        else
            echo "⚠️ Процесс бота не найден."
        fi
        ;;
        
    restart)
        $0 stop
        sleep 1.5
        # ИСПРАВЛЕНО: Пробрасываем второй аргумент ($2) в вызов команды start
        $0 start "$2"
        ;;
        
    status)
        if pgrep -f "python3.*$PROJECT_DIR/$BOT_SCRIPT" > /dev/null; then
            PID=$(pgrep -f "python3.*$PROJECT_DIR/$BOT_SCRIPT" | head -n 1)
            echo "🟢 Бот РАБОТАЕТ (PID: $PID)"
        else
            echo "🔴 Бот ОСТАНОВЛЕН"
        fi
        ;;
        
    logs)
        if [ -f "$LOG_FILE" ]; then
            echo "📋 Вывод логов в реальном времени (нажмите Ctrl+C для выхода):"
            tail -f "$LOG_FILE"
        else
            echo "❌ Файл логов еще не создан. Запустите бота."
        fi
        ;;
        
    clear-logs)
        if [ -f "$LOG_FILE" ]; then
            true > "$LOG_FILE"
            echo "🧹 Лог-файл успешно очищен."
        else
            echo "❌ Лог-файл не найден."
        fi
        ;;
        
    *)
        echo "📋 Использование: $0 {start|stop|restart|status|logs|clear-logs}"
        exit 1
        ;;
esac
exit 0
