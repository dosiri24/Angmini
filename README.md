# 🤖 Angmini - Personal AI Assistant (CrewAI Edition)

**Angmini**는 Google Gemini와 CrewAI 기반의 멀티 에이전트 시스템을 활용한 개인용 AI 어시스턴트입니다. 전문화된 에이전트들이 협력하여 복잡한 작업을 자동화하고, 다양한 인터페이스(CLI, Discord)를 통해 사용자와 상호작용합니다.

## 🎯 프로젝트 목표
- CrewAI 기반 멀티 에이전트 협업 시스템 구축
- Google Gemini 기반 LLM과 MCP 도구 생태계 통합
- Hierarchical 프로세스로 효율적인 작업 위임 및 조율
- 확장 가능한 도구(파일, Notion, Apple, 메모리 등) 통합
- 환경 변수 기반 설정으로 인터페이스를 유연하게 전환

## 🏗️ 핵심 아키텍처

### 1. **CrewAI 멀티 에이전트 시스템 (핵심)**
- **PlannerAgent (Manager)**: 사용자 요청을 분석하고 작업을 전문 에이전트에게 위임
- **FileAgent**: 파일 시스템 작업 전문가
- **NotionAgent**: Notion 워크스페이스 관리 전문가
- **MemoryAgent**: 장기 기억 관리 및 경험 검색 전문가
- **SystemAgent**: macOS 시스템 통합 전문가
- **Hierarchical Process**: Manager-Worker 패턴으로 효율적인 작업 조율

### 2. **지능형 메모리 시스템**
- **Memory Service**: 장기 기억 저장 및 관련성 기반 검색
- **Vector Index**: Qwen3 임베딩 기반 의미적 유사도 검색
- **Memory Curator**: LLM 기반 기억 요약 및 품질 관리
- **Cascaded Retriever**: 다단계 필터링으로 정확한 기억 검색
- **FAISS + SQLite**: 고성능 벡터 검색 및 메타데이터 저장

### 3. **MCP (Model Context Protocol) 도구 시스템**
- **Tool Manager**: 도구 등록 및 실행 라우팅
- **CrewAI Adapters**: MCP 도구를 CrewAI BaseTool로 변환
- **File Tool**: 파일 시스템 조작 (읽기/쓰기/목록/검색)
- **Notion Tool**: Notion API 연동 (할일 관리, 프로젝트 관리)
- **Memory Tool**: 장기 기억 저장 및 검색 도구
- **Apple Tool**: macOS 시스템 통합 (Apple MCP 서버 기반)

### 4. **다중 인터페이스 지원**
- **CLI**: 실시간 스트리밍 출력 지원 명령줄 인터페이스
- **Discord Bot**: Discord 메시지 기반 상호작용
- **Streaming Interface**: 작업 진행 상황을 실시간으로 확인
- 환경변수 기반 인터페이스 전환

