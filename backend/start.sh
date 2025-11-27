#!/bin/bash
# Angmini 백엔드 시작 스크립트
# 기존 프로세스 종료 후 새로 시작하여 중복 실행 방지
#
# 사용법:
#   ./start.sh          백엔드 시작 (포그라운드)
#   ./start.sh --bg     백엔드 시작 (백그라운드)
#   ./start.sh --stop   백엔드 종료

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$SCRIPT_DIR/angmini.pid"
BOT_SCRIPT="$SCRIPT_DIR/bot.py"

# 색상 코드
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 기존 프로세스 종료 함수
kill_existing() {
    # PID 파일로 종료 시도
    if [ -f "$PID_FILE" ]; then
        OLD_PID=$(cat "$PID_FILE")
        if kill -0 "$OLD_PID" 2>/dev/null; then
            echo -e "${YELLOW}기존 프로세스 종료 중 (PID: $OLD_PID)...${NC}"
            kill "$OLD_PID" 2>/dev/null || true
            sleep 1
            # 강제 종료 필요 시
            if kill -0 "$OLD_PID" 2>/dev/null; then
                kill -9 "$OLD_PID" 2>/dev/null || true
            fi
            echo -e "${GREEN}✓ 종료됨${NC}"
        fi
        rm -f "$PID_FILE"
    fi

    # 혹시 모를 좀비 프로세스도 정리 (같은 bot.py를 실행 중인 경우)
    ZOMBIE_PIDS=$(pgrep -f "bot\.py" 2>/dev/null || true)
    if [ -n "$ZOMBIE_PIDS" ]; then
        echo -e "${YELLOW}추가 bot.py 프로세스 발견 (PIDs: $ZOMBIE_PIDS), 종료 중...${NC}"
        echo "$ZOMBIE_PIDS" | xargs kill 2>/dev/null || true
        sleep 1
        # 강제 종료 필요 시
        REMAINING=$(pgrep -f "bot\.py" 2>/dev/null || true)
        if [ -n "$REMAINING" ]; then
            echo "$REMAINING" | xargs kill -9 2>/dev/null || true
        fi
        echo -e "${GREEN}✓ 좀비 프로세스 정리됨${NC}"
    fi
}

# 상태 확인 함수
check_status() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo -e "${GREEN}✓ Angmini 백엔드 실행 중 (PID: $PID)${NC}"
            return 0
        else
            echo -e "${YELLOW}PID 파일은 있으나 프로세스 없음${NC}"
            rm -f "$PID_FILE"
            return 1
        fi
    else
        echo -e "${RED}✗ Angmini 백엔드 실행 중 아님${NC}"
        return 1
    fi
}

# 메인 로직
case "${1:-}" in
    --stop)
        echo -e "${YELLOW}Angmini 백엔드 종료 중...${NC}"
        kill_existing
        echo -e "${GREEN}✓ 종료 완료${NC}"
        ;;
    --status)
        check_status
        ;;
    --bg)
        echo -e "${GREEN}🐱 Angmini 백엔드 시작 (백그라운드)${NC}"
        kill_existing

        cd "$SCRIPT_DIR"
        nohup python3 bot.py > "$SCRIPT_DIR/bot.log" 2>&1 &
        NEW_PID=$!
        echo "$NEW_PID" > "$PID_FILE"

        sleep 2
        if kill -0 "$NEW_PID" 2>/dev/null; then
            echo -e "${GREEN}✓ 시작됨 (PID: $NEW_PID)${NC}"
            echo -e "   로그: $SCRIPT_DIR/bot.log"
        else
            echo -e "${RED}✗ 시작 실패. 로그를 확인하세요.${NC}"
            exit 1
        fi
        ;;
    *)
        echo -e "${GREEN}🐱 Angmini 백엔드 시작 (포그라운드)${NC}"
        kill_existing

        cd "$SCRIPT_DIR"
        # 포그라운드 실행 - PID는 bot.py에서 직접 관리
        python3 bot.py
        ;;
esac
