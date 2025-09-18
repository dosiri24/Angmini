# Personal AI Assistant

Personal AI Assistant 프로젝트는 다양한 인터페이스(CLI, Discord)를 통해 사용자의 작업을 도와주는 에이전트를 구축하는 것을 목표로 합니다. 시스템은 `PLAN_for_AI_Agent.md`의 로드맵을 따르며 단계적으로 기능을 확장합니다.

## 프로젝트 목표
- 환경 변수 기반 설정으로 인터페이스를 유연하게 전환
- Google Gemini 기반 LLM과 MCP 도구 생태계를 활용한 ReAct 엔진 구축
- 확장 가능한 도구(파일, Notion, 웹 등) 통합
- 단계별 테스트와 문서화를 통해 안정성 확보

## 현재 진행 상태
- Phase 1.1~1.3: 기본 구조 및 인터페이스 토대 구축 완료

## 기본 폴더 구조
```
ai/
  core/           # 핵심 설정, 로깅, 예외 처리 모듈 예정
  react_engine/   # Goal/Step Executor 등 ReAct 로직 예정
mcp/
  tools/          # FileTool 등 MCP 도구 구현 예정
  tool_manager.py # 도구 등록 및 실행 관리 예정
 tests/
 data/
 docs/
```

## 시작하기
1. 가상환경을 생성하고 `requirements.txt`를 설치하세요.
2. `.env.example`을 참고하여 `.env` 파일을 준비하세요. 필수 항목은 `DEFAULT_INTERFACE`, `DISCORD_BOT_TOKEN`(Discord 사용 시), `GEMINI_API_KEY`, `GEMINI_MODEL`입니다.
3. `main.py`를 실행하면 설정한 기본 인터페이스가 구동됩니다.

자세한 향후 일정과 작업 범위는 `PLAN_for_AI_Agent.md`에서 확인할 수 있습니다.
