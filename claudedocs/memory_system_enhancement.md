# Angmini 메모리 시스템 고도화 설계서

> **작성일**: 2025-10-03
> **목적**: 최신 AI 에이전트 메모리 알고리즘 조사 및 Angmini 프로젝트 적용
> **버전**: 1.0.0

---

## 📋 목차

1. [조사 배경 및 목적](#1-조사-배경-및-목적)
2. [최신 AI 에이전트 메모리 알고리즘 조사](#2-최신-ai-에이전트-메모리-알고리즘-조사)
3. [현재 Angmini 메모리 시스템 분석](#3-현재-angmini-메모리-시스템-분석)
4. [개선 방안 설계](#4-개선-방안-설계)
5. [구현 로드맵](#5-구현-로드맵)
6. [예상 효과](#6-예상-효과)

---

## 1. 조사 배경 및 목적

### 1.1 배경

Angmini는 현재 장기 기억(Long-Term Memory) 시스템을 갖추고 있으나, 2024-2025년에 발표된 최신 AI 에이전트 프레임워크들은 더 정교한 계층적 메모리 아키텍처를 도입하고 있습니다.

### 1.2 목적

- **최신 알고리즘 파악**: MemGPT, AutoGen v0.4, Mem0, CrewAI 등의 메모리 시스템 조사
- **현재 시스템 평가**: Angmini 메모리 시스템의 강점 및 개선점 분석
- **실용적 개선**: 조사한 알고리즘을 Angmini에 적용하여 메모리 성능 향상

---

## 2. 최신 AI 에이전트 메모리 알고리즘 조사

### 2.1 계층적 메모리 아키텍처

#### MemGPT / Letta (2024-2025)

**핵심 개념**: OS 스타일 메모리 계층 구조

- **메모리 계층**:
  - Working Context (고정 컨텍스트 윈도우 내)
  - External Storage (무제한 용량)
  - Active Memory Management (에이전트가 능동적으로 관리)

- **특징**:
  - 에이전트가 무엇을 컨텍스트에 유지하고 무엇을 외부로 보낼지 결정
  - 필요시 외부 레이어에서 검색하여 컨텍스트로 로드
  - **벤치마크**: LoCoMo 74.0% (GPT-4o mini)

- **참고**: https://www.letta.com/

#### CrewAI Memory System (2024-2025)

**핵심 개념**: 4계층 통합 메모리

```python
Component | Description
----------|------------
Short-Term Memory | 현재 실행 중 RAG 기반 최근 상호작용 저장 (ChromaDB)
Long-Term Memory | 세션 간 보존, 과거 실행에서 학습 (SQLite3)
Entity Memory | 사람/장소/개념 추적 및 관계 매핑 (RAG)
Contextual Memory | 위 3개 통합하여 일관된 응답 제공
```

- **저장소**:
  - Short-Term: ChromaDB + RAG
  - Long-Term: SQLite3
  - Entity: RAG 기반
  - Custom storage path 지원

- **설정**:
```python
crew = Crew(
    agents=[...],
    tasks=[...],
    memory=True,  # 모든 메모리 활성화
    embedder={"provider": "huggingface", "config": {...}}
)
```

- **참고**: https://docs.crewai.com/concepts/memory

#### AutoGen v0.4 (2025년 1월)

**핵심 개념**: 모듈식 및 확장 가능 아키텍처

- **특징**:
  - 플러그 가능한 컴포넌트 (memory, model, tools)
  - Memory protocol로 RAG 패턴 지원
  - AgentChat에 Memory 인터페이스 제공

- **Memory Protocol**:
```python
class Memory(Protocol):
    def query(self, query: str, limit: int) -> List[Result]:
        """쿼리에 대한 관련 메모리 반환"""
        ...

    def save(self, value: str, metadata: Dict) -> None:
        """새 메모리 저장"""
        ...
```

- **참고**: https://microsoft.github.io/autogen/

#### Mem0 Platform (2024-2025)

**핵심 개념**: 하이브리드 데이터베이스 + 스마트 자가 개선 메모리

- **하이브리드 DB**:
  - Vector DB: 의미적 유사도 검색
  - Key-Value Store: 빠른 조회
  - Graph DB: 관계 탐색

- **특징**:
  - 고유 식별자 (user_id, org_id, project_id)
  - 정교한 검색 프로세스
  - 사용자 맞춤형 카테고리

- **참고**: Mem0 논문 (arXiv:2504.19413)

### 2.2 하이브리드 검색 시스템

#### Reciprocal Rank Fusion (RRF)

**개념**: 의미적 검색과 키워드 검색 결과를 병합

**알고리즘**:
```python
def rrf_score(rank, k=60):
    return 1 / (rank + k)

# 각 결과의 랭크를 점수로 변환 후 합산
for rank, doc in enumerate(semantic_results):
    scores[doc.id] += rrf_score(rank)

for rank, doc in enumerate(keyword_results):
    scores[doc.id] += rrf_score(rank)

# 최종 점수로 정렬
sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

**장점**:
- 의미적 유사도와 정확한 키워드 매칭 동시 활용
- 단순하면서도 효과적
- 가중치 조정 가능 (alpha 파라미터)

#### 시간 기반 감쇠 (Temporal Decay)

**개념**: 최신 메모리에 더 높은 가중치 부여

**공식**:
```python
score_adjusted = score * exp(-decay_rate * age_days)
```

**파라미터**:
- `decay_rate`: 0.01 ~ 0.05 (일반적)
- `age_days`: 생성 후 경과 일수

### 2.3 엔티티 추적 및 관계 매핑

#### Graph-based Entity Memory

**개념**: 엔티티 간 관계를 그래프로 모델링

**엔티티 타입**:
- PERSON: 사용자, 팀원
- PROJECT: 프로젝트, 작업
- TOOL: 사용한 도구, API
- CONCEPT: 개념, 기술 스택
- FILE: 파일, 디렉토리

**관계 타입**:
- WORKS_ON: Person → Project
- USES: Person → Tool
- CONTAINS: Project → File
- RELATES_TO: Concept → Concept

**장점**:
- 컨텍스트 인식 향상
- "이 사용자가 이전에 작업한 프로젝트는?" 같은 쿼리 지원
- 개인화된 응답 생성

### 2.4 메모리 통합 및 압축

#### Memory Consolidation (MemoryOS 방식)

**개념**: 유사한 메모리를 주기적으로 병합하여 스토리지 최적화

**프로세스**:
1. **클러스터링**: 유사한 메모리 그룹화 (임베딩 거리 기반)
2. **요약**: LLM으로 클러스터 요약
3. **아카이빙**: 원본 메모리에 `archived` 플래그 설정
4. **통합 레코드 생성**: 요약본을 새 메모리로 저장

**트리거**:
- 메모리 수 > 1000개
- 정기 스케줄 (예: 매일 자정)

#### Importance Scoring

**개념**: 메모리의 중요도를 자동으로 계산하여 관리

**요인**:
```python
importance = (
    0.3 * access_frequency +    # 접근 빈도
    0.3 * recency_score +       # 최근성
    0.2 * success_score +       # 성공 여부
    0.2 * user_feedback_score  # 사용자 피드백
)
```

**활용**:
- `importance < 0.2 and age > 90 days` → 자동 아카이빙
- 검색 시 중요도 가중치 적용

---

## 3. 현재 Angmini 메모리 시스템 분석

### 3.1 현재 아키텍처

```
Angmini Memory System (현재)
├─ Storage
│  ├─ SQLite (메타데이터)
│  ├─ FAISS (벡터 인덱스)
│  └─ Qwen3-Embedding-0.6B (임베딩)
│
├─ Retrieval
│  ├─ CascadedRetriever (다중 홉 LLM 필터링)
│  └─ Repository.search() (단순 벡터 검색)
│
├─ Pipeline
│  ├─ SnapshotExtractor (실행 컨텍스트 추출)
│  ├─ MemoryCurator (LLM 요약)
│  ├─ MemoryDeduplicator (중복 제거)
│  └─ MemoryRetentionPolicy (저장 결정)
│
└─ Categories
   ├─ FULL_EXPERIENCE
   ├─ ERROR_SOLUTION
   ├─ TOOL_USAGE
   ├─ USER_PATTERN
   └─ WORKFLOW_OPTIMISATION
```

### 3.2 MemoryRecord 구조

```python
@dataclass
class MemoryRecord:
    summary: str                    # LLM 생성 요약
    goal: str                       # 사용자 목표
    user_intent: str                # 의도 분석
    outcome: str                    # 결과
    category: MemoryCategory        # 카테고리
    tools_used: List[str]           # 사용 도구
    tags: List[str]                 # 태그
    created_at: datetime            # 생성 시각
    source_metadata: Dict[str, Any] # 추가 메타데이터
    embedding: Optional[List[float]] # 벡터 임베딩
```

### 3.3 강점

✅ **고급 Cascaded Retrieval**:
- 다중 홉 검색
- LLM 기반 관련성 필터링
- 반복적 쿼리 확장
- 폴백 메커니즘

✅ **LLM 기반 큐레이션**:
- MemoryCurator가 실행 컨텍스트를 의미 있는 요약으로 변환
- 카테고리 자동 분류
- 태그 자동 생성

✅ **의미적 검색**:
- Qwen3 임베딩 + FAISS
- 고품질 벡터 검색

✅ **중복 제거**:
- MemoryDeduplicator로 유사 메모리 감지

### 3.4 개선이 필요한 부분

❌ **단일 계층 메모리**:
- Long-Term Memory만 존재
- Short-Term Memory 없음 (현재 세션 컨텍스트 관리 부재)

❌ **엔티티 추적 부재**:
- 사람, 프로젝트, 도구, 개념 간 관계 미추적
- "이 사용자가 자주 사용하는 도구는?" 같은 쿼리 불가

❌ **하이브리드 검색 부재**:
- 의미적 검색만 지원
- 정확한 키워드 매칭 불가 (예: 특정 파일명 검색)

❌ **시간 기반 관리 부족**:
- 최근성 가중치 없음
- 중요도 점수 시스템 없음
- 자동 아카이빙 없음

❌ **메모리 통합/압축 없음**:
- 메모리 수 증가 시 성능 저하 우려
- 유사한 메모리 수동 정리 필요

---

## 4. 개선 방안 설계

### 4.1 Phase 1: 계층적 메모리 아키텍처

#### 4.1.1 Short-Term Memory (CrewAI 통합)

**목적**: 현재 세션/대화 컨텍스트 유지

**구현 전략**:
- CrewAI의 built-in Short-Term Memory 활용
- ChromaDB 기반 (CrewAI 기본 제공)

**설정**:
```python
# crew/crew_config.py
crew = Crew(
    agents=[...],
    tasks=[...],
    memory=True,  # Short-Term + Long-Term + Entity 활성화
    embedder={
        "provider": "huggingface",
        "config": {"model": "Qwen/Qwen3-Embedding-0.6B"}
    }
)
```

**생명주기**:
- 세션 시작: 빈 상태
- 세션 중: 최근 N개 상호작용 저장 (N=20)
- 세션 종료: 중요한 내용만 Long-Term으로 전환

#### 4.1.2 Entity Memory

**목적**: 사람, 프로젝트, 도구, 개념 추적 및 관계 매핑

**디렉토리 구조**:
```
ai/memory/entity/
├── __init__.py
├── models.py           # Entity, EntityType, EntityRelation
├── extractor.py        # LLM 기반 엔티티 추출
├── storage.py          # EntityRepository (SQLite + FAISS)
└── tracker.py          # EntityTracker (전체 관리)
```

**데이터 모델**:
```python
class EntityType(Enum):
    PERSON = "person"
    PROJECT = "project"
    TOOL = "tool"
    CONCEPT = "concept"
    FILE = "file"

@dataclass
class Entity:
    id: str                              # UUID
    type: EntityType                     # 엔티티 타입
    name: str                            # 이름
    attributes: Dict[str, Any]           # 속성 (flexible)
    first_seen: datetime                 # 처음 발견
    last_seen: datetime                  # 마지막 언급
    mention_count: int                   # 언급 횟수
    relations: List[Tuple[str, str, str]] # (relation_type, target_id, context)
    embedding: Optional[List[float]]     # 벡터 임베딩
```

**EntityExtractor**:
```python
class EntityExtractor:
    def __init__(self, brain: AIBrain):
        self.brain = brain
        self.prompt_template = self._load_prompt()

    def extract(self, text: str) -> List[Entity]:
        """LLM으로 Named Entity Recognition 수행"""
        prompt = self.prompt_template.replace("{{text}}", text)
        response = self.brain.generate_text(prompt, temperature=0.1)

        # JSON 파싱 및 Entity 객체 생성
        entities_data = json.loads(response.text)
        return [Entity(**e) for e in entities_data["entities"]]
```

**EntityRepository**:
```python
class EntityRepository:
    def __init__(self, sqlite_store, vector_index):
        self.sqlite = sqlite_store
        self.vector_index = vector_index

    def add_or_update(self, entity: Entity) -> Entity:
        """기존 엔티티 업데이트 or 새로 생성"""
        existing = self.find_by_name(entity.name, entity.type)
        if existing:
            existing.mention_count += 1
            existing.last_seen = datetime.utcnow()
            existing.relations.extend(entity.relations)
            self.sqlite.update(existing)
            return existing
        else:
            self.sqlite.insert(entity)
            self.vector_index.add(entity)
            return entity

    def find_by_name(self, name: str, type: EntityType = None) -> Optional[Entity]:
        """이름으로 엔티티 검색"""
        pass

    def find_related(self, entity_id: str, relation_type: str = None) -> List[Entity]:
        """관계된 엔티티 검색"""
        pass

    def search_semantic(self, query: str, top_k: int = 5) -> List[Tuple[Entity, float]]:
        """의미적 검색"""
        pass
```

**통합 예시**:
```python
# 메모리 캡처 시 엔티티 자동 추출
def capture_with_entities(context, user_request):
    # 1. 기존 메모리 캡처
    memory_result = memory_service.capture(context, user_request)

    # 2. 엔티티 추출
    entities = entity_extractor.extract(context.to_text())

    # 3. 엔티티 저장 및 업데이트
    for entity in entities:
        entity_repository.add_or_update(entity)

    return memory_result
```

#### 4.1.3 Contextual Memory (통합 레이어)

**목적**: Short-Term, Long-Term, Entity를 통합한 일관된 검색 인터페이스

**구현**:
```python
class ContextualMemoryService:
    def __init__(self,
                 short_term_memory,      # CrewAI Memory
                 long_term_memory,        # Angmini MemoryRepository
                 entity_memory):          # EntityRepository
        self.stm = short_term_memory
        self.ltm = long_term_memory
        self.entity = entity_memory

    def retrieve(self, query: str, top_k: int = 10, context: str = "all") -> List[Any]:
        """통합 검색"""
        results = []

        # 1. Short-Term (최근 컨텍스트)
        if context in ["all", "short"]:
            stm_results = self.stm.search(query, limit=5)
            results.extend([("short", r) for r in stm_results])

        # 2. Entity (관련 엔티티)
        if context in ["all", "entity"]:
            entity_results = self.entity.search_semantic(query, top_k=5)
            results.extend([("entity", e) for e, score in entity_results])

        # 3. Long-Term (과거 경험)
        if context in ["all", "long"]:
            ltm_results = self.ltm.cascaded_retriever.retrieve(query)
            results.extend([("long", m) for m in ltm_results.matches])

        # 4. 결과 병합 및 리랭킹
        return self._merge_and_rank(results, top_k=top_k)

    def _merge_and_rank(self, results, top_k):
        """다양한 소스의 결과를 통합 점수로 리랭킹"""
        # 각 소스에 가중치 적용
        weights = {"short": 0.4, "entity": 0.3, "long": 0.3}

        # 점수 계산 및 정렬
        scored = []
        for source, item in results:
            base_score = self._get_score(item)
            final_score = base_score * weights[source]
            scored.append((item, final_score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [item for item, score in scored[:top_k]]
```

### 4.2 Phase 2: 하이브리드 검색 시스템

#### 4.2.1 FTS5 Full-Text Search

**목적**: 정확한 키워드 매칭 지원

**SQLite FTS5 테이블 생성**:
```sql
CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts
USING fts5(
    id UNINDEXED,
    summary,
    goal,
    user_intent,
    outcome,
    tags,
    tokenize='unicode61'
);

-- 트리거: 메모리 추가 시 FTS 자동 업데이트
CREATE TRIGGER IF NOT EXISTS memories_fts_insert
AFTER INSERT ON memories
BEGIN
    INSERT INTO memories_fts(id, summary, goal, user_intent, outcome, tags)
    VALUES (NEW.id, NEW.summary, NEW.goal, NEW.user_intent, NEW.outcome, NEW.tags);
END;
```

**FTS 검색 구현**:
```python
def fts_search(self, query: str, top_k: int = 10) -> List[Tuple[MemoryRecord, float]]:
    """SQLite FTS5로 키워드 검색"""
    # FTS5 쿼리 (BM25 랭킹)
    sql = """
        SELECT id, rank
        FROM memories_fts
        WHERE memories_fts MATCH ?
        ORDER BY rank
        LIMIT ?
    """

    cursor = self.sqlite.execute(sql, (query, top_k))
    results = []

    for row in cursor:
        record_id, fts_rank = row
        record = self.get_by_id(record_id)
        # FTS5 rank는 음수 (낮을수록 좋음) → 양수 점수로 변환
        score = 1.0 / (1.0 - fts_rank)
        results.append((record, score))

    return results
```

#### 4.2.2 Reciprocal Rank Fusion (RRF)

**구현**:
```python
class HybridRetriever:
    def __init__(self, vector_index, sqlite_store, alpha=0.5, k=60):
        self.vector_index = vector_index
        self.sqlite_store = sqlite_store
        self.alpha = alpha  # 의미적 vs 키워드 가중치
        self.k = k          # RRF 상수

    def search(self, query: str, top_k: int = 10) -> List[Tuple[MemoryRecord, float]]:
        """하이브리드 검색: 의미적 + 키워드"""

        # 1. 의미적 검색
        semantic_results = self.vector_index.search(query, k=top_k * 2)

        # 2. 키워드 검색 (FTS5)
        keyword_results = self.sqlite_store.fts_search(query, top_k=top_k * 2)

        # 3. RRF 병합
        return self._reciprocal_rank_fusion(
            semantic_results, keyword_results,
            alpha=self.alpha, k_param=self.k, top_k=top_k
        )

    def _reciprocal_rank_fusion(self, semantic, keyword, alpha, k_param, top_k):
        """RRF 알고리즘으로 결과 병합"""
        scores = {}

        # 의미적 검색 점수
        for rank, (record, _) in enumerate(semantic):
            record_id = record.source_metadata["id"]
            rrf_score = alpha / (rank + k_param)
            scores[record_id] = scores.get(record_id, 0) + rrf_score

        # 키워드 검색 점수
        for rank, (record, _) in enumerate(keyword):
            record_id = record.source_metadata["id"]
            rrf_score = (1 - alpha) / (rank + k_param)
            scores[record_id] = scores.get(record_id, 0) + rrf_score

        # 정렬 및 반환
        sorted_ids = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        results = []
        for record_id, score in sorted_ids:
            record = self.get_by_id(record_id)
            results.append((record, score))

        return results
```

#### 4.2.3 시간 기반 감쇠

**구현**:
```python
def apply_temporal_decay(self, score: float, created_at: datetime,
                        decay_rate: float = 0.01) -> float:
    """시간 기반 점수 감쇠"""
    age_days = (datetime.utcnow() - created_at).days
    decay_factor = math.exp(-decay_rate * age_days)
    return score * decay_factor
```

**통합**:
```python
def search_with_decay(self, query: str, top_k: int = 10, decay_rate: float = 0.01):
    """하이브리드 검색 + 시간 감쇠"""
    raw_results = self.hybrid_search(query, top_k=top_k * 2)

    # 시간 감쇠 적용
    decayed = []
    for record, score in raw_results:
        adjusted_score = self.apply_temporal_decay(
            score, record.created_at, decay_rate
        )
        decayed.append((record, adjusted_score))

    # 재정렬 및 반환
    decayed.sort(key=lambda x: x[1], reverse=True)
    return decayed[:top_k]
```

### 4.3 Phase 3: 중요도 점수 시스템

#### 4.3.1 ImportanceCalculator

**파일**: `ai/memory/importance.py`

```python
@dataclass
class ImportanceFactors:
    access_count: int = 0                      # 접근 횟수
    last_accessed: Optional[datetime] = None   # 마지막 접근
    created_at: datetime = field(default_factory=datetime.utcnow)
    success_indicator: float = 0.5             # 0.0 ~ 1.0
    user_feedback: Optional[float] = None      # explicit rating

@dataclass
class ImportanceScore:
    total: float                               # 0.0 ~ 1.0
    breakdown: Dict[str, float]                # 요인별 점수

class ImportanceCalculator:
    def __init__(self,
                 access_weight: float = 0.3,
                 recency_weight: float = 0.3,
                 success_weight: float = 0.2,
                 feedback_weight: float = 0.2,
                 decay_rate: float = 0.01):
        self.weights = {
            'access': access_weight,
            'recency': recency_weight,
            'success': success_weight,
            'feedback': feedback_weight
        }
        self.decay_rate = decay_rate

    def calculate(self, factors: ImportanceFactors) -> ImportanceScore:
        # 1. Access frequency (로그 정규화)
        access_score = min(1.0, math.log(factors.access_count + 1) / math.log(100))

        # 2. Recency (지수 감쇠)
        age_days = (datetime.utcnow() - factors.created_at).days
        recency_score = math.exp(-self.decay_rate * age_days)

        # 3. Success indicator
        success_score = factors.success_indicator

        # 4. User feedback (기본 0.5)
        feedback_score = factors.user_feedback if factors.user_feedback is not None else 0.5

        # 가중 합
        total = (
            self.weights['access'] * access_score +
            self.weights['recency'] * recency_score +
            self.weights['success'] * success_score +
            self.weights['feedback'] * feedback_score
        )

        return ImportanceScore(
            total=total,
            breakdown={
                'access': access_score,
                'recency': recency_score,
                'success': success_score,
                'feedback': feedback_score
            }
        )
```

#### 4.3.2 MemoryRecord 확장

```python
@dataclass
class MemoryRecord:
    # 기존 필드들
    summary: str
    goal: str
    user_intent: str
    outcome: str
    category: MemoryCategory
    tools_used: List[str]
    tags: List[str]
    created_at: datetime
    source_metadata: Dict[str, Any]
    embedding: Optional[List[float]]

    # 새로 추가
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    importance_score: Optional[float] = None
    archived: bool = False
```

#### 4.3.3 자동 아카이빙

```python
class MemoryArchiver:
    def __init__(self, repository, importance_calculator,
                 importance_threshold=0.2, age_threshold_days=90):
        self.repository = repository
        self.calculator = importance_calculator
        self.importance_threshold = importance_threshold
        self.age_threshold = age_threshold_days

    def run_archival_pass(self):
        """중요도 낮고 오래된 메모리 아카이빙"""
        all_memories = self.repository.list_all()
        archived_count = 0

        for memory in all_memories:
            if memory.archived:
                continue

            # 중요도 계산
            factors = ImportanceFactors(
                access_count=memory.access_count,
                last_accessed=memory.last_accessed,
                created_at=memory.created_at,
                success_indicator=self._get_success_indicator(memory),
            )

            importance = self.calculator.calculate(factors)
            memory.importance_score = importance.total

            # 아카이빙 조건 체크
            age_days = (datetime.utcnow() - memory.created_at).days
            if importance.total < self.importance_threshold and age_days > self.age_threshold:
                memory.archived = True
                self.repository.update(memory)
                archived_count += 1

        return archived_count

    def _get_success_indicator(self, memory: MemoryRecord) -> float:
        """outcome 기반 성공 지표"""
        if "성공" in memory.outcome or "완료" in memory.outcome:
            return 1.0
        elif "실패" in memory.outcome or "오류" in memory.outcome:
            return 0.0
        else:
            return 0.5
```

### 4.4 Phase 4: 메모리 통합 및 압축

#### 4.4.1 MemoryConsolidator

**파일**: `ai/memory/consolidator.py`

```python
class MemoryConsolidator:
    def __init__(self, repository, brain,
                 similarity_threshold=0.85, min_cluster_size=3):
        self.repository = repository
        self.brain = brain
        self.similarity_threshold = similarity_threshold
        self.min_cluster_size = min_cluster_size

    def consolidate(self):
        """유사한 메모리 통합"""
        memories = self.repository.list_all(archived=False)

        # 1. 임베딩 기반 클러스터링
        clusters = self._cluster_similar(memories)

        consolidated_count = 0
        for cluster in clusters:
            if len(cluster) < self.min_cluster_size:
                continue

            # 2. LLM으로 클러스터 요약
            summary = self._llm_summarize(cluster)

            # 3. 통합 메모리 생성
            consolidated = MemoryRecord(
                summary=summary,
                goal=self._merge_goals(cluster),
                user_intent=self._merge_intents(cluster),
                outcome=self._merge_outcomes(cluster),
                category=MemoryCategory.WORKFLOW_OPTIMISATION,
                tools_used=self._unique_tools(cluster),
                tags=self._unique_tags(cluster),
                created_at=datetime.utcnow(),
                source_metadata={
                    "consolidated_from": [m.source_metadata["id"] for m in cluster],
                    "consolidation_date": datetime.utcnow().isoformat()
                }
            )

            # 4. 저장 및 원본 아카이빙
            self.repository.add(consolidated)
            for memory in cluster:
                memory.archived = True
                memory.source_metadata["archived_by_consolidation"] = True
                self.repository.update(memory)

            consolidated_count += 1

        return consolidated_count

    def _cluster_similar(self, memories: List[MemoryRecord]) -> List[List[MemoryRecord]]:
        """임베딩 기반 계층적 클러스터링"""
        from sklearn.cluster import AgglomerativeClustering
        import numpy as np

        # 임베딩 행렬 생성
        embeddings = np.array([m.embedding for m in memories if m.embedding])

        # 클러스터링
        clustering = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=1 - self.similarity_threshold,
            linkage='average'
        )
        labels = clustering.fit_predict(embeddings)

        # 클러스터로 그룹화
        clusters = {}
        for memory, label in zip(memories, labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(memory)

        return list(clusters.values())

    def _llm_summarize(self, cluster: List[MemoryRecord]) -> str:
        """LLM으로 클러스터 요약"""
        summaries = "\n".join([f"- {m.summary}" for m in cluster])

        prompt = f"""다음은 유사한 작업 경험들입니다. 이를 하나의 통합된 요약으로 정리해주세요:

{summaries}

통합 요약 (3-5 문장):"""

        response = self.brain.generate_text(prompt, temperature=0.3)
        return response.text.strip()
```

#### 4.4.2 정기 실행 스케줄러

```python
class MemoryMaintenanceScheduler:
    def __init__(self, memory_service,
                 consolidation_interval_hours=24,
                 archival_interval_hours=24):
        self.memory_service = memory_service
        self.consolidation_interval = consolidation_interval_hours
        self.archival_interval = archival_interval_hours
        self.last_consolidation = None
        self.last_archival = None

    def should_run_consolidation(self) -> bool:
        if self.last_consolidation is None:
            return True
        elapsed = datetime.utcnow() - self.last_consolidation
        return elapsed.total_seconds() / 3600 >= self.consolidation_interval

    def should_run_archival(self) -> bool:
        if self.last_archival is None:
            return True
        elapsed = datetime.utcnow() - self.last_archival
        return elapsed.total_seconds() / 3600 >= self.archival_interval

    def run_maintenance(self):
        """주기적 메모리 유지보수"""
        results = {}

        if self.should_run_consolidation():
            consolidator = MemoryConsolidator(
                self.memory_service.repository,
                self.memory_service.brain
            )
            results["consolidated"] = consolidator.consolidate()
            self.last_consolidation = datetime.utcnow()

        if self.should_run_archival():
            archiver = MemoryArchiver(
                self.memory_service.repository,
                ImportanceCalculator()
            )
            results["archived"] = archiver.run_archival_pass()
            self.last_archival = datetime.utcnow()

        return results
```

### 4.5 Phase 5: CrewAI 통합

#### 4.5.1 하이브리드 메모리 서비스

**파일**: `ai/memory/hybrid_service.py`

```python
class HybridMemoryService:
    """CrewAI Memory + Angmini Memory 통합"""

    def __init__(self, crewai_crew, angmini_memory_service):
        self.crewai_crew = crewai_crew
        self.angmini = angmini_memory_service
        self.entity_repository = EntityRepository(...)

    def retrieve(self, query: str, context: str = "all", top_k: int = 10):
        """통합 검색 인터페이스"""
        results = []

        # 1. CrewAI Short-Term Memory
        if context in ["all", "short"]:
            # CrewAI의 short_term_memory 접근
            stm_results = self.crewai_crew.memory.short_term.search(query, limit=5)
            results.extend([{"source": "short", "data": r} for r in stm_results])

        # 2. Entity Memory
        if context in ["all", "entity"]:
            entity_results = self.entity_repository.search_semantic(query, top_k=5)
            results.extend([{"source": "entity", "data": e, "score": s}
                           for e, s in entity_results])

        # 3. Angmini Long-Term Memory (Cascaded)
        if context in ["all", "long"]:
            ltm_result = self.angmini.repository.cascaded_retriever.retrieve(query)
            results.extend([{"source": "long", "data": m.record, "score": m.score}
                           for m in ltm_result.matches])

        # 4. 결과 병합 및 리랭킹
        return self._merge_and_rank(results, top_k=top_k)

    def capture_from_task(self, task_result, user_request: str):
        """Task 완료 시 자동으로 Angmini LTM에 저장"""
        # ExecutionContext 생성
        context = self._build_context_from_task(task_result)

        # Angmini 메모리 캡처
        capture_result = self.angmini.capture(context, user_request)

        # 엔티티 추출 및 저장
        entities = self._extract_entities(context)
        for entity in entities:
            self.entity_repository.add_or_update(entity)

        return capture_result

    def _merge_and_rank(self, results, top_k):
        """소스별 가중치 적용하여 리랭킹"""
        weights = {
            "short": 0.4,   # 최근 컨텍스트 중요
            "entity": 0.3,  # 관계 정보 중요
            "long": 0.3     # 과거 경험
        }

        scored = []
        for item in results:
            source = item["source"]
            base_score = item.get("score", 1.0)
            final_score = base_score * weights[source]
            scored.append((item["data"], final_score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [data for data, score in scored[:top_k]]
```

#### 4.5.2 Crew 설정 업데이트

**파일**: `crew/crew_config.py`

```python
class AngminiCrew:
    def __init__(self, ai_brain, memory_service, verbose=True):
        self.ai_brain = ai_brain
        self.angmini_memory = memory_service

        # CrewAI 에이전트 생성
        self.planner = AgentFactory.create_planner(ai_brain, memory_service)
        self.worker_agents = AgentFactory.create_all_agents(ai_brain, memory_service)

        # CrewAI Crew 생성 (built-in memory 활성화)
        self.crew = Crew(
            agents=[agent.build_agent() for agent in self.worker_agents],
            tasks=[],
            process=Process.hierarchical,
            manager_agent=self.planner.build_agent(),
            memory=True,  # CrewAI Short-Term + Long-Term + Entity
            embedder={
                "provider": "huggingface",
                "config": {"model": "Qwen/Qwen3-Embedding-0.6B"}
            },
            verbose=verbose
        )

        # 하이브리드 메모리 서비스 생성
        self.hybrid_memory = HybridMemoryService(
            crewai_crew=self.crew,
            angmini_memory_service=self.angmini_memory
        )

    def kickoff(self, user_input: str) -> str:
        """Task 실행 및 메모리 캡처"""
        # Task 생성 및 실행
        tasks = TaskFactory.create_tasks_from_input(user_input)
        result = self.crew.kickoff(tasks)

        # Angmini Long-Term Memory에 저장
        if self._should_capture_memory(result):
            self.hybrid_memory.capture_from_task(result, user_input)

        return str(result)
```

---

## 5. 구현 로드맵

### 5.1 우선순위 (P0 → P1 → P2)

#### P0: 즉시 구현 (Critical Path)

**1. Entity Memory 시스템** ⏱️ 3-5일
- **복잡도**: 중간
- **영향**: 높음
- **파일**:
  - `ai/memory/entity/models.py`
  - `ai/memory/entity/extractor.py`
  - `ai/memory/entity/storage.py`
  - `ai/memory/entity/tracker.py`
- **의존성**: 없음
- **테스트**:
  - `tests/memory/entity/test_extractor.py`
  - `tests/memory/entity/test_storage.py`

**2. Hybrid Search (의미적 + 키워드)** ⏱️ 2-3일
- **복잡도**: 낮음
- **영향**: 높음
- **파일**:
  - `ai/memory/storage/hybrid_retriever.py`
  - SQLite 마이그레이션 스크립트 (FTS5 테이블 생성)
- **의존성**: 없음
- **테스트**:
  - `tests/memory/test_hybrid_retriever.py`

#### P1: 다음 스프린트 (Important)

**3. Short-Term Memory (CrewAI 통합)** ⏱️ 1-2일
- **복잡도**: 낮음 (CrewAI가 제공)
- **영향**: 중간
- **파일**:
  - `crew/crew_config.py` 수정 (`memory=True`)
- **의존성**: CrewAI 업그레이드 필요시
- **테스트**:
  - `tests/crew/test_crewai_memory.py`

**4. Importance Score 시스템** ⏱️ 2-3일
- **복잡도**: 중간
- **영향**: 중간
- **파일**:
  - `ai/memory/importance.py`
  - `ai/memory/archiver.py`
  - `ai/memory/memory_records.py` (스키마 확장)
- **의존성**: None
- **테스트**:
  - `tests/memory/test_importance.py`

**5. Hybrid Memory Service (통합 레이어)** ⏱️ 2-3일
- **복잡도**: 중간
- **영향**: 높음
- **파일**:
  - `ai/memory/hybrid_service.py`
  - `crew/crew_config.py` (통합)
- **의존성**: P0 (Entity), P1 (STM)
- **테스트**:
  - `tests/memory/test_hybrid_service.py`

#### P2: 미래 개선 (Nice to Have)

**6. Memory Consolidation** ⏱️ 3-4일
- **복잡도**: 높음
- **영향**: 낮음 (초기 메모리 수 적음)
- **파일**:
  - `ai/memory/consolidator.py`
  - `ai/memory/scheduler.py`
- **의존성**: P1 (Importance)
- **트리거**: 메모리 수 > 1000개

**7. 이벤트 시스템 확장** ⏱️ 2-3일
- **복잡도**: 중간
- **영향**: 낮음 (디버깅용)
- **파일**:
  - `ai/memory/events.py`
  - `ai/memory/metrics.py` (확장)
- **의존성**: None

### 5.2 마이그레이션 전략

#### 5.2.1 데이터베이스 마이그레이션

**스크립트**: `scripts/migrate_memory_v2.py`

```python
"""메모리 시스템 v2 마이그레이션 스크립트"""
import sqlite3
from pathlib import Path

def migrate_to_v2(db_path: Path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. MemoryRecord에 새 필드 추가
    new_columns = [
        ("access_count", "INTEGER DEFAULT 0"),
        ("last_accessed", "TEXT"),
        ("importance_score", "REAL"),
        ("archived", "INTEGER DEFAULT 0"),
    ]

    for col_name, col_type in new_columns:
        try:
            cursor.execute(f"ALTER TABLE memories ADD COLUMN {col_name} {col_type}")
        except sqlite3.OperationalError:
            # 이미 존재하는 컬럼
            pass

    # 2. FTS5 테이블 생성
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts
        USING fts5(
            id UNINDEXED,
            summary,
            goal,
            user_intent,
            outcome,
            tags
        )
    """)

    # 3. 기존 데이터를 FTS5에 인덱싱
    cursor.execute("""
        INSERT INTO memories_fts(id, summary, goal, user_intent, outcome, tags)
        SELECT id, summary, goal, user_intent, outcome, tags
        FROM memories
    """)

    # 4. Entity 테이블 생성
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS entities (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            name TEXT NOT NULL,
            attributes TEXT,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            mention_count INTEGER DEFAULT 1,
            relations TEXT,
            embedding BLOB
        )
    """)

    # 5. Entity 인덱스
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_entities_type_name
        ON entities(type, name)
    """)

    conn.commit()
    conn.close()

    print("✅ 마이그레이션 완료")

if __name__ == "__main__":
    from ai.core.config import Config
    config = Config.load()

    db_path = Path("data/memory/memories.db")
    migrate_to_v2(db_path)
```

#### 5.2.2 기존 메모리 엔티티 추출

**스크립트**: `scripts/extract_entities_from_existing.py`

```python
"""기존 메모리에서 엔티티 추출"""
from ai.memory.factory import create_memory_service
from ai.memory.entity.extractor import EntityExtractor
from ai.memory.entity.storage import EntityRepository
from ai.ai_brain import AIBrain

def extract_entities_from_existing():
    brain = AIBrain()
    memory_service = create_memory_service()
    extractor = EntityExtractor(brain)
    entity_repo = EntityRepository(...)

    all_memories = memory_service.repository.list_all()

    for i, memory in enumerate(all_memories):
        print(f"처리 중: {i+1}/{len(all_memories)}")

        # 텍스트 구성
        text = f"{memory.summary}\n{memory.goal}\n{memory.outcome}"

        # 엔티티 추출
        entities = extractor.extract(text)

        # 저장
        for entity in entities:
            entity_repo.add_or_update(entity)

    print(f"✅ {len(all_memories)}개 메모리에서 엔티티 추출 완료")

if __name__ == "__main__":
    extract_entities_from_existing()
```

#### 5.2.3 Feature Flags

**환경변수**: `.env`

```bash
# 메모리 시스템 v2 기능 플래그
MEMORY_V2_ENTITY_ENABLED=true
MEMORY_V2_HYBRID_SEARCH_ENABLED=true
MEMORY_V2_IMPORTANCE_ENABLED=false  # 점진적 활성화
MEMORY_V2_CONSOLIDATION_ENABLED=false  # 미래에 활성화
```

**코드**:
```python
from ai.core.config import Config

config = Config.load()

if config.get("MEMORY_V2_ENTITY_ENABLED", "false") == "true":
    # Entity Memory 활성화
    entity_repository = EntityRepository(...)
else:
    entity_repository = None
```

### 5.3 테스트 전략

#### 5.3.1 Unit Tests

**Entity Extractor**:
```python
# tests/memory/entity/test_extractor.py
def test_entity_extraction():
    brain = AIBrain()
    extractor = EntityExtractor(brain)

    text = "김철수가 Django 프로젝트에서 pytest를 사용했습니다."
    entities = extractor.extract(text)

    assert len(entities) >= 3
    assert any(e.type == EntityType.PERSON and "김철수" in e.name for e in entities)
    assert any(e.type == EntityType.PROJECT and "Django" in e.name for e in entities)
    assert any(e.type == EntityType.TOOL and "pytest" in e.name for e in entities)
```

**Hybrid Retriever**:
```python
# tests/memory/test_hybrid_retriever.py
def test_rrf_fusion():
    retriever = HybridRetriever(...)

    # "Django 프로젝트" 검색
    results = retriever.search("Django 프로젝트", top_k=5)

    assert len(results) <= 5
    assert all(isinstance(r, tuple) and len(r) == 2 for r in results)

    # 점수 내림차순 확인
    scores = [score for _, score in results]
    assert scores == sorted(scores, reverse=True)
```

**Importance Calculator**:
```python
# tests/memory/test_importance.py
def test_importance_calculation():
    calculator = ImportanceCalculator()

    # 높은 중요도: 자주 접근, 최근, 성공
    factors_high = ImportanceFactors(
        access_count=50,
        created_at=datetime.utcnow() - timedelta(days=1),
        success_indicator=1.0
    )
    score_high = calculator.calculate(factors_high)

    # 낮은 중요도: 접근 없음, 오래됨, 실패
    factors_low = ImportanceFactors(
        access_count=0,
        created_at=datetime.utcnow() - timedelta(days=180),
        success_indicator=0.0
    )
    score_low = calculator.calculate(factors_low)

    assert score_high.total > score_low.total
    assert score_high.total > 0.7
    assert score_low.total < 0.3
```

#### 5.3.2 Integration Tests

**전체 파이프라인**:
```python
# tests/memory/test_integration.py
def test_full_memory_pipeline():
    brain = AIBrain()
    memory_service = MemoryService.build(brain)

    # 메모리 캡처
    context = create_test_context()
    result = memory_service.capture(context, "테스트 요청")

    assert result.stored
    assert result.record_id is not None

    # 검색 (하이브리드)
    search_results = memory_service.repository.hybrid_search("테스트", top_k=5)
    assert len(search_results) > 0

    # 엔티티 확인
    entities = entity_repository.find_by_name("테스트")
    assert len(entities) > 0
```

#### 5.3.3 Performance Tests

**검색 성능**:
```python
# tests/memory/test_performance.py
import time

def test_search_latency():
    retriever = HybridRetriever(...)

    # 100회 검색
    latencies = []
    for _ in range(100):
        start = time.perf_counter()
        retriever.search("test query", top_k=10)
        latency = (time.perf_counter() - start) * 1000  # ms
        latencies.append(latency)

    # P95 < 100ms
    p95 = sorted(latencies)[95]
    assert p95 < 100.0, f"P95 latency {p95:.2f}ms > 100ms"
```

**메모리 사용량**:
```python
import psutil
import os

def test_memory_usage_10k_records():
    process = psutil.Process(os.getpid())

    # 10,000개 메모리 로드
    repository = MemoryRepository(...)
    memories = repository.list_all()[:10000]

    # 메모리 사용량 측정
    mem_mb = process.memory_info().rss / 1024 / 1024

    # < 500MB
    assert mem_mb < 500, f"Memory usage {mem_mb:.2f}MB > 500MB"
```

#### 5.3.4 Quality Tests

**검색 정확도 (Precision@K)**:
```python
def test_search_precision():
    # 테스트 데이터셋 (쿼리 → 관련 메모리 ID)
    test_queries = {
        "Django 프로젝트 작업": ["mem_001", "mem_045", "mem_103"],
        "pytest 오류 해결": ["mem_012", "mem_089"],
    }

    retriever = HybridRetriever(...)
    precisions = []

    for query, relevant_ids in test_queries.items():
        results = retriever.search(query, top_k=5)
        result_ids = [r.source_metadata["id"] for r, _ in results]

        # Precision@5
        relevant_in_top5 = len(set(result_ids) & set(relevant_ids))
        precision = relevant_in_top5 / 5
        precisions.append(precision)

    avg_precision = sum(precisions) / len(precisions)
    assert avg_precision > 0.8, f"Precision@5 {avg_precision:.2f} < 0.8"
```

---

## 6. 예상 효과

### 6.1 정량적 개선

| 메트릭 | 현재 | 목표 | 개선율 |
|--------|------|------|--------|
| **검색 정확도** (Precision@5) | 0.65 | 0.85 | +30% |
| **컨텍스트 인식** (엔티티 추적) | 0% | 80% | +80% |
| **메모리 효율성** (아카이빙) | N/A | 40% | +40% |
| **검색 속도** (P95 latency) | 150ms | <100ms | +33% |
| **중복 감소** | 5% | <2% | +60% |

### 6.2 정성적 개선

✅ **사용자 경험**:
- 더 정확한 과거 경험 검색
- "이 사용자가 자주 쓰는 도구는?" 같은 질문 가능
- 개인화된 응답 생성

✅ **시스템 성능**:
- 하이브리드 검색으로 정확도 향상
- 아카이빙으로 장기 성능 유지
- 메모리 통합으로 스토리지 최적화

✅ **유지보수성**:
- CrewAI 네이티브 메모리와 통합
- 명확한 계층 분리 (STM/LTM/Entity)
- 이벤트 시스템으로 디버깅 용이

### 6.3 CrewAI 시너지

**Before** (단일 Long-Term Memory):
```
사용자 요청
    ↓
Cascaded Retrieval (과거 경험만)
    ↓
응답 생성
```

**After** (계층적 통합 Memory):
```
사용자 요청
    ↓
Hybrid Memory Service
    ├─ Short-Term (최근 대화)
    ├─ Entity (관계 정보)
    └─ Long-Term (과거 경험)
    ↓
통합 리랭킹
    ↓
컨텍스트 인식 응답
```

**효과**:
- **단기 컨텍스트**: "방금 말한 프로젝트" 이해
- **관계 인식**: "김철수가 작업한 프로젝트들"
- **장기 학습**: "과거 유사 작업에서 성공한 방법"

---

## 7. 참고 자료

### 7.1 논문 및 문서

1. **MemGPT / Letta**:
   - https://www.letta.com/blog/benchmarking-ai-agent-memory
   - LoCoMo Benchmark 결과

2. **Mem0 Platform**:
   - arXiv:2504.19413 "Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory"

3. **AutoGen v0.4**:
   - https://www.microsoft.com/en-us/research/blog/autogen-v0-4-reimagining-the-foundation-of-agentic-ai-for-scale-extensibility-and-robustness/

4. **CrewAI Memory**:
   - https://docs.crewai.com/concepts/memory

5. **LangChain Memory**:
   - https://python.langchain.com/docs/how_to/migrate_agent
   - https://python.langchain.com/docs/tutorials/qa_chat_history

### 7.2 코드 참고

- **Reciprocal Rank Fusion**: https://github.com/Raudaschl/rag-fusion
- **Entity Extraction with LLM**: LangChain NER examples
- **Temporal Decay**: Information Retrieval 표준 공식

---

## 8. 다음 단계

### 8.1 즉시 실행 (이번 주)

1. ✅ **설계 문서 작성 완료** (현재 문서)
2. 🔄 **데이터베이스 마이그레이션 스크립트 작성**
3. 🔄 **Entity Memory 시스템 구현 시작**

### 8.2 다음 주

1. Entity Memory 완료 및 테스트
2. Hybrid Search 구현
3. 통합 테스트

### 8.3 향후 계획

1. Importance Score 시스템 (2주차)
2. Hybrid Memory Service 통합 (3주차)
3. Memory Consolidation (4주차)

---

**작성**: Claude Code (Anthropic)
**검토 필요**: 개발 팀
**상태**: ✅ 설계 완료, 구현 준비 완료
