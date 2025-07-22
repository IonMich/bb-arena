#!/usr/bin/env python3
"""
Test the task-based collector with configurable countries, seasons, and league levels.
Defaults to USA level 1 teams for seasons 68,69.
"""

import sys
import os
import asyncio
import argparse
import sqlite3
from pathlib import Path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from bb_arena_optimizer.api.client import BuzzerBeaterAPI
from bb_arena_optimizer.storage.database import DatabaseManager
from bb_arena_optimizer.collecting.task_based_collector import TaskBasedCollector, RateLimitConfig, run_complete_data_collection_pipeline
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_collection(countries, seasons, max_league_level, selected_tasks):
    """Test task-based collection for specified countries, seasons, and league levels."""
    
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
        
        print(f"\n🌍 Testing Collection")
        print("=" * 60)
        print(f"Target: Countries {countries}, Seasons {seasons}, Max Level {max_league_level}")
        
        # Task 1: Discover teams
        print("\n🎯 TASK 1: Discovering team IDs")
        print("-" * 40)
        
        team_ids_result = await collector.task_1_collect_team_ids(
            countries=countries,
            seasons=seasons,
            max_league_level=max_league_level
        )
        
        if not team_ids_result.success:
            print(f"❌ Task 1 failed: {team_ids_result.error}")
            return
        
        team_ids = team_ids_result.data
        print(f"✅ Task 1 completed!")
        print(f"   - Teams discovered: {len(team_ids)}")
        print(f"   - Execution time: {team_ids_result.execution_time:.1f}s")
        print(f"   - Sample team IDs: {list(team_ids)[:10]}")
        
        # Validate expected results (only for USA Level 1 default case)
        if countries == [1] and seasons == [68, 69] and max_league_level == 1:
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
        else:
            print(f"✅ Found {len(team_ids)} teams for the specified criteria")
        
        # Use all discovered teams since the count should be manageable
        test_team_ids = team_ids
        print(f"\n🧪 Processing all {len(test_team_ids)} discovered teams")
        
        # Run selected tasks
        print(f"\n🚀 TASKS {selected_tasks}: Running selected data collection tasks")
        print("-" * 80)
        
        # Initialize results
        team_info_result = None
        arena_result = None
        history_result = None
        games_result = None
        pricing_result = None
        
        # Run tasks 2,3,4,5 in parallel if selected
        parallel_tasks = []
        
        if 2 in selected_tasks:
            print("📋 Will run Task 2: Team Info Collection")
            parallel_tasks.append(('team_info', collector.task_2_collect_team_info(test_team_ids)))
        
        if 3 in selected_tasks:
            print("🏟️ Will run Task 3: Arena Snapshots Collection")
            parallel_tasks.append(('arena', collector.task_3_collect_arena_snapshots(test_team_ids)))
        
        if 4 in selected_tasks:
            print("📚 Will run Task 4: Team History Collection")
            parallel_tasks.append(('history', collector.task_4_collect_team_history(test_team_ids)))
        
        if 5 in selected_tasks:
            print("🏈 Will run Task 5: Home Games Collection")
            parallel_tasks.append(('games', collector.task_5_collect_home_games(test_team_ids, seasons)))
        
        # Execute parallel tasks
        if parallel_tasks:
            print(f"\n⚡ Running {len(parallel_tasks)} tasks in parallel...")
            task_names, task_coroutines = zip(*parallel_tasks)
            results = await asyncio.gather(*task_coroutines, return_exceptions=True)
            
            # Map results back to variables
            for task_name, result in zip(task_names, results):
                if isinstance(result, Exception):
                    print(f"❌ Task {task_name} failed with exception: {result}")
                    # Create a failed TaskResult
                    from bb_arena_optimizer.collecting.task_based_collector import TaskResult
                    result = TaskResult(task_name=task_name, success=False, error=str(result))
                
                if task_name == 'team_info':
                    team_info_result = result
                elif task_name == 'arena':
                    arena_result = result
                elif task_name == 'history':
                    history_result = result
                elif task_name == 'games':
                    games_result = result
        
        # Run task 6 sequentially after parallel tasks (if selected)
        if 6 in selected_tasks:
            print("\n💰 Running Task 6: Game Pricing Updates (sequential)")
            pricing_result = await collector.task_6_update_game_pricing(test_team_ids)
        
        # Task 2 Results
        if team_info_result:
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
        if arena_result:
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
        if history_result:
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
        if games_result:
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
        
        # Overall summary
        print(f"\n🎉 Collection Test Results")
        print("=" * 60)
        print(f"✅ Task 1 (Team Discovery): {team_ids_result.success}")
        print(f"   └─ {len(team_ids)} teams discovered from countries {countries}, max level {max_league_level}")
        
        if team_info_result:
            print(f"✅ Task 2 (Team Info): {team_info_result.success}")
            print(f"   └─ {team_info_result.items_processed}/{len(test_team_ids)} teams processed")
        elif 2 in selected_tasks:
            print(f"❌ Task 2 (Team Info): FAILED")
        else:
            print(f"⚠️ Task 2 (Team Info): SKIPPED")
            
        if arena_result:
            print(f"✅ Task 3 (Arena Data): {arena_result.success}")
            print(f"   └─ {arena_result.items_processed}/{len(test_team_ids)} teams processed")
        elif 3 in selected_tasks:
            print(f"❌ Task 3 (Arena Data): FAILED")
        else:
            print(f"⚠️ Task 3 (Arena Data): SKIPPED")
            
        if history_result:
            print(f"✅ Task 4 (Team History): {history_result.success}")
            print(f"   └─ {history_result.items_processed}/{len(test_team_ids)} teams processed")
        elif 4 in selected_tasks:
            print(f"❌ Task 4 (Team History): FAILED")
        else:
            print(f"⚠️ Task 4 (Team History): SKIPPED")
            
        if games_result:
            print(f"✅ Task 5 (Home Games): {games_result.success}")
            print(f"   └─ {games_result.items_processed} games collected")
        elif 5 in selected_tasks:
            print(f"❌ Task 5 (Home Games): FAILED")
        else:
            print(f"⚠️ Task 5 (Home Games): SKIPPED")
            
        if pricing_result:
            print(f"✅ Task 6 (Game Pricing): {pricing_result.success}")
            print(f"   └─ {pricing_result.items_processed} games with updated pricing")
        elif 6 in selected_tasks:
            print(f"❌ Task 6 (Game Pricing): FAILED")
        else:
            print(f"⚠️ Task 6 (Game Pricing): SKIPPED")
        
        # Calculate total execution time
        selected_results = [r for r in [team_info_result, arena_result, history_result, games_result, pricing_result] if r is not None]
        tasks_time = sum(r.execution_time for r in selected_results)
        total_time = team_ids_result.execution_time + tasks_time
        print(f"📊 Total execution time: {total_time:.1f}s (discovery + selected tasks)")
        
        # Recommendations
        selected_results_success = [r.success for r in selected_results]
        all_tasks_success = team_ids_result.success and all(selected_results_success)
        
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

