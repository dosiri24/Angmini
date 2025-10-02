# Angmini CLI 설치 가이드

Angmini를 터미널에서 `angmini` 명령어로 바로 실행할 수 있도록 설정하는 방법입니다.

## 빠른 설정 (권장)

프로젝트의 `bin/angmini` 스크립트를 PATH에 추가하세요:

### macOS / Linux

```bash
# 1. bin/angmini에 실행 권한 부여 (이미 되어 있음)
chmod +x bin/angmini

# 2. 심볼릭 링크 생성 (선택 1 - 사용자 bin)
ln -s $(pwd)/bin/angmini ~/.local/bin/angmini

# 또는 PATH 직접 추가 (선택 2 - ~/.bashrc 또는 ~/.zshrc)
echo 'export PATH="$PATH:'$(pwd)'/bin"' >> ~/.zshrc
source ~/.zshrc
```

### 테스트
```bash
angmini --version  # Angmini 2.0.0 (CrewAI) 출력
```

## 대안: Python 패키지 설치

프로젝트 루트 디렉토리에서:

```bash
# 가상환경 활성화
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate    # Windows

# 패키지 설치 (현재 editable install 이슈 있음, 위 방법 권장)
pip install -e .
```

## 사용법

### 1. 대화형 모드 (기본)
```bash
angmini
```

기존처럼 대화형 REPL이 시작됩니다.

### 2. 단일 명령 실행
```bash
angmini "파일 목록 보여줘"
```

명령을 실행하고 바로 종료됩니다. AI 테스트에 유용합니다.

### 3. 디버그 모드
```bash
angmini --debug "테스트"
```

CrewAI의 상세한 실행 과정을 볼 수 있습니다.

### 4. 빠른 응답 (스트리밍 없이)
```bash
angmini --no-stream "빠른 질문"
```

스트리밍 효과 없이 즉시 결과를 출력합니다.

### 5. 인터페이스 선택
```bash
angmini --interface discord  # Discord 봇 실행
angmini --interface cli       # CLI 실행 (기본값)
```

### 6. 도움말
```bash
angmini --help
```

모든 옵션과 사용 예시를 확인할 수 있습니다.

### 7. 버전 확인
```bash
angmini --version
```

## 예시

```bash
# 간단한 질문
angmini "오늘 날짜 알려줘"

# 파일 작업
angmini "현재 디렉토리의 Python 파일 목록을 보여줘"

# Notion 작업
angmini "Notion에서 오늘 할 일 목록 가져와줘"

# 디버그 모드로 문제 확인
angmini --debug "메모리 검색: 지난주에 작업한 내용"

# 빠른 테스트 (스트리밍 없이)
angmini --no-stream "안녕"
```

## 제거

설치를 제거하려면:

```bash
pip uninstall angmini
```

## 개발 모드

코드를 수정하면서 테스트하려면 editable 모드(`-e`)로 설치하는 것을 권장합니다:

```bash
pip install -e .
```

이렇게 하면 코드 변경사항이 즉시 반영되어 재설치 없이 테스트할 수 있습니다.

## 문제 해결

### 명령어를 찾을 수 없음
```
angmini: command not found
```

이 경우 다음을 확인하세요:

1. 가상환경이 활성화되어 있는지 확인
   ```bash
   which python  # 가상환경 경로가 나와야 함
   ```

2. 설치가 제대로 되었는지 확인
   ```bash
   pip show angmini
   ```

3. PATH에 스크립트 경로가 포함되어 있는지 확인
   ```bash
   echo $PATH
   ```

### 환경변수 설정
`.env` 파일이 프로젝트 루트에 있어야 합니다:

```
GEMINI_API_KEY=your_api_key_here
DEFAULT_INTERFACE=cli
```

자세한 설정은 `.env.example`을 참고하세요.
