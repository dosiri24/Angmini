# 📋 Personal AI Assistant: 개발 계획서 (AI Agent용)

이 문서는 Personal AI Assistant 프로젝트 개발을 위한 구체적인 작업 계획을 정의합니다. 모든 작업은 `새로운_아키텍처_설계.md`에 명시된 로드맵을 따르며, 각 단계는 독립적으로 검증 가능해야 합니다.

---

## ✅ Phase 1: 기본 구조 구축 (1-2주) - **완료**

- [x] **1.1: 프로젝트 초기 설정**
    - [x] ~~1.1.1: `poetry init`을 사용하여 `pyproject.toml` 생성 및 기본 정보 설정~~ => `requirements.txt` 사용으로 변경
    - [x] 1.1.2: `README.md` 파일 생성 및 프로젝트 개요 작성
    - [x] 1.1.3: `.gitignore` 파일 생성 (Python, macOS, venv 관련)
    - [x] 1.1.4: `.env.example` 파일 생성 (필요한 환경변수 목록 정의)
    - [x] 1.1.5: `requirements.txt` 파일 생성
    - [x] 1.1.6: 폴더 구조 생성 (`ai`, `mcp`, `tests`, `data`, `docs`로 단순화)

- [x] **1.2: Core 모듈 개발**
    - [x] 1.2.1: `ai/core/config.py`: 환경변수를 로드하고 관리하는 `Config` 클래스 구현 (+ `DEFAULT_INTERFACE` 설정 추가)
    - [x] 1.2.2: `ai/core/logger.py`: 프로젝트 전반에서 사용할 `Logger` 설정 구현
    - [x] 1.2.3: `ai/core/exceptions.py`: 커스텀 예외 클래스 정의 (`ToolError`, `EngineError` 등)
    - [x] 1.2.4: `main.py`: 기본 진입점 파일 생성 및 `Config`, `Logger` 초기화 코드 작성 (환경변수 기반 인터페이스 선택 기능 추가)

- [x] **1.3: 기본 인터페이스 구축**
    - [x] 1.3.1: `interface/cli.py`: 간단한 상호작용이 가능한 CLI 인터페이스 초안 구현
    - [x] 1.3.2: `interface/discord_bot.py`: Discord 봇 기본 연결 및 메시지 수신/발신 기능 구현 (기본 `on_message` 이벤트)

### 📝 **Phase 1에서 적용된 사용자 피드백 및 수정사항**
- ✅ **아키텍처 개선**: `core` 폴더를 `ai/core`로 이동하여 구조 명확화
- ✅ **인터페이스 배치**: Discord 봇을 `ai` 폴더가 아닌 `interface` 폴더에 배치하여 역할 분리
- ✅ **환경변수 기반 시스템**: 매번 메뉴 선택 대신 `DEFAULT_INTERFACE` 환경변수로 기본 인터페이스 설정
- ✅ **타입 안전성**: Discord 봇 코드의 타입 체크 오류 수정
- ✅ **코드 품질**: `main.py` 함수 중복 및 구조적 문제 해결

---

## 🟡 Phase 2: ReAct Engine 구현 (3-4주) - *핵심*

- [x] **2.1: LLM 및 기본 데이터 구조**
    - [x] 2.1.1: `ai/ai_brain.py`: Google Gemini API와 연동하는 `AIBrain` 클래스 구현 (구 `LLMProvider`)
    - [x] 2.1.2: `mcp/tool_blueprint.py`: 모든 도구의 기반이 될 `ToolBlueprint` 추상 클래스와 `ToolResult` 데이터 클래스 정의 (구 `BaseTool`)
    - [x] 2.1.3: `mcp/tool_manager.py`: 도구를 등록하고 실행 요청을 라우팅하는 `ToolManager` 클래스 구현 (구 `ToolRegistry`)

- [x] **2.2: ReAct 엔진 핵심 로직 (MVP Stage 1 완료)**
    - [x] 2.2.1: `ai/react_engine/goal_executor.py`: GoalExecutor 구현 (Function Calling 기반 계획 수립 + 실행 루프)
    - [x] 2.2.2: `ai/react_engine/step_executor.py`: StepExecutor 구현 (도구 실행 및 결과 검증)
    - [x] 2.2.3: `ai/react_engine/safety_guard.py`: SafetyGuard 구현 (기본 단계/재시도 제한)
    - [ ] 2.2.4: `ai/react_engine/prompt_templates/`: `system_prompt.md`, `react_prompt.md` 등 프롬프트 템플릿 파일 생성
    - [ ] 2.2.5: `ai/react_engine/agent_scratchpad.py`: 확장된 사고/관찰 기록 모듈 (React Engine Stage 2로 이관)

- [ ] **2.3: 루프 제어 및 계획**
    - [ ] 2.3.1: `ai/react_engine/loop_detector.py`: `LoopDetector` 클래스 구현 (동일 액션 반복 감지 로직)
    - [ ] 2.3.2: `ai/react_engine/planning_engine.py`: `PlanningEngine` 클래스 기본 골격 구현 (복잡도 평가 로직 우선)