def get_available_countries(db_path: str = "bb_arena_data.db") -> list[tuple[int, str]]:
    """Get available countries from the league_hierarchy table.
    
    Returns:
        List of (country_id, country_name) tuples
    """
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("""
                SELECT DISTINCT country_id, country_name 
                FROM league_hierarchy 
                ORDER BY country_id
            """)
            return cursor.fetchall()
    except sqlite3.Error:
        return []

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Test task-based collector with configurable parameters',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --list-countries
      List available countries

  %(prog)s
      Use default (USA level 1, seasons 68-69, all tasks)

  %(prog)s --tasks 5 6
      Run task 1 (always runs) plus tasks 5 (home games) and 6 (pricing)

  %(prog)s --countries 1 7 12 --seasons 68 69 --max-league-level 2 --tasks 2 3 4
      Custom parameters with only team info, arena, and history tasks

  %(prog)s --countries 1 --seasons 68 69 --tasks 5
      Resume collection: skip tasks 2,3,4 and only run home games collection
        """.strip()
    )
    
    parser.add_argument(
        '--list-countries',
        action='store_true',
        help='List available countries from database and exit'
    )
    
    parser.add_argument(
        '--countries', 
        type=int, 
        nargs='+', 
        default=[1], 
        help='Country IDs to collect data for (use --list-countries to see available countries)'
    )
    
    parser.add_argument(
        '--seasons', 
        type=int, 
        nargs='+', 
        default=[68, 69], 
        help='Season numbers to collect data for'
    )
    
    parser.add_argument(
        '--max-league-level', 
        type=int, 
        default=1, 
        help='Maximum league level to collect (1=top level, 2=includes second level, etc.)'
    )
    
    parser.add_argument(
        '--tasks',
        type=int,
        nargs='+',
        choices=[2, 3, 4, 5, 6],
        default=[2, 3, 4, 5, 6],
        help='Tasks to run after Task 1 (always runs). Choose from: 2=team_info, 3=arena_snapshots, 4=team_history, 5=home_games, 6=game_pricing'
    )
    
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    
    if args.list_countries:
        countries = get_available_countries()
        if countries:
            print("Available countries:")
            print("ID\tCountry Name")
            print("-" * 30)
            for country_id, country_name in countries:
                print(f"{country_id}\t{country_name}")
        else:
            print("No countries found in database.")
            print("You may need to populate the league_hierarchy table first.")
        sys.exit(0)
    
    asyncio.run(test_collection(args.countries, args.seasons, args.max_league_level, args.tasks))