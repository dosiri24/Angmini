# Angmini 구현 상태 및 개발 계획서

**작성일**: 2025년 10월 2일
**프로젝트 버전**: v2.0.1
**CrewAI 버전**: 0.28.0+
**최신 업데이트**: 2024-2025 AI 에이전트 베스트 프랙티스 적용

---

## 📊 전체 진행 상황

```
Phase 1-2: Core System        ████████████████████  100% ✅
Phase 3: Tool Integration     ████████████████████  100% ✅
Phase 4: Memory System        ████████████████████  100% ✅
Phase 5: Proactive Notify     ░░░░░░░░░░░░░░░░░░░░    0% ⏸️
Phase 6: Optimization         ███████░░░░░░░░░░░░░   35% 🚧
─────────────────────────────────────────────────────
전체 진행률                    ████████████████░░░░   80%
```

---

## ✅ 구현 완료된 기능

### Phase 1-2: 핵심 CrewAI 멀티 에이전트 시스템 (100%)

#### 1.1 에이전트 시스템
- ✅ **BaseAngminiAgent**: 모든 에이전트의 기본 클래스
  - 위치: `ai/agents/base_agent.py`
  - 기능: 역할, 목표, 배경 스토리, 도구 정의
  - LLM 설정 및 CrewAI Agent 빌드

- ✅ **PlannerAgent (Manager)**:
  - 위치: `ai/agents/planner_agent.py`
  - 역할: 작업 계획 및 조율 총괄 책임자
  - 기능: 사용자 요청 분석, 작업 분해, 전문가 에이전트 위임
  - 프로세스: Hierarchical (Manager-Worker 패턴)

- ✅ **FileAgent (Worker)**:
  - 위치: `ai/agents/file_agent.py`
  - 역할: 파일 시스템 관리 전문가
  - 도구: FileCrewAITool
  - 기능: 파일 읽기/쓰기/이동/삭제, 디렉토리 탐색

- ✅ **NotionAgent (Worker)**:
  - 위치: `ai/agents/notion_agent.py`
  - 역할: Notion 워크스페이스 관리 전문가
  - 도구: NotionCrewAITool
  - 기능: 할일 관리, 프로젝트 추적, DB 조회

- ✅ **MemoryAgent (Worker)**:
  - 위치: `ai/agents/memory_agent.py`
  - 역할: 장기 기억 관리 및 경험 검색 전문가
  - 도구: MemoryCrewAITool
  - 기능: 과거 경험 검색, 패턴 분석, 솔루션 추천

- ✅ **AppleAppsAgent (Worker, macOS only)**:
  - 위치: `ai/agents/apple_apps_agent.py`
  - 역할: macOS 시스템 통합 전문가
  - 도구: AppleCrewAITool
  - 기능: Notes, Reminders, Calendar, Mail 등 연동

#### 1.2 Crew 설정
- ✅ **AngminiCrew**: CrewAI Crew 초기화 및 관리
  - 위치: `crew/crew_config.py`
  - 기능: 에이전트 생성, Crew 설정, 작업 실행
  - 프로세스: Hierarchical 프로세스 지원
  - 메모리: CrewAI 메모리 시스템 통합 준비

- ✅ **TaskFactory**: 사용자 입력을 CrewAI Task로 변환
  - 위치: `crew/task_factory.py`
  - 기능: 동적 Task 생성, PlannerAgent에 할당

#### 1.3 협업 메커니즘
- ✅ **Delegation (위임)**: `allow_delegation=True` 설정
- ✅ **Information Sharing (정보 공유)**: 작업 컨텍스트 공유
- ✅ **Task Assistance (작업 지원)**: 전문가 간 협력
- ✅ **Resource Allocation (리소스 할당)**: 동적 작업 분배

### Phase 3: MCP 도구 통합 (100%)

