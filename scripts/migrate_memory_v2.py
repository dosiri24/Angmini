#!/usr/bin/env python3
"""Database migration script for Entity Memory system.

This script adds Entity Memory tables to the existing SQLite database:
- entities: Stores extracted entities (people, projects, tools, concepts, files)
- entity_relations: Tracks relationships between entities
- memory_entities: Links memories to entities with relevance scores
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ai.core.config import Config
from ai.core.logger import get_logger

logger = get_logger("MemoryMigration")

# Migration schema for Entity Memory
ENTITY_SCHEMA = """
-- Entity table: Stores extracted entities
CREATE TABLE IF NOT EXISTS entities (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,  -- person, project, tool, concept, file
    name TEXT NOT NULL,
    attributes TEXT NOT NULL,  -- JSON object
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    mention_count INTEGER DEFAULT 1,
    embedding TEXT,  -- JSON array of floats
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type);
CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);
CREATE INDEX IF NOT EXISTS idx_entities_last_seen ON entities(last_seen DESC);

-- Entity relations table: Tracks relationships between entities
CREATE TABLE IF NOT EXISTS entity_relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_entity_id TEXT NOT NULL,
    target_entity_id TEXT NOT NULL,
    relation_type TEXT NOT NULL,  -- collaborates_with, depends_on, belongs_to, etc.
    context TEXT,  -- Optional context about the relationship
    created_at TEXT NOT NULL,
    FOREIGN KEY (source_entity_id) REFERENCES entities(id) ON DELETE CASCADE,
    FOREIGN KEY (target_entity_id) REFERENCES entities(id) ON DELETE CASCADE,
    UNIQUE(source_entity_id, target_entity_id, relation_type)
);

CREATE INDEX IF NOT EXISTS idx_entity_relations_source ON entity_relations(source_entity_id);
CREATE INDEX IF NOT EXISTS idx_entity_relations_target ON entity_relations(target_entity_id);

-- Memory-Entity linking table: Links memories to entities
CREATE TABLE IF NOT EXISTS memory_entities (
    memory_id TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    relevance_score REAL DEFAULT 1.0,
    created_at TEXT NOT NULL,
    PRIMARY KEY (memory_id, entity_id),
    FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_memory_entities_memory ON memory_entities(memory_id);
CREATE INDEX IF NOT EXISTS idx_memory_entities_entity ON memory_entities(entity_id);

-- Full-text search for memories (for hybrid search)
CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    external_id UNINDEXED,
    summary,
    goal,
    user_intent,
    outcome,
    tags,
    content='memories',
    content_rowid='id'
);

-- Triggers to keep FTS index in sync
CREATE TRIGGER IF NOT EXISTS memories_fts_insert AFTER INSERT ON memories BEGIN
    INSERT INTO memories_fts(rowid, external_id, summary, goal, user_intent, outcome, tags)
    VALUES (new.id, new.external_id, new.summary, new.goal, new.user_intent, new.outcome, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS memories_fts_update AFTER UPDATE ON memories BEGIN
    UPDATE memories_fts SET
        external_id = new.external_id,
        summary = new.summary,
        goal = new.goal,
        user_intent = new.user_intent,
        outcome = new.outcome,
        tags = new.tags
    WHERE rowid = new.id;
END;

CREATE TRIGGER IF NOT EXISTS memories_fts_delete AFTER DELETE ON memories BEGIN
    DELETE FROM memories_fts WHERE rowid = old.id;
END;
"""


def get_database_path() -> Path:
    """Get the database path from config or use default."""
    try:
        config = Config.load()
        # Memory database is typically in data/memory/memories.db
        db_path = project_root / "data" / "memory" / "memories.db"
        return db_path
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        # Fallback to default path
        return project_root / "data" / "memory" / "memories.db"


def check_existing_tables(conn: sqlite3.Connection) -> dict:
    """Check which tables already exist."""
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )
    existing_tables = {row[0] for row in cursor}

    required_tables = {
        'memories', 'entities', 'entity_relations',
        'memory_entities', 'memories_fts'
    }

    return {
        'existing': existing_tables,
        'required': required_tables,
        'missing': required_tables - existing_tables
    }


def backup_database(db_path: Path) -> Path:
    """Create a backup of the database before migration."""
    if not db_path.exists():
        logger.info(f"No existing database at {db_path}, skipping backup")
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.parent / f"{db_path.stem}_backup_{timestamp}.db"

    import shutil
    shutil.copy2(db_path, backup_path)
    logger.info(f"Database backed up to: {backup_path}")
    return backup_path


def run_migration(db_path: Path, skip_backup: bool = False) -> bool:
    """Run the database migration."""
    try:
        # Create backup unless skipped
        if not skip_backup:
            backup_database(db_path)

        # Ensure directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # Connect and check existing schema
        with sqlite3.connect(db_path) as conn:
            table_status = check_existing_tables(conn)

            logger.info(f"Existing tables: {sorted(table_status['existing'])}")
            logger.info(f"Missing tables: {sorted(table_status['missing'])}")

            if not table_status['missing']:
                logger.info("All required tables already exist. Migration not needed.")
                return True

            # Run migration
            logger.info("Running Entity Memory migration...")
            conn.executescript(ENTITY_SCHEMA)
            conn.commit()

            # Verify migration
            table_status_after = check_existing_tables(conn)
            if table_status_after['missing']:
                logger.error(f"Migration incomplete. Still missing: {table_status_after['missing']}")
                return False

            logger.info("✅ Entity Memory migration completed successfully")
            logger.info(f"New tables added: {sorted(table_status['missing'])}")

            # Populate FTS index from existing memories
            if 'memories' in table_status['existing']:
                logger.info("Populating FTS index from existing memories...")
                cursor = conn.execute("SELECT COUNT(*) FROM memories")
                count = cursor.fetchone()[0]

                if count > 0:
                    conn.execute("""
                        INSERT INTO memories_fts(rowid, external_id, summary, goal, user_intent, outcome, tags)
                        SELECT id, external_id, summary, goal, user_intent, outcome, tags
                        FROM memories
                    """)
                    conn.commit()
                    logger.info(f"✅ Indexed {count} existing memories for full-text search")

            return True

    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        return False


def main():
    """Main migration entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Migrate Angmini memory database to Entity Memory v2"
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        help="Path to database file (default: auto-detect from config)"
    )
    parser.add_argument(
        "--skip-backup",
        action="store_true",
        help="Skip database backup before migration"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check migration status, don't run migration"
    )

    args = parser.parse_args()

    # Get database path
    db_path = args.db_path or get_database_path()
    logger.info(f"Database path: {db_path}")

    # Check-only mode
    if args.check_only:
        if not db_path.exists():
            logger.info("❌ Database does not exist yet")
            return 0

        with sqlite3.connect(db_path) as conn:
            status = check_existing_tables(conn)
            logger.info(f"Existing tables: {sorted(status['existing'])}")
            logger.info(f"Missing tables: {sorted(status['missing'])}")

            if status['missing']:
                logger.info("⚠️  Migration needed")
                return 1
            else:
                logger.info("✅ All tables present, migration complete")
                return 0

    # Run migration
    success = run_migration(db_path, skip_backup=args.skip_backup)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
