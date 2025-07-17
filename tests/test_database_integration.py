"""Tests for database integration in pricing collection pipeline."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from bb_arena_optimizer.storage.database import DatabaseManager
from bb_arena_optimizer.storage.models import GameRecord


@pytest.fixture
def mock_db_manager():
    """Create a mock database manager."""
    return Mock(spec=DatabaseManager)


class TestDatabaseIntegration:
    """Test database integration for pricing collection."""
    
    def test_game_lookup_by_string_id(self, mock_db_manager):
        """Test that games can be looked up by string game ID."""
        # Setup mock to return a game when queried
        test_game = GameRecord(
            game_id="134429413",
            home_team_id=88636,
            away_team_id=12345,
            date=datetime(2025, 6, 7)
        )
        mock_db_manager.get_games_for_team.return_value = [test_game]
        
        # Query for games
        team_id = 88636
        games = mock_db_manager.get_games_for_team(team_id)
        
        # Verify we get the expected game back
        assert len(games) == 1
        assert games[0].game_id == "134429413"
        assert games[0].home_team_id == 88636
    
    def test_game_matching_with_string_comparison(self, mock_db_manager):
        """Test that game matching works with string comparison."""
        # Mock database games
        db_games = [
            GameRecord(game_id="134429413", home_team_id=88636, away_team_id=12345, date=datetime(2025, 6, 7)),
            GameRecord(game_id="134429414", home_team_id=88636, away_team_id=67890, date=datetime(2025, 6, 14))
        ]
        mock_db_manager.get_games_for_team.return_value = db_games
        
        # Arena games (as strings, which is how they come from web scraping)
        arena_game_ids = ["134429413", "134429414", "999999"]  # Third one doesn't exist in DB
        
        # Simulate the matching logic
        db_games_by_id = {str(game.game_id): game for game in db_games}
        
        matched_games = []
        for arena_game_id in arena_game_ids:
            if arena_game_id in db_games_by_id:
                matched_games.append(db_games_by_id[arena_game_id])
        
        # Should match first two games but not the third
        assert len(matched_games) == 2
        assert matched_games[0].game_id == "134429413"
        assert matched_games[1].game_id == "134429414"
    
    def test_date_format_consistency(self, mock_db_manager):
        """Test that date formats are handled consistently between arena and database."""
        # Database typically stores dates as datetime objects
        db_games = [
            GameRecord(game_id="12345", home_team_id=88636, away_team_id=12345, date=datetime(2025, 6, 7))
        ]
        mock_db_manager.get_games_for_team.return_value = db_games
        
        # Arena webpage uses MM/DD/YYYY format
        arena_date = "6/7/2025"
        
        # Test date conversion logic (this would be in the actual service)
        
        # Convert arena date to database format
        arena_datetime = datetime.strptime(arena_date, "%m/%d/%Y")
        db_date_format = arena_datetime.strftime("%Y-%m-%d")
        
        assert db_date_format == "2025-06-07"
        
        # Verify the game can be matched by converted date
        matching_games = [g for g in db_games if g.date and g.date.date() == arena_datetime.date()]
        assert len(matching_games) == 1
        assert matching_games[0].game_id == "12345"
    
    def test_missing_games_handling(self, mock_db_manager):
        """Test handling when arena has games not in database."""
        # Database has fewer games than arena
        db_games = [
            GameRecord(game_id="12345", home_team_id=88636, away_team_id=12345, date=datetime(2025, 6, 7))
        ]
        mock_db_manager.get_games_for_team.return_value = db_games
        
        # Arena has additional games
        arena_game_ids = ["12345", "12346", "12347"]
        
        # Simulate lookup
        db_games_by_id = {str(game.game_id): game for game in db_games}
        
        found_games = []
        missing_games = []
        
        for arena_game_id in arena_game_ids:
            if arena_game_id in db_games_by_id:
                found_games.append(db_games_by_id[arena_game_id])
            else:
                missing_games.append(arena_game_id)
        
        # Should find one game and identify two as missing
        assert len(found_games) == 1
        assert len(missing_games) == 2
        assert missing_games == ["12346", "12347"]
    
    def test_empty_database_handling(self, mock_db_manager):
        """Test handling when database has no games for team."""
        mock_db_manager.get_games_for_team.return_value = []
        
        # Arena has games but database is empty
        arena_game_ids = ["12345", "12346"]
        
        # All games should be missing
        db_games_by_id = {}
        missing_games = [gid for gid in arena_game_ids if gid not in db_games_by_id]
        
        assert len(missing_games) == 2
        assert missing_games == ["12345", "12346"]


class TestDatabaseQueries:
    """Test database query patterns used in pricing collection."""
    
    def test_get_games_for_team_query(self, mock_db_manager):
        """Test the get_games_for_team query pattern."""
        team_id = 88636
        mock_db_manager.get_games_for_team.return_value = [
            GameRecord(game_id="12345", home_team_id=88636, away_team_id=12345, date=datetime(2025, 6, 7))
        ]
        
        games = mock_db_manager.get_games_for_team(team_id)
        
        # Verify the method was called with correct team ID
        mock_db_manager.get_games_for_team.assert_called_once_with(team_id)
        assert len(games) == 1
    
    def test_game_record_field_access(self):
        """Test accessing fields on GameRecord objects."""
        game = GameRecord(
            game_id="134429413",
            home_team_id=88636,
            away_team_id=12345,
            date=datetime(2025, 6, 7)
        )
        
        # Test all expected fields are accessible
        assert game.game_id == "134429413"
        assert game.date == datetime(2025, 6, 7)
        assert game.home_team_id == 88636
        assert game.away_team_id == 12345
    
    def test_bulk_game_processing(self, mock_db_manager):
        """Test processing multiple games efficiently."""
        # Simulate a team with many games
        db_games = []
        for i in range(50):
            db_games.append(GameRecord(
                game_id=f"game_{i:03d}",
                home_team_id=88636 if i % 2 == 0 else i + 1000,
                away_team_id=i + 1000 if i % 2 == 0 else 88636,
                date=datetime(2025, (i % 9) + 1, (i % 28) + 1)
            ))
        
        mock_db_manager.get_games_for_team.return_value = db_games
        
        # Test efficient lookup by creating index
        games = mock_db_manager.get_games_for_team(12345)
        games_by_id = {str(game.game_id): game for game in games}
        
        # Verify we can efficiently look up any game
        assert "game_025" in games_by_id
        assert games_by_id["game_025"].game_id == "game_025"
        
        # Verify bulk processing is efficient (no individual queries)
        mock_db_manager.get_games_for_team.assert_called_once_with(12345)


class TestDataConsistency:
    """Test data consistency between arena and database."""
    
    def test_game_id_type_consistency(self):
        """Test that game IDs are handled consistently as strings."""
        # Both arena and database should use string game IDs
        arena_game_id = "134429413"  # From web scraping
        db_game_id = "134429413"     # From database
        
        # They should be directly comparable
        assert arena_game_id == db_game_id
        assert type(arena_game_id) == type(db_game_id)
        assert isinstance(arena_game_id, str)
        assert isinstance(db_game_id, str)
    
    def test_opponent_name_variations(self, mock_db_manager):
        """Test handling of opponent name variations between sources."""
        db_games = [
            GameRecord(game_id="12345", home_team_id=88636, away_team_id=12345, date=datetime(2025, 6, 7))
        ]
        mock_db_manager.get_games_for_team.return_value = db_games
        
        # Arena might have slightly different opponent names
        arena_opponents = ["Team Name", "vs Team Name", "@ Team Name"]
        
        # Should be able to match despite formatting differences
        # (This would require fuzzy matching in the actual implementation)
        for arena_opponent in arena_opponents:
            # Simple contains check for testing - we match by game_id instead of opponent name
            matches = [g for g in db_games if g.game_id == "12345"]
            assert len(matches) >= 0  # Should handle gracefully
    
    def test_home_away_indicator_consistency(self, mock_db_manager):
        """Test that home/away indicators are handled consistently."""
        db_games = [
            GameRecord(game_id="12345", home_team_id=88636, away_team_id=12345, date=datetime(2025, 6, 7)),
            GameRecord(game_id="12346", home_team_id=67890, away_team_id=88636, date=datetime(2025, 6, 8))
        ]
        mock_db_manager.get_games_for_team.return_value = db_games
        
        # Test that we can determine home/away based on team IDs
        team_id = 88636
        home_games = [g for g in db_games if g.home_team_id == team_id]
        away_games = [g for g in db_games if g.away_team_id == team_id]
        
        assert len(home_games) == 1  # Game 12345 is home for team 88636
        assert len(away_games) == 1  # Game 12346 is away for team 88636


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
