# 📋 Personal AI Assistant: 개발 계획서 (AI Agent용)

이 문서는 Personal AI Assistant 프로젝트 개발을 위한 구체적인 작업 계획을 정의합니다. 모든 작업은 `새로운_아키텍처_설계.md`에 명시된 로드맵을 따르며, 각 단계는 독립적으로 검증 가능해야 합니다.

---

## ⬜ Phase 1: 기본 구조 구축 (1-2주) - **미완료**

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
- [ ] **아키텍처 개선**: `core` 폴더를 `ai/core`로 이동하여 구조 명확화
- [x] **인터페이스 배치**: Discord 봇을 `ai` 폴더가 아닌 `interface` 폴더에 배치하여 역할 분리
- [x] **환경변수 기반 시스템**: 매번 메뉴 선택 대신 `DEFAULT_INTERFACE` 환경변수로 기본 인터페이스 설정
- [x] **타입 안전성**: Discord 봇 코드의 타입 체크 오류 수정
- [x] **코드 품질**: `main.py` 함수 중복 및 구조적 문제 해결
- [x] **Discord 구성 간소화**: Guild ID 없이 봇 토큰만으로 실행할 수 있도록 조정
- [x] **Gemini 모델 설정**: 환경변수 `GEMINI_MODEL`로 사용할 모델을 지정

---

## 🟡 Phase 2: ReAct Engine 구현 (3-4주) - *핵심*

- [x] **2.1: LLM 및 기본 데이터 구조**
    - [x] 2.1.1: `ai/ai_brain.py`: Google Gemini API와 연동하는 `AIBrain` 클래스 구현 (구 `LLMProvider`)
    - [x] 2.1.2: `mcp/tool_blueprint.py`: 모든 도구의 기반이 될 `ToolBlueprint` 추상 클래스와 `ToolResult` 데이터 클래스 정의 (구 `BaseTool`)
    - [x] 2.1.3: `mcp/tool_manager.py`: 도구를 등록하고 실행 요청을 라우팅하는 `ToolManager` 클래스 구현 (구 `ToolRegistry`)

- [x] **2.2: ReAct 엔진 핵심 로직 (MVP Stage 1 완료)**
    - [x] 2.2.A: 계획 생성 LLM 프롬프트를 JSON 배열 응답으로 강제하고, `PlanStep(status)` 구조로 관리
    - [x] 2.2.B: Step 진행 상황(완료/진행중)을 LLM Thinking 단계에 반복 공급하여 일관성 확보
    - [x] 2.2.C: `StepResult(status, error_reason, attempt)` 구조와 스텝별 `max_attempts` 설정
    - [x] 2.2.D: 실패 시 최근 명령·파라미터·오류를 `ExecutionContext.fail_log`에 기록하고 다음 프롬프트에 제공
    - [x] 2.2.E: `ExecutionContext` 데이터 클래스로 목표/계획/현재 단계/실패 로그를 중앙 관리
    - [x] 2.2.F: 계획 자체가 틀렸을 때 이유를 포함해 LLM에게 재계획 요청 경로 마련
    - [x] 2.2.G: 스모크 테스트는 최소 구조 확인용으로 유지, 실제 시나리오는 실 환경으로 검증
    - [x] 2.2.H: `PlanStep`, `StepResult`, `ExecutionContext`, `StepCompletedEvent` 등 DTO/이벤트 정의
    - [x] 2.2.1: `ai/react_engine/goal_executor.py`: GoalExecutor 구현 (Function Calling 기반 계획 수립 + 실행 루프)
    - [x] 2.2.2: `ai/react_engine/step_executor.py`: StepExecutor 구현 (도구 실행 및 결과 검증)
    - [x] 2.2.3: `ai/react_engine/safety_guard.py`: SafetyGuard 구현 (기본 단계/재시도 제한)
    - [x] 2.2.4: `ai/react_engine/prompt_templates/`: `system_prompt.md`, `react_prompt.md` 등 프롬프트 템플릿 파일 생성
    - [x] 2.2.5: `ai/react_engine/agent_scratchpad.py`: 확장된 사고/관찰 기록 모듈 (React Engine Stage 2로 이관)

