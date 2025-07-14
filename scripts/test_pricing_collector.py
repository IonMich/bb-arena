#!/usr/bin/env python3
"""
Test script for the historical pricing data collector.

This script tests the collector and shows what database operations would occur,
including proper pricing logic for games vs price updates.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from bb_arena_optimizer.collecting.team_arena_collector import TeamArenaCollector
from bb_arena_optimizer.collecting.pricing_service import HistoricalPricingService
from bb_arena_optimizer.storage.database import DatabaseManager
from bb_arena_optimizer.utils.logging_config import setup_logging


def test_collection_and_database_operations(team_id: str = "29613", dry_run: bool = True):
    """Test the team arena collector and show database operations.
    
    Args:
        team_id: Team ID to test with (default: 29613)
        dry_run: If True, don't actually update database, just show what would happen
    """
    print(f"Testing Team Arena Collector with team {team_id}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE UPDATE'}")
    print("=" * 60)
    
    try:
        # Step 1: Collect the data
        print("📊 STEP 1: Collecting arena data...")
        with TeamArenaCollector(request_delay=1.0) as collector:
            result = collector.collect_team_arena_data(team_id)
        
        if not result.success:
            print(f"❌ Collection failed: {result.error_message}")
            return
        
        print(f"✅ Collection successful!")
        print(f"   - Games found: {result.last_10_games_found}")
        print(f"   - Price changes found: {result.price_changes_found}")
        print()
        
        # Step 2: Analyze the collected data
        print("🔍 STEP 2: Analyzing collected data...")
        
        games = [g for g in result.games_data if not g.is_price_change]
        price_updates = [g for g in result.games_data if g.is_price_change]
        
        # Sort by date for chronological analysis, with table_row_index as tiebreaker for same-day events
        games.sort(key=lambda x: (x.date or datetime.min, x.table_row_index or 0))
        price_updates.sort(key=lambda x: (x.date or datetime.min, x.table_row_index or 0))
        
        print(f"📅 Price Updates (chronological):")
        if not price_updates:
            print("   - No price updates found")
        else:
            for i, update in enumerate(price_updates, 1):
                print(f"   {i}. {update.date.strftime('%Y-%m-%d') if update.date else 'Unknown'}: "
                      f"B=${update.bleachers_price}, L=${update.lower_tier_price}, "
                      f"C=${update.courtside_price}, LB=${update.luxury_boxes_price}")
        
        print(f"\n🏀 Games (chronological):")
        for i, game in enumerate(games, 1):
            print(f"   {i}. {game.date.strftime('%Y-%m-%d') if game.date else 'Unknown'} vs {game.opponent} "
                  f"- Attendance: {game.attendance}")
        print()
        
        # Step 3: Database analysis
        print("🗄️  STEP 3: Database analysis...")
        
        try:
            db_manager = DatabaseManager()
            pricing_service = HistoricalPricingService(db_manager)
            
            # Check what games exist in database for this team
            stored_games = db_manager.get_games_for_team(team_id, limit=100)
            print(f"   - Games in database for team {team_id}: {len(stored_games)}")
            
            if stored_games:
                print(f"   - Date range: {min(g.date for g in stored_games if g.date)} to {max(g.date for g in stored_games if g.date)}")
            
            # Step 4: Pricing logic analysis
            print("\n💰 STEP 4: Pricing logic analysis...")
            
            if not price_updates:
                print("   ✅ No price updates found - can use current arena snapshot for all games")
                
                # Check if we have price snapshots
                price_snapshots = db_manager.get_price_history(team_id)
                if price_snapshots:
                    latest_snapshot = max(price_snapshots, key=lambda x: x.created_at or datetime.min)
                    print(f"   📸 Latest price snapshot: {latest_snapshot.created_at}")
                    print(f"      Prices: B=${latest_snapshot.bleachers_price}, L=${latest_snapshot.lower_tier_price}, "
                          f"C=${latest_snapshot.courtside_price}, LB=${latest_snapshot.luxury_boxes_price}")
                    
                    updatable_games = []
                    for game in games:
                        matched_game = next((sg for sg in stored_games if sg.date and game.date and 
                                           abs((sg.date.date() - game.date.date()).days) <= 1), None)
                        if matched_game:
                            updatable_games.append((game, matched_game))
                    
                    print(f"   🎯 Games that can be updated with current pricing: {len(updatable_games)}")
                else:
                    print("   ⚠️  No price snapshots available - cannot determine pricing")
                    
            else:
                print("   ⚠️  Price updates found - complex pricing logic needed")
                oldest_price_update = min(price_updates, key=lambda x: x.date or datetime.max)
                newest_price_update = max(price_updates, key=lambda x: x.date or datetime.min)
                
                print(f"   📅 Price update period: {oldest_price_update.date} to {newest_price_update.date}")
                
                # Categorize games
                games_before_updates = [g for g in games if g.date and oldest_price_update.date and 
                                      g.date < oldest_price_update.date]
                games_after_updates = [g for g in games if g.date and newest_price_update.date and 
                                     g.date > newest_price_update.date]
                games_during_updates = [g for g in games if g not in games_before_updates and g not in games_after_updates]
                
                print(f"   📊 Games before oldest price update: {len(games_before_updates)}")
                print(f"   📊 Games during price update period: {len(games_during_updates)}")
                print(f"   📊 Games after newest price update: {len(games_after_updates)}")
                
                if games_before_updates:
                    print("   ❌ Games before updates: Need historical price snapshots (likely unavailable)")
                
                if games_after_updates:
                    print("   ❌ Games after updates: No official games yet, cannot update pricing")
                
                if games_during_updates:
                    print("   ⚡ Games during updates: Need to match with specific price periods")
            
            # Step 5: Show what would happen
            print(f"\n🔄 STEP 5: Database operations ({'DRY RUN' if dry_run else 'EXECUTING'})...")
            
            if dry_run:
                print("   📋 What WOULD happen:")
                
                if not price_updates:
                    # Simple case - use current pricing
                    price_snapshots = db_manager.get_price_history(team_id)
                    if price_snapshots:
                        latest_snapshot = max(price_snapshots, key=lambda x: x.created_at or datetime.min)
                        updatable_count = 0
                        for game in games:
                            matched_game = next((sg for sg in stored_games if sg.date and game.date and 
                                               abs((sg.date.date() - game.date.date()).days) <= 1), None)
                            if matched_game:
                                updatable_count += 1
                                needs_update = (
                                    matched_game.bleachers_price != latest_snapshot.bleachers_price or
                                    matched_game.lower_tier_price != latest_snapshot.lower_tier_price or
                                    matched_game.courtside_price != latest_snapshot.courtside_price or
                                    matched_game.luxury_boxes_price != latest_snapshot.luxury_boxes_price
                                )
                                status = "UPDATE" if needs_update else "NO CHANGE"
                                print(f"      • {game.date.strftime('%Y-%m-%d')} vs {game.opponent}: {status}")
                        
                        print(f"   📊 Summary: {updatable_count} games would be updated with current pricing")
                    else:
                        print("      ❌ No price snapshots available - no updates possible")
                else:
                    # Complex case with price updates - analyze each game
                    print("      📋 Detailed analysis by game:")
                    
                    oldest_price_update = min(price_updates, key=lambda x: x.date or datetime.max)
                    newest_price_update = max(price_updates, key=lambda x: x.date or datetime.min)
                    
                    games_before_updates = [g for g in games if g.date and oldest_price_update.date and 
                                          g.date < oldest_price_update.date]
                    games_after_updates = [g for g in games if g.date and newest_price_update.date and 
                                         g.date > newest_price_update.date]
                    games_during_updates = [g for g in games if g not in games_before_updates and g not in games_after_updates]
                    
                    updatable_count = 0
                    
                    # Analyze games before updates
                    for game in games_before_updates:
                        print(f"      • {game.date.strftime('%Y-%m-%d')} vs {game.opponent}: ❌ CANNOT UPDATE (before price updates)")
                    
                    # Analyze games during updates - these CAN be updated!
                    for game in games_during_updates:
                        matched_game = next((sg for sg in stored_games if sg.date and game.date and 
                                           abs((sg.date.date() - game.date.date()).days) <= 1), None)
                        if matched_game:
                            # Find the most recent price update BEFORE this game
                            # Table is in REVERSE chronological order (newer events have smaller row indices)
                            # So for same-day events, LARGER row index means EARLIER in time
                            applicable_price = None
                            for price_update in sorted(price_updates, key=lambda x: (x.date or datetime.min, x.table_row_index or 0)):
                                if price_update.date and game.date:
                                    # Price update must be before game date, OR same day but LATER in table (happened earlier)
                                    if (price_update.date < game.date or 
                                        (price_update.date.date() == game.date.date() and 
                                         (price_update.table_row_index or 0) > (game.table_row_index or 0))):
                                        applicable_price = price_update
                            
                            if applicable_price:
                                needs_update = (
                                    matched_game.bleachers_price != applicable_price.bleachers_price or
                                    matched_game.lower_tier_price != applicable_price.lower_tier_price or
                                    matched_game.courtside_price != applicable_price.courtside_price or
                                    matched_game.luxury_boxes_price != applicable_price.luxury_boxes_price
                                )
                                status = "✅ UPDATE" if needs_update else "➖ NO CHANGE"
                                updatable_count += 1
                                price_info = f"B=${applicable_price.bleachers_price}, L=${applicable_price.lower_tier_price}, C=${applicable_price.courtside_price}, LB=${applicable_price.luxury_boxes_price}"
                                print(f"      • {game.date.strftime('%Y-%m-%d')} vs {game.opponent}: {status} (using {applicable_price.date.strftime('%m-%d')} prices: {price_info})")
                            else:
                                print(f"      • {game.date.strftime('%Y-%m-%d')} vs {game.opponent}: ❌ CANNOT UPDATE (no applicable price before game date)")
                        else:
                            print(f"      • {game.date.strftime('%Y-%m-%d')} vs {game.opponent}: ❌ CANNOT UPDATE (game not in database)")
                    
                    # Analyze games after updates
                    for game in games_after_updates:
                        print(f"      • {game.date.strftime('%Y-%m-%d')} vs {game.opponent}: ❌ CANNOT UPDATE (after price updates, no current prices)")
                    
                    print(f"      📊 Summary: {updatable_count} games can be updated using collected price data")
            else:
                # Actually perform the update
                update_result = pricing_service.update_games_with_pricing_data(team_id, result)
                print(f"   ✅ Database update completed:")
                print(f"      • Games updated: {update_result['games_updated']}")
                print(f"      • Games not found: {update_result['games_not_found']}")
                print(f"      • Price changes processed: {update_result['price_changes_processed']}")
        
        except Exception as e:
            print(f"   ❌ Database analysis failed: {e}")
        
        print(f"\n{'='*60}")
        print(f"✅ Test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    from datetime import datetime
    
    # Setup logging to see what's happening
    setup_logging(level="DEBUG")
    
    # Parse command line arguments
    team_id = sys.argv[1] if len(sys.argv) > 1 else "29613"
    dry_run = "--live" not in sys.argv  # Default to dry run unless --live specified
    
    if not dry_run:
        confirm = input("⚠️  This will make actual database changes. Continue? (y/N): ")
        if confirm.lower() != 'y':
            print("Cancelled.")
            sys.exit(0)
    
    test_collection_and_database_operations(team_id, dry_run)
