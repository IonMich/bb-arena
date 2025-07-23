"""Database models for storing BuzzerBeater data."""

from dataclasses import dataclass, asdict
from datetime import datetime, UTC as datetime_utc
from typing import Any, Dict

from bb_arena_optimizer.api.client import BoxscoreData, ScheduleMatchData


@dataclass
class ArenaSnapshot:
    """Represents a snapshot of arena information at a specific time."""

    id: int | None = None
    team_id: str | None = None
    arena_name: str | None = None
    bleachers_capacity: int = 0
    lower_tier_capacity: int = 0
    courtside_capacity: int = 0
    luxury_boxes_capacity: int = 0
    total_capacity: int = 0
    expansion_in_progress: bool = False
    expansion_completion_date: str | None = None
    expansion_cost: float | None = None
    created_at: datetime | None = None

    @classmethod
    def from_api_data(cls, arena_data: dict[str, Any]) -> "ArenaSnapshot":
        """Create ArenaSnapshot from API arena data."""
        return cls(
            team_id=arena_data.get("team_id"),
            arena_name=arena_data.get("name"),
            bleachers_capacity=arena_data["seats"].get("bleachers", 0),
            lower_tier_capacity=arena_data["seats"].get("lower_tier", 0),
            courtside_capacity=arena_data["seats"].get("courtside", 0),
            luxury_boxes_capacity=arena_data["seats"].get("luxury_boxes", 0),
            total_capacity=arena_data.get("total_capacity", 0),
            expansion_in_progress=arena_data.get("expansion", {}).get(
                "in_progress", False
            ),
            expansion_completion_date=arena_data.get("expansion", {}).get(
                "completion_date"
            ),
            expansion_cost=arena_data.get("expansion", {}).get("cost"),
            created_at=datetime.now(datetime_utc)
        )


@dataclass
class PriceSnapshot:
    """Represents ticket prices at a specific time from arena API."""

    id: int | None = None
    team_id: str | None = None
    bleachers_price: int | None = None
    lower_tier_price: int | None = None
    courtside_price: int | None = None
    luxury_boxes_price: int | None = None
    created_at: datetime | None = None

    @classmethod
    def from_api_data(
        cls,
        arena_data: dict[str, Any],
        team_id: str | None = None,
    ) -> "PriceSnapshot":
        """Create PriceSnapshot from API arena data."""
        prices = arena_data.get("prices", {})
        return cls(
            team_id=team_id,
            bleachers_price=int(prices["bleachers"]) if prices.get("bleachers") is not None else None,
            lower_tier_price=int(prices["lower_tier"]) if prices.get("lower_tier") is not None else None,
            courtside_price=int(prices["courtside"]) if prices.get("courtside") is not None else None,
            luxury_boxes_price=int(prices["luxury_boxes"]) if prices.get("luxury_boxes") is not None else None,
            created_at=datetime.now(datetime_utc),
        )


