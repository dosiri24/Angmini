# SmartScheduler Desktop App 디자인 리뉴얼 계획서

> 토스 스타일의 깔끔하고 직관적인 UI/UX로 전면 개편

---

## 1. 현재 디자인 문제점 진단

### 1-1. 색상 체계
| 문제 | 상세 |
|------|------|
| 그라데이션 남용 | 보라-핑크 그라데이션이 2010년대 앱 느낌을 줌 |
| 포인트 컬러 불명확 | 보라, 핑크, 파랑이 혼재되어 통일감 없음 |
| 배경과 요소 충돌 | 채팅 버블이 그라데이션 배경에 묻힘 |

### 1-2. 채팅 UI
| 문제 | 상세 |
|------|------|
| 버블 가독성 | 어두운 반투명 버블이 배경과 대비 부족 |
| 모서리 과다 | 버블 radius가 너무 커서 장난감 같은 느낌 |
| 시간 표시 | 너무 연하고 작아서 잘 안 보임 |

### 1-3. 입력창 & 탭바
| 문제 | 상세 |
|------|------|
| 입력창 배경 | 어두운 색이라 전체적으로 무겁고 답답함 |
| 전송 버튼 | 그라데이션 원형으로 현대적 디자인과 거리 멂 |
| 탭바 하이라이트 | 보라색이 위 그라데이션과 또 충돌 |

---

## 2. 디자인 원칙

### 2-1. 핵심 철학
```
"Less is More" - 미니멀리즘
"One Page, One Thing" - 토스 철학 차용
```

### 2-2. 적용할 UX 원칙
- **단순함**: 불필요한 장식 요소 제거
- **일관성**: 하나의 포인트 컬러로 통일
- **가독성**: 충분한 대비와 여백
- **직관성**: 3초 안에 이해되는 UI

---

## 3. 새로운 색상 시스템

### 3-1. 다크 모드 팔레트 (Primary)

```css
/* 배경 계층 */
--bg-primary: #0F0F0F;      /* 최하단 배경 */
--bg-secondary: #1A1A1A;    /* 카드/컨테이너 배경 */
--bg-tertiary: #252525;     /* 입력창, 호버 상태 */

/* 텍스트 */
--text-primary: #FFFFFF;     /* 주요 텍스트 (opacity 87%) */
--text-secondary: #A0A0A0;   /* 보조 텍스트 (시간 등) */
--text-tertiary: #666666;    /* 비활성 텍스트 */

/* 포인트 컬러 - 토스 블루 계열 */
--accent-primary: #3182F6;   /* 메인 액센트 (토스 블루) */
--accent-secondary: #1B64DA; /* 호버/액티브 상태 */
--accent-subtle: rgba(49, 130, 246, 0.15); /* 배경용 연한 버전 */

/* 채팅 버블 */
--bubble-user: #3182F6;      /* 사용자 메시지 */
--bubble-bot: #2A2A2A;       /* 봇 메시지 */

/* 시스템 */
--border: #333333;           /* 구분선 */
--success: #34C759;          /* 성공 */
--error: #FF3B30;            /* 에러 */
```

### 3-2. 라이트 모드 팔레트 (Optional - 추후 구현)

```css
--bg-primary: #FFFFFF;
--bg-secondary: #F7F8FA;
--bg-tertiary: #ECEEF0;
--text-primary: #191F28;
--text-secondary: #6B7684;
--accent-primary: #3182F6;
```

---

## 4. 컴포넌트별 수정 사항

### 4-1. 채팅 영역 배경

**Before:**
```css
background: linear-gradient(to bottom, #667eea, #764ba2);
```

**After:**
```css
background: #0F0F0F;
/* 또는 캐릭터 영역과 자연스럽게 연결되는 단색 */
```

### 4-2. 채팅 버블

**Before:**
- 봇: 어두운 반투명 회색, 과한 border-radius
- 사용자: 보라색, 그라데이션과 충돌

**After:**

```css
/* 사용자 메시지 (오른쪽) */
.message-user {
  background: #3182F6;
  color: #FFFFFF;
  border-radius: 18px 18px 4px 18px;
  padding: 12px 16px;
  max-width: 75%;
}

/* 봇 메시지 (왼쪽) */
.message-bot {
  background: #2A2A2A;
  color: #FFFFFF;
  border-radius: 18px 18px 18px 4px;
  padding: 12px 16px;
  max-width: 75%;
}

/* 시간 표시 */
.message-time {
  font-size: 11px;
  color: #808080;
  margin-top: 4px;
}
```

