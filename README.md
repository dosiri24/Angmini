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

### 2. **MCP (Model Context Protocol) 도구 시스템**
- **Tool Manager**: 도구 등록 및 실행 라우팅
- **File Tool**: 파일 시스템 조작 (읽기/쓰기/목록)
- **Notion Tool**: Notion API 연동 (할일 관리, 프로젝트 관리)

### 3. **다중 인터페이스 지원**
- **CLI**: 명령줄 인터페이스
- **Discord Bot**: Discord 메시지 기반 상호작용
- 환경변수 기반 인터페이스 전환

## 📁 프로젝트 구조
```
Angmini/
├── main.py                     # 애플리케이션 진입점
├── requirements.txt            # Python 의존성
├── .env.example               # 환경변수 템플릿
├── ai/                        # AI 엔진 핵심
│   ├── ai_brain.py           # Gemini API 연동 클래스
│   ├── core/                 # 핵심 모듈
│   │   ├── config.py         # 환경변수 및 설정 관리
│   │   ├── logger.py         # 로깅 시스템
│   │   └── exceptions.py     # 커스텀 예외 클래스
│   └── react_engine/         # ReAct 패턴 구현체
│       ├── goal_executor.py  # 목표 실행 엔진
│       ├── step_executor.py  # 단계별 실행기
│       ├── planning_engine.py # 재계획/재시도 결정
│       ├── loop_detector.py  # 무한 루프 감지
│       ├── safety_guard.py   # 안전 제한 장치
│       ├── runtime.py        # 실행 팩토리
│       ├── models.py         # 데이터 모델 정의
│       ├── agent_scratchpad.py # 사고 과정 기록
│       ├── conversation_memory.py # 대화 메모리
│       └── prompt_templates/ # LLM 프롬프트 템플릿
│           ├── system_prompt.md
│           ├── react_prompt.md
│           └── final_response_prompt.md
├── mcp/                      # MCP 도구 생태계
│   ├── tool_blueprint.py     # 도구 기본 추상 클래스
│   ├── tool_manager.py       # 도구 등록/실행 관리
│   └── tools/                # 구체적 도구 구현
│       ├── file_tool.py      # 파일 시스템 도구
│       └── notion_tool.py    # Notion API 도구
├── interface/                # 사용자 인터페이스
│   ├── cli.py               # 명령줄 인터페이스
│   ├── discord_bot.py       # Discord 봇 인터페이스
│   └── summary.py           # 실행 결과 요약 포맷터
├── tests/                   # 테스트 코드
│   ├── test_file_tool.py    # 파일 도구 테스트
│   ├── test_notion_tool.py  # Notion 도구 테스트
│   ├── test_react_engine_integration.py # 통합 테스트
│   └── test_smoke.py        # 스모크 테스트
├── scripts/                 # 유틸리티 스크립트
│   └── gemini_quickcheck.py # Gemini API 연결 테스트
├── docs/                    # 프로젝트 문서
│   ├── USAGE.md            # 사용 가이드
│   ├── React_Engine_Design.md # 엔진 설계 문서
│   ├── PLAN_for_Users.md   # 사용자용 계획
│   └── instructions.md     # 개발 지침
└── data/                   # 데이터 저장소
```

## 🚀 현재 진행 상황

### ✅ 완료된 기능 (Phase 1-4.5)
- **기본 구조**: 설정 관리, 로깅, 예외 처리
- **ReAct Engine**: 완전한 계획-실행-검증 루프
- **도구 통합**: File Tool, Notion Tool (관계형 데이터 포함)
- **인터페이스**: CLI와 Discord 봇 완전 연동
- **안전 장치**: 루프 감지, 재시도 제한, 에러 복구

### 🔄 진행 중인 작업 (Phase 5)
- **통합 테스트 확장 및 안정화**
- **배포 자동화 & 운영 가이드 정비**

## 🛠️ 기술 스택
- **언어**: Python 3.11+
- **AI 모델**: Google Gemini (gemini-1.5-pro)
- **주요 라이브러리**: 
  - `google-generativeai`: Gemini API 연동
  - `discord.py`: Discord 봇 기능
  - `notion-client`: Notion API 연동
  - `python-dotenv`: 환경변수 관리

## 💡 주요 특징

### 1. **지능적 계획 수립**
- LLM이 사용자 요청을 분석하여 단계별 계획 생성
- 실패 시 자동 재계획 또는 재시도 결정

### 2. **강력한 에러 복구**
- 실패 로그 추적 및 LLM에 피드백 제공
- 무한 루프 방지 및 안전 제한

### 3. **확장 가능한 도구 시스템**
- MCP 표준 기반 도구 아키텍처
- 새로운 도구 쉽게 추가 가능

### 4. **다중 인터페이스**
- 환경변수로 인터페이스 전환
- CLI와 Discord에서 동일한 기능 제공

### 5. **장기 기억 관찰 및 유지보수**
- `MemoryMetrics`로 저장/조회 성공률과 평균 지연을 실시간으로 집계
- `docs/memory_maintenance.md`에 임베딩 교체·데이터 정리/보호 절차를 문서화
- 최종 응답은 `[chars_total=..., thinking_chars=...]` 형식으로 내부 사고/출력 길이를 함께 제공하여 투명성을 높였습니다

## 🎮 사용 예시
```bash
# CLI에서
assistant> 내 홈 디렉터리 문서 폴더 목록 보여줘

# Discord에서
@bot 내 다운로드 폴더 파일 목록 정리해줘
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
