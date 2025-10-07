# Angmini 멀티모달 업그레이드 계획서

## 개요

Discord 인터페이스를 통해 이미지/문서/PDF 파일을 수신하고, 전문 분석 에이전트가 파일 타입별로 분석하는 멀티모달 시스템 구축.

**핵심 원칙**: 기존 Angmini 아키텍처 패턴을 최대한 활용하여 확장성과 일관성을 유지.

---

## 기존 시스템 분석

### 현재 아키텍처 패턴

**에이전트 패턴** (`ai/agents/`)
- `BaseAngminiAgent` 추상 클래스 상속
- `role()`, `goal()`, `backstory()`, `tools()` 메서드 구현
- 마크다운 프롬프트 파일 지원 (`ai/agents/prompts/*.md`)
- `AgentFactory`를 통한 중앙 집중식 생성

**MCP 도구 패턴** (`mcp/tools/`)
- CrewAI `BaseTool` 직접 상속 (FileTool 참고)
- Pydantic `BaseModel`로 입력 스키마 정의
- `name`, `description`, `args_schema` 속성
- `_run()` 메서드에서 실제 로직 구현

**작업 흐름** (`ai/crew/`)
- `TaskFactory`: 사용자 입력 → CrewAI Task 변환
- `AngminiCrew`: 에이전트 orchestration 및 실행
- Hierarchical 모드: PlannerAgent가 워커 에이전트에게 위임

**Discord 인터페이스** (`interface/discord_bot.py`)
- `on_message()` 이벤트에서 메시지 수신
- `asyncio.to_thread()`로 동기 CrewAI 실행
- `message.attachments`로 첨부 파일 접근 가능

---

## 아키텍처 설계

### 전체 흐름도

```
사용자 (Discord)
    ↓ 파일 첨부 + 메시지
Discord Bot (interface/discord_bot.py)
    ↓ 타임스탬프 기반 임시 저장 (data/temp/attachments/)
    ↓ 파일 메타데이터 생성
    ↓ 10초 대기 (후속 메시지 수신)
TaskFactory (ai/crew/task_factory.py)
    ↓ 파일 메타데이터를 Task description에 포함
PlannerAgent (Manager)
    ↓ LLM이 파일명/타입 인식 → AnalyzerAgent 위임
AnalyzerAgent (Worker)
    ↓ 파일 타입별 도구 선택
    ├─ ImageAnalysisTool (google.genai)
    ├─ DocumentAnalysisTool (python-docx)
    └─ PDFAnalysisTool (pdfplumber)
    ↓ 분석 결과 반환
PlannerAgent ← 결과 취합
    ↓ 최종 응답 생성
사용자 (Discord) ← 자연어 응답
```

---

## 1단계: Discord 인터페이스 확장

### 구현 위치
`interface/discord_bot.py`

### 기존 패턴 활용
- **on_message 이벤트**: 기존 메시지 처리 로직 확장
- **asyncio.to_thread**: 기존과 동일하게 동기 CrewAI 실행
- **message.attachments**: Discord.py API로 첨부 파일 접근

### 기능 요구사항

#### 1.1 파일 첨부 감지 및 다운로드
- `on_message()` 이벤트에서 `message.attachments` 체크
- 지원 파일 형식:
  - **이미지**: `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`
  - **문서**: `.txt`, `.md`, `.docx`
  - **PDF**: `.pdf`

#### 1.2 타임스탬프 기반 파일명 변경 및 저장
- 저장 경로: `data/temp/attachments/`
- 파일명 형식: `{YYYYMMDD_HHMMSS}_{원본확장자}` (예: `20250106_143022.png`)
- 메타데이터 구조:
  ```python
  {
      "original_name": str,  # 원본 파일명
      "saved_path": str,     # 절대 경로
      "file_type": str,      # "image" | "document" | "pdf"
      "uploaded_at": str     # ISO 8601 형식
  }
  ```

#### 1.3 대기 로직
- 파일 수신 후 **10초 대기** (`asyncio.wait_for` 활용)
- 대기 중 사용자 메시지 수신 시 즉시 처리 시작
- 타임아웃 시 안내 메시지 전송

#### 1.4 Crew로 데이터 전달
- 기존: `crew.kickoff(content: str)`
- 변경: `crew.kickoff(user_input: Union[str, dict])`
- 딕셔너리 형태: `{"user_message": str, "attachments": List[dict]}`

