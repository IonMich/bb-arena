"""
Arena Pricing Pipeline - Arena Row Parsing and Data Objects

This module provides classes for parsing individual rows from BuzzerBeater arena
attendance tables and creating structured data objects for both game attendance 
and price change records.

Key Components:
- GameAttendance: Structured data for game attendance records
- PriceChange: Structured data for ticket price updates  
- ArenaRowParser: Service for parsing table rows into data objects
- TestArenaRowParsing: Comprehensive test suite
"""

import pytest
from pathlib import Path
from bs4 import BeautifulSoup, Tag

from bb_arena_optimizer.collecting.arena_row import ArenaRowParser, GameEvent, PriceChange


class TestArenaRowParsing:
    """Test suite for Arena Row Parsing and Data Objects."""
    
    @pytest.fixture
    def games_only_html(self) -> str:
        """Load HTML fixture with only game rows (team 27795)."""
        fixture_path = Path(__file__).parent / "fixtures" / "team_27795_no_price_update.html"
        with open(fixture_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    @pytest.fixture
    def mixed_data_html(self) -> str:
        """Load HTML fixture with both games and price changes (team 142773)."""
        fixture_path = Path(__file__).parent / "fixtures" / "team_142773_with_price_updates_table_only.html"
        with open(fixture_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    @pytest.fixture
    def parser(self) -> ArenaRowParser:
        """Get a parser instance."""
        return ArenaRowParser()
    
    def test_can_identify_price_change_rows(self, mixed_data_html: str, parser: ArenaRowParser) -> None:
        """Test: Can we correctly identify price change vs game rows?"""
        soup = BeautifulSoup(mixed_data_html, 'html.parser')
        table = soup.find('table', id='cphContent_seatingStats')
        assert table is not None and isinstance(table, Tag)
        
        all_rows = table.find_all('tr')
        data_rows = [row for row in all_rows 
                    if isinstance(row, Tag) and not (row.get('class') and 'tableHeader' in str(row.get('class')))]
        
        # Based on our analysis: rows 1, 2, 5 should be price changes
        assert not parser.is_price_change_row(data_rows[0]), "Row 0 should be game (Rodon)"
        assert parser.is_price_change_row(data_rows[1]), "Row 1 should be price change"
        assert parser.is_price_change_row(data_rows[2]), "Row 2 should be price change"
        assert not parser.is_price_change_row(data_rows[3]), "Row 3 should be game (Red Pirates)"
        assert parser.is_price_change_row(data_rows[5]), "Row 5 should be price change"
    
    def test_parse_game_attendance_object(self, games_only_html: str, parser: ArenaRowParser) -> None:
        """Test: Can we parse a complete GameEvent object?"""
        soup = BeautifulSoup(games_only_html, 'html.parser')
        table = soup.find('table', id='cphContent_seatingStats')
        assert table is not None and isinstance(table, Tag)
        
        parsed_objects = parser.parse_data_rows(table)
        
        # Should have 10 games, no price changes
        assert len(parsed_objects) == 10, f"Expected 10 objects, got {len(parsed_objects)}"
        assert all(isinstance(obj, GameEvent) for obj in parsed_objects), "All should be GameEvent"
        
        # Test first game (Alfea)
        first_game = parsed_objects[0]
        assert isinstance(first_game, GameEvent)
        assert first_game.row_index == 0
        assert first_game.game_id == "135269762"
        assert first_game.date_raw == "7/12/2025"
    
    def test_parse_price_change_object(self, mixed_data_html: str, parser: ArenaRowParser) -> None:
        """Test: Can we parse a complete PriceChange object?"""
        soup = BeautifulSoup(mixed_data_html, 'html.parser')
        table = soup.find('table', id='cphContent_seatingStats')
        assert table is not None and isinstance(table, Tag)
        
        parsed_objects = parser.parse_data_rows(table)
        
        # Find price change objects
        price_changes = [obj for obj in parsed_objects if isinstance(obj, PriceChange)]
        assert len(price_changes) >= 3, f"Expected at least 3 price changes, got {len(price_changes)}"
        
        # Test first price change (should be row index 1)
        first_price_change = price_changes[0]
        assert isinstance(first_price_change, PriceChange)
        assert first_price_change.row_index == 1
        assert first_price_change.date_raw == "7/6/2025"
        assert first_price_change.bleachers_price == 13
        assert first_price_change.lower_tier_price == 38
        assert first_price_change.courtside_price == 133
        assert first_price_change.luxury_boxes_price == 860
    
    def test_mixed_parsing_preserves_order(self, mixed_data_html: str, parser: ArenaRowParser) -> None:
        """Test: Does mixed parsing preserve row order and indices?"""
        soup = BeautifulSoup(mixed_data_html, 'html.parser')
        table = soup.find('table', id='cphContent_seatingStats')
        assert table is not None and isinstance(table, Tag)
        
        parsed_objects = parser.parse_data_rows(table)
        
        # Verify row indices are sequential
        for i, obj in enumerate(parsed_objects):
            assert obj.row_index == i, f"Object {i} should have row_index {i}, got {obj.row_index}"
        
        # Verify we have both types in correct positions
        assert isinstance(parsed_objects[0], GameEvent), "Index 0 should be GameEvent"
        assert isinstance(parsed_objects[1], PriceChange), "Index 1 should be PriceChange"
        assert isinstance(parsed_objects[2], PriceChange), "Index 2 should be PriceChange"
        assert isinstance(parsed_objects[3], GameEvent), "Index 3 should be GameEvent"

    def test_handles_malformed_rows_gracefully(self, parser: ArenaRowParser) -> None:
        """Test: Does parser handle malformed rows without crashing?"""
        # Create minimal malformed HTML with a valid game row that has game_id
        malformed_html = """
        <table id="cphContent_seatingStats">
            <tr class="tableHeader"><th>Date</th><th>Opponent</th></tr>
            <tr><td>7/12/2025</td></tr>
            <tr><td><a href="/match/12345/boxscore.aspx">7/11/2025</a></td><td>Valid Team</td><td>100</td><td>200</td><td>50</td><td>10</td><td>360</td><td></td></tr>
        </table>
        """
        
        soup = BeautifulSoup(malformed_html, 'html.parser')
        table = soup.find('table', id='cphContent_seatingStats')
        assert table is not None and isinstance(table, Tag)
        
        # Should not crash, and should parse the valid row
        parsed_objects = parser.parse_data_rows(table)
        
        # Should get 1 valid object (malformed row gets skipped)
        assert len(parsed_objects) == 1
        assert isinstance(parsed_objects[0], GameEvent)
        assert parsed_objects[0].game_id == "12345"


def test_arena_row_parsing_integration() -> None:
    """Integration test for Arena Row Parsing functionality."""
    print("Testing Arena Row Parsing...")
    
    # Test with mixed data (games + price changes)
    fixture_path = Path(__file__).parent / "fixtures" / "team_142773_with_price_updates_table_only.html"
    with open(fixture_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Parse the data
    soup = BeautifulSoup(html_content, 'html.parser')
    table = soup.find('table', id='cphContent_seatingStats')
    assert table is not None and isinstance(table, Tag), "Should find table"
    
    parser = ArenaRowParser()
    parsed_objects = parser.parse_data_rows(table)
    
    # Count object types
    games = [obj for obj in parsed_objects if isinstance(obj, GameEvent)]
    price_changes = [obj for obj in parsed_objects if isinstance(obj, PriceChange)]
    
    print(f"✅ Arena Row Parsing Complete: Parsed {len(games)} games and {len(price_changes)} price changes")
    print(f"   Total objects: {len(parsed_objects)}")
    
    # Verify we got both types
    assert len(games) > 0, "Should have game attendance records"
    assert len(price_changes) > 0, "Should have price change records"


if __name__ == "__main__":
    # Run integration test
    test_arena_row_parsing_integration()
