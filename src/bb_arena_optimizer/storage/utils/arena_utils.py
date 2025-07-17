"""Arena snapshot database operations."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from ..models import ArenaSnapshot
from ...utils.logging_config import get_logger

logger = get_logger(__name__)


class ArenaSnapshotManager:
    """Manages arena snapshot database operations."""
    
    def __init__(self, db_path: str | Path):
        """Initialize arena snapshot manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
    
    def save_arena_snapshot(self, arena_snapshot: ArenaSnapshot) -> int:
        """Save arena snapshot to database.

        Args:
            arena_snapshot: ArenaSnapshot instance to save

        Returns:
            Database ID of the saved record
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO arena_snapshots (
                    team_id, arena_name, bleachers_capacity, lower_tier_capacity,
                    courtside_capacity, luxury_boxes_capacity, total_capacity,
                    expansion_in_progress, expansion_completion_date, expansion_cost,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    arena_snapshot.team_id,
                    arena_snapshot.arena_name,
                    arena_snapshot.bleachers_capacity,
                    arena_snapshot.lower_tier_capacity,
                    arena_snapshot.courtside_capacity,
                    arena_snapshot.luxury_boxes_capacity,
                    arena_snapshot.total_capacity,
                    arena_snapshot.expansion_in_progress,
                    arena_snapshot.expansion_completion_date,
                    arena_snapshot.expansion_cost,
                    arena_snapshot.created_at,
                ),
            )
            conn.commit()
            row_id = cursor.lastrowid
            if row_id is None:
                raise RuntimeError("Failed to get row ID after insert")
            return row_id

    def get_latest_arena_snapshot(self, team_id: str) -> ArenaSnapshot | None:
        """Get the most recent arena snapshot for a team.

        Args:
            team_id: Team ID to query

        Returns:
            Latest ArenaSnapshot or None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM arena_snapshots 
                WHERE team_id = ? 
                ORDER BY created_at DESC 
                LIMIT 1
            """,
                (team_id,),
            )

            row = cursor.fetchone()
            if row:
                return ArenaSnapshot(
                    id=row["id"],
                    team_id=row["team_id"],
                    arena_name=row["arena_name"],
                    bleachers_capacity=row["bleachers_capacity"],
                    lower_tier_capacity=row["lower_tier_capacity"],
                    courtside_capacity=row["courtside_capacity"],
                    luxury_boxes_capacity=row["luxury_boxes_capacity"],
                    total_capacity=row["total_capacity"],
                    expansion_in_progress=bool(row["expansion_in_progress"]),
                    expansion_completion_date=row["expansion_completion_date"],
                    expansion_cost=row["expansion_cost"],
                    created_at=datetime.fromisoformat(row["created_at"])
                    if row["created_at"]
                    else None,
                )
            return None

    def get_arena_snapshots(
        self, limit: int = 50, offset: int = 0
    ) -> list[ArenaSnapshot]:
        """Get arena snapshots with pagination.

        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of ArenaSnapshot instances
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            query = """
                SELECT * FROM arena_snapshots 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            """
            cursor = conn.execute(query, [limit, offset])

            snapshots = []
            for row in cursor.fetchall():
                snapshots.append(ArenaSnapshot(
                    id=row["id"],
                    team_id=row["team_id"],
                    arena_name=row["arena_name"],
                    bleachers_capacity=row["bleachers_capacity"],
                    lower_tier_capacity=row["lower_tier_capacity"],
                    courtside_capacity=row["courtside_capacity"],
                    luxury_boxes_capacity=row["luxury_boxes_capacity"],
                    total_capacity=row["total_capacity"],
                    expansion_in_progress=bool(row["expansion_in_progress"]),
                    expansion_completion_date=row["expansion_completion_date"],
                    expansion_cost=row["expansion_cost"],
                    created_at=datetime.fromisoformat(row["created_at"])
                    if row["created_at"]
                    else None,
                ))

            return snapshots

    def get_arena_snapshots_count(self) -> int:
        """Get total count of arena snapshots.

        Returns:
            Total count of arena snapshots
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM arena_snapshots")
            result = cursor.fetchone()
            return int(result[0]) if result else 0

    def get_arena_snapshot_by_id(self, arena_id: int) -> ArenaSnapshot | None:
        """Get a specific arena snapshot by ID.

        Args:
            arena_id: Arena snapshot ID

        Returns:
            ArenaSnapshot instance or None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            cursor = conn.execute(
                "SELECT * FROM arena_snapshots WHERE id = ?", [arena_id]
            )
            row = cursor.fetchone()

            if row:
                return ArenaSnapshot(
                    id=row["id"],
                    team_id=row["team_id"],
                    arena_name=row["arena_name"],
                    bleachers_capacity=row["bleachers_capacity"],
                    lower_tier_capacity=row["lower_tier_capacity"],
                    courtside_capacity=row["courtside_capacity"],
                    luxury_boxes_capacity=row["luxury_boxes_capacity"],
                    total_capacity=row["total_capacity"],
                    expansion_in_progress=bool(row["expansion_in_progress"]),
                    expansion_completion_date=row["expansion_completion_date"],
                    expansion_cost=row["expansion_cost"],
                    created_at=datetime.fromisoformat(row["created_at"])
                    if row["created_at"]
                    else None,
                )
            return None

    def get_arena_snapshots_by_team(
        self, team_id: str, limit: int = 50
    ) -> list[ArenaSnapshot]:
        """Get arena snapshots for a specific team.

        Args:
            team_id: Team ID to query
            limit: Maximum number of records to return

        Returns:
            List of ArenaSnapshot instances
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            query = """
                SELECT * FROM arena_snapshots 
                WHERE team_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            """
            cursor = conn.execute(query, [team_id, limit])

            snapshots = []
            for row in cursor.fetchall():
                snapshots.append(ArenaSnapshot(
                    id=row["id"],
                    team_id=row["team_id"],
                    arena_name=row["arena_name"],
                    bleachers_capacity=row["bleachers_capacity"],
                    lower_tier_capacity=row["lower_tier_capacity"],
                    courtside_capacity=row["courtside_capacity"],
                    luxury_boxes_capacity=row["luxury_boxes_capacity"],
                    total_capacity=row["total_capacity"],
                    expansion_in_progress=bool(row["expansion_in_progress"]),
                    expansion_completion_date=row["expansion_completion_date"],
                    expansion_cost=row["expansion_cost"],
                    created_at=datetime.fromisoformat(row["created_at"])
                    if row["created_at"]
                    else None,
                ))

            return snapshots

    def should_save_arena_snapshot(self, arena_snapshot: ArenaSnapshot) -> bool:
        """Determine if an arena snapshot should be saved based on existing data.
        
        Args:
            arena_snapshot: ArenaSnapshot to check
            
        Returns:
            True if snapshot should be saved, False otherwise
        """
        if not arena_snapshot.team_id:
            return True  # Always save if no team_id
            
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Get the most recent snapshot for this team
            cursor = conn.execute(
                """
                SELECT * FROM arena_snapshots 
                WHERE team_id = ? 
                ORDER BY created_at DESC 
                LIMIT 1
                """,
                [arena_snapshot.team_id]
            )
            
            latest_row = cursor.fetchone()
            if not latest_row:
                return True  # No existing snapshot, save this one
                
            # Convert to ArenaSnapshot for comparison
            latest_snapshot = ArenaSnapshot(
                id=latest_row["id"],
                team_id=latest_row["team_id"],
                arena_name=latest_row["arena_name"],
                bleachers_capacity=latest_row["bleachers_capacity"],
                lower_tier_capacity=latest_row["lower_tier_capacity"],
                courtside_capacity=latest_row["courtside_capacity"],
                luxury_boxes_capacity=latest_row["luxury_boxes_capacity"],
                total_capacity=latest_row["total_capacity"],
                expansion_in_progress=bool(latest_row["expansion_in_progress"]),
                expansion_completion_date=latest_row["expansion_completion_date"],
                expansion_cost=latest_row["expansion_cost"],
                created_at=datetime.fromisoformat(latest_row["created_at"]) if latest_row["created_at"] else None
            )
            
            # Check if arena data has changed
            arena_data_changed = (
                latest_snapshot.bleachers_capacity != arena_snapshot.bleachers_capacity or
                latest_snapshot.lower_tier_capacity != arena_snapshot.lower_tier_capacity or
                latest_snapshot.courtside_capacity != arena_snapshot.courtside_capacity or
                latest_snapshot.luxury_boxes_capacity != arena_snapshot.luxury_boxes_capacity or
                latest_snapshot.expansion_in_progress != arena_snapshot.expansion_in_progress or
                latest_snapshot.expansion_completion_date != arena_snapshot.expansion_completion_date or
                latest_snapshot.expansion_cost != arena_snapshot.expansion_cost
            )
            
            if arena_data_changed:
                return True  # Arena data changed, save new snapshot
                
            # Check if it's a different day (even if data is the same)
            if latest_snapshot.created_at and arena_snapshot.created_at:
                latest_date = latest_snapshot.created_at.date()
                new_date = arena_snapshot.created_at.date()
                if latest_date != new_date:
                    return True  # Different date, save new snapshot
                    
            return False  # Same data and same date, don't save duplicate

    def save_arena_snapshot_smart(self, arena_snapshot: ArenaSnapshot) -> tuple[int | None, bool]:
        """Save arena snapshot with smart deduplication.
        
        Args:
            arena_snapshot: ArenaSnapshot instance to save
            
        Returns:
            Tuple of (database_id, was_saved) where:
            - database_id: ID of saved record or None if not saved
            - was_saved: True if new snapshot was saved, False if duplicate was skipped
        """
        if self.should_save_arena_snapshot(arena_snapshot):
            return self.save_arena_snapshot(arena_snapshot), True
        else:
            return None, False

    def get_latest_arena_snapshots(self, limit: int = 50, offset: int = 0) -> list[ArenaSnapshot]:
        """Get the latest arena snapshot for each team.
        
        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of ArenaSnapshot instances (latest per team)
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Get latest snapshot per team
            query = """
                SELECT a1.* FROM arena_snapshots a1
                INNER JOIN (
                    SELECT team_id, MAX(created_at) as max_created_at
                    FROM arena_snapshots
                    GROUP BY team_id
                ) a2 ON a1.team_id = a2.team_id AND a1.created_at = a2.max_created_at
                ORDER BY a1.created_at DESC
                LIMIT ? OFFSET ?
            """
            
            cursor = conn.execute(query, [limit, offset])
            
            snapshots = []
            for row in cursor.fetchall():
                snapshots.append(ArenaSnapshot(
                    id=row["id"],
                    team_id=row["team_id"],
                    arena_name=row["arena_name"],
                    bleachers_capacity=row["bleachers_capacity"],
                    lower_tier_capacity=row["lower_tier_capacity"],
                    courtside_capacity=row["courtside_capacity"],
                    luxury_boxes_capacity=row["luxury_boxes_capacity"],
                    total_capacity=row["total_capacity"],
                    expansion_in_progress=bool(row["expansion_in_progress"]),
                    expansion_completion_date=row["expansion_completion_date"],
                    expansion_cost=row["expansion_cost"],
                    created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None
                ))
            
            return snapshots

    def get_latest_arena_snapshots_count(self) -> int:
        """Get count of unique teams with arena snapshots.
        
        Returns:
            Number of unique teams
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT COUNT(DISTINCT team_id) FROM arena_snapshots"
            )
            result = cursor.fetchone()
            return result[0] if result else 0
