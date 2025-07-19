"""
Price Period Builder Test

This test verifies the price period builder functionality using test data.
Tests both home team IDs with their corresponding fixture data.
"""

import pytest
from pathlib import Path
from bs4 import BeautifulSoup, Tag
from datetime import datetime, timezone as tz

from bb_arena_optimizer.collecting.price_period import build_price_periods_from_data
from bb_arena_optimizer.collecting.arena_row import ArenaRowParser
from bb_arena_optimizer.collecting.price_period import PricePeriod
from bb_arena_optimizer.utils.datetime_utils import get_bb_timezone_from_html
from bb_arena_optimizer.storage.database import DatabaseManager


def load_test_data(home_team_id: str):
    """Load test data for a given home team ID."""
    if home_team_id == "27795":
        fixture_path = Path(__file__).parent / "fixtures" / "team_27795_no_price_update.html"
    elif home_team_id == "142773":
        fixture_path = Path(__file__).parent / "fixtures" / "team_142773_with_price_updates_table_only.html"
    else:
        raise ValueError(f"Unknown team ID: {home_team_id}")
    
    with open(fixture_path, 'r', encoding='utf-8') as f:
        return f.read()


def print_source_table_data(parsed_objects):
    """Print formatted source table data for debugging."""
    print("📋 Source Table Data:")
    print("Row | Type         | Date     | Bleachers | Lower | Court | Luxury")
    print("----|--------------|----------|-----------|-------|-------|--------")
    
    for i, obj in enumerate(parsed_objects):
        if hasattr(obj, 'game_id'):  # GameEvent
            print(f"{obj.row_index:3d} | Game {obj.game_id} | {obj.date_raw:8s} |     -     |   -   |   -   |   -    ")
        else:  # PriceChange
            print(f"{obj.row_index:3d} |  Price Change  | {obj.date_raw:8s} |    {obj.bleachers_price:2d}     |  {obj.lower_tier_price:2d}   |  {obj.courtside_price:3d}  |  {obj.luxury_boxes_price:3d}")
    print()


def print_price_periods(periods: list[PricePeriod]):
    """Print formatted price periods for debugging."""
    print(f"📊 Built {len(periods)} price periods:")
    print()
    
    for period in periods:
        print(f"Period {period.period_id}:")
        print(f"   Games: {period.official_game_count} games")
        if period.game_events:
            game_rows = [str(g.row_index) for g in period.game_events]
            print(f"   Game rows: {', '.join(game_rows)}")
        else:
            print(f"   Game rows: none")
        if period.start_price_change:
            print(f"   Start boundary: price change on {period.start_price_change.date_raw} (row {period.start_price_change.row_index})")
        print(f"   Start boundary time: {period.safe_start}")
            
        if period.end_price_change:
            print(f"   End boundary: price change on {period.end_price_change.date_raw} (row {period.end_price_change.row_index})")
        print(f"   End boundary time: {period.safe_end}")
        print()
        # show pricing details
        if period.has_valid_pricing():
            source = period.start_price_change if period.start_price_change else period.price_snapshot
            if source is not None:
                print((
                    f"   Bleachers: {source.bleachers_price},\n"
                    f"   Lower Tier: {source.lower_tier_price},\n"
                    f"   Court Side: {source.courtside_price},\n"
                    f"   Luxury Boxes: {source.luxury_boxes_price}"
                ))


