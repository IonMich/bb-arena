#!/usr/bin/env python3
"""
Example script demonstrating how to collect historical pricing data.

This example shows:
1. How to collect a single team's arena page
2. How to update games with pricing data
3. How to check pricing coverage status
"""

import sys
from pathlib import Path

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from bb_arena_optimizer.collecting import HistoricalPricingService, TeamArenaCollector
from bb_arena_optimizer.storage.database import DatabaseManager
from bb_arena_optimizer.utils.logging_config import setup_logging


def example_single_team_collection():
    """Example of collecting a single team's pricing data."""
    print("Example 1: Single Team Collection")
    print("=" * 40)
    
    # Note: Replace with a real team ID when testing
    example_team_id = "12345"
    
    print(f"This example would collect team {example_team_id}")
    print("URL would be: https://www.buzzerbeater.com/team/12345/arena.aspx")
    print()
    
    # Example of how to use the collector directly
    print("Code example:")
    print("""
    with TeamArenaCollector(request_delay=1.5) as collector:
        result = collector.collect_team_arena_data("12345")
        
        if result.success:
            print(f"Found {result.last_10_games_found} games")
            print(f"Found {result.price_changes_found} price changes")
            
            for game in result.games_data:
                if not game.is_price_change:
                    print(f"Game vs {game.opponent} on {game.date}")
                    print(f"  Attendance: {game.attendance}")
                    print(f"  Prices: ${game.bleachers_price}, ${game.lower_tier_price}, ${game.courtside_price}, ${game.luxury_boxes_price}")
        else:
            print(f"Collection failed: {result.error_message}")
    """)


def example_pricing_service():
    """Example of using the pricing service to update database."""
    print("Example 2: Pricing Service")
    print("=" * 40)
    
    print("The pricing service automatically matches collected games with stored games")
    print("and updates the pricing information in the database.")
    print()
    
    print("Code example:")
    print("""
    # Initialize services
    db_manager = DatabaseManager("bb_arena_data.db")
    pricing_service = HistoricalPricingService(db_manager)
    
    # Collect and update pricing for a single team
    result = pricing_service.collect_and_update_team_pricing("12345")
    
    if result["success"]:
        print("Collection successful!")
        print(f"Games updated: {result['update_result']['games_updated']}")
        print(f"Games not found: {result['update_result']['games_not_found']}")
    else:
        print(f"Collection failed: {result['error']}")
    """)


def example_batch_collection():
    """Example of collecting data for multiple teams."""
    print("Example 3: Batch Collection")
    print("=" * 40)
    
    print("For collecting data from multiple teams, use the batch method:")
    print()
    
    print("Code example:")
    print("""
    team_ids = ["12345", "67890", "11111"]
    
    # Collect for multiple teams with increased delay
    results = pricing_service.collect_for_multiple_teams(team_ids, collector_delay=2.0)
    
    print(f"Processed {results['teams_processed']} teams")
    print(f"Successful: {results['teams_successful']}")
    print(f"Failed: {results['teams_failed']}")
    print(f"Total games updated: {results['total_games_updated']}")
    
    # Check individual team results
    for team_result in results['team_results']:
        if team_result['success']:
            print(f"Team {team_result['team_id']}: Success")
        else:
            print(f"Team {team_result['team_id']}: Failed - {team_result['error']}")
    """)


def example_api_usage():
    """Example of using the API endpoints."""
    print("Example 4: API Usage")
    print("=" * 40)
    
    print("You can also trigger collection via the API endpoints:")
    print()
    
    print("Single team collection:")
    print("""
    POST /api/historical-pricing/collect
    {
        "team_id": "12345",
        "delay": 1.5
    }
    """)
    
    print("Multiple team collection:")
    print("""
    POST /api/historical-pricing/collect
    {
        "team_ids": ["12345", "67890", "11111"],
        "delay": 2.0
    }
    """)
    
    print("Check pricing status:")
    print("""
    GET /api/historical-pricing/status/12345
    
    Response:
    {
        "team_id": "12345",
        "total_games": 45,
        "games_with_pricing": 32,
        "games_without_pricing": 13,
        "pricing_coverage": 71.1
    }
    """)


def example_best_practices():
    """Show best practices for using the collector."""
    print("Example 5: Best Practices")
    print("=" * 40)
    
    print("1. Start with small batches to test:")
    print("   python scripts/collect_historical_pricing.py --team-id 12345 --verbose")
    print()
    
    print("2. Use appropriate delays (especially for batch processing):")
    print("   - Single team: 1.0-1.5 seconds")
    print("   - Multiple teams: 1.5-2.5 seconds")
    print()
    
    print("3. Monitor logs for errors:")
    print("   - Network timeouts: Increase delays")
    print("   - Parsing errors: Page structure may have changed")
    print("   - Game matching issues: Check date formats")
    print()
    
    print("4. Check coverage after collection:")
    print("   Use the status endpoint to see how many games got pricing data")
    print()
    
    print("5. Regular updates:")
    print("   Run weekly/monthly to capture new games and price changes")


def main():
    """Run all examples."""
    setup_logging(level="INFO")
    
    print("Historical Pricing Data Collection Examples")
    print("=" * 50)
    print()
    print("This script shows examples of how to use the new historical")
    print("pricing data collection functionality. The examples use")
    print("placeholder team IDs - replace with real team IDs when testing.")
    print()
    
    example_single_team_collection()
    print()
    
    example_pricing_service()
    print()
    
    example_batch_collection()
    print()
    
    example_api_usage()
    print()
    
    example_best_practices()
    print()
    
    print("For more information, see docs/historical_pricing.md")


if __name__ == "__main__":
    main()
