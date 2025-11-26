# SmartScheduler Mac App 개발 계획서

**목표**: 2D 캐릭터 비서가 함께하는 데스크톱 일정관리 앱 (채팅 + 달력)

---

## 핵심 컨셉

- **세로로 길쭉한 위젯 형태** (360 x 780, Mac 좌측 구석에 띄워두고 사용)
- **3단 구조**: 캐릭터 영역 / 컨텐츠(채팅 or 달력) / 토글 스위치
- **백엔드 통신**: Discord API를 통해 기존 backend 서버와 연동

---

## 기술 스택

- **프레임워크**: Tauri (Rust 기반 경량 데스크톱 앱)
- **프론트엔드**: React + TypeScript
- **스타일링**: CSS Modules 또는 Tailwind CSS
- **상태관리**: React Context 또는 Zustand
- **통신**: Discord REST API (fetch)

---

## 폴더 구조

```
app-mac/
├── src-tauri/              # Tauri (Rust) 설정
│   ├── tauri.conf.json     # 창 크기, 타이틀 등
│   └── ...
├── src/                    # React 소스
│   ├── components/         # 컴포넌트
│   │   ├── Character/      # 캐릭터 영역
│   │   ├── Chat/           # 채팅 관련
│   │   ├── Calendar/       # 달력 관련
│   │   └── Toggle/         # 토글 스위치
│   ├── hooks/              # 커스텀 훅
│   │   ├── useDiscord.ts   # Discord 통신
│   │   └── useCharacter.ts # 캐릭터 상태 관리
│   ├── styles/             # 스타일
│   ├── types/              # TypeScript 타입 정의
│   ├── App.tsx             # 메인 앱
│   └── main.tsx            # 엔트리포인트
├── assets/                 # 정적 파일
│   └── character/          # 캐릭터 이미지 (나중에)
├── package.json
└── README.md
```

---

## Phase 1: 기본 틀 (뼈대)

### 1.1 Tauri + React 프로젝트 생성
- [ ] **IMPL**: `create-tauri-app`으로 프로젝트 초기화
- [ ] **IMPL**: TypeScript 설정 확인
- [ ] **IMPL**: `npm run tauri dev` 동작 확인

### 1.2 창 설정
- [ ] **IMPL**: tauri.conf.json에서 창 크기 설정 (360 x 640)
- [ ] **IMPL**: 리사이즈 비활성화
- [ ] **IMPL**: 타이틀바 커스텀 또는 숨김 (선택)

### 1.3 3단 레이아웃 구현
- [ ] **IMPL**: Layout 컴포넌트 생성
- [ ] **IMPL**: 캐릭터 영역 (고정 높이, 16:9 비율)
- [ ] **IMPL**: 컨텐츠 영역 (가변 높이, 스크롤 가능)
- [ ] **IMPL**: 토글 영역 (고정 높이)

### 1.4 토글 스위치 구현
- [ ] **IMPL**: Toggle 컴포넌트 생성
- [ ] **IMPL**: 채팅 ↔ 달력 상태 관리
- [ ] **IMPL**: 슬라이드 애니메이션
- [ ] **IMPL**: 클릭/드래그로 전환

### 1.5 캐릭터 상태 시스템
- [ ] **IMPL**: useCharacter 훅 생성
- [ ] **IMPL**: 상태 종류 정의 (idle, thinking, action, looking_down)
- [ ] **IMPL**: 상태 텍스트로 표시 (개발용 플레이스홀더)
- [ ] **IMPL**: 모드 전환 시 상태 변경 (idle ↔ looking_down)

---

## Phase 2: 채팅 기능

### 2.1 메시지 UI
- [ ] **IMPL**: ChatContainer 컴포넌트 생성
- [ ] **IMPL**: MessageList 컴포넌트 (스크롤 가능)
- [ ] **IMPL**: MessageItem 컴포넌트 (사용자/봇/시스템 구분)
- [ ] **IMPL**: MessageInput 컴포넌트 (입력창 + 전송 버튼)

### 2.2 메시지 상태 관리
- [ ] **IMPL**: 메시지 타입 정의 (user, bot, system)
- [ ] **IMPL**: 메시지 목록 상태 관리
- [ ] **IMPL**: 새 메시지 추가 시 자동 스크롤

### 2.3 Discord API 연동 - 전송
- [ ] **IMPL**: useDiscord 훅 생성
- [ ] **IMPL**: 설정값 로드 (Bot Token, Channel ID)
- [ ] **IMPL**: POST /channels/{channel_id}/messages 구현
- [ ] **IMPL**: 에러 핸들링