### 구현 방향
1. `_save_attachments()` 헬퍼 메서드: 파일 다운로드 및 메타데이터 생성
2. `_wait_for_follow_up()` 헬퍼 메서드: 10초 대기 로직
3. 기존 `crew.kickoff()` 호출부 수정: 문자열 → Union 타입 지원

---

## 2단계: TaskFactory 확장

### 구현 위치
`ai/crew/task_factory.py`

### 기존 패턴 활용
- **create_tasks_from_input**: 현재 문자열 입력 → 향후 Union 타입 지원
- **LLM 기반 의도 분류**: 기존 `_classify_intent()` 패턴 유지
- **메모리 검색**: 기존 로직 그대로 유지

### 기능 요구사항

#### 2.1 입력 형식 확장
- 현재: `user_input: str`
- 변경: `user_input: Union[str, dict]`
- 딕셔너리 처리: 파일 정보 추출 → Task description에 포함

#### 2.2 파일 정보 자연어 변환
- 파일명 리스트를 텍스트로 변환
- PlannerAgent의 LLM이 파일 타입 인식하도록 명시적 표현
- 예: "첨부 파일: image.png (이미지), document.docx (문서), report.pdf (PDF)"

### 구현 방향
1. `create_tasks_from_input()` 시그니처 변경
2. 파일 메타데이터를 자연어 형태로 description에 통합
3. 기존 메모리 검색 및 의도 분류 로직은 유지

---

## 3단계: AnalyzerAgent 및 MCP 도구 구현

### 3.1 AnalyzerAgent 생성

#### 구현 위치
`ai/agents/analyzer_agent.py`

#### 기존 패턴 활용
- **BaseAngminiAgent 상속**: FileAgent, NotionAgent와 동일한 패턴
- **마크다운 프롬프트**: `ai/agents/prompts/analyzer_agent_prompt.md` 생성
- **AgentFactory 등록**: `ai/agents/__init__.py` 수정

#### 프롬프트 구조 (analyzer_agent_prompt.md)
```markdown
## Role
파일 분석 전문가

## Goal
이미지, 문서, PDF 파일을 분석하여 사용자에게 유용한 정보를 제공합니다.

## Backstory
당신은 다양한 파일 형식을 분석하는 전문가입니다.
이미지는 Gemini Vision API로, 문서는 텍스트 추출 라이브러리로, PDF는 구조 분석 도구로 처리합니다.
파일 경로를 받으면 적절한 도구를 선택하여 분석하고 결과를 명확하게 전달합니다.
```

#### 도구 등록
```python
def tools(self) -> list:
    return [
        ImageAnalysisCrewAITool(),
        DocumentAnalysisCrewAITool(),
        PDFAnalysisCrewAITool()
    ]
```

---

### 3.2 MCP 도구 구현

#### 기존 패턴 참고: FileTool
- CrewAI `BaseTool` 직접 상속
- Pydantic `BaseModel`로 입력 스키마 정의 (`FileToolInput`)
- `args_schema`, `name`, `description` 속성
- `_run()` 메서드에서 실제 로직 구현

---

#### 3.2.1 ImageAnalysisTool

**구현 위치**: `mcp/tools/image_analysis_tool.py`

**기술 스택** (Context7 조사 결과)
- `google.genai.Client`: Gemini API 클라이언트
- `PIL.Image.open()`: 이미지 로드
- `client.models.generate_content()`: 멀티모달 분석

**주요 API 패턴** (googleapis/python-genai):
- **작은 이미지 직접 전달**: `contents=[Image.open(path), "prompt"]`
- **큰 파일 업로드 후 참조**: `client.files.upload(file=path)` → `contents=[file_ref, "prompt"]`
- **바이트 데이터 전달**: `types.Part.from_bytes(data=bytes, mime_type="image/jpeg")`

**구현 방향**:
1. Pydantic 스키마 정의: `ImageAnalysisToolInput(BaseModel)`
2. `ImageAnalysisCrewAITool(BaseTool)` 클래스 생성
3. 작은 이미지(<10MB)는 PIL Image 직접 전달, 큰 이미지는 file upload
4. 에러 처리: API 오류, 파일 없음, 잘못된 형식

---

#### 3.2.2 DocumentAnalysisTool

**구현 위치**: `mcp/tools/document_analysis_tool.py`

