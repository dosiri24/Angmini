# SmartScheduler MVP 개발 계획서

**목표**: 자연어로 일정 추가 + 이동시간 경고까지 동작하는 MVP 완성

---

## 폴더 구조 (Flat Start)

```
smart-scheduler/
├── models.py        # Schedule 데이터 모델
├── database.py      # SQLite DB + Repository
├── tools.py         # Tool 정의 및 구현
├── agent.py         # LLM Agent (ReAct)
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

## Phase 3: Tools 구현 (tools.py)

### 3.1 Tool 스키마 정의
- [ ] **IMPL**: Gemini Function Calling 형식으로 각 Tool 스키마 작성
- [ ] **IMPL**: TOOL_DEFINITIONS 딕셔너리 생성

### 3.2 add_schedule Tool
- [ ] **TEST**: 정상 입력 시 일정 추가 테스트
- [ ] **TEST**: 날짜 파싱 테스트 ("내일", "금요일", "11/28")
- [ ] **IMPL**: add_schedule(title, date, time?, location?, category?)
- [ ] **IMPL**: 자연어 날짜 → date 변환 헬퍼

### 3.3 get_schedules_for_date Tool
- [ ] **TEST**: 특정 날짜 조회 테스트
- [ ] **TEST**: 일정 없는 날짜 빈 리스트 테스트
- [ ] **IMPL**: get_schedules_for_date(date) → List[dict]

### 3.4 complete_schedule Tool
- [ ] **TEST**: 완료 처리 후 status 변경 테스트
- [ ] **TEST**: 없는 ID 에러 처리 테스트
- [ ] **IMPL**: complete_schedule(schedule_id) → dict

### 3.5 check_travel_time Tool
- [ ] **TEST**: 이전 일정 있을 때 이동시간 추정 테스트
- [ ] **TEST**: 이전 일정 없을 때 처리 테스트
- [ ] **IMPL**: check_travel_time(date, time, new_location) → dict
- [ ] **IMPL**: 이동시간 추정 로직 (자주 가는 경로 캐시 or LLM 추정)

### 3.6 Tool 실행기
- [ ] **TEST**: tool_name으로 함수 호출 테스트
- [ ] **IMPL**: execute_tool(name, params) → dict

---

## Phase 4: LLM Agent (agent.py)

### 4.1 Gemini 클라이언트 설정
- [ ] **IMPL**: config.py에서 API 키 로드
- [ ] **IMPL**: Gemini 모델 초기화 (gemini-1.5-flash)
- [ ] **IMPL**: Tool 스키마 등록

### 4.2 단일 턴 Tool Calling
- [ ] **TEST**: 단순 요청 → Tool 호출 테스트 (mock)
- [ ] **IMPL**: process_message(user_input) → response
- [ ] **IMPL**: Tool 호출 결과 파싱

### 4.3 ReAct 패턴 (멀티 턴)
- [ ] **TEST**: 일정 추가 후 이동시간 확인까지 연속 실행 테스트
- [ ] **IMPL**: 반복 루프 - Tool 호출 → 결과 확인 → 추가 필요? → 반복/종료
- [ ] **IMPL**: 최대 반복 횟수 제한 (무한루프 방지)

### 4.4 응답 생성
- [ ] **TEST**: Tool 결과 → 자연어 응답 변환 테스트
- [ ] **IMPL**: 최종 응답 포맷팅 (이모지, 구조화)

---

## Phase 5: Discord Bot (bot.py)

### 5.1 Bot 기본 설정
- [ ] **IMPL**: discord.py 클라이언트 초기화
- [ ] **IMPL**: on_ready 이벤트
- [ ] **IMPL**: 특정 채널에서만 응답

### 5.2 메시지 처리
- [ ] **IMPL**: on_message 이벤트
- [ ] **IMPL**: Agent 호출 → 응답 전송
- [ ] **IMPL**: 에러 핸들링 (사용자 친화적 메시지)

### 5.3 빠른 명령어
- [ ] **IMPL**: `!today` - 오늘 일정 조회
- [ ] **IMPL**: `!tomorrow` - 내일 일정 조회
- [ ] **IMPL**: `!tasks` - 다가오는 할일 목록
- [ ] **IMPL**: `!done <id>` - 완료 처리

### 5.4 실행 스크립트
- [ ] **IMPL**: main() 함수
- [ ] **IMPL**: `python bot.py`로 실행 가능하게

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

## 진행 상태 추적

| Phase | 상태 | 시작일 | 완료일 |
|-------|------|--------|--------|
| 1. 데이터 모델 | ✅ 완료 | 2025-11-26 | 2025-11-26 |
| 2. 데이터베이스 | ✅ 완료 | 2025-11-26 | 2025-11-26 |
| 3. Tools | ⏳ 대기 | - | - |
| 4. LLM Agent | ⏳ 대기 | - | - |
| 5. Discord Bot | ⏳ 대기 | - | - |
| 6. 통합/마무리 | ⏳ 대기 | - | - |

---

*작성일: 2025-11-26*
*설계문서 참조: SmartScheduler-설계문서-v4.md*
