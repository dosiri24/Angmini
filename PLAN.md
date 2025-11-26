# SmartScheduler MVP 개발 계획서

**목표**: 자연어로 일정 추가 + 이동시간 경고까지 동작하는 MVP 완성

---

## ⚠️ 핵심 원칙 (CLAUDE.md 준수)

### 순수 LLM 기반 원칙 (No Keyword Parsing)
- **자연어 처리는 100% LLM이 담당**
- Tool은 **구조화된 데이터만** 처리 (ISO 형식)
- 키워드 파싱, 정규식 라우팅 **절대 금지**

```
올바른 흐름:
사용자: "내일 3시에 미팅"
    ↓
LLM: 자연어 이해 → 구조화 변환  ← ✅ LLM이 담당
    ↓
LLM: add_schedule(date="2025-11-27", start_time="15:00")  ← ISO 형식
    ↓
Tool: 검증 후 DB 저장  ← 파싱 없음
```

---

## 폴더 구조 (Flat Start)

```
smart-scheduler/
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
│   └── test_agent.py
├── requirements.txt
├── .env.example
├── .env             # (gitignore)
└── README.md
```

> 복잡해지면 `tools/`, `agent/` 등으로 분리 예정

---

## Phase 1: 데이터 모델 (models.py) ✅ 완료

### 1.1 Schedule 데이터클래스 정의
- [x] **TEST**: Schedule 객체 생성 테스트
- [x] **IMPL**: @dataclass로 Schedule 정의
- [x] **필드 목록**:
  - `id`: Optional[int] - DB 자동생성
  - `title`: str - 일정 제목
  - `scheduled_date`: date - 예정 날짜
  - `start_time`: Optional[time] - 시작 시간 (없으면 할일)
  - `end_time`: Optional[time] - 종료 시간
  - `location`: Optional[str] - 장소
  - `major_category`: str - 대분류 (학업/약속/개인/업무/루틴/기타)
  - `status`: str - 상태 (예정/완료/취소)
  - `created_at`: datetime - 생성 시각

### 1.2 Schedule 유효성 검증
- [x] **TEST**: 빈 title 거부 테스트
- [x] **TEST**: 잘못된 category 거부 테스트
- [x] **IMPL**: validate() 메서드 구현

### 1.3 Schedule 직렬화
- [x] **TEST**: to_dict() / from_dict() 테스트
- [x] **IMPL**: dict 변환 메서드 구현

---

## Phase 2: 데이터베이스 (database.py) ✅ 완료

### 2.1 SQLite 연결 및 스키마
- [x] **TEST**: DB 파일 생성 테스트
- [x] **IMPL**: Database 클래스 - __init__, connect, close
- [x] **IMPL**: schedules 테이블 스키마 정의
- [x] **IMPL**: init_schema() - 테이블 생성

### 2.2 기본 CRUD - Create
- [x] **TEST**: insert() 후 ID 반환 테스트
- [x] **IMPL**: insert(schedule) → int

### 2.3 기본 CRUD - Read
- [x] **TEST**: get_by_id() 테스트
- [x] **TEST**: get_by_date() 테스트 (해당 날짜 일정 목록)
- [x] **IMPL**: get_by_id(id) → Optional[Schedule]
- [x] **IMPL**: get_by_date(date) → List[Schedule]

### 2.4 기본 CRUD - Update
- [x] **TEST**: update() 후 변경 확인 테스트
- [x] **IMPL**: update(schedule) → bool

### 2.5 기본 CRUD - Delete
- [x] **TEST**: delete() 후 조회 실패 테스트
- [x] **IMPL**: delete(id) → bool

### 2.6 추가 쿼리
- [x] **TEST**: get_upcoming() 테스트 (n일 이내 일정)
- [x] **TEST**: search() 테스트 (키워드 검색)
- [x] **IMPL**: get_upcoming(days=7) → List[Schedule]
- [x] **IMPL**: search(query) → List[Schedule]

---

## Phase 3: Tools 구현 (tools.py) ✅ 완료

### 3.1 Tool 스키마 정의
- [x] **IMPL**: Gemini Function Calling 형식으로 각 Tool 스키마 작성
- [x] **IMPL**: TOOL_DEFINITIONS 딕셔너리 생성
- [x] **IMPL**: **ISO 형식 명시** (YYYY-MM-DD, HH:MM) - 순수 LLM 원칙

### ~~3.2 자연어 날짜 파싱~~ ❌ 삭제됨
> **CLAUDE.md 원칙 위반으로 제거**
> - ~~parse_natural_date 함수~~ → LLM이 담당
> - Tool은 ISO 형식만 처리

### 3.2 add_schedule Tool (수정됨)
- [x] **TEST**: 정상 입력 시 일정 추가 테스트 (ISO 형식)
- [x] **TEST**: 잘못된 날짜 형식 거부 테스트 ← 신규
- [x] **IMPL**: add_schedule(title, date, start_time?, end_time?, location?, category?)
- [x] **IMPL**: ISO 형식 검증 (자연어 입력 시 에러 반환)

### 3.3 get_schedules_for_date Tool
- [x] **TEST**: 특정 날짜 조회 테스트 (ISO 형식)
- [x] **TEST**: 잘못된 날짜 형식 거부 테스트 ← 신규
- [x] **IMPL**: get_schedules_for_date(date) → List[dict]

### 3.4 complete_schedule Tool
- [x] **TEST**: 완료 처리 후 status 변경 테스트
- [x] **TEST**: 없는 ID 에러 처리 테스트
- [x] **IMPL**: complete_schedule(schedule_id) → dict

