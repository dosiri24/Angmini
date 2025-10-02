# ✅ CLI 커맨드 설정 완료

Angmini를 터미널에서 `angmini` 명령어로 직접 실행할 수 있게 되었습니다!

## 🎯 완료된 작업

### 1. CLI 인터페이스 개선
- **단일 명령 실행 모드** 추가: `angmini "명령어"` 형태로 바로 실행 가능
- **커맨드라인 인자 파싱**: argparse로 다양한 옵션 지원
- **비대화형 모드**: AI가 자동으로 테스트할 수 있는 환경 구축

### 2. 실행 스크립트 생성
- **`bin/angmini`**: Bash wrapper 스크립트 생성
- **자동 가상환경 활성화**: 스크립트가 알아서 `.venv` 활성화
- **프로젝트 경로 독립성**: 어디서든 실행 가능

### 3. 문서화
- **`INSTALL.md`**: 설치 및 설정 가이드
- **`TESTING.md`**: 포괄적인 테스트 시나리오
- **`CLAUDE.md`**: AI 테스트 섹션 추가

## 🚀 사용 방법

### 즉시 사용 (PATH 설정 없이)
```bash
# 프로젝트 디렉토리에서
bin/angmini --help
bin/angmini --version
bin/angmini --no-stream "안녕"
```

### PATH 설정 후 전역 사용
```bash
# 심볼릭 링크 생성
ln -s $(pwd)/bin/angmini ~/.local/bin/angmini

# 또는 PATH 추가
echo 'export PATH="$PATH:'$(pwd)'/bin"' >> ~/.zshrc
source ~/.zshrc

# 이제 어디서든 사용 가능
angmini --version
angmini "파일 목록 보여줘"
```

## 📝 주요 명령어

```bash
# 도움말
angmini --help

# 버전 확인
angmini --version

# 단일 명령 실행
angmini "현재 디렉토리 파일 목록"

# 스트리밍 없이 빠른 응답
angmini --no-stream "빠른 질문"

# 디버그 모드 (CrewAI 상세 로그)
angmini --debug "테스트"

# 대화형 모드
angmini
```

## 🤖 AI 테스트 예시

Claude Code나 다른 AI가 직접 테스트할 수 있는 명령어:

```bash
# 1. 기본 기능 확인
bin/angmini --version
bin/angmini --help

# 2. 간단한 실행
bin/angmini --no-stream "안녕"

# 3. FileAgent 테스트
bin/angmini --no-stream "현재 디렉토리의 Python 파일 목록 보여줘"

# 4. 디버그 모드 확인
bin/angmini --debug --no-stream "테스트"
```

## 📁 생성된 파일

```
Angmini/
├── bin/
│   └── angmini              # 실행 스크립트 (새로 생성)
├── main.py                  # argparse 추가 (수정됨)
├── interface/
│   └── cli.py               # run_single_command() 추가 (수정됨)
├── angmini_cli.py           # Entry point wrapper (새로 생성)
├── pyproject.toml           # 패키지 메타데이터 (새로 생성)
├── INSTALL.md               # 설치 가이드 (새로 생성)
├── TESTING.md               # 테스트 가이드 (새로 생성)
└── CLAUDE.md                # AI 테스트 섹션 추가 (수정됨)
```

## 🎨 새로운 기능

### argparse 기반 옵션
- `--interface {cli,discord}`: 인터페이스 선택
- `--debug`: 디버그 모드 활성화
- `--no-stream`: 스트리밍 출력 비활성화
- `--version`: 버전 정보 표시
- `--help`: 도움말 표시

### 실행 모드
1. **대화형 모드**: `angmini` (기본)
2. **단일 명령 모드**: `angmini "명령어"`
3. **디버그 모드**: `angmini --debug "명령어"`

## ⚡ 성능 최적화

- `--no-stream` 옵션으로 응답 속도 향상
- 단일 명령 모드로 API 호출 최소화
- 디버그 모드로 문제 진단 간소화

## 🔧 문제 해결

### "command not found" 오류
```bash
chmod +x bin/angmini
./bin/angmini --version
```

### 가상환경 문제
```bash
source .venv/bin/activate
python3 main.py  # 기존 방식으로 실행
```

### API 키 오류
```bash
# .env 파일 확인
cat .env | grep GEMINI_API_KEY
```

## 📚 추가 문서

- **설치**: `INSTALL.md`
- **테스트**: `TESTING.md`
- **개발 가이드**: `CLAUDE.md`
- **프로젝트 계획**: `PLAN_for_AI_Agent.md`

## 🎉 요약

이제 Angmini를 다음과 같이 사용할 수 있습니다:

1. ✅ **터미널 어디서든**: `angmini` 명령어로 실행
2. ✅ **AI가 자동 테스트**: `--no-stream` 옵션으로 비대화형 실행
3. ✅ **빠른 디버깅**: `--debug` 모드로 상세 로그 확인
4. ✅ **유연한 옵션**: 다양한 커맨드라인 인자 지원

---

**개발 속도가 훨씬 빠르겠네요! 🚀**

이제 Claude Code 같은 AI가 직접 `bin/angmini --no-stream "명령어"` 형태로 테스트하고 검증할 수 있습니다.