- [x] **2.3: 루프 제어 및 계획 조정**
    - [x] 2.3.1: `ExecutionContext`에 시도/시간 추적 헬퍼 추가하고 GoalExecutor의 시도 관리 코드를 이 헬퍼로 이관
    - [x] 2.3.2: `ai/react_engine/loop_detector.py`: `LoopDetector`가 `ExecutionContext`의 헬퍼와 실패 로그를 활용해 반복 패턴을 감지하고 이벤트를 발행하도록 구현
    - [x] 2.3.3: `ai/react_engine/planning_engine.py`: 현재 계획과 실패 원인을 평가해 "재시도"와 "재계획" 경로를 명확히 구분하는 인터페이스 구현
    - [x] 2.3.4: GoalExecutor에 LoopDetector/PlanningEngine을 주입하고, 기존 재시도 로직과 역할이 겹치지 않도록 통합

- [x] **2.4: 첫 번째 도구 및 통합**
    - [x] 2.4.1: `mcp/tools/file_tool.py`: 파일 읽기/쓰기/목록 조회를 수행하는 `FileTool` 구현
    - [x] 2.4.2: `ToolManager`에 `FileTool` 등록 (CLI/Discord 인터페이스 초기화 시 등록 완료)
    - [x] 2.4.3: React Engine이 `FileTool`을 호출하고 Observation을 기록하는 통합 테스트 (LLM 환경 준비 후 진행)

- [x] **2.5: 인터페이스 연결 및 실사용 검증**
    - [x] 2.5.1: CLI 인터페이스에 GoalExecutor를 주입하고 사용자 입력 -> 엔진 실행 -> 결과 응답 루프 구성
    - [x] 2.5.2: Discord 봇에 동일한 엔진 연동을 적용하고 기본 명령에 대한 응답 흐름 정리
    - [x] 2.5.3: `.env` 기반 LLM 설정 확인 및 엔진 초기화 오류 처리/로깅 개선
    - [x] 2.5.4: FileTool 시나리오를 이용한 수동 통합 검증 가이드(README 또는 docs/USAGE.md)에 기록

### 🛠️ 최근 업데이트 (2025-09-18)
- Discord 봇 인터페이스에 GoalExecutorFactory를 주입하고, 메시지 처리 루프에서 ReAct 실행 요약을 응답하도록 개선했습니다.
- CLI에서도 GoalExecutorFactory를 통해 사용자 요청을 곧바로 실행 루프로 전달하며, 실행 요약을 바로 출력합니다.
- `.env` 설정 오류 시 인터페이스 단계에서 친절한 오류 메시지를 제공하고, 수동 검증 가이드를 `docs/USAGE.md`로 정리했습니다.

---

## 🔵 Phase 3: 도구 확장 (2-3주)

- [x] **3.1: Notion 도구 구현**
    - [x] 3.1.1: `mcp/tools/notion_tool.py`: `NotionTool` 클래스 구현
    - [x] 3.1.2: Notion API 클라이언트 초기화 및 인증
    - [x] 3.1.3: 할일(Todo) 추가/조회 기능 구현
    - [x] 3.1.4: `ToolManager`에 `NotionTool` 등록 (구 `ToolRegistry`)

- [x] **3.2: Notion Relation 확장**
    - [x] 3.2.1: 경험/프로젝트 데이터베이스(`NOTION_PROJECT_DATABASE_ID`) 연동 및 속성 매핑 환경변수 정의
    - [x] 3.2.2: 프로젝트 목록 조회/검색용 `list_projects` 도구 operation 추가
    - [x] 3.2.3: 프로젝트 ID 자동 매칭 로직과 투두 생성 시 relation 연결 지원 (LLM 프롬프트 가이드 포함)
    - [x] 3.2.4: Relation 데이터가 포함된 `list_tasks` 응답 구조 확장 및 통합 테스트 작성

- ⏸️ **3.3: 웹 도구 구현 (무기한 보류)**
    - ⏸️ 3.3.1: `mcp/tools/web_tool.py`: `WebTool` 클래스 구현
    - ⏸️ 3.3.2: 특정 URL 내용 가져오기, 웹 검색 기능 구현
    - ⏸️ 3.3.3: `ToolManager`에 `WebTool` 등록 (구 `ToolRegistry`)