**기술 스택** (Context7 조사 결과)
- `docx.Document()`: .docx 파일 로드
- `document.paragraphs`: 문단 리스트 접근
- `paragraph.text`: 각 문단의 텍스트 추출

**주요 API 패턴** (python-openxml/python-docx):
- `.txt/.md`: `open(path).read()`
- `.docx`: `Document(path)` → `"\n".join([p.text for p in doc.paragraphs])`

**구현 방향**:
1. Pydantic 스키마 정의: `DocumentAnalysisToolInput(BaseModel)`
2. `DocumentAnalysisCrewAITool(BaseTool)` 클래스 생성
3. 파일 확장자별 분기 처리 (txt/md/docx)
4. 전체 텍스트 결합 후 반환

---

#### 3.2.3 PDFAnalysisTool

**구현 위치**: `mcp/tools/pdf_analysis_tool.py`

**기술 스택** (Context7 조사 결과)
- `pdfplumber.open(path)`: PDF 파일 로드
- `pdf.pages`: 페이지 리스트 접근
- `page.extract_text()`: 텍스트 추출
- `page.extract_table()` / `page.extract_tables()`: 테이블 추출

**주요 API 패턴** (jsvine/pdfplumber):
- 기본 텍스트: `with pdfplumber.open(path) as pdf: "".join([p.extract_text() for p in pdf.pages])`
- 테이블: `page.extract_tables()` 또는 `page.extract_table(table_settings)`
- 디버깅: `page.to_image()`, `im.debug_tablefinder()`

**구현 방향**:
1. Pydantic 스키마 정의: `PDFAnalysisToolInput(BaseModel)`
2. `PDFAnalysisCrewAITool(BaseTool)` 클래스 생성
3. 전체 페이지 순회하며 텍스트 추출
4. 테이블 추출은 선택적 기능 (`extract_tables` 파라미터)
5. 반환 형식: `{"text": str, "tables": List[List] | None}`

---

### 3.3 도구 등록

#### 구현 위치
`mcp/tools/__init__.py`

#### 변경 사항
기존:
```python
__all__ = ["AppleTool", "FileTool", "MemoryTool", "NotionTool"]
```

추가:
```python
from .image_analysis_tool import ImageAnalysisCrewAITool
from .document_analysis_tool import DocumentAnalysisCrewAITool
from .pdf_analysis_tool import PDFAnalysisCrewAITool

__all__ = [
    "AppleTool", "FileTool", "MemoryTool", "NotionTool",
    "ImageAnalysisCrewAITool", "DocumentAnalysisCrewAITool", "PDFAnalysisCrewAITool"
]
```

---

## 4단계: CrewAI 통합

### 4.1 AngminiCrew 수정

**구현 위치**: `ai/crew/crew_config.py`

#### 변경 사항
1. **worker_agents 추가**: `AnalyzerAgent` 생성 및 등록
2. **kickoff 시그니처 변경**: `user_input: Union[str, dict]` 지원

#### 기존 패턴 유지
- hierarchical 모드: PlannerAgent가 AnalyzerAgent에게 위임
- 메모리 저장 로직: 기존과 동일
- step_callback: 기존 로깅 패턴 유지

---

### 4.2 AgentFactory 수정

**구현 위치**: `ai/agents/__init__.py`

#### 변경 사항
1. AnalyzerAgent 임포트 추가
2. `create_all_agents()`에 AnalyzerAgent 추가

---

## 5단계: 환경 설정 및 의존성

### 5.1 환경 변수 (.env)

**필수**:
- `GEMINI_API_KEY`: 기존 사용 중 (Gemini 멀티모달 API 키)

**선택**:
- `TEMP_ATTACHMENTS_DIR`: 임시 파일 저장 경로 (기본값: `data/temp/attachments`)

### 5.2 의존성 추가 (requirements.txt)

```
# 멀티모달 분석 (신규)
google-genai>=0.3.0
Pillow>=10.0.0

# 문서 분석 (신규)
python-docx>=1.1.0

# PDF 분석 (신규)
pdfplumber>=0.10.0
```

---

## 6단계: 테스트 시나리오

### 6.1 이미지 분석
**입력**:
- Discord에 이미지 업로드
- 메시지: "이 이미지 설명해줘"

**예상 출력**:
- Gemini Vision API를 통한 이미지 설명

### 6.2 문서 분석
**입력**:
- `.docx` 파일 업로드
- 메시지: "이 문서 요약해줘"

