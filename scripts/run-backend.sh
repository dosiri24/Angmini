#!/bin/bash
# 백엔드 서버(Discord 봇) 실행 스크립트

cd "$(dirname "$0")"
source .venv/bin/activate
python backend/bot.py