- [ ] **3.4: Apple 시스템 도구 구현 (Apple MCP 연동)**
    - [x] 3.4.1: **Apple MCP 서버 관리 모듈 구현**
        - [x] 3.4.1.1: `mcp/apple_mcp_manager.py`: Apple MCP 서버 시작/중지/통신 관리 클래스 구현
        - [x] 3.4.1.2: STDIO 프로토콜 기반 JSON-RPC 통신 구현 (`STDIOCommunicator` 클래스)
        - [x] 3.4.1.3: 프로세스 상태 모니터링 및 자동 복구 로직 구현 (`ProcessManager` 클래스)
        - [x] 3.4.1.4: Apple MCP 서버 설치 및 의존성 확인 자동화 (`AppleMCPInstaller` 클래스)
    - [x] 3.4.2: **Apple Tool 래퍼 구현**
        - [x] 3.4.2.1: `mcp/tools/apple_tool.py`: `AppleTool` 클래스 구현 (ToolBlueprint 상속)
        - [x] 3.4.2.2: 7개 Apple 앱 지원 (연락처, 메모, 메시지, 메일, 캘린더, 미리알림, 지도)
        - [x] 3.4.2.3: macOS 권한 확인 및 안내 기능 구현
        - [x] 3.4.2.4: 오류 처리 및 재시도 로직 구현 (서버 연결 실패, 권한 오류 등)
    - [x] 3.4.3: **AppleTool 운영 품질 다듬기**
        - [x] 3.4.3.1: `AppleMCPManager`/`STDIOCommunicator` 재시작·대기 로직 점검 및 로그 정비
        - [x] 3.4.3.2: AppleTool 타임아웃·재시도 기본값 검토와 성능 메트릭 정리
        - [x] 3.4.3.3: AppleTool 보안 검사 규칙(금지 패턴/텍스트 길이) 검토와 테스트 추가
        - [x] 3.4.3.4: 동기 실행 기반 장애 시나리오 점검 및 수동 부하 테스트 체크리스트 작성
    - [x] 3.4.4: **통합 및 검증**
        - [x] 3.4.4.1: `ToolManager` 기본 등록 확인 및 실패 시 사용자 알림 메시지 정의
        - [x] 3.4.4.2: CLI/Discord 인터페이스에서 Apple 명령 수동 점검 시나리오 문서화
        - [x] 3.4.4.3: AppleTool 통합 테스트 스켈레톤 정비 (macOS 권한 가이드 포함)
        - [x] 3.4.4.4: 간단 사용 가이드/FAQ 작성 (`docs/APPLE_TOOL_GUIDE.md`)

---

## 🟣 Phase 4: 고급 기능 및 최적화 (2-3주)

- [x] **4.1: ReAct 실패 흐름 강화**
    - [x] 4.1.1: `ai/react_engine/planning_engine.py`의 실패 판단 로직을 재구성해 재시도/재계획 이유를 더 명확히 기록
    - ⏸️ 4.1.2: (보류) 고급 루프 감지 로직 추가
    - ⏸️ 4.1.3: (보류) Scratchpad 토큰 관리 및 요약 기능 추가

- [x] **4.2: 로깅/출력 정비**
    - [x] 4.2.1: `main.py` 실행 시 세션 타임스탬프(예: `YYYYMMDD_HHMMSS.log`)로 로그 파일을 분리 저장
    - [x] 4.2.2: CLI/콘솔 로그 포맷을 정리하고 컬러 하이라이트 적용 (성공/경고/오류 색상 구분)
    - [x] 4.2.3: 로그 메시지 템플릿을 간결하게 정비하고 중복 메시지를 제거

---

## 🔶 Phase 4.5: Adaptive Memory Layer (2-3주)