@dataclass
class GameRecord:
    """Represents a game/match record with attendance and revenue data."""

    game_id: str  # From API
    id: int | None = None
    home_team_id: int | None = None  # Home team ID 
    away_team_id: int | None = None  # Away team ID
    date: datetime | None = None
    game_type: str | None = None
    season: int | None = None
    division: str | None = None
    country: str | None = None
    cup_round: str | None = None
    score_home: int | None = None
    score_away: int | None = None

    # Attendance by seat type
    bleachers_attendance: int | None = None
    lower_tier_attendance: int | None = None
    courtside_attendance: int | None = None
    luxury_boxes_attendance: int | None = None
    
    # Game venue information
    neutral_arena: bool = False  # True if game is played at a neutral venue

    # Revenue data (in whole dollars)
    ticket_revenue: int | None = None
    
    # Calculated revenue (computed from attendance * prices, read-only)
    calculated_revenue: int | None = None

    # Pricing at the time of the game (in whole dollars)
    bleachers_price: int | None = None
    lower_tier_price: int | None = None
    courtside_price: int | None = None
    luxury_boxes_price: int | None = None

    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def total_attendance(self) -> int | None:
        """Calculate total attendance from individual section attendances."""
        attendances = [
            self.bleachers_attendance,
            self.lower_tier_attendance,
            self.courtside_attendance,
            self.luxury_boxes_attendance
        ]
        
        # Only calculate if we have at least one non-None attendance value
        valid_attendances = [a for a in attendances if a is not None]
        if not valid_attendances:
            return None
            
        # Sum all valid attendances (treat None as 0)
        return sum(a if a is not None else 0 for a in attendances)

    def to_dict(self) -> Dict[str, Any]:
        """Convert GameRecord to JSON-serializable dictionary."""
        result = asdict(self)
        
        # Convert datetime objects to ISO strings for JSON serialization
        if self.date:
            result['date'] = self.date.isoformat()
        if self.created_at:
            result['created_at'] = self.created_at.isoformat()
        if self.updated_at:
            result['updated_at'] = self.updated_at.isoformat()
            
        # Add computed total_attendance to the dictionary
        result['total_attendance'] = self.total_attendance
        
        return result

    def update_scores_from_schedule(self, schedule_match: ScheduleMatchData) -> None:
        """Update game scores from schedule data.
        
        Args:
            schedule_match: ScheduleMatchData containing scores to update
        """
        if schedule_match["home_score"] is not None:
            self.score_home = schedule_match["home_score"]
        if schedule_match["away_score"] is not None:
            self.score_away = schedule_match["away_score"]
        self.updated_at = datetime.now(datetime_utc)

    @classmethod
    def from_api_data(cls, boxscore_data: BoxscoreData, season: int | None = None) -> "GameRecord":
        """Create GameRecord from a dict of extracted boxscore data.

        Performs extra processing like: 
        - date parsing and conversion to datetime
        - fixing BBM and BBM playoff games to always be neutral
        Args:
            boxscore_data: Boxscore data from the API
        """
        start_date_str = boxscore_data["start_date"].strip()
        if not start_date_str:
            raise ValueError("BoxscoreData start_date is required but was empty after stripping")
        
        try:
            # Handle timezone-aware strings (with Z or +00:00)
            if start_date_str.endswith("Z"):
                # Replace Z with +00:00 for ISO format parsing
                game_date = datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))
            elif "+" in start_date_str or start_date_str.endswith("00:00"):
                # Already has timezone info
                game_date = datetime.fromisoformat(start_date_str)
            else:
                # Assume naive datetime string is in UTC
                naive_datetime = datetime.fromisoformat(start_date_str)
                game_date = naive_datetime.replace(tzinfo=datetime_utc)
        except ValueError as e:
            raise ValueError(f"Invalid start_date format '{start_date_str}': {e}")

        # Determine neutral_arena logic:
        # BBM and BBM playoff are always neutral, regardless of the API field
        if boxscore_data["game_type"] in ["bbm", "bbm.playoff"]:
            is_neutral = True
        else:
            # Use the neutral field from the BoxscoreData
            is_neutral = boxscore_data["neutral"]

        return cls(
            game_id=str(boxscore_data["match_id"]),
            home_team_id=boxscore_data["home_team_id"],
            away_team_id=boxscore_data["away_team_id"],
            date=game_date,
            game_type=boxscore_data["game_type"],
            season=season,
            score_home=boxscore_data["home_score"],
            score_away=boxscore_data["away_score"],
            bleachers_attendance=boxscore_data["bleachers_attendance"],
            lower_tier_attendance=boxscore_data["lower_tier_attendance"],
            courtside_attendance=boxscore_data["courtside_attendance"],
            luxury_boxes_attendance=boxscore_data["luxury_box_attendance"],
            neutral_arena=is_neutral,
            created_at=datetime.now(datetime_utc),
            updated_at=datetime.now(datetime_utc)
        )


@dataclass
class Season:
    """Represents a BuzzerBeater season with start and end dates."""
    
    id: int | None = None
    season_number: int | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    created_at: datetime | None = None
    
    @classmethod
    def from_api_data(cls, season_data: dict[str, Any]) -> "Season":
        """Create Season from API season data."""
        
        start_date = None
        end_date = None
        
        if season_data.get("start"):
            try:
                # Parse ISO format dates from BBAPI
                start_date = datetime.fromisoformat(season_data["start"].replace('Z', '+00:00'))
            except (ValueError, TypeError):
                pass
                
        if season_data.get("end"):
            try:
                # Parse ISO format dates from BBAPI
                end_date = datetime.fromisoformat(season_data["end"].replace('Z', '+00:00'))
            except (ValueError, TypeError):
                pass
        
        return cls(
            season_number=season_data.get("number"),
            start_date=start_date,
            end_date=end_date,
            created_at=datetime.now(datetime_utc)  # Use UTC for consistency
        )


