# SmartScheduler Desktop App

2D 캐릭터 비서가 함께하는 데스크톱 일정관리 앱 (채팅 + 달력)

## 개요

- **형태**: 세로로 길쭉한 위젯 (360 x 780)
- **구조**: 캐릭터 영역 / 컨텐츠(채팅 or 달력) / 토글 스위치
- **백엔드 통신**: Discord API를 통해 기존 backend 서버와 연동

## 기술 스택

- **프레임워크**: Tauri v2 (Rust 기반 경량 데스크톱 앱)
- **프론트엔드**: React + TypeScript
- **스타일링**: CSS
- **통신**: Discord REST API (Tauri HTTP Plugin)

## 사전 요구사항

- Node.js 18+
- Rust (최신 stable)
- Tauri CLI v2

## 설치

```bash
# 의존성 설치
npm install

# Rust 의존성 설치 (최초 1회)
cd src-tauri
cargo build
cd ..
```

## 개발

```bash
# 개발 서버 실행
npm run tauri dev
```

## 빌드

```bash
# 프로덕션 빌드
npm run tauri build
```

빌드된 앱은 `src-tauri/target/release/bundle/` 에 생성됩니다.

### 빌드 결과물

| 플랫폼 | 위치 |
|--------|------|
| macOS | `src-tauri/target/release/bundle/macos/SmartScheduler.app` |
| macOS DMG | `src-tauri/target/release/bundle/dmg/SmartScheduler_*.dmg` |
| Windows | `src-tauri/target/release/bundle/msi/SmartScheduler_*.msi` |
| Linux | `src-tauri/target/release/bundle/deb/smart-scheduler_*.deb` |

## Discord 설정

앱 실행 후 우측 상단 ⚙️ 버튼을 클릭하여 설정합니다.

### 필요한 정보

1. **Bot Token**: Discord Developer Portal에서 발급
2. **Channel ID**: 봇과 대화할 채널의 ID
3. **Bot User ID**: 봇의 사용자 ID (응답 필터링용)

### 설정 방법

1. [Discord Developer Portal](https://discord.com/developers/applications)에서 봇 생성
2. Bot 탭에서 Token 복사
3. Discord 설정에서 개발자 모드 활성화
4. 채널 우클릭 → "채널 ID 복사"
5. 봇 프로필 우클릭 → "ID 복사"

## 환경 변수 (선택)

`.env` 파일 또는 환경 변수로 기본값 설정 가능:

```env
DISCORD_BOT_TOKEN=your_bot_token
DISCORD_CHANNEL_ID=your_channel_id
DISCORD_BOT_USER_ID=your_bot_user_id
```

## 프로젝트 구조

```
app-mac/
├── src-tauri/              # Tauri (Rust) 설정
│   ├── src/lib.rs          # Rust 명령어 (항상 위에 등)
│   └── tauri.conf.json     # 창 크기, 타이틀 등
├── src/
│   ├── components/
│   │   ├── Calendar/       # 달력 (월간/일간 뷰)
│   │   ├── Character/      # 캐릭터 영역
│   │   ├── Chat/           # 채팅 UI
│   │   ├── Layout/         # 메인 레이아웃
│   │   ├── Settings/       # 설정 모달
│   │   └── Toggle/         # 채팅/달력 전환
│   ├── hooks/
│   │   ├── useCharacter.ts # 캐릭터 상태
│   │   ├── useDiscord.ts   # Discord API
│   │   ├── useMessages.ts  # 채팅 메시지
│   │   ├── useSchedules.ts # 일정 관리
│   │   └── useWindow.ts    # 창 속성
│   ├── utils/
│   │   ├── localCache.ts   # 로컬 캐시
│   │   ├── logger.ts       # 로깅
│   │   └── scheduleParser.ts # 일정 파싱
│   ├── types/              # TypeScript 타입
│   ├── App.tsx
│   └── main.tsx
├── package.json
└── README.md
```

## 기능

### 채팅
- Discord 채널을 통한 백엔드 통신
- 실시간 메시지 송수신 (1.5초 폴링)
- 대화 내역 로컬 캐시 (앱 재시작 시 복원)

### 달력
- 월간 달력 뷰 (일정 있는 날짜 점 표시)
- 일간 시간표 뷰 (3일: 어제/오늘/내일)
- 카테고리별 색상 구분
- 일정 데이터 로컬 캐시

### 창 설정
- "항상 위에" 토글
- 설정값 자동 저장

## Recommended IDE Setup

- [VS Code](https://code.visualstudio.com/) + [Tauri](https://marketplace.visualstudio.com/items?itemName=tauri-apps.tauri-vscode) + [rust-analyzer](https://marketplace.visualstudio.com/items?itemName=rust-lang.rust-analyzer)

## 라이선스

MIT

## 관련 문서

- [개발 계획서](../PLAN_APP_MAC.md)
- [백엔드 계획서](../PLAN_BACKEND.md)
