"""
MCP Tool for Image Analysis using Gemini Multimodal API.

이미지 분석 도구:
- Gemini API의 멀티모달 기능을 사용하여 이미지 분석
- 지원 포맷: JPG, JPEG, PNG, GIF, BMP, WEBP
- CrewAI BaseTool 패턴 준수
"""
from typing import Type, Dict, Any, Optional
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from crewai.tools import BaseTool

from ai.core.logger import get_logger
from ai.core.config import Config


class ImageAnalysisInput(BaseModel):
    """ImageAnalysisTool 입력 스키마"""

    filepath: str = Field(
        ...,
        description="분석할 이미지 파일의 절대 경로"
    )
    prompt: str = Field(
        default="이 이미지에 대해 상세히 설명해주세요.",
        description="이미지 분석을 위한 프롬프트 (선택 사항)"
    )


class ImageAnalysisCrewAITool(BaseTool):
    """Gemini 멀티모달 API를 사용한 이미지 분석 CrewAI 도구"""

    name: str = "image_analysis"
    description: str = """
    이미지 파일을 분석하여 내용을 설명하거나 질문에 답변합니다.

    사용 예시:
    - filepath: "/path/to/image.jpg"
    - prompt: "이 사진에서 무엇이 보이나요?"

    지원 포맷: JPG, JPEG, PNG, GIF, BMP, WEBP
    """
    args_schema: Type[BaseModel] = ImageAnalysisInput

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def model_post_init(self, __context):
        """Pydantic v2 post-initialization hook for logger/config setup"""
        super().model_post_init(__context)

        # Pydantic 검증 우회하여 속성 할당 (object.__setattr__ 사용)
        object.__setattr__(self, 'logger', get_logger(__name__))
        object.__setattr__(self, 'config', Config.load())

        # Gemini API 초기화 검증
        if not self.config.gemini_api_key:
            self.logger.error("GEMINI_API_KEY not configured")
            raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")

    def _run(
        self,
        filepath: str,
        prompt: str = "이 이미지에 대해 상세히 설명해주세요."
    ) -> str:
        """
        이미지 파일 분석 실행.

        Args:
            filepath: 이미지 파일 경로
            prompt: 분석 프롬프트

        Returns:
            분석 결과 텍스트
        """
        try:
            self.logger.info(f"Starting image analysis: {filepath}")

            # 파일 존재 확인
            file_path = Path(filepath)
            if not file_path.exists():
                error_msg = f"이미지 파일을 찾을 수 없습니다: {filepath}"
                self.logger.error(error_msg)
                return f"❌ {error_msg}"

            # 파일 확장자 확인
            supported_exts = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
            if file_path.suffix.lower() not in supported_exts:
                error_msg = f"지원하지 않는 이미지 포맷: {file_path.suffix}"
                self.logger.error(error_msg)
                return f"❌ {error_msg}"

            # Gemini 멀티모달 API 사용
            result = self._analyze_with_gemini(file_path, prompt)

            self.logger.info(f"Image analysis completed: {len(result)} characters")
            return result

        except Exception as exc:
            error_msg = f"이미지 분석 실패: {exc}"
            self.logger.exception(error_msg)
            return f"❌ {error_msg}"

    def _analyze_with_gemini(self, file_path: Path, prompt: str) -> str:
        """
        Gemini API를 사용하여 이미지 분석.

        Args:
            file_path: 이미지 파일 경로
            prompt: 분석 프롬프트

        Returns:
            분석 결과 텍스트
        """
        try:
            # google.genai Client API 임포트 (느슨한 의존성)
            try:
                from google import genai
                from google.genai import types
            except ImportError as exc:
                raise ImportError(
                    "google-genai 패키지가 설치되지 않았습니다. "
                    "'pip install google-genai' 후 다시 시도하세요."
                ) from exc

            # Gemini 클라이언트 초기화
            client = genai.Client(api_key=self.config.gemini_api_key)

            # 이미지 로드 (PIL Image 사용)
            try:
                from PIL import Image
            except ImportError as exc:
                raise ImportError(
                    "Pillow 패키지가 설치되지 않았습니다. "
                    "'pip install Pillow' 후 다시 시도하세요."
                ) from exc

            # 파일 크기 제한 확인 (Fix #6)
            MAX_FILE_SIZE_MB = 20
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            if file_size_mb > MAX_FILE_SIZE_MB:
                raise ValueError(
                    f"이미지 파일이 너무 큽니다: {file_size_mb:.1f}MB (최대: {MAX_FILE_SIZE_MB}MB)"
                )

            # PIL 픽셀 제한 설정 (Fix #5)
            # Gemini API는 명시적 픽셀 제한이 없지만, PIL 디컴프레션 폭탄 방지
            # 기본값 128MP 대신 보수적으로 89MP 사용 (~9,500 x 9,500 픽셀)
            Image.MAX_IMAGE_PIXELS = 89_478_485

            # 이미지 로드 (context manager 사용, Fix #11)
            with Image.open(file_path) as img:
                # 이미지 데이터를 메모리에 로드 (파일 핸들 닫기 전)
                image = img.copy()

            # 모델 선택 (멀티모달 지원 모델)
            model_name = self.config.gemini_model
            if model_name.startswith("models/"):
                model_name = model_name.replace("models/", "")

            # Gemini API로 이미지 분석 (직접 Image 객체 전달)
            self.logger.debug(f"Calling Gemini API with model: {model_name}")

            response = client.models.generate_content(
                model=model_name,
                contents=[image, prompt],
            )

            # 응답 텍스트 추출
            if response and response.text:
                result_text = response.text.strip()
                self.logger.debug(f"Gemini response: {len(result_text)} characters")
                return result_text
            else:
                self.logger.warning("Gemini returned empty response")
                return "⚠️ Gemini API가 빈 응답을 반환했습니다."

        except Exception as exc:
            error_msg = f"Gemini API 호출 실패: {exc}"
            self.logger.exception(error_msg)
            raise RuntimeError(error_msg) from exc
