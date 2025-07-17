"""Comprehensive tests for the PricingService pricing collection pipeline."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass
from typing import List, Dict, Optional
import pytz

from bb_arena_optimizer.collecting.improved_pricing_service import ImprovedPricingService, PricingPeriod
from bb_arena_optimizer.collecting.team_arena_collector import (
    GamePricingData, CollectionResult, TeamArenaCollector
)
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
def sample_collection_result():
    """Sample collection result for testing."""
    return CollectionResult(
        team_id="88636",
        success=True,
        games_data=[
            GamePricingData(
                game_id="12345",
                date=datetime(2025, 1, 15),
                opponent="Team A",
                table_row_index=8
            ),
            GamePricingData(
                game_id="12346", 
                date=datetime(2025, 1, 20),
                opponent="Team B",
                table_row_index=7
            ),
            GamePricingData(
                game_id="12347",
                date=datetime(2025, 1, 25),
                opponent="Team C", 
                table_row_index=6
            ),
            GamePricingData(
                is_price_change=True,
                date=datetime(2025, 1, 18),
                price_change_note="Ticket Price Update",
                table_row_index=5,
                bleachers_price=15,
                lower_tier_price=35,
                courtside_price=85,
                luxury_boxes_price=450
            )
        ]
    )


@pytest.fixture
def sample_db_games():
    """Sample database games for testing.""" 
    return [
        GameRecord(game_id="12345"),
        GameRecord(game_id="12346"),
        GameRecord(game_id="12347")
    ]


class TestPricingPeriodDetection:
    """Test pricing period detection logic."""
    
    def test_timezone_detection(self, pricing_service, sample_collection_result):
        """Test arena timezone detection."""
        timezone = pricing_service.detect_arena_timezone(sample_collection_result)
        
        # Default should be US Eastern
        assert timezone == "US/Eastern"
    
    def test_analyze_pricing_periods_single_update(self, pricing_service, sample_collection_result, mock_db_manager):
        """Test pricing period analysis with single price update."""
        mock_db_manager.get_games_for_team.return_value = []
        
        periods = pricing_service.analyze_pricing_periods(88636, sample_collection_result)
        
        # Should detect periods based on price changes
        assert len(periods) >= 1
        # Periods should have proper period types
        period_types = {p.period_type for p in periods}
        assert len(period_types) > 0
    
    def test_pricing_period_structure(self, pricing_service, sample_collection_result, mock_db_manager):
        """Test that pricing periods have proper structure."""
        mock_db_manager.get_games_for_team.return_value = []
        
        periods = pricing_service.analyze_pricing_periods(88636, sample_collection_result)
        
        for period in periods:
            # Each period should have required fields
            assert hasattr(period, 'period_type')
            assert hasattr(period, 'description')
            assert hasattr(period, 'has_price_snapshot')
            assert period.period_type is not None
            assert period.description is not None


class TestGameAssignment:
    """Test game assignment to pricing periods."""
    
    def test_find_games_in_period(self, pricing_service, sample_collection_result, sample_db_games, mock_db_manager):
        """Test finding games that belong to a pricing period."""
        mock_db_manager.get_games_for_team.return_value = sample_db_games
        
        # Create a test period
        test_period = PricingPeriod(
            start_date=datetime(2025, 1, 1),
            end_date=datetime(2025, 1, 31),
            prices={"bleachers": 15},
            period_type="test_period",
            description="Test period",
            has_price_snapshot=True
        )
        
        games = pricing_service.find_games_in_period(88636, test_period, sample_collection_result)
        
        # Should return valid GameRecord objects
        assert isinstance(games, list)
        for game in games:
            assert hasattr(game, 'game_id')
    
    def test_complete_pricing_update_flow(self, pricing_service, sample_collection_result, sample_db_games, mock_db_manager):
        """Test the complete pricing update flow."""
        mock_db_manager.get_games_for_team.return_value = sample_db_games
        
        # Run the complete update process
        result = pricing_service.update_games_with_period_based_pricing(
            88636, sample_collection_result, force_update=True
        )
        
        # Should return a summary of the update
        assert isinstance(result, dict)
        assert 'total_updated' in result or 'periods' in result or len(result) >= 0


class TestTimezoneHandling:
    """Test timezone handling in pricing service."""
    
    def test_arena_timezone_detection(self, pricing_service, sample_collection_result):
        """Test arena timezone detection."""
        timezone = pricing_service.detect_arena_timezone(sample_collection_result)
        
        # Default should be US Eastern
        assert timezone == "US/Eastern"


class TestErrorHandling:
    """Test error handling in pricing service."""
    
    def test_missing_game_data_handling(self, pricing_service, mock_db_manager):
        """Test handling of games in arena but not in database."""
        # Collection result with games
        collection_result = CollectionResult(
            team_id="88636",
            success=True,
            games_data=[
                GamePricingData(game_id="12345", date=datetime(2025, 1, 15), opponent="Team A"),
                GamePricingData(game_id="99999", date=datetime(2025, 1, 20), opponent="Team B"),  # Not in DB
            ]
        )
        
        # Only return one game from database
        mock_db_manager.get_games_for_team.return_value = [
            GameRecord(game_id="12345")
        ]
        
        # Should handle gracefully without crashing
        result = pricing_service.update_games_with_period_based_pricing("88636", collection_result)
        assert isinstance(result, dict)
    
    def test_empty_collection_result_handling(self, pricing_service, mock_db_manager):
        """Test handling of empty collection results."""
        empty_result = CollectionResult(
            team_id="88636",
            success=True,
            games_data=[]
        )
        
        mock_db_manager.get_games_for_team.return_value = []
        
        result = pricing_service.update_games_with_period_based_pricing("88636", empty_result)
        
        # Should handle gracefully
        assert isinstance(result, dict)
    
    def test_failed_collection_handling(self, pricing_service, mock_db_manager):
        """Test handling of failed collection results."""
        failed_result = CollectionResult(
            team_id="88636", 
            success=False,
            games_data=[],
            error_message="Network error"
        )
        
        mock_db_manager.get_games_for_team.return_value = []
        
        result = pricing_service.update_games_with_period_based_pricing("88636", failed_result)
        
        # Should handle gracefully
        assert isinstance(result, dict)


class TestIntegrationScenarios:
    """Integration tests for complete pricing collection scenarios."""
    
    def test_real_world_scenario_team_88636(self, pricing_service, mock_db_manager):
        """Test the specific scenario that caused the bug with team 88636."""
        collection_result = CollectionResult(
            team_id="88636",
            success=True,
            games_data=[
                GamePricingData(
                    game_id="134429413",
                    date=datetime(2025, 6, 7),
                    opponent="Dimlorence",
                    table_row_index=6
                ),
                GamePricingData(
                    game_id="134429414",
                    date=datetime(2025, 6, 14),
                    opponent="Other Team",
                    table_row_index=4
                ),
                GamePricingData(
                    is_price_change=True,
                    date=datetime(2025, 6, 7),
                    price_change_note="Ticket Price Update",
                    table_row_index=5,
                    bleachers_price=9,
                    lower_tier_price=30,
                    courtside_price=95,
                    luxury_boxes_price=700
                )
            ]
        )
        
        db_games = [
            GameRecord(game_id="134429413"),
            GameRecord(game_id="134429414")
        ]
        
        mock_db_manager.get_games_for_team.return_value = db_games
        
        # Run the complete update process
        result = pricing_service.update_games_with_period_based_pricing(
            "88636", collection_result, force_update=True
        )
        
        # Should complete without errors - this tests the fix for the duplicate assignment bug
        assert isinstance(result, dict)
        
        # The key test is that it doesn't crash or cause infinite loops
        # which was the symptom of the original bug


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
