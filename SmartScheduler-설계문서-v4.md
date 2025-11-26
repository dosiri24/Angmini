# SmartScheduler 설계 문서

**LLM 기반 개인 일정관리 비서**

---

## 1. 프로젝트 개요

### 배경
애플 생태계의 캘린더/리마인더가 분리되어 있고, 자연어 입력이 불편함. 대학생 생활에 맞는 통합 일정 관리가 필요.

### 핵심 아이디어
- 자연어로 일정 추가 ("내일 3시 신촌에서 친구 만나기")
- LLM이 직접 도구(Tool)를 선택하고 실행
- 캘린더/리마인더 구분 없이 통합 관리
- Apple 캘린더와 자동 동기화

### 기술 스택
- **서버**: Python, SQLite, Gemini API
- **통신**: Discord API (포트포워딩 없이 외부 접속)
- **클라이언트**: iOS (Swift)

---

## 2. 시스템 아키텍처

### 전체 구조

```
사용자 (iPhone)
    ↓
iOS App (Swift) - 챗봇 UI, 달력 뷰, 할일 뷰
    ↓
Discord API - 양방향 메시지 전달
    ↓
Mac Server (Python, 집에서 상시 가동)
    ├── LLM Agent (Gemini) - 자연어 이해 & Tool 자동 호출
    ├── Tools - 일정 추가, 조회, 이동시간 확인 등
    ├── SQLite DB - 통합 일정 저장
    └── Apple Calendar 연동 (CalDAV)
```

### 핵심 설계: LLM + Tool Calling

LLM(Gemini)에게 사용 가능한 도구 목록을 알려주면, 사용자 요청을 분석해서 적절한 도구를 자동으로 선택하고 호출합니다.

**ReAct 패턴 (Reasoning + Acting)**
1. 사용자 입력 받음
2. LLM이 어떤 도구를 쓸지 추론
3. 도구 실행 → 결과 받음
4. 추가 도구 필요하면 반복
5. 최종 응답 생성

**예시 흐름**
```
사용자: "내일 3시 신촌에서 친구 만나기"

LLM 추론 → add_schedule 도구 호출
→ 일정 저장됨 (ID: 42)

LLM 추론 → 이동 시간도 확인해야겠다 → check_travel_time 호출
→ "이전 수업에서 90분 이동 필요, 빠듯함"

LLM 최종 응답:
"일정 추가했어요! 📅 11월 27일 15:00 신촌
 ⚠️ 수업 후 이동이 빠듯할 수 있어요"
```

---

## 3. Tool 목록

LLM이 자동으로 선택해서 호출하는 도구들입니다.

| Tool | 설명 | 주요 파라미터 |
|------|------|--------------|
| `add_schedule` | 일정/할일 추가 | title, date, time, location, category |
| `get_schedules_for_date` | 특정 날짜 일정 조회 | date |
| `get_upcoming_tasks` | 다가오는 할일 목록 | days (기본 7일) |
| `complete_schedule` | 완료 처리 | schedule_id |
| `update_schedule` | 일정 수정 | schedule_id, 변경할 필드들 |
| `delete_schedule` | 일정 삭제 | schedule_id |
| `check_travel_time` | 이동 시간 확인 | date, time, new_location |
| `search_schedules` | 키워드 검색 | query |
| `sync_apple_calendar` | 캘린더 동기화 | direction (push/pull/both) |

각 도구는 Python 함수로 구현하며, Gemini Function Calling 형식의 스키마(이름, 설명, 파라미터 타입)를 정의합니다.

---

## 4. 데이터 구조

### 통합 Schedule 모델

캘린더 일정과 리마인더(할일)를 하나의 모델로 통합 관리합니다.

**핵심 필드**
- **기본**: id, title, description
- **날짜/시간**: scheduled_date, start_time, end_time, is_all_day
- **분류**: major_category (학업/약속/개인/업무/루틴/기타), minor_category
- **장소**: location, travel_from_previous (이동시간)
- **마감**: has_deadline, deadline_date, deadline_time
- **상태**: status (예정/진행중/완료/취소)
- **동기화**: sync_to_apple, apple_calendar_id, sync_status

**일정 vs 할일 구분 방식**
- 시간 고정 일정: start_time이 있음
- 할일: start_time 없고, deadline만 있거나 둘 다 없음