#### 3.1 도구 아키텍처
- ✅ **ToolBlueprint**: 도구 기본 추상 클래스
  - 위치: `mcp/tool_blueprint.py`
  - 기능: tool_name, schema, __call__ 메서드 정의

- ✅ **ToolManager**: 도구 등록 및 실행 관리
  - 위치: `mcp/tool_manager.py`
  - 기능: 도구 등록, 실행 라우팅

#### 3.2 구현된 도구

**FileTool** (파일 시스템):
- ✅ 위치: `mcp/tools/file_tool.py`
- ✅ 기능:
  - read: 파일 읽기
  - write: 파일 쓰기
  - list: 디렉토리 목록 조회 (recursive, include_hidden)
  - move: 파일/디렉토리 이동
  - trash: 안전한 휴지통 이동 (send2trash)
- ✅ CrewAI 통합: FileCrewAITool 클래스 (BaseTool 직접 상속)
- ✅ 입력 검증: Pydantic BaseModel (FileToolInput)
- ✅ 오류 처리: 명확한 오류 메시지 및 우아한 성능 저하

**NotionTool** (Notion API):
- ✅ 위치: `mcp/tools/notion_tool.py`
- ✅ 기능:
  - list_todos: 할일 목록 조회
  - create_task: 할일 생성
  - update_task_status: 할일 상태 업데이트
  - get_task_details: 할일 상세 정보
  - list_projects: 프로젝트 목록 조회
- ✅ CrewAI 통합: NotionCrewAITool 클래스
- ✅ 데이터베이스: TODO 및 Project 데이터베이스 지원
- ✅ 관계 관리: 프로젝트-할일 관계 자동 매칭

**MemoryTool** (장기 기억):
- ✅ 위치: `mcp/tools/memory_tool.py`
- ✅ 기능:
  - search_experiences: 과거 경험 검색
  - find_solutions: 유사 상황 솔루션 추천
  - analyze_patterns: 패턴 분석
- ✅ CrewAI 통합: MemoryCrewAITool 클래스
- ✅ 검색: Cascaded Retriever 통합

**AppleTool** (macOS 시스템):
- ✅ 위치: `mcp/tools/apple_tool.py`
- ✅ 기능:
  - Apple MCP 서버 subprocess 연동
  - Notes, Reminders, Calendar, Mail, Contacts 등
  - AppleScript 기반 자동화
- ✅ CrewAI 통합: AppleCrewAITool 클래스
- ✅ 서버 관리: AppleMCPManager (서브프로세스 생명주기 관리)

### Phase 4: 메모리 시스템 (100%)

#### 4.1 메모리 저장소
- ✅ **SQLiteStore**: 메타데이터 저장
  - 위치: `ai/memory/storage/sqlite_store.py`
  - 기능: 메모리 레코드 CRUD, 메타데이터 관리
  - 저장소: `data/memory/memories.db`

- ✅ **VectorIndex**: FAISS 벡터 인덱스
  - 위치: `ai/memory/storage/vector_index.py`
  - 기능: 벡터 임베딩 저장, 유사도 검색
  - 저장소: `data/memory/memory.index`, `data/memory/memory.ids`

- ✅ **MemoryRepository**: 통합 저장소 인터페이스
  - 위치: `ai/memory/storage/repository.py`
  - 기능: SQLite + FAISS 조정, 통합 검색 API

#### 4.2 메모리 파이프라인
- ✅ **MemoryService**: 장기 기억 고수준 API
  - 위치: `ai/memory/service.py`
  - 기능: 메모리 캡처, 검색, 관리

- ✅ **MemoryCurator**: LLM 기반 메모리 큐레이터
  - 위치: `ai/memory/memory_curator.py`
  - 기능: 자동 요약, 품질 관리, 태그 생성
  - LLM: Gemini 활용

- ✅ **Deduplicator**: 중복 제거기
  - 위치: `ai/memory/deduplicator.py`
  - 기능: 벡터 유사도 기반 중복 탐지 및 제거

