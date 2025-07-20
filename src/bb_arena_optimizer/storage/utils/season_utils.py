"""Season management database operations."""

import sqlite3
from datetime import datetime, UTC as datetime_utc
from pathlib import Path
from typing import Any

from ..models import Season
from ...utils.logging_config import get_logger

logger = get_logger(__name__)


class SeasonManager:
    """Manages season database operations."""
    
    def __init__(self, db_path: str | Path):
        """Initialize season manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
    
    def save_seasons(self, seasons: list[Season]) -> None:
        """Save multiple seasons to database.
        
        Args:
            seasons: List of Season objects to save
        """
        with sqlite3.connect(self.db_path) as conn:
            for season in seasons:
                conn.execute("""
                    INSERT OR REPLACE INTO seasons 
                    (season_number, start_date, end_date, created_at)
                    VALUES (?, ?, ?, ?)
                """, (
                    season.season_number,
                    season.start_date.isoformat() if season.start_date else None,
                    season.end_date.isoformat() if season.end_date else None,
                    season.created_at.isoformat() if season.created_at else datetime.now(datetime_utc).isoformat()
                ))
            conn.commit()
            logger.info(f"Saved {len(seasons)} seasons to database")
    
    def get_all_seasons(self) -> list[Season]:
        """Get all seasons from database.
        
        Returns:
            List of Season objects ordered by season number
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT season_number, start_date, end_date, created_at
                FROM seasons 
                ORDER BY season_number
            """)
            
            seasons = []
            for row in cursor.fetchall():
                seasons.append(Season(
                    id=row[0],  # season_number is now the primary key/id
                    season_number=row[0],
                    start_date=datetime.fromisoformat(row[1]) if row[1] else None,
                    end_date=datetime.fromisoformat(row[2]) if row[2] else None,
                    created_at=datetime.fromisoformat(row[3]) if row[3] else None,
                ))
            
            return seasons
    
    def get_current_season(self) -> Season | None:
        """Get the current season based on today's date.
        
        Returns:
            Current Season object or None if no season found
        """
        now = datetime.now(datetime_utc)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT season_number, start_date, end_date, created_at
                FROM seasons 
                WHERE datetime(start_date) <= datetime(?) AND (end_date IS NULL OR datetime(end_date) >= datetime(?))
                ORDER BY season_number DESC
                LIMIT 1
            """, (now.isoformat(), now.isoformat()))
            
            row = cursor.fetchone()
            if row:
                return Season(
                    id=row[0],  # season_number is now the primary key/id
                    season_number=row[0],
                    start_date=datetime.fromisoformat(row[1]) if row[1] else None,
                    end_date=datetime.fromisoformat(row[2]) if row[2] else None,
                    created_at=datetime.fromisoformat(row[3]) if row[3] else None,
                )
            
            return None
    
    def get_latest_season(self) -> Season | None:
        """Get the latest season by number.
        
        Returns:
            Latest Season object or None if no seasons found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT season_number, start_date, end_date, created_at
                FROM seasons 
                ORDER BY season_number DESC
                LIMIT 1
            """)
            
            row = cursor.fetchone()
            if row:
                return Season(
                    id=row[0],  # season_number is now the primary key/id
                    season_number=row[0],
                    start_date=datetime.fromisoformat(row[1]) if row[1] else None,
                    end_date=datetime.fromisoformat(row[2]) if row[2] else None,
                    created_at=datetime.fromisoformat(row[3]) if row[3] else None,
                )
            
            return None
    
    def should_update_seasons(self) -> bool:
        """Check if seasons should be updated from API.
        
        Returns:
            True if seasons should be updated
        """
        latest_season = self.get_latest_season()
        if not latest_season:
            return True

        now = datetime.now(datetime_utc)

        # If the latest season has an end date and it has passed, we might need new seasons
        if latest_season.end_date:
            # Ensure both datetimes are timezone-aware for comparison
            end_date = latest_season.end_date
            if end_date.tzinfo is None:
                # If loaded date is naive, assume it's UTC
                end_date = end_date.replace(tzinfo=datetime_utc)
            if end_date < now:
                return True
            
        # If the latest season doesn't have an end date, check if it's been running too long
        # by comparing to historical season durations
        if not latest_season.end_date and latest_season.start_date:
            start_date = latest_season.start_date
            if start_date.tzinfo is None:
                # If loaded date is naive, assume it's UTC
                start_date = start_date.replace(tzinfo=datetime_utc)
            current_season_duration = (now - start_date).days
            
            # Get the maximum duration of all completed seasons as our threshold
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT MAX(
                        JULIANDAY(end_date) - JULIANDAY(start_date)
                    ) as max_duration_days
                    FROM seasons 
                    WHERE start_date IS NOT NULL 
                    AND end_date IS NOT NULL
                """)
                result = cursor.fetchone()
                max_historical_duration = result[0] if result and result[0] else 180  # fallback to 180 days
                
            # If current season has been running longer than any historical season, update
            if current_season_duration > max_historical_duration:
                return True
                
        # Check if we haven't updated seasons in a while (every 7 days)
        if latest_season.created_at:
            created_at = latest_season.created_at
            if created_at.tzinfo is None:
                # If loaded date is naive, assume it's UTC
                created_at = created_at.replace(tzinfo=datetime_utc)
            days_since_update = (now - created_at).days
            if days_since_update > 7:
                return True
            
        return False

    def get_season_for_date(self, date_str: str) -> int | None:
        """Get the season number that was active for a given date.
        
        Args:
            date_str: Date string in ISO format (e.g., "2022-04-24T21:28:00Z")
            
        Returns:
            Season number if found, None otherwise
        """
        if not date_str:
            return None
            
        try:
            # Parse the date string, handling timezone info
            target_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            # Convert to naive datetime for comparison
            if target_date.tzinfo is not None:
                target_date = target_date.replace(tzinfo=None)
        except (ValueError, TypeError):
            logger.warning(f"Could not parse date: {date_str}")
            return None
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT season_number
                FROM seasons 
                WHERE datetime(start_date) <= datetime(?) AND (end_date IS NULL OR datetime(end_date) >= datetime(?))
                ORDER BY season_number DESC
                LIMIT 1
            """, (target_date.isoformat(), target_date.isoformat()))
            
            row = cursor.fetchone()
            if row:
                return row[0]
            
            # If no exact match, find the season that started before this date
            cursor = conn.execute("""
                SELECT season_number
                FROM seasons 
                WHERE datetime(start_date) <= datetime(?)
                ORDER BY season_number DESC
                LIMIT 1
            """, (target_date.isoformat(),))
            
            row = cursor.fetchone()
            if row:
                return row[0]
            
            return None

    def get_minimum_season_for_team(self, team_id: str) -> int | None:
        """Get the minimum season for a team based on its creation date.
        
        Args:
            team_id: Team ID to get minimum season for
            
        Returns:
            Minimum season number, or None if team info not found
        """
        # First try to get team info by team ID, prioritizing records with create_date
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT create_date
                FROM team_info 
                WHERE bb_team_id = ? AND create_date IS NOT NULL
                ORDER BY last_synced DESC
                LIMIT 1
            """, (team_id,))
            
            row = cursor.fetchone()
            if row and row[0]:
                return self.get_season_for_date(row[0])
            
            return None