- [ ] **2.4: 첫 번째 도구 및 통합**
    - [x] 2.4.1: `mcp/tools/file_tool.py`: 파일 읽기/쓰기/목록 조회를 수행하는 `FileTool` 구현
    - [x] 2.4.2: `ToolManager`에 `FileTool` 등록 (CLI/Discord 인터페이스 초기화 시 등록 완료)
    - [ ] 2.4.3: React Engine이 `FileTool`을 호출하고 Observation을 기록하는 통합 테스트 (LLM 환경 준비 후 진행)

### 🛠️ 최근 업데이트 (2025-09-18)
- Discord 봇 인터페이스에서 `ToolManager` 경로를 수정하고 `FileTool`을 등록하여 CLI와 동일한 파일 작업 기능을 제공하도록 정비했습니다.
- `GoalExecutor`의 단순 대화 판별 로직을 작업 키워드 우선 검사 방식으로 개선하여, "파일 만들어줘"처럼 구체적인 요청이 자동으로 실행 루프로 분류됩니다.

---

## 🔵 Phase 3: 도구 확장 (2-3주)

- [ ] **3.1: Notion 도구 구현**
    - [ ] 3.1.1: `mcp/tools/notion_tool.py`: `NotionTool` 클래스 구현
    - [ ] 3.1.2: Notion API 클라이언트 초기화 및 인증
    - [ ] 3.1.3: 일정 추가/조회, 할일 추가/조회 기능 구현
    - [ ] 3.1.4: `ToolManager`에 `NotionTool` 등록 (구 `ToolRegistry`)

- [ ] **3.2: 웹 도구 구현**
    - [ ] 3.2.1: `mcp/tools/web_tool.py`: `WebTool` 클래스 구현
    - [ ] 3.2.2: 특정 URL 내용 가져오기, 웹 검색 기능 구현
    - [ ] 3.2.3: `ToolManager`에 `WebTool` 등록 (구 `ToolRegistry`)

- [ ] **3.3: Apple 시스템 도구 구현 (선택적)**
    - [ ] 3.3.1: `mcp/tools/apple_tool.py`: `AppleTool` 클래스 구현
    - [ ] 3.3.2: AppleScript 또는 `py-applescript`를 이용한 시스템 제어 기능 연구 및 구현 (예: 알림 보내기)
    - [ ] 3.3.3: `ToolManager`에 `AppleTool` 등록 (구 `ToolRegistry`)

---

## 🟣 Phase 4: 고급 기능 및 최적화 (2-3주)

- [ ] **4.1: ReAct 엔진 고도화**
    - [ ] 4.1.1: `ai/react_engine/planning_engine.py`의 동적 계획 수정(`adapt_plan`) 로직 구현
    - [ ] 4.1.2: `ai/react_engine/loop_detector.py`의 순환 패턴 감지 등 고급 루프 감지 로직 추가
    - [ ] 4.1.3: `ai/react_engine/agent_scratchpad.py`의 토큰 수 관리 및 요약 기능 추가

- [ ] **4.2: Memory System 구현**
    - [ ] 4.2.1: `ai/core/database.py`: SQLite를 사용한 데이터베이스 연결 및 기본 테이블 생성 로직 구현
    - [ ] 4.2.2: `ai/memory_system.py`: `MemorySystem` 클래스 구현
    - [ ] 4.2.3: ReAct 세션 정보를 DB에 저장하는 기능 구현
    - [ ] 4.2.4: `chromadb`를 사용하여 세션 정보를 벡터 임베딩으로 저장하고, 유사 목표를 검색하는 기능 구현

- [ ] **4.3: 모니터링 및 로깅 강화**
    - [ ] 4.3.1: `Logger`를 통해 ReAct 루프의 각 단계를 상세히 로깅
    - [ ] 4.3.2: `AgentScratchpad`의 내용을 파일이나 DB에 저장하여 시각적으로 검토할 수 있는 기능 구현

---

## 🟢 Phase 5: 통합, 테스트 및 배포 (1-2주)

- [ ] **5.1: 통합 테스트**
    - [ ] 5.1.1: `tests/` 폴더 내에 각 모듈별 단위 테스트 코드 작성 (`pytest`)
    - [ ] 5.1.2: `test_integration.py`: 복잡한 시나리오(여러 도구 사용)에 대한 End-to-End 테스트 작성
    - [ ] 5.1.3: `pytest-mock`을 사용하여 외부 API 호출 모킹

- [ ] **5.2: 문서화**
    - [x] 5.2.1: `docs/PLAN_for_Users.md`: 사용자를 위한 쉬운 버전의 개발 계획서 작성 (Phase 1에서 조기 완성)
    - [ ] 5.2.2: `docs/API.md`: 각 도구의 사용법과 API 명세 작성
    - [ ] 5.2.3: `docs/SETUP.md`: 프로젝트 설치 및 설정 가이드 작성
    - [ ] 5.2.4: `docs/USAGE.md`: 사용법 및 예시 명령어 작성

- [ ] **5.3: 배포 준비**
    - [ ] 5.3.1: `Dockerfile` 작성 (선택적)
    - [ ] 5.3.2: macOS에서 `launchd`를 사용하여 백그라운드 서비스로 등록하는 스크립트 작성
    - [ ] 5.3.3: 최종 `README.md` 업데이트
