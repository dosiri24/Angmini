#!/usr/bin/env python3
"""Test script for enhanced memory system.

Tests:
1. Entity extraction from sample memory
2. Entity storage and retrieval
3. Hybrid search (vector + keyword)
4. Importance scoring
5. Integration with memory capture
"""

import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ai.core.config import Config
from ai.core.logger import get_logger
from ai.memory.factory import (
    create_entity_tracker,
    create_hybrid_retriever,
    create_importance_scorer,
    create_enhanced_memory_service,
)
from ai.memory.memory_records import MemoryCategory

logger = get_logger("EnhancedMemoryTest")


def test_entity_extraction():
    """Test 1: Entity extraction from sample memory."""
    logger.info("=" * 60)
    logger.info("Test 1: Entity Extraction")
    logger.info("=" * 60)

    try:
        tracker = create_entity_tracker()

        # Sample memory dict
        sample_memory = {
            "summary": "User requested to implement Entity Memory system using CrewAI framework",
            "goal": "Add entity tracking to Angmini memory system",
            "user_intent": "Enhance memory with entity extraction",
            "outcome": "Successfully implemented EntityTracker, EntityRepository, and EntityExtractor classes",
            "tools_used": ["file_tool", "notion_tool"],
            "tags": ["memory", "enhancement", "entity"],
            "category": "workflow_optimisation",
        }

        memory_id = "test_memory_001"

        # Track entities
        entities, relations = tracker.track_memory(memory_id, sample_memory)

        logger.info(f"✅ Extracted {len(entities)} entities:")
        for entity in entities:
            logger.info(f"   - {entity.type.value}: {entity.name}")

        logger.info(f"✅ Extracted {len(relations)} relations:")
        for relation in relations:
            logger.info(f"   - {relation.source_entity_id} -{relation.relation_type.value}-> {relation.target_entity_id}")

        # Search for entity
        search_results = tracker.search_entities("CrewAI", fuzzy=False)
        logger.info(f"✅ Search for 'CrewAI': {len(search_results)} results")

        logger.info("✅ Test 1 PASSED\n")
        return True

    except Exception as e:
        logger.error(f"❌ Test 1 FAILED: {e}", exc_info=True)
        return False


def test_hybrid_search():
    """Test 2: Hybrid search combining vector and keyword."""
    logger.info("=" * 60)
    logger.info("Test 2: Hybrid Search")
    logger.info("=" * 60)

    try:
        retriever = create_hybrid_retriever(
            vector_weight=0.6,
            keyword_weight=0.4,
        )

        # Test query
        query = "entity memory implementation"

        # Perform hybrid search
        results = retriever.search(query, top_k=5)

        logger.info(f"✅ Hybrid search for '{query}': {len(results)} results")
        for i, result in enumerate(results, 1):
            logger.info(
                f"   {i}. RRF={result.rrf_score:.3f} "
                f"(V={result.vector_score:.3f}, K={result.keyword_score:.3f})"
            )

        # Get statistics
        stats = retriever.get_statistics()
        logger.info(f"✅ Retriever stats: {stats}")

        logger.info("✅ Test 2 PASSED\n")
        return True

    except Exception as e:
        logger.error(f"❌ Test 2 FAILED: {e}", exc_info=True)
        return False


def test_importance_scoring():
    """Test 3: Importance scoring for memories."""
    logger.info("=" * 60)
    logger.info("Test 3: Importance Scoring")
    logger.info("=" * 60)

    try:
        scorer = create_importance_scorer()

        # Record some access events
        test_memory_id = "test_memory_001"

        for _ in range(5):
            scorer.record_access(test_memory_id, access_type="retrieval")

        # Record feedback
        scorer.record_feedback(test_memory_id, rating=0.9, comment="Very useful")

        # Calculate importance
        score = scorer.calculate_importance(test_memory_id)

        logger.info(f"✅ Importance score for {test_memory_id}:")
        logger.info(f"   Total: {score.total_score:.3f}")
        logger.info(f"   Frequency: {score.frequency_score:.3f}")
        logger.info(f"   Recency: {score.recency_score:.3f}")
        logger.info(f"   Success: {score.success_score:.3f}")
        logger.info(f"   Feedback: {score.feedback_score:.3f}")
        logger.info(f"   Entity: {score.entity_score:.3f}")

        # Get top memories
        top_memories = scorer.get_top_memories(limit=5)
        logger.info(f"✅ Top {len(top_memories)} most important memories")

        logger.info("✅ Test 3 PASSED\n")
        return True

    except Exception as e:
        logger.error(f"❌ Test 3 FAILED: {e}", exc_info=True)
        return False


