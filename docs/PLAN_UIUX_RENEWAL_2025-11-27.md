# SmartScheduler UI/UX 리뉴얼 계획서 (2025-11-27)

**버전**: v1.0
**작성일**: 2025-11-27
**목표**: 토스 스타일의 깔끔하고 직관적인 UI/UX로 전면 개편

---

## 핵심 컨셉

- **미니멀리즘**: "Less is More" - 불필요한 장식 요소 제거
- **토스 철학**: "One Page, One Thing" - 직관적이고 3초 안에 이해되는 UI
- **일관성**: 하나의 포인트 컬러(#3182F6)로 통일
- **가독성**: 충분한 대비(최소 4.5:1)와 여백

---

## 디자인 시스템

### 색상 팔레트 (다크 모드)

| 용도 | 변수명 | 값 |
|------|--------|-----|
| 최하단 배경 | `--bg-primary` | #0F0F0F |
| 카드/컨테이너 | `--bg-secondary` | #1A1A1A |
| 입력창/호버 | `--bg-tertiary` | #252525 |
| 주요 텍스트 | `--text-primary` | #FFFFFF (87%) |
| 보조 텍스트 | `--text-secondary` | #A0A0A0 |
| 비활성 텍스트 | `--text-tertiary` | #666666 |
| 메인 액센트 | `--accent-primary` | #3182F6 |
| 호버/액티브 | `--accent-secondary` | #1B64DA |
| 사용자 버블 | `--bubble-user` | #3182F6 |
| 봇 버블 | `--bubble-bot` | #2A2A2A |
| 구분선 | `--border` | #333333 |
| 성공 | `--success` | #34C759 |
| 에러 | `--error` | #FF3B30 |

### 타이포그래피

| 용도 | 크기 | 굵기 |
|------|------|------|
| 앱 타이틀 | 17px | 600 |
| 메시지 본문 | 15px | 400 |
| 보조 텍스트 | 11px | 400 |
| 탭 라벨 | 14px | 500 |
| 입력창 placeholder | 15px | 400 |

### 간격 시스템

```
--spacing-xs: 4px
--spacing-sm: 8px
--spacing-md: 12px
--spacing-lg: 16px
--spacing-xl: 24px
```

---

## 관련 파일

```
app-mac/src/
├── styles/
│   ├── index.css           # 전역 CSS 변수
│   ├── Chat.module.css     # 채팅 컴포넌트 스타일
│   ├── Calendar.module.css # 달력 컴포넌트 스타일
│   └── Settings.module.css # 설정 모달 스타일 (신규)
├── components/
│   ├── Chat/
│   │   ├── MessageItem.tsx
│   │   └── MessageInput.tsx
│   ├── Calendar/
│   │   ├── DaySchedule.tsx
│   │   └── MonthCalendar.tsx
│   └── Toggle/
│       └── Toggle.tsx
└── App.tsx
```

---

## Phase 1: 색상 & 배경 시스템

### 1.1 전역 CSS 변수 정의
- [ ] **IMPL**: index.css에 새 색상 변수 추가
- [ ] **IMPL**: 기존 그라데이션 색상 변수 제거
- [ ] **IMPL**: 타이포그래피 변수 추가
- [ ] **IMPL**: 간격 변수 추가

### 1.2 배경 그라데이션 제거
- [ ] **IMPL**: 채팅 영역 배경 → #0F0F0F 단색
- [ ] **IMPL**: 캐릭터 영역과 자연스럽게 연결
- [ ] **IMPL**: 전체 레이아웃 배경색 통일

### 1.3 포인트 컬러 통일
- [ ] **IMPL**: 모든 액센트 색상 → #3182F6
- [ ] **IMPL**: 기존 보라색(#667eea, #764ba2) 제거

---

## Phase 2: 채팅 UI 개선

### 2.1 채팅 버블 스타일
- [ ] **IMPL**: 사용자 버블 - #3182F6, radius: 18px 18px 4px 18px
- [ ] **IMPL**: 봇 버블 - #2A2A2A, radius: 18px 18px 18px 4px
- [ ] **IMPL**: max-width: 75%로 제한
- [ ] **IMPL**: padding: 12px 16px

### 2.2 시간 표시 개선
- [ ] **IMPL**: font-size: 11px, color: #808080
- [ ] **IMPL**: 버블 외부 하단에 표시
- [ ] **IMPL**: margin-top: 4px

### 2.3 입력창 스타일
- [ ] **IMPL**: 컨테이너 배경 #1A1A1A
- [ ] **IMPL**: 입력 필드 배경 #252525, radius: 20px
- [ ] **IMPL**: border-top: 1px solid #252525
- [ ] **IMPL**: placeholder 색상 #666666

### 2.4 전송 버튼 스타일
- [ ] **IMPL**: 배경 #3182F6, radius: 50%
- [ ] **IMPL**: 크기: 36x36px
- [ ] **IMPL**: disabled 상태: #333333
- [ ] **IMPL**: 그라데이션 제거

### 2.5 메시지 애니메이션
- [ ] **IMPL**: 새 메시지 등장 - slideIn (opacity + translateY)
- [ ] **IMPL**: 애니메이션 duration: 0.2s ease

---

## Phase 3: 탭바 & 네비게이션

### 3.1 탭바 컨테이너
- [ ] **IMPL**: 배경 #1A1A1A
- [ ] **IMPL**: padding: 8px 16px
- [ ] **IMPL**: gap: 8px

### 3.2 탭 버튼 스타일
- [ ] **IMPL**: 공통 - flex: 1, radius: 10px, font: 14px/500
- [ ] **IMPL**: 활성 탭 - 배경 #3182F6, 텍스트 #FFFFFF
- [ ] **IMPL**: 비활성 탭 - 배경 transparent, 텍스트 #808080
- [ ] **IMPL**: 호버 - 배경 #252525, 텍스트 #FFFFFF
- [ ] **IMPL**: transition: 0.2s ease

### 3.3 설정 버튼 스타일
- [ ] **IMPL**: 배경 rgba(255, 255, 255, 0.1)
- [ ] **IMPL**: 크기: 32x32px, radius: 8px
- [ ] **IMPL**: 아이콘 색상 #FFFFFF (opacity 0.7)
- [ ] **IMPL**: 호버 시 opacity 증가

---

## Phase 4: 달력 UI 개선

### 4.1 오늘 날짜 강조 변경
- [ ] **IMPL**: 컬럼 전체 강조 → 헤더만 강조로 변경
- [ ] **IMPL**: 헤더 배경 rgba(49, 130, 246, 0.2)
- [ ] **IMPL**: 헤더 텍스트 #3182F6, font-weight: 600
- [ ] **IMPL**: 컬럼 배경 rgba(49, 130, 246, 0.03) - 미세하게만

### 4.2 3일 뷰 날짜 헤더 추가
- [ ] **IMPL**: 날짜 헤더 영역 추가 (26(수) / 27(목) / 28(금))
- [ ] **IMPL**: border-bottom: 1px solid #252525
- [ ] **IMPL**: 오늘 날짜 헤더 색상 #3182F6
- [ ] **IMPL**: 날짜 font-size: 15px, 요일 font-size: 12px

### 4.3 시간 구분선 버그 수정
- [ ] **IMPL**: 17:00 이후 구분선 누락 수정
- [ ] **IMPL**: 시간 라벨 font-size: 11px, color: #666666
- [ ] **IMPL**: 구분선 색상 #252525

### 4.4 월간 달력 스타일 통일
- [ ] **IMPL**: 오늘 날짜 표시 #3182F6 (그라데이션 제거)
- [ ] **IMPL**: 일정 점(dot) 색상 통일

---

## Phase 5: 설정 모달 개선

### 5.1 모달 기본 스타일
- [x] **IMPL**: 오버레이 rgba(0, 0, 0, 0.6) + blur(4px)
- [x] **IMPL**: 컨테이너 배경 #1A1A1A, radius: 16px
- [x] **IMPL**: max-width: 340px, padding: 24px
- [x] **IMPL**: 헤더 font-size: 18px, font-weight: 600

### 5.2 연결 상태 뱃지 개선
- [x] **IMPL**: 연결됨 - 배경 rgba(52, 199, 89, 0.15), 텍스트 #34C759
- [x] **IMPL**: 연결 안됨 - 배경 rgba(255, 59, 48, 0.15), 텍스트 #FF3B30
- [x] **IMPL**: 연결 중 - 배경 rgba(255, 204, 0, 0.15), 텍스트 #FFCC00

### 5.3 섹션 구분 강화
- [x] **IMPL**: 섹션 간격 margin-top: 28px, padding-top: 20px
- [x] **IMPL**: border-top: 1px solid #252525
- [x] **IMPL**: 섹션 타이틀 font-size: 12px, uppercase, letter-spacing: 0.8px

### 5.4 토글 스위치 개선
- [x] **IMPL**: OFF 상태 배경 #333333 (흰색 → 회색)
- [x] **IMPL**: ON 상태 배경 #3182F6
- [x] **IMPL**: 노브 크기: 27x27px, box-shadow 추가
- [x] **IMPL**: transition: 0.2s ease

### 5.5 입력 필드 스타일
- [x] **IMPL**: 라벨 font-size: 14px, font-weight: 500
- [x] **IMPL**: 설명 텍스트 color: #888888 (기존보다 밝게)
- [x] **IMPL**: 필드 배경 #252525, border: 1px solid #333333
- [x] **IMPL**: focus 시 border-color: #3182F6

---

## Phase 6: 애니메이션 & 트랜지션 통일

### 6.1 트랜지션 변수 정의
- [x] **IMPL**: --transition-fast: 0.15s ease
- [x] **IMPL**: --transition-normal: 0.2s ease
- [x] **IMPL**: --transition-slow: 0.3s ease

### 6.2 적용 대상 정리
- [x] **IMPL**: 버튼 호버/클릭 → fast
- [x] **IMPL**: 탭 전환 → normal
- [x] **IMPL**: 모달 열기/닫기 → slow
- [x] **IMPL**: 메시지 등장 → normal

---

## 진행 상태 추적

| Phase | 상태 | 시작 | 완료 |
|-------|------|------|------|
| 1. 색상 & 배경 | ✅ 완료 | 2025-11-27 17:30 | 2025-11-27 17:33 |
| 2. 채팅 UI | ✅ 완료 | 2025-11-27 17:33 | 2025-11-27 17:35 |
| 3. 탭바 & 네비게이션 | ✅ 완료 | 2025-11-27 17:35 | 2025-11-27 17:36 |
| 4. 달력 UI | ✅ 완료 | 2025-11-27 17:37 | 2025-11-27 17:38 |
| 5. 설정 모달 | ✅ 완료 | 2025-11-27 18:50 | 2025-11-27 18:52 |
| 6. 애니메이션 | ✅ 완료 | 2025-11-27 18:52 | 2025-11-27 18:55 |

---

## 최종 체크리스트

### 공통
- [ ] 모든 텍스트가 배경과 충분한 대비(최소 4.5:1)를 가지는가?
- [ ] 포인트 컬러가 #3182F6으로 통일되었는가?
- [ ] 그라데이션이 완전히 제거되었는가?

### 채팅
- [ ] 버블 모서리가 적절한가? (18px)
- [ ] 시간 표시가 잘 보이는가?
- [ ] 입력창이 깔끔한가?

### 달력
- [ ] 오늘 날짜 강조가 헤더로만 되어있는가?
- [ ] 3일 뷰에 날짜 헤더가 표시되는가?
- [ ] 시간 구분선이 전체 시간대에 표시되는가?

### 설정
- [ ] "연결됨" 뱃지가 초록색인가?
- [ ] 섹션 구분이 명확한가?
- [ ] 토글 ON/OFF 색상이 통일되었는가?
- [ ] 설명 텍스트가 잘 보이는가?

### 전체
- [ ] 탭 전환이 명확하게 구분되는가?
- [ ] 전체적으로 "토스 같은" 깔끔함이 느껴지는가?

---

## 참고 문서

- **원본 계획서**: SmartScheduler-디자인-리뉴얼-계획서.md
- **앱 개발 계획서**: docs/PLAN_APP_MAC.md
- **디자인 레퍼런스**: 토스 앱, Apple Messages, Telegram, ChatGPT 앱

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| v1.0 | 2025-11-27 | 초안 작성 |

---

*작성일: 2025-11-27*
*문서 ID: PLAN_UIUX_RENEWAL_2025-11-27*
*참조: SmartScheduler-디자인-리뉴얼-계획서.md*
