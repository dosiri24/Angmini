# Angmini (앙미니)

자연어 기반 AI 일정 관리 시스템. Discord를 메시지 브로커로 활용하여 데스크톱 앱과 백엔드를 연결한다.

## 아키텍처 개요

```
┌──────────────────────────────────────────────────────────────┐
│                    Desktop App (Tauri v2)                    │
│     React 19  +  useDiscord (폴링)  +  useSchedules (동기화)  │
└──────────────────────────────┬───────────────────────────────┘
                               │ [DESKTOP_USER] prefix
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                 Discord Channel (메시지 브로커)                │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                      Backend (Python)                        │
│                                                              │
│   Discord Bot ──→ LLM Agent (ReAct) ──→ Tools ──→ SQLite    │
│    (라우터)          (자연어 해석)      (ISO 검증)              │
└──────────────────────────────────────────────────────────────┘
```

데스크톱 앱(Tauri v2)에서 사용자가 메시지를 입력하면 Discord 채널을 통해 백엔드로 전달된다. 백엔드의 Discord Bot이 메시지를 수신하면 LLM Agent(ReAct 패턴)가 자연어를 분석하고 적절한 Tool을 호출한다. Tool 실행 결과는 SQLite에 저장되고, 봇이 응답을 Discord에 전송하면 데스크톱 앱이 폴링으로 수신하여 화면에 표시한다.

## 핵심 설계 원칙

### 1. 순수 LLM 기반 자연어 처리 (키워드 파싱 금지)

모든 자연어 해석은 LLM(Gemini)이 담당한다. 키워드 파싱, 정규식 라우팅, if-else 기반 의도 분류는 일체 사용하지 않는다. LLM이 "내일 오후 3시에 팀 미팅"이라는 자연어를 분석하여 ISO 형식(2025-11-28, 15:00)으로 변환한 뒤 Tool을 호출한다. Tool은 구조화된 데이터만 검증하고 처리하며, Bot은 메시지 라우팅만 담당한다.

### 2. 구조화된 동기화 프로토콜

봇 응답에 마커 기반 구조화 데이터를 포함한다. `[SCHEDULE_SYNC]...[/SCHEDULE_SYNC]` 마커 안에 JSON 형태로 동기화 이벤트를 전달한다. action 타입은 add(일정 추가), update(일정 수정/완료), delete(일정 삭제), full_sync(전체 동기화) 4가지가 있다.

### 3. Discord를 메시지 브로커로 활용

데스크톱 앱과 백엔드가 동일한 봇 토큰을 사용하므로, 백엔드가 앱에서 보낸 메시지를 자신의 메시지로 인식하는 문제가 있다. 이를 해결하기 위해 데스크톱 앱에서 보내는 모든 메시지에 `[DESKTOP_USER]` prefix를 붙이고, 백엔드는 이 prefix로 메시지 소스를 구분한다.

## 기술 스택

### 백엔드
- AI: Google Gemini (gemini-flash-latest)
- 에이전트 패턴: ReAct (Reason + Act)
- 봇 프레임워크: discord.py 2.x
- 데이터베이스: SQLite3
- 언어: Python 3.10+

### 데스크톱 앱
- 프레임워크: Tauri v2 (Rust)
- 프론트엔드: React 19 + TypeScript
- 빌드 도구: Vite 7
- HTTP 클라이언트: @tauri-apps/plugin-http (CORS 우회)

## 프로젝트 구조

