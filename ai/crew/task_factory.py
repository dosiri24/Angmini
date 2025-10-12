"""
crew/task_factory.py
사용자 입력을 CrewAI Task로 변환
"""
from typing import List, Optional, Dict, Any, Union
from pathlib import Path
from crewai import Task
from ai.agents.planner_agent import PlannerAgent
from ai.agents.base_agent import BaseAngminiAgent
from ai.memory.service import MemoryService
from ai.core.logger import get_logger


class TaskFactory:
    """Task 생성 팩토리"""

    def __init__(
        self,
        planner: PlannerAgent,
        worker_agents: List[BaseAngminiAgent],
        memory_service: Optional[MemoryService] = None
    ):
        self.planner = planner
        self.worker_agents = {agent.role(): agent for agent in worker_agents}
        self.memory_service = memory_service
        self.logger = get_logger(__name__)

    def _format_file_metadata_to_text(self, file_metadata: List[Dict[str, Any]]) -> str:
        """
        파일 메타데이터를 자연어 설명으로 변환.

        Args:
            file_metadata: 파일 메타데이터 리스트

        Returns:
            자연어 형태의 파일 정보 텍스트
        """
        if not file_metadata:
            return ""

        file_descriptions = []
        for idx, metadata in enumerate(file_metadata, 1):
            filename = metadata.get("filename", "unknown")
            original_name = metadata.get("original_filename", filename)
            filepath = metadata.get("filepath", "")
            content_type = metadata.get("content_type", "unknown")
            size_bytes = metadata.get("size", 0)

            # 파일 크기를 읽기 쉬운 형태로 변환
            if size_bytes < 1024:
                size_str = f"{size_bytes} bytes"
            elif size_bytes < 1024 * 1024:
                size_str = f"{size_bytes / 1024:.1f} KB"
            else:
                size_str = f"{size_bytes / (1024 * 1024):.1f} MB"

            # 파일 타입 추론
            file_ext = Path(original_name).suffix.lower()
            if file_ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"]:
                file_type = "이미지"
            elif file_ext in [".pdf"]:
                file_type = "PDF 문서"
            elif file_ext in [".doc", ".docx"]:
                file_type = "Word 문서"
            elif file_ext in [".txt", ".md"]:
                file_type = "텍스트 문서"
            else:
                file_type = "파일"

            file_desc = (
                f"{idx}. {file_type}: {original_name} "
                f"(크기: {size_str}, 저장 위치: {filepath})"
            )
            file_descriptions.append(file_desc)

        header = f"\n\n### 📎 첨부된 파일 ({len(file_metadata)}개)\n"
        files_text = "\n".join(file_descriptions)
        footer = "\n\n**중요**: 위 파일들을 AnalyzerAgent에게 위임하여 분석하세요.\n"

        return header + files_text + footer

    def _classify_intent(self, user_input: str) -> str:
        """LLM으로 사용자 의도 분류 (메모리 검색 전 실행)"""
        if not self.planner.ai_brain:
            return "task_request"  # 안전하게 작업 요청으로 간주

        classification_prompt = f"""다음 사용자 입력을 분석하여 의도를 판단하세요.

사용자 입력: {user_input}

의도 분류 기준:
- simple_conversation: 단순 인사, 일상 대화, 감사 표현 등
  예시: "안녕", "하이", "고마워", "잘 지내?", "수고했어", "반가워"

- task_request: 명확한 작업 요청이나 질문
  예시: "파일 목록 보여줘", "과거 작업 찾아줘", "Notion에서 할 일 가져와"

다음 중 정확히 하나만 응답하세요: simple_conversation 또는 task_request"""

        try:
            response = self.planner.ai_brain.generate_text(
                classification_prompt,
                temperature=0.3,
                max_output_tokens=200  # 50→200: 의도 분류 응답 생성 보장
            )
            intent = response.text.strip().lower()

            if "simple_conversation" in intent:
                self.logger.debug(f"의도 분류: 단순 대화 - '{user_input}'")
                return "simple_conversation"
            else:
                self.logger.debug(f"의도 분류: 작업 요청 - '{user_input}'")
                return "task_request"
        except Exception as e:
            self.logger.warning(f"의도 분류 실패: {e}, 기본값(task_request) 사용")
            return "task_request"

    def _validate_file_metadata(self, file_metadata: Any) -> bool:
        """
        파일 메타데이터의 스키마 검증 (Fix #10).

        Args:
            file_metadata: 검증할 파일 메타데이터

        Returns:
            검증 성공 여부
        """
        # 타입 검증: 리스트여야 함
        if not isinstance(file_metadata, list):
            self.logger.warning(f"Invalid file_metadata type: expected list, got {type(file_metadata)}")
            return False

        # 각 항목 검증
        required_keys = {"filename", "filepath"}
        optional_keys = {"original_filename", "content_type", "size"}

        for idx, item in enumerate(file_metadata):
            # 각 항목이 딕셔너리여야 함
            if not isinstance(item, dict):
                self.logger.warning(f"Invalid file_metadata[{idx}] type: expected dict, got {type(item)}")
                return False

            # 필수 키 확인
            missing_keys = required_keys - set(item.keys())
            if missing_keys:
                self.logger.warning(f"Missing required keys in file_metadata[{idx}]: {missing_keys}")
                return False

            # 값 타입 확인
            if not isinstance(item.get("filename"), str):
                self.logger.warning(f"Invalid filename type in file_metadata[{idx}]")
                return False

            if not isinstance(item.get("filepath"), str):
                self.logger.warning(f"Invalid filepath type in file_metadata[{idx}]")
                return False

        return True

    def create_tasks_from_input(
        self, user_input: Union[str, Dict[str, Any]]
    ) -> List[Task]:
        """사용자 입력으로부터 Task 리스트 생성 - 100% LLM 기반

        Args:
            user_input: 문자열 또는 딕셔너리 (파일 메타데이터 포함)
                - str: 일반 텍스트 입력
                - dict: {"user_input": str, "file_metadata": List[Dict]}

        Returns:
            Task 리스트

        프로세스:
            1단계: 입력 타입 확인 및 파일 메타데이터 처리
            2단계: 의도 분류 (simple_conversation vs task_request)
            3단계: task_request인 경우에만 메모리 검색
            4단계: Task 생성
        """

        # 1단계: 입력 타입 확인 및 처리
        file_context = ""
        if isinstance(user_input, dict):
            # 딕셔너리 입력: 파일 메타데이터 포함
            text_input = user_input.get("user_input", "")
            file_metadata = user_input.get("file_metadata", [])

            # 파일 메타데이터 스키마 검증 (Fix #10)
            if file_metadata and not self._validate_file_metadata(file_metadata):
                self.logger.error("Invalid file_metadata schema, ignoring file metadata")
                file_metadata = []

            if file_metadata:
                file_context = self._format_file_metadata_to_text(file_metadata)
                self.logger.info(f"Multimodal input detected: {len(file_metadata)} file(s)")
            else:
                self.logger.warning("Dict input received but no file_metadata found")

            # 이후 처리를 위해 텍스트 입력만 사용
            user_input = text_input
        else:
            # 문자열 입력: 일반 텍스트
            self.logger.debug("Text-only input received")

        # 2단계: 의도 분류
        intent = self._classify_intent(user_input)

        # 3단계: 의도에 따라 메모리 검색 여부 결정
        memory_context = ""
        if intent == "task_request" and self.memory_service:
            try:
                self.logger.debug(f"메모리 검색 시작 (작업 요청 감지)")
                search_results = self.memory_service.repository.search(user_input, top_k=3)
                if search_results:
                    memory_context = "\n\n### 📚 관련 경험 (이미 검색 완료)\n"
                    # search() returns List[Tuple[MemoryRecord, float]]
                    for i, (record, score) in enumerate(search_results, 1):
                        memory_context += f"\n{i}. {record.summary}\n"
                        memory_context += f"   - 목표: {record.goal}\n"
                        if record.outcome:
                            memory_context += f"   - 결과: {record.outcome}\n"
                    memory_context += "\n**중요**: 위 내용은 이미 검색된 결과입니다. Memory Agent를 다시 호출하지 마세요.\n"
                else:
                    memory_context = "\n\n### 📚 관련 경험\n관련된 과거 기억이 없습니다.\n"
                self.logger.debug(f"메모리 검색 완료: {len(search_results)}개 발견")
            except Exception as e:
                self.logger.warning(f"메모리 검색 실패: {e}")
                memory_context = ""
        else:
            self.logger.debug(f"메모리 검색 건너뜀 (단순 대화)")

        # 4단계: Task 생성
        if intent == "simple_conversation" and not file_context:
            # 단순 대화 (파일 없음): 메모리 검색 없이 바로 응답
            description = f"""
            사용자 요청: {user_input}

            위 요청은 단순 인사나 일상 대화입니다.
            자연스럽고 친근하게 응답하세요. 다른 에이전트에게 작업을 위임하지 마세요.

            **중요**: 최종 답변은 JSON이나 기술적 형식이 아닌, 자연스러운 한국어 문장으로 작성하세요.
            """.strip()
        else:
            # 작업 요청 또는 파일 첨부: 메모리 컨텍스트 + 파일 컨텍스트와 함께 작업 수행
            description = f"""
            사용자 요청: {user_input}
            {file_context}
            {memory_context}

            위 요청을 분석하고 적절한 전문 에이전트를 선택하여 작업을 수행하세요.

            **중요**: 최종 답변은 JSON이나 기술적 형식이 아닌, 자연스러운 한국어 문장으로 작성하세요.
            """.strip()

        return [Task(
            description=description,
            expected_output="""사용자가 이해하기 쉬운 자연스러운 한국어 답변.
            기술적 JSON, 딕셔너리, 코드 형식이 아닌 일반 대화체로 작성.
            예: "바탕화면에 총 5개의 파일이 있습니다: test.txt, image.png, ..."
            """,
            agent=self.planner.build_agent()
        )]

    def create_sequential_tasks(
        self,
        descriptions: List[str],
        agent_names: List[str]
    ) -> List[Task]:
        """순차 실행용 Task 생성 (명시적 순서)"""
        from agents import AgentFactory

        tasks = []

        for desc, agent_name in zip(descriptions, agent_names):
            if agent_name not in self.worker_agents:
                self.logger.warning(f"알 수 없는 에이전트 역할: {agent_name}")
                continue

            agent = self.worker_agents[agent_name]
            task = Task(
                description=desc,
                expected_output=f"{agent_name} 작업 결과",
                agent=agent.build_agent()
            )
            tasks.append(task)

        # Task 의존성 설정 (순차 실행)
        for i in range(1, len(tasks)):
            tasks[i].context = [tasks[i-1]]  # 이전 Task 결과를 컨텍스트로 사용

        self.logger.debug(f"순차 Task {len(tasks)}개 생성 완료")
        return tasks

    def create_parallel_tasks(
        self,
        task_descriptions: Dict[str, str]
    ) -> List[Task]:
        """병렬 실행용 Task 생성"""
        from agents import AgentFactory

        tasks = []

        for agent_role, description in task_descriptions.items():
            if agent_role not in self.worker_agents:
                self.logger.warning(f"알 수 없는 에이전트 역할: {agent_role}")
                continue

            agent = self.worker_agents[agent_role]
            task = Task(
                description=description,
                expected_output=f"{agent_role} 작업 결과",
                agent=agent.build_agent()
            )
            tasks.append(task)

        # 병렬 실행이므로 의존성 설정 없음
        self.logger.debug(f"병렬 Task {len(tasks)}개 생성 완료")
        return tasks