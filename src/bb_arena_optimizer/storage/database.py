"""Database manager for SQLite storage."""

import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import ArenaSnapshot, GameRecord, PriceSnapshot

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages SQLite database operations for BuzzerBeater data."""

    def __init__(self, db_path: str | Path = "bb_arena_data.db"):
        """Initialize database manager.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self._ensure_database_exists()

    def _ensure_database_exists(self) -> None:
        """Create database and tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")

            # Create arena_snapshots table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS arena_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    team_id TEXT,
                    arena_name TEXT,
                    bleachers_capacity INTEGER DEFAULT 0,
                    lower_tier_capacity INTEGER DEFAULT 0,
                    courtside_capacity INTEGER DEFAULT 0,
                    luxury_boxes_capacity INTEGER DEFAULT 0,
                    total_capacity INTEGER DEFAULT 0,
                    expansion_in_progress BOOLEAN DEFAULT FALSE,
                    expansion_completion_date TEXT,
                    expansion_cost REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create price_snapshots table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS price_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    team_id TEXT,
                    bleachers_price REAL,
                    lower_tier_price REAL,
                    courtside_price REAL,
                    luxury_boxes_price REAL,
                    game_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create games table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS games (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id TEXT UNIQUE NOT NULL,
                    team_id TEXT,
                    date TIMESTAMP,
                    opponent TEXT,
                    is_home BOOLEAN DEFAULT FALSE,
                    game_type TEXT,
                    season INTEGER,
                    division TEXT,
                    country TEXT,
                    cup_round TEXT,
                    score_home INTEGER,
                    score_away INTEGER,
                    bleachers_attendance INTEGER,
                    lower_tier_attendance INTEGER,
                    courtside_attendance INTEGER,
                    luxury_boxes_attendance INTEGER,
                    total_attendance INTEGER,
                    ticket_revenue REAL,
                    bleachers_price REAL,
                    lower_tier_price REAL,
                    courtside_price REAL,
                    luxury_boxes_price REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes for better query performance
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_arena_snapshots_team_id ON arena_snapshots(team_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_arena_snapshots_created_at ON arena_snapshots(created_at)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_price_snapshots_team_id ON price_snapshots(team_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_price_snapshots_game_id ON price_snapshots(game_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_games_team_id ON games(team_id)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_games_date ON games(date)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_games_game_id ON games(game_id)"
            )

            conn.commit()
            logger.info(f"Database initialized at {self.db_path}")
            
            # Run migrations
            self._run_migrations(conn)

    def _run_migrations(self, conn: sqlite3.Connection) -> None:
        """Run database migrations to add new columns."""
        # Check if new columns exist, if not add them
        cursor = conn.cursor()
        
        # Get existing columns
        cursor.execute("PRAGMA table_info(games)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        
        # Add new columns if they don't exist
        new_columns = {
            'season': 'INTEGER',
            'division': 'TEXT',
            'country': 'TEXT', 
            'cup_round': 'TEXT'
        }
        
        for column_name, column_type in new_columns.items():
            if column_name not in existing_columns:
                try:
                    conn.execute(f"ALTER TABLE games ADD COLUMN {column_name} {column_type}")
                    logger.info(f"Added column {column_name} to games table")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" not in str(e).lower():
                        raise
        
        # Add new indexes for better query performance
        try:
            conn.execute("CREATE INDEX IF NOT EXISTS idx_games_season ON games(season)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_games_division ON games(division)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_games_country ON games(country)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_games_cup_round ON games(cup_round)")
        except sqlite3.OperationalError:
            pass  # Indexes might already exist
            
        conn.commit()

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

    def save_price_snapshot(self, price_snapshot: PriceSnapshot) -> int:
        """Save price snapshot to database.

        Args:
            price_snapshot: PriceSnapshot instance to save

        Returns:
            Database ID of the saved record
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO price_snapshots (
                    team_id, bleachers_price, lower_tier_price, courtside_price,
                    luxury_boxes_price, game_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    price_snapshot.team_id,
                    price_snapshot.bleachers_price,
                    price_snapshot.lower_tier_price,
                    price_snapshot.courtside_price,
                    price_snapshot.luxury_boxes_price,
                    price_snapshot.game_id,
                    price_snapshot.created_at,
                ),
            )
            conn.commit()
            row_id = cursor.lastrowid
            if row_id is None:
                raise ValueError("Failed to insert price snapshot")
            return row_id

    def save_game_record(self, game_record: GameRecord) -> int:
        """Save or update game record in database.

        Args:
            game_record: GameRecord instance to save

        Returns:
            Database ID of the saved record
        """
        with sqlite3.connect(self.db_path) as conn:
            # Try to update existing record first
            cursor = conn.execute(
                """
                UPDATE games SET
                    team_id = ?, date = ?, opponent = ?, is_home = ?, game_type = ?,
                    season = ?, division = ?, country = ?, cup_round = ?,
                    score_home = ?, score_away = ?, bleachers_attendance = ?,
                    lower_tier_attendance = ?, courtside_attendance = ?,
                    luxury_boxes_attendance = ?, total_attendance = ?,
                    ticket_revenue = ?, bleachers_price = ?, lower_tier_price = ?,
                    courtside_price = ?, luxury_boxes_price = ?, updated_at = ?
                WHERE game_id = ?
            """,
                (
                    game_record.team_id,
                    game_record.date,
                    game_record.opponent,
                    game_record.is_home,
                    game_record.game_type,
                    game_record.season,
                    game_record.division,
                    game_record.country,
                    game_record.cup_round,
                    game_record.score_home,
                    game_record.score_away,
                    game_record.bleachers_attendance,
                    game_record.lower_tier_attendance,
                    game_record.courtside_attendance,
                    game_record.luxury_boxes_attendance,
                    game_record.total_attendance,
                    game_record.ticket_revenue,
                    game_record.bleachers_price,
                    game_record.lower_tier_price,
                    game_record.courtside_price,
                    game_record.luxury_boxes_price,
                    datetime.now(),
                    game_record.game_id,
                ),
            )

            if cursor.rowcount == 0:
                # Insert new record
                cursor = conn.execute(
                    """
                    INSERT INTO games (
                        game_id, team_id, date, opponent, is_home, game_type,
                        season, division, country, cup_round,
                        score_home, score_away, bleachers_attendance,
                        lower_tier_attendance, courtside_attendance,
                        luxury_boxes_attendance, total_attendance, ticket_revenue,
                        bleachers_price, lower_tier_price, courtside_price,
                        luxury_boxes_price, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        game_record.game_id,
                        game_record.team_id,
                        game_record.date,
                        game_record.opponent,
                        game_record.is_home,
                        game_record.game_type,
                        game_record.season,
                        game_record.division,
                        game_record.country,
                        game_record.cup_round,
                        game_record.score_home,
                        game_record.score_away,
                        game_record.bleachers_attendance,
                        game_record.lower_tier_attendance,
                        game_record.courtside_attendance,
                        game_record.luxury_boxes_attendance,
                        game_record.total_attendance,
                        game_record.ticket_revenue,
                        game_record.bleachers_price,
                        game_record.lower_tier_price,
                        game_record.courtside_price,
                        game_record.luxury_boxes_price,
                        game_record.created_at,
                        datetime.now(),
                    ),
                )

            conn.commit()
            row_id = cursor.lastrowid
            if row_id is None:
                raise ValueError("Failed to insert game record")
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

    def get_games_for_team(
        self, team_id: str, limit: int | None = None
    ) -> list[GameRecord]:
        """Get games for a team, ordered by date.

        Args:
            team_id: Team ID to query
            limit: Optional limit on number of records

        Returns:
            List of GameRecord instances
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            query = "SELECT * FROM games WHERE team_id = ? ORDER BY date DESC"
            params: list[str | int] = [team_id]

            if limit:
                query += " LIMIT ?"
                params.append(limit)

            cursor = conn.execute(query, params)

            games = []
            for row in cursor.fetchall():
                games.append(
                    GameRecord(
                        game_id=row["game_id"],
                        id=row["id"],
                        team_id=row["team_id"],
                        date=datetime.fromisoformat(row["date"])
                        if row["date"]
                        else None,
                        opponent=row["opponent"],
                        is_home=bool(row["is_home"]),
                        game_type=row["game_type"],
                        season=row["season"],
                        division=row["division"],
                        country=row["country"],
                        cup_round=row["cup_round"],
                        score_home=row["score_home"],
                        score_away=row["score_away"],
                        bleachers_attendance=row["bleachers_attendance"],
                        lower_tier_attendance=row["lower_tier_attendance"],
                        courtside_attendance=row["courtside_attendance"],
                        luxury_boxes_attendance=row["luxury_boxes_attendance"],
                        total_attendance=row["total_attendance"],
                        ticket_revenue=row["ticket_revenue"],
                        bleachers_price=row["bleachers_price"],
                        lower_tier_price=row["lower_tier_price"],
                        courtside_price=row["courtside_price"],
                        luxury_boxes_price=row["luxury_boxes_price"],
                        created_at=datetime.fromisoformat(row["created_at"])
                        if row["created_at"]
                        else None,
                        updated_at=datetime.fromisoformat(row["updated_at"])
                        if row["updated_at"]
                        else None,
                    )
                )

            return games

    def get_price_history(
        self, team_id: str, limit: int | None = None
    ) -> list[PriceSnapshot]:
        """Get price history for a team.

        Args:
            team_id: Team ID to query
            limit: Optional limit on number of records

        Returns:
            List of PriceSnapshot instances
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            query = "SELECT * FROM price_snapshots WHERE team_id = ? ORDER BY created_at DESC"
            params: list[str | int] = [team_id]

            if limit:
                query += " LIMIT ?"
                params.append(limit)

            cursor = conn.execute(query, params)

            prices = []
            for row in cursor.fetchall():
                prices.append(
                    PriceSnapshot(
                        id=row["id"],
                        team_id=row["team_id"],
                        bleachers_price=row["bleachers_price"],
                        lower_tier_price=row["lower_tier_price"],
                        courtside_price=row["courtside_price"],
                        luxury_boxes_price=row["luxury_boxes_price"],
                        game_id=row["game_id"],
                        created_at=datetime.fromisoformat(row["created_at"])
                        if row["created_at"]
                        else None,
                    )
                )

            return prices

    def get_database_stats(self) -> dict[str, Any]:
        """Get statistics about the database contents.

        Returns:
            Dictionary with database statistics
        """
        with sqlite3.connect(self.db_path) as conn:
            stats = {}

            # Count records in each table
            cursor = conn.execute("SELECT COUNT(*) FROM arena_snapshots")
            stats["arena_snapshots"] = cursor.fetchone()[0]

            cursor = conn.execute("SELECT COUNT(*) FROM price_snapshots")
            stats["price_snapshots"] = cursor.fetchone()[0]

            cursor = conn.execute("SELECT COUNT(*) FROM games")
            stats["total_games"] = cursor.fetchone()[0]

            # Count unique teams
            cursor = conn.execute(
                "SELECT COUNT(DISTINCT team_id) FROM games WHERE team_id IS NOT NULL"
            )
            stats["unique_teams"] = cursor.fetchone()[0]

            # Date range of games
            cursor = conn.execute(
                "SELECT MIN(date), MAX(date) FROM games WHERE date IS NOT NULL"
            )
            date_range = cursor.fetchone()
            stats["earliest_game"] = date_range[0]
            stats["latest_game"] = date_range[1]

            return stats

    def close(self) -> None:
        """Close database connections (placeholder for future connection pooling)."""

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
            return cursor.fetchone()[0]

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
