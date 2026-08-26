#!/bin/bash

# Пути к файлам и папкам
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE}")" && pwd)"
BOT_SCRIPT="bot_schedule_nbc.py"

ENV_NAME=$(basename "$PROJECT_DIR")

# Определяем бинарник Python с проверкой прав на выполнение (-x)
if [ -x "$PROJECT_DIR/.venv/bin/python3" ]; then
    PYTHON_EXEC="$PROJECT_DIR/.venv/bin/python3"
elif [ -x "$HOME/.venv/bin/python3" ]; then
    PYTHON_EXEC="$HOME/.venv/bin/python3"
else
    PYTHON_EXEC="python3"
fi

# УНИВЕРСАЛЬНОЕ И БЕЗОПАСНОЕ ОПРЕДЕЛЕНИЕ ПУТИ:
# Если передан $2 — берем его. Если нет — парсим config.json напрямую через быстрый однострочник Python.
if [ -n "$2" ]; then
    SHM_DIR="$2"
    EXTRA_ARGS="--shm-dir $2"
else
    if [ -f "$PROJECT_DIR/config.json" ]; then
        SHM_DIR=$("$PYTHON_EXEC" -c "import json; print(json.load(open('$PROJECT_DIR/config.json')).get('files', {}).get('shm_dir', '/dev/shm/schedule_nbc'))" 2>/dev/null)
    fi
    SHM_DIR=${SHM_DIR:-"/dev/shm/schedule_nbc"}
    EXTRA_ARGS=""
fi

LOG_FILE="$SHM_DIR/bot_schedule_nbc.log"

case "$1" in
    start)
        echo "🚀 Запуск бота ($ENV_NAME)..."
        mkdir -p "$SHM_DIR"
        chmod 775 "$SHM_DIR" 2>/dev/null || true
        
        if pgrep -f "python3.*$PROJECT_DIR/$BOT_SCRIPT" > /dev/null; then
            echo "⚠️ Бот уже запущен!"
            exit 1
        fi

        # old # nohup "$PYTHON_EXEC" "$PROJECT_DIR/$BOT_SCRIPT" $EXTRA_ARGS > "$LOG_FILE" 2>&1 &
        # Переменная PYTHONUNBUFFERED=1 заставляет Python мгновенно писать логи на диск
        #env PYTHONUNBUFFERED=1 nohup "$PYTHON_EXEC" "$PROJECT_DIR/$BOT_SCRIPT" $EXTRA_ARGS > "$LOG_FILE" 2>&1 &
	nohup "$PYTHON_EXEC" -u "$PROJECT_DIR/$BOT_SCRIPT" $EXTRA_ARGS > "$LOG_FILE" 2>&1 &
        
        sleep 1.5
        if pgrep -f "python3.*$PROJECT_DIR/$BOT_SCRIPT" > /dev/null; then
            echo "✅ Бот успешно запущен в фоне."
            echo "📄 Логи пишутся в: $LOG_FILE"
        else
            echo "❌ Ошибка старта! Проверьте логи командой: ./manage.sh logs"
        fi
        ;;
        
    stop)
        echo "🛑 Остановка бота ($ENV_NAME)..."
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
        $0 start "$2"
        ;;
        
    status)
        if pgrep -f "python3.*$PROJECT_DIR/$BOT_SCRIPT" > /dev/null; then
            PID=$(pgrep -f "python3.*$PROJECT_DIR/$BOT_SCRIPT" | head -n 1)
            echo "🟢 Бот РАБОТАЕТ (PID: $PID) [$ENV_NAME]"
            echo "📊 Активный RAM-диск: $SHM_DIR"
        else
            echo "🔴 Бот ОСТАНОВЛЕН [$ENV_NAME]"
        fi
        ;;
        
    logs)
        if [ -f "$LOG_FILE" ]; then
            echo "📋 Вывод логов в реальном времени (нажмите Ctrl+C для выхода) [$ENV_NAME]:"
            tail -f "$LOG_FILE"
        else
            echo "❌ Файл логов еще не создан по пути: $LOG_FILE"
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