### 🧱 현재 메모리 서브시스템 구조 참고
- `ai/memory/service.py`: MemoryService가 ExecutionContext 종료 시 파이프라인(`pipeline.py`, `retention_policy.py`, `memory_curator.py`)을 호출해 장기 기억을 저장.
- `ai/memory/factory.py`: SQLite + FAISS + Qwen 임베딩을 묶어 `MemoryRepository`(`storage/repository.py`)를 생성하고, 현재 OpenMP 환경 변수도 설정.
- `ai/memory/storage/repository.py`: `search()`가 임베딩 유사도 기반 상위 결과를 반환하며, `MemoryRecord`는 `memory_records.py`에 정의.
- `mcp/tools/memory_tool.py`: MCP 인터페이스에서 MemoryRepository 검색 API를 노출하며 `search_experience` 등 엔드포인트를 제공.
- `ai/react_engine/goal_executor.py`: 세션 시작 시 `_prefetch_relevant_memories()`가 MemoryService.repository를 직접 호출해 상위 기억을 가져와 ReAct 컨텍스트에 주입.
- `ai/memory/prompts/` 폴더: curator 프롬프트가 정리돼 있으며, LLM 기반 보조 프롬프트를 추가하기 좋은 위치.

- [x] **4.5.1: Memory Record 설계 및 추출 시점 정의**
    - [x] 4.5.1.1: 단일 Memory Record 스키마 정의 (요약 본문, 사용 도구, 사용자 의도, 성과 태그 등)
    - [x] 4.5.1.2: ExecutionContext 종료 직전 수집할 데이터 목록 확정 (사용자 입력, 계획, 도구 호출, 최종 응답 초안)
    - [x] 4.5.1.3: 저장 대상 선별 기준 정의 (신규 시나리오, 오류 해결, 사용자 선호 등)

- [x] **4.5.2: Memory Curator 모듈 구현**
    - [x] 4.5.2.1: Curator LLM 프롬프트 설계 (핵심만 정리하는 요약 가이드)
    - [x] 4.5.2.2: ExecutionContext → Curator 모듈 파이프라인 구축 (최종 응답 전 동기 실행)
    - [x] 4.5.2.3: 중복 메모리 감지/병합 규칙 정의 및 1차 구현

- [x] **4.5.3: Qwen3-Embedding 기반 저장소 구성**
    - [x] 4.5.3.1: Qwen3-Embedding 0.6 호출 래퍼 구현 및 API 키 관리 규칙 수립
    - [x] 4.5.3.2: 메타데이터 저장(예: SQLite)과 벡터 인덱스(예: 로컬 FAISS) 병행 설계
    - [x] 4.5.3.3: 삽입·검색 공통 인터페이스 정의 (확장 가능하도록 추상화)

- [x] **4.5.4: Memory MCP 도구 구현**
    - [x] 4.5.4.1: `mcp/tools/memory_tool.py`에서 `MemoryTool` 구현 (ToolBlueprint 상속)
    - [x] 4.5.4.2: 검색 엔드포인트 정의 (`search_experience`, `find_solution`, `get_tool_guidance`, `analyze_patterns`)
    - [x] 4.5.4.3: 쿼리 타입별 검색 우선순위 로직 (임베딩 유사도 + 메타 필터)
    - [x] 4.5.4.4: System Prompt에 MemoryTool 우선 사용 지침 추가 (ToolManager 구조 변경 없이)

- [x] **4.5.5: ReAct Engine 통합**
    - [x] 4.5.5.1: `GoalExecutor`에 최종 메모리 생성 단계 연결 (최종 응답 전 Curator 호출)
    - [x] 4.5.5.2: 기억 검색 결과를 ExecutionContext에 주입하는 헬퍼 구현
    - [x] 4.5.5.3: 재시도/오류 흐름에서 MemoryTool을 활용하는 프롬프트 가이드 정비

