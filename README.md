# SmartScheduler

자연어로 일정을 관리하는 Discord 봇입니다. Gemini AI를 활용하여 자연어 입력을 이해하고, 일정 추가/조회/완료 처리 및 이동시간 경고까지 제공합니다.

## 주요 기능

- **자연어 일정 추가**: "내일 오후 3시에 팀 미팅 추가해줘"
- **일정 조회**: "오늘 일정 알려줘", "이번 주 할 일 뭐 있어?"
- **완료 처리**: "첫 번째 일정 완료했어"
- **이동시간 경고**: 연속된 일정 간 위치가 다르면 이동시간을 추정하여 경고

## 아키텍처

```
사용자 (Discord) → Bot → LLM Agent → Tools → Database
                          ↓
                   자연어 → ISO 형식 변환
                   (LLM이 100% 담당)
```

### 핵심 원칙: 순수 LLM 기반 (No Keyword Parsing)

- **자연어 처리는 100% LLM이 담당**
- Tool은 **구조화된 데이터만** 처리 (ISO 형식: YYYY-MM-DD, HH:MM)
- 키워드 파싱, 정규식 라우팅 **절대 금지**

## 설치

### 1. 의존성 설치

```bash
cd backend
pip install -r requirements.txt
```

### 2. 환경변수 설정

```bash
cp .env.example .env
```

`.env` 파일을 편집하여 실제 값을 입력하세요:

```env
# Gemini API Key (필수)
# https://aistudio.google.com/app/apikey 에서 발급
GEMINI_API_KEY=your_gemini_api_key_here

# Discord Bot Token (필수)
# https://discord.com/developers/applications 에서 발급
DISCORD_BOT_TOKEN=your_discord_bot_token_here

# Discord Channel ID (필수)
# 봇이 응답할 채널의 ID
DISCORD_CHANNEL_ID=your_channel_id_here

# 데이터베이스 경로 (선택, 기본값: ./schedules.db)
DATABASE_PATH=./schedules.db

# 로그 레벨 (선택, 기본값: INFO)
LOG_LEVEL=INFO
```

### 3. Discord Bot 설정

1. [Discord Developer Portal](https://discord.com/developers/applications)에서 새 애플리케이션 생성
2. Bot 섹션에서 봇 토큰 발급
3. OAuth2 → URL Generator에서:
   - Scopes: `bot`, `applications.commands`
   - Bot Permissions: `Send Messages`, `Read Message History`
4. 생성된 URL로 봇을 서버에 초대

## 실행

```bash
python3 bot.py
```

## 사용법

### 자연어 대화

봇이 활성화된 채널에서 자연어로 대화하세요:

```
👤 내일 오후 3시에 강남역에서 팀 미팅 추가해줘
🤖 ✅ 일정이 추가되었습니다!

   📅 팀 미팅
   📆 2025-11-27 (목)
   🕐 15:00
   📍 강남역
   🏷️ 약속

👤 오늘 일정 알려줘
🤖 📋 오늘의 일정입니다:

   1️⃣ 팀 회의 (14:00 ~ 15:00) - 회사
   2️⃣ 저녁 약속 (19:00) - 홍대

👤 첫 번째 일정 완료했어
🤖 ✅ '팀 회의' 일정을 완료 처리했습니다!
```

### 슬래시 명령어

빠른 조작을 위한 슬래시 명령어:

| 명령어 | 설명 |
|--------|------|
| `/today` | 오늘 일정 조회 |
| `/tomorrow` | 내일 일정 조회 |
| `/tasks` | 다가오는 할 일 목록 (7일) |
| `/done <id>` | 일정 완료 처리 |
| `/help` | 사용 가이드 |

## 테스트

```bash
# 전체 테스트 실행
python3 -m pytest tests/ -v

# 커버리지 포함
python3 -m pytest tests/ --cov=. --cov-report=term-missing

# 단위 테스트만 (API 키 불필요)
python3 -m pytest tests/ -v -k "not Integration"
```

## 프로젝트 구조

```
backend/
├── models.py        # Schedule 데이터 모델
├── database.py      # SQLite DB + Repository
├── tools.py         # Tool 정의 및 구현 (ISO 형식만 처리)
├── agent.py         # LLM Agent (ReAct) - 자연어→구조화 담당
├── bot.py           # Discord Bot
├── config.py        # 환경설정
├── tests/           # 테스트 (TDD)
│   ├── test_models.py
│   ├── test_database.py
│   ├── test_tools.py
│   ├── test_agent.py
│   ├── test_bot.py
│   └── test_config.py
├── requirements.txt
├── .env.example
├── .env             # (gitignore)
└── README.md
```

## 기술 스택

- **AI**: Google Gemini (gemini-flash-latest)
- **Bot**: discord.py 2.x
- **DB**: SQLite3
- **테스트**: pytest, pytest-asyncio
- **언어**: Python 3.10+

## 일정 카테고리

| 카테고리 | 설명 |
|----------|------|
| 학업 | 수업, 과제, 시험 등 |
| 약속 | 미팅, 모임, 약속 등 |
| 개인 | 개인 일정, 취미 등 |
| 업무 | 업무 관련 일정 |
| 루틴 | 반복적인 일상 |
| 기타 | 그 외 모든 것 |

## 라이선스

MIT License

---

*작성일: 2025-11-26*