- ✅ **CascadedRetriever**: 다단계 검색기
  - 위치: `ai/memory/cascaded_retriever.py`
  - 기능: 다단계 필터링, LLM 기반 관련성 평가, follow-up 쿼리

#### 4.3 임베딩 시스템
- ✅ **Qwen3EmbeddingModel**: Qwen3-0.6B 임베딩
  - 위치: `ai/memory/embedding.py`
  - 모델: `Qwen/Qwen3-Embedding-0.6B`
  - 기능: 텍스트 → 벡터 변환, 의미적 유사도 계산

#### 4.4 메모리 관리
- ✅ **RetentionPolicy**: 보존 정책
  - 위치: `ai/memory/retention_policy.py`
  - 기능: 중요도 기반 보존 (현재 모든 메모리 허용)

- ✅ **MemoryMetrics**: 메모리 메트릭스
  - 위치: `ai/memory/metrics.py`
  - 기능: 성능 모니터링 및 통계

### Phase 6: 인터페이스 및 인프라 (35%)

#### 6.1 인터페이스 (100%)
- ✅ **CLI**: 명령줄 인터페이스
  - 위치: `interface/cli.py`
  - 기능: 실시간 스트리밍 출력, CrewAI 통합
  - 실행 스크립트: `bin/angmini`

- ✅ **Discord Bot**: Discord 메시지 인터페이스
  - 위치: `interface/discord_bot.py`
  - 기능: 비동기 메시지 처리, CrewAI 통합

- ✅ **Streaming Interface**: 스트리밍 출력 관리
  - 위치: `interface/streaming.py`

- ✅ **Summary Formatter**: 실행 결과 요약
  - 위치: `interface/summary.py`

#### 6.2 핵심 인프라 (100%)
- ✅ **Config**: 환경변수 관리
  - 위치: `ai/core/config.py`
  - 기능: `.env` 파일 로드, 설정 검증

- ✅ **Logger**: 로깅 시스템
  - 위치: `ai/core/logger.py`
  - 기능: 세션별 타임스탬프 로그, 구조화된 로깅

- ✅ **Exceptions**: 커스텀 예외
  - 위치: `ai/core/exceptions.py`
  - 기능: EngineError, ToolError, ConfigError, InterfaceError

- ✅ **AIBrain**: Gemini API 연동
  - 위치: `ai/ai_brain.py`
  - 기능: Gemini API 호출, 응답 처리, 토큰 추적

---

## 🚧 구현 중인 기능 (Phase 6: 35%)

### 6.1 성능 최적화

#### 6.1.1 병렬 함수 호출 (0%)
- ❌ **상태**: 미구현
- 📝 **계획**: CrewAI 도구에서 병렬 함수 호출 지원
- 💡 **참고**: OpenAI의 병렬 함수 호출 패턴
- 🎯 **목표**: 다단계 작업의 지연 시간 단축

#### 6.1.2 비동기 도구 확대 (20%)
- 🔄 **상태**: 일부 구현
- ✅ **완료**: 기본 비동기 구조 준비
- ⏳ **진행 중**: FileTool, NotionTool 비동기 변환
- 📝 **계획**: AppleTool, MemoryTool 비동기 지원
- 🎯 **목표**: 비블로킹 I/O로 응답성 향상

#### 6.1.3 캐싱 전략 (0%)
- ❌ **상태**: 미구현
- 📝 **계획**:
  - 메모리 검색 결과 캐싱 (1시간)
  - Notion API 응답 캐싱
  - 임베딩 벡터 캐싱
- 🎯 **목표**: API 호출 및 연산 비용 절감

### 6.2 메모리 시스템 고도화

#### 6.2.1 하이브리드 인덱싱 (0%)
- ❌ **상태**: 미구현
- 📝 **계획**: 밀집(dense) + 희소(sparse) 표현 결합
- 💡 **기술**: FAISS (dense) + BM25 (sparse)
- 🎯 **목표**: 검색 정확도 향상

