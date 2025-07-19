"""
Arena Pricing Pipeline - Arena Table Isolation

This module provides functionality for isolating and validating BuzzerBeater arena 
attendance tables from HTML pages. It serves as the foundation for the arena data
collection pipeline by ensuring we can reliably find and validate table structure.

Key Components:
- ArenaTableIsolator: Service for finding and validating arena tables
- TestArenaTableIsolation: Comprehensive test suite for table isolation
"""

import pytest
from pathlib import Path
from bs4 import BeautifulSoup, Tag

from bb_arena_optimizer.collecting.arena_table_parser import ArenaTableIsolator


class TestArenaTableIsolation:
    """Test suite for Arena Table Isolation functionality."""
    
    @pytest.fixture
    def arena_html(self) -> str:
        """Load the real arena HTML fixture."""
        fixture_path = Path(__file__).parent / "fixtures" / "team_27795_no_price_update.html"
        with open(fixture_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    @pytest.fixture
    def isolator(self) -> ArenaTableIsolator:
        """Get an isolator instance."""
        return ArenaTableIsolator()
    
    def test_can_find_attendance_table(self, arena_html: str, isolator: ArenaTableIsolator) -> None:
        """Test: Can we find the attendance table?"""
        table = isolator.find_attendance_table(arena_html)
        
        assert table is not None, "Should find attendance table"
        assert isinstance(table, Tag), "Should return a Tag object"
        assert table.name == 'table', "Should be a table element"
        assert table.get('id') == 'cphContent_seatingStats', "Should have correct ID"
    
    def test_table_structure_validation(self, arena_html: str, isolator: ArenaTableIsolator) -> None:
        """Test: Does the table have the expected structure?"""
        table = isolator.find_attendance_table(arena_html)
        assert table is not None
        
        is_valid = isolator.validate_table_structure(table)
        assert is_valid, "Table should have valid structure"
    
    def test_can_count_data_rows(self, arena_html: str, isolator: ArenaTableIsolator) -> None:
        """Test: Can we count the data rows correctly?"""
        table = isolator.find_attendance_table(arena_html)
        assert table is not None
        
        row_count = isolator.count_data_rows(table)
        
        # Based on the real fixture, we expect 10 game rows
        assert row_count == 10, f"Expected 10 data rows, got {row_count}"
    
    def test_isolation_with_invalid_html(self, isolator: ArenaTableIsolator) -> None:
        """Test: How does isolation handle invalid HTML?"""
        invalid_html = "<html><body><p>No table here</p></body></html>"
        
        table = isolator.find_attendance_table(invalid_html)
        assert table is None, "Should return None for HTML without attendance table"
    
    def test_isolation_roundtrip(self, arena_html: str, isolator: ArenaTableIsolator) -> None:
        """Test: Can we extract the table and it remains functional?"""
        table = isolator.find_attendance_table(arena_html)
        assert table is not None
        
        # Convert back to HTML string and re-parse
        table_html = str(table)
        assert 'cphContent_seatingStats' in table_html, "Should preserve table ID in HTML"
        
        # Re-parse the isolated table
        soup = BeautifulSoup(table_html, 'html.parser')
        reparsed_table = soup.find('table')
        
        assert reparsed_table is not None, "Should be able to re-parse isolated table"
        assert isinstance(reparsed_table, Tag), "Re-parsed table should be a Tag"
        
        # Should still validate
        is_valid = isolator.validate_table_structure(reparsed_table)
        assert is_valid, "Re-parsed table should still be valid"


def test_arena_table_isolation_integration() -> None:
    """Integration test for Arena Table Isolation functionality."""
    print("Testing Arena Table Isolation...")
    
    # Test with real BuzzerBeater HTML
    fixture_path = Path(__file__).parent / "fixtures" / "team_27795_no_price_update.html"
    with open(fixture_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Isolate the table
    isolator = ArenaTableIsolator()
    table = isolator.find_attendance_table(html_content)
    assert table is not None, "Should find attendance table"
    
    # Validate structure
    isolator.validate_table_structure(table)
    data_rows = isolator.count_data_rows(table)
    
    print(f"✅ Arena Table Isolation Complete: Found table with {data_rows} data rows")
    
    # Verify we got expected data
    assert data_rows == 10, f"Expected 10 data rows for team 27795, got {data_rows}"


if __name__ == "__main__":
    # Run integration test
    test_arena_table_isolation_integration()