## 📁 프로젝트 구조
```
Angmini/
├── main.py                     # 애플리케이션 진입점
├── requirements.txt            # Python 의존성 (CrewAI 포함)
├── .env.example               # 환경변수 템플릿
├── .env                       # 실제 환경변수 (gitignore)
├── .gitignore                 # Git 무시 파일 목록
├── .gitmodules                # Git 서브모듈 설정
├── memory_embedding.log       # 메모리 임베딩 로그
├── PLAN_for_AI_Agent.md       # AI 에이전트 개발 계획
├── .vscode/                   # VS Code 설정
├── ai/                        # AI 엔진 핵심
│   ├── ai_brain.py           # Gemini API 연동 클래스 (LiteLLM 통합)
│   ├── core/                 # 핵심 모듈
│   │   ├── __init__.py
│   │   ├── config.py         # 환경변수 및 설정 관리
│   │   ├── logger.py         # 로깅 시스템
│   │   └── exceptions.py     # 커스텀 예외 클래스
│   ├── memory/               # 메모리 시스템
│   │   ├── __init__.py
│   │   ├── embedding.py      # Qwen3 임베딩 처리
│   │   ├── factory.py        # 메모리 팩토리
│   │   ├── service.py        # 메모리 서비스
│   │   ├── pipeline.py       # 메모리 파이프라인
│   │   ├── memory_records.py # 메모리 레코드 관리
│   │   ├── memory_curator.py # LLM 기반 메모리 큐레이터
│   │   ├── cascaded_retriever.py # 다단계 검색기
│   │   ├── deduplicator.py   # 중복 제거기
│   │   ├── metrics.py        # 메모리 메트릭스
│   │   ├── retention_policy.py # 보존 정책
│   │   ├── snapshot_extractor.py # 스냅샷 추출기
│   │   ├── prompts/          # 메모리 관련 프롬프트
│   │   │   ├── cascaded_filter_prompt.md
│   │   │   └── memory_curator_prompt.md
│   │   └── storage/          # 저장소 구현
│   │       ├── __init__.py
│   │       ├── base.py       # 저장소 기본 클래스
│   │       ├── repository.py # 메모리 리포지토리
│   │       ├── sqlite_store.py # SQLite 저장소
│   │       └── vector_index.py # FAISS 벡터 인덱스
│   └── react_engine/         # 레거시 ReAct 엔진 (백업)
│       ├── goal_executor.py  # (백업: cli_react_backup.py)
│       └── ...               # 기타 ReAct 관련 파일들
├── agents/                   # CrewAI 에이전트 구현 (신규)
│   ├── __init__.py
│   ├── base_agent.py        # 에이전트 기본 클래스
│   ├── planner_agent.py     # 계획 및 조율 매니저
│   ├── file_agent.py        # 파일 시스템 전문가
│   ├── notion_agent.py      # Notion 관리 전문가
│   ├── memory_agent.py      # 메모리 관리 전문가
│   └── system_agent.py      # 시스템 통합 전문가
├── crew/                    # CrewAI Crew 설정 (신규)
│   ├── __init__.py
│   ├── crew_config.py       # Crew 초기화 및 설정
│   └── task_factory.py      # Task 생성 팩토리
├── mcp/                     # MCP 도구 생태계
│   ├── __init__.py
│   ├── tool_blueprint.py    # 도구 기본 추상 클래스
│   ├── tool_manager.py      # 도구 등록/실행 관리
│   ├── apple_mcp_manager.py # Apple MCP 서버 관리자
│   ├── crewai_adapters/     # CrewAI 어댑터 (신규)
│   │   ├── __init__.py
│   │   ├── file_crewai_tool.py    # FileTool 어댑터
│   │   ├── notion_crewai_tool.py  # NotionTool 어댑터
│   │   ├── memory_crewai_tool.py  # MemoryTool 어댑터
│   │   └── apple_crewai_tool.py   # AppleTool 어댑터
│   └── tools/               # 구체적 도구 구현
│       ├── __init__.py
│       ├── file_tool.py     # 파일 시스템 도구
│       ├── notion_tool.py   # Notion API 도구
│       ├── apple_tool.py    # Apple 도구
│       └── memory_tool.py   # 메모리 도구
├── interface/               # 사용자 인터페이스
│   ├── __init__.py
│   ├── cli.py              # CLI (CrewAI 통합)
│   ├── discord_bot.py      # Discord Bot (CrewAI 통합)
│   ├── cli_react_backup.py # 레거시 ReAct CLI 백업
│   ├── discord_bot_react_backup.py # 레거시 Discord 백업
│   ├── streaming.py        # 스트리밍 인터페이스
│   └── summary.py          # 실행 결과 요약 포맷터
├── external/               # 외부 의존성
│   └── apple-mcp/          # Apple MCP 서버 (Git 서브모듈)
│       ├── dist/
│       │   └── index.js    # 빌드된 Apple MCP 서버
│       ├── src/
│       │   ├── index.ts
│       │   └── tools.ts
│       ├── package.json
│       ├── bun.lockb
│       └── ...
├── tests/                  # 테스트 코드
├── scripts/                # 유틸리티 스크립트
│   ├── gemini_quickcheck.py # Gemini API 연결 테스트
│   └── crewai_poc.py       # CrewAI POC 테스트
├── docs/                   # 프로젝트 문서
│   ├── USAGE.md
│   ├── CREWAI_MIGRATION_PLAN.md # CrewAI 마이그레이션 계획
│   ├── memory_maintenance.md
│   ├── APPLE_MCP_분석_보고서.md
│   └── APPLE_TOOL_GUIDE.md
├── logs/                   # 로그 파일들
└── data/                   # 데이터 저장소
    └── memory/             # 메모리 데이터베이스
        ├── memories.db     # SQLite 메모리 데이터베이스
        ├── memory.ids      # 메모리 ID 인덱스
        └── memory.index    # FAISS 벡터 인덱스
```

## 🛠️ 기술 스택
- **언어**: Python 3.11+
- **AI 프레임워크**: CrewAI 0.28.0+ (멀티 에이전트 협업)
- **AI 모델**: Google Gemini (gemini-2.5-pro) via LiteLLM
- **벡터 검색**: FAISS + Qwen3-Embedding-0.6B
- **주요 라이브러리**:
  - `crewai`: 멀티 에이전트 프레임워크
  - `crewai-tools`: CrewAI 도구 라이브러리
  - `google-generativeai`: Gemini API
  - `discord.py`: Discord 봇 기능
  - `notion-client`: Notion API 연동
  - `faiss-cpu`: 벡터 유사도 검색
  - `transformers`: Qwen3 임베딩 모델
  - `python-dotenv`: 환경변수 관리

## ✨ 핵심 기능

### 🤝 **멀티 에이전트 협업 시스템**
- **Hierarchical Process**: Planner가 Manager 역할로 작업 위임 및 조율
- **전문화된 에이전트**: 각 도메인별 전문 에이전트가 효율적으로 작업 수행
- **자동 작업 분배**: 사용자 요청을 분석하여 적절한 에이전트에게 자동 할당
- **컨텍스트 공유**: 에이전트 간 작업 결과 공유 및 협업
- **동적 프로세스**: 작업 복잡도에 따라 Hierarchical/Sequential 프로세스 선택

### 🧩 **확장 가능한 도구 생태계**
- **파일 시스템**: 읽기/쓰기/검색/정리 등 포괄적 파일 관리
- **Notion 통합**: 할일 관리, 프로젝트 추적, 데이터베이스 조회
- **macOS 시스템**: Apple MCP를 통한 Contacts, Notes, Messages, Mail, Calendar 등 연동
- **메모리 도구**: 장기 기억 저장 및 의미적 검색
- **모듈형 설계**: 새로운 도구를 CrewAI 어댑터로 쉽게 추가

### 🧠 **장기 기억 시스템**
- **의미적 검색**: Qwen3 임베딩을 활용한 관련성 기반 기억 검색
- **지능형 큐레이션**: LLM 기반 자동 요약 및 품질 관리
- **계층적 검색**: 다단계 필터링으로 정확한 정보 검색
- **자동 보존**: 중요도 기반 기억 보존 정책
- **실시간 메트릭스**: 메모리 성능 모니터링 및 최적화

### 🎯 **다중 인터페이스 지원**
- **CLI**: 개발자를 위한 터미널 기반 인터페이스 (CrewAI verbose 모드 지원)
- **Discord Bot**: Discord 메시지 기반 상호작용
- **실시간 스트리밍**: 에이전트 작업 진행 상황을 실시간으로 확인
- **유연한 전환**: 환경변수로 인터페이스 간 즉시 전환

### 🛡️ **신뢰성 및 안전성**
- **에이전트 검증**: 각 에이전트의 작업 결과 검증 및 피드백
- **에러 복구**: 실패 시 Planner가 자동으로 대안 제시
- **토큰 사용량 추적**: LLM 비용 모니터링 (thinking_tokens, response_tokens)
- **상세한 로깅**: CrewAI verbose 모드 및 커스텀 로깅 시스템

## 🎮 실제 사용 사례

### 📁 **파일 관리 자동화**
```bash
# FileAgent가 자동으로 처리
👤 You: 내 다운로드 폴더에서 PDF 파일들을 날짜별로 정리해줘
🤖 Angmini: [Planner → FileAgent 위임]
             → FileAgent가 파일 목록 조회
             → 날짜별로 폴더 생성 및 파일 이동
             → 작업 완료 보고
```

