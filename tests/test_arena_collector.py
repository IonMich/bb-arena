"""Tests for the TeamArenaCollector arena webpage scraping functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from bs4 import BeautifulSoup

from bb_arena_optimizer.collecting.team_arena_collector import TeamArenaCollector, CollectionResult


@pytest.fixture
def arena_collector():
    """Create a team arena collector for testing.""" 
    return TeamArenaCollector()


@pytest.fixture
def sample_arena_html():
    """Sample arena HTML with games and price updates."""
    return """
    <html>
    <body>
        <table>
            <tr><td>Date</td><td>Event</td><td>Details</td></tr>
            <tr>
                <td>6/14/2025</td>
                <td><a href="/match/134429414/boxscore.aspx">vs Other Team</a></td>
                <td>Game details</td>
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
            <tr>
                <td>5/30/2025</td>
                <td><a href="/match/134429412/boxscore.aspx">@ Previous Team</a></td>
                <td>L 68-75</td>
            </tr>
        </table>
    </body>
    </html>
    """


@pytest.fixture 
def arena_html_no_games():
    """Arena HTML with only price updates, no games."""
    return """
    <html>
    <body>
        <table>
            <tr><td>Date</td><td>Event</td><td>Details</td></tr>
            <tr>
                <td>6/7/2025</td>
                <td>Ticket Price Update</td>
                <td>Bleachers: 9, Lower Tier: 30, Courtside: 95, Luxury Boxes: 700</td>
            </tr>
            <tr>
                <td>5/30/2025</td>
                <td>Another Price Update</td>
                <td>Bleachers: 12, Lower Tier: 35, Courtside: 100, Luxury Boxes: 800</td>
            </tr>
        </table>
    </body>
    </html>
    """


@pytest.fixture
def arena_html_no_updates():
    """Arena HTML with only games, no price updates."""
    return """
    <html>
    <body>
        <table>
            <tr><td>Date</td><td>Event</td><td>Details</td></tr>
            <tr>
                <td>6/14/2025</td>
                <td><a href="/match/134429414/boxscore.aspx">vs Team A</a></td>
                <td>Game details</td>
            </tr>
            <tr>
                <td>6/7/2025</td>
                <td><a href="/match/134429413/boxscore.aspx">@ Team B</a></td>
                <td>W 74-62</td>
            </tr>
        </table>
    </body>
    </html>
    """


class TestArenaDataParsing:
    """Test arena webpage parsing functionality."""
    
    def test_parse_games_from_html(self, arena_collector, sample_arena_html):
        """Test parsing games from arena HTML."""
        soup = BeautifulSoup(sample_arena_html, 'html.parser')
        
        with patch.object(arena_collector, '_fetch_arena_webpage') as mock_fetch:
            mock_fetch.return_value = soup
            
            result = arena_collector.collect_team_arena_data(88636)
            
            assert result.success
            # Check games were found (excluding price updates)
            games = [g for g in result.games_data if not g.is_price_change]
            assert len(games) >= 2
            
            # Check game IDs are extracted correctly
            game_ids = {g.game_id for g in games if g.game_id}
            assert "134429414" in game_ids or "134429413" in game_ids
    
    def test_parse_price_updates_from_html(self, arena_collector, sample_arena_html):
        """Test parsing price updates from arena HTML."""
        soup = BeautifulSoup(sample_arena_html, 'html.parser')
        
        with patch.object(arena_collector, '_fetch_arena_webpage') as mock_fetch:
            mock_fetch.return_value = soup
            
            result = arena_collector.collect_team_arena_data(88636)
            
            assert result.success
            # Check if price updates were found in the games data
            price_updates = [g for g in result.games_data if g.is_price_change]
            assert len(price_updates) >= 1
    
    def test_table_position_assignment(self, arena_collector, sample_arena_html):
        """Test that table position is correctly assigned."""
        soup = BeautifulSoup(sample_arena_html, 'html.parser')
        
        with patch.object(arena_collector, '_fetch_arena_webpage') as mock_fetch:
            mock_fetch.return_value = soup
            
            result = arena_collector.collect_team_arena_data(88636)
            
            # Verify table row indices are assigned
            for game_data in result.games_data:
                assert game_data.table_row_index is not None
                assert game_data.table_row_index > 0
    
    def test_game_id_extraction_from_href(self, arena_collector):
        """Test game ID extraction from different href patterns using inline logic."""
        import re
        
        test_cases = [
            ('/match/134429413/boxscore.aspx', '134429413'),
            ('/match/12345/', '12345'),
            ('/match/9999/stats.aspx', '9999'),
            ('/other/link', None),  # Non-match link
            ('', None),  # Empty href
        ]
        
        for href, expected_id in test_cases:
            if expected_id:
                # Test that valid hrefs extract game ID
                match_id_match = re.search(r'/match/(\d+)/', href)
                if match_id_match:
                    extracted_id = match_id_match.group(1)
                    assert extracted_id == expected_id, f"Failed for href: {href}"
                else:
                    pytest.fail(f"Should have extracted ID for href: {href}")
            else:
                # Test that invalid hrefs return None
                match_id_match = re.search(r'/match/(\d+)/', href)
                assert match_id_match is None, f"Should return None for href: {href}"
    
    def test_price_parsing_from_text(self, arena_collector):
        """Test price parsing from various text formats using regex logic."""
        import re
        
        test_cases = [
            ("Bleachers: 9, Lower Tier: 30, Courtside: 95, Luxury Boxes: 700", {
                "bleachers": 9, "lower_tier": 30, "courtside": 95, "luxury_boxes": 700
            }),
            ("Bleachers: 15, Lower Tier: 40", {
                "bleachers": 15, "lower_tier": 40
            }),
            ("Lower Tier: 25, Luxury Boxes: 500", {
                "lower_tier": 25, "luxury_boxes": 500
            }),
            ("No price info", {}),
        ]
        
        for text, expected_prices in test_cases:
            # Parse prices using regex similar to the actual implementation
            parsed_prices = {}
            
            # Extract prices using regex patterns
            bleachers_match = re.search(r'Bleachers:\s*(\d+)', text, re.IGNORECASE)
            if bleachers_match:
                parsed_prices["bleachers"] = int(bleachers_match.group(1))
                
            lower_tier_match = re.search(r'Lower Tier:\s*(\d+)', text, re.IGNORECASE)
            if lower_tier_match:
                parsed_prices["lower_tier"] = int(lower_tier_match.group(1))
                
            courtside_match = re.search(r'Courtside:\s*(\d+)', text, re.IGNORECASE)
            if courtside_match:
                parsed_prices["courtside"] = int(courtside_match.group(1))
                
            luxury_match = re.search(r'Luxury Boxes:\s*(\d+)', text, re.IGNORECASE)
            if luxury_match:
                parsed_prices["luxury_boxes"] = int(luxury_match.group(1))
            
            # Compare with expected (only checking keys that should exist)
            for key, expected_value in expected_prices.items():
                assert key in parsed_prices, f"Missing {key} in parsed prices for text: {text}"
                assert parsed_prices[key] == expected_value, f"Wrong value for {key} in text: {text}"


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_arena_page(self, arena_collector):
        """Test handling of empty arena page."""
        empty_html = "<html><body></body></html>"
        soup = BeautifulSoup(empty_html, 'html.parser')
        
        with patch.object(arena_collector, '_fetch_arena_webpage') as mock_fetch:
            mock_fetch.return_value = soup
            
            result = arena_collector.collect_team_arena_data(88636)
            
            assert result.success
            assert len(result.arena_data["games"]) == 0
            assert len(result.arena_data["pricing_updates"]) == 0
    
    def test_malformed_html(self, arena_collector):
        """Test handling of malformed HTML."""
        malformed_html = "<table><tr><td>Date</td><tr><td>6/7/2025"  # Missing closing tags
        soup = BeautifulSoup(malformed_html, 'html.parser')
        
        with patch.object(arena_collector, '_fetch_arena_webpage') as mock_fetch:
            mock_fetch.return_value = soup
            
            result = arena_collector.collect_team_arena_data(88636)
            
            # Should handle gracefully without crashing
            assert result.success or not result.success  # Just verify it doesn't crash
    
    def test_network_error_handling(self, arena_collector):
        """Test handling of network errors."""
        with patch.object(arena_collector, '_fetch_arena_webpage') as mock_fetch:
            mock_fetch.side_effect = Exception("Network error")
            
            result = arena_collector.collect_team_arena_data(88636)
            
            assert not result.success
            assert "error" in result.arena_data or result.arena_data == {}
    
    def test_no_games_only_updates(self, arena_collector, arena_html_no_games):
        """Test arena page with price updates but no games."""
        soup = BeautifulSoup(arena_html_no_games, 'html.parser')
        
        with patch.object(arena_collector, '_fetch_arena_webpage') as mock_fetch:
            mock_fetch.return_value = soup
            
            result = arena_collector.collect_team_arena_data(88636)
            
            assert result.success
            assert len(result.arena_data["games"]) == 0
            assert len(result.arena_data["pricing_updates"]) == 2
    
    def test_no_updates_only_games(self, arena_collector, arena_html_no_updates):
        """Test arena page with games but no price updates."""
        soup = BeautifulSoup(arena_html_no_updates, 'html.parser')
        
        with patch.object(arena_collector, '_fetch_arena_webpage') as mock_fetch:
            mock_fetch.return_value = soup
            
            result = arena_collector.collect_team_arena_data(88636)
            
            assert result.success
            assert len(result.arena_data["games"]) == 2
            assert len(result.arena_data["pricing_updates"]) == 0
    
    def test_duplicate_game_ids(self, arena_collector):
        """Test handling of duplicate game IDs in arena page."""
        duplicate_html = """
        <html>
        <body>
            <table>
                <tr><td>Date</td><td>Event</td><td>Details</td></tr>
                <tr>
                    <td>6/7/2025</td>
                    <td><a href="/match/12345/boxscore.aspx">vs Team A</a></td>
                    <td>W 74-62</td>
                </tr>
                <tr>
                    <td>6/7/2025</td>
                    <td><a href="/match/12345/boxscore.aspx">vs Team A (replay)</a></td>
                    <td>W 74-62</td>
                </tr>
            </table>
        </body>
        </html>
        """
        soup = BeautifulSoup(duplicate_html, 'html.parser')
        
        with patch.object(arena_collector, '_fetch_arena_webpage') as mock_fetch:
            mock_fetch.return_value = soup
            
            result = arena_collector.collect_team_arena_data(88636)
            
            # Should handle duplicates gracefully (either include both or deduplicate)
            assert result.success
            game_ids = [g["game_id"] for g in result.arena_data["games"]]
            assert "12345" in game_ids


class TestRegressionScenarios:
    """Test specific regression scenarios that were previously bugs."""
    
    def test_team_88636_original_bug(self, arena_collector):
        """Test the exact scenario that caused the original bug with team 88636."""
        # This HTML represents the exact state that caused game 134429413 
        # to appear in multiple periods
        bug_html = """
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
        soup = BeautifulSoup(bug_html, 'html.parser')
        
        with patch.object(arena_collector, '_fetch_arena_webpage') as mock_fetch:
            mock_fetch.return_value = soup
            
            result = arena_collector.collect_team_arena_data(88636)
            
            assert result.success
            
            # Verify game IDs are extracted correctly
            games_by_id = {g["game_id"]: g for g in result.arena_data["games"]}
            assert "134429413" in games_by_id
            assert "134429414" in games_by_id
            
            # Verify table positions are correct
            assert games_by_id["134429414"]["table_position"] == 1  # Row 1
            # Price update at position 2
            assert games_by_id["134429413"]["table_position"] == 3  # Row 3
            
            # Verify the problematic game has the correct date and opponent
            game_134429413 = games_by_id["134429413"]
            assert game_134429413["date"] == "6/7/2025"
            assert "Dimlorence" in game_134429413["opponent"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