**디자인 포인트:**
- 보낸 쪽 모서리만 작게 (방향성 표시)
- 적당한 radius (18px)로 부드럽지만 과하지 않게
- 시간은 버블 외부 하단에 표시

### 4-3. 메시지 입력창

**Before:**
- 어두운 배경에 둥근 입력창
- 그라데이션 전송 버튼

**After:**

```css
/* 입력 영역 컨테이너 */
.input-container {
  background: #1A1A1A;
  padding: 12px 16px;
  border-top: 1px solid #252525;
}

/* 입력창 */
.input-field {
  background: #252525;
  border: none;
  border-radius: 20px;
  padding: 10px 16px;
  color: #FFFFFF;
  font-size: 15px;
}

.input-field::placeholder {
  color: #666666;
}

/* 전송 버튼 */
.send-button {
  background: #3182F6;
  border: none;
  border-radius: 50%;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.send-button:disabled {
  background: #333333;
}

.send-button svg {
  color: #FFFFFF;
  width: 18px;
  height: 18px;
}
```

### 4-4. 탭바 (채팅/달력 전환)

**Before:**
- 보라색 하이라이트
- 두꺼운 스타일

**After:**

```css
/* 탭바 컨테이너 */
.tab-bar {
  background: #1A1A1A;
  padding: 8px 16px 8px 16px;
  display: flex;
  gap: 8px;
}

/* 탭 버튼 공통 */
.tab-button {
  flex: 1;
  padding: 10px 16px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  border: none;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

/* 선택된 탭 */
.tab-button.active {
  background: #3182F6;
  color: #FFFFFF;
}

/* 선택 안 된 탭 */
.tab-button.inactive {
  background: transparent;
  color: #808080;
}

.tab-button.inactive:hover {
  background: #252525;
  color: #FFFFFF;
}
```

### 4-5. 설정 버튼 (우측 상단)

```css
.settings-button {
  background: rgba(255, 255, 255, 0.1);
  border: none;
  border-radius: 8px;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.settings-button:hover {
  background: rgba(255, 255, 255, 0.15);
}

.settings-button svg {
  color: #FFFFFF;
  opacity: 0.7;
  width: 18px;
  height: 18px;
}
```

---

## 5. 타이포그래피

### 5-1. 폰트 설정

```css
font-family: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 
             'Pretendard', sans-serif;
```

### 5-2. 폰트 크기 체계

| 용도 | 크기 | 굵기 |
|------|------|------|
| 앱 타이틀 | 17px | 600 (Semibold) |
| 메시지 본문 | 15px | 400 (Regular) |
| 보조 텍스트 (시간) | 11px | 400 (Regular) |
| 탭 라벨 | 14px | 500 (Medium) |
| 입력창 placeholder | 15px | 400 (Regular) |

---

## 6. 간격 및 여백 시스템

### 6-1. 기본 단위
```css
--spacing-xs: 4px;
--spacing-sm: 8px;
--spacing-md: 12px;
--spacing-lg: 16px;
--spacing-xl: 24px;
```

### 6-2. 메시지 간격
- 같은 발신자 연속 메시지: 4px
- 다른 발신자 메시지: 16px
- 메시지와 시간 사이: 4px

---

## 7. 애니메이션 & 트랜지션

### 7-1. 기본 트랜지션
```css
--transition-fast: 0.15s ease;
--transition-normal: 0.2s ease;
--transition-slow: 0.3s ease;
```

### 7-2. 적용 대상
- 버튼 호버/클릭: `transition-fast`
- 탭 전환: `transition-normal`
- 모달/패널 열기: `transition-slow`

### 7-3. 메시지 등장 애니메이션

```css
@keyframes messageSlideIn {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message-new {
  animation: messageSlideIn 0.2s ease;
}
```

---

## 8. 수정 우선순위

