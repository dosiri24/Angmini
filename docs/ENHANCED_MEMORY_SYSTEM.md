# Enhanced Memory System - User Guide

## Overview

Angmini's enhanced memory system incorporates cutting-edge AI agent memory algorithms inspired by MemGPT/Letta, AutoGen v0.4, and Mem0. The system provides:

1. **Entity Memory**: Track people, projects, tools, concepts, and files across conversations
2. **Hybrid Search**: Combine semantic (vector) and keyword (FTS5) search using Reciprocal Rank Fusion
3. **Importance Scoring**: Multi-factor scoring based on frequency, recency, success, feedback, and entity richness
4. **Graph Relationships**: Track relationships between entities for context-aware retrieval

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Enhanced Memory Service                    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌────────────────┐  ┌──────────────────┐  ┌──────────────┐│
│  │ Entity Tracker │  │ Hybrid Retriever │  │   Importance ││
│  │                │  │                  │  │     Scorer   ││
│  │  - LLM-based  │  │  - Vector (FAISS)│  │              ││
│  │    NER        │  │  - Keyword (FTS5)│  │  - Frequency ││
│  │  - Graph      │  │  - RRF Fusion    │  │  - Recency   ││
│  │    Relations  │  │                  │  │  - Success   ││
│  └────────────────┘  └──────────────────┘  └──────────────┘│
│                                                               │
├─────────────────────────────────────────────────────────────┤
│               Core Memory System (Existing)                   │
│  - MemoryRepository (SQLite + FAISS + Qwen3)                │
│  - MemoryCurator (LLM-based summarization)                  │
│  - CascadedRetriever (Multi-hop search)                     │
└─────────────────────────────────────────────────────────────┘
```

## Installation & Migration

### 1. Database Migration

Before using the enhanced features, run the migration to add new tables:

```bash
# Check migration status
python scripts/migrate_memory_v2.py --check-only

# Run migration (creates backup automatically)
python scripts/migrate_memory_v2.py

# Run migration without backup
python scripts/migrate_memory_v2.py --skip-backup
```

**New Tables Created:**
- `entities` - Stores extracted entities with embeddings
- `entity_relations` - Tracks relationships between entities
- `memory_entities` - Links memories to entities
- `memories_fts` - FTS5 full-text search index
- `memory_access_log` - Tracks memory access patterns
- `memory_feedback` - Stores user feedback ratings

### 2. Test Installation

```bash
# Run comprehensive test suite
python scripts/test_enhanced_memory.py

# Expected output:
# ✅ Test 0 PASSED: Migration Status
# ✅ Test 1 PASSED: Entity Extraction
# ✅ Test 2 PASSED: Hybrid Search
# ✅ Test 3 PASSED: Importance Scoring
# ✅ Test 4 PASSED: Enhanced Service
# 🎉 All tests passed!
```

## Usage Examples

### Basic Usage (Automatic)

The enhanced memory system is automatically integrated when you create a `MemoryService`:

```python
from ai.memory.factory import create_enhanced_memory_service

# Create service with all features enabled
service = create_enhanced_memory_service(
    enable_entity_tracking=True,
    enable_hybrid_search=True,
    enable_importance_scoring=True,
)

# Access components
entity_tracker = service.entity_tracker
hybrid_retriever = service.hybrid_retriever
importance_scorer = service.importance_scorer
```

### Entity Memory

#### 1. Extract Entities from Memory

```python
from ai.memory.factory import create_entity_tracker

tracker = create_entity_tracker()

# Sample memory record
memory_dict = {
    "summary": "User implemented Entity Memory system using CrewAI",
    "goal": "Add entity tracking to memory",
    "user_intent": "Enhance memory with entity extraction",
    "outcome": "Successfully implemented EntityTracker and EntityRepository",
    "tools_used": ["file_tool", "notion_tool"],
    "tags": ["memory", "enhancement"],
    "category": "workflow_optimisation",
}

# Track entities
entities, relations = tracker.track_memory("memory_001", memory_dict)

# Output:
# entities = [
#     Entity(type=TOOL, name="CrewAI", ...),
#     Entity(type=CONCEPT, name="Entity Memory", ...),
#     Entity(type=PERSON, name="User", ...),
# ]
# relations = [
#     EntityRelation(source="User", target="Entity Memory", type=IMPLEMENTS),
#     EntityRelation(source="Entity Memory", target="CrewAI", type=USES),
# ]
```

#### 2. Search Entities

```python
# Search by name
results = tracker.search_entities("CrewAI", fuzzy=False)

# Search by type
from ai.memory.entity import EntityType
tools = tracker.get_entities_by_type(EntityType.TOOL, limit=10)

# Get entity context (with relations)
context = tracker.get_entity_context("tool_crewai_abc123", depth=2)

# Output:
# {
#     "entity": Entity(...),
#     "related_entities": [Entity(...), Entity(...)],
#     "memory_count": 5,
#     "recent_memories": [("memory_001", 0.95), ...],
#     "mention_count": 15,
#     "last_seen": datetime(...)
# }
```

#### 3. Entity Statistics

```python
stats = tracker.get_statistics()

# Output:
# {
#     "total_entities": 142,
#     "by_type": {
#         "person": 8,
#         "project": 12,
#         "tool": 45,
#         "concept": 53,
#         "file": 24
#     }
# }
```

### Hybrid Search

#### 1. Basic Hybrid Search

```python
from ai.memory.factory import create_hybrid_retriever

retriever = create_hybrid_retriever(
    vector_weight=0.6,  # 60% semantic search
    keyword_weight=0.4,  # 40% keyword search
)

# Perform search
results = retriever.search("entity memory implementation", top_k=10)

# Results are ranked by RRF score
for result in results:
    print(f"Score: {result.rrf_score:.3f}")
    print(f"  Vector: {result.vector_score:.3f}")
    print(f"  Keyword: {result.keyword_score:.3f}")
    print(f"  Summary: {result.record.summary}")
```

#### 2. Advanced Search Options

```python
# Search with minimum score threshold
results = retriever.search(
    query="CrewAI memory",
    top_k=5,
    min_rrf_score=0.3,  # Only results with RRF score >= 0.3
)

# Custom retrieval counts
results = retriever.search(
    query="entity tracking",
    top_k=10,
    vector_k=20,  # Fetch top 20 from vector search
    keyword_k=30,  # Fetch top 30 from keyword search
)

# Get retriever statistics
stats = retriever.get_statistics()
# {
#     "vector_weight": 0.6,
#     "keyword_weight": 0.4,
#     "rrf_k": 60,
#     "fts_indexed_memories": 1245,
#     "vector_index_size": 1245
# }
```

### Importance Scoring

#### 1. Calculate Importance

```python
from ai.memory.factory import create_importance_scorer

scorer = create_importance_scorer(
    frequency_weight=0.25,
    recency_weight=0.25,
    success_weight=0.20,
    feedback_weight=0.15,
    entity_weight=0.15,
)

# Calculate score for a memory
score = scorer.calculate_importance("memory_001")

# Output:
# ImportanceScore(
#     total_score=0.742,
#     frequency_score=0.65,  # Accessed frequently
#     recency_score=0.85,    # Recently accessed
#     success_score=0.70,    # Positive outcome
#     feedback_score=0.90,   # High user rating
#     entity_score=0.60      # Rich entity connections
# )
```

#### 2. Track Access Patterns

```python
# Record memory access
scorer.record_access("memory_001", access_type="retrieval")

# Record user feedback
scorer.record_feedback(
    "memory_001",
    rating=0.9,  # 0.0-1.0 scale
    comment="Very helpful for implementation"
)
```

#### 3. Get Most Important Memories

```python
# Get top memories overall
top_memories = scorer.get_top_memories(limit=10)

for memory_id, score in top_memories:
    print(f"{memory_id}: {score.total_score:.3f}")

# Get top memories by category
top_workflows = scorer.get_top_memories(
    limit=5,
    category="workflow_optimisation"
)
```

## Component Details

### Entity Types

```python
from ai.memory.entity import EntityType

EntityType.PERSON      # Users, collaborators, team members
EntityType.PROJECT     # Code projects, repositories
EntityType.TOOL        # Software tools, libraries, frameworks
EntityType.CONCEPT     # Algorithms, patterns, ideas
EntityType.FILE        # Specific files, modules
```

### Relation Types

```python
from ai.memory.entity import RelationType

# Collaboration
RelationType.COLLABORATES_WITH  # person <-> person
RelationType.WORKS_ON          # person -> project
RelationType.MAINTAINS         # person -> tool/project

# Dependencies
RelationType.DEPENDS_ON        # project -> tool, file -> file
RelationType.USES              # project -> tool
RelationType.IMPORTS           # file -> file

# Hierarchy
RelationType.BELONGS_TO        # file -> project
RelationType.CONTAINS          # project -> file
RelationType.PART_OF           # concept -> concept

# Semantics
RelationType.RELATED_TO        # concept <-> concept
RelationType.IMPLEMENTS        # file -> concept
RelationType.DISCUSSES         # any -> concept
```

### Hybrid Search Algorithm

The Reciprocal Rank Fusion (RRF) algorithm merges vector and keyword results:

```
RRF_score(item) = Σ [ weight_i / (k + rank_i) ]

where:
- weight_i: Weight for each search method (vector/keyword)
- k: RRF constant (default 60)
- rank_i: Rank in each result list (1-indexed)
```

### Importance Scoring Formula

```
Total_Score =
    0.25 × Frequency_Score +
    0.25 × Recency_Score +
    0.20 × Success_Score +
    0.15 × Feedback_Score +
    0.15 × Entity_Score

where:
- Frequency: log(1 + access_count) / log(1 + 100)
- Recency: 2^(-age_days / 30)  (exponential decay)
- Success: Based on category and tags
- Feedback: User rating (0.0-1.0)
- Entity: log(1 + entity_count) / log(1 + 10)
```

## Integration with Existing System

### Memory Capture with Entity Tracking

The entity tracker is automatically called during memory capture:

```python
# In ai/memory/service.py
def capture(self, context, user_request: str):
    # ... existing capture logic ...

    # Entity tracking (if enabled)
    if hasattr(self, 'entity_tracker') and self.entity_tracker:
        memory_id = curated_record.source_metadata.get("id")
        memory_dict = curated_record.to_document()
        entities, relations = self.entity_tracker.track_memory(
            memory_id,
            memory_dict
        )
        logger.info(f"Tracked {len(entities)} entities")

    return result
```

### Retrieval with Hybrid Search

```python
# In ai/memory/service.py
def search(self, query: str, top_k: int = 5):
    # Use hybrid search if available
    if hasattr(self, 'hybrid_retriever') and self.hybrid_retriever:
        results = self.hybrid_retriever.search(query, top_k=top_k)
        return [r.record for r in results]

    # Fallback to vector-only search
    return self._repository.search(query, top_k=top_k)
```

## Performance Considerations

### Entity Extraction

- **LLM-based**: Uses Gemini for accurate entity extraction (~2-5 seconds per memory)
- **Fallback**: Rule-based extraction for files and known tools (~100ms)
- **Caching**: Entities are stored in SQLite with embeddings for fast retrieval

### Hybrid Search

- **Vector Search**: FAISS index (~5-20ms for top-k retrieval)
- **Keyword Search**: SQLite FTS5 index (~10-30ms)
- **RRF Fusion**: O(n) merge algorithm (~1-5ms)
- **Total**: ~20-60ms for hybrid search

### Importance Scoring

- **Score Calculation**: ~5-10ms per memory (SQLite queries)
- **Access Logging**: ~1-2ms per access event
- **Batch Scoring**: Parallelizable for large memory sets

## Troubleshooting

### Migration Issues

**Issue**: Migration script fails with "table already exists"
```bash
# Solution: Check existing tables
python scripts/migrate_memory_v2.py --check-only

# Drop and recreate (WARNING: Data loss)
rm data/memory/memories.db
python scripts/migrate_memory_v2.py
```

### Entity Extraction Failures

**Issue**: No entities extracted from memory
- Check Gemini API key is configured
- Review LLM prompt in `entity/extractor.py`
- Enable fallback rule-based extraction

### Hybrid Search Returns No Results

**Issue**: FTS5 index is empty
```python
# Rebuild FTS5 index
import sqlite3
conn = sqlite3.connect("data/memory/memories.db")
conn.execute("DELETE FROM memories_fts")
conn.execute("""
    INSERT INTO memories_fts(rowid, external_id, summary, goal, user_intent, outcome, tags)
    SELECT id, external_id, summary, goal, user_intent, outcome, tags
    FROM memories
""")
conn.commit()
```

## Configuration

### Environment Variables

```bash
# Memory database path (default: data/memory/memories.db)
export MEMORY_STORE_PATH="path/to/custom/memories.db"

# FAISS index path (default: data/memory/memory.index)
export MEMORY_INDEX_PATH="path/to/custom/memory.index"

# Embedding instruction
export MEMORY_EMBED_INSTRUCTION="Custom instruction for embeddings"
```

### Feature Flags

```python
# Disable specific features
service = create_enhanced_memory_service(
    enable_entity_tracking=False,   # Disable entity memory
    enable_hybrid_search=False,     # Use vector-only search
    enable_importance_scoring=False # No importance tracking
)
```

## Next Steps

1. **Explore Entity Graphs**: Visualize entity relationships using graph libraries
2. **Custom Entity Types**: Extend `EntityType` enum for domain-specific entities
3. **Feedback Collection**: Integrate user feedback into the system via UI/CLI
4. **Memory Consolidation**: Implement clustering and summarization (P2 feature)
5. **CrewAI Integration**: Use CrewAI's Short-Term Memory alongside custom LTM (P1 feature)

## References

- Design Document: `claudedocs/memory_system_enhancement.md`
- Migration Script: `scripts/migrate_memory_v2.py`
- Test Suite: `scripts/test_enhanced_memory.py`
- Implementation: `ai/memory/entity/`, `ai/memory/hybrid_retriever.py`, `ai/memory/importance_scorer.py`

## Support

For issues or questions:
1. Check migration status: `python scripts/migrate_memory_v2.py --check-only`
2. Run test suite: `python scripts/test_enhanced_memory.py`
3. Review logs: `logs/YYYYMMDD_HHMMSS.log`
4. Consult design document: `claudedocs/memory_system_enhancement.md`