### 대분류 카테고리
- 학업: 수업, 과제, 시험
- 약속: 친구, 미팅
- 개인: 병원, 쇼핑, 취미
- 업무: 연구실, 아르바이트
- 루틴: 반복 일정
- 기타

---

## 5. 주요 기능

### 5.1 자연어 일정 추가

사용자가 자연어로 입력하면 LLM이 자동 파싱하여 일정 추가.
- "내일 오후 3시 신촌에서 친구랑 밥" → 날짜, 시간, 장소, 카테고리 자동 추출
- "GPS 과제 금요일까지" → 마감일 있는 할일로 추가
- "치과 예약" → 시간 미정 할일로 추가

### 5.2 이동 시간 자동 확인

일정 추가 시 이전 일정과의 이동 시간을 자동 확인.
- 이전 일정 장소 → 새 일정 장소 이동시간 추정
- 여유 충분/빠듯함/부족 판단하여 경고 표시

이동시간은 자주 가는 경로 캐시 + LLM 추정으로 계산 (외부 지도 API는 선택사항).

### 5.3 3자간 동기화

iOS 앱 ↔ 서버 ↔ Apple 캘린더 자동 동기화.
- 주기적 동기화 (5분 간격)
- 비정기 일정만 Apple 캘린더에 동기화
- 정기 일정(시간표)과 이동 블록은 앱 전용

### 5.4 Discord 명령어

자연어 외에 빠른 조회용 명령어 지원.
- `!today` - 오늘 일정
- `!tomorrow` - 내일 일정
- `!tasks` - 마감 다가오는 할일
- `!done <id>` - 완료 처리

---

## 6. iOS 앱 화면 구성

### 탭 구조
1. **챗봇 (메인)**: 자연어 대화로 일정 관리
2. **달력**: 월간 달력 + 날짜 선택 시 일일 타임라인
3. **할일**: 마감 기준 정렬된 할일 목록

### 일정 추가 방식
1. 챗봇에서 자연어로 요청
2. + 버튼으로 직접 폼 입력

---

## 7. 파일 구조

### 서버 (Python)
```
smart-scheduler-server/
├── agent/           # LLM 에이전트 (ReAct 패턴)
├── tools/           # Tool 정의 및 구현
├── bot/             # Discord Bot
├── data/            # 모델, DB, Repository
├── integrations/    # Apple Calendar, 이동시간 캐시
└── services/        # 동기화, 알림 서비스
```

### iOS (Swift)
```
SmartScheduler/
├── Models/          # Schedule 등 데이터 모델
├── Views/           # Chat, Calendar, Tasks, Add 뷰
├── ViewModels/      # MVVM 뷰모델
└── Services/        # Discord 통신, 로컬 캐시
```

---

## 8. 개발 로드맵

### Phase 1: MVP (2-3주)
- 데이터 모델 및 DB 구현
- 핵심 Tool 구현 (add, get, complete, check_travel)
- LLM Agent (ReAct 패턴)
- Discord Bot 연동
- **완료 조건**: 자연어로 일정 추가하고 이동시간 경고까지 동작

### Phase 2: 스마트 기능 (2주)
- Apple 캘린더 동기화 (CalDAV)
- 스마트 알림 (선택)

### Phase 3: iOS 앱 (3주)
- 챗봇 UI
- 월간 달력 + 일일 타임라인
- 할일 목록
- 직접 추가 폼

---

## 9. 환경 설정

### 필요 API 키
- `DISCORD_BOT_TOKEN` - Discord 봇 토큰
- `DISCORD_CHANNEL_ID` - 사용할 채널 ID
- `GEMINI_API_KEY` - Google Gemini API
- `APPLE_ID` / `APPLE_APP_SPECIFIC_PASSWORD` - iCloud 연동용
- `CALDAV_URL` - Apple 캘린더 CalDAV 주소

---

## 10. 구현 시작 가이드

Claude Code에 이 문서와 함께 다음과 같이 요청:

```
SmartScheduler 프로젝트 구현을 시작해줘.

순서:
1. 프로젝트 폴더 구조 생성
2. requirements.txt (google-generativeai, discord.py, caldav 등)
3. data/models.py - Schedule 데이터클래스
4. data/database.py - SQLite 연결 및 스키마
5. tools/ - Tool 정의 및 구현
6. agent/ - Gemini Function Calling + ReAct 패턴
7. bot/ - Discord Bot

설계 문서의 Tool 목록과 데이터 구조를 참고해줘.
```

---

*작성일: 2025-11-26*
