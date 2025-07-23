"""Game records database operations."""

import sqlite3
from datetime import datetime, UTC as datetime_utc
from pathlib import Path

from ..models import GameRecord
from ...utils.logging_config import get_logger

logger = get_logger(__name__)


class GameRecordManager:
    """Manages game record database operations."""
    
    def __init__(self, db_path: str | Path):
        """Initialize game record manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
    
    def _validate_game_record(self, game_record: GameRecord) -> None:
        """Validate game record data before saving to database.
        
        Args:
            game_record: GameRecord to validate
            
        Raises:
            ValueError: If required fields are missing or invalid
        """
        errors = []
        
        # Check required string fields
        if not game_record.game_id or not isinstance(game_record.game_id, str):
            errors.append("game_id must be a non-empty string")
            
        # Check required integer fields
        if not isinstance(game_record.home_team_id, int) or game_record.home_team_id <= 0:
            errors.append("home_team_id must be a positive integer")
            
        if not isinstance(game_record.away_team_id, int) or game_record.away_team_id <= 0:
            errors.append("away_team_id must be a positive integer")
            
        # Check that home and away teams are different
        if game_record.home_team_id == game_record.away_team_id:
            errors.append("home_team_id and away_team_id must be different")
            
        # Check required fields for database schema
        if not game_record.game_type:
            errors.append("game_type is required")
            
        if not isinstance(game_record.season, int) or game_record.season <= 0:
            errors.append("season must be a positive integer")
            
        if not game_record.date:
            errors.append("date is required")
            
        if errors:
            raise ValueError(f"Invalid game record data: {'; '.join(errors)}")

    def save_game_record(self, game_record: GameRecord) -> int:
        """Save or update game record in database.
        
        When updating existing records, null values in the new record will not
        overwrite existing non-null values in the database.

        Args:
            game_record: GameRecord instance to save

        Returns:
            Database ID of the saved record
        """
        # Validate game record data
        self._validate_game_record(game_record)
        
        with sqlite3.connect(self.db_path) as conn:
            # Check if record already exists
            existing_cursor = conn.execute("SELECT * FROM games WHERE game_id = ?", (game_record.game_id,))
            existing_record = existing_cursor.fetchone()
            
            if existing_record:
                # Build dynamic update that preserves non-null existing values
                update_parts = []
                update_values = []
                
                # Define all updateable fields with their values
                field_mapping = {
                    "home_team_id": game_record.home_team_id,
                    "away_team_id": game_record.away_team_id,
                    "date": game_record.date,
                    "game_type": game_record.game_type,
                    "season": game_record.season,
                    "division": game_record.division,
                    "country": game_record.country,
                    "cup_round": game_record.cup_round,
                    "score_home": game_record.score_home,
                    "score_away": game_record.score_away,
                    "bleachers_attendance": game_record.bleachers_attendance,
                    "lower_tier_attendance": game_record.lower_tier_attendance,
                    "courtside_attendance": game_record.courtside_attendance,
                    "luxury_boxes_attendance": game_record.luxury_boxes_attendance,
                    "neutral_arena": game_record.neutral_arena,
                    "ticket_revenue": game_record.ticket_revenue,
                    "bleachers_price": game_record.bleachers_price,
                    "lower_tier_price": game_record.lower_tier_price,
                    "courtside_price": game_record.courtside_price,
                    "luxury_boxes_price": game_record.luxury_boxes_price,
                }
                
                # For each field, only update if new value is not None (don't overwrite existing data with null)
                for field_name, new_value in field_mapping.items():
                    if new_value is not None:
                        update_parts.append(f"{field_name} = ?")
                        update_values.append(new_value)
                
                # Always update timestamp
                update_parts.append("updated_at = ?")
                update_values.append(datetime.now(datetime_utc))
                update_values.append(game_record.game_id)  # For WHERE clause
                
                if update_parts:
                    cursor = conn.execute(
                        f"UPDATE games SET {', '.join(update_parts)} WHERE game_id = ?",
                        update_values
                    )
                    
                    # Get the database ID
                    id_cursor = conn.execute("SELECT id FROM games WHERE game_id = ?", (game_record.game_id,))
                    return id_cursor.fetchone()[0]
            else:
                # Insert new record
                columns = [
                    "game_id", "home_team_id", "away_team_id", "date", "game_type",
                    "season", "division", "country", "cup_round",
                    "score_home", "score_away", "bleachers_attendance",
                    "lower_tier_attendance", "courtside_attendance",
                    "luxury_boxes_attendance", "total_attendance", "neutral_arena",
                    "ticket_revenue", "bleachers_price", "lower_tier_price", 
                    "courtside_price", "luxury_boxes_price", "created_at", "updated_at"
                ]
                placeholders = ", ".join(["?"] * len(columns))
                columns_str = ", ".join(columns)
                
                cursor = conn.execute(
                    f"""
                    INSERT INTO games ({columns_str}) 
                    VALUES ({placeholders})
                """,
                    (
                        game_record.game_id,
                        game_record.home_team_id,
                        game_record.away_team_id,
                        game_record.date,
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
                        game_record.neutral_arena,
                        game_record.ticket_revenue,
                        game_record.bleachers_price,
                        game_record.lower_tier_price,
                        game_record.courtside_price,
                        game_record.luxury_boxes_price,
                        game_record.created_at,
                        datetime.now(datetime_utc),
                    ),
                )
                
                conn.commit()
                row_id = cursor.lastrowid
                if row_id is None:
                    raise ValueError("Failed to insert game record")
                return row_id

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

            query = "SELECT * FROM games WHERE (home_team_id = ? OR away_team_id = ?) AND neutral_arena = FALSE ORDER BY date DESC"
            params: list[str | int] = [team_id, team_id]

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
                        home_team_id=row["home_team_id"],
                        away_team_id=row["away_team_id"],
                        date=datetime.fromisoformat(row["date"])
                        if row["date"]
                        else None,
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
                        neutral_arena=bool(row["neutral_arena"]),
                        ticket_revenue=row["ticket_revenue"],
                        calculated_revenue=row["calculated_revenue"] if "calculated_revenue" in row.keys() else None,
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

    def get_game_by_id(self, game_id: str) -> GameRecord | None:
        """Get a specific game by its game_id.

        Args:
            game_id: Game ID to query

        Returns:
            GameRecord instance if found, None otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            query = "SELECT * FROM games WHERE game_id = ?"
            cursor = conn.execute(query, [game_id])
            row = cursor.fetchone()

            if row:
                return GameRecord(
                    game_id=row["game_id"],
                    id=row["id"],
                    home_team_id=row["home_team_id"],
                    away_team_id=row["away_team_id"],
                    date=datetime.fromisoformat(row["date"])
                    if row["date"]
                    else None,
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
                    neutral_arena=bool(row["neutral_arena"]),
                    ticket_revenue=row["ticket_revenue"],
                    calculated_revenue=row["calculated_revenue"] if "calculated_revenue" in row.keys() else None,
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

            return None

    def get_prefix_max_attendance(self, team_id: str, up_to_date: str) -> dict[str, int]:
        """Get the maximum attendance for each section from all home games up to a specific date.
        
        This provides lower bounds for arena capacity based on historical attendance data.
        
        Args:
            team_id: Team ID to query
            up_to_date: ISO format date string - only consider games before this date
            
        Returns:
            Dictionary with max attendance for each section: {
                'bleachers': max_bleachers_attendance,
                'lower_tier': max_lower_tier_attendance, 
                'courtside': max_courtside_attendance,
                'luxury_boxes': max_luxury_boxes_attendance
            }
        """
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT 
                    MAX(bleachers_attendance) as max_bleachers,
                    MAX(lower_tier_attendance) as max_lower_tier,
                    MAX(courtside_attendance) as max_courtside,
                    MAX(luxury_boxes_attendance) as max_luxury_boxes
                FROM games 
                WHERE home_team_id = ? 
                AND datetime(date) < datetime(?)
                AND neutral_arena = FALSE
                AND bleachers_attendance IS NOT NULL
                AND lower_tier_attendance IS NOT NULL
                AND courtside_attendance IS NOT NULL
                AND luxury_boxes_attendance IS NOT NULL
                ORDER BY date ASC
            """
            
            cursor = conn.execute(query, [team_id, up_to_date])
            row = cursor.fetchone()
            
            if row:
                return {
                    'bleachers': row[0] or 0,
                    'lower_tier': row[1] or 0,
                    'courtside': row[2] or 0,
                    'luxury_boxes': row[3] or 0
                }
            else:
                return {
                    'bleachers': 0,
                    'lower_tier': 0,
                    'courtside': 0,
                    'luxury_boxes': 0
                }
    
    def get_team_games(self, team_id: str, limit: int = 1000) -> list[GameRecord]:
        """Get all games for a team (both home and away).
        
        Args:
            team_id: Team ID to get games for
            limit: Maximum number of games to return
            
        Returns:
            List of GameRecord objects
        """
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT game_id, id, home_team_id, away_team_id, date, game_type, season,
                       division, country, cup_round, score_home, score_away,
                       bleachers_attendance, lower_tier_attendance, courtside_attendance,
                       luxury_boxes_attendance, total_attendance, neutral_arena,
                       ticket_revenue, calculated_revenue, bleachers_price, lower_tier_price,
                       courtside_price, luxury_boxes_price, created_at, updated_at
                FROM games 
                WHERE home_team_id = ? OR away_team_id = ?
                ORDER BY date DESC
                LIMIT ?
            """
            
            cursor = conn.execute(query, [team_id, team_id, limit])
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
