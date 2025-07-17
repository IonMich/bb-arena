#!/usr/bin/env python3
"""
Script to populate all level 1 leagues from BB API into the database.
This is a one-time setup to ensure we have accurate league level data.
"""

import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from bb_arena_optimizer.storage.utils.team_utils import TeamInfoManager
from bb_arena_optimizer.storage.database import DatabaseManager
from bb_arena_optimizer.utils.logging_config import get_logger

logger = get_logger(__name__)

def main():
    """Populate all level 1 leagues from countries 1-110."""
    try:
        # Initialize database
        db = DatabaseManager()
        team_manager = TeamInfoManager(db.db_path)
        
        logger.info("Starting population of all level 1 leagues...")
        
        # Populate all level 1 leagues using the API
        results = team_manager.populate_all_level_1_leagues(max_country_id=110)
        
        logger.info(f"Population completed!")
        logger.info(f"Results: {results}")
        print(f"Successfully populated {results['total_leagues']} level 1 leagues")
        print(f"Countries processed: {results['successful']} successful, {results['failed']} failed")
        
        return 0
        
    except Exception as e:
        logger.error(f"Failed to populate level 1 leagues: {e}")
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
