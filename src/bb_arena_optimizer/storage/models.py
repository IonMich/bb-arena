"""Database models for storing BuzzerBeater data."""

from dataclasses import dataclass
from datetime import datetime, UTC as datetime_utc
from typing import Any


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
    total_attendance: int | None = None
    
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

    @classmethod
    def from_api_data(
        cls, game_data: dict[str, Any], home_team_id: int | None = None, away_team_id: int | None = None
    ) -> "GameRecord":
        """Create GameRecord from API game data.
        
        Args:
            game_data: Game data from the API
            home_team_id: ID of the home team (required)
            away_team_id: ID of the away team (required)
        """
        # Validate input
        if not game_data or not isinstance(game_data, dict):
            raise ValueError("game_data must be a non-empty dictionary")
        
        if home_team_id is None or away_team_id is None:
            raise ValueError("Both home_team_id and away_team_id are required")
        
        # Parse date
        game_date = None
        if game_data.get("date"):
            import contextlib

            with contextlib.suppress(ValueError, AttributeError):
                game_date = datetime.fromisoformat(
                    game_data["date"].replace("Z", "+00:00")
                )

        # Extract attendance data if available
        attendance_data = game_data.get("attendance") or {}
        total_attendance = None
        if attendance_data and isinstance(attendance_data, dict):
            attendance_sum = sum(v for v in attendance_data.values() if isinstance(v, int | float))
            total_attendance = int(attendance_sum) if attendance_sum else None

        # Convert revenue to integer dollars (from float or string)
        ticket_revenue = None
        if game_data.get("ticket_revenue") is not None:
            try:
                ticket_revenue = int(float(game_data["ticket_revenue"]))
            except (ValueError, TypeError):
                pass

        # Convert price fields to integer dollars
        def to_int_dollars(value) -> int | None:
            if value is None:
                return None
            try:
                return int(float(value))
            except (ValueError, TypeError):
                return None

        # Determine neutral_arena logic:
        game_type = game_data.get("type")
        # BBM and BBM playoff are always neutral, regardless of the field
        if game_type in ["bbm", "bbm.playoff"]:
            is_neutral = True
        else:
            # Use the neutral field from the API if present, else fallback to False
            is_neutral = bool(game_data.get("neutral", 0))

        # If neutral, clear prices
        if is_neutral:
            bleachers_price = None
            lower_tier_price = None
            courtside_price = None
            luxury_boxes_price = None
        else:
            bleachers_price = to_int_dollars(game_data.get("bleachers_price"))
            lower_tier_price = to_int_dollars(game_data.get("lower_tier_price"))
            courtside_price = to_int_dollars(game_data.get("courtside_price"))
            luxury_boxes_price = to_int_dollars(game_data.get("luxury_boxes_price"))

        return cls(
            game_id=game_data.get("id", ""),
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            date=game_date,
            game_type=game_type,
            season=game_data.get("season"),
            division=game_data.get("division"),
            country=game_data.get("country"),
            cup_round=game_data.get("cup_round"),
            score_home=game_data.get("score_home"),
            score_away=game_data.get("score_away"),
            bleachers_attendance=attendance_data.get("bleachers") if isinstance(attendance_data, dict) else None,
            lower_tier_attendance=attendance_data.get("lower_tier") if isinstance(attendance_data, dict) else None,
            courtside_attendance=attendance_data.get("courtside") if isinstance(attendance_data, dict) else None,
            luxury_boxes_attendance=attendance_data.get("luxury_boxes") if isinstance(attendance_data, dict) else None,
            total_attendance=total_attendance,
            neutral_arena=is_neutral,
            ticket_revenue=ticket_revenue,
            bleachers_price=bleachers_price,
            lower_tier_price=lower_tier_price,
            courtside_price=courtside_price,
            luxury_boxes_price=luxury_boxes_price,
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
