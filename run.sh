#!/usr/bin/env bash
# Rundown 赛程/比分：每日未来七天赛程，赛时每分钟比分。
set -euo pipefail
cd "$(dirname "$0")"
VENV=".venv"
PY="$VENV/bin/python"
PIDFILE="rundown.pid"
LOGDIR="logs"

py() { if [ -x "$PY" ]; then echo "$PY"; else echo "python3"; fi; }

case "${1:-}" in
    setup)
        python3 -m venv "$VENV"
        "$PY" -m pip install -r requirements.txt
        ;;
    daily)
        shift
        if [ -n "${1:-}" ]; then exec "$(py)" rundown_etl.py daily --date "$1"; fi
        exec "$(py)" rundown_etl.py daily
        ;;
    live)
        shift
        exec "$(py)" rundown_etl.py live "$@"
        ;;
    serve)
        exec "$(py)" rundown_etl.py serve
        ;;
    start)
        mkdir -p "$LOGDIR"
        if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
            echo "已运行 PID $(cat "$PIDFILE")"
            exit 0
        fi
        nohup "$(py)" rundown_etl.py serve >> "$LOGDIR/rundown.log" 2>&1 &
        echo $! > "$PIDFILE"
        echo "已启动 PID $(cat "$PIDFILE")，日志: $LOGDIR/rundown.log"
        ;;
    stop)
        if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
            kill "$(cat "$PIDFILE")"
            echo "已停止 PID $(cat "$PIDFILE")"
        fi
        if [ -f "$PIDFILE" ]; then unlink "$PIDFILE"; fi
        ;;
    status)
        if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
            echo "运行中 PID $(cat "$PIDFILE")"
        else
            echo "未运行"
        fi
        ;;
    *)
        echo "用法: ./run.sh {setup|daily [日期]|live [--once]|serve|start|stop|status}"
        exit 1
        ;;
esac
