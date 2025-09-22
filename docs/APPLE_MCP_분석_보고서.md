# 🍎 Apple MCP 분석 보고서

## 📋 개요

Apple MCP는 AI 모델(특히 Claude)이 Mac의 네이티브 Apple 앱들과 직접 상호작용할 수 있게 해주는 **Model Context Protocol (MCP) 서버**입니다. 쉽게 말해, "AI가 당신의 Mac을 조작할 수 있게 해주는 브릿지" 역할을 합니다.

## 🎯 프로젝트 정보

- **프로젝트명**: apple-mcp
- **소유자**: supermemoryai
- **버전**: 1.0.0
- **라이선스**: MIT
- **개발자**: Dhravya Shah
- **저장소**: https://github.com/dhravya/apple-mcp.git

## 🔧 기술 스택

- **메인 언어**: TypeScript/Node.js
- **런타임**: Bun (빠른 JavaScript 런타임)
- **핵심 프로토콜**: Model Context Protocol (MCP)
- **Apple 앱 제어**: AppleScript + SQLite
- **스키마 검증**: Zod
- **빌드 타겟**: Node.js

## 🛠️ 지원하는 Apple 앱들

### 1. **연락처 (Contacts)** 📱
- 연락처 검색 및 조회
- 전화번호, 이메일 정보 가져오기
- 전체 연락처 목록 조회

### 2. **메모 (Notes)** 📝  
- 메모 생성, 검색, 조회
- 특정 폴더에 메모 저장
- 전체 메모 목록 가져오기

### 3. **메시지 (Messages)** 💬
- 메시지 전송 및 읽기
- 메시지 예약 전송
- 읽지 않은 메시지 조회

### 4. **메일 (Mail)** 📧
- 이메일 전송 (첨부파일, CC, BCC 지원)
- 이메일 검색 및 조회
- 이메일 예약 전송
- 읽지 않은 메일 개수 확인
- 계정별/메일함별 관리

### 5. **미리 알림 (Reminders)** ⏰
- 리마인더 생성 및 관리
- 리마인더 검색
- 목록별 리마인더 조회

### 6. **캘린더 (Calendar)** 📅
- 일정 생성 및 조회
- 이벤트 검색
- 특정 기간 일정 조회

### 7. **지도 (Maps)** 🗺️
- 위치 검색 및 내비게이션
- 위치 저장 및 핀 드롭
- 길찾기 기능
- 가이드 생성 및 관리

## ⚙️ 핵심 작동 원리

### 1. **AppleScript 기반 제어** 📜
Mac의 네이티브 자동화 스크립팅 언어를 사용:

```javascript
// 예시: 연락처 앱에서 정보 가져오기
const script = `
tell application "Contacts"
    set contactList to {}
    set allPeople to people
    
    repeat with currentPerson in allPeople
        set personName to name of currentPerson
        set phonesList to phones of currentPerson
        -- 연락처 정보 처리...
    end repeat
    
    return contactList
end tell`;

await runAppleScript(script);
```

### 2. **SQLite 데이터베이스 직접 접근** 🗄️
일부 앱(특히 메시지)의 경우:

```javascript
// 메시지 히스토리를 위해 SQLite DB 접근
const dbPath = `${process.env.HOME}/Library/Messages/chat.db`;
await execAsync(`sqlite3 "${dbPath}" "SELECT content, date FROM message;"`);
```

### 3. **터미널 명령어는 최소 사용**
- 주로 `runAppleScript()` 함수 사용
- SQLite 쿼리 (메시지 DB 접근용)
- 파일 시스템 API (권한 체크용)

## 🔐 필요한 macOS 권한

### 1. **자동화 권한 (Automation)**
- 경로: `시스템 설정 > 개인정보 보호 및 보안 > 자동화`
- 목적: 터미널/앱이 각 Apple 앱을 제어할 수 있도록 허용

### 2. **전체 디스크 접근 (Full Disk Access)**
- 경로: `시스템 설정 > 개인정보 보호 및 보안 > 전체 디스크 접근`
- 목적: 메시지 데이터베이스(`~/Library/Messages/chat.db`) 접근

### 3. **연락처 접근 (Contacts)**
- 경로: `시스템 설정 > 개인정보 보호 및 보안 > 연락처`
- 목적: 연락처 앱 데이터 접근

## 🖥️ MCP 서버 아키텍처

### **서버 기반 구조**
Apple MCP는 **반드시 서버를 실행해야만 작동**하는 구조입니다.

