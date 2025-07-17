"""End-to-end integration tests for the complete pricing collection pipeline."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from bs4 import BeautifulSoup

from bb_arena_optimizer.collecting.improved_pricing_service import ImprovedPricingService
from bb_arena_optimizer.collecting.team_arena_collector import TeamArenaCollector, CollectionResult
from bb_arena_optimizer.storage.database import DatabaseManager
from bb_arena_optimizer.storage.models import GameRecord


@pytest.fixture
def mock_db_manager():
    """Create a mock database manager."""
    return Mock(spec=DatabaseManager)


@pytest.fixture
def pricing_service(mock_db_manager):
    """Create a pricing service with mocked database."""
    return ImprovedPricingService(mock_db_manager)


@pytest.fixture
def arena_collector():
    """Create an arena collector."""
    return TeamArenaCollector()


class TestEndToEndPipeline:
    """Test the complete pricing collection pipeline from arena scraping to pricing assignment."""
    
    def test_complete_pipeline_success(self, arena_collector, pricing_service, mock_db_manager):
        """Test a complete successful pipeline run."""
        # Setup: Mock arena HTML
        arena_html = """
        <html>
        <body>
            <table>
                <tr><td>Date</td><td>Event</td><td>Details</td></tr>
                <tr>
                    <td>6/14/2025</td>
                    <td><a href="/match/134429414/boxscore.aspx">vs Team B</a></td>
                    <td></td>
                </tr>
                <tr>
                    <td>6/7/2025</td>
                    <td>Ticket Price Update</td>
                    <td>Bleachers: 15, Lower Tier: 40, Courtside: 100, Luxury Boxes: 800</td>
                </tr>
                <tr>
                    <td>6/1/2025</td>
                    <td><a href="/match/134429413/boxscore.aspx">@ Team A</a></td>
                    <td>W 80-75</td>
                </tr>
            </table>
        </body>
        </html>
        """
        
        # Setup: Mock database games
        db_games = [
            GameRecord(game_id="134429413", home_team_id=88636, away_team_id=12345, date=datetime(2025, 6, 1)),
            GameRecord(game_id="134429414", home_team_id=88636, away_team_id=67890, date=datetime(2025, 6, 14))
        ]
        mock_db_manager.get_games_for_team.return_value = db_games
        
        # Step 1: Arena collection
        soup = BeautifulSoup(arena_html, 'html.parser')
        with patch.object(arena_collector, '_fetch_arena_webpage', return_value=soup):
            collection_result = arena_collector.collect_team_arena_data(88636)
        
        # Verify arena collection succeeded
        assert collection_result.success
        assert len(collection_result.arena_data["games"]) == 2
        assert len(collection_result.arena_data["pricing_updates"]) == 1
        
        # Step 2: Pricing analysis
        pricing_data = pricing_service.collect_pricing_data(collection_result)
        
        # Verify pricing analysis succeeded
        assert pricing_data.team_id == 88636
        assert len(pricing_data.games) == 2
        
        # Verify games are assigned to correct periods
        before_games = [g for g in pricing_data.games if g.pricing_period == "before_updates"]
        after_games = [g for g in pricing_data.games if g.pricing_period == "after_updates"]
        
        # Game at position 3 (134429413) should be before update at position 2
        # Game at position 1 (134429414) should be after update at position 2
        before_game_ids = {g.game_id for g in before_games}
        after_game_ids = {g.game_id for g in after_games}
        
        assert "134429413" in before_game_ids
        assert "134429414" in after_game_ids
    
    def test_pipeline_with_missing_database_games(self, arena_collector, pricing_service, mock_db_manager):
        """Test pipeline when some arena games are not in database."""
        arena_html = """
        <html>
        <body>
            <table>
                <tr><td>Date</td><td>Event</td><td>Details</td></tr>
                <tr>
                    <td>6/14/2025</td>
                    <td><a href="/match/999999/boxscore.aspx">vs Missing Team</a></td>
                    <td></td>
                </tr>
                <tr>
                    <td>6/1/2025</td>
                    <td><a href="/match/134429413/boxscore.aspx">@ Team A</a></td>
                    <td>W 80-75</td>
                </tr>
            </table>
        </body>
        </html>
        """
        
        # Database only has one of the games
        db_games = [
            GameRecord(game_id="134429413", home_team_id=88636, away_team_id=12345, date=datetime(2025, 6, 1))
        ]
        mock_db_manager.get_games_for_team.return_value = db_games
        
        # Run pipeline
        soup = BeautifulSoup(arena_html, 'html.parser')
        with patch.object(arena_collector, '_fetch_arena_webpage', return_value=soup):
            collection_result = arena_collector.collect_team_arena_data(88636)
        
        pricing_data = pricing_service.collect_pricing_data(collection_result)
        
        # Should only include the game that exists in database
        assert len(pricing_data.games) == 1
        assert pricing_data.games[0].game_id == "134429413"
    
    def test_pipeline_with_network_failure(self, arena_collector, pricing_service, mock_db_manager):
        """Test pipeline behavior when arena scraping fails."""
        # Simulate network failure
        with patch.object(arena_collector, '_fetch_arena_webpage', side_effect=Exception("Network timeout")):
            collection_result = arena_collector.collect_team_arena_data(88636)
        
        # Arena collection should fail gracefully
        assert not collection_result.success
        
        # Pricing service should handle failed collection
        pricing_data = pricing_service.collect_pricing_data(collection_result)
        
        # Should return empty but valid data
        assert pricing_data.team_id == 88636
        assert len(pricing_data.games) == 0
    
    def test_regression_team_88636_scenario(self, arena_collector, pricing_service, mock_db_manager):
        """Test the exact scenario that caused the original bug with team 88636."""
        # Exact HTML structure that caused the duplicate assignment bug
        arena_html = """
        <html>
        <body>
            <table>
                <tr><td>Date</td><td>Event</td><td>Details</td></tr>
                <tr>
                    <td>6/14/2025</td>
                    <td><a href="/match/134429414/boxscore.aspx">vs Other Team</a></td>
                    <td></td>
                </tr>
                <tr>
                    <td>6/7/2025</td>
                    <td>Ticket Price Update</td>
                    <td>Bleachers: 9, Lower Tier: 30, Courtside: 95, Luxury Boxes: 700</td>
                </tr>
                <tr>
                    <td>6/7/2025</td>
                    <td><a href="/match/134429413/boxscore.aspx">vs Dimlorence</a></td>
                    <td>W 74-62</td>
                </tr>
            </table>
        </body>
        </html>
        """
        
        # Database games matching the scenario
        db_games = [
            GameRecord(game_id="134429413", home_team_id=88636, away_team_id=12345, date=datetime(2025, 6, 7)),
            GameRecord(game_id="134429414", home_team_id=88636, away_team_id=67890, date=datetime(2025, 6, 14))
        ]
        mock_db_manager.get_games_for_team.return_value = db_games
        
        # Run complete pipeline
        soup = BeautifulSoup(arena_html, 'html.parser')
        with patch.object(arena_collector, '_fetch_arena_webpage', return_value=soup):
            collection_result = arena_collector.collect_team_arena_data(88636)
        
        pricing_data = pricing_service.collect_pricing_data(collection_result)
        
        # Critical test: Verify game 134429413 is not assigned to multiple periods
        game_periods: dict[str, str] = {}
        for game in pricing_data.games:
            if game.game_id in game_periods:
                pytest.fail(f"Game {game.game_id} assigned to multiple periods: {game_periods[game.game_id]} and {game.pricing_period}")
            game_periods[game.game_id] = game.pricing_period
        
        # Verify specific assignments
        assert game_periods["134429413"] == "before_updates"  # Position 3 > 2
        assert game_periods["134429414"] == "after_updates"   # Position 1 < 2
        
        # Verify each game appears exactly once
        all_game_ids = [g.game_id for g in pricing_data.games]
        unique_game_ids = set(all_game_ids)
        assert len(all_game_ids) == len(unique_game_ids)
    
    def test_complex_multi_update_scenario(self, arena_collector, pricing_service, mock_db_manager):
        """Test a complex scenario with multiple price updates and many games."""
        arena_html = """
        <html>
        <body>
            <table>
                <tr><td>Date</td><td>Event</td><td>Details</td></tr>
                <tr>
                    <td>6/20/2025</td>
                    <td><a href="/match/5/boxscore.aspx">vs Team E</a></td>
                    <td></td>
                </tr>
                <tr>
                    <td>6/18/2025</td>
                    <td>Third Price Update</td>
                    <td>Bleachers: 20, Lower Tier: 50, Courtside: 120, Luxury Boxes: 900</td>
                </tr>
                <tr>
                    <td>6/15/2025</td>
                    <td><a href="/match/4/boxscore.aspx">@ Team D</a></td>
                    <td>L 70-75</td>
                </tr>
                <tr>
                    <td>6/12/2025</td>
                    <td>Second Price Update</td>
                    <td>Bleachers: 15, Lower Tier: 40, Courtside: 100, Luxury Boxes: 800</td>
                </tr>
                <tr>
                    <td>6/10/2025</td>
                    <td><a href="/match/3/boxscore.aspx">vs Team C</a></td>
                    <td>W 85-80</td>
                </tr>
                <tr>
                    <td>6/5/2025</td>
                    <td>First Price Update</td>
                    <td>Bleachers: 12, Lower Tier: 35, Courtside: 90, Luxury Boxes: 700</td>
                </tr>
                <tr>
                    <td>6/3/2025</td>
                    <td><a href="/match/2/boxscore.aspx">@ Team B</a></td>
                    <td>W 90-85</td>
                </tr>
                <tr>
                    <td>6/1/2025</td>
                    <td><a href="/match/1/boxscore.aspx">vs Team A</a></td>
                    <td>W 80-75</td>
                </tr>
            </table>
        </body>
        </html>
        """
        
        # Database games
        db_games = [
            GameRecord(game_id="1", home_team_id=88636, away_team_id=12345, date=datetime(2025, 6, 1)),
            GameRecord(game_id="2", home_team_id=12345, away_team_id=88636, date=datetime(2025, 6, 3)),
            GameRecord(game_id="3", home_team_id=88636, away_team_id=67890, date=datetime(2025, 6, 10)),
            GameRecord(game_id="4", home_team_id=99999, away_team_id=88636, date=datetime(2025, 6, 15)),
            GameRecord(game_id="5", home_team_id=88636, away_team_id=11111, date=datetime(2025, 6, 20))
        ]
        mock_db_manager.get_games_for_team.return_value = db_games
        
        # Run pipeline
        soup = BeautifulSoup(arena_html, 'html.parser')
        with patch.object(arena_collector, '_fetch_arena_webpage', return_value=soup):
            collection_result = arena_collector.collect_team_arena_data(88636)
        
        pricing_data = pricing_service.collect_pricing_data(collection_result)
        
        # Should have 3 periods: before, between, after
        periods = set(g.pricing_period for g in pricing_data.games)
        assert "before_updates" in periods
        assert "between_updates" in periods  
        assert "after_updates" in periods
        
        # Verify no game appears in multiple periods
        game_assignments = {}
        for game in pricing_data.games:
            if game.game_id in game_assignments:
                pytest.fail(f"Game {game.game_id} assigned multiple times")
            game_assignments[game.game_id] = game.pricing_period
        
        # All games should be assigned
        assert len(game_assignments) == 5
        
        # Verify specific assignments based on table positions
        # Position 1: Game 5 (after all updates)
        # Position 2: Third update
        # Position 3: Game 4 (between second and third updates)  
        # Position 4: Second update
        # Position 5: Game 3 (between first and second updates)
        # Position 6: First update
        # Position 7: Game 2 (before all updates)
        # Position 8: Game 1 (before all updates)
        
        assert game_assignments["5"] == "after_updates"      # Position 1
        assert game_assignments["4"] == "between_updates"    # Position 3  
        assert game_assignments["3"] == "between_updates"    # Position 5
        assert game_assignments["2"] == "before_updates"     # Position 7
        assert game_assignments["1"] == "before_updates"     # Position 8


class TestPipelineErrorRecovery:
    """Test error recovery and resilience in the pipeline."""
    
    def test_partial_data_recovery(self, arena_collector, pricing_service, mock_db_manager):
        """Test that pipeline can recover from partial data corruption."""
        # Arena HTML with some corrupted entries
        arena_html = """
        <html>
        <body>
            <table>
                <tr><td>Date</td><td>Event</td><td>Details</td></tr>
                <tr>
                    <td>6/14/2025</td>
                    <td><a href="/match/12345/boxscore.aspx">vs Team A</a></td>
                    <td>W 80-75</td>
                </tr>
                <tr>
                    <td>BAD_DATE</td>
                    <td>Corrupted Price Update</td>
                    <td>Invalid price data</td>
                </tr>
                <tr>
                    <td>6/1/2025</td>
                    <td><a href="/invalid/link">Bad Game Link</a></td>
                    <td>Game with bad link</td>
                </tr>
            </table>
        </body>
        </html>
        """
        
        db_games = [
            GameRecord(game_id="12345", home_team_id=88636, away_team_id=67890, date=datetime(2025, 6, 14))
        ]
        mock_db_manager.get_games_for_team.return_value = db_games
        
        # Run pipeline
        soup = BeautifulSoup(arena_html, 'html.parser')
        with patch.object(arena_collector, '_fetch_arena_webpage', return_value=soup):
            collection_result = arena_collector.collect_team_arena_data(88636)
        
        # Should succeed and recover valid data
        assert collection_result.success
        
        pricing_data = pricing_service.collect_pricing_data(collection_result)
        
        # Should include at least the valid game
        valid_games = [g for g in pricing_data.games if g.game_id == "12345"]
        assert len(valid_games) == 1
    
    def test_empty_response_handling(self, arena_collector, pricing_service, mock_db_manager):
        """Test handling of completely empty responses."""
        # Empty arena response
        arena_html = "<html><body></body></html>"
        
        mock_db_manager.get_games_for_team.return_value = []
        
        # Run pipeline
        soup = BeautifulSoup(arena_html, 'html.parser')
        with patch.object(arena_collector, '_fetch_arena_webpage', return_value=soup):
            collection_result = arena_collector.collect_team_arena_data(88636)
        
        pricing_data = pricing_service.collect_pricing_data(collection_result)
        
        # Should handle gracefully
        assert pricing_data.team_id == 88636
        assert len(pricing_data.games) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