@pytest.mark.parametrize("home_team_id", ["142773", "27795"])
def test_price_period_builder(home_team_id, capsys):
    """Test the price period builder with demo data for different teams."""
    print(f"🏟️ Price Period Builder Test for Team {home_team_id}")
    print()
    
    # Load test data
    html_content = load_test_data(home_team_id)
    
    # Parse data
    soup = BeautifulSoup(html_content, 'html.parser')
    table = soup.find('table', id='cphContent_seatingStats')
    assert table is not None and isinstance(table, Tag)
    
    parser = ArenaRowParser()
    parsed_objects = parser.parse_data_rows(table)
    
    # Show the source table data for debugging
    print_source_table_data(parsed_objects)
    
    # Detect timezone
    timezone_str = get_bb_timezone_from_html(html_content)
    
    # Build periods (use a fixed time for consistent testing)
    # Using July 18, 2025 instead of July 17 to match the actual test date
    demo_request_time = datetime(2025, 7, 18, 22, 50, 16, 206409, tzinfo=tz.utc)
    
    # Create database manager
    db_manager = DatabaseManager()
    
    # Build price periods
    periods = build_price_periods_from_data(parsed_objects, db_manager, home_team_id, timezone_str, demo_request_time)
    
    # Print periods for debugging
    print_price_periods(periods)
    
    # Validate results based on team ID
    if home_team_id == "142773":
        # Expected results for team 142773
        assert len(periods) == 2, f"Expected 2 periods for team {home_team_id}, got {len(periods)}"
        
        # Period 0 validation
        period_0 = periods[0]
        assert period_0.period_id == 0
        assert period_0.official_game_count == 2
        assert len(period_0.game_events) == 2
        game_rows = [g.row_index for g in period_0.game_events]
        assert game_rows == [3, 4], f"Expected game rows [3, 4], got {game_rows}"
        
        # Check start boundary for period 0
        assert period_0.start_price_change is not None
        assert period_0.start_price_change.date_raw == "6/22/2025"
        assert period_0.start_price_change.row_index == 5
        
        # Check end boundary for period 0
        assert period_0.end_price_change is not None
        assert period_0.end_price_change.date_raw == "7/6/2025"
        assert period_0.end_price_change.row_index == 2
        
        # Check pricing for period 0
        assert period_0.has_valid_pricing()
        source = period_0.start_price_change
        assert source.bleachers_price == 13
        assert source.lower_tier_price == 36
        assert source.courtside_price == 128
        assert source.luxury_boxes_price == 830
        
        # Check other home games for period 0
        assert len(period_0.other_home_games) == 2
        assert period_0.total_game_count == 4
        other_game_ids = [g.game_id for g in period_0.other_home_games]
        expected_other_game_ids = ['135028185', '135133006']
        assert other_game_ids == expected_other_game_ids, f"Expected other game IDs {expected_other_game_ids}, got {other_game_ids}"
        
        # Period 1 validation
        period_1 = periods[1]
        assert period_1.period_id == 1
        assert period_1.official_game_count == 1
        assert len(period_1.game_events) == 1
        assert period_1.game_events[0].row_index == 0
        
        # Check start boundary for period 1
        assert period_1.start_price_change is not None
        assert period_1.start_price_change.date_raw == "7/6/2025"
        assert period_1.start_price_change.row_index == 1
        
        # Check pricing for period 1
        assert period_1.has_valid_pricing()
        source = period_1.start_price_change
        assert source.bleachers_price == 13
        assert source.lower_tier_price == 38
        assert source.courtside_price == 133
        assert source.luxury_boxes_price == 860
        
        # Check other home games for period 1
        assert len(period_1.other_home_games) == 1
        assert period_1.total_game_count == 2
        other_game_ids = [g.game_id for g in period_1.other_home_games]
        expected_other_game_ids = ['135194843']
        assert other_game_ids == expected_other_game_ids, f"Expected other game IDs {expected_other_game_ids}, got {other_game_ids}"
        
    elif home_team_id == "27795":
        # Expected results for team 27795
        assert len(periods) == 1, f"Expected 1 period for team {home_team_id}, got {len(periods)}"
        
        # Period 0 validation
        period_0 = periods[0]
        assert period_0.period_id == 0
        assert period_0.official_game_count == 10
        assert len(period_0.game_events) == 10
        game_rows = [g.row_index for g in period_0.game_events]
        expected_game_rows = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
        assert game_rows == expected_game_rows, f"Expected game rows {expected_game_rows}, got {game_rows}"
        
        # Check that there's no start price change (no price updates in this team's data)
        assert period_0.start_price_change is None
        
        # Check that there's no end price change
        assert period_0.end_price_change is None
        
        # Check that pricing comes from price_snapshot
        assert period_0.has_valid_pricing()
        assert period_0.price_snapshot is not None
        price_source = period_0.price_snapshot
        assert price_source.bleachers_price == 9
        assert price_source.lower_tier_price == 18
        assert price_source.courtside_price == 78
        assert price_source.luxury_boxes_price == 410
        
        # Check other home games for period 0
        assert len(period_0.other_home_games) == 8
        assert period_0.total_game_count == 18
        other_game_ids = [g.game_id for g in period_0.other_home_games]
        expected_other_game_ids = ['134941600', '134970648', '134983322', '134995667', '135025802', '135101590', '135112068', '135151954']
        assert other_game_ids == expected_other_game_ids, f"Expected other game IDs {expected_other_game_ids}, got {other_game_ids}"


def test_price_period_builder_demo():
    """Legacy test function to maintain backward compatibility."""
    test_price_period_builder("142773", None)