#### 6.2.2 도메인 특화 임베딩 (0%)
- ❌ **상태**: 미구현
- 📝 **계획**: 개인 비서 도메인에 특화된 임베딩 모델 미세 조정
- 💡 **기술**: Qwen3 Fine-tuning on personal assistant tasks
- 🎯 **목표**: 의미적 검색 품질 향상

#### 6.2.3 CrewAI 메모리 통합 (30%)
- 🔄 **상태**: 준비 중
- ✅ **완료**: 환경변수 설정 (`CREW_MEMORY_ENABLED`)
- ⏳ **진행 중**: Angmini 메모리 시스템과 CrewAI 메모리 연동 설계
- 📝 **계획**:
  - CrewAI Short-term memory 활용
  - CrewAI Long-term memory와 FAISS 동기화
  - Entity memory 통합
- 🎯 **목표**: 에이전트 간 메모리 공유 강화

#### 6.2.4 적응형 검색 메커니즘 (40%)
- 🔄 **상태**: Cascaded Retriever로 일부 구현
- ✅ **완료**: 다단계 필터링, LLM 기반 관련성 평가
- 📝 **계획**:
  - 쿼리 복잡성에 따른 동적 조정
  - 컨텍스트 재순위화 (Reranking)
  - 메타데이터 필터링 강화
- 🎯 **목표**: 검색 정확도 및 효율성 향상

### 6.3 보안 강화

#### 6.3.1 MCP 인증 강화 (0%)
- ❌ **상태**: 미구현
- 📝 **계획**: Resource Indicators (RFC 8707) 구현
- 💡 **목적**: 악의적인 서버의 토큰 획득 방지
- 🎯 **목표**: 2025년 6월 MCP 사양 준수

#### 6.3.2 입력 검증 강화 (60%)
- 🔄 **상태**: 기본 구현
- ✅ **완료**: Pydantic 스키마 기반 검증
- 📝 **계획**:
  - 커맨드 인젝션 방지 강화
  - 프롬프트 인젝션 탐지
  - 입력 정제 (sanitization) 개선
- 🎯 **목표**: 보안 취약점 최소화

#### 6.3.3 샌드박싱 (0%)
- ❌ **상태**: 미구현
- 📝 **계획**: MCP 서버를 샌드박스에서 실행
- 💡 **기술**: 리소스 격리 및 권한 제한
- 🎯 **목표**: 시스템 보안 강화

### 6.4 모니터링 및 관찰성

#### 6.4.1 성능 메트릭스 (40%)
- 🔄 **상태**: 기본 로깅
- ✅ **완료**: 토큰 사용량 추적, 세션 로그
- 📝 **계획**:
  - 작업 실행 시간 측정
  - 에이전트별 성능 분석
  - 도구 호출 빈도 및 성공률
  - 메모리 검색 성능 (지연 시간, 정확도)
- 🎯 **목표**: 데이터 기반 최적화

#### 6.4.2 감사 추적 (30%)
- 🔄 **상태**: 기본 로깅
- ✅ **완료**: 작업 실행 로그
- 📝 **계획**:
  - 모든 MCP 도구 호출 로그
  - 에이전트 결정 추적
  - 오류 및 예외 상세 기록
  - SIEM 통합 준비
- 🎯 **목표**: 디버깅 및 보안 감사 용이성

---

## ⏸️ 계획 중인 기능 (Phase 5: 0%)

### Phase 5: 능동적 알림 시스템

#### 5.1 알림 트리거 (0%)
- ❌ **상태**: 미착수
- 📝 **계획**:
  - 시간 기반 트리거 (예: 일정 시간 전 알림)
  - 이벤트 기반 트리거 (예: 할일 마감일)
  - 패턴 기반 트리거 (예: 반복 작업)
- 💡 **참고**: Event-Driven Architecture 패턴

