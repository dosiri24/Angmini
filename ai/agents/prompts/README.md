# Agent System Prompts

이 폴더는 각 에이전트의 시스템 프롬프트를 마크다운 형태로 관리합니다.

## 파일 구조

- `file_agent_prompt.md` - 파일 시스템 관리 전문 에이전트
- `memory_agent_prompt.md` - 장기 기억 및 경험 관리 전문 에이전트
- `notion_agent_prompt.md` - Notion 워크스페이스 관리 전문 에이전트
- `planner_agent_prompt.md` - 작업 계획 및 조율 총괄 에이전트
- `system_agent_prompt.md` - macOS 시스템 통합 전문 에이전트

## 사용 방법

각 에이전트의 `backstory()` 메서드는 해당하는 마크다운 파일의 내용을 기반으로 합니다.

프롬프트를 수정하려면:
1. 해당 마크다운 파일을 편집
2. 에이전트 코드에서 필요시 파일을 읽어 사용

## 프롬프트 구조

각 프롬프트 파일은 다음 구조를 따릅니다:

```markdown
# [Agent Name] System Prompt

## Role
에이전트의 역할 정의

## Goal
에이전트의 목표

## Backstory
에이전트의 배경 스토리 및 상세 지침

### 주요 책임
- 주요 업무 목록

### 작업 원칙
- 작업 시 준수해야 할 원칙
```

## 주의사항

- 프롬프트 수정 후 에이전트 재시작 필요
- 일관성 있는 형식 유지
- 명확하고 구체적인 지침 작성