@dataclass
class TeamInfo:
    """Represents cached team information from BuzzerBeater API."""
    
    id: int | None = None
    bb_team_id: str | None = None  # BuzzerBeater team ID
    bb_username: str | None = None  # BuzzerBeater username this info belongs to
    team_name: str | None = None
    short_name: str | None = None
    owner: str | None = None
    league_id: str | None = None
    league_name: str | None = None
    league_level: str | None = None
    country_id: str | None = None
    country_name: str | None = None
    rival_id: str | None = None
    rival_name: str | None = None
    create_date: str | None = None  # Team creation date from BB API
    last_synced: datetime | None = None
    created_at: datetime | None = None
    
    @classmethod
    def from_api_data(cls, team_data: dict[str, Any], username: str) -> "TeamInfo":
        """Create TeamInfo from API team data."""
        return cls(
            bb_team_id=team_data.get("id"),
            bb_username=username,
            team_name=team_data.get("name"),
            short_name=team_data.get("short_name"),
            owner=team_data.get("owner"),
            league_id=team_data.get("league_id"),
            league_name=team_data.get("league"),
            league_level=team_data.get("league_level"),
            country_id=team_data.get("country_id"),
            country_name=team_data.get("country"),
            rival_id=team_data.get("rival_id"),
            rival_name=team_data.get("rival"),
            create_date=team_data.get("create_date"),
            last_synced=datetime.now(datetime_utc),
            created_at=datetime.now(datetime_utc)
        )


@dataclass
class LeagueHierarchy:
    """Represents league hierarchy information for efficient level calculation."""
    
    id: int | None = None
    country_id: int | None = None
    country_name: str | None = None
    league_id: int | None = None  # The league ID
    league_name: str | None = None  # The league name (e.g., "USA I.1" or "A1 Ethniki")
    league_level: int | None = None  # The league level (1=I, 2=II, etc.)
    created_at: datetime | None = None
    
    @classmethod
    def from_api_data(cls, country_id: int, country_name: str, league_id: int,
                     league_name: str, league_level: int) -> "LeagueHierarchy":
        """Create LeagueHierarchy from BB API leagues data."""
        return cls(
            country_id=country_id,
            country_name=country_name,
            league_id=league_id,
            league_name=league_name,
            league_level=league_level,
            created_at=datetime.now(datetime_utc),
        )


@dataclass
class TeamLeagueHistory:
    """Represents a team's league information for a specific season."""
    
    id: int | None = None
    bb_team_id: str | None = None  # BuzzerBeater team ID (the current team ID)
    season: int | None = None
    team_name: str | None = None  # Name of the team in that season (may be different for predecessor teams)
    league_id: str | None = None  # League ID extracted from URL
    league_name: str | None = None  # Full league name like "USA III.1"
    league_level: int | None = None  # Calculated level: 1=I, 2=II, 3=III, etc.
    achievement: str | None = None  # Achievement description (champions, playoffs, etc.)
    is_active_team: bool = True  # False for inactive/predecessor teams (displayed in muted color)
    created_at: datetime | None = None
    
    @classmethod
    def from_webpage_data(
        cls,
        team_id: str,
        season: int,
        team_name: str,
        league_id: str,
        league_name: str,
        league_level: int | None = None,
        achievement: str | None = None,
        is_active_team: bool = True
    ) -> "TeamLeagueHistory":
        """Create TeamLeagueHistory from parsed webpage data."""
        return cls(
            bb_team_id=team_id,
            season=season,
            team_name=team_name,
            league_id=league_id,
            league_name=league_name,
            league_level=league_level,
            achievement=achievement,
            is_active_team=is_active_team,
            created_at=datetime.now(datetime_utc)
        )
    
    def calculate_league_level(self) -> int | None:
        """Calculate league level from league name (e.g., 'USA III.1' -> 3)."""
        if not self.league_name:
            return None
            
        # Extract the Roman numeral from league name
        import re
        roman_match = re.search(r'\b([IVX]+)\.\d+', self.league_name)
        if not roman_match:
            return None
            
        roman_numeral = roman_match.group(1)
        
        # Convert Roman numeral to integer
        roman_to_int = {
            'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5,
            'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10
        }
        
        return roman_to_int.get(roman_numeral)
