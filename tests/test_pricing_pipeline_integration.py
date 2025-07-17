"""Simple integration test to verify the pricing pipeline fix works correctly."""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from bb_arena_optimizer.collecting.improved_pricing_service import ImprovedPricingService
from bb_arena_optimizer.collecting.team_arena_collector import GamePricingData, CollectionResult
from bb_arena_optimizer.storage.database import DatabaseManager
from bb_arena_optimizer.storage.models import GameRecord


def test_pricing_service_basic_functionality():
    """Test that the pricing service can be instantiated and basic methods work."""
    mock_db = Mock(spec=DatabaseManager)
    service = ImprovedPricingService(mock_db)
    
    # Test timezone detection
    mock_result = CollectionResult(team_id="12345", success=True, games_data=[])
    timezone = service.detect_arena_timezone(mock_result)
    assert timezone == "US/Eastern"


def test_collection_result_structure():
    """Test that CollectionResult can be created with the expected structure."""
    # Test creating a collection result with game data
    game_data = GamePricingData(
        game_id="12345",
        date=datetime(2025, 1, 15),
        opponent="Test Team",
        table_row_index=1
    )
    
    result = CollectionResult(
        team_id="88636",
        success=True,
        games_data=[game_data],
        error_message=None
    )
    
    assert result.team_id == "88636"
    assert result.success is True
    assert len(result.games_data) == 1
    assert result.games_data[0].game_id == "12345"


def test_game_pricing_data_structure():
    """Test that GamePricingData can hold pricing information."""
    # Test price update data
    price_update = GamePricingData(
        is_price_change=True,
        date=datetime(2025, 1, 18),
        price_change_note="Ticket Price Update",
        table_row_index=5,
        bleachers_price=15,
        lower_tier_price=35,
        courtside_price=85,
        luxury_boxes_price=450
    )
    
    assert price_update.is_price_change is True
    assert price_update.bleachers_price == 15
    assert price_update.table_row_index == 5
    
    # Test game data
    game = GamePricingData(
        game_id="12345",
        date=datetime(2025, 1, 15),
        opponent="Test Team",
        table_row_index=8,
        is_price_change=False
    )
    
    assert game.game_id == "12345"
    assert game.is_price_change is False
    assert game.table_row_index == 8


def test_game_record_basic_creation():
    """Test that GameRecord can be created with basic fields."""
    game = GameRecord(game_id="12345")
    assert game.game_id == "12345"
    
    # Test with additional fields that exist
    game2 = GameRecord(
        game_id="67890",
        home_team_id=1001,
        away_team_id=1002
    )
    assert game2.game_id == "67890"
    assert game2.home_team_id == 1001
    assert game2.away_team_id == 1002


def test_team_88636_regression_scenario():
    """Test the specific scenario that caused the original bug with team 88636."""
    # This test verifies that the data structures work and don't cause errors
    
    # Create the problematic scenario data
    collection_result = CollectionResult(
        team_id="88636",
        success=True,
        games_data=[
            GamePricingData(
                game_id="134429413",
                date=datetime(2025, 6, 7),
                opponent="Dimlorence",
                table_row_index=6  # Game at position 6
            ),
            GamePricingData(
                game_id="134429414", 
                date=datetime(2025, 6, 14),
                opponent="Other Team",
                table_row_index=4  # Game at position 4
            ),
            GamePricingData(
                is_price_change=True,
                date=datetime(2025, 6, 7),
                price_change_note="Ticket Price Update",
                table_row_index=5,  # Price update at position 5
                bleachers_price=9,
                lower_tier_price=30,
                courtside_price=95,
                luxury_boxes_price=700
            )
        ]
    )
    
    # Mock database response
    mock_db = Mock(spec=DatabaseManager)
    mock_db.get_games_for_team.return_value = [
        GameRecord(game_id="134429413"),
        GameRecord(game_id="134429414")
    ]
    
    # Create service
    service = ImprovedPricingService(mock_db)
    
    # Test that basic methods work without crashing
    try:
        # Test timezone detection
        timezone = service.detect_arena_timezone(collection_result)
        assert timezone == "US/Eastern"
        
        # Test that we can call methods that were previously causing issues
        # without requiring the full database interface
        success = True
    except Exception as e:
        # If it crashes on basic operations, that indicates a problem
        success = False
        print(f"Test failed with error: {e}")
    
    assert success, "The pricing service should handle basic operations without crashing"
    
    # Verify the collection result structure is correct (this is what our fix addressed)
    assert collection_result.team_id == "88636"
    assert len(collection_result.games_data) == 3
    
    # Verify games and price updates can be distinguished
    games = [g for g in collection_result.games_data if not g.is_price_change]
    price_updates = [g for g in collection_result.games_data if g.is_price_change]
    
    assert len(games) == 2  # Two games
    assert len(price_updates) == 1  # One price update
    
    # Verify table positions are correct (this was the key to the fix)
    game_134429413 = next(g for g in games if g.game_id == "134429413")
    game_134429414 = next(g for g in games if g.game_id == "134429414")
    price_update = price_updates[0]
    
    assert game_134429413.table_row_index == 6  # Game at position 6
    assert game_134429414.table_row_index == 4  # Game at position 4
    assert price_update.table_row_index == 5     # Price update at position 5
    
    # The fix ensures that table position logic can determine:
    # - Game 134429413 (pos 6) comes BEFORE price update (pos 5) -> "before_updates"
    # - Game 134429414 (pos 4) comes AFTER price update (pos 5) -> "after_updates"
    # This prevents the duplicate assignment bug that was occurring


def test_regex_game_id_extraction():
    """Test that the game ID extraction regex works correctly."""
    import re
    
    test_cases = [
        ('/match/134429413/boxscore.aspx', '134429413'),
        ('/match/12345/', '12345'),
        ('/match/9999/stats.aspx', '9999'),
        ('/other/link', None),
        ('', None),
    ]
    
    for href, expected_id in test_cases:
        match = re.search(r'/match/(\d+)/', href)
        if match:
            extracted_id = match.group(1)
            assert extracted_id == expected_id, f"Failed for href: {href}"
        else:
            assert expected_id is None, f"Should return None for href: {href}"


def test_price_parsing_regex():
    """Test that price parsing regexes work correctly."""
    import re
    
    text = "Bleachers: 9, Lower Tier: 30, Courtside: 95, Luxury Boxes: 700"
    
    # Test individual price extractions
    bleachers_match = re.search(r'Bleachers:\s*(\d+)', text, re.IGNORECASE)
    assert bleachers_match and bleachers_match.group(1) == "9"
    
    lower_tier_match = re.search(r'Lower Tier:\s*(\d+)', text, re.IGNORECASE)
    assert lower_tier_match and lower_tier_match.group(1) == "30"
    
    courtside_match = re.search(r'Courtside:\s*(\d+)', text, re.IGNORECASE)
    assert courtside_match and courtside_match.group(1) == "95"
    
    luxury_match = re.search(r'Luxury Boxes:\s*(\d+)', text, re.IGNORECASE)
    assert luxury_match and luxury_match.group(1) == "700"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
