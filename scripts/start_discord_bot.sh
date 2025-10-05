#!/bin/bash
# Discord 봇 중복 실행 방지 스크립트 (강화된 중복 검사)

# 프로젝트 루트 디렉토리
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PIDFILE="$PROJECT_ROOT/.discord_bot.pid"

echo "🤖 Angmini Discord Bot 시작 스크립트"
echo "프로젝트 경로: $PROJECT_ROOT"

# === 1단계: PID 파일 기반 종료 ===
if [ -f "$PIDFILE" ]; then
    OLD_PID=$(cat "$PIDFILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo "⚠️  PID 파일의 프로세스 종료 중 (PID: $OLD_PID)"
        kill -9 "$OLD_PID" 2>/dev/null || true
        sleep 1
    fi
    rm -f "$PIDFILE"
fi

# === 2단계: 모든 main.py 프로세스 강제 종료 ===
echo "🔍 모든 Angmini 프로세스 검사 중..."

# Python main.py를 실행하는 모든 프로세스 찾기 (CLI, Discord 모두 포함)
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

    echo "✅ 모든 기존 프로세스 정리 완료"
else
    echo "✅ 실행 중인 프로세스 없음"
fi

# === 3단계: 최종 확인 ===
FINAL_CHECK=$(pgrep -f "python.*main.py" || true)
if [ -n "$FINAL_CHECK" ]; then
    echo "❌ 오류: 프로세스 종료 실패"
    echo "수동으로 종료해주세요: kill -9 $FINAL_CHECK"
    exit 1
fi

# 가상환경 활성화
if [ -f "$PROJECT_ROOT/.venv/bin/activate" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
    echo "✅ 가상환경 활성화 완료"
else
    echo "⚠️  가상환경을 찾을 수 없습니다: $PROJECT_ROOT/.venv"
fi

# Discord 봇 시작
cd "$PROJECT_ROOT"
echo "🚀 Discord 봇 시작 중..."
nohup python main.py --interface discord > logs/discord_bot.out 2>&1 &
NEW_PID=$!

# PID 저장
echo "$NEW_PID" > "$PIDFILE"
echo "✅ Discord 봇 시작 완료 (PID: $NEW_PID)"
echo "📋 로그 위치: $PROJECT_ROOT/logs/discord_bot.out"
echo ""
echo "봇 상태 확인: ps -p $NEW_PID"
echo "봇 종료: kill $NEW_PID"
echo "로그 확인: tail -f logs/discord_bot.out"
