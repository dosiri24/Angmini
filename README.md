# 🤖 Angmini - Personal AI Assistant

**Angmini**는 Google Gemini와 CrewAI 기반의 차세대 멀티 에이전트 시스템을 활용한 개인용 AI 어시스턴트입니다. 전문화된 에이전트들이 협력하여 복잡한 작업을 자동화하고, 다양한 인터페이스(CLI, Discord)를 통해 사용자와 상호작용합니다.

[![CrewAI](https://img.shields.io/badge/CrewAI-0.28.0+-blue.svg)](https://github.com/crewAIInc/crewAI)
[![Python](https://img.shields.io/badge/Python-3.10+-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 🎯 프로젝트 목표

- CrewAI 기반 **멀티 에이전트 협업 시스템** 구축 (2024-2025 최신 아키텍처 패턴 적용)
- Google Gemini 기반 LLM과 **MCP 도구 생태계** 통합
- **Hierarchical 프로세스**로 효율적인 작업 위임 및 조율
- 확장 가능한 도구(파일, Notion, Apple, 메모리 등) 통합
- 환경 변수 기반 설정으로 인터페이스를 유연하게 전환
- **장기 기억 시스템**으로 컨텍스트 지속성 및 학습 능력 제공

## 🏗️ 핵심 아키텍처

### 1. **CrewAI 멀티 에이전트 시스템**

Angmini는 CrewAI의 **Hierarchical Process**를 활용하여 Manager-Worker 패턴으로 작업을 효율적으로 조율합니다.

#### 전문화된 에이전트 팀

- **PlannerAgent (Manager)**:
  - 사용자 요청 분석 및 작업 계획 수립
  - 전문 에이전트에게 동적 작업 위임
  - 작업 결과 검토 및 품질 보장

- **FileAgent**: 파일 시스템 작업 전문가
  - 파일 읽기/쓰기/이동/삭제
  - 디렉토리 탐색 및 검색
  - 배치 작업 및 파일 관리

- **NotionAgent**: Notion 워크스페이스 관리 전문가
  - 할일 및 프로젝트 CRUD 작업
  - 데이터베이스 조회 및 관리
  - 작업 우선순위 분석

- **MemoryAgent**: 장기 기억 관리 및 경험 검색 전문가
  - 과거 작업 경험 검색
  - 유사 상황 패턴 분석
  - 솔루션 추천 및 학습

- **AppleAppsAgent**: macOS 시스템 통합 전문가 (macOS only)
  - Notes, Reminders, Calendar, Mail 등 연동
  - Apple MCP 서버를 통한 시스템 통합
  - macOS 내장 앱 자동화

#### 협업 패턴 및 베스트 프랙티스

**Hierarchical Teams Pattern** (계층적 팀 패턴):
- PlannerAgent가 복잡한 목표를 하위 작업으로 분해
- 각 전문가 에이전트에게 최적 작업 할당
- 동적 작업 분배 및 실시간 조정
- 결과 통합 및 품질 검증

**설계 원칙** (2024-2025 베스트 프랙티스):
- ✅ **전문가 > 제너럴리스트**: 각 에이전트는 특정 도메인의 전문가
- ✅ **80/20 규칙**: 에이전트 정의 20%, 작업 설계 80%
- ✅ **상호 보완적 기술**: 다르지만 보완적인 능력 조합
- ✅ **명확한 목적**: 각 에이전트는 명확한 역할과 책임
- ✅ **위임 활성화**: `allow_delegation=True`로 자율적 협업 지원

### 2. **지능형 메모리 시스템**

**장기 기억 아키텍처**:
```
사용자 작업 → Memory Curator (LLM 기반 요약) → 중복 제거
   → FAISS 벡터 인덱스 + SQLite 메타데이터 → Cascaded Retriever
```

**핵심 기능**:
- **Memory Service**: 장기 기억 저장 및 관련성 기반 검색
- **Vector Index**: Qwen3-0.6B 임베딩 기반 의미적 유사도 검색
- **Memory Curator**: LLM 기반 자동 요약 및 품질 관리
- **Cascaded Retriever**: 다단계 필터링으로 정확한 기억 검색
- **Deduplicator**: 중복 방지 및 메모리 최적화
- **FAISS + SQLite**: 고성능 벡터 검색 및 메타데이터 관리

**메모리 큐레이션 전략** (2024-2025):
- **노화 (Aging)**: 오래된 메모리에 낮은 가중치 부여
- **프루닝 (Pruning)**: 사용되지 않는 메모리 제거
- **충돌 해결**: 모순되는 정보 탐지 및 최신 정보로 업데이트
- **계층적 조직**: 중요도에 따른 메모리 계층화

### 3. **MCP (Model Context Protocol) 도구 시스템**

**MCP 통합 아키텍처**:
- **Tool Manager**: 도구 등록 및 실행 라우팅
- **CrewAI Adapters**: MCP 도구를 CrewAI BaseTool로 변환
- **보안 베스트 프랙티스**: 로깅, 입력 검증, 샌드박싱

**도구 카탈로그**:

| 도구 | 기능 | 에이전트 |
|------|------|---------|
| **File Tool** | 파일 읽기/쓰기/이동/삭제, 디렉토리 탐색 | FileAgent |
| **Notion Tool** | 할일 관리, 프로젝트 추적, DB 조회 | NotionAgent |
| **Memory Tool** | 장기 기억 저장 및 검색 | MemoryAgent |
| **Apple Tool** | macOS 내장 앱 연동 (Notes, Calendar 등) | AppleAppsAgent |

**도구 설계 원칙**:
- ✅ **표준화된 인터페이스**: MCP 사양 준수
- ✅ **명확한 오류 처리**: 우아한 성능 저하 (Graceful Degradation)
- ✅ **성능 최적화**: 응답 시간 최소화 및 캐싱
- ✅ **포괄적 문서화**: 사용 예제 및 제한사항 명시
- ✅ **비동기 지원**: 비블로킹 작업 처리

### 4. **다중 인터페이스 지원**

**CLI** (Command Line Interface):
- 실시간 스트리밍 출력 지원
- CrewAI verbose 모드 통합
- 개발자 친화적 디버깅 인터페이스
- 빠른 테스트 및 개발 워크플로우

**Discord Bot**:
- Discord 메시지 기반 상호작용
- 비동기 메시지 처리
- 채널 내 응답 및 상태 업데이트
- 다중 사용자 지원

**환경변수 기반 전환**:
```bash
DEFAULT_INTERFACE=cli     # CLI 모드
DEFAULT_INTERFACE=discord # Discord 모드
```

## 📁 프로젝트 구조

```
Angmini/
├── main.py                     # 애플리케이션 진입점
├── angmini_cli.py             # CLI 편의 스크립트
├── requirements.txt            # Python 의존성 (CrewAI 포함)
├── .env.example               # 환경변수 템플릿
├── CLAUDE.md                  # AI 어시스턴트 개발 가이드
├── IMPLEMENTATION_STATUS.md   # 구현 현황 및 로드맵
├── README.md                  # 프로젝트 개요 (현재 파일)
├── LICENSE                    # MIT 라이선스
│
├── ai/                        # AI 엔진 핵심
│   ├── ai_brain.py           # Gemini API 연동 클래스
│   ├── core/                 # 핵심 모듈
│   │   ├── config.py         # 환경변수 및 설정 관리
│   │   ├── logger.py         # 로깅 시스템
│   │   └── exceptions.py     # 커스텀 예외 클래스
│   ├── memory/               # 지능형 메모리 시스템
│   │   ├── service.py        # 메모리 서비스 (고수준 API)
│   │   ├── factory.py        # 메모리 컴포넌트 팩토리
│   │   ├── pipeline.py       # 메모리 처리 파이프라인
│   │   ├── embedding.py      # Qwen3 임베딩 엔진
│   │   ├── memory_curator.py # LLM 기반 자동 큐레이터
│   │   ├── cascaded_retriever.py # 다단계 검색 엔진
│   │   ├── hybrid_retriever.py   # 하이브리드 검색기
│   │   ├── deduplicator.py   # 중복 제거기
│   │   ├── importance_scorer.py  # 중요도 평가기
│   │   ├── retention_policy.py   # 보존 정책 관리
│   │   ├── metrics.py        # 메모리 성능 메트릭스
│   │   ├── memory_records.py # 메모리 레코드 모델
│   │   ├── snapshot_extractor.py # 실행 스냅샷 추출
│   │   ├── entity/           # 엔티티 기반 메모리 (진행 중)
│   │   ├── prompts/          # LLM 프롬프트 템플릿
│   │   └── storage/          # 저장소 구현
│   │       ├── repository.py # 통합 메모리 리포지토리
│   │       ├── sqlite_store.py # SQLite 메타데이터 저장소
│   │       └── vector_index.py # FAISS 벡터 인덱스
│   ├── agents/               # CrewAI 에이전트 구현
│   │   ├── __init__.py       # AgentFactory
│   │   ├── base_agent.py     # 에이전트 기본 클래스
│   │   ├── planner_agent.py  # 계획 및 조율 매니저
│   │   ├── file_agent.py     # 파일 시스템 전문가
│   │   ├── notion_agent.py   # Notion 관리 전문가
│   │   ├── memory_agent.py   # 메모리 관리 전문가
│   │   └── apple_apps_agent.py # Apple 시스템 통합 전문가
│   ├── crew/                 # CrewAI Crew 설정
│   │   ├── crew_config.py    # Crew 초기화 및 실행 조율
│   │   └── task_factory.py   # Task 생성 팩토리
│   └── shared/               # 공유 컴포넌트
│
├── mcp/                      # MCP 도구 생태계
│   ├── tool_blueprint.py     # 도구 기본 추상 클래스
│   ├── apple_mcp_manager.py  # Apple MCP 서버 관리자
│   └── tools/                # 구체적 도구 구현
│       ├── file_tool.py      # 파일 시스템 도구 + CrewAI 어댑터
│       ├── notion_tool.py    # Notion API 도구 + CrewAI 어댑터
│       ├── apple_tool.py     # Apple 도구 + CrewAI 어댑터
│       └── memory_tool.py    # 메모리 도구 + CrewAI 어댑터
│
├── interface/                # 다중 인터페이스 지원
│   ├── cli.py               # CLI (CrewAI 통합)
│   ├── discord_bot.py       # Discord Bot (CrewAI 통합)
│   ├── streaming.py         # 실시간 스트리밍 인터페이스
│   └── summary.py           # 실행 결과 요약 포맷터
│
├── external/                # 외부 의존성 (Git 서브모듈)
│   └── apple-mcp/           # Apple MCP 서버 (TypeScript)
│       ├── dist/index.js    # 빌드된 Apple MCP 서버
│       └── package.json     # Node.js 패키지 설정
│
├── bin/                     # 실행 스크립트
│   └── angmini              # CLI 실행 래퍼 스크립트
│
├── scripts/                 # 유틸리티 스크립트
│   └── gemini_quickcheck.py # Gemini API 연결 테스트
│
├── tests/                   # 테스트 스위트
│   ├── test_file_tool.py    # 파일 도구 테스트
│   └── ...                  # 기타 테스트 파일
│
├── docs/                    # 프로젝트 문서
│   ├── USAGE.md             # 사용 가이드
│   ├── TESTING.md           # 테스트 가이드
│   ├── INSTALL.md           # 설치 가이드
│   ├── CREWAI_MIGRATION_PLAN.md # ReAct → CrewAI 마이그레이션
│   ├── memory_maintenance.md    # 메모리 시스템 유지보수
│   └── APPLE_TOOL_GUIDE.md      # Apple MCP 사용법
│
├── claudedocs/              # AI 조사 보고서 및 분석
│   └── research_ai_agent_systems_20251002.md
│
├── archive/                 # 레거시 코드 보관
│   └── react_engine/        # 구 ReAct 엔진 (참고용)
│
├── data/                    # 애플리케이션 데이터
│   └── memory/              # 메모리 시스템 데이터베이스
│       ├── memories.db      # SQLite 메모리 메타데이터
│       ├── memory.ids       # 메모리 ID 매핑 인덱스
│       └── memory.index     # FAISS 벡터 인덱스
│
├── logs/                    # 애플리케이션 로그
│   ├── YYYYMMDD_HHMMSS.log  # 세션별 타임스탬프 로그
│   └── memory_embedding.log # 메모리 임베딩 로그
│
├── .serena/                 # Serena MCP 작업 공간
│   ├── cache/               # Serena 캐시
│   └── memories/            # Serena 메모리
│
└── .claude/                 # Claude Code 설정
    └── commands/            # 커스텀 슬래시 커맨드
```

## 🛠️ 기술 스택

### 핵심 프레임워크
- **언어**: Python 3.10+
- **AI 프레임워크**: CrewAI 0.28.0+ (멀티 에이전트 협업)
- **AI 모델**: Google Gemini (gemini-2.5-pro)
- **벡터 검색**: FAISS + Qwen3-Embedding-0.6B

### 주요 라이브러리
```python
# Multi-Agent Framework
crewai>=0.28.0                  # 멀티 에이전트 프레임워크
crewai-tools>=0.2.0             # CrewAI 도구 라이브러리

# AI & Machine Learning
google-generativeai>=0.5.0      # Gemini API
torch>=2.1.0                    # 딥러닝 프레임워크
transformers>=4.51.0            # Hugging Face 트랜스포머
faiss-cpu>=1.8.0                # 벡터 유사도 검색

# Integration
discord.py>=2.3.2               # Discord 봇
notion-client>=2.2.0            # Notion API
send2trash>=1.8.2               # 안전한 파일 삭제

# Utilities
python-dotenv>=1.0.0            # 환경변수 관리
numpy>=1.24.0                   # 수치 연산
```

## ✨ 핵심 기능

### 🤝 **멀티 에이전트 협업 시스템**

**Hierarchical Process** (계층적 프로세스):
- Planner가 Manager 역할로 작업 위임 및 조율
- 전문화된 에이전트가 각 도메인별로 효율적 작업 수행
- 자동 작업 분배 및 동적 리소스 할당
- 컨텍스트 공유 및 에이전트 간 협업

**작업 위임 및 조율**:
```
사용자 요청 → PlannerAgent 분석
   ↓
작업 분해 및 우선순위 결정
   ↓
전문 에이전트에게 동적 할당
   ↓
FileAgent / NotionAgent / MemoryAgent / AppleAppsAgent
   ↓
결과 통합 및 품질 검증
   ↓
최종 응답 생성
```

### 🧩 **확장 가능한 도구 생태계**

**파일 시스템** (FileAgent):
- 읽기/쓰기/검색/정리 등 포괄적 파일 관리
- 배치 작업 및 대용량 파일 처리
- 안전한 휴지통 이동 (send2trash)
- 절대 경로 기반 안정적 작업

**Notion 통합** (NotionAgent):
- 할일 관리 (TODO 데이터베이스)
- 프로젝트 추적 (Project 데이터베이스)
- 데이터베이스 조회 및 관계 관리
- 우선순위 분석 및 필터링

**macOS 시스템** (AppleAppsAgent):
- Apple MCP를 통한 시스템 통합
- Notes, Reminders, Calendar, Mail, Contacts 등 연동
- AppleScript 기반 자동화
- macOS 전용 기능

**메모리 도구** (MemoryAgent):
- 장기 기억 저장 및 의미적 검색
- 과거 경험 회상 및 패턴 분석
- 솔루션 추천 및 학습
- 컨텍스트 기반 검색

### 🧠 **장기 기억 시스템**

**의미적 검색** (Semantic Search):
- Qwen3 임베딩을 활용한 관련성 기반 기억 검색
- 벡터 유사도 계산으로 정확한 매칭
- 키워드가 아닌 의미 기반 검색

**지능형 큐레이션** (Intelligent Curation):
- LLM 기반 자동 요약 및 품질 관리
- 중복 제거 및 메모리 최적화
- 시간 경과에 따른 노화 및 프루닝

**계층적 검색** (Cascaded Retrieval):
- 다단계 필터링으로 정확한 정보 검색
- LLM 기반 관련성 평가
- 동적 follow-up 쿼리 생성

**자동 보존** (Automatic Retention):
- 중요도 기반 기억 보존 정책
- 실시간 메트릭스 및 성능 모니터링
- 세션 간 컨텍스트 지속

### 🎯 **다중 인터페이스 지원**

**CLI** (개발자 친화적):
- 터미널 기반 인터페이스
- CrewAI verbose 모드 지원
- 실시간 스트리밍 출력
- 빠른 테스트 및 디버깅

**Discord Bot** (사용자 친화적):
- Discord 메시지 기반 상호작용
- 비동기 메시지 처리
- 다중 사용자 지원
- 채널 내 응답

**유연한 전환**:
- 환경변수로 인터페이스 간 즉시 전환
- 동일한 에이전트 시스템 공유
- 일관된 사용자 경험

### 🛡️ **신뢰성 및 안전성**

**에이전트 검증**:
- 각 에이전트의 작업 결과 검증 및 피드백
- PlannerAgent의 품질 보장 역할
- 실패 시 자동 재시도 및 대안 제시

**오류 복구** (2024-2025 베스트 프랙티스):
- 타임아웃 및 재시도 메커니즘
- 우아한 성능 저하 (Graceful Degradation)
- 명시적 오류 노출 및 디버깅

**토큰 사용량 추적**:
- LLM 비용 모니터링
- 토큰 사용량 로깅
- 성능 최적화

**상세한 로깅**:
- CrewAI verbose 모드
- 커스텀 로깅 시스템
- 세션별 타임스탬프 로그

## 🎮 실제 사용 사례

### 📁 **파일 관리 자동화**
```bash
👤 You: 내 다운로드 폴더에서 PDF 파일들을 날짜별로 정리해줘
🤖 Angmini: [Planner → FileAgent 위임]
             → FileAgent가 파일 목록 조회
             → 날짜별로 폴더 생성 및 파일 이동
             → 작업 완료 보고
```

### 📋 **Notion 워크스페이스 관리**
```bash
👤 You: 오늘 완료해야 할 작업들을 Notion에서 가져와서 우선순위 순으로 보여줘
🤖 Angmini: [Planner → NotionAgent 위임]
             → NotionAgent가 할일 데이터베이스 조회
             → 우선순위 정렬 및 포맷팅
             → 결과 반환
```

### 🧠 **지능형 정보 검색**
```bash
👤 You: 지난 달에 논의했던 API 설계 방향에 대해 다시 알려줘
🤖 Angmini: [Planner → MemoryAgent 위임]
             → MemoryAgent가 관련 기억 검색
             → 시간순/관련도순 정렬
             → 요약 및 제시
```

### 🖥️ **macOS 시스템 통합**
```bash
👤 You: 오늘 받은 이메일 중 중요한 것들 보여줘
🤖 Angmini: [Planner → AppleAppsAgent 위임]
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
CREW_PROCESS_TYPE=hierarchical          # hierarchical 또는 sequential
CREW_MEMORY_ENABLED=true                # CrewAI 메모리 활성화
```

### 3. Apple MCP 설정 (macOS만 해당)

```bash
# Bun 설치 (https://bun.sh/)
curl -fsSL https://bun.sh/install | bash

# Apple MCP 서브모듈 초기화
git submodule update --init --recursive

# Apple MCP 빌드
cd external/apple-mcp
bun install
bun run build
cd ../..
```

### 4. 실행

```bash
# CLI 모드 실행 (기본)
python main.py

# 또는 편리한 실행 스크립트 사용
bin/angmini

# DEBUG 모드 (CrewAI verbose 출력 포함)
LOG_LEVEL=DEBUG python main.py
```

### 5. 빠른 테스트

```bash
# 단일 명령 실행
bin/angmini --no-stream "안녕"

# 도움말 보기
bin/angmini --help

# 버전 확인
bin/angmini --version
```

## 📚 문서

### 사용 가이드
- **사용법**: `docs/USAGE.md` - 상세한 사용 가이드
- **설치**: `docs/INSTALL.md` - 설치 및 설정 가이드
- **테스트**: `docs/TESTING.md` - 테스트 시나리오 및 검증

### 기술 문서
- **CrewAI 마이그레이션**: `docs/CREWAI_MIGRATION_PLAN.md` - ReAct → CrewAI 전환 계획
- **메모리 유지보수**: `docs/memory_maintenance.md` - 메모리 시스템 관리
- **Apple MCP 가이드**: `docs/APPLE_TOOL_GUIDE.md` - Apple 도구 사용법
- **개발 가이드**: `CLAUDE.md` - AI 어시스턴트 개발 참고사항

### 연구 보고서
- **AI 에이전트 기술 조사**: `claudedocs/research_ai_agent_systems_20251002.md`
  - CrewAI 멀티 에이전트 시스템
  - Multi-Agent Systems 이론
  - Model Context Protocol (MCP)
  - AI 에이전트 메모리 시스템
  - 에이전트 도구 생태계

## 🔄 최근 주요 업데이트

### v2.0.1 - 최신 기술 적용 (2025-10-02)
- ✅ **2024-2025 베스트 프랙티스 적용**
  - Hierarchical 프로세스 최적화
  - 에이전트 전문화 강화 (80/20 규칙)
  - 협업 패턴 개선

- ✅ **메모리 시스템 강화**
  - 메모리 큐레이션 전략 적용
  - 중복 제거 메커니즘 개선
  - Cascaded Retriever 성능 향상

- ✅ **도구 시스템 개선**
  - CrewAI 직접 통합 (어댑터 제거)
  - 오류 처리 강화
  - 비동기 지원 개선

### v2.0.0 - CrewAI 마이그레이션 (2025-10-02)
- ✅ ReAct Engine → CrewAI 멀티 에이전트 시스템 전환
- ✅ 5개 전문 에이전트 구현 (Planner, File, Notion, Memory, AppleApps)
- ✅ Hierarchical Process 적용 (Manager-Worker 패턴)
- ✅ MCP 도구들을 CrewAI BaseTool로 어댑팅
- ✅ CLI & Discord 인터페이스 CrewAI 통합
- ✅ Apple MCP 서버 초기화 문제 해결

### 레거시 ReAct 엔진
- 기존 ReAct 엔진 코드는 백업되어 유지됨
- 참고 및 학습 목적으로 보관

## 🛡️ 보안 및 프라이버시

### MCP 보안 베스트 프랙티스 (2024-2025)
- ✅ **서버 신뢰**: 신뢰할 수 있는 MCP 서버만 사용
- ✅ **보안 테스트**: SAST 및 SCA 통합
- ✅ **커맨드 인젝션 방지**: 입력 검증 및 정제
- ✅ **로깅 및 모니터링**: 포괄적 감사 추적
- ✅ **비밀 관리**: 환경변수 사용, 하드코딩 금지
- ✅ **샌드박싱**: 리소스 격리 및 제한

### 데이터 보호
- 로컬 데이터 저장 (외부 전송 최소화)
- 환경변수 기반 비밀 관리
- 안전한 파일 삭제 (send2trash)

## 🧪 테스트

```bash
# 전체 테스트 실행
pytest tests/

# 특정 테스트 파일
pytest tests/test_file_tool.py

# Verbose 모드
pytest tests/ -v

# 빠른 Gemini API 체크
python scripts/gemini_quickcheck.py
```

## 🗺️ 로드맵

자세한 구현 계획은 `IMPLEMENTATION_STATUS.md`를 참고하세요.

**Phase 1-2**: ✅ 핵심 CrewAI 시스템 (완료)
**Phase 3**: ✅ 도구 통합 (완료)
**Phase 4**: ✅ 메모리 시스템 (완료)
**Phase 5**: ⏸️ 능동적 알림 시스템 (계획 중)
**Phase 6**: 🚧 성능 최적화 및 고도화 (진행 중)

## 🤝 기여

이슈와 PR은 언제나 환영합니다!

## 📄 라이선스

MIT License

---

**Built with** ❤️ **using**:
- [CrewAI](https://www.crewai.com/) - Multi-Agent Framework
- [Google Gemini](https://deepmind.google/technologies/gemini/) - AI Model
- [FAISS](https://github.com/facebookresearch/faiss) - Vector Search
- [Qwen](https://huggingface.co/Qwen) - Embedding Model
- [Model Context Protocol](https://modelcontextprotocol.io/) - Tool Integration Standard
