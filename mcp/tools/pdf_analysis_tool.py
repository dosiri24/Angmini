"""
MCP Tool for PDF Analysis using pdfplumber library.

PDF 분석 도구:
- pdfplumber 라이브러리를 사용하여 PDF 문서 텍스트 및 테이블 추출
- LLM API 미사용 (라이브러리 기반 분석)
- 지원 포맷: PDF
- CrewAI BaseTool 패턴 준수
"""
from typing import Type, List
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from crewai.tools import BaseTool

from ai.core.logger import get_logger


class PDFAnalysisInput(BaseModel):
    """PDFAnalysisTool 입력 스키마"""

    filepath: str = Field(
        ...,
        description="분석할 PDF 파일의 절대 경로"
    )
    extract_tables: bool = Field(
        default=True,
        description="테이블 추출 여부 (기본값: True)"
    )


class PDFAnalysisCrewAITool(BaseTool):
    """pdfplumber를 사용한 PDF 문서 분석 CrewAI 도구"""

    name: str = "pdf_analysis"
    description: str = """
    PDF 파일에서 텍스트와 테이블을 추출하여 내용을 분석합니다.

    사용 예시:
    - filepath: "/path/to/document.pdf"
    - extract_tables: True (테이블 추출 여부)

    지원 포맷: PDF

    주의: 이 도구는 텍스트 및 테이블 추출만 수행합니다. 추출된 내용의 해석이 필요하면
    PlannerAgent에게 위임하세요.
    """
    args_schema: Type[BaseModel] = PDFAnalysisInput

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def model_post_init(self, __context):
        """Pydantic v2 post-initialization hook for logger setup"""
        super().model_post_init(__context)
        object.__setattr__(self, 'logger', get_logger(__name__))

    def _run(self, filepath: str, extract_tables: bool = True) -> str:
        """
        PDF 파일에서 텍스트 및 테이블 추출.

        Args:
            filepath: PDF 파일 경로
            extract_tables: 테이블 추출 여부

        Returns:
            추출된 텍스트, 테이블, 메타데이터
        """
        try:
            self.logger.info(f"Starting PDF analysis: {filepath}")

            # 파일 존재 확인
            file_path = Path(filepath)
            if not file_path.exists():
                error_msg = f"PDF 파일을 찾을 수 없습니다: {filepath}"
                self.logger.error(error_msg)
                return f"❌ {error_msg}"

            # 파일 확장자 확인
            if file_path.suffix.lower() != ".pdf":
                error_msg = f"지원하지 않는 파일 포맷: {file_path.suffix} (PDF만 지원)"
                self.logger.error(error_msg)
                return f"❌ {error_msg}"

            # 파일 크기 제한 확인 (Fix #6)
            MAX_FILE_SIZE_MB = 100
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            if file_size_mb > MAX_FILE_SIZE_MB:
                error_msg = f"PDF 파일이 너무 큽니다: {file_size_mb:.1f}MB (최대: {MAX_FILE_SIZE_MB}MB)"
                self.logger.error(error_msg)
                return f"❌ {error_msg}"

            # pdfplumber로 PDF 분석
            result = self._extract_from_pdf(file_path, extract_tables)

            self.logger.info(f"PDF analysis completed: {len(result)} characters")
            return result

        except Exception as exc:
            error_msg = f"PDF 분석 실패: {exc}"
            self.logger.exception(error_msg)
            return f"❌ {error_msg}"

    def _extract_from_pdf(self, file_path: Path, extract_tables: bool) -> str:
        """
        pdfplumber를 사용하여 PDF 파일에서 텍스트 및 테이블 추출.

        Args:
            file_path: PDF 파일 경로
            extract_tables: 테이블 추출 여부

        Returns:
            추출된 텍스트 및 테이블 (포맷팅된 문자열)
        """
        try:
            # pdfplumber 임포트 (느슨한 의존성)
            try:
                import pdfplumber
            except ImportError as exc:
                raise ImportError(
                    "pdfplumber 패키지가 설치되지 않았습니다. "
                    "'pip install pdfplumber' 후 다시 시도하세요."
                ) from exc

            # PDF 열기
            self.logger.debug(f"Opening PDF: {file_path}")

            result_lines = ["📄 PDF 문서 분석 결과\n"]

            with pdfplumber.open(file_path) as pdf:
                # 메타데이터
                metadata = pdf.metadata or {}
                num_pages = len(pdf.pages)

                result_lines.append("### 📋 문서 정보")
                result_lines.append(f"- 페이지 수: {num_pages}개")
                result_lines.append(f"- 제목: {metadata.get('Title', '(제목 없음)')}")
                result_lines.append(f"- 작성자: {metadata.get('Author', '(작성자 미상)')}")
                result_lines.append(f"- 생성일: {metadata.get('CreationDate', '(날짜 미상)')}")
                result_lines.append(f"- 파일 크기: {file_path.stat().st_size / 1024:.1f} KB")

                # 텍스트 추출 (페이지별)
                result_lines.append("\n### 📝 문서 내용")

                total_text_chars = 0
                total_tables = 0

                for page_num, page in enumerate(pdf.pages, 1):
                    # 페이지 텍스트 추출
                    text = page.extract_text()

                    if text and text.strip():
                        # 너무 긴 텍스트는 요약 (페이지당 1000자 제한)
                        text_preview = text.strip()
                        if len(text_preview) > 1000:
                            text_preview = text_preview[:1000] + "... (이하 생략)"

                        result_lines.append(f"\n[페이지 {page_num}]")
                        result_lines.append(text_preview)
                        total_text_chars += len(text)

                    # 테이블 추출 (옵션)
                    if extract_tables:
                        tables = page.extract_tables()
                        if tables:
                            result_lines.append(f"\n📊 페이지 {page_num}에서 {len(tables)}개의 테이블 발견:")
                            for table_idx, table in enumerate(tables, 1):
                                result_lines.append(f"\n[테이블 {table_idx}]")
                                # 테이블을 마크다운 형식으로 변환
                                if table and len(table) > 0:
                                    # 헤더
                                    if table[0]:
                                        header = " | ".join(str(cell or "") for cell in table[0])
                                        result_lines.append(header)
                                        result_lines.append("-" * len(header))

                                    # 데이터 행 (최대 5행)
                                    for row in table[1:6]:
                                        if row:
                                            row_text = " | ".join(str(cell or "") for cell in row)
                                            result_lines.append(row_text)

                                    if len(table) > 6:
                                        result_lines.append(f"... (총 {len(table)}행, 일부만 표시)")

                                total_tables += 1

                # 통계 정보
                result_lines.append(f"\n### 📊 통계")
                result_lines.append(f"- 총 페이지 수: {num_pages}개")
                result_lines.append(f"- 총 텍스트 문자 수: {total_text_chars:,}자")
                if extract_tables:
                    result_lines.append(f"- 총 테이블 수: {total_tables}개")

            result_text = "\n".join(result_lines)
            self.logger.debug(f"Extracted from {num_pages} pages, {total_text_chars} characters, {total_tables} tables")

            return result_text

        except Exception as exc:
            error_msg = f"PDF 텍스트 추출 실패: {exc}"
            self.logger.exception(error_msg)
            raise RuntimeError(error_msg) from exc
