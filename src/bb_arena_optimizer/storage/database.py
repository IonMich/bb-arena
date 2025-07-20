"""Database manager for SQLite storage."""

import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import ArenaSnapshot, GameRecord, PriceSnapshot, Season, TeamInfo, TeamLeagueHistory, LeagueHierarchy
from .utils.arena_utils import ArenaSnapshotManager
from .utils.game_utils import GameRecordManager
from .utils.team_utils import TeamInfoManager
from .utils.season_utils import SeasonManager

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
        
        # Initialize utility managers
        self.arena_manager = ArenaSnapshotManager(self.db_path)
        self.game_manager = GameRecordManager(self.db_path)
        self.team_manager = TeamInfoManager(self.db_path)
        self.season_manager = SeasonManager(self.db_path)

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
                    bleachers_price INTEGER,
                    lower_tier_price INTEGER,
                    courtside_price INTEGER,
                    luxury_boxes_price INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create games table (updated schema with calculated revenue)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS games (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id TEXT UNIQUE NOT NULL,
                    home_team_id INTEGER NOT NULL,
                    away_team_id INTEGER NOT NULL,
                    date TIMESTAMP NOT NULL,
                    game_type TEXT NOT NULL,
                    season INTEGER NOT NULL,
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
                    ticket_revenue INTEGER,
                    bleachers_price INTEGER,
                    lower_tier_price INTEGER,
                    courtside_price INTEGER,
                    luxury_boxes_price INTEGER,
                    neutral_arena BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    calculated_revenue INTEGER GENERATED ALWAYS AS (
                        COALESCE(bleachers_attendance * bleachers_price, 0) +
                        COALESCE(lower_tier_attendance * lower_tier_price, 0) +
                        COALESCE(courtside_attendance * courtside_price, 0) +
                        COALESCE(luxury_boxes_attendance * luxury_boxes_price, 0)
                    ) STORED
                )
            """)

            # Create seasons table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS seasons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    season_number INTEGER UNIQUE,
                    start_date TIMESTAMP,
                    end_date TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create team_info table for caching team information
            conn.execute("""
                CREATE TABLE IF NOT EXISTS team_info (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bb_team_id TEXT,
                    bb_username TEXT,
                    team_name TEXT,
                    short_name TEXT,
                    owner TEXT,
                    league_id TEXT,
                    league_name TEXT,
                    league_level TEXT,
                    country_id TEXT,
                    country_name TEXT,
                    rival_id TEXT,
                    rival_name TEXT,
                    create_date TEXT,
                    last_synced TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(bb_username)
                )
            """)

            # Create league_hierarchy table for efficient league level lookups
            conn.execute("""
                CREATE TABLE IF NOT EXISTS league_hierarchy (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    country_id INTEGER NOT NULL,
                    country_name TEXT NOT NULL,
                    league_id INTEGER NOT NULL,
                    league_name TEXT NOT NULL,
                    league_level INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(country_id, league_id)
                )
            """)

            # Create team_league_history table for storing team history data
            conn.execute("""
                CREATE TABLE IF NOT EXISTS team_league_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    team_id INTEGER NOT NULL,
                    season INTEGER NOT NULL,
                    team_name TEXT NOT NULL,
                    league_id INTEGER,
                    league_name TEXT NOT NULL,
                    league_level INTEGER NOT NULL,
                    achievement TEXT,
                    is_active_team BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(team_id, season, team_name)
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
                "CREATE INDEX IF NOT EXISTS idx_games_home_team ON games(home_team_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_games_away_team ON games(away_team_id)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_games_date ON games(date)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_games_game_id ON games(game_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_seasons_number ON seasons(season_number)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_team_info_username ON team_info(bb_username)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_team_info_team_id ON team_info(bb_team_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_league_hierarchy_country ON league_hierarchy(country_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_league_hierarchy_level ON league_hierarchy(league_level)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_team_history_team ON team_league_history(team_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_team_history_season ON team_league_history(season)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_team_history_active ON team_league_history(is_active_team)"
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
                except sqlite3.OperationalError as e:
                    logger.warning(f"Could not add column {column_name}: {e}")
        
        # Add new indexes for better query performance
        try:
            conn.execute("CREATE INDEX IF NOT EXISTS idx_games_season ON games(season)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_games_division ON games(division)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_games_country ON games(country)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_games_cup_round ON games(cup_round)")
        except sqlite3.OperationalError:
            pass  # Indexes might already exist
            
        conn.commit()

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
                    luxury_boxes_price, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    price_snapshot.team_id,
                    price_snapshot.bleachers_price,
                    price_snapshot.lower_tier_price,
                    price_snapshot.courtside_price,
                    price_snapshot.luxury_boxes_price,
                    price_snapshot.created_at,
                ),
            )
            conn.commit()
            row_id = cursor.lastrowid
            if row_id is None:
                raise ValueError("Failed to insert price snapshot")
            return row_id

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
                        created_at=datetime.fromisoformat(row["created_at"])
                        if row["created_at"]
                        else None,
                    )
                )

            return prices

    def get_price_snapshot_in_range(
        self, 
        team_id: str, 
        start_time: datetime, 
        end_time: datetime
    ) -> PriceSnapshot | None:
        """Get a price snapshot for a team within a specific time range.
        
        Args:
            team_id: Team ID to query for
            start_time: Start of time range (UTC)
            end_time: End of time range (UTC)
            
        Returns:
            PriceSnapshot instance if found, None otherwise
            
        Note:
            Returns the most recent snapshot within the time range.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            query = """
                SELECT * FROM price_snapshots 
                WHERE team_id = ? 
                AND datetime(created_at) BETWEEN datetime(?) AND datetime(?)
                ORDER BY created_at DESC 
                LIMIT 1
            """
            params = [team_id, start_time.isoformat(), end_time.isoformat()]
            
            cursor = conn.execute(query, params)
            row = cursor.fetchone()
            
            if row:
                return PriceSnapshot(
                    id=row["id"],
                    team_id=row["team_id"],
                    bleachers_price=row["bleachers_price"],
                    lower_tier_price=row["lower_tier_price"],
                    courtside_price=row["courtside_price"],
                    luxury_boxes_price=row["luxury_boxes_price"],
                    created_at=datetime.fromisoformat(row["created_at"])
                    if row["created_at"]
                    else None,
                )
            return None

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
                """SELECT COUNT(DISTINCT team_id) FROM (
                    SELECT home_team_id as team_id FROM games WHERE home_team_id IS NOT NULL
                    UNION
                    SELECT away_team_id as team_id FROM games WHERE away_team_id IS NOT NULL
                )"""
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
        pass

    # Delegation methods to utility managers
    
    def get_game_start_time_UTC(self, game_id: str) -> datetime:
        """
        Get the exact timezone-aware datetime for a game by querying the database.
        
        Args:
            game_id: The game ID to query for
            
        Returns:
            datetime: Timezone-aware datetime of the game start time
            
        Raises:
            ValueError: If game_id is not found in the database
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT date FROM games WHERE game_id = ?",
                (game_id,)
            )
            row = cursor.fetchone()
            
            if row is None:
                raise ValueError(f"Game with ID {game_id} not found in database")
            
            game_date = row[0]
            if game_date is None:
                raise ValueError(f"Game {game_id} has no date information")
            
            # Convert to datetime if it's a string
            if isinstance(game_date, str):
                return datetime.fromisoformat(game_date)
            else:
                return game_date
    
    # Arena snapshot delegations
    def save_arena_snapshot(self, arena_snapshot: ArenaSnapshot) -> int:
        """Delegate to arena manager."""
        return self.arena_manager.save_arena_snapshot(arena_snapshot)
    
    def get_latest_arena_snapshot(self, team_id: str) -> ArenaSnapshot | None:
        """Delegate to arena manager."""
        return self.arena_manager.get_latest_arena_snapshot(team_id)
    
    def get_arena_snapshots(self, limit: int = 50, offset: int = 0) -> list[ArenaSnapshot]:
        """Delegate to arena manager."""
        return self.arena_manager.get_arena_snapshots(limit, offset)
    
    def get_arena_snapshots_count(self) -> int:
        """Delegate to arena manager."""
        return self.arena_manager.get_arena_snapshots_count()
    
    def get_arena_snapshot_by_id(self, arena_id: int) -> ArenaSnapshot | None:
        """Delegate to arena manager."""
        return self.arena_manager.get_arena_snapshot_by_id(arena_id)
    
    def get_arena_snapshots_by_team(self, team_id: str, limit: int = 50) -> list[ArenaSnapshot]:
        """Delegate to arena manager."""
        return self.arena_manager.get_arena_snapshots_by_team(team_id, limit)
    
    def should_save_arena_snapshot(self, arena_snapshot: ArenaSnapshot) -> bool:
        """Delegate to arena manager."""
        return self.arena_manager.should_save_arena_snapshot(arena_snapshot)
    
    def save_arena_snapshot_smart(self, arena_snapshot: ArenaSnapshot) -> tuple[int | None, bool]:
        """Delegate to arena manager."""
        return self.arena_manager.save_arena_snapshot_smart(arena_snapshot)
    
    def get_latest_arena_snapshots(self, limit: int = 50, offset: int = 0) -> list[ArenaSnapshot]:
        """Delegate to arena manager."""
        return self.arena_manager.get_latest_arena_snapshots(limit, offset)
    
    def get_latest_arena_snapshots_count(self) -> int:
        """Delegate to arena manager."""
        return self.arena_manager.get_latest_arena_snapshots_count()
    
    # Game record delegations
    def save_game_record(self, game_record: GameRecord) -> int:
        """Delegate to game manager."""
        return self.game_manager.save_game_record(game_record)
    
    def get_games_for_team(self, team_id: str, limit: int | None = None) -> list[GameRecord]:
        """Delegate to game manager."""
        return self.game_manager.get_games_for_team(team_id, limit)
    
    def get_game_by_id(self, game_id: str) -> GameRecord | None:
        """Delegate to game manager."""
        return self.game_manager.get_game_by_id(game_id)
    
    def get_prefix_max_attendance(self, team_id: str, up_to_date: str) -> dict[str, int]:
        """Delegate to game manager."""
        return self.game_manager.get_prefix_max_attendance(team_id, up_to_date)
    
    # Team info delegations
    def save_team_info(self, team_info: TeamInfo) -> None:
        """Delegate to team manager."""
        return self.team_manager.save_team_info(team_info)
    
    def get_team_info_by_username(self, username: str) -> TeamInfo | None:
        """Delegate to team manager."""
        return self.team_manager.get_team_info_by_username(username)
    
    def should_sync_team_info(self, username: str, hours_threshold: int = 24) -> bool:
        """Delegate to team manager."""
        return self.team_manager.should_sync_team_info(username, hours_threshold)
    
    # League hierarchy delegations
    def save_league_hierarchy(self, leagues: list) -> None:
        """Delegate to team manager."""
        return self.team_manager.save_league_hierarchy(leagues)
    
    def get_league_hierarchy_by_country(self, country_id: int) -> list:
        """Delegate to team manager."""
        return self.team_manager.get_league_hierarchy_by_country(country_id)
    
    def get_league_level(self, league_id: int) -> int | None:
        """Delegate to team manager."""
        return self.team_manager.get_league_level(league_id)
    
    def populate_league_hierarchy_for_countries(self, country_ids: list[int]) -> None:
        """Delegate to team manager."""
        return self.team_manager.populate_league_hierarchy_for_countries(country_ids)
    
    # Team league history delegations
    def save_team_league_history(self, team_id: int, history_entries: list) -> None:
        """Delegate to team manager."""
        return self.team_manager.save_team_league_history(team_id, history_entries)
    
    def get_team_league_history(self, team_id: int, active_only: bool = True) -> list:
        """Delegate to team manager."""
        return self.team_manager.get_team_league_history(team_id, active_only)
    
    def get_team_current_league_info(self, team_id: int) -> dict | None:
        """Delegate to team manager."""
        return self.team_manager.get_team_current_league_info(team_id)
    
    def collect_team_history_from_webpage(self, team_id: int) -> bool:
        """Delegate to team manager."""
        return self.team_manager.collect_team_history_from_webpage(team_id)
    
    def bulk_collect_team_histories(self, team_ids: list[int]) -> dict:
        """Delegate to team manager."""
        return self.team_manager.bulk_collect_team_histories(team_ids)
    
    # Season delegations
    def save_seasons(self, seasons: list[Season]) -> None:
        """Delegate to season manager."""
        return self.season_manager.save_seasons(seasons)
    
    def get_all_seasons(self) -> list[Season]:
        """Delegate to season manager."""
        return self.season_manager.get_all_seasons()
    
    def get_current_season(self) -> Season | None:
        """Delegate to season manager."""
        return self.season_manager.get_current_season()
    
    def get_latest_season(self) -> Season | None:
        """Delegate to season manager."""
        return self.season_manager.get_latest_season()
    
    def should_update_seasons(self) -> bool:
        """Delegate to season manager."""
        return self.season_manager.should_update_seasons()
    
    def get_season_for_date(self, date_str: str) -> int | None:
        """Delegate to season manager."""
        return self.season_manager.get_season_for_date(date_str)
    
    def get_minimum_season_for_team(self, team_id: str) -> int | None:
        """Delegate to season manager."""
        return self.season_manager.get_minimum_season_for_team(team_id)

    # Enhanced pricing service methods
    def get_team_games(self, team_id: str, limit: int = 1000) -> list[GameRecord]:
        """Get all games for a team."""
        return self.game_manager.get_team_games(team_id, limit)
    
    def get_team_games_in_time_range(
        self, 
        team_id: str, 
        start_time: datetime, 
        end_time: datetime,
        home_games_only: bool = True
    ) -> list[GameRecord]:
        """
        Query database for team's games within specified time range.
        Used by PricePeriod.check_games_in_time_range()
        
        Args:
            team_id: Team ID to query for
            start_time: Start of time range (UTC)
            end_time: End of time range (UTC)  
            home_games_only: If True, only return home games
            
        Returns:
            List of GameRecord objects within the time range
        """
        # Convert team_id to int since database stores it as INTEGER
        team_id_int = int(team_id)
        
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT game_id, id, home_team_id, away_team_id, date, game_type, season,
                       division, country, cup_round, score_home, score_away,
                       bleachers_attendance, lower_tier_attendance, courtside_attendance,
                       luxury_boxes_attendance, total_attendance, neutral_arena,
                       ticket_revenue, calculated_revenue, bleachers_price, lower_tier_price,
                       courtside_price, luxury_boxes_price, created_at, updated_at
                FROM games 
                WHERE (home_team_id = ? OR away_team_id = ?)
                AND datetime(date) BETWEEN datetime(?) AND datetime(?)
            """
            params = [team_id_int, team_id_int, start_time.isoformat(), end_time.isoformat()]
            
            if home_games_only:
                query += " AND home_team_id = ?"
                params.append(team_id_int)
                
            query += " ORDER BY date"
            
            cursor = conn.execute(query, params)
            games = []
            
            for row in cursor.fetchall():
                game = GameRecord(
                    game_id=row[0],
                    id=row[1],
                    home_team_id=row[2],
                    away_team_id=row[3],
                    date=datetime.fromisoformat(row[4]) if row[4] else None,
                    game_type=row[5],
                    season=row[6],
                    division=row[7],
                    country=row[8],
                    cup_round=row[9],
                    score_home=row[10],
                    score_away=row[11],
                    bleachers_attendance=row[12],
                    lower_tier_attendance=row[13],
                    courtside_attendance=row[14],
                    luxury_boxes_attendance=row[15],
                    total_attendance=row[16],
                    neutral_arena=bool(row[17]),
                    ticket_revenue=row[18],
                    calculated_revenue=row[19],
                    bleachers_price=row[20],
                    lower_tier_price=row[21],
                    courtside_price=row[22],
                    luxury_boxes_price=row[23],
                    created_at=datetime.fromisoformat(row[24]) if row[24] else None,
                    updated_at=datetime.fromisoformat(row[25]) if row[25] else None,
                )
                games.append(game)
                
            return games
    
    def update_game_prices(self, game: GameRecord) -> bool:
        """
        Update game prices in database.
        Used after PricePeriod.set_game_prices()
        
        Args:
            game: GameRecord with updated prices
            
        Returns:
            True if update was successful
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = """
                    UPDATE games 
                    SET bleachers_price = ?, lower_tier_price = ?, 
                        courtside_price = ?, luxury_boxes_price = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE game_id = ?
                """
                params = [
                    game.bleachers_price,
                    game.lower_tier_price,
                    game.courtside_price,
                    game.luxury_boxes_price,
                    game.game_id
                ]
                
                cursor = conn.execute(query, params)
                success = cursor.rowcount > 0
                
                if success:
                    logger.info(f"Updated prices for game {game.game_id}")
                else:
                    logger.warning(f"No rows updated for game {game.game_id}")
                    
                return success
                
        except Exception as e:
            logger.error(f"Error updating prices for game {game.game_id}: {e}")
            return False
