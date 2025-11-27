#!/bin/bash
# Angmini 실행 스크립트
# 사용법: ./run-app.sh [옵션]
#   (옵션 없음)   데스크톱 앱만 실행 (기본)
#   --with-bot    백엔드 봇 + 데스크톱 앱 함께 실행
#   --bot-only    백엔드 봇만 실행

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$SCRIPT_DIR/app-mac"
BACKEND_DIR="$SCRIPT_DIR/backend"

# 색상 코드
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 정리 함수 (Ctrl+C 시 모든 프로세스 종료)
cleanup() {
    echo -e "\n${YELLOW}🛑 종료 중...${NC}"
    if [ ! -z "$BOT_PID" ]; then
        kill $BOT_PID 2>/dev/null || true
    fi
    if [ ! -z "$APP_PID" ]; then
        kill $APP_PID 2>/dev/null || true
    fi
    exit 0
}
trap cleanup SIGINT SIGTERM

run_bot() {
    echo -e "${GREEN}🤖 백엔드 봇 시작...${NC}"

    if [ ! -d "$BACKEND_DIR" ]; then
        echo -e "${RED}❌ backend 디렉토리를 찾을 수 없습니다.${NC}"
        return 1
    fi

    cd "$BACKEND_DIR"

    # Python 확인
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ Python3가 설치되어 있지 않습니다.${NC}"
        return 1
    fi

    # 가상환경 활성화 (있으면)
    if [ -d "venv" ]; then
        source venv/bin/activate
    elif [ -d ".venv" ]; then
        source .venv/bin/activate
    fi

    # 봇 실행
    python3 bot.py &
    BOT_PID=$!
    echo -e "${GREEN}✅ 백엔드 봇 시작됨 (PID: $BOT_PID)${NC}"

    cd "$SCRIPT_DIR"
}

run_app() {
    echo -e "${GREEN}🚀 데스크톱 앱 시작...${NC}"

    if [ ! -d "$APP_DIR" ]; then
        echo -e "${RED}❌ app-mac 디렉토리를 찾을 수 없습니다.${NC}"
        return 1
    fi

    cd "$APP_DIR"

    # Node.js 확인
    if ! command -v node &> /dev/null; then
        echo -e "${RED}❌ Node.js가 설치되어 있지 않습니다.${NC}"
        return 1
    fi

    # Rust 확인
    if ! command -v rustc &> /dev/null; then
        echo -e "${RED}❌ Rust가 설치되어 있지 않습니다.${NC}"
        return 1
    fi

    # 의존성 설치 (node_modules 없으면)
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}📦 npm 의존성 설치 중...${NC}"
        npm install
    fi

    # Tauri 개발 서버 실행
    echo -e "${GREEN}✨ 앱 실행 중... (처음 실행 시 빌드에 시간이 걸릴 수 있습니다)${NC}"
    npm run tauri dev &
    APP_PID=$!

    cd "$SCRIPT_DIR"
}

# 메인 로직
case "${1:-}" in
    --with-bot)
        echo -e "${GREEN}🎮 Angmini 통합 실행${NC}"
        echo -e "${YELLOW}   Ctrl+C로 모두 종료${NC}"
        echo ""

        run_bot
        sleep 2  # 봇이 먼저 시작되도록 대기
        run_app

        echo ""
        echo -e "${GREEN}✅ 모든 서비스 시작됨${NC}"
        echo -e "   백엔드 봇: PID $BOT_PID"
        echo -e "   데스크톱 앱: PID $APP_PID"
        echo ""

        # 둘 중 하나가 종료될 때까지 대기
        wait
        ;;
    --bot-only)
        run_bot
        wait $BOT_PID
        ;;
    *)
        # 기본: 프론트엔드(데스크톱 앱)만 실행
        run_app
        wait $APP_PID
        ;;
esac