```typescript
// 메인 서버 초기화
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

const server = new Server(/* ... */);
const transport = new StdioServerTransport();
await server.connect(transport);
```

### **실행 방법**
```bash
# 개발 모드
bun run dev

# 빌드 후 실행
bun run build
bun run start

# 글로벌 설치 후
apple-mcp
```

### **통신 방식: STDIO**
- AI 모델과 **표준 입출력(STDIO)**으로 JSON 메시지 교환
- 실시간 요청-응답 처리
- 상태 유지 및 모듈 동적 로딩

## 🔄 작동 흐름

```
1. AI 요청 → "John에게 메시지 보내줘"
2. MCP 서버가 요청 받음 → `message` 도구 호출
3. AppleScript 생성 → 메시지 앱 제어 스크립트 작성
4. `runAppleScript()` 실행 → macOS가 스크립트 실행
5. 메시지 앱이 실제로 작동 → iMessage 전송
6. 결과 반환 → AI에게 성공/실패 알림
```

## 📁 프로젝트 구조

```
apple-mcp/
├── index.ts          # 메인 MCP 서버 엔트리포인트
├── tools.ts          # 모든 도구들의 스키마 정의
├── utils/            # 각 Apple 앱별 유틸리티 함수들
│   ├── contacts.ts   # 연락처 관련 기능
│   ├── notes.ts      # 메모 관련 기능
│   ├── mail.ts       # 메일 관련 기능
│   ├── message.ts    # 메시지 관련 기능
│   ├── reminders.ts  # 미리 알림 관련 기능
│   ├── calendar.ts   # 캘린더 관련 기능
│   └── maps.ts       # 지도 관련 기능
├── tests/            # 통합 테스트
├── dist/             # 빌드된 파일들
├── package.json      # 프로젝트 설정
├── tsconfig.json     # TypeScript 설정
└── manifest.json     # MCP 매니페스트
```

## 🚀 AI 프로젝트 통합 가이드

### **1. MCP 서버 설치 및 실행**
```bash
# 저장소 클론
git clone https://github.com/supermemoryai/apple-mcp.git
cd apple-mcp

# 의존성 설치
bun install

# 서버 실행
bun run dev
```

### **2. AI 클라이언트에서 연결**
- MCP 클라이언트 라이브러리 사용
- STDIO 프로토콜로 통신
- JSON-RPC 방식으로 도구 호출

### **3. 사용 가능한 도구들**
- `contacts`: 연락처 검색/조회
- `notes`: 메모 생성/검색/조회
- `messages`: 메시지 전송/읽기/예약
- `mail`: 이메일 전송/검색/조회
- `reminders`: 리마인더 생성/관리
- `calendar`: 일정 생성/조회/검색
- `maps`: 위치 검색/저장/길찾기

### **4. 예시 사용법**
```javascript
// 연락처 검색
{
  "method": "tools/call",
  "params": {
    "name": "contacts",
    "arguments": {
      "name": "John"
    }
  }
}

// 메시지 전송
{
  "method": "tools/call",
  "params": {
    "name": "messages",
    "arguments": {
      "operation": "send",
      "phoneNumber": "+1234567890",
      "message": "Hello from AI!"
    }
  }
}
```

## ⚠️ 주의사항

1. **macOS 전용**: Mac에서만 작동
2. **권한 필수**: 각 Apple 앱에 대한 시스템 권한 필요
3. **서버 상주**: MCP 서버가 계속 실행되어야 함
4. **AppleScript 의존**: Mac의 AppleScript 환경에 의존
5. **보안 고려**: 시스템 앱 제어 권한이므로 보안 주의 필요

## 💡 핵심 장점

- **네이티브 통합**: Mac의 모든 기본 앱과 완벽 통합
- **실시간 처리**: 즉시 응답하는 서버 구조
- **확장 가능**: 새로운 Apple 앱 지원 추가 용이
- **표준 프로토콜**: MCP 표준 준수로 다양한 AI 모델과 호환
- **타입 안전**: TypeScript로 개발되어 타입 안전성 보장

---

**결론**: Apple MCP는 AI 모델이 Mac의 네이티브 앱들을 직접 조작할 수 있게 해주는 강력한 도구입니다. "더 똑똑한 Siri" 같은 역할을 하며, 자연어 명령을 통해 Mac의 모든 기본 기능을 자동화할 수 있습니다.