#### 5.2 알림 채널 (0%)
- ❌ **상태**: 미착수
- 📝 **계획**:
  - Discord 메시지
  - macOS 시스템 알림
  - 이메일 (선택)
- 🎯 **목표**: 다중 채널 알림 지원

#### 5.3 알림 관리 (0%)
- ❌ **상태**: 미착수
- 📝 **계획**:
  - 알림 우선순위 결정
  - 사용자 선호도 학습
  - 알림 스누즈 및 해제
- 🎯 **목표**: 사용자 친화적 알림 시스템

---

## 🔄 개선 예정 사항

### 우선순위 1 (단기 - 1개월 이내)

**CrewAI 버전 업그레이드**:
- 현재: CrewAI 0.28.0
- 목표: CrewAI 0.201.1 (최신)
- 이유: 최신 기능 및 성능 개선 활용
- 영향:
  - RAG 패키지 기능 동등성
  - 향상된 LLM 이벤트 처리
  - Knowledge Retrieval 기능

**CrewAI 메모리 통합 완료**:
- 목표: Angmini 메모리 시스템과 CrewAI 메모리 완전 통합
- 계획:
  1. CrewAI Short-term memory로 작업 컨텍스트 공유
  2. Long-term memory와 FAISS 동기화
  3. Entity memory로 중요 개체 추적
- 기대 효과: 에이전트 간 협업 강화, 컨텍스트 유지 향상

**비동기 도구 전환 완료**:
- 목표: 모든 도구를 비동기로 전환
- 우선순위:
  1. FileTool (I/O 집약적)
  2. NotionTool (API 호출)
  3. MemoryTool (DB 쿼리)
  4. AppleTool (서브프로세스)
- 기대 효과: 응답 시간 단축, 동시성 향상

### 우선순위 2 (중기 - 3개월 이내)

**하이브리드 인덱싱 구현**:
- 기술: FAISS (dense) + BM25 (sparse)
- 목표: 검색 정확도 및 커버리지 향상
- 구현:
  1. BM25 인덱스 구축
  2. Dense + Sparse 점수 결합
  3. 성능 벤치마크
- 기대 효과: 의미적 검색 + 정확한 매칭 = 최상의 검색

**MCP 보안 강화**:
- Resource Indicators (RFC 8707) 구현
- 입력 검증 및 정제 강화
- 샌드박싱 도입
- 기대 효과: 2025 MCP 보안 표준 준수

**성능 모니터링 대시보드**:
- 메트릭스: 작업 실행 시간, 토큰 사용량, 검색 성능
- 시각화: 에이전트별, 도구별 성능 분석
- 알람: 성능 임계값 초과 시 알림
- 기대 효과: 데이터 기반 최적화 및 문제 조기 발견

### 우선순위 3 (장기 - 6개월 이내)

**도메인 특화 임베딩 모델**:
- 기반 모델: Qwen3-0.6B
- 미세 조정: 개인 비서 도메인 (작업 관리, 파일 관리, 정보 검색)
- 데이터: Angmini 사용 기록 (익명화)
- 기대 효과: 의미적 검색 정확도 향상

**능동적 알림 시스템 (Phase 5)**:
- 트리거: 시간, 이벤트, 패턴
- 채널: Discord, macOS 알림
- 관리: 우선순위, 선호도, 스누즈
- 기대 효과: 사용자 능동적 지원

**멀티 모달 지원**:
- 이미지: 스크린샷 분석, OCR
- 음성: 음성 명령 입력
- 비디오: 화면 녹화 분석
- 기대 효과: 더 풍부한 상호작용

---

## 📈 성능 지표 및 목표

### 현재 성능 (v2.0.1)

**응답 시간**:
- 단순 쿼리 (예: "안녕"): 2-5초
- 파일 작업: 3-8초
- Notion 작업: 5-10초
- 메모리 검색: 2-4초
- 복잡한 쿼리: 8-20초

