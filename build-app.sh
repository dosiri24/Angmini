#!/bin/bash
# Angmini 프로덕션 빌드 스크립트
# 사용법: ./build-app.sh [옵션]
#   --install     빌드 후 Applications 폴더에 설치
#   --open        설치 후 앱 바로 실행
#   (옵션 없음)   빌드만 실행

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$SCRIPT_DIR/app-mac"
APP_NAME="SmartScheduler"
BUNDLE_PATH="$APP_DIR/src-tauri/target/release/bundle/macos/$APP_NAME.app"

# 색상 코드
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   🔨 Angmini 프로덕션 빌드 시작    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════╝${NC}"
echo ""

# 디렉토리 확인
if [ ! -d "$APP_DIR" ]; then
    echo -e "${RED}❌ app-mac 디렉토리를 찾을 수 없습니다.${NC}"
    exit 1
fi

cd "$APP_DIR"

# Node.js 확인
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js가 설치되어 있지 않습니다.${NC}"
    exit 1
fi

# Rust 확인
if ! command -v rustc &> /dev/null; then
    echo -e "${RED}❌ Rust가 설치되어 있지 않습니다.${NC}"
    exit 1
fi

# 의존성 설치 (node_modules 없으면)
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}📦 npm 의존성 설치 중...${NC}"
    npm install
fi

# 프로덕션 빌드
echo -e "${GREEN}🔨 프로덕션 빌드 중... (시간이 좀 걸립니다)${NC}"
npm run tauri build

# 빌드 성공 확인
if [ ! -d "$BUNDLE_PATH" ]; then
    echo -e "${RED}❌ 빌드 실패: .app 파일을 찾을 수 없습니다.${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ 빌드 완료!${NC}"
echo -e "   위치: ${BLUE}$BUNDLE_PATH${NC}"

# 옵션 처리
INSTALL=false
OPEN=false

for arg in "$@"; do
    case $arg in
        --install)
            INSTALL=true
            ;;
        --open)
            INSTALL=true
            OPEN=true
            ;;
    esac
done

# Applications 폴더에 설치
if [ "$INSTALL" = true ]; then
    echo ""
    echo -e "${YELLOW}📂 Applications 폴더에 설치 중...${NC}"

    # 기존 앱 있으면 삭제
    if [ -d "/Applications/$APP_NAME.app" ]; then
        echo -e "${YELLOW}   기존 앱 삭제 중...${NC}"
        rm -rf "/Applications/$APP_NAME.app"
    fi

    # 복사
    cp -r "$BUNDLE_PATH" /Applications/
    echo -e "${GREEN}✅ 설치 완료: /Applications/$APP_NAME.app${NC}"
fi

# 앱 실행
if [ "$OPEN" = true ]; then
    echo ""
    echo -e "${GREEN}🚀 앱 실행 중...${NC}"
    open "/Applications/$APP_NAME.app"
fi

echo ""
echo -e "${BLUE}════════════════════════════════════${NC}"
echo -e "${GREEN}사용법:${NC}"
echo -e "  ${YELLOW}./build-app.sh${NC}            빌드만"
echo -e "  ${YELLOW}./build-app.sh --install${NC}  빌드 + 설치"
echo -e "  ${YELLOW}./build-app.sh --open${NC}     빌드 + 설치 + 실행"
echo -e "${BLUE}════════════════════════════════════${NC}"