- [ ] **4.5.6: Cascaded LLM-Filter Retrieval 실험**
    - [ ] 4.5.6.1: `ai/memory/prompts/`에 LLM 필터링 프롬프트 초안을 추가하고, `ai/memory/cascaded_retriever.py`(신규)에서 사용할 few-shot 예시/판정 규칙 정의
    - [ ] 4.5.6.2: `ai/memory/cascaded_retriever.py`에서 `CascadedRetriever` 클래스를 구현해 ① `MemoryRepository.search()`로 1차 상위 5개 조회 → ② LLM 필터(`AIBrain`) 호출 → ③ 관련 결과로부터 키워드/후속 쿼리를 생성해 재임베딩/재검색을 반복 (최대 N회, 가중치 조합 포함)
    - [ ] 4.5.6.3: 동일 기억 재발견 방지를 위해 `CascadedRetriever` 내부에 조회 ID 캐시(set)와 재귀 깊이 제한, score 하한선, “신규 결과 없음” 카운터를 적용하고, 구성 옵션을 `Config` 혹은 `MemoryService`에서 주입 가능하도록 설계
    - [ ] 4.5.6.4: `CascadedRetriever`가 각 반복에서 수집한 메트릭(신규 기억 수, LLM keep ratio, 누적 지연)을 `ai/core/logger`를 통해 로그/테레메트리로 남기고, `MemoryService` 또는 `GoalExecutor._prefetch_relevant_memories()`에서 결과 요약을 기록
    - [ ] 4.5.6.5: 최종 반환 단계에서 `ai/react_engine/goal_executor.py`를 수정해 CascadedRetriever의 결과를 기존 scratchpad 주입 로직과 통합하고, 중복 제거·요약(`memory_records` 기반) 후 ReAct 컨텍스트에 전달되도록 후처리 함수를 추가

- [ ] **4.5.7: 관찰 및 유지보수 체계**
    - [ ] 4.5.7.1: 메모리 저장/조회 성공률 및 응답 품질 모니터링 항목 정의
    - [ ] 4.5.7.2: 임베딩 갱신/모델 교체 시나리오 문서화
    - [ ] 4.5.7.3: 데이터 정리 및 개인정보 관리 정책 수립

### 🎯 **Phase 4.5 핵심 목표**
- 대화 종료 시 자동으로 핵심 기억을 생성하고, 적절한 임베딩/메타데이터와 함께 보존
- Qwen3-Embedding 0.6을 활용해 유사 시나리오를 빠르게 검색하고 LLM이 필요할 때 MCP 도구로 호출할 수 있는 구조 확보
- 기존 ReAct 실행 루프를 크게 바꾸지 않고도 기억 생성·활용을 단계적으로 통합

### 📌 **Phase 4.5 구현 참고**
- Qwen3 임베딩 모델은 기본적으로 Hugging Face Hub에서 `Qwen/Qwen3-Embedding-0.6B`를 바로 로드하며, 로컬 캐시를 사용하려면 `QWEN3_EMBEDDING_PATH` 환경변수에 디렉터리를 지정하면 됩니다.
- 테스트 용도로 `tests/test_qwen3_embedding_vector_store.py`가 제공되며, `pytest tests/test_qwen3_embedding_vector_store.py -q`로 실행 시 모델 로딩 → 임베딩 생성 → FAISS 인덱스 검색 흐름이 정상 동작하는지 확인할 수 있습니다.
- 모델 로딩과 임베딩 계산은 GPU 없이도 가능하지만, 대용량 처리 시 README 권장처럼 Flash Attention 설정을 검토합니다.

---

## 🟢 Phase 5: 통합, 테스트 및 배포 (1-2주)

- [ ] **5.1: 통합 테스트**
    - [ ] 5.1.1: `tests/` 폴더 내에 각 모듈별 단위 테스트 코드 작성 (`pytest`)
    - [ ] 5.1.2: `test_integration.py`: 복잡한 시나리오(여러 도구 사용)에 대한 End-to-End 테스트 작성
    - [ ] 5.1.3: `pytest-mock`을 사용하여 외부 API 호출 모킹

- [ ] **5.2: 문서화**
    - [ ] 5.2.1: `docs/PLAN_for_Users.md`: 사용자를 위한 쉬운 버전의 개발 계획서 작성 (Phase 1에서 조기 완성)
    - [ ] 5.2.2: `docs/API.md`: 각 도구의 사용법과 API 명세 작성
    - [ ] 5.2.3: `docs/SETUP.md`: 프로젝트 설치 및 설정 가이드 작성
    - [ ] 5.2.4: `docs/USAGE.md`: 사용법 및 예시 명령어 작성

- [ ] **5.3: 배포 준비**
    - [ ] 5.3.1: `Dockerfile` 작성 (선택적)
    - [ ] 5.3.2: macOS에서 `launchd`를 사용하여 백그라운드 서비스로 등록하는 스크립트 작성
    - [ ] 5.3.3: 최종 `README.md` 업데이트
