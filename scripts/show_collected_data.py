#!/usr/bin/env python3
"""
Show collected data for all teams with timestamps to verify collection success.
"""

import sys
import os
import sqlite3
from datetime import datetime
from typing import Dict, List, Any
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from bb_arena_optimizer.storage.database import DatabaseManager

def show_collected_data():
    """Display all collected data with timestamps for verification."""
    
    db_manager = DatabaseManager("bb_arena_data.db")
    
    print("🔍 Collected Data Summary")
    print("=" * 80)
    
    with sqlite3.connect(db_manager.db_path) as conn:
        conn.row_factory = sqlite3.Row  # Enable column access by name
        cursor = conn.cursor()
        
        # Task 1: Team Discovery (should be exactly 21 teams from USA level 1)
        print("\n🎯 TASK 1: Team Discovery - Reconstructing the 21 teams")
        print("-" * 50)
        print("Method: 16 teams from current season + 5 teams from season 68 only")
        
        discovered_teams = set()
        
        # Step 1: Get current season teams from team_info (teams currently in NBBA level 1)
        cursor.execute("""
            SELECT DISTINCT bb_team_id FROM team_info 
            WHERE league_name = 'NBBA' AND league_level = 1
            ORDER BY bb_team_id
        """)
        
        current_season_teams = [int(row['bb_team_id']) for row in cursor.fetchall()]
        discovered_teams.update(current_season_teams)
        print(f"✅ Current season teams (NBBA level 1): {len(current_season_teams)}")
        print(f"   Team IDs: {', '.join(map(str, current_season_teams))}")
        
        # Step 2: Get season 68 teams from team_league_history 
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='team_league_history'
        """)
        
        if cursor.fetchone():
            cursor.execute("PRAGMA table_info(team_league_history)")
            history_columns = [col[1] for col in cursor.fetchall()]
            print(f"team_league_history columns: {', '.join(history_columns)}")
            
            # Check for the correct column names
            team_id_col = None
            season_col = None
            
            if 'team_id' in history_columns:
                team_id_col = 'team_id'
            elif 'bb_team_id' in history_columns:
                team_id_col = 'bb_team_id'
                
            if 'season' in history_columns:
                season_col = 'season'
            elif 'season_number' in history_columns:
                season_col = 'season_number'
            
            if team_id_col and season_col:
                # Get USA level 1 teams in season 68  
                cursor.execute(f"""
                    SELECT DISTINCT {team_id_col} FROM team_league_history 
                    WHERE {season_col} = 68 AND league_level = 1 AND league_name = 'USA NBBA'
                    ORDER BY {team_id_col}
                """)
                season_68_teams = [int(row[team_id_col]) for row in cursor.fetchall()]
                
                # Find teams that were in season 68 but not in current season (the 5 relegated teams)
                season_68_only = [t for t in season_68_teams if t not in discovered_teams]
                discovered_teams.update(season_68_only)
                
                print(f"✅ Season 68 teams: {len(season_68_teams)}")
                print(f"✅ Teams only in season 68 (relegated): {len(season_68_only)}")
                print(f"   Relegated team IDs: {', '.join(map(str, season_68_only))}")
            else:
                print(f"❌ team_league_history table missing required columns: {history_columns}")
                print(f"   Need: team_id column and season column")
        else:
            print("⚠️  team_league_history table not found - cannot get season 68 teams")
        
        # Convert to sorted list
        discovered_teams = sorted(list(discovered_teams))
        
        print(f"\n🎯 TOTAL DISCOVERED TEAMS: {len(discovered_teams)}")
        print(f"All 21 team IDs: {', '.join(map(str, discovered_teams))}")
        
        if len(discovered_teams) != 21:
            print(f"⚠️  Expected 21 teams but found {len(discovered_teams)}")
        
        if not discovered_teams:
            print("❌ No teams found - collection may not have run successfully")
            return
        
        # Limit to first 21 teams for display
        teams_to_show = discovered_teams[:21]
        
        # Task 2: Team Info Collection - Check each of the 21 teams
        print(f"\n📋 TASK 2: Team Info Collection - Checking 21 specific teams")
        print("-" * 50)
        
        team_info_success = 0
        team_info_missing = []
        
        for team_id in discovered_teams:
            cursor.execute("""
                SELECT * FROM team_info 
                WHERE bb_team_id = ?
                ORDER BY rowid DESC
                LIMIT 1
            """, (team_id,))
            
            team_info = cursor.fetchone()
            if team_info:
                team_info_success += 1
            else:
                team_info_missing.append(team_id)
        
        print(f"✅ Teams with team_info: {team_info_success}/{len(discovered_teams)}")
        
        if team_info_missing:
            print(f"❌ Teams missing team_info: {len(team_info_missing)}")
            print(f"   Missing team IDs: {', '.join(map(str, team_info_missing[:10]))}")
        
        # Show sample team_info data
        if team_info_success > 0:
            cursor.execute("""
                SELECT * FROM team_info 
                WHERE bb_team_id IN ({})
                ORDER BY rowid DESC
                LIMIT 3
            """.format(','.join('?' * len(discovered_teams))), discovered_teams)
            
            sample_infos = cursor.fetchall()
            print(f"\nSample team_info records:")
            for i, info in enumerate(sample_infos):
                print(f"  Record {i+1}: {dict(info)}")
        
        # Task 3: Arena Snapshots - Check each of the 21 teams
        print(f"\n🏟️ TASK 3: Arena Snapshots Collection - Checking 21 specific teams")
        print("-" * 50)
        
        arena_success = 0
        arena_missing = []
        
        for team_id in discovered_teams:
            cursor.execute("""
                SELECT * FROM arena_snapshots 
                WHERE team_id = ?
                ORDER BY rowid DESC
                LIMIT 1
            """, (team_id,))
            
            arena_snapshot = cursor.fetchone()
            if arena_snapshot:
                arena_success += 1
            else:
                arena_missing.append(team_id)
        
        print(f"✅ Teams with arena snapshots: {arena_success}/{len(discovered_teams)}")
        
        if arena_missing:
            print(f"❌ Teams missing arena snapshots: {len(arena_missing)}")
            print(f"   Missing team IDs: {', '.join(map(str, arena_missing[:10]))}")
        
        # Show sample arena data
        if arena_success > 0:
            cursor.execute("""
                SELECT * FROM arena_snapshots 
                WHERE team_id IN ({})
                ORDER BY rowid DESC
                LIMIT 3
            """.format(','.join('?' * len(discovered_teams))), discovered_teams)
            
            sample_arenas = cursor.fetchall()
            print(f"\nSample arena snapshots:")
            for i, arena in enumerate(sample_arenas):
                print(f"  Arena {i+1}: {dict(arena)}")
        
        # Task 3 continued: Price Snapshots - Check each of the 21 teams
        print(f"\n💰 TASK 3: Price Snapshots Collection - Checking 21 specific teams")
        print("-" * 50)
        
        price_success = 0
        price_missing = []
        
        for team_id in discovered_teams:
            cursor.execute("""
                SELECT * FROM price_snapshots 
                WHERE team_id = ?
                ORDER BY rowid DESC
                LIMIT 1
            """, (team_id,))
            
            price_snapshot = cursor.fetchone()
            if price_snapshot:
                price_success += 1
            else:
                price_missing.append(team_id)
        
        print(f"✅ Teams with price snapshots: {price_success}/{len(discovered_teams)}")
        
        if price_missing:
            print(f"❌ Teams missing price snapshots: {len(price_missing)}")
            print(f"   Missing team IDs: {', '.join(map(str, price_missing[:10]))}")
        
        # Show sample price data
        if price_success > 0:
            cursor.execute("""
                SELECT * FROM price_snapshots 
                WHERE team_id IN ({})
                ORDER BY rowid DESC
                LIMIT 3
            """.format(','.join('?' * len(discovered_teams))), discovered_teams)
            
            sample_prices = cursor.fetchall()
            print(f"\nSample price snapshots:")
            for i, price in enumerate(sample_prices):
                print(f"  Price {i+1}: {dict(price)}")
        
        # Task 4: Team History - Check each of the 21 teams
        print(f"\n📚 TASK 4: Team History Collection - Checking 21 specific teams")
        print("-" * 50)
        
        # First check if team_league_history table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='team_league_history'
        """)
        
        history_table_exists = cursor.fetchone()
        
        if history_table_exists:
            # Determine the correct column names
            cursor.execute("PRAGMA table_info(team_league_history)")
            history_columns = [col[1] for col in cursor.fetchall()]
            
            team_id_col = 'team_id' if 'team_id' in history_columns else 'bb_team_id'
            season_col = 'season' if 'season' in history_columns else 'season_number'
            
            history_success = 0
            history_missing = []
            total_entries = 0
            
            for team_id in discovered_teams:
                cursor.execute(f"""
                    SELECT COUNT(*) as entry_count FROM team_league_history 
                    WHERE {team_id_col} = ?
                """, (team_id,))
                
                result = cursor.fetchone()
                entry_count = result['entry_count'] if result else 0
                
                if entry_count > 0:
                    history_success += 1
                    total_entries += entry_count
                else:
                    history_missing.append(team_id)
            
            print(f"✅ Teams with team history: {history_success}/{len(discovered_teams)}")
            print(f"📊 Total history entries: {total_entries}")
            
            if history_missing:
                print(f"❌ Teams missing team history: {len(history_missing)}")
                print(f"   Missing team IDs: {', '.join(map(str, history_missing[:10]))}")
            
            # Show sample history data
            if history_success > 0:
                cursor.execute(f"""
                    SELECT {team_id_col}, COUNT(*) as entries, MIN({season_col}) as min_season, MAX({season_col}) as max_season
                    FROM team_league_history 
                    WHERE {team_id_col} IN ({','.join('?' * len(discovered_teams))})
                    GROUP BY {team_id_col}
                    ORDER BY entries DESC
                    LIMIT 5
                """, discovered_teams)
                
                sample_histories = cursor.fetchall()
                print(f"\nSample team history summaries:")
                for history in sample_histories:
                    team_id = history[team_id_col]
                    entries = history['entries']
                    seasons = f"{history['min_season']}-{history['max_season']}"
                    print(f"  Team {team_id}: {entries} entries, seasons {seasons}")
        else:
            print("⚠️  team_league_history table not found - history data may not be stored yet")
            print("    This is expected if team history storage isn't implemented in the schema")
        
        # Task 5: Home Games Collection - Check game data for the 21 teams
        print(f"\n🏈 TASK 5: Home Games Collection - Checking 21 specific teams")
        print("-" * 50)
        
        games_success = 0
        games_missing = []
        total_games_found = 0
        
        for team_id in discovered_teams:
            cursor.execute("""
                SELECT COUNT(*) as game_count FROM games 
                WHERE home_team_id = ?
            """, (team_id,))
            
            result = cursor.fetchone()
            game_count = result['game_count'] if result else 0
            
            if game_count > 0:
                games_success += 1
                total_games_found += game_count
            else:
                games_missing.append(team_id)
        
        print(f"✅ Teams with home games: {games_success}/{len(discovered_teams)}")
        print(f"📊 Total home games found: {total_games_found}")
        
        if games_missing:
            print(f"❌ Teams missing home games: {len(games_missing)}")
            print(f"   Missing team IDs: {', '.join(map(str, games_missing[:10]))}")
        
        # Show sample game data
        if games_success > 0:
            cursor.execute(f"""
                SELECT home_team_id, COUNT(*) as games, MIN(season) as min_season, MAX(season) as max_season
                FROM games 
                WHERE home_team_id IN ({','.join('?' * len(discovered_teams))})
                GROUP BY home_team_id
                ORDER BY games DESC
                LIMIT 5
            """, discovered_teams)
            
            sample_games = cursor.fetchall()
            print(f"\nSample home game summaries:")
            for game_summary in sample_games:
                team_id = game_summary['home_team_id']
                games = game_summary['games']
                seasons = f"{game_summary['min_season']}-{game_summary['max_season']}"
                print(f"  Team {team_id}: {games} home games, seasons {seasons}")
        
        # Overall Summary
        print(f"\n🎉 COLLECTION VERIFICATION SUMMARY FOR 21 TEAMS")
        print("=" * 60)
        
        print(f"✅ Task 1 (Team Discovery): {'SUCCESS' if len(discovered_teams) == 21 else 'PARTIAL'}")
        print(f"   └─ {len(discovered_teams)}/21 teams discovered")
        
        print(f"✅ Task 2 (Team Info): {'SUCCESS' if team_info_success == len(discovered_teams) else 'PARTIAL'}")
        print(f"   └─ {team_info_success}/{len(discovered_teams)} teams have team_info")
        
        print(f"✅ Task 3a (Arena Snapshots): {'SUCCESS' if arena_success == len(discovered_teams) else 'PARTIAL'}")
        print(f"   └─ {arena_success}/{len(discovered_teams)} teams have arena snapshots")
        
        print(f"✅ Task 3b (Price Snapshots): {'SUCCESS' if price_success == len(discovered_teams) else 'PARTIAL'}")
        print(f"   └─ {price_success}/{len(discovered_teams)} teams have price snapshots")
        
        if history_table_exists:
            print(f"✅ Task 4 (Team History): {'SUCCESS' if history_success == len(discovered_teams) else 'PARTIAL'}")
            print(f"   └─ {history_success}/{len(discovered_teams)} teams have history data")
        else:
            print(f"⚠️  Task 4 (Team History): PENDING")
            print(f"   └─ History table not found - may need schema update")
        
        print(f"✅ Task 5 (Home Games): {'SUCCESS' if games_success == len(discovered_teams) else 'PARTIAL'}")
        print(f"   └─ {games_success}/{len(discovered_teams)} teams have home games ({total_games_found} total)")
        
        # Overall success rate
        total_tasks = 5 if history_table_exists else 4
        successful_tasks = 0
        
        if len(discovered_teams) == 21:
            successful_tasks += 1
        if team_info_success == len(discovered_teams):
            successful_tasks += 1
        if arena_success == len(discovered_teams) and price_success == len(discovered_teams):
            successful_tasks += 1
        if history_table_exists and history_success == len(discovered_teams):
            successful_tasks += 1
        if games_success == len(discovered_teams):
            successful_tasks += 1
        
        success_rate = successful_tasks / total_tasks
        print(f"\n📊 Overall Success Rate: {successful_tasks}/{total_tasks} tasks ({success_rate:.1%})")
        
        # Show collection timing
        if arena_success > 0:
            # Get a sample arena snapshot for timestamp
            cursor.execute("""
                SELECT * FROM arena_snapshots 
                ORDER BY rowid DESC
                LIMIT 1
            """)
            sample_snapshot = cursor.fetchone()
            if sample_snapshot:
                first_snapshot = dict(sample_snapshot)
                timestamp_fields = ['created_at', 'updated_at', 'timestamp', 'date']
                latest_collection = None
                
                for field in timestamp_fields:
                    if field in first_snapshot and first_snapshot[field]:
                        latest_collection = first_snapshot[field]
                        print(f"\n⏰ Latest collection timestamp ({field}): {latest_collection}")
                        break
                
                if not latest_collection:
                    print(f"\n⏰ Collection timestamp fields not found in data")
                    print(f"   Available fields: {list(first_snapshot.keys())}")

if __name__ == "__main__":
    show_collected_data()