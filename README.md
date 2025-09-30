# 📊 Angmini - Personal AI Assistant

**Angmini**는 Google Gemini 기반의 ReAct (Reasoning and Acting) 패턴을 활용한 개인용 AI 어시스턴트 프로젝트입니다. 다양한 인터페이스(CLI, Discord)를 통해 사용자의 작업을 자동화하고 도구를 활용한 복잡한 작업을 수행할 수 있습니다.

## 🎯 프로젝트 목표
- Google Gemini 기반 LLM과 MCP 도구 생태계를 활용한 ReAct 엔진 구축
- 환경 변수 기반 설정으로 인터페이스를 유연하게 전환
- 확장 가능한 도구(파일, Notion, 웹 등) 통합
- 지능적 계획 수립과 강력한 에러 복구 시스템

## 🏗️ 핵심 아키텍처

### 1. **ReAct Engine (핵심)**
- **Goal Executor**: 사용자 목표를 받아 계획을 수립하고 실행하는 핵심 엔진
- **Step Executor**: 개별 단계를 실행하고 결과를 검증
- **Planning Engine**: 실패 시 재시도/재계획 결정
- **Loop Detector**: 무한 루프나 반복 패턴 감지
- **Safety Guard**: 실행 제한 및 안전 장치

### 2. **지능형 메모리 시스템**
- **Memory Service**: 장기 기억 저장 및 관련성 기반 검색
- **Vector Index**: 임베딩 기반 의미적 유사도 검색
- **Memory Curator**: 중복 제거 및 기억 품질 관리
- **Cascaded Retriever**: 다단계 필터링으로 정확한 기억 검색
- **Retention Policy**: 기억 보존 정책 및 자동 정리

### 3. **MCP (Model Context Protocol) 도구 시스템**
- **Tool Manager**: 도구 등록 및 실행 라우팅
- **File Tool**: 파일 시스템 조작 (읽기/쓰기/목록/검색)
- **Notion Tool**: Notion API 연동 (할일 관리, 프로젝트 관리)
- **Memory Tool**: 장기 기억 저장 및 검색 도구
- **Apple Tool**: macOS 시스템 통합 (Apple MCP 기반)

### 4. **다중 인터페이스 지원**
- **CLI**: 실시간 스트리밍 출력 지원 명령줄 인터페이스
- **Discord Bot**: Discord 메시지 기반 상호작용
- **Streaming Interface**: 토큰 단위 실시간 응답 출력
- 환경변수 기반 인터페이스 전환

