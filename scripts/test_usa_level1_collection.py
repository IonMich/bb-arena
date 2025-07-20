#!/usr/bin/env python3
"""
Test the task-based collector with USA level 1 teams for seasons 68,69.
"""

import sys
import os
import asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from bb_arena_optimizer.api.client import BuzzerBeaterAPI
from bb_arena_optimizer.storage.database import DatabaseManager
from bb_arena_optimizer.collecting.task_based_collector import TaskBasedCollector, RateLimitConfig, run_complete_data_collection_pipeline
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_usa_level1_collection():
    """Test task-based collection for USA level 1 teams."""
    
    # Get credentials from environment
    username = os.getenv('BB_USERNAME')
    security_code = os.getenv('BB_SECURITY_CODE')
    
    if not username or not security_code:
        print("❌ Please set BB_USERNAME and BB_SECURITY_CODE environment variables")
        return
    
    api = BuzzerBeaterAPI(username, security_code)
    db_manager = DatabaseManager("bb_arena_data.db")
    
    # Conservative rate limiting for testing
    rate_config = RateLimitConfig(
        requests_per_minute=20,
        min_delay_between_requests=3.0,
        max_delay_between_requests=5.0
    )
    
    try:
        # Login
        if not api.login():
            print("❌ Failed to login to BuzzerBeater API")
            return
        
        print("✅ Successfully logged in to BuzzerBeater API")
        
        # Initialize collector
        collector = TaskBasedCollector(api, db_manager, rate_config)
        
        print("\n🇺🇸 Testing USA Level 1 Collection")
        print("=" * 60)
        print("Target: USA (country_id=1), Seasons [68, 69], Level 1 only")
        
        # Task 1: Discover teams
        print("\n🎯 TASK 1: Discovering team IDs")
        print("-" * 40)
        
        team_ids_result = await collector.task_1_collect_team_ids(
            countries=[1],  # USA only
            seasons=[68, 69],
            max_league_level=1  # Level 1 only
        )
        
        if not team_ids_result.success:
            print(f"❌ Task 1 failed: {team_ids_result.error}")
            return
        
        team_ids = team_ids_result.data
        print(f"✅ Task 1 completed!")
        print(f"   - Teams discovered: {len(team_ids)}")
        print(f"   - Execution time: {team_ids_result.execution_time:.1f}s")
        print(f"   - Sample team IDs: {list(team_ids)[:10]}")
        
        # Validate expected results
        # Level 1 has 1 league with 16 teams per season
        # Between seasons: 5 relegated (no promotion upward), 5 promoted from level 2, 11 stay
        # So 2 seasons = 16 (season 68) + 5 (new in season 69) = 21 teams total
        expected_teams = 21
        
        if len(team_ids) == expected_teams:
            print(f"✅ Perfect! Found exactly {len(team_ids)} teams (expected {expected_teams})")
        elif abs(len(team_ids) - expected_teams) <= 2:
            print(f"✅ Team count looks reasonable ({len(team_ids)} ≈ {expected_teams})")
        else:
            print(f"⚠️  Unexpected team count ({len(team_ids)} vs expected {expected_teams})")
            print(f"    This could indicate API changes or different promotion/relegation")
        
        # Use all discovered teams since the count should be manageable
        test_team_ids = team_ids
        print(f"\n🧪 Processing all {len(test_team_ids)} discovered teams")
        
        # Tasks 2, 3, 4, 5 & 6: Run complete pipeline
        print("\n🚀 TASKS 2-6: Running complete data collection pipeline")
        print("-" * 80)
        
        team_info_result, arena_result, history_result, games_result, pricing_result = await run_complete_data_collection_pipeline(
            api, db_manager, test_team_ids, [68, 69], include_pricing_update=True
        )
        
        # Task 2 Results
        print(f"\n📋 Task 2 (Team Info) Results:")
        print(f"   - Success: {team_info_result.success}")
        print(f"   - Execution time: {team_info_result.execution_time:.1f}s")
        print(f"   - Items processed: {team_info_result.items_processed}")
        
        if team_info_result.data:
            data = team_info_result.data
            print(f"   - Success rate: {data.get('success_rate', 0):.1%}")
            print(f"   - Successful: {data.get('successful', 0)}")
            print(f"   - Failed: {data.get('failed', 0)}")
        
        # Task 3 Results
        print(f"\n🏟️ Task 3 (Arena Snapshots) Results:")
        print(f"   - Success: {arena_result.success}")
        print(f"   - Execution time: {arena_result.execution_time:.1f}s")
        print(f"   - Items processed: {arena_result.items_processed}")
        
        if arena_result.data:
            data = arena_result.data
            print(f"   - Success rate: {data.get('success_rate', 0):.1%}")
            print(f"   - Successful: {data.get('successful', 0)}")
            print(f"   - Failed: {data.get('failed', 0)}")
        
        # Task 4 Results
        print(f"\n📚 Task 4 (Team History) Results:")
        print(f"   - Success: {history_result.success}")
        print(f"   - Execution time: {history_result.execution_time:.1f}s")
        print(f"   - Items processed: {history_result.items_processed}")
        
        if history_result.data:
            data = history_result.data
            print(f"   - Success rate: {data.get('success_rate', 0):.1%}")
            print(f"   - Successful: {data.get('successful', 0)}")
            print(f"   - Failed: {data.get('failed', 0)}")
            print(f"   - Total history entries: {data.get('total_history_entries', 0)}")
        
        # Task 5 Results
        print(f"\n🏈 Task 5 (Home Games) Results:")
        print(f"   - Success: {games_result.success}")
        print(f"   - Execution time: {games_result.execution_time:.1f}s")
        print(f"   - Items processed: {games_result.items_processed}")
        
        if games_result.data:
            data = games_result.data
            print(f"   - Success rate: {data.get('success_rate', 0):.1%}")
            print(f"   - Successful teams: {data.get('successful_teams', 0)}")
            print(f"   - Failed teams: {data.get('failed_teams', 0)}")
            print(f"   - Total games collected: {data.get('total_games_collected', 0)}")
            print(f"   - Total games skipped: {data.get('total_games_skipped', 0)}")
            print(f"   - Seasons: {data.get('seasons', [])}")
        
        # Task 6 Results
        if pricing_result:
            print(f"\n💰 Task 6 (Game Pricing) Results:")
            print(f"   - Success: {pricing_result.success}")
            print(f"   - Execution time: {pricing_result.execution_time:.1f}s")
            print(f"   - Items processed: {pricing_result.items_processed}")
            
            if pricing_result.data:
                data = pricing_result.data
                print(f"   - Success rate: {data.get('success_rate', 0):.1%}")
                print(f"   - Successful teams: {data.get('successful_teams', 0)}")
                print(f"   - Failed teams: {data.get('failed_teams', 0)}")
                print(f"   - Total periods created: {data.get('total_periods_created', 0)}")
                print(f"   - Total games updated: {data.get('total_games_updated', 0)}")
        else:
            print(f"\n💰 Task 6 (Game Pricing): SKIPPED (dependent on Task 5 success)")
        
        # Overall summary
        print(f"\n🎉 USA Level 1 Collection Test Results")
        print("=" * 60)
        print(f"✅ Task 1 (Team Discovery): {team_ids_result.success}")
        print(f"   └─ {len(team_ids)} teams discovered from USA level 1")
        print(f"✅ Task 2 (Team Info): {team_info_result.success}")
        print(f"   └─ {team_info_result.items_processed}/{len(test_team_ids)} teams processed")
        print(f"✅ Task 3 (Arena Data): {arena_result.success}")
        print(f"   └─ {arena_result.items_processed}/{len(test_team_ids)} teams processed")
        print(f"✅ Task 4 (Team History): {history_result.success}")
        print(f"   └─ {history_result.items_processed}/{len(test_team_ids)} teams processed")
        print(f"✅ Task 5 (Home Games): {games_result.success}")
        print(f"   └─ {games_result.items_processed} games collected")
        if pricing_result:
            print(f"✅ Task 6 (Game Pricing): {pricing_result.success}")
            print(f"   └─ {pricing_result.items_processed} games with updated pricing")
        else:
            print(f"⚠️ Task 6 (Game Pricing): SKIPPED")
        
        # Note: Tasks 2,3,4,5 run in parallel, then Task 6 runs sequentially
        parallel_time = max(team_info_result.execution_time, 
                           arena_result.execution_time, 
                           history_result.execution_time,
                           games_result.execution_time)
        pricing_time = pricing_result.execution_time if pricing_result else 0
        total_time = team_ids_result.execution_time + parallel_time + pricing_time
        print(f"📊 Total execution time: {total_time:.1f}s (discovery + parallel collection + pricing)")
        
        # Recommendations
        all_tasks_success = all([
            team_ids_result.success, 
            team_info_result.success, 
            arena_result.success,
            history_result.success,
            games_result.success,
            pricing_result.success if pricing_result else True
        ])
        
        if all_tasks_success:
            print(f"\n✅ All tasks completed successfully!")
            print(f"💡 Task-based collector with parallel execution is working correctly")
            print(f"📈 Ready to scale up to multiple countries and league levels")
        else:
            print(f"\n⚠️  Some tasks had issues - review logs above")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        logger.exception("Full error details:")
    
    finally:
        api.logout()
        print("\n👋 Logged out")

if __name__ == "__main__":
    asyncio.run(test_usa_level1_collection())