def test_enhanced_service():
    """Test 4: Enhanced memory service integration."""
    logger.info("=" * 60)
    logger.info("Test 4: Enhanced Memory Service")
    logger.info("=" * 60)

    try:
        # Create enhanced service with all features
        service = create_enhanced_memory_service(
            enable_entity_tracking=True,
            enable_hybrid_search=True,
            enable_importance_scoring=True,
        )

        logger.info("✅ Enhanced memory service created with:")
        logger.info(f"   - Entity tracker: {service.entity_tracker is not None}")
        logger.info(f"   - Hybrid retriever: {service.hybrid_retriever is not None}")
        logger.info(f"   - Importance scorer: {service.importance_scorer is not None}")

        # Test entity tracking integration
        if service.entity_tracker:
            stats = service.entity_tracker.get_statistics()
            logger.info(f"   - Entity stats: {stats}")

        # Test hybrid search integration
        if service.hybrid_retriever:
            hybrid_stats = service.hybrid_retriever.get_statistics()
            logger.info(f"   - Hybrid retriever indexed: {hybrid_stats.get('fts_indexed_memories', 0)} memories")

        logger.info("✅ Test 4 PASSED\n")
        return True

    except Exception as e:
        logger.error(f"❌ Test 4 FAILED: {e}", exc_info=True)
        return False


def test_migration_status():
    """Test 0: Check migration status."""
    logger.info("=" * 60)
    logger.info("Test 0: Migration Status Check")
    logger.info("=" * 60)

    try:
        import sqlite3
        from ai.memory.factory import Path, os, MEMORY_DB_ENV

        db_path = Path(os.getenv(MEMORY_DB_ENV, "data/memory/memories.db"))

        if not db_path.exists():
            logger.warning("⚠️  Database does not exist yet - will be created on first use")
            return True

        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = {row[0] for row in cursor}

            required_tables = {
                'memories', 'entities', 'entity_relations',
                'memory_entities', 'memories_fts',
                'memory_access_log', 'memory_feedback'
            }

            missing = required_tables - tables
            if missing:
                logger.error(f"❌ Missing tables: {missing}")
                logger.error("Run: python scripts/migrate_memory_v2.py")
                return False
            else:
                logger.info(f"✅ All required tables present: {sorted(required_tables)}")

                # Count entities
                cursor = conn.execute("SELECT COUNT(*) FROM entities")
                entity_count = cursor.fetchone()[0]
                logger.info(f"✅ Entities in database: {entity_count}")

                # Count FTS indexed memories
                cursor = conn.execute("SELECT COUNT(*) FROM memories_fts")
                fts_count = cursor.fetchone()[0]
                logger.info(f"✅ FTS-indexed memories: {fts_count}")

        logger.info("✅ Test 0 PASSED\n")
        return True

    except Exception as e:
        logger.error(f"❌ Test 0 FAILED: {e}", exc_info=True)
        return False


def main():
    """Run all tests."""
    logger.info("🚀 Enhanced Memory System Test Suite\n")

    tests = [
        ("Migration Status", test_migration_status),
        ("Entity Extraction", test_entity_extraction),
        ("Hybrid Search", test_hybrid_search),
        ("Importance Scoring", test_importance_scoring),
        ("Enhanced Service", test_enhanced_service),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            logger.error(f"Test '{test_name}' raised exception: {e}", exc_info=True)
            results.append((test_name, False))

    # Summary
    logger.info("=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"{status}: {test_name}")

    logger.info(f"\nTotal: {passed_count}/{total_count} tests passed")

    if passed_count == total_count:
        logger.info("🎉 All tests passed!")
        return 0
    else:
        logger.error(f"❌ {total_count - passed_count} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