## 📁 프로젝트 구조
```
Angmini/
├── main.py                     # 애플리케이션 진입점
├── requirements.txt            # Python 의존성
├── .env.example               # 환경변수 템플릿
├── .env                       # 실제 환경변수 (gitignore)
├── .gitignore                 # Git 무시 파일 목록
├── .gitmodules                # Git 서브모듈 설정
├── memory_embedding.log       # 메모리 임베딩 로그
├── PLAN_for_AI_Agent.md       # AI 에이전트 개발 계획
├── .vscode/                   # VS Code 설정
├── ai/                        # AI 엔진 핵심
│   ├── ai_brain.py           # Gemini API 연동 클래스
│   ├── core/                 # 핵심 모듈
│   │   ├── __init__.py
│   │   ├── config.py         # 환경변수 및 설정 관리
│   │   ├── logger.py         # 로깅 시스템
│   │   └── exceptions.py     # 커스텀 예외 클래스
│   ├── memory/               # 메모리 시스템 (새로 추가됨)
│   │   ├── __init__.py
│   │   ├── embedding.py      # 임베딩 처리
│   │   ├── factory.py        # 메모리 팩토리
│   │   ├── service.py        # 메모리 서비스
│   │   ├── pipeline.py       # 메모리 파이프라인
│   │   ├── memory_records.py # 메모리 레코드 관리
│   │   ├── memory_curator.py # 메모리 큐레이터
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
│   │       └── vector_index.py # 벡터 인덱스
│   └── react_engine/         # ReAct 패턴 구현체
│       ├── __init__.py
│       ├── goal_executor.py  # 목표 실행 엔진
│       ├── step_executor.py  # 단계별 실행기
│       ├── planning_engine.py # 재계획/재시도 결정
│       ├── loop_detector.py  # 무한 루프 감지
│       ├── safety_guard.py   # 안전 제한 장치
│       ├── runtime.py        # 실행 팩토리
│       ├── models.py         # 데이터 모델 정의
│       ├── agent_scratchpad.py # 사고 과정 기록
│       ├── conversation_memory.py # 대화 메모리
│       ├── result_formatter.py # 결과 포맷터
│       └── prompt_templates/ # LLM 프롬프트 템플릿
│           ├── system_prompt.md
│           ├── react_prompt.md
│           └── final_response_prompt.md
├── mcp/                      # MCP 도구 생태계
│   ├── __init__.py
│   ├── tool_blueprint.py     # 도구 기본 추상 클래스
│   ├── tool_manager.py       # 도구 등록/실행 관리
│   ├── apple_mcp_manager.py  # Apple MCP 관리자 (새로 추가됨)
│   └── tools/                # 구체적 도구 구현
│       ├── __init__.py
│       ├── file_tool.py      # 파일 시스템 도구
│       ├── notion_tool.py    # Notion API 도구
│       ├── apple_tool.py     # Apple 도구 (새로 추가됨)
│       └── memory_tool.py    # 메모리 도구 (새로 추가됨)
├── interface/                # 사용자 인터페이스
│   ├── __init__.py
│   ├── cli.py               # 명령줄 인터페이스
│   ├── discord_bot.py       # Discord 봇 인터페이스
│   ├── streaming.py         # 스트리밍 인터페이스 (새로 추가됨)
│   └── summary.py           # 실행 결과 요약 포맷터
├── external/                # 외부 의존성 (새로 추가됨)
│   └── apple-mcp/           # Apple MCP 서브모듈
│       ├── index.ts
│       ├── tools.ts
│       ├── package.json
│       ├── manifest.json
│       └── ... (TypeScript/Node.js 파일들)
├── tests/                   # 테스트 코드
│   ├── stream.py            # 스트리밍 테스트
│   ├── test_*.py            # 다양한 테스트 파일들
│   └── ...
├── scripts/                 # 유틸리티 스크립트
│   └── gemini_quickcheck.py # Gemini API 연결 테스트
├── docs/                    # 프로젝트 문서
│   ├── USAGE.md            # 사용 가이드
│   ├── React_Engine_Design.md # 엔진 설계 문서
│   ├── PLAN_for_Users.md   # 사용자용 계획
│   ├── instructions.md     # 개발 지침
│   ├── memory_maintenance.md # 메모리 유지보수 가이드
│   ├── APPLE_MCP_분석_보고서.md
│   └── APPLE_TOOL_GUIDE.md
├── logs/                    # 로그 파일들
│   └── *.log               # 타임스탬프별 로그 파일들
└── data/                   # 데이터 저장소
    └── memory/             # 메모리 데이터베이스
        ├── memories.db     # SQLite 메모리 데이터베이스
        ├── memory.ids      # 메모리 ID 인덱스
        └── memory.index    # 벡터 인덱스 파일
```

## ️ 기술 스택
- **언어**: Python 3.11+
- **AI 모델**: Google Gemini (gemini-1.5-pro)
- **주요 라이브러리**: 
  - `google-generativeai`: Gemini API 연동
  - `discord.py`: Discord 봇 기능
  - `notion-client`: Notion API 연동
  - `python-dotenv`: 환경변수 관리

## ✨ 핵심 기능

### 🧠 **지능적 작업 자동화**
- **ReAct 패턴**: LLM이 추론(Reasoning)과 행동(Acting)을 반복하며 복잡한 작업을 단계별로 해결
- **자동 계획 수립**: 사용자 요청을 분석하여 최적의 실행 계획을 자동으로 생성
- **적응형 재계획**: 실패 시 상황을 분석하여 새로운 접근 방식으로 자동 재시도
- **컨텍스트 인식**: 이전 대화와 작업 이력을 고려한 지능적 응답