### backend/
- **agent.py**: ReAct Agent. 자연어를 분석하여 Tool Call로 변환하고, 최대 5회 반복하며 결과를 생성한다.
- **bot.py**: Discord Bot. 메시지 라우팅만 담당하며, 자연어 파싱 로직 없음.
- **tools.py**: Tool 정의 및 실행. ISO 형식 검증과 DB 연동을 담당한다.
- **models.py**: Schedule 도메인 모델. Dataclass 기반으로 유효성 검증을 포함한다.
- **database.py**: SQLite 저장소. CRUD 및 날짜별/기간별 조회 기능 제공.
- **config.py**: 환경변수 관리. 싱글톤 패턴으로 구현.
- **tests/**: pytest 기반 TDD 테스트.

### app-mac/src/
- **components/Layout/**: 3단 레이아웃 (캐릭터/컨텐츠/토글)
- **components/Chat/**: 채팅 UI
- **components/Calendar/**: 월간/일간 달력
- **components/Character/**: 캐릭터 상태 애니메이션
- **hooks/useDiscord.ts**: Discord API 폴링 (1.5초 주기)
- **hooks/useSchedules.ts**: 일정 상태 관리 및 동기화 이벤트 처리
- **hooks/useMessages.ts**: 채팅 메시지 상태 관리
- **utils/scheduleParser.ts**: 마커 기반 JSON 파싱

### app-mac/src-tauri/
- Rust 기반 Tauri 백엔드

## 에이전트 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                   Agent.process_message()                   │
├─────────────────────────────────────────────────────────────┤
│  1. 사용자 입력 → ConversationMemory 저장                    │
│  2. 시스템 프롬프트 + LLM 호출                               │
│  3. ReAct 루프 (최대 5회):                                  │
│       ┌─────────────────────────────────────────────┐       │
│       │  LLM 응답 분석                               │       │
│       │    ├─ 텍스트만 → 최종 응답 반환              │       │
│       │    └─ Function Call → Tool 실행 → 재호출    │       │
│       └─────────────────────────────────────────────┘       │
│  4. 최종 응답을 메모리에 저장                                │
└─────────────────────────────────────────────────────────────┘
```

Agent.process_message()가 호출되면 먼저 사용자 입력을 ConversationMemory에 저장한다. 현재 날짜/시간이 포함된 시스템 프롬프트와 함께 LLM에 요청을 보낸다. LLM 응답에 Function Call이 포함되어 있으면 해당 Tool을 실행하고 결과를 다시 LLM에 전달한다. 이 과정을 최대 5회 반복하며, 텍스트 응답이 나오면 최종 결과로 반환한다.

### Tool 목록
- **add_schedule**: 일정 추가. title과 date(ISO) 필수.
- **get_schedules_for_date**: 날짜별 조회. date(ISO) 필수.
- **complete_schedule**: 완료 처리. schedule_id 필수.
- **get_all_schedules**: 전체 조회 (동기화용).
- **check_travel_time**: 이동시간 확인. date, time, location 필수.

## 데스크톱 앱 데이터 흐름

```
사용자 입력
     │
     ▼
useDiscord.sendMessage() ─── [DESKTOP_USER] prefix 추가
     │
     ▼
Discord API (POST /channels/{id}/messages)
     │
     ▼
백엔드 bot.on_message() → Agent.process_message()
     │
     ▼
Discord 봇 응답 ─── [SCHEDULE_SYNC] 마커 포함
     │
     ▼
useDiscord 폴링 (1.5초 주기)
     │
     ▼
useSchedules.processMessage() → 동기화 이벤트 파싱
     │
     ▼
로컬 상태 + localStorage 캐시 업데이트
```

사용자가 메시지를 입력하면 useDiscord.sendMessage()가 `[DESKTOP_USER]` prefix를 붙여 Discord API로 전송한다. 백엔드의 bot.on_message()가 이를 수신하면 Agent.process_message()를 호출한다. 에이전트가 처리를 완료하면 `[SCHEDULE_SYNC]` 마커가 포함된 응답을 Discord에 전송한다. 데스크톱 앱은 1.5초 주기로 폴링하여 새 메시지를 수신하고, useSchedules.processMessage()가 동기화 이벤트를 파싱하여 로컬 상태와 localStorage 캐시를 업데이트한다.

## 주요 구현 세부사항

### ConversationMemory
deque 기반으로 최근 10턴의 대화를 유지한다. Gemini API 형식으로 context를 변환하며, 토큰 사용량을 제한한다.

### Schedule 모델
Dataclass로 구현되어 유효성 검증을 포함한다. 상태는 예정/완료/취소 중 하나이고, 카테고리는 학업/약속/개인/업무/루틴/기타 중 하나이다.

### 로컬 캐시
localStorage 기반으로 메시지 히스토리와 일정 데이터를 영속화한다. 앱 재시작 시 자동으로 복원된다.

### 백그라운드 동기화
앱 시작 시 초기 동기화를 수행하고, 이후 30분 주기로 자동 동기화한다. 사용자가 메시지를 전송하면 3초 후에 추가 동기화를 트리거한다.

## 환경변수

### 백엔드
- GEMINI_API_KEY: Gemini API 키
- DISCORD_BOT_TOKEN: Discord 봇 토큰
- DISCORD_CHANNEL_ID: 응답할 채널 ID
- DATABASE_PATH: SQLite DB 경로 (기본값: ./backend/schedules.db)

### 데스크톱 앱
- DISCORD_BOT_TOKEN: Discord 봇 토큰
- DISCORD_CHANNEL_ID: 채널 ID
- DISCORD_BOT_USER_ID: 봇 사용자 ID (응답 필터링용)

## 모델 설정

- gemini-flash-latest: 빠른 응답용
- gemini-3.0-pro: 복잡한 추론용

---

*마지막 업데이트: 2025-11-27*