### 2.4 Discord API 연동 - 수신
- [ ] **IMPL**: GET /channels/{channel_id}/messages 구현
- [ ] **IMPL**: 폴링 로직 (1초 간격)
- [ ] **IMPL**: 마지막 메시지 ID 이후만 조회
- [ ] **IMPL**: 봇 메시지만 필터링

### 2.5 캐릭터 상태 연동
- [ ] **IMPL**: 메시지 전송 시 → thinking
- [ ] **IMPL**: 응답 수신 시 → action
- [ ] **IMPL**: 일정 시간 후 → idle (타이머)

### 2.6 빠른 명령어 (선택)
- [ ] **IMPL**: `!` 로 시작하면 명령어 인식
- [ ] **IMPL**: !today, !tomorrow, !tasks 등 지원
- [ ] **IMPL**: 자동완성 힌트 표시 (선택)

---

## Phase 3: 달력 기능

### 3.1 월간 달력 UI
- [ ] **IMPL**: MonthCalendar 컴포넌트 생성
- [ ] **IMPL**: 달력 그리드 표시 (7열 x 6행)
- [ ] **IMPL**: 상단에 월 표시 + 이전/다음 버튼
- [ ] **IMPL**: 오늘 날짜 강조 표시
- [ ] **IMPL**: 일정 있는 날짜에 점(dot) 표시

### 3.2 일간 시간표 UI
- [ ] **IMPL**: DaySchedule 컴포넌트 생성
- [ ] **IMPL**: 3일 뷰 (어제/오늘/내일)
- [ ] **IMPL**: 세로축 시간 표시 (06:00 ~ 24:00)
- [ ] **IMPL**: 상단에 뒤로가기 버튼

### 3.3 일정 블록 표시
- [ ] **IMPL**: ScheduleBlock 컴포넌트 생성
- [ ] **IMPL**: 카테고리별 색상 구분
  - 학업: 파랑
  - 약속: 초록
  - 개인: 보라
  - 업무: 주황
  - 루틴: 하늘색
  - 기타: 회색
- [ ] **IMPL**: 블록에 제목 표시 (말줄임 처리)
- [ ] **IMPL**: 블록 탭 시 상세 정보 표시

### 3.4 네비게이션
- [ ] **IMPL**: 월간 달력에서 날짜 클릭 → 일간 시간표
- [ ] **IMPL**: 일간 시간표에서 스와이프로 날짜 이동
- [ ] **IMPL**: 뒤로가기 → 월간 달력 복귀

### 3.5 더미 데이터 연동
- [ ] **IMPL**: 일정 타입 정의 (types/schedule.ts)
- [ ] **IMPL**: 더미 일정 데이터로 UI 테스트

---

## Phase 4: 통합 및 마무리

### 4.1 서버 응답 파싱
- [ ] **IMPL**: 서버 응답에서 일정 데이터 추출 로직
- [ ] **IMPL**: 파싱된 데이터로 달력 업데이트
- [ ] **IMPL**: 파싱 실패 시 에러 핸들링

### 4.2 로컬 캐시 (선택)
- [ ] **IMPL**: 최근 대화 내역 저장 (앱 재시작 시 복원)
- [ ] **IMPL**: 일정 데이터 캐시 (오프라인 조회용)
- [ ] **IMPL**: Tauri fs API 또는 localStorage 사용

### 4.3 설정 화면
- [ ] **IMPL**: 설정 화면 또는 설정 파일 관리
- [ ] **IMPL**: Bot Token, Channel ID 입력/저장
- [ ] **IMPL**: 첫 실행 시 설정 안내

### 4.4 창 속성 마무리
- [ ] **IMPL**: "항상 위에" 옵션 제공
- [ ] **IMPL**: 시스템 트레이 상주 (선택)
- [ ] **IMPL**: 타이틀바 최종 조정

### 4.5 캐릭터 이미지 교체 준비
- [ ] **IMPL**: 플레이스홀더 → 실제 GIF/이미지 교체 가능한 구조
- [ ] **IMPL**: 이미지 네이밍 규칙: character_idle.gif 등

### 4.6 문서화
- [ ] **DOCS**: README.md - 설치 및 실행 방법
- [ ] **DOCS**: 빌드 및 배포 가이드

---

## 진행 상태 추적

| Phase | 상태 | 시작 | 완료 |
|-------|------|------|------|
| 1. 기본 틀 | ⏳ 대기 | - | - |
| 2. 채팅 기능 | ⏳ 대기 | - | - |
| 3. 달력 기능 | ⏳ 대기 | - | - |
| 4. 통합/마무리 | ⏳ 대기 | - | - |

---

## 참고 문서

- **설계 문서**: SmartScheduler-Desktop-개발계획서.md
- **백엔드 계획서**: PLAN_BACKEND.md

---

*작성일: 2025-11-26*
*설계문서 참조: SmartScheduler-Desktop-개발계획서.md*