**예상 출력**:
- 문서 내용 추출 후 요약

### 6.3 PDF 분석
**입력**:
- `.pdf` 파일 업로드
- 메시지: "이 논문의 핵심 주장을 정리해줘"

**예상 출력**:
- PDF 텍스트 추출 후 핵심 내용 요약

### 6.4 복합 파일 분석
**입력**:
- 이미지 + PDF 동시 업로드
- 메시지: "이 자료들을 비교 분석해줘"

**예상 출력**:
- 각 파일 분석 후 통합 비교 리포트

---

## 7단계: 구현 우선순위

1. **Discord 파일 수신 로직** (1단계)
2. **TaskFactory 확장** (2단계)
3. **AnalyzerAgent 및 도구 뼈대 구현** (3단계)
4. **ImageAnalysisTool 구현** (3.2.1) - Gemini API 우선
5. **DocumentAnalysisTool 구현** (3.2.2) - 간단한 텍스트 추출
6. **PDFAnalysisTool 구현** (3.2.3) - 기본 텍스트 추출
7. **CrewAI 통합 및 테스트** (4단계 + 6단계)
8. **고급 기능 추가** (테이블 추출, 이미지 추출 등)

---

## 참고 사항

### Gemini API 멀티모달 활용 (googleapis/python-genai)

**기본 패턴**:
- 클라이언트 초기화: `client = genai.Client(api_key=GEMINI_API_KEY)`
- 이미지 직접 전달: `contents=[Image.open(path), "prompt"]`
- 파일 업로드 후 참조: `file = client.files.upload(file=path)` → `contents=[file, "prompt"]`

**지원 모델**:
- `gemini-2.0-flash-exp`: 최신 멀티모달 모델
- `gemini-2.5-flash`: 빠른 처리용

### python-docx API (python-openxml/python-docx)

**기본 패턴**:
- 문서 로드: `doc = Document(path)`
- 문단 접근: `for para in doc.paragraphs: print(para.text)`
- 전체 텍스트: `"\n".join([p.text for p in doc.paragraphs])`

### pdfplumber API (jsvine/pdfplumber)

**기본 패턴**:
- PDF 로드: `with pdfplumber.open(path) as pdf:`
- 페이지 접근: `for page in pdf.pages:`
- 텍스트 추출: `page.extract_text()`
- 테이블 추출: `page.extract_tables()` 또는 `page.extract_table()`

---

## 디렉토리 구조 (변경 후)

```
Angmini/
├── data/
│   └── temp/
│       └── attachments/        # 파일 임시 저장소 (신규)
│           ├── 20250106_143022.png
│           └── 20250106_143025.pdf
├── interface/
│   └── discord_bot.py          # 파일 수신 로직 추가
├── ai/
│   ├── agents/
│   │   ├── __init__.py         # AnalyzerAgent 등록
│   │   ├── analyzer_agent.py   # 신규: 파일 분석 전문가
│   │   └── prompts/
│   │       └── analyzer_agent_prompt.md  # 신규
│   └── crew/
│       ├── task_factory.py     # Union 타입 지원
│       └── crew_config.py      # AnalyzerAgent 추가
├── mcp/
│   └── tools/
│       ├── __init__.py         # 신규 도구 등록
│       ├── image_analysis_tool.py      # 신규: Gemini Vision
│       ├── document_analysis_tool.py   # 신규: python-docx
│       └── pdf_analysis_tool.py        # 신규: pdfplumber
└── docs/
    └── MULTIMODAL_UPGRADE_PLAN.md  # 본 문서
```

---

## 마일스톤

- [x] 계획서 작성
- [x] 프로젝트 구조 분석
- [x] 최신 기술 문서 조사
- [ ] Discord 파일 수신 구현
- [ ] TaskFactory 확장
- [ ] AnalyzerAgent 생성
- [ ] ImageAnalysisTool 구현
- [ ] DocumentAnalysisTool 구현
- [ ] PDFAnalysisTool 구현
- [ ] CrewAI 통합
- [ ] 테스트 및 검증
- [ ] 문서화 업데이트 (CLAUDE.md)

---

**최종 목표**: 사용자가 Discord에 파일을 업로드하면, Angmini가 파일 타입을 자동 인식하고 적절한 분석 도구를 선택하여 유용한 인사이트를 자연어로 제공하는 시스템 구축.