### 📋 **Notion 워크스페이스 관리**
```bash
# NotionAgent가 전문적으로 처리
👤 You: 오늘 완료해야 할 작업들을 Notion에서 가져와서 우선순위 순으로 보여줘
🤖 Angmini: [Planner → NotionAgent 위임]
             → NotionAgent가 할일 데이터베이스 조회
             → 우선순위 정렬 및 포맷팅
             → 결과 반환
```

### 🧠 **지능형 정보 검색**
```bash
# MemoryAgent가 과거 경험 검색
👤 You: 지난 달에 논의했던 API 설계 방향에 대해 다시 알려줘
🤖 Angmini: [Planner → MemoryAgent 위임]
             → MemoryAgent가 관련 기억 검색
             → 시간순/관련도순 정렬
             → 요약 및 제시
```

### 🖥️ **macOS 시스템 통합**
```bash
# SystemAgent가 Apple MCP를 통해 처리
👤 You: 오늘 받은 이메일 중 중요한 것들 보여줘
🤖 Angmini: [Planner → SystemAgent 위임]
             → Apple MCP Mail 도구 호출
             → 이메일 조회 및 필터링
             → 중요 메일 목록 반환
```

## 🚀 시작하기

### 1. 환경 설정

```bash
# 1. 가상환경 생성 및 활성화
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2. 의존성 설치
pip install -r requirements.txt
```

### 2. 환경변수 설정

`.env.example`을 참고하여 `.env` 파일을 생성하세요:

```bash
# 필수 설정
DEFAULT_INTERFACE=cli                    # cli 또는 discord
GEMINI_API_KEY=your_api_key_here        # Google Gemini API 키
GEMINI_MODEL=gemini-2.5-pro             # Gemini 모델

# CrewAI 설정 (자동 설정됨)
EMBEDDINGS_HUGGINGFACE_URL=https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-MiniLM-L6-v2

# 선택 설정
DISCORD_BOT_TOKEN=your_token_here       # Discord 사용 시
NOTION_API_KEY=your_notion_key          # Notion 연동 시
LOG_LEVEL=INFO                          # DEBUG, INFO, WARNING, ERROR
STREAM_DELAY=0.01                       # 스트리밍 딜레이 (초)
```

### 3. Apple MCP 설정 (macOS만 해당)

```bash
# Bun 설치 (https://bun.sh/)
curl -fsSL https://bun.sh/install | bash

# Apple MCP 서브모듈 초기화
git submodule update --init --recursive

# Apple MCP 빌드 (자동으로 처리되지만 수동으로도 가능)
cd external/apple-mcp
bun install
bun run build
cd ../..
```

### 4. 실행

```bash
# CLI 모드 실행 (기본)
python main.py

# DEBUG 모드 (CrewAI verbose 출력 포함)
LOG_LEVEL=DEBUG python main.py
```

## 📚 문서

- **사용 가이드**: `docs/USAGE.md`
- **CrewAI 마이그레이션 계획**: `docs/CREWAI_MIGRATION_PLAN.md`
- **메모리 유지보수**: `docs/memory_maintenance.md`
- **Apple MCP 가이드**: `docs/APPLE_TOOL_GUIDE.md`
- **개발 계획**: `PLAN_for_AI_Agent.md`

## 🔄 최근 주요 업데이트

### v2.0.0 - CrewAI 마이그레이션 (2025-10-02)
- ✅ ReAct Engine → CrewAI 멀티 에이전트 시스템 전환
- ✅ 5개 전문 에이전트 구현 (Planner, File, Notion, Memory, System)
- ✅ Hierarchical Process 적용 (Manager-Worker 패턴)
- ✅ MCP 도구들을 CrewAI BaseTool로 어댑팅
- ✅ CLI & Discord 인터페이스 CrewAI 통합
- ✅ Apple MCP 서버 초기화 문제 해결
- 📝 향후 개선: 메모리 시스템과 CrewAI 더 긴밀한 통합

### 레거시 ReAct 엔진
- 기존 ReAct 엔진 코드는 백업되어 유지됨
- `interface/cli_react_backup.py`
- `interface/discord_bot_react_backup.py`

## 🤝 기여

이슈와 PR은 언제나 환영합니다!

## 📄 라이선스

MIT License
