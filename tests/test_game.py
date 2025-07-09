"""Tests for Game and GameType models."""

from datetime import datetime

from bb_arena_optimizer.models.game import Game, GameType


def test_game_type_from_string():
    """Test GameType creation from string values."""
    assert GameType.from_string("Regular") == GameType.REGULAR
    assert GameType.from_string("Cup") == GameType.CUP
    assert GameType.from_string("tv") == GameType.TV  # Case insensitive
    assert GameType.from_string("Unknown") == GameType.REGULAR  # Default


def test_game_type_demand_multipliers():
    """Test demand multipliers for different game types."""
    assert GameType.REGULAR.get_demand_multiplier() == 1.0
    assert GameType.TV.get_demand_multiplier() == 1.2
    assert GameType.CUP.get_demand_multiplier() == 1.5
    assert GameType.RELEGATION.get_demand_multiplier() == 1.8
    assert GameType.FINAL.get_demand_multiplier() == 2.2
    assert GameType.FRIENDLY.get_demand_multiplier() == 0.8


def test_game_creation_from_api_data():
    """Test Game creation from API data."""
    api_data = {
        "id": "12345",
        "date": "2025-07-15T19:00:00Z",
        "opponent": "Test Team",
        "home": True,
        "type": "Cup",
        "score_home": 85,
        "score_away": 78,
    }

    game = Game.from_api_data(api_data)

    assert game.game_id == "12345"
    assert game.opponent == "Test Team"
    assert game.is_home is True
    assert game.game_type == GameType.CUP
    assert game.score_home == 85
    assert game.score_away == 78


def test_game_status_checks():
    """Test game status checking methods."""
    # Completed game
    completed_game = Game(
        game_id="1",
        date=datetime(2025, 7, 1),
        opponent="Team A",
        is_home=True,
        game_type=GameType.REGULAR,
        score_home=90,
        score_away=85,
    )

    assert completed_game.is_completed()
    assert not completed_game.is_upcoming()
    assert completed_game.did_win() is True
    assert completed_game.get_score_differential() == 5

    # Upcoming game
    upcoming_game = Game(
        game_id="2",
        date=datetime(2025, 12, 1),  # Future date
        opponent="Team B",
        is_home=True,
        game_type=GameType.TV,
    )

    assert not upcoming_game.is_completed()
    assert upcoming_game.is_upcoming()
    assert upcoming_game.did_win() is None
    assert upcoming_game.get_score_differential() is None


def test_fan_sentiment_modifier():
    """Test fan sentiment calculation based on recent performance."""
    game = Game(
        game_id="1",
        date=datetime(2025, 7, 15),
        opponent="Test Team",
        is_home=True,
        game_type=GameType.REGULAR,
    )

    # Test different win/loss scenarios
    assert game.get_fan_sentiment_modifier(8, 2) == 1.3  # 80% wins - very positive
    assert game.get_fan_sentiment_modifier(6, 4) == 1.15  # 60% wins - positive
    assert game.get_fan_sentiment_modifier(5, 5) == 1.0  # 50% wins - neutral
    assert game.get_fan_sentiment_modifier(3, 7) == 0.85  # 30% wins - negative
    assert game.get_fan_sentiment_modifier(1, 9) == 0.7  # 10% wins - very negative
    assert game.get_fan_sentiment_modifier(0, 0) == 1.0  # No games - neutral


def test_attendance_calculation():
    """Test total attendance calculation."""
    game = Game(
        game_id="1",
        date=datetime(2025, 7, 15),
        opponent="Test Team",
        is_home=True,
        game_type=GameType.REGULAR,
        attendance={
            "bleachers": 8000,
            "lower_tier": 1500,
            "courtside": 400,
            "luxury_boxes": 35,
        },
    )

    assert game.calculate_total_attendance() == 9935

    # Test with no attendance data
    game_no_attendance = Game(
        game_id="2",
        date=datetime(2025, 7, 16),
        opponent="Test Team 2",
        is_home=True,
        game_type=GameType.REGULAR,
    )

    assert game_no_attendance.calculate_total_attendance() == 0