### 3.5 check_travel_time Tool
- [x] **TEST**: 이전 일정 있을 때 이동시간 추정 테스트 (ISO 형식)
- [x] **TEST**: 잘못된 날짜 형식 거부 테스트 ← 신규
- [x] **IMPL**: check_travel_time(date, time, new_location) → dict
- [x] **IMPL**: 이동시간 추정 로직 (간단한 휴리스틱 - MVP)

### 3.6 Tool 실행기
- [x] **TEST**: tool_name으로 함수 호출 테스트
- [x] **IMPL**: execute_tool(name, params) → dict

---

## Phase 4: LLM Agent (agent.py) ✅ 완료

### 4.1 Gemini 클라이언트 설정
- [x] **IMPL**: config.py에서 API 키 로드
- [x] **IMPL**: Gemini 모델 초기화 (gemini-flash-latest)
- [x] **IMPL**: Tool 스키마 등록 (build_gemini_tools)

### 4.2 대화 메모리 (Memory)
- [x] **TEST**: 대화 히스토리 저장/조회 테스트
- [x] **IMPL**: ConversationMemory 클래스 (최근 N턴 유지)
- [x] **IMPL**: add(role, content), get_context(), clear() 메서드
- [x] **IMPL**: Gemini chat 세션과 연동

### 4.3 단일 턴 Tool Calling (async)
- [x] **TEST**: 단순 요청 → Tool 호출 테스트 (mock)
- [x] **IMPL**: async process_message(user_input) → response
- [x] **IMPL**: send_message_async() 사용 (비동기 LLM 호출)
- [x] **IMPL**: Tool 호출 결과 파싱
- [x] **IMPL**: **자연어 → ISO 형식 변환은 LLM이 수행** ← 핵심

### 4.4 ReAct 패턴 (멀티 턴)
- [x] **TEST**: 일정 추가 후 이동시간 확인까지 연속 실행 테스트
- [x] **IMPL**: 반복 루프 - Tool 호출 → 결과 확인 → 추가 필요? → 반복/종료
- [x] **IMPL**: 최대 반복 횟수 제한 (무한루프 방지)

### 4.5 응답 생성
- [x] **TEST**: Tool 결과 → 자연어 응답 변환 테스트
- [x] **IMPL**: 최종 응답 포맷팅 (이모지, 친근한 톤)

---

## Phase 5: Discord Bot (bot.py) ✅ 완료

### 5.1 Bot 기본 설정
- [x] **IMPL**: discord.py 클라이언트 초기화 (AngminiBot 클래스)
- [x] **IMPL**: on_ready 이벤트 (상태 메시지 설정)
- [x] **IMPL**: 특정 채널에서만 응답 (target_channel_id 설정)

### 5.2 메시지 처리
- [x] **IMPL**: on_message 이벤트 (자연어 → Agent 위임)
- [x] **IMPL**: Agent 호출 → 응답 전송 (typing 표시)
- [x] **IMPL**: 에러 핸들링 (사용자 친화적 메시지)
- [x] **IMPL**: 긴 메시지 분할 (split_message, 2000자 제한)

### 5.3 빠른 명령어 (슬래시 커맨드 - 예외 허용)
- [x] **IMPL**: `/today` - 오늘 일정 조회
- [x] **IMPL**: `/tomorrow` - 내일 일정 조회
- [x] **IMPL**: `/tasks` - 다가오는 할일 목록
- [x] **IMPL**: `/done <id>` - 완료 처리
- [x] **IMPL**: `/help` - 사용 가이드

### 5.4 실행 스크립트
- [x] **IMPL**: main() 함수 (asyncio.run)
- [x] **IMPL**: `python bot.py`로 실행 가능하게

---

## Phase 6: 통합 및 마무리

### 6.1 환경 설정
- [ ] **IMPL**: requirements.txt 작성
- [ ] **IMPL**: .env.example 작성
- [ ] **IMPL**: config.py - 환경변수 로드

### 6.2 통합 테스트
- [ ] **TEST**: 전체 플로우 테스트 (메시지 → Agent → Tool → DB → 응답)
- [ ] **FIX**: 발견된 버그 수정

### 6.3 문서화
- [ ] **DOCS**: README.md - 설치 및 실행 방법
- [ ] **DOCS**: 사용 예시

---

## 진행 상태 추적 (시작과 완료 일자 표시에 시각까지 명시하고, 이때 시간은 직접 확인할 것.)

| Phase | 상태 | 시작 | 완료 |
|-------|------|------|------|
| 1. 데이터 모델 | ✅ 완료 | 2025-11-26 12:49 | 2025-11-26 12:55 |
| 2. 데이터베이스 | ✅ 완료 | 2025-11-26 12:55 | 2025-11-26 12:57 |
| 3. Tools | ✅ 완료 | 2025-11-26 13:08 | 2025-11-26 13:56 |
| 4. LLM Agent | ✅ 완료 | 2025-11-26 14:00 | 2025-11-26 14:08 |
| 5. Discord Bot | ✅ 완료 | 2025-11-26 15:12 | 2025-11-26 15:14 |
| 6. 통합/마무리 | ⏳ 대기 | - | - |

---

*작성일: 2025-11-26*
*설계문서 참조: SmartScheduler-설계문서-v4.md*
*최종수정: 2025-11-26 14:08 - Phase 4 완료 (LLM Agent 구현)*