### Phase 1: 색상 & 배경 (즉시)
1. ✅ 그라데이션 배경 → 단색 다크 배경으로 변경
2. ✅ 포인트 컬러를 토스 블루(#3182F6)로 통일

### Phase 2: 채팅 UI (핵심)
3. ✅ 채팅 버블 스타일 전면 수정
4. ✅ 시간 표시 가독성 개선
5. ✅ 입력창 스타일 수정

### Phase 3: 네비게이션 (마무리)
6. ✅ 탭바 스타일 수정
7. ✅ 설정 버튼 스타일 수정

---

## 9. 예상 결과물 (Before/After)

### Before
```
┌─────────────────────┐
│ ▓▓ 그라데이션 배경 ▓▓ │
│                     │
│  [반투명회색버블]     │
│         [보라색버블] │
│                     │
│ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ │
│ [어두운입력창] (◐)  │
│ [■보라] 채팅  달력  │
└─────────────────────┘
```

### After
```
┌─────────────────────┐
│ ■■ 단색 다크 배경 ■■ │
│                     │
│  [#2A2A2A 버블]      │
│          [파란버블]  │
│     오후 3:32       │
│                     │
│─────────────────────│
│ [#252525 입력창] (●) │
│ [●파랑] 채팅  달력   │
└─────────────────────┘
```

---

## 10. 참고 자료

### 디자인 레퍼런스
- 토스 앱
- Apple Messages
- Telegram
- ChatGPT 앱

### 색상 참고
- 토스 블루: #3182F6
- Material Design Dark Theme
- Apple Human Interface Guidelines (Dark Mode)

---

## 11. 체크리스트

작업 완료 후 확인할 사항:

- [ ] 모든 텍스트가 배경과 충분한 대비를 가지는가? (최소 4.5:1)
- [ ] 포인트 컬러가 #3182F6으로 통일되었는가?
- [ ] 그라데이션이 완전히 제거되었는가?
- [ ] 버블 모서리가 적절한가? (18px 권장)
- [ ] 시간 표시가 잘 보이는가?
- [ ] 탭 전환이 명확하게 구분되는가?
- [ ] 전체적으로 "토스 같은" 깔끔함이 느껴지는가?

---

## 12. 추가 수정 사항 (달력 & 설정)

### 12-1. 일간 시간표 개선

#### 오늘 날짜 강조 방식 변경

현재 오늘 날짜 컬럼 전체가 파란색으로 채워져 있어서, 일정이 없는데도 일정이 있는 것처럼 보이는 문제가 있음.

**Before:**
- 오늘 컬럼 전체를 진한 파란색으로 채움 → 혼란 유발

**After:**
- 컬럼 헤더에만 강조 표시
- 컬럼 배경은 아주 미세하게만 구분

```css
/* 오늘 날짜 컬럼 헤더 */
.day-column-header.today {
  background: rgba(49, 130, 246, 0.2);
  border-radius: 8px;
  color: #3182F6;
  font-weight: 600;
  padding: 8px 12px;
}

/* 오늘 컬럼 배경 - 아주 미세하게 */
.day-column.today {
  background: rgba(49, 130, 246, 0.03);
}

/* 일반 컬럼 */
.day-column {
  background: transparent;
}
```

#### 3일 뷰 날짜 헤더 추가

현재 각 컬럼이 며칠인지 표시가 없어서 일정이 언제인지 파악하기 어려움.

**Before:**
```
← 월간    11월 27일
09:00  |     [블록]    |           |
10:00  |     [블록]    |           |
```

**After:**
```
← 월간    11월 27일
         26(수)    27(목)    28(금)
09:00  |          |           |
10:00  |          |    [일정]  |
```

```css
/* 날짜 헤더 컨테이너 */
.day-headers {
  display: flex;
  border-bottom: 1px solid #252525;
  padding: 8px 0;
  margin-left: 50px; /* 시간 컬럼 너비만큼 */
}

/* 개별 날짜 헤더 */
.day-header {
  flex: 1;
  text-align: center;
  font-size: 13px;
  color: #A0A0A0;
}

.day-header.today {
  color: #3182F6;
  font-weight: 600;
}

.day-header .date {
  font-size: 15px;
  font-weight: 500;
}

.day-header .weekday {
  font-size: 12px;
  margin-top: 2px;
}
```

#### 시간 구분선 버그 수정

17:00 이후 시간 구분선이 누락되는 버그 수정 필요.

```css
/* 시간 구분선 - 전체 높이에 걸쳐 표시되도록 */
.time-grid-line {
  position: absolute;
  left: 50px;
  right: 0;
  height: 1px;
  background: #252525;
}

/* 시간 라벨 */
.time-label {
  position: absolute;
  left: 0;
  width: 45px;
  font-size: 11px;
  color: #666666;
  text-align: right;
  padding-right: 8px;
}
```

---

### 12-2. 설정 모달 개선

#### "연결됨" 상태 뱃지

현재 파란색/보라색이라 "성공" 느낌이 약함. 초록색으로 변경.

**Before:**
```css
.status-badge {
  background: #3182F6; /* 파란색 */
}
```

**After:**
```css
/* 연결됨 상태 */
.status-badge.connected {
  background: rgba(52, 199, 89, 0.15);
  color: #34C759;
  padding: 6px 12px;
  border-radius: 16px;
  font-size: 13px;
  font-weight: 500;
}

/* 연결 안됨 상태 */
.status-badge.disconnected {
  background: rgba(255, 59, 48, 0.15);
  color: #FF3B30;
}

/* 연결 중 상태 */
.status-badge.connecting {
  background: rgba(255, 204, 0, 0.15);
  color: #FFCC00;
}
```

#### 섹션 구분 강화

현재 구분선만으로는 섹션 간 구분이 약함.

```css
/* 섹션 컨테이너 */
.settings-section {
  margin-top: 28px;
  padding-top: 20px;
  border-top: 1px solid #252525;
}

.settings-section:first-child {
  margin-top: 0;
  padding-top: 0;
  border-top: none;
}

/* 섹션 타이틀 */
.settings-section-title {
  font-size: 12px;
  font-weight: 600;
  color: #666666;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  margin-bottom: 16px;
}
```

#### 토글 스위치 색상 통일

OFF 상태가 흰색이라 포인트 컬러와 통일감이 떨어짐.

```css
/* 토글 스위치 트랙 */
.toggle-track {
  width: 51px;
  height: 31px;
  border-radius: 16px;
  transition: background 0.2s ease;
}

/* OFF 상태 */
.toggle-track.off {
  background: #333333;
}

/* ON 상태 */
.toggle-track.on {
  background: #3182F6;
}

/* 토글 원형 노브 */
.toggle-knob {
  width: 27px;
  height: 27px;
  border-radius: 50%;
  background: #FFFFFF;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  transition: transform 0.2s ease;
}

.toggle-track.on .toggle-knob {
  transform: translateX(20px);
}
```

#### 설명 텍스트 가독성 개선

현재 너무 연해서 잘 안 보임.

```css
/* 입력 필드 라벨 */
.input-label {
  font-size: 14px;
  font-weight: 500;
  color: #FFFFFF;
  margin-bottom: 8px;
}

/* 입력 필드 설명 (helper text) */
.input-description {
  font-size: 12px;
  color: #888888;  /* 기존보다 밝게 */
  margin-top: 8px;
  line-height: 1.4;
}

/* 입력 필드 */
.input-field {
  background: #252525;
  border: 1px solid #333333;
  border-radius: 10px;
  padding: 12px 14px;
  font-size: 15px;
  color: #FFFFFF;
  width: 100%;
}

.input-field:focus {
  border-color: #3182F6;
  outline: none;
}

.input-field::placeholder {
  color: #555555;
}
```

#### 모달 전체 스타일

```css
/* 모달 오버레이 */
.modal-overlay {
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
}

/* 모달 컨테이너 */
.modal-container {
  background: #1A1A1A;
  border-radius: 16px;
  padding: 24px;
  max-width: 340px;
  max-height: 80vh;
  overflow-y: auto;
}

/* 모달 헤더 */
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.modal-title {
  font-size: 18px;
  font-weight: 600;
  color: #FFFFFF;
}

/* 닫기 버튼 */
.modal-close {
  background: transparent;
  border: none;
  color: #666666;
  font-size: 24px;
  cursor: pointer;
  padding: 4px;
}

.modal-close:hover {
  color: #FFFFFF;
}
```

---

## 13. 수정 우선순위 (업데이트)

### Phase 1: 색상 & 배경 (즉시)
1. ✅ 그라데이션 배경 → 단색 다크 배경으로 변경
2. ✅ 포인트 컬러를 토스 블루(#3182F6)로 통일

### Phase 2: 채팅 UI (핵심)
3. ✅ 채팅 버블 스타일 전면 수정
4. ✅ 시간 표시 가독성 개선
5. ✅ 입력창 스타일 수정

### Phase 3: 네비게이션 (마무리)
6. ✅ 탭바 스타일 수정
7. ✅ 설정 버튼 스타일 수정

### Phase 4: 달력 UI (추가)
8. ✅ 일간 시간표 - 오늘 컬럼 강조 방식 변경
9. ✅ 일간 시간표 - 3일 뷰 날짜 헤더 추가
10. ✅ 일간 시간표 - 시간 구분선 버그 수정

### Phase 5: 설정 모달 (추가)
11. ✅ "연결됨" 뱃지 초록색으로 변경
12. ✅ 섹션 구분 스타일 강화
13. ✅ 토글 스위치 색상 통일
14. ✅ 설명 텍스트 가독성 개선

---

## 14. 최종 체크리스트

### 공통
- [ ] 모든 텍스트가 배경과 충분한 대비를 가지는가? (최소 4.5:1)
- [ ] 포인트 컬러가 #3182F6으로 통일되었는가?
- [ ] 그라데이션이 완전히 제거되었는가?

### 채팅
- [ ] 버블 모서리가 적절한가? (18px 권장)
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

*이 계획서를 기반으로 CSS/스타일 파일을 수정해주세요.*
