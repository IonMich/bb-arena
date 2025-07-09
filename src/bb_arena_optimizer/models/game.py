"""Game and match data models."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class GameType(Enum):
    """Types of basketball games in BuzzerBeater."""

    REGULAR = "Regular"
    TV = "TV"
    CUP = "Cup"
    RELEGATION = "Relegation"
    FRIENDLY = "Friendly"
    QUARTERFINAL = "QF"
    SEMIFINAL = "SF"
    FINAL = "F"
    PLAYOFF = "Playoff"

    @classmethod
    def from_string(cls, game_type_str: str) -> "GameType":
        """Create GameType from string, defaulting to REGULAR if unknown."""
        try:
            # Try exact match first
            return cls(game_type_str)
        except ValueError:
            # Try case-insensitive match
            for game_type in cls:
                if game_type.value.lower() == game_type_str.lower():
                    return game_type
            # Default to regular if no match
            return cls.REGULAR

    def get_demand_multiplier(self) -> float:
        """Get demand multiplier for this game type."""
        multipliers = {
            GameType.REGULAR: 1.0,
            GameType.TV: 1.2,
            GameType.CUP: 1.5,
            GameType.RELEGATION: 1.8,
            GameType.PLAYOFF: 1.6,
            GameType.QUARTERFINAL: 1.7,
            GameType.SEMIFINAL: 1.9,
            GameType.FINAL: 2.2,
            GameType.FRIENDLY: 0.8,
        }
        return multipliers.get(self, 1.0)


@dataclass
class Game:
    """Represents a basketball game/match."""

    game_id: str
    date: datetime
    opponent: str
    is_home: bool
    game_type: GameType
    attendance: dict[str, int] | None = None
    score_home: int | None = None
    score_away: int | None = None
    ticket_revenue: float | None = None

    @classmethod
    def from_api_data(cls, game_data: dict[str, Any]) -> "Game":
        """Create Game instance from API data."""
        # Parse date
        date_str = game_data.get("date", "")
        try:
            game_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except ValueError:
            game_date = datetime.now()

        # Parse game type
        game_type = GameType.from_string(game_data.get("type", "Regular"))

        return cls(
            game_id=game_data.get("id", ""),
            date=game_date,
            opponent=game_data.get("opponent", ""),
            is_home=game_data.get("home", False),
            game_type=game_type,
            score_home=game_data.get("score_home"),
            score_away=game_data.get("score_away"),
            attendance=game_data.get("attendance"),  # Will be None for upcoming games
        )

    def is_completed(self) -> bool:
        """Check if the game has been played."""
        return self.score_home is not None and self.score_away is not None

    def is_upcoming(self) -> bool:
        """Check if the game is in the future."""
        return not self.is_completed() and self.date > datetime.now()

    def did_win(self) -> bool | None:
        """Check if the home team won (only for completed home games)."""
        if not self.is_home or not self.is_completed():
            return None
        if self.score_home is None or self.score_away is None:
            return None
        return self.score_home > self.score_away

    def get_score_differential(self) -> int | None:
        """Get score differential from home team perspective."""
        if not self.is_completed():
            return None
        if self.score_home is None or self.score_away is None:
            return None

        if self.is_home:
            return self.score_home - self.score_away
        else:
            return self.score_away - self.score_home

    def calculate_total_attendance(self) -> int:
        """Calculate total attendance across all seat types."""
        if not self.attendance:
            return 0
        return sum(self.attendance.values())

    def get_fan_sentiment_modifier(self, recent_wins: int, recent_losses: int) -> float:
        """Calculate fan sentiment modifier based on recent performance.

        Args:
            recent_wins: Number of wins in recent games
            recent_losses: Number of losses in recent games

        Returns:
            Multiplier for demand (0.7 to 1.3)
        """
        if recent_wins + recent_losses == 0:
            return 1.0

        win_percentage = recent_wins / (recent_wins + recent_losses)

        # Map win percentage to sentiment multiplier
        if win_percentage >= 0.75:
            return 1.3  # Very positive sentiment
        elif win_percentage >= 0.60:
            return 1.15  # Positive sentiment
        elif win_percentage >= 0.40:
            return 1.0  # Neutral sentiment
        elif win_percentage >= 0.25:
            return 0.85  # Negative sentiment
        else:
            return 0.7  # Very negative sentiment

    def __str__(self) -> str:
        """String representation of the game."""
        home_away = "vs" if self.is_home else "@"
        status = ""

        if self.is_completed():
            if self.is_home:
                status = f" ({self.score_home}-{self.score_away})"
            else:
                status = f" ({self.score_away}-{self.score_home})"

        return f"{self.date.strftime('%m/%d/%Y')} {home_away} {self.opponent} [{self.game_type.value}]{status}"
