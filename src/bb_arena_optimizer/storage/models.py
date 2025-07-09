"""Database models for storing BuzzerBeater data."""

from dataclasses import dataclass
from datetime import datetime
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
            created_at=datetime.now(),
        )


@dataclass
class PriceSnapshot:
    """Represents ticket prices at a specific time."""

    id: int | None = None
    team_id: str | None = None
    bleachers_price: float | None = None
    lower_tier_price: float | None = None
    courtside_price: float | None = None
    luxury_boxes_price: float | None = None
    created_at: datetime | None = None
    game_id: str | None = None  # If associated with a specific game

    @classmethod
    def from_api_data(
        cls,
        arena_data: dict[str, Any],
        team_id: str | None = None,
        game_id: str | None = None,
    ) -> "PriceSnapshot":
        """Create PriceSnapshot from API arena data."""
        return cls(
            team_id=team_id,
            bleachers_price=arena_data["prices"].get("bleachers"),
            lower_tier_price=arena_data["prices"].get("lower_tier"),
            courtside_price=arena_data["prices"].get("courtside"),
            luxury_boxes_price=arena_data["prices"].get("luxury_boxes"),
            created_at=datetime.now(),
            game_id=game_id,
        )


@dataclass
class GameRecord:
    """Represents a game/match record with attendance and revenue data."""

    game_id: str  # From API
    id: int | None = None
    team_id: str | None = None
    date: datetime | None = None
    opponent: str | None = None
    is_home: bool = False
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

    # Revenue data
    ticket_revenue: float | None = None

    # Pricing at the time of the game (if available)
    bleachers_price: float | None = None
    lower_tier_price: float | None = None
    courtside_price: float | None = None
    luxury_boxes_price: float | None = None

    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_api_data(
        cls, game_data: dict[str, Any], team_id: str | None = None
    ) -> "GameRecord":
        """Create GameRecord from API game data."""
        # Validate input
        if not game_data or not isinstance(game_data, dict):
            raise ValueError("game_data must be a non-empty dictionary")
        
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

        return cls(
            game_id=game_data.get("id", ""),
            team_id=team_id,
            date=game_date,
            opponent=game_data.get("opponent"),
            is_home=game_data.get("home", False),
            game_type=game_data.get("type"),
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
            ticket_revenue=game_data.get("ticket_revenue"),
            created_at=datetime.now(),
        )