### 🧩 **확장 가능한 도구 생태계**
- **파일 시스템**: 읽기/쓰기/검색/정리 등 포괄적 파일 관리
- **Notion 통합**: 할일 관리, 프로젝트 추적, 노트 정리
- **macOS 시스템**: Apple MCP를 통한 시스템 레벨 작업 자동화
- **메모리 도구**: 장기 기억 저장 및 의미적 검색
- **모듈형 설계**: 새로운 도구를 플러그인 방식으로 쉽게 추가

### 🧠 **장기 기억 시스템**
- **의미적 검색**: 벡터 임베딩을 활용한 관련성 기반 기억 검색
- **지능형 큐레이션**: 중복 기억 자동 제거 및 품질 관리
- **계층적 검색**: 다단계 필터링으로 정확한 정보 검색
- **자동 보존**: 중요도 기반 기억 보존 정책
- **실시간 메트릭스**: 메모리 성능 모니터링 및 최적화

### 🎯 **다중 인터페이스 지원**
- **CLI**: 개발자를 위한 터미널 기반 인터페이스
- **Discord Bot**: Discord 메시지 기반 상호작용
- **실시간 스트리밍**: 작업 진행 상황을 실시간으로 확인
- **유연한 전환**: 환경변수로 인터페이스 간 즉시 전환

### 🛡️ **신뢰성 및 안전성**
- **무한 루프 방지**: 반복 패턴 감지 및 자동 중단
- **에러 복구**: 실패 원인 분석 및 자동 복구 시도
- **토큰 사용량 추적**: LLM 비용 모니터링 및 최적화
- **상세한 로깅**: 디버깅과 운영을 위한 포괄적 로그 시스템

## 🎮 실제 사용 사례

### 📁 **파일 관리 자동화**
```bash
# 복잡한 파일 정리 작업
assistant> 내 다운로드 폴더에서 PDF 파일들을 날짜별로 정리해줘

# 프로젝트 구조 분석
assistant> 이 프로젝트의 Python 파일들에서 TODO 주석이 있는 부분들을 찾아서 정리해줘
```

### 📋 **Notion 워크스페이스 관리**
```bash
# 할일 관리
assistant> 오늘 완료해야 할 작업들을 Notion에서 가져와서 우선순위 순으로 보여줘

# 프로젝트 진행상황 업데이트
assistant> 이번 주에 완료한 작업들을 Notion 프로젝트 보드에 업데이트해줘
```

### 🧠 **지능형 정보 검색**
```bash
# 장기 기억에서 정보 검색
assistant> 지난 달에 논의했던 API 설계 방향에 대해 다시 알려줘

# 컨텍스트 기반 추천
assistant> 현재 작업 중인 프로젝트와 관련된 이전 경험들을 찾아서 참고할 만한 내용 보여줘
```

### 🖥️ **macOS 시스템 통합**
```bash
# 시스템 정보 및 관리
assistant> 현재 실행 중인 애플리케이션들의 CPU 사용량을 확인하고 정리해줘

# 파일 시스템 작업
assistant> 데스크톱의 스크린샷 파일들을 월별 폴더로 정리해줘

```

## 시작하기
1. 가상환경을 생성하고 `requirements.txt`를 설치하세요.
   ```bash
   python -m pip install -r requirements.txt
   ```

2. `.env.example`을 참고하여 `.env` 파일을 준비하세요. 필수 항목:
   - `DEFAULT_INTERFACE=cli` (또는 `discord`)
   - `GEMINI_API_KEY=your_api_key_here` (필수)
   - `GEMINI_MODEL=gemini-1.5-pro` (기본값)
   - `DISCORD_BOT_TOKEN=your_token_here` (Discord 사용 시)

3. `main.py`를 실행하면 설정한 기본 인터페이스가 구동됩니다.
   ```bash
   python main.py
   ```

자세한 사용법은 `docs/USAGE.md`에서 확인할 수 있습니다.
작업 계획과 진행 상황은 `PLAN_for_AI_Agent.md`에서 확인할 수 있습니다.
메모리 유지보수와 관찰 지침은 `docs/memory_maintenance.md`에서 확인할 수 있습니다.
