#!/usr/bin/env python3
"""
Script to collect historical arena pricing data from BuzzerBeater team arena pages.

This script collects the team/{teamid}/arena.aspx pages to extract:
- Last 10 official home game attendances 
- Historical ticket price changes

The data is used to update existing game records in the database with pricing information.
"""

import argparse
import logging
import sys
from pathlib import Path

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from bb_arena_optimizer.collecting import HistoricalPricingService
from bb_arena_optimizer.storage.database import DatabaseManager
from bb_arena_optimizer.utils.logging_config import setup_logging


def main():
    """Main entry point for the pricing collection script."""
    parser = argparse.ArgumentParser(
        description="Collect historical arena pricing data from BuzzerBeater team pages",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Collect data for a single team
  python collect_historical_pricing.py --team-id 12345

  # Collect data for multiple teams
  python collect_historical_pricing.py --team-ids 12345 67890 11111

  # Use custom database path and request delay
  python collect_historical_pricing.py --team-id 12345 --db-path /path/to/db.sqlite --delay 2.0

  # Enable debug logging
  python collect_historical_pricing.py --team-id 12345 --verbose
        """
    )
    
    # Team selection arguments
    team_group = parser.add_mutually_exclusive_group(required=True)
    team_group.add_argument(
        "--team-id",
        type=str,
        help="Single team ID to collect data for"
    )
    team_group.add_argument(
        "--team-ids",
        type=str,
        nargs="+",
        help="Multiple team IDs to collect data for"
    )
    
    # Configuration arguments
    parser.add_argument(
        "--db-path",
        type=str,
        default="bb_arena_data.db",
        help="Path to SQLite database file (default: bb_arena_data.db)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.5,
        help="Delay between requests in seconds to be respectful to server (default: 1.5)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logging(level=log_level)
    logger = logging.getLogger(__name__)
    
    # Initialize database manager
    try:
        db_manager = DatabaseManager(args.db_path)
        logger.info(f"Connected to database: {args.db_path}")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return 1
    
    # Initialize pricing service
    pricing_service = HistoricalPricingService(db_manager)
    
    # Determine which teams to process
    if args.team_id:
        team_ids = [args.team_id]
        logger.info(f"Collecting pricing data for team {args.team_id}")
    else:
        team_ids = args.team_ids
        logger.info(f"Collecting pricing data for {len(team_ids)} teams: {', '.join(team_ids)}")
    
    # Collect pricing data
    try:
        if len(team_ids) == 1:
            # Single team - use individual method for more detailed output
            result = pricing_service.collect_and_update_team_pricing(team_ids[0], args.delay)
            
            if result["success"]:
                logger.info("✓ Pricing collection completed successfully")
                if "collection_result" in result:
                    sr = result["collection_result"]
                    logger.info(f"  - Found {sr['last_10_games_found']} recent games")
                    logger.info(f"  - Found {sr['price_changes_found']} price changes")
                
                if "update_result" in result:
                    ur = result["update_result"]
                    logger.info(f"  - Updated {ur['games_updated']} games with pricing data")
                    logger.info(f"  - {ur['games_not_found']} collected games not found in database")
                    logger.info(f"  - Processed {ur['price_changes_processed']} price changes")
                
                return 0
            else:
                logger.error(f"✗ Pricing collection failed: {result.get('error', 'Unknown error')}")
                return 1
        else:
            # Multiple teams - use batch method
            results = pricing_service.collect_for_multiple_teams(team_ids, args.delay)
            
            logger.info("✓ Batch pricing collection completed")
            logger.info(f"  - Teams processed: {results['teams_processed']}")
            logger.info(f"  - Teams successful: {results['teams_successful']}")
            logger.info(f"  - Teams failed: {results['teams_failed']}")
            logger.info(f"  - Total games updated: {results['total_games_updated']}")
            
            if results["failed_teams"]:
                logger.warning("Failed teams:")
                for failure in results["failed_teams"]:
                    logger.warning(f"  - Team {failure['team_id']}: {failure['error']}")
            
            return 0 if results["teams_failed"] == 0 else 1
            
    except KeyboardInterrupt:
        logger.info("Collection interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error during collection: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
