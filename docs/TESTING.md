# Angmini 테스트 가이드

AI가 Angmini 프로젝트를 직접 테스트할 수 있도록 돕는 가이드입니다.

## Claude Code에서 테스트하기

### 1. 도움말 확인
```bash
bin/angmini --help
```

### 2. 버전 확인
```bash
bin/angmini --version
```

### 3. 단일 명령 실행 (빠른 테스트)
```bash
# 스트리밍 없이 빠른 응답
bin/angmini --no-stream "안녕"

# 파일 관련 테스트
bin/angmini --no-stream "현재 디렉토리에 어떤 파일이 있어?"

# 간단한 질문
bin/angmini --no-stream "오늘 날짜 알려줘"
```

### 4. 디버그 모드 (상세 로그)
```bash
# CrewAI의 전체 실행 과정 확인
bin/angmini --debug "테스트"
```

### 5. 대화형 모드
```bash
# 대화형 REPL 시작 (exit로 종료)
bin/angmini
```

## 빠른 기능 검증

### FileAgent 테스트
```bash
bin/angmini --no-stream "현재 디렉토리의 Python 파일 목록 보여줘"
```

### MemoryAgent 테스트
```bash
bin/angmini --no-stream "최근에 뭐 작업했어?"
```

### SystemAgent 테스트 (macOS만)
```bash
bin/angmini --no-stream "Mac의 Notes 앱에 있는 노트 목록 보여줘"
```

### NotionAgent 테스트 (Notion API 키 필요)
```bash
bin/angmini --no-stream "Notion에서 오늘 할 일 목록 가져와줘"
```

## 환경변수 설정 확인

테스트 전 `.env` 파일 확인:
```bash
# 필수
GEMINI_API_KEY=your_api_key_here
DEFAULT_INTERFACE=cli

# 선택
LOG_LEVEL=INFO
STREAM_DELAY=0.01
```

## 로그 확인

실행 로그는 다음 위치에 저장됩니다:
```bash
# 세션별 로그
ls -lt logs/

# 최신 로그 확인
tail -f logs/$(ls -t logs/ | head -1)

# 메모리 임베딩 로그
tail -f memory_embedding.log
```

## 에러 처리 테스트

### 잘못된 명령
```bash
bin/angmini --no-stream "존재하지 않는 파일 삭제해줘"
# 에러 메시지가 명확하게 출력되어야 함
```

### API 키 없이 실행
```bash
# .env에서 GEMINI_API_KEY 제거 후
bin/angmini --version
# 버전은 표시되지만, 명령 실행 시 API 키 오류 발생
```

## 성능 테스트

### 스트리밍 효과 비교
```bash
# 스트리밍 O (기본)
time bin/angmini "안녕"

# 스트리밍 X
time bin/angmini --no-stream "안녕"
```

### 디버그 모드 오버헤드
```bash
# 일반 모드
time bin/angmini --no-stream "간단한 질문"

# 디버그 모드
time bin/angmini --debug --no-stream "간단한 질문"
```

## 통합 테스트 시나리오

### 1. 파일 작업 플로우
```bash
# 1. 파일 생성
bin/angmini --no-stream "test.txt 파일을 만들고 'Hello World' 내용 써줘"

# 2. 파일 읽기
bin/angmini --no-stream "test.txt 파일 내용 보여줘"

# 3. 파일 삭제
bin/angmini --no-stream "test.txt 파일 삭제해줘"
```

### 2. 메모리 시스템 테스트
```bash
# 1. 작업 수행
bin/angmini --no-stream "Python으로 간단한 계산기 만드는 방법 알려줘"

# 2. 메모리 검색
bin/angmini --no-stream "아까 계산기 관련해서 뭐 물어봤었지?"
```

### 3. 다중 에이전트 협업 테스트
```bash
# PlannerAgent가 적절한 워커에게 위임하는지 확인
bin/angmini --no-stream "현재 디렉토리 파일 목록 보여주고, Notion에 TODO로 추가해줘"
```

## CI/CD 자동화 테스트

### 기본 smoke test
```bash
#!/bin/bash
set -e

echo "1. 버전 확인..."
bin/angmini --version

echo "2. 도움말 확인..."
bin/angmini --help > /dev/null

echo "3. 간단한 명령 실행..."
bin/angmini --no-stream "테스트" > /dev/null

echo "✅ 모든 테스트 통과!"
```

### pytest 실행 (선택사항)
```bash
# pytest가 requirements.txt에 있음
pytest tests/ -v
pytest tests/test_file_tool.py
```

## 문제 해결

### 명령어를 찾을 수 없음
```bash
# 스크립트 위치 확인
ls -la bin/angmini

# 실행 권한 확인
chmod +x bin/angmini

# 직접 경로로 실행
./bin/angmini --version
```

### 가상환경 문제
```bash
# 가상환경 확인
echo $VIRTUAL_ENV

# 가상환경 재생성
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Apple MCP 서버 오류 (macOS)
```bash
# TypeScript 서버 상태 확인
cd external/apple-mcp
npm install
npm test

# 서버 수동 시작
npm start
```
