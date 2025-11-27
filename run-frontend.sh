#!/bin/bash
# Angmini 프론트엔드 개발 서버 실행
# 사용법: ./run-frontend.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$SCRIPT_DIR/app-mac"

# 색상 코드
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}🚀 Angmini 프론트엔드 개발 서버 시작${NC}"

# app-mac 디렉토리 확인
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
if [ ! -d "node_modules" ] && [ ! -L "node_modules" ]; then
    echo -e "${YELLOW}📦 npm 의존성 설치 중...${NC}"
    npm install
fi

# Tauri 개발 서버 실행
echo -e "${GREEN}✨ 개발 서버 실행 중...${NC}"
echo -e "${YELLOW}   (처음 실행 시 Rust 빌드에 시간이 걸립니다)${NC}"
echo -e "${YELLOW}   종료: Ctrl+C${NC}"
echo ""

npx tauri dev