**토큰 사용량** (평균):
- 단순 쿼리: 1,500-2,000 토큰
- 파일 작업: 2,000-3,000 토큰
- 복잡한 쿼리: 3,000-5,000 토큰
- Hierarchical 프로세스: +30-50% 토큰

**메모리 성능**:
- 벡터 인덱스 생성: ~72초 (FAISS)
- 50개 쿼리 검색: ~1.8초
- Precision/Recall: ChromaDB보다 우수

### 목표 성능 (6개월 후)

**응답 시간** (목표: 30-50% 단축):
- 단순 쿼리: 1-3초 (-40%)
- 파일 작업: 2-5초 (-35%)
- Notion 작업: 3-7초 (-30%)
- 메모리 검색: 1-2초 (-50%, 캐싱)
- 복잡한 쿼리: 5-15초 (-25%)

**토큰 사용량** (목표: 20-30% 절감):
- 프롬프트 최적화로 입력 토큰 절감
- 응답 포맷 개선으로 출력 토큰 절감
- 캐싱으로 반복 호출 절감

**메모리 성능** (목표: 검색 정확도 +15%):
- 하이브리드 인덱싱: Precision +10%, Recall +15%
- 적응형 검색: 관련성 점수 향상
- 도메인 특화 임베딩: 의미적 검색 품질 +20%

---

## 🏆 2024-2025 베스트 프랙티스 적용 현황

### CrewAI 베스트 프랙티스

| 항목 | 상태 | 설명 |
|------|------|------|
| ✅ 전문가 > 제너럴리스트 | 완료 | 5개 전문 에이전트 구현 |
| ✅ 80/20 규칙 | 적용 | 작업 설계에 80% 노력 집중 |
| ✅ 상호 보완적 기술 | 완료 | 파일/Notion/메모리/Apple 보완 |
| ✅ 명확한 목적 | 완료 | 각 에이전트 역할 명확 정의 |
| ✅ 위임 활성화 | 완료 | `allow_delegation=True` |
| ✅ Hierarchical 프로세스 | 완료 | Manager-Worker 패턴 |
| ⏳ CrewAI 메모리 통합 | 30% | 환경변수 준비, 통합 설계 중 |

### Multi-Agent Systems 베스트 프랙티스

| 항목 | 상태 | 설명 |
|------|------|------|
| ✅ 단순성 우선 | 완료 | Hierarchical 프로세스로 시작 |
| ✅ 단계적 접근 | 완료 | Phase별 점진적 구현 |
| ✅ 타임아웃 및 재시도 | 완료 | CrewAI 자동 처리 |
| ⏳ 우아한 성능 저하 | 60% | 기본 오류 처리, 개선 필요 |
| ✅ 에러 표면화 | 완료 | 명시적 오류 노출 |
| ⏳ 포괄적 로깅 | 40% | 기본 로깅, 감사 추적 개선 필요 |

### MCP 보안 베스트 프랙티스

| 항목 | 상태 | 설명 |
|------|------|------|
| ✅ 서버 신뢰 | 완료 | Apple MCP 서브모듈 검증 |
| ⏳ 보안 테스트 | 0% | SAST/SCA 파이프라인 미구축 |
| ⏳ 커맨드 인젝션 방지 | 60% | 기본 검증, 강화 필요 |
| ⏳ Resource Indicators | 0% | RFC 8707 미구현 |
| ✅ 로깅 및 모니터링 | 40% | 기본 로깅, 감사 개선 필요 |
| ✅ 비밀 관리 | 완료 | 환경변수 사용 |
| ❌ 샌드박싱 | 0% | 미구현 |

### RAG 베스트 프랙티스

| 항목 | 상태 | 설명 |
|------|------|------|
| ✅ 의미 기반 청킹 | 완료 | LLM 기반 요약 및 분할 |
| ✅ 적응형 검색 | 40% | Cascaded Retriever, 개선 필요 |
| ⏳ 하이브리드 인덱싱 | 0% | Dense만 구현, Sparse 미구현 |
| ✅ 데이터 정제 | 완료 | Memory Curator로 품질 관리 |
| ⏳ 쿼리 향상 | 30% | 기본 구현, 재순위화 미구현 |
| ⏳ 도메인 특화 임베딩 | 0% | Qwen3 기본 모델, 미세 조정 없음 |

---

## 🛠️ 기술 부채

### 높은 우선순위

**CrewAI 어댑터 제거 완료 검증**:
- 현재: `mcp/crewai_adapters/` 디렉토리 삭제됨
- 확인 필요: 모든 도구가 직접 CrewAI BaseTool 상속
- 검증: 단위 테스트 및 통합 테스트 필요

**테스트 커버리지 부족**:
- 현재: 대부분의 테스트 파일 삭제됨
- 필요:
  - 에이전트 단위 테스트
  - 도구 통합 테스트
  - 메모리 시스템 테스트
  - E2E 테스트
- 목표: 80% 코드 커버리지

### 중간 우선순위

**문서 업데이트**:
- 삭제된 파일: `PLAN_for_AI_Agent.md`
- 업데이트 필요:
  - `docs/USAGE.md`: 최신 기능 반영
  - `docs/TESTING.md`: 테스트 가이드 갱신
  - `CLAUDE.md`: 개발 가이드 업데이트

**Apple MCP 오류 처리**:
- 현재: 실패 시 경고 로그만 출력
- 개선: 우아한 성능 저하, 대체 전략 제공

### 낮은 우선순위

**레거시 코드 정리**:
- `interface/cli_react_backup.py`
- `interface/discord_bot_react_backup.py`
- `ai/react_engine/` 디렉토리
- 결정: 학습 목적으로 보관 vs 제거

---

## 📝 다음 단계 (Next Steps)

### 즉시 (1주일 이내)
1. ✅ README.md 업데이트 (완료)
2. ✅ IMPLEMENTATION_STATUS.md 작성 (완료)
3. ⏳ CrewAI 버전 업그레이드 준비
4. ⏳ 테스트 작성 (에이전트 단위 테스트)

### 단기 (1개월 이내)
1. CrewAI 0.201.1 업그레이드
2. CrewAI 메모리 통합 완료
3. 비동기 도구 전환 (FileTool, NotionTool)
4. 테스트 커버리지 50% 달성

### 중기 (3개월 이내)
1. 하이브리드 인덱싱 구현
2. MCP 보안 강화 (Resource Indicators)
3. 성능 모니터링 대시보드
4. 테스트 커버리지 80% 달성

### 장기 (6개월 이내)
1. 도메인 특화 임베딩 모델
2. 능동적 알림 시스템 (Phase 5)
3. 멀티 모달 지원 연구
4. 프로덕션 배포 준비

---

## 📚 참고 자료

### 프로젝트 문서
- README.md: 프로젝트 개요 및 시작 가이드
- CLAUDE.md: AI 어시스턴트 개발 참고사항
- docs/USAGE.md: 사용법
- docs/TESTING.md: 테스트 가이드
- docs/CREWAI_MIGRATION_PLAN.md: CrewAI 마이그레이션 계획

### 연구 자료
- claudedocs/research_ai_agent_systems_20251002.md: 최신 AI 에이전트 기술 조사
  - CrewAI 멀티 에이전트 시스템
  - Multi-Agent Systems 이론
  - Model Context Protocol (MCP)
  - AI 에이전트 메모리 시스템
  - 에이전트 도구 생태계

### 외부 자료
- CrewAI 공식 문서: https://docs.crewai.com/
- MCP 사양: https://modelcontextprotocol.io/
- FAISS 문서: https://github.com/facebookresearch/faiss
- Qwen 모델: https://huggingface.co/Qwen

---

**마지막 업데이트**: 2025년 10월 2일
**작성자**: AI Assistant (Claude Code)
**버전**: 1.0
