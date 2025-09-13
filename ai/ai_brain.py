"""
AI Brain 모듈: Google Gemini API와 연동하여 LLM 기능을 제공합니다.

이 모듈은 Personal AI Assistant의 핵심 추론 엔진입니다.
"""

from typing import Optional, Dict, Any, List
from ai.core.config import config
from ai.core.logger import logger
from ai.core.exceptions import EngineError

# Google Generative AI import with error handling
try:
    import google.generativeai as genai  # type: ignore
except ImportError as e:
    logger.error(f"Google Generative AI 라이브러리 import 실패: {e}")
    raise EngineError(f"Required library not found: {e}")


class AIBrain:
    """
    Google Gemini API와 연동하는 AI 추론 엔진입니다.
    
    이 클래스는 다음과 같은 책임을 가집니다:
    - Gemini API 연결 및 인증 관리
    - 프롬프트 기반 텍스트 생성
    - ReAct 패턴에 특화된 응답 생성
    - 토큰 사용량 모니터링 (향후 구현)
    """
    
    def __init__(self, model_name: str = "gemini-1.5-flash"):
        """
        AIBrain 인스턴스를 초기화합니다.
        
        Args:
            model_name (str): 사용할 Gemini 모델명 (기본값: "gemini-1.5-flash")
            
        Raises:
            EngineError: API 키가 없거나 모델 초기화에 실패한 경우
        """
        try:
            # Rule 2: Explicit Failure Handling
            # API 키가 설정되지 않았거나 잘못된 경우, 명시적으로 에러를 발생시켜
            # 사용자가 즉시 문제를 인지하고 해결할 수 있도록 합니다.
            genai.configure(api_key=config.google_api_key)  # type: ignore
            self.model = genai.GenerativeModel(model_name)  # type: ignore
            self.model_name = model_name
            
            logger.info(f"AIBrain 초기화 완료 - 모델: {model_name}")
            
        except Exception as e:
            logger.error(f"AIBrain 초기화 실패: {str(e)}")
            raise EngineError(f"Gemini API 초기화에 실패했습니다: {str(e)}")
    
    def generate_response(self, prompt: str, 
                         system_instruction: Optional[str] = None,
                         temperature: float = 0.7,
                         max_tokens: Optional[int] = None) -> str:
        """
        주어진 프롬프트에 대한 AI 응답을 생성합니다.
        
        Args:
            prompt (str): 사용자 입력 또는 시스템이 생성한 프롬프트
            system_instruction (Optional[str]): 시스템 지시사항 (역할 정의 등)
            temperature (float): 창의성 수준 (0.0~1.0, 기본값: 0.7)
            max_tokens (Optional[int]): 최대 토큰 수 제한
            
        Returns:
            str: AI가 생성한 응답 텍스트
            
        Raises:
            EngineError: API 호출 실패 또는 응답 생성 오류 시
        """
        try:
            # Rule 4: Clear and Detailed Comments
            # system_instruction이 있는 경우, 프롬프트 앞에 추가하여
            # AI가 특정 역할이나 지침을 따르도록 유도합니다.
            full_prompt = prompt
            if system_instruction:
                full_prompt = f"{system_instruction}\n\n{prompt}"
            
            logger.debug(f"AI 응답 생성 요청 - 프롬프트 길이: {len(full_prompt)} 문자")
            
            # Gemini API 호출
            response = self.model.generate_content(
                full_prompt,
                generation_config=genai.GenerationConfig(  # type: ignore
                    temperature=temperature,
                    max_output_tokens=max_tokens
                )
            )
            
            # Rule 2: Explicit Failure Handling
            # API 응답이 비어있거나 차단된 경우, 명확한 에러 메시지를 제공합니다.
            if not response.text:
                if response.prompt_feedback:
                    # 안전 필터에 의해 차단된 경우
                    reason = response.prompt_feedback.block_reason
                    raise EngineError(f"프롬프트가 안전 필터에 의해 차단되었습니다: {reason}")
                else:
                    raise EngineError("AI가 빈 응답을 반환했습니다.")
            
            logger.debug(f"AI 응답 생성 완료 - 응답 길이: {len(response.text)} 문자")
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"AI 응답 생성 실패: {str(e)}")
            raise EngineError(f"AI 응답 생성 중 오류가 발생했습니다: {str(e)}")
    
    def generate_react_step(self, context: str, available_tools: List[str]) -> str:
        """
        ReAct 패턴에 특화된 단일 스텝(Thought, Action, 또는 Final Answer)을 생성합니다.
        
        Args:
            context (str): 현재까지의 대화 맥락 (이전 Thought, Action, Observation)
            available_tools (List[str]): 사용 가능한 도구 목록
            
        Returns:
            str: ReAct 패턴에 따른 AI의 다음 스텝
            
        Raises:
            EngineError: ReAct 스텝 생성 실패 시
        """
        try:
            # Rule 4: Clear and Detailed Comments
            # ReAct 패턴을 위한 전용 시스템 지시사항을 정의합니다.
            # 이는 AI가 구조화된 사고-행동 패턴을 따르도록 유도합니다.
            system_instruction = self._get_react_system_instruction(available_tools)
            
            return self.generate_response(
                prompt=context,
                system_instruction=system_instruction,
                temperature=0.3  # ReAct는 창의성보다 논리적 일관성이 중요
            )
            
        except Exception as e:
            logger.error(f"ReAct 스텝 생성 실패: {str(e)}")
            raise EngineError(f"ReAct 스텝 생성 중 오류가 발생했습니다: {str(e)}")
    
    def _get_react_system_instruction(self, available_tools: List[str]) -> str:
        """
        ReAct 패턴을 위한 시스템 지시사항을 생성합니다.
        
        Args:
            available_tools (List[str]): 사용 가능한 도구 목록
            
        Returns:
            str: ReAct 패턴 시스템 지시사항
        """
        tools_list = "\n".join([f"- {tool}" for tool in available_tools])
        
        return f"""
당신은 ReAct(Reasoning and Acting) 패턴을 사용하는 AI 어시스턴트입니다.

사용 가능한 도구:
{tools_list}

다음 형식을 엄격히 따라주세요:

Thought: [현재 상황에 대한 분석과 다음에 취할 행동에 대한 계획]
Action: [실행할 도구명]
Action Input: [도구에 전달할 입력값]

또는 최종 답변이 준비되었다면:

Thought: [최종 분석]
Final Answer: [사용자에게 제공할 최종 답변]

중요한 규칙:
1. 반드시 "Thought:"로 시작하여 현재 상황을 분석하세요.
2. 도구가 필요하면 "Action:"과 "Action Input:"을 사용하세요.
3. 최종 답변이 준비되었으면 "Final Answer:"를 사용하세요.
4. 한 번에 하나의 Action만 실행하세요.
"""

    def validate_api_connection(self) -> bool:
        """
        Gemini API 연결 상태를 확인합니다.
        
        Returns:
            bool: 연결 성공 시 True, 실패 시 False
        """
        try:
            # Rule 4: Clear and Detailed Comments
            # 간단한 테스트 프롬프트로 API 연결을 확인합니다.
            # 이는 설정 문제를 조기에 발견하는 데 도움이 됩니다.
            test_response = self.generate_response("Hello")
            return len(test_response) > 0
            
        except Exception as e:
            logger.warning(f"API 연결 확인 실패: {str(e)}")
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        현재 모델의 정보를 반환합니다.
        
        Returns:
            Dict[str, Any]: 모델 정보 딕셔너리
        """
        return {
            "model_name": self.model_name,
            "provider": "Google Gemini",
            "api_connected": self.validate_api_connection()
        }
