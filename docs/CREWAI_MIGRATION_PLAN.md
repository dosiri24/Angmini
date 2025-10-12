# 🔧 Angmini → CrewAI 멀티 에이전트 시스템 마이그레이션 계획서

> **작성일**: 2025-10-02
> **목적**: 단일 ReAct 엔진 → CrewAI 기반 멀티 에이전트 아키텍처 전환
> **예상 기간**: 4-6주
> **위험도**: 🟡 Medium (기존 코드 대부분 재활용 가능)

---

## 📋 목차

1. [현황 분석](#1-현황-분석)
2. [목표 아키텍처](#2-목표-아키텍처)
3. [마이그레이션 전략](#3-마이그레이션-전략)
4. [단계별 실행 계획](#4-단계별-실행-계획)
5. [코드 매핑 가이드](#5-코드-매핑-가이드)
6. [검증 및 테스트](#6-검증-및-테스트)
7. [롤백 전략](#7-롤백-전략)
8. [FAQ](#8-faq)

---

## 1. 현황 분석

### 1.1 현재 아키텍처 (ReAct 엔진)

```
사용자 입력
    ↓
interface/ (CLI/Discord)
    ↓
GoalExecutor (ai/react_engine/goal_executor.py)
    ├─ _update_plan() → Gemini LLM 호출
    ├─ StepExecutor → ToolManager → 개별 Tools
    ├─ PlanningEngine (실패 처리)
    ├─ LoopDetector (무한 루프 감지)
    └─ SafetyGuard (안전 제한)
    ↓
ExecutionContext → MemoryService
    ↓
응답 생성 및 출력
```

**핵심 컴포넌트**:
- `goal_executor.py` (776줄): 메인 오케스트레이터
- `step_executor.py` (16,275바이트): 도구 실행 래퍼
- `planning_engine.py`: 재시도/재계획 로직
- `models.py`: 데이터 클래스 (`PlanStep`, `ExecutionContext`, `StepResult`)

### 1.2 현재 도구 시스템

**도구 목록** (`mcp/tools/`):
- `file_tool.py`: 파일 I/O, 검색, 목록화
- `notion_tool.py`: Notion API (task CRUD, 프로젝트 관계)
- `memory_tool.py`: 경험 검색, 솔루션 찾기, 패턴 분석
- `apple_tool.py`: macOS 시스템 통합 (Notes, Reminders, Calendar)

**도구 인터페이스**:
```python
class ToolBlueprint(ABC):
    @abstractmethod
    def tool_name(self) -> str: ...

    @abstractmethod
    def schema(self) -> Dict[str, Any]: ...

    @abstractmethod
    def __call__(self, **kwargs) -> ToolResult: ...
```

### 1.3 강점 및 보존할 것

✅ **보존 필수**:
- `ai/memory/` 전체 시스템 (SQLite + FAISS + Qwen3 임베딩)
- `ai/ai_brain.py` (Gemini API 클라이언트)
- `mcp/tools/` 원본 (래핑만 추가)
- `ai/core/` 인프라 (config, logger, exceptions)

✅ **잘 작동하는 기능**:
- 메모리 캡처/검색 파이프라인
- Apple MCP 서브프로세스 관리
- 토큰 사용량 추적
- 스트리밍 출력

### 1.4 개선 필요 사항

❌ **현재 한계**:
- 단일 실행 흐름 (병렬 처리 어려움)
- 도메인별 전문화 부족
- 새 도구 추가 시 `goal_executor.py` 수정 필요
- 복잡한 멀티 단계 작업 처리 어려움
- 디버깅 시 전체 엔진 추적 필요

---

## 2. 목표 아키텍처

### 2.1 CrewAI 기반 멀티 에이전트 시스템

```
사용자 입력
    ↓
interface/ (CLI/Discord)
    ↓
Crew (crew/crew_config.py)
    ↓
Planner Agent (Manager) ─┐
                         ├─→ Notion Agent
                         ├─→ File Agent
                         ├─→ Memory Agent
                         └─→ System Agent
    ↓
Task Execution (CrewAI Process)
    ↓
Result Aggregation
    ↓
응답 생성 및 출력
```

### 2.2 에이전트 역할 정의

| 에이전트 | 역할 | 백엔드 도구 | 책임 범위 |
|---------|------|-----------|----------|
| **Planner** | 작업 계획 및 조율 | AIBrain (Gemini) | 의도 파악, 서브 에이전트 선택, 결과 통합 |
| **Notion Agent** | Notion 워크스페이스 관리 | NotionTool | 할일 CRUD, 데이터베이스 쿼리, 페이지 생성 |
| **File Agent** | 파일 시스템 관리 | FileTool | 파일 읽기/쓰기, 디렉토리 검색, 파일 정리 |
| **Memory Agent** | 장기 기억 관리 | MemoryTool + ai/memory/ | 의미적 검색, 메모리 큐레이션, 관련성 랭킹 |
| **System Agent** | macOS 시스템 작업 | AppleTool | 애플리케이션 제어, 시스템 정보, 파일 시스템 |

### 2.3 새 디렉토리 구조

```
Angmini/
├── agents/                         # 🆕 에이전트 정의
│   ├── __init__.py
│   ├── base_agent.py              # 공통 인터페이스
│   ├── planner_agent.py           # 메인 플래너
│   ├── notion_agent.py            # Notion 전문가
│   ├── file_agent.py              # 파일 시스템 전문가
│   ├── memory_agent.py            # 메모리 전문가
│   └── system_agent.py            # macOS 시스템 전문가
│
├── crew/                           # 🆕 Crew 설정
│   ├── __init__.py
│   ├── crew_config.py             # Crew 초기화 및 설정
│   └── task_factory.py            # Task 생성 팩토리
│
├── mcp/
│   ├── tools/                      # ✅ 기존 유지
│   │   ├── file_tool.py
│   │   ├── notion_tool.py
│   │   ├── memory_tool.py
│   │   └── apple_tool.py
│   └── crewai_adapters/           # 🆕 CrewAI 래퍼
│       ├── __init__.py
│       ├── file_crewai_tool.py
│       ├── notion_crewai_tool.py
│       ├── memory_crewai_tool.py
│       └── apple_crewai_tool.py
│
├── ai/
│   ├── react_engine/              # ⏸️ Deprecated (점진적 제거)
│   ├── memory/                    # ✅ 그대로 유지
│   ├── ai_brain.py                # ✅ 그대로 유지
│   └── core/                      # ✅ 그대로 유지
│
└── interface/                      # 🔧 수정 필요
    ├── cli.py                     # Crew 통합
    └── discord_bot.py             # Crew 통합
```

### 2.4 기술 스택 변경

**추가 의존성**:
```txt
crewai>=0.28.0
crewai-tools>=0.2.0
```

**유지 의존성**:
```txt
google-generativeai>=0.5.0    # AIBrain
torch>=2.1.0                  # Memory 시스템
transformers>=4.51.0          # Qwen3 임베딩
faiss-cpu>=1.8.0              # 벡터 검색
notion-client>=2.2.0          # Notion API
discord.py>=2.3.2             # Discord 봇
```

---

## 3. 마이그레이션 전략

### 3.1 점진적 마이그레이션 원칙

1. **백업 우선**: `feat/crewai-migration` 브랜치 생성
2. **병렬 개발**: 기존 ReAct 엔진 유지하며 새 시스템 구축
3. **단계별 검증**: 각 에이전트별 독립 테스트
4. **기능 패리티**: 기존 기능 100% 재현 후 전환
5. **롤백 가능**: 언제든 기존 시스템으로 복귀 가능

### 3.2 코드 재활용 전략

| 구분 | 파일/디렉토리 | 처리 방법 | 이유 |
|-----|-------------|----------|------|
| **완전 보존** | `ai/memory/` | 그대로 사용 | 완성도 높은 시스템 |
| **완전 보존** | `ai/ai_brain.py` | 그대로 사용 | Gemini API 클라이언트 |
| **완전 보존** | `ai/core/` | 그대로 사용 | 인프라 코드 |
| **래핑** | `mcp/tools/*.py` | 원본 유지 + 어댑터 추가 | CrewAI BaseTool 형식 |
| **통합** | `ai/react_engine/planning_engine.py` | Planner Agent로 통합 | 재계획 로직 재사용 |
| **통합** | `ai/react_engine/loop_detector.py` | Planner Agent로 통합 | 무한 루프 감지 |
| **통합** | `system_prompt.md` | Agent backstory로 활용 | 페르소나 재사용 |
| **Deprecated** | `ai/react_engine/goal_executor.py` | 점진적 제거 | CrewAI로 대체 |
| **Deprecated** | `ai/react_engine/step_executor.py` | 점진적 제거 | CrewAI Task로 대체 |
| **수정** | `interface/cli.py` | Crew.kickoff() 통합 | 진입점 변경 |
| **수정** | `interface/discord_bot.py` | Crew.kickoff() 통합 | 진입점 변경 |

### 3.3 데이터 마이그레이션

**메모리 시스템**: 변경 없음
- `data/memory/memories.db` (SQLite)
- `data/memory/memory.index` (FAISS)
- `data/memory/memory.ids`

**로그 시스템**: 변경 없음
- `logs/YYYYMMDD_HHMMSS.log`
- `memory_embedding.log`

---

## 4. 단계별 실행 계획

### Phase 1: 환경 구축 (1주)

#### 1.1 Git 브랜치 생성 및 백업

```bash
# 현재 상태 백업
git checkout -b backup/pre-crewai-migration
git push origin backup/pre-crewai-migration

# 작업 브랜치 생성
git checkout main
git checkout -b feat/crewai-migration
```

#### 1.2 의존성 설치

```bash
# requirements.txt 업데이트
echo "crewai>=0.28.0" >> requirements.txt
echo "crewai-tools>=0.2.0" >> requirements.txt

# 설치 및 검증
pip install -r requirements.txt
python -c "import crewai; print(crewai.__version__)"
```

#### 1.3 디렉토리 구조 생성

```bash
# 새 디렉토리 생성
mkdir -p agents crew mcp/crewai_adapters

# __init__.py 파일 생성
touch agents/__init__.py
touch crew/__init__.py
touch mcp/crewai_adapters/__init__.py
```

#### 1.4 CrewAI 학습 및 POC

```python
# scripts/crewai_poc.py
"""CrewAI 기본 동작 확인용 POC"""
from crewai import Agent, Task, Crew, Process
from ai.ai_brain import AIBrain

# AIBrain을 CrewAI LLM으로 래핑하는 테스트
brain = AIBrain()

test_agent = Agent(
    role='테스트 에이전트',
    goal='CrewAI 동작 확인',
    backstory='CrewAI 통합 테스트를 위한 에이전트',
    verbose=True,
    llm=brain.model  # Gemini 모델 주입
)

test_task = Task(
    description='안녕하세요라고 인사하기',
    expected_output='간단한 인사말',
    agent=test_agent
)

crew = Crew(
    agents=[test_agent],
    tasks=[test_task],
    process=Process.sequential,
    verbose=True
)

result = crew.kickoff()
print(f"결과: {result}")
```

---

### Phase 2: 기반 인프라 구축 (1주)

#### 2.1 `agents/base_agent.py` 구현

```python
"""
agents/base_agent.py
모든 에이전트의 공통 인터페이스 및 유틸리티
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from crewai import Agent
from ai.ai_brain import AIBrain
from ai.memory.service import MemoryService
from ai.core.logger import logger

class BaseAngminiAgent(ABC):
    """Angmini 전용 에이전트 베이스 클래스"""

    def __init__(
        self,
        ai_brain: AIBrain,
        memory_service: Optional[MemoryService] = None,
        verbose: bool = True
    ):
        self.ai_brain = ai_brain
        self.memory_service = memory_service
        self.verbose = verbose
        self._agent: Optional[Agent] = None

    @abstractmethod
    def role(self) -> str:
        """에이전트 역할"""
        pass

    @abstractmethod
    def goal(self) -> str:
        """에이전트 목표"""
        pass

    @abstractmethod
    def backstory(self) -> str:
        """에이전트 배경 스토리"""
        pass

    @abstractmethod
    def tools(self) -> list:
        """에이전트가 사용할 도구 리스트"""
        pass

    def build_agent(self) -> Agent:
        """CrewAI Agent 인스턴스 생성"""
        if self._agent is None:
            self._agent = Agent(
                role=self.role(),
                goal=self.goal(),
                backstory=self.backstory(),
                tools=self.tools(),
                llm=self.ai_brain.model,
                verbose=self.verbose,
                memory=True  # CrewAI 메모리 활성화
            )
            logger.info(f"Agent '{self.role()}' 생성 완료")
        return self._agent

    def get_memory_context(self, query: str, top_k: int = 3) -> str:
        """메모리에서 관련 컨텍스트 조회"""
        if not self.memory_service:
            return ""

        memories = self.memory_service.repository.search(query, top_k=top_k)
        if not memories:
            return ""

        context = "### 관련 경험:\n"
        for mem in memories:
            context += f"- {mem.summary}\n"
        return context
```

#### 2.2 `mcp/crewai_adapters/` 구현

**파일별 어댑터 생성 예시 (FileTool)**:

```python
"""
mcp/crewai_adapters/file_crewai_tool.py
기존 FileTool을 CrewAI BaseTool로 래핑
"""
from crewai_tools import BaseTool
from typing import Type, Any
from pydantic import BaseModel, Field
from mcp.tools.file_tool import FileTool, ToolResult

class FileToolInput(BaseModel):
    """FileTool 입력 스키마"""
    operation: str = Field(..., description="Operation to perform: read_file, write_file, list_directory, search_files")
    path: str = Field(default=".", description="File or directory path")
    content: str = Field(default=None, description="Content to write (for write_file operation)")
    pattern: str = Field(default=None, description="Search pattern (for search_files operation)")

class FileCrewAITool(BaseTool):
    name: str = "파일 시스템 도구"
    description: str = "파일 읽기/쓰기, 디렉토리 목록, 파일 검색을 수행합니다."
    args_schema: Type[BaseModel] = FileToolInput

    def __init__(self):
        super().__init__()
        self._file_tool = FileTool()

    def _run(
        self,
        operation: str,
        path: str = ".",
        content: str = None,
        pattern: str = None,
        **kwargs: Any
    ) -> str:
        """도구 실행"""
        # FileTool 호출
        params = {"operation": operation, "path": path}
        if content:
            params["content"] = content
        if pattern:
            params["pattern"] = pattern

        result: ToolResult = self._file_tool(**params)

        # 결과를 문자열로 변환
        if result.success:
            return f"✅ 성공: {result.data}"
        else:
            return f"❌ 실패: {result.error}"
```

**다른 어댑터들도 동일한 패턴으로 구현**:
- `notion_crewai_tool.py`
- `memory_crewai_tool.py`
- `apple_crewai_tool.py`

#### 2.3 `agents/__init__.py` 유틸리티

```python
"""
agents/__init__.py
에이전트 팩토리 및 공통 유틸리티
"""
from typing import List, Optional
from ai.ai_brain import AIBrain
from ai.memory.service import MemoryService
from .base_agent import BaseAngminiAgent
from .planner_agent import PlannerAgent
from .file_agent import FileAgent
from .notion_agent import NotionAgent
from .memory_agent import MemoryAgent
from .system_agent import SystemAgent

class AgentFactory:
    """에이전트 생성 팩토리"""

    @staticmethod
    def create_all_agents(
        ai_brain: AIBrain,
        memory_service: Optional[MemoryService] = None
    ) -> List[BaseAngminiAgent]:
        """모든 에이전트 생성"""
        return [
            FileAgent(ai_brain, memory_service),
            NotionAgent(ai_brain, memory_service),
            MemoryAgent(ai_brain, memory_service),
            SystemAgent(ai_brain, memory_service)
        ]

    @staticmethod
    def create_planner(
        ai_brain: AIBrain,
        memory_service: Optional[MemoryService] = None
    ) -> PlannerAgent:
        """Planner 에이전트 생성"""
        return PlannerAgent(ai_brain, memory_service)
```

---

### Phase 3: 개별 에이전트 구현 (2주)

#### 3.1 File Agent (가장 단순, 먼저 구현)

```python
"""
agents/file_agent.py
파일 시스템 관리 전문 에이전트
"""
from .base_agent import BaseAngminiAgent
from mcp.crewai_adapters.file_crewai_tool import FileCrewAITool

class FileAgent(BaseAngminiAgent):
    """파일 시스템 작업 전문가"""

    def role(self) -> str:
        return "파일 시스템 관리 전문가"

    def goal(self) -> str:
        return "파일 및 디렉토리 작업을 정확하고 효율적으로 수행"

    def backstory(self) -> str:
        return """
        당신은 파일 시스템 작업의 전문가입니다.
        파일 읽기/쓰기, 디렉토리 탐색, 파일 검색을 담당합니다.
        사용자가 요청한 파일 작업을 안전하고 정확하게 수행하세요.

        주요 책임:
        - 파일 내용 읽기 및 분석
        - 파일 생성 및 수정
        - 디렉토리 구조 탐색
        - 파일 검색 및 필터링
        """

    def tools(self) -> list:
        return [FileCrewAITool()]
```

**테스트 스크립트**:
```python
# scripts/test_file_agent.py
from ai.ai_brain import AIBrain
from agents.file_agent import FileAgent
from crewai import Task, Crew, Process

brain = AIBrain()
file_agent = FileAgent(brain)

task = Task(
    description='현재 디렉토리의 Python 파일 목록을 보여주세요',
    expected_output='Python 파일 목록',
    agent=file_agent.build_agent()
)

crew = Crew(
    agents=[file_agent.build_agent()],
    tasks=[task],
    process=Process.sequential,
    verbose=True
)

result = crew.kickoff()
print(f"결과:\n{result}")
```

#### 3.2 Notion Agent

```python
"""
agents/notion_agent.py
Notion 워크스페이스 관리 전문 에이전트
"""
from .base_agent import BaseAngminiAgent
from mcp.crewai_adapters.notion_crewai_tool import NotionCrewAITool

class NotionAgent(BaseAngminiAgent):
    """Notion 작업 전문가"""

    def role(self) -> str:
        return "Notion 워크스페이스 관리 전문가"

    def goal(self) -> str:
        return "Notion API를 활용하여 할일, 프로젝트, 페이지를 효과적으로 관리"

    def backstory(self) -> str:
        return """
        당신은 Notion 워크스페이스 관리의 전문가입니다.
        할일 생성, 조회, 업데이트, 삭제 및 프로젝트 관계 설정을 담당합니다.

        주요 책임:
        - 할일(Task) CRUD 작업
        - 프로젝트 데이터베이스 쿼리
        - 할일-프로젝트 관계 설정
        - 마감일 및 우선순위 관리

        **중요 규칙**:
        - 할일 생성 시 사용자의 원래 표현 유지
        - 프로젝트 매칭 시 키워드 기반 자동 연결
        - 마감일은 ISO 8601 형식 사용
        """

    def tools(self) -> list:
        return [NotionCrewAITool()]
```

#### 3.3 Memory Agent

```python
"""
agents/memory_agent.py
장기 기억 관리 전문 에이전트
"""
from .base_agent import BaseAngminiAgent
from mcp.crewai_adapters.memory_crewai_tool import MemoryCrewAITool

class MemoryAgent(BaseAngminiAgent):
    """장기 기억 관리 전문가"""

    def role(self) -> str:
        return "장기 기억 및 경험 관리 전문가"

    def goal(self) -> str:
        return "과거 경험을 검색하고 관련성 있는 정보를 제공하여 더 나은 의사결정 지원"

    def backstory(self) -> str:
        return """
        당신은 Angmini의 장기 기억 시스템을 관리하는 전문가입니다.
        벡터 임베딩 기반 의미적 검색으로 관련 경험을 찾아냅니다.

        주요 책임:
        - 과거 실행 경험 검색
        - 유사한 문제의 해결 방법 찾기
        - 사용자 선호도 및 패턴 분석
        - 학습된 지식 활용

        **검색 전략**:
        - 의미적 유사도 기반 검색
        - 컨텍스트 기반 필터링
        - 관련성 순위 정렬
        """

    def tools(self) -> list:
        return [MemoryCrewAITool()]
```

#### 3.4 System Agent (Apple MCP)

```python
"""
agents/system_agent.py
macOS 시스템 작업 전문 에이전트
"""
from .base_agent import BaseAngminiAgent
from mcp.crewai_adapters.apple_crewai_tool import AppleCrewAITool

class SystemAgent(BaseAngminiAgent):
    """macOS 시스템 작업 전문가"""

    def role(self) -> str:
        return "macOS 시스템 통합 전문가"

    def goal(self) -> str:
        return "Apple MCP를 활용하여 macOS 애플리케이션 및 시스템 레벨 작업 수행"

    def backstory(self) -> str:
        return """
        당신은 macOS 시스템 통합의 전문가입니다.
        Apple Notes, Reminders, Calendar 등 시스템 앱과 상호작용합니다.

        주요 책임:
        - Notes 앱 관리 (메모 생성/조회/수정)
        - Reminders 관리 (할일 생성/완료)
        - Calendar 이벤트 관리
        - 시스템 정보 조회
        - 파일 시스템 고급 작업

        **주의사항**:
        - Apple MCP 서버가 실행 중이어야 함
        - 권한이 필요한 작업은 사용자 확인 필요
        """

    def tools(self) -> list:
        return [AppleCrewAITool()]
```

#### 3.5 Planner Agent (메인 오케스트레이터)

```python
"""
agents/planner_agent.py
메인 플래너 에이전트 - 작업 분석 및 조율
"""
from .base_agent import BaseAngminiAgent
from ai.react_engine.loop_detector import LoopDetector
from ai.core.logger import logger

class PlannerAgent(BaseAngminiAgent):
    """작업 계획 및 조율 전문가"""

    def __init__(self, ai_brain, memory_service=None, verbose=True):
        super().__init__(ai_brain, memory_service, verbose)
        self.loop_detector = LoopDetector()  # 기존 로직 재사용

    def role(self) -> str:
        return "작업 계획 및 조율 총괄 책임자"

    def goal(self) -> str:
        return "사용자 요청을 분석하여 최적의 실행 계획을 수립하고 서브 에이전트들을 조율"

    def backstory(self) -> str:
        # 기존 system_prompt.md 내용 활용
        with open('ai/react_engine/prompt_templates/system_prompt.md', 'r', encoding='utf-8') as f:
            original_prompt = f.read()

        return f"""
        당신은 Angmini의 메인 플래너입니다.
        사용자 요청을 받아 어떤 전문 에이전트들이 필요한지 판단하고 작업을 조율합니다.

        **핵심 원칙**:
        {original_prompt}

        **추가 책임**:
        - 사용자 의도 파악 (대화 vs 작업 요청)
        - 필요한 전문 에이전트 선택
        - 작업 순서 결정 (순차/병렬)
        - 에이전트 간 데이터 전달 관리
        - 실패 시 재계획 수립
        - 최종 결과 통합 및 검증

        **사용 가능한 전문 에이전트**:
        - File Agent: 파일 시스템 작업
        - Notion Agent: Notion 워크스페이스 관리
        - Memory Agent: 과거 경험 검색
        - System Agent: macOS 시스템 작업
        """

    def tools(self) -> list:
        # Planner는 직접 도구를 사용하지 않고, 다른 에이전트에게 위임
        return []

    def check_loop_risk(self, task_history: list) -> bool:
        """무한 루프 위험 감지 (기존 LoopDetector 활용)"""
        # 기존 loop_detector.py 로직 통합
        if len(task_history) < 3:
            return False

        recent_tasks = [t.description for t in task_history[-3:]]
        if len(set(recent_tasks)) == 1:
            logger.warning(f"루프 감지: 동일한 작업 반복 - {recent_tasks[0]}")
            return True

        return False
```

---

### Phase 4: Crew 통합 (1주)

#### 4.1 `crew/crew_config.py` 구현

```python
"""
crew/crew_config.py
Crew 초기화 및 설정 관리
"""
from typing import Optional, List
from crewai import Crew, Process
from ai.ai_brain import AIBrain
from ai.memory.service import MemoryService
from agents import AgentFactory
from ai.core.logger import logger

class AngminiCrew:
    """Angmini CrewAI 설정 및 초기화"""

    def __init__(
        self,
        ai_brain: AIBrain,
        memory_service: Optional[MemoryService] = None,
        verbose: bool = True
    ):
        self.ai_brain = ai_brain
        self.memory_service = memory_service
        self.verbose = verbose

        # 에이전트 생성
        self.planner = AgentFactory.create_planner(ai_brain, memory_service)
        self.worker_agents = AgentFactory.create_all_agents(ai_brain, memory_service)

        logger.info(f"Crew 초기화 완료 - Planner + {len(self.worker_agents)} 워커")

    def create_crew(self, tasks: List, process_type: str = "hierarchical") -> Crew:
        """Crew 인스턴스 생성"""
        all_agents = [agent.build_agent() for agent in self.worker_agents]

        if process_type == "hierarchical":
            # Planner가 Manager 역할
            crew = Crew(
                agents=all_agents,
                tasks=tasks,
                process=Process.hierarchical,
                manager_agent=self.planner.build_agent(),
                verbose=self.verbose,
                memory=True,  # 대화 컨텍스트 유지
                embedder={
                    "provider": "huggingface",
                    "config": {
                        "model": "Qwen/Qwen3-Embedding-0.6B"
                    }
                }
            )
        else:
            # 순차 실행
            crew = Crew(
                agents=all_agents,
                tasks=tasks,
                process=Process.sequential,
                verbose=self.verbose,
                memory=True
            )

        return crew

    def kickoff(self, user_input: str) -> str:
        """사용자 요청 실행"""
        from crew.task_factory import TaskFactory

        # Task 생성
        task_factory = TaskFactory(
            planner=self.planner,
            worker_agents=self.worker_agents,
            memory_service=self.memory_service
        )

        tasks = task_factory.create_tasks_from_input(user_input)

        # Crew 실행
        crew = self.create_crew(tasks, process_type="hierarchical")
        result = crew.kickoff()

        logger.info(f"Crew 실행 완료 - 결과: {len(str(result))} 문자")
        return str(result)
```

#### 4.2 `crew/task_factory.py` 구현

```python
"""
crew/task_factory.py
사용자 입력을 CrewAI Task로 변환
"""
from typing import List, Optional
from crewai import Task
from agents.planner_agent import PlannerAgent
from agents.base_agent import BaseAngminiAgent
from ai.memory.service import MemoryService
from ai.core.logger import logger

class TaskFactory:
    """Task 생성 팩토리"""

    def __init__(
        self,
        planner: PlannerAgent,
        worker_agents: List[BaseAngminiAgent],
        memory_service: Optional[MemoryService] = None
    ):
        self.planner = planner
        self.worker_agents = {agent.role(): agent for agent in worker_agents}
        self.memory_service = memory_service

    def create_tasks_from_input(self, user_input: str) -> List[Task]:
        """사용자 입력으로부터 Task 리스트 생성"""

        # 메모리에서 관련 컨텍스트 조회
        memory_context = ""
        if self.memory_service:
            memories = self.memory_service.repository.search(user_input, top_k=3)
            if memories:
                memory_context = "\n\n### 관련 경험:\n"
                for mem in memories:
                    memory_context += f"- {mem.summary}\n"

        # Planner가 분석할 메인 Task 생성
        planning_task = Task(
            description=f"""
            사용자 요청: {user_input}
            {memory_context}

            다음을 수행하세요:
            1. 사용자 의도 파악 (순수 대화 vs 작업 요청)
            2. 필요한 전문 에이전트 식별
            3. 작업 순서 결정
            4. 각 에이전트에게 명확한 지시사항 전달
            """,
            expected_output="실행 계획 및 에이전트 할당 결과",
            agent=self.planner.build_agent()
        )

        # Hierarchical 모드에서는 Planner가 자동으로 서브 Task 생성
        return [planning_task]

    def create_sequential_tasks(
        self,
        descriptions: List[str],
        agent_names: List[str]
    ) -> List[Task]:
        """순차 실행용 Task 생성 (명시적 순서)"""
        tasks = []

        for desc, agent_name in zip(descriptions, agent_names):
            if agent_name not in self.worker_agents:
                logger.warning(f"알 수 없는 에이전트: {agent_name}")
                continue

            agent = self.worker_agents[agent_name]
            task = Task(
                description=desc,
                expected_output=f"{agent_name} 작업 결과",
                agent=agent.build_agent()
            )
            tasks.append(task)

        # Task 의존성 설정 (순차 실행)
        for i in range(1, len(tasks)):
            tasks[i].context = [tasks[i-1]]  # 이전 Task 결과를 컨텍스트로 사용

        return tasks
```

---

### Phase 5: 인터페이스 통합 (1주)

#### 5.1 `interface/cli.py` 수정

```python
# interface/cli.py (핵심 부분만)

from crew.crew_config import AngminiCrew
from ai.ai_brain import AIBrain
from ai.memory.factory import create_memory_service
from ai.core.logger import logger

class CLI:
    def __init__(self):
        self.ai_brain = AIBrain()
        self.memory_service = create_memory_service()

        # 🆕 CrewAI 초기화
        self.crew = AngminiCrew(
            ai_brain=self.ai_brain,
            memory_service=self.memory_service,
            verbose=True
        )

        logger.info("CLI 초기화 완료 (CrewAI 모드)")

    def run(self):
        """메인 실행 루프"""
        print("Angmini CLI (CrewAI 모드)")
        print("종료하려면 'exit' 입력\n")

        while True:
            user_input = input("You: ").strip()

            if user_input.lower() in ['exit', 'quit']:
                break

            if not user_input:
                continue

            # 🆕 Crew 실행
            try:
                result = self.crew.kickoff(user_input)
                print(f"\nAngmini: {result}\n")
            except Exception as e:
                logger.error(f"실행 오류: {e}", exc_info=True)
                print(f"❌ 오류 발생: {e}\n")
```

#### 5.2 `interface/discord_bot.py` 수정

```python
# interface/discord_bot.py (핵심 부분만)

import discord
from crew.crew_config import AngminiCrew
from ai.ai_brain import AIBrain
from ai.memory.factory import create_memory_service

class AngminiBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.ai_brain = AIBrain()
        self.memory_service = create_memory_service()

        # 🆕 CrewAI 초기화
        self.crew = AngminiCrew(
            ai_brain=self.ai_brain,
            memory_service=self.memory_service,
            verbose=False  # Discord에서는 verbose 끄기
        )

    async def on_message(self, message: discord.Message):
        # 봇 자신의 메시지 무시
        if message.author == self.user:
            return

        # 🆕 Crew 실행
        try:
            # 타이핑 인디케이터 표시
            async with message.channel.typing():
                result = self.crew.kickoff(message.content)

            # 결과 전송 (2000자 제한)
            if len(result) > 2000:
                result = result[:1997] + "..."

            await message.channel.send(result)

        except Exception as e:
            await message.channel.send(f"❌ 오류 발생: {e}")
```

#### 5.3 `main.py` 업데이트 (선택적)

```python
# main.py
"""
Angmini 진입점
"""
import os
from dotenv import load_dotenv
from ai.core.logger import logger

def main():
    load_dotenv()

    interface = os.getenv("DEFAULT_INTERFACE", "cli").lower()

    logger.info(f"Angmini 시작 - 인터페이스: {interface}")

    if interface == "cli":
        from interface.cli import CLI
        cli = CLI()
        cli.run()

    elif interface == "discord":
        from interface.discord_bot import AngminiBot
        token = os.getenv("DISCORD_BOT_TOKEN")
        if not token:
            raise ValueError("DISCORD_BOT_TOKEN 환경변수 필요")

        bot = AngminiBot()
        bot.run(token)

    else:
        raise ValueError(f"지원하지 않는 인터페이스: {interface}")

if __name__ == "__main__":
    main()
```

---

### Phase 6: 테스트 및 검증 (1주)

#### 6.1 통합 테스트 작성

```python
# tests/test_crewai_integration.py
"""
CrewAI 통합 테스트
"""
import pytest
from crew.crew_config import AngminiCrew
from ai.ai_brain import AIBrain
from ai.memory.factory import create_memory_service

@pytest.fixture
def crew():
    brain = AIBrain()
    memory = create_memory_service()
    return AngminiCrew(brain, memory, verbose=False)

def test_file_agent_basic(crew):
    """File Agent 기본 동작 테스트"""
    result = crew.kickoff("현재 디렉토리에 있는 Python 파일 목록을 보여줘")
    assert "py" in result.lower()

def test_notion_agent_list_tasks(crew):
    """Notion Agent 할일 조회 테스트"""
    result = crew.kickoff("Notion에서 내 할일 목록 가져와줘")
    assert "할일" in result or "task" in result.lower()

def test_memory_agent_search(crew):
    """Memory Agent 검색 테스트"""
    result = crew.kickoff("과거에 파일 관련 작업을 어떻게 했는지 찾아줘")
    assert len(result) > 0

def test_planner_delegation(crew):
    """Planner의 작업 위임 테스트"""
    result = crew.kickoff("파일 목록을 확인하고 Notion에 요약해줘")
    # Planner가 File Agent → Notion Agent 순서로 위임해야 함
    assert "성공" in result or "완료" in result

def test_conversation_handling(crew):
    """순수 대화 처리 테스트"""
    result = crew.kickoff("안녕하세요")
    assert len(result) > 0
    # 도구를 사용하지 않고 대화로만 응답해야 함
```

#### 6.2 기능 패리티 체크리스트

기존 ReAct 엔진과 동일한 기능 제공 확인:

- [ ] 파일 읽기/쓰기
- [ ] Notion 할일 CRUD
- [ ] Notion 프로젝트 관계 설정
- [ ] 메모리 검색
- [ ] Apple MCP 통합
- [ ] 스트리밍 출력
- [ ] 토큰 사용량 추적
- [ ] 오류 핸들링
- [ ] 무한 루프 감지
- [ ] 메모리 캡처
- [ ] CLI 인터페이스
- [ ] Discord 봇 인터페이스

---

## 5. 코드 매핑 가이드

### 5.1 핵심 개념 매핑

| 기존 ReAct 엔진 | CrewAI 대응 | 비고 |
|---------------|-----------|------|
| `GoalExecutor` | `Crew` + `PlannerAgent` | 오케스트레이션 |
| `StepExecutor` | `Task` 실행 | CrewAI가 자동 처리 |
| `PlanStep` | `Task` | 작업 단위 |
| `ExecutionContext` | `Crew.memory` | 컨텍스트 저장 |
| `ToolManager` | CrewAI Tools | 도구 관리 |
| `_update_plan()` | `Manager Agent` | 계획 수립 |
| `planning_engine.py` | `PlannerAgent` 로직 | 재계획 통합 |
| `loop_detector.py` | `PlannerAgent.check_loop_risk()` | 무한 루프 감지 |

### 5.2 프롬프트 재활용

**기존**: `ai/react_engine/prompt_templates/system_prompt.md`

**새 위치**:
- `PlannerAgent.backstory()`: 메인 시스템 프롬프트
- 각 에이전트 `backstory()`: 도메인별 전문화 프롬프트

### 5.3 메모리 시스템 통합

```python
# 기존: GoalExecutor._prefetch_relevant_memories()
memories = self.memory_service.repository.search(goal, top_k=3)

# 🆕 CrewAI: TaskFactory.create_tasks_from_input()
if self.memory_service:
    memories = self.memory_service.repository.search(user_input, top_k=3)
    memory_context = "\n\n### 관련 경험:\n"
    for mem in memories:
        memory_context += f"- {mem.summary}\n"

    # Task description에 포함
    task = Task(
        description=f"{user_input}\n{memory_context}",
        ...
    )
```

### 5.4 토큰 사용량 추적

```python
# 기존: ExecutionContext.record_token_usage()

# 🆕 CrewAI: Crew.usage_metrics (내장)
crew = Crew(...)
result = crew.kickoff()

# CrewAI는 자동으로 토큰 사용량 추적
print(crew.usage_metrics)
```

---

## 6. 검증 및 테스트

### 6.1 단위 테스트

각 에이전트별 독립 테스트:

```bash
pytest tests/test_file_agent.py -v
pytest tests/test_notion_agent.py -v
pytest tests/test_memory_agent.py -v
pytest tests/test_system_agent.py -v
pytest tests/test_planner_agent.py -v
```

### 6.2 통합 테스트

전체 Crew 동작 테스트:

```bash
pytest tests/test_crewai_integration.py -v
```

### 6.3 수동 테스트 시나리오

**시나리오 1: 단순 파일 작업**
```
Input: "현재 디렉토리에 test.txt 파일을 만들어줘"
Expected: File Agent가 파일 생성
Verify: test.txt 존재 확인
```

**시나리오 2: Notion 할일 생성**
```
Input: "Notion에 '회의록 작성' 할일 추가해줘"
Expected: Notion Agent가 할일 생성
Verify: Notion 웹에서 할일 확인
```

**시나리오 3: 복합 작업**
```
Input: "requirements.txt를 읽고 Notion에 의존성 목록을 정리해줘"
Expected: File Agent (읽기) → Notion Agent (쓰기)
Verify: Notion 페이지에 의존성 목록 존재
```

**시나리오 4: 메모리 활용**
```
Input: "지난번에 파일 작업 어떻게 했지?"
Expected: Memory Agent가 과거 경험 검색
Verify: 관련 메모리 반환
```

**시나리오 5: 순수 대화**
```
Input: "오늘 날씨 어때?"
Expected: Planner가 도구 없이 대화로 응답
Verify: 도구 호출 없음
```

### 6.4 성능 벤치마크

| 메트릭 | 기존 ReAct | CrewAI 목표 | 비고 |
|-------|-----------|-----------|------|
| 단순 작업 응답 시간 | ~2초 | ~3초 | CrewAI 오버헤드 허용 |
| 복합 작업 응답 시간 | ~5초 | ~6초 | 병렬 처리로 개선 가능 |
| 메모리 사용량 | ~200MB | ~250MB | 에이전트 인스턴스 증가 |
| 토큰 사용량 | 기준 | 1.2배 이하 | 에이전트 간 통신 비용 |

---

## 7. 롤백 전략

### 7.1 백업 브랜치

```bash
# 마이그레이션 실패 시
git checkout main
git branch -D feat/crewai-migration

# 또는 특정 커밋으로 복구
git reset --hard <commit-hash>
```

### 7.2 환경변수 스위치 (선택적)

`.env`에 모드 선택 옵션 추가:

```bash
# .env
EXECUTION_MODE=crewai  # 또는 react
```

`main.py`에서 분기:

```python
execution_mode = os.getenv("EXECUTION_MODE", "crewai")

if execution_mode == "react":
    # 기존 ReAct 엔진 사용
    from ai.react_engine.goal_executor import GoalExecutor
    executor = GoalExecutor(...)
elif execution_mode == "crewai":
    # 새 CrewAI 사용
    from crew.crew_config import AngminiCrew
    crew = AngminiCrew(...)
```

### 7.3 단계별 롤백 포인트

- **Phase 1 완료 후**: CrewAI 설치만 롤백
- **Phase 2 완료 후**: 새 디렉토리 삭제로 롤백
- **Phase 3 완료 후**: 에이전트 구현 롤백
- **Phase 4 완료 후**: Crew 통합 롤백
- **Phase 5 완료 후**: 인터페이스 원복으로 전체 롤백

---

## 8. FAQ

### Q1: 기존 메모리 데이터는 어떻게 되나요?

**A**: 전혀 영향 없습니다. `ai/memory/` 시스템은 그대로 유지되며, CrewAI Memory Agent가 백엔드로 사용합니다.

### Q2: 기존 ReAct 엔진 코드는 삭제해야 하나요?

**A**: 아니요. 처음에는 deprecated 처리만 하고, CrewAI가 안정화된 후 삭제합니다.

### Q3: Apple MCP는 어떻게 되나요?

**A**: `AppleCrewAITool`로 래핑하여 System Agent가 사용합니다. 기존 `apple_tool.py`는 수정 없이 그대로 사용합니다.

### Q4: CrewAI가 Gemini API를 지원하나요?

**A**: 네. `ai_brain.model`을 Agent의 `llm` 파라미터로 주입하면 됩니다.

### Q5: 토큰 사용량이 증가하지 않을까요?

**A**: 에이전트 간 통신 비용으로 약간 증가할 수 있지만, Hierarchical Process로 불필요한 호출을 줄일 수 있습니다.

### Q6: 병렬 실행이 가능한가요?

**A**: 네. CrewAI는 독립적인 Task를 병렬로 실행할 수 있습니다. 기존 ReAct 엔진보다 효율적입니다.

### Q7: 기존 기능이 모두 동작할까요?

**A**: Phase 6의 기능 패리티 체크리스트를 모두 통과하면 100% 호환됩니다.

### Q8: 마이그레이션 실패 시 어떻게 하나요?

**A**: `backup/pre-crewai-migration` 브랜치로 복구하거나, `EXECUTION_MODE=react`로 기존 시스템 사용합니다.

---

## 9. 다음 단계

마이그레이션 완료 후:

1. **성능 최적화**
   - 에이전트별 캐싱 전략
   - Task 병렬 실행 최대화
   - 토큰 사용량 프로파일링

2. **새 에이전트 추가**
   - Web Agent (웹 검색/스크래핑)
   - Code Agent (코드 분석/생성)
   - Analytics Agent (데이터 분석)

3. **문서 업데이트**
   - `CLAUDE.md` 업데이트
   - `docs/USAGE.md` 리뉴얼
   - 새 아키텍처 다이어그램 추가

4. **모니터링 강화**
   - 에이전트별 성능 메트릭
   - 실패율 추적
   - 사용자 만족도 측정

---

## 10. 참고 자료

- [CrewAI 공식 문서](https://docs.crewai.com/)
- [CrewAI Hierarchical Process](https://docs.crewai.com/concepts/processes#hierarchical-process)
- [CrewAI Custom Tools](https://docs.crewai.com/concepts/tools#custom-tools)
- [CrewAI Memory](https://docs.crewai.com/concepts/memory)
- [Angmini 기존 설계 문서](React_Engine_Design.md)

---

**최종 업데이트**: 2025-10-02
**작성자**: Claude Code
**상태**: ✅ Ready for Implementation
