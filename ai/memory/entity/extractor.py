"""LLM-based entity extraction from conversation and execution context.

Uses Gemini to identify and extract structured entities (people, projects, tools,
concepts, files) from natural language text and execution metadata.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from ai.core.logger import get_logger
from ..llm.gemini_client import GeminiClient
from .models import EntityType, ExtractedEntityInfo, RelationType


_ENTITY_EXTRACTION_PROMPT = """당신은 대화 내용과 실행 컨텍스트에서 엔티티를 추출하는 전문가입니다.

다음 텍스트에서 중요한 엔티티를 식별하고 구조화된 JSON 형식으로 추출하세요.

**추출할 엔티티 유형:**
- PERSON: 사용자, 협력자, 팀원, 개발자 이름
- PROJECT: 코드 프로젝트, 이니셔티브, 리포지토리 이름
- TOOL: 소프트웨어 도구, 라이브러리, 프레임워크, 프로그래밍 언어
- CONCEPT: 추상적 개념, 알고리즘, 디자인 패턴, 아키텍처 패턴
- FILE: 구체적인 파일, 모듈, 컴포넌트 (경로 포함 시)

**추출 규칙:**
1. 대화 맥락에서 실제로 중요한 엔티티만 추출 (일반적인 단어는 제외)
2. 각 엔티티의 유형을 정확히 분류
3. 가능한 경우 추가 속성 정보 포함 (예: 파일 경로, 프로젝트 URL, 버전)
4. 엔티티 간 관계가 명확한 경우 relations 필드에 포함
5. 신뢰도(confidence)는 0.0~1.0 범위로 평가

**입력 텍스트:**
{text}

**추출 컨텍스트 (참고용):**
{context}

**출력 형식 (JSON):**
{{
  "entities": [
    {{
      "type": "TOOL",
      "name": "CrewAI",
      "attributes": {{"version": "2.0", "category": "multi-agent framework"}},
      "confidence": 0.95
    }},
    {{
      "type": "FILE",
      "name": "memory_records.py",
      "attributes": {{"file_path": "ai/memory/memory_records.py", "module": "memory"}},
      "confidence": 0.9
    }}
  ],
  "relations": [
    {{
      "source": "Angmini",
      "target": "CrewAI",
      "relation_type": "USES"
    }}
  ]
}}

중요: 반드시 유효한 JSON만 출력하세요. 설명이나 추가 텍스트는 포함하지 마세요.
"""


_RELATION_EXTRACTION_PROMPT = """다음은 엔티티 목록입니다. 이들 간의 관계를 식별하세요.

**엔티티:**
{entities_json}

**관계 유형:**
- COLLABORATES_WITH: 사람 간 협력
- WORKS_ON: 사람이 프로젝트에 참여
- MAINTAINS: 사람이 도구/프로젝트 유지보수
- DEPENDS_ON: 프로젝트/파일이 다른 것에 의존
- USES: 프로젝트/파일이 도구 사용
- IMPORTS: 파일 간 임포트
- BELONGS_TO: 파일이 프로젝트에 속함
- CONTAINS: 프로젝트가 파일 포함
- PART_OF: 개념이 다른 개념의 일부
- RELATED_TO: 개념 간 관련
- IMPLEMENTS: 파일이 개념 구현
- DISCUSSES: 어떤 것이 개념 논의

**컨텍스트:**
{context}

**출력 형식 (JSON):**
{{
  "relations": [
    {{
      "source": "memory_records.py",
      "target": "memory",
      "relation_type": "BELONGS_TO",
      "context": "memory module implementation"
    }}
  ]
}}

