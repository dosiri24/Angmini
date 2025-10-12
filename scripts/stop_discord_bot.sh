#!/bin/bash
# Discord 봇 종료 스크립트 (강화된 중복 검사)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PIDFILE="$PROJECT_ROOT/.discord_bot.pid"

echo "🛑 Angmini 전체 종료 스크립트"

# === 1단계: PID 파일 기반 종료 ===
if [ -f "$PIDFILE" ]; then
    PID=$(cat "$PIDFILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "PID 파일의 프로세스 종료 중 (PID: $PID)..."
        kill -9 "$PID" 2>/dev/null || true
        sleep 1
    fi
    rm -f "$PIDFILE"
    echo "✅ PID 파일 정리 완료"
fi

# === 2단계: 모든 main.py 프로세스 강제 종료 ===
echo "🔍 모든 Angmini 프로세스 검사 중..."

ALL_PIDS=$(pgrep -f "python.*main.py" || true)
if [ -n "$ALL_PIDS" ]; then
    echo "⚠️  발견된 모든 Angmini 프로세스:"
    ps -p $ALL_PIDS -o pid,command 2>/dev/null || true

    echo ""
    echo "모든 프로세스를 강제 종료합니다..."
    echo "$ALL_PIDS" | xargs kill -9 2>/dev/null || true
    sleep 2

    # 재확인
    REMAINING=$(pgrep -f "python.*main.py" || true)
    if [ -n "$REMAINING" ]; then
        echo "⚠️  일부 프로세스가 남아있습니다. 다시 강제 종료..."
        echo "$REMAINING" | xargs kill -9 2>/dev/null || true
        sleep 1
    fi

    echo "✅ 모든 Angmini 프로세스 종료 완료"
else
    echo "✅ 실행 중인 프로세스 없음"
fi

# === 3단계: 최종 확인 ===
FINAL_CHECK=$(pgrep -f "python.*main.py" || true)
if [ -n "$FINAL_CHECK" ]; then
    echo "❌ 경고: 일부 프로세스가 여전히 실행 중입니다"
    echo "PID: $FINAL_CHECK"
    echo "수동으로 종료해주세요: kill -9 $FINAL_CHECK"
else
    echo "✅ 모든 프로세스 종료 확인 완료"
fi