중요: 반드시 유효한 JSON만 출력하세요.
"""


class EntityExtractor:
    """Extract structured entities from text using LLM.

    Uses Gemini to perform Named Entity Recognition (NER) and extract
    structured entities with attributes and relationships.
    """

    def __init__(self, llm_client: GeminiClient) -> None:
        """Initialize extractor with LLM client.

        Args:
            llm_client: Gemini client for LLM-based extraction
        """
        self._llm = llm_client
        self._logger = get_logger(self.__class__.__name__)

    def extract_from_text(
        self,
        text: str,
        context: Dict[str, Any] | None = None,
    ) -> List[ExtractedEntityInfo]:
        """Extract entities from natural language text.

        Args:
            text: Natural language text to extract entities from
            context: Optional execution context (tools_used, outcome, etc.)

        Returns:
            List of extracted entities with metadata
        """
        if not text or not text.strip():
            return []

        # Prepare context string
        context_str = self._format_context(context or {})

        # Generate extraction prompt
        prompt = _ENTITY_EXTRACTION_PROMPT.format(
            text=text,
            context=context_str,
        )

        try:
            # Call LLM for entity extraction
            response = self._llm.generate_text(prompt)
            response_text = response.strip()

            # Parse JSON response
            extraction_result = self._parse_extraction_response(response_text)

            # Convert to ExtractedEntityInfo objects
            entities = []
            for entity_dict in extraction_result.get("entities", []):
                try:
                    entity_type = EntityType(entity_dict["type"].lower())
                    entity = ExtractedEntityInfo(
                        type=entity_type,
                        name=entity_dict["name"],
                        attributes=entity_dict.get("attributes", {}),
                        confidence=entity_dict.get("confidence", 0.8),
                        text_span=None,  # Could be enhanced with span detection
                    )
                    entities.append(entity)
                except (KeyError, ValueError) as e:
                    self._logger.warning(f"Invalid entity format: {e}, skipping")
                    continue

            self._logger.info(f"Extracted {len(entities)} entities from text")
            return entities

        except Exception as e:
            self._logger.error(f"Entity extraction failed: {e}", exc_info=True)
            return []

    def extract_relations(
        self,
        entities: List[ExtractedEntityInfo],
        context: Dict[str, Any] | None = None,
    ) -> List[tuple[str, str, RelationType, str]]:
        """Extract relationships between entities.

        Args:
            entities: List of extracted entities
            context: Optional context about entity interactions

        Returns:
            List of (source_name, target_name, relation_type, context) tuples
        """
        if len(entities) < 2:
            return []

        # Convert entities to JSON for prompt
        entities_json = json.dumps(
            [
                {
                    "type": e.type.value,
                    "name": e.name,
                    "attributes": e.attributes,
                }
                for e in entities
            ],
            ensure_ascii=False,
            indent=2,
        )

        context_str = self._format_context(context or {})

        # Generate relation extraction prompt
        prompt = _RELATION_EXTRACTION_PROMPT.format(
            entities_json=entities_json,
            context=context_str,
        )

        try:
            response = self._llm.generate_text(prompt)
            response_text = response.strip()

            # Parse JSON response
            relation_result = self._parse_extraction_response(response_text)

            relations = []
            for rel_dict in relation_result.get("relations", []):
                try:
                    relation_type = RelationType(rel_dict["relation_type"].lower())
                    relation = (
                        rel_dict["source"],
                        rel_dict["target"],
                        relation_type,
                        rel_dict.get("context", ""),
                    )
                    relations.append(relation)
                except (KeyError, ValueError) as e:
                    self._logger.warning(f"Invalid relation format: {e}, skipping")
                    continue

            self._logger.info(f"Extracted {len(relations)} relations")
            return relations

        except Exception as e:
            self._logger.error(f"Relation extraction failed: {e}", exc_info=True)
            return []

    def extract_from_memory_context(
        self,
        memory_dict: Dict[str, Any],
    ) -> tuple[List[ExtractedEntityInfo], List[tuple]]:
        """Extract entities and relations from memory record context.

        Args:
            memory_dict: Dictionary with keys like summary, goal, user_intent,
                         outcome, tools_used, etc.

        Returns:
            Tuple of (entities, relations)
        """
        # Combine relevant text fields
        text_parts = []
        if "summary" in memory_dict:
            text_parts.append(f"요약: {memory_dict['summary']}")
        if "goal" in memory_dict:
            text_parts.append(f"목표: {memory_dict['goal']}")
        if "user_intent" in memory_dict:
            text_parts.append(f"사용자 의도: {memory_dict['user_intent']}")
        if "outcome" in memory_dict:
            text_parts.append(f"결과: {memory_dict['outcome']}")

        text = "\n".join(text_parts)

        # Prepare context
        context = {
            "tools_used": memory_dict.get("tools_used", []),
            "tags": memory_dict.get("tags", []),
            "category": memory_dict.get("category", ""),
        }

        # Extract entities
        entities = self.extract_from_text(text, context)

        # Extract relations between entities
        relations = self.extract_relations(entities, context)

        return entities, relations

    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context dictionary as readable string."""
        parts = []
        if context.get("tools_used"):
            parts.append(f"사용된 도구: {', '.join(context['tools_used'])}")
        if context.get("tags"):
            parts.append(f"태그: {', '.join(context['tags'])}")
        if context.get("category"):
            parts.append(f"카테고리: {context['category']}")

        return "\n".join(parts) if parts else "(컨텍스트 없음)"

    def _parse_extraction_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response as JSON, handling markdown code blocks."""
        # Remove markdown code blocks if present
        response = re.sub(r"```json\s*", "", response)
        response = re.sub(r"```\s*", "", response)
        response = response.strip()

        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            self._logger.error(f"Failed to parse JSON: {e}")
            self._logger.debug(f"Response text: {response}")
            return {"entities": [], "relations": []}


class RuleBasedEntityExtractor:
    """Fallback rule-based entity extraction.

    Used when LLM extraction fails or for supplementary extraction.
    Uses pattern matching and heuristics.
    """

    def __init__(self) -> None:
        self._logger = get_logger(self.__class__.__name__)

        # File path patterns
        self._file_patterns = [
            r"\b[\w_/]+\.py\b",  # Python files
            r"\b[\w_/]+\.js\b",  # JavaScript files
            r"\b[\w_/]+\.ts\b",  # TypeScript files
            r"\b[\w_/]+\.md\b",  # Markdown files
            r"\b[\w_/]+\.json\b",  # JSON files
        ]

        # Tool/framework names (common ones)
        self._known_tools = {
            "crewai", "langchain", "gemini", "openai", "faiss",
            "sqlite", "discord", "notion", "pytest", "torch",
            "transformers", "qwen", "python", "javascript",
            "typescript", "react", "vue", "nodejs",
        }

    def extract_files(self, text: str) -> List[ExtractedEntityInfo]:
        """Extract file paths using regex patterns."""
        entities = []
        text_lower = text.lower()

        for pattern in self._file_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                file_name = match.group(0)
                entity = ExtractedEntityInfo(
                    type=EntityType.FILE,
                    name=file_name,
                    attributes={"file_path": file_name},
                    confidence=0.7,
                    text_span=file_name,
                )
                entities.append(entity)

        return entities

    def extract_tools(self, text: str) -> List[ExtractedEntityInfo]:
        """Extract known tool/framework names."""
        entities = []
        text_lower = text.lower()

        for tool in self._known_tools:
            if tool in text_lower:
                entity = ExtractedEntityInfo(
                    type=EntityType.TOOL,
                    name=tool.capitalize(),
                    attributes={"category": "framework" if tool in {"crewai", "langchain", "react"} else "tool"},
                    confidence=0.6,
                )
                entities.append(entity)

        return entities
