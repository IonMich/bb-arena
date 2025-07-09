"""Collect historical data for Season 68 with enhanced metadata."""

import os
import time
from datetime import datetime
from dotenv import load_dotenv
from bb_arena_optimizer.api.client import BuzzerBeaterAPI
from bb_arena_optimizer.storage.database import DatabaseManager
from bb_arena_optimizer.storage.models import GameRecord


def main() -> None:
    """Collect historical data for Season 68."""
    load_dotenv()
    
    username = os.getenv("BB_USERNAME")
    security_code = os.getenv("BB_SECURITY_CODE")
    
    if not username or not security_code:
        print("❌ Please set BB_USERNAME and BB_SECURITY_CODE in .env file")
        return
    
    print("🏀 Historical Data Collection - Season 68")
    print("=" * 50)
    
    # Initialize database (this will run migrations)
    db_manager = DatabaseManager("bb_arena_data.db")
    
    target_season = 68
    
    print(f"Collecting data for Season {target_season}")
    print()
    
    with BuzzerBeaterAPI(username, security_code) as api:
        # Get team info once for metadata
        print("👥 Getting team info for metadata...")
        team_info = api.get_team_info()
        team_id = None
        country = None
        division = None
        
        if team_info:
            team_id = str(team_info.get('id', ''))
            country = team_info.get('country')
            division = team_info.get('league')
            print(f"Team: {team_info.get('name')} ({team_info.get('short_name')})")
            print(f"Country: {country}, Division: {division}")
        else:
            print("⚠️  Could not get team info - proceeding without team metadata")
        print()
        
        print(f"🎯 Season {target_season}")
        print("-" * 40)
        
        try:
            # Get season schedule to determine date range and game metadata
            print(f"📅 Getting Season {target_season} schedule...")
            schedule_data = api.get_schedule(season=target_season)
            
            if not schedule_data or not schedule_data.get('games'):
                print(f"❌ Could not get Season {target_season} schedule")
                return
            
            season_games = schedule_data['games']
            print(f"Found {len(season_games)} games in Season {target_season} schedule")
            print()
            
            # Process games from the schedule
            games_collected = 0
            games_with_attendance = 0
            games_updated = 0
            games_skipped = 0
            
            for i, game in enumerate(season_games):
                game_id = str(game.get('id', ''))
                if not game_id:
                    continue
                    
                print(f"Game {i+1}/{len(season_games)}: {game_id}")
                
                try:
                    # Check if we already have this game with attendance AND metadata
                    import sqlite3
                    with sqlite3.connect(db_manager.db_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            "SELECT total_attendance, season, division, country FROM games WHERE game_id = ?", 
                            (game_id,)
                        )
                        existing_data = cursor.fetchone()
                    
                    if existing_data:
                        existing_att, existing_season, existing_div, existing_country = existing_data
                        if (existing_att is not None and existing_season is not None and 
                            existing_div is not None and existing_country is not None):
                            print(f"  ✅ Already complete (attendance: {existing_att:,}, metadata: {existing_season}/{existing_country}/{existing_div})")
                            games_skipped += 1
                            continue
                    
                    # Parse game date
                    game_date = None
                    if game.get('date'):
                        try:
                            game_date = datetime.fromisoformat(game['date'].replace("Z", "+00:00"))
                        except (ValueError, AttributeError):
                            pass
                    
                    # Determine cup round for cup games
                    cup_round = None
                    game_type = game.get('type', '')
                    if 'cup' in game_type.lower():
                        # Try to infer cup round from game type or date
                        if 'final' in game_type.lower():
                            cup_round = 'final'
                        elif 'semi' in game_type.lower():
                            cup_round = 'semifinal'
                        elif 'quarter' in game_type.lower():
                            cup_round = 'quarterfinal'
                        else:
                            cup_round = 'early_round'
                    
                    # Try to get boxscore data for attendance and scores
                    print(f"  📊 Getting boxscore...")
                    boxscore_data = api.get_boxscore(game_id)
                    
                    # Create game record with enhanced metadata
                    game_record = GameRecord(
                        game_id=game_id,
                        team_id=team_id,
                        date=game_date,
                        opponent=game.get('opponent'),
                        is_home=game.get('home', False),
                        game_type=game_type,
                        season=target_season,
                        division=division,
                        country=country,
                        cup_round=cup_round,
                        created_at=datetime.now()
                    )
                    
                    attendance_found = False
                    if boxscore_data:
                        # Verify game ID match
                        returned_id = str(boxscore_data.get("game_id", ""))
                        if returned_id != game_id:
                            print(f"  🚨 ID mismatch: got {returned_id}, expected {game_id}")
                            continue
                        
                        # Add attendance and scores from boxscore
                        attendance = boxscore_data.get("attendance", {})
                        scores = boxscore_data.get("scores", {})
                        
                        if isinstance(attendance, dict) and attendance:
                            game_record.bleachers_attendance = attendance.get("bleachers")
                            game_record.lower_tier_attendance = attendance.get("lower_tier")
                            game_record.courtside_attendance = attendance.get("courtside")
                            game_record.luxury_boxes_attendance = attendance.get("luxury_boxes")
                            
                            total_att = sum(v for v in attendance.values() if isinstance(v, (int, float)))
                            if total_att > 0:
                                game_record.total_attendance = int(total_att)
                                print(f"  ✅ Attendance: {total_att:,}")
                                attendance_found = True
                        
                        if isinstance(scores, dict) and scores:
                            game_record.score_home = scores.get("home")
                            game_record.score_away = scores.get("away")
                            print(f"  🏀 Score: {scores.get('home', '?')} - {scores.get('away', '?')}")
                    
                    if not attendance_found:
                        print(f"  ⚠️  No attendance data available")
                    
                    # Save to database
                    db_manager.save_game_record(game_record)
                    
                    if existing_data:
                        games_updated += 1
                        print(f"  💾 Updated existing record")
                    else:
                        games_collected += 1
                        print(f"  💾 Saved new record")
                    
                    if attendance_found:
                        games_with_attendance += 1
                    
                    # Small delay to be respectful to the API
                    time.sleep(0.1)
                    
                except Exception as e:
                    print(f"  ❌ Error processing game {game_id}: {e}")
                    continue
            
            print(f"\n🎉 Season {target_season} Collection Complete!")
            print(f"✅ New games collected: {games_collected}")
            print(f"🔄 Existing games updated: {games_updated}")
            print(f"⏭️  Games skipped (complete): {games_skipped}")
            print(f"🎟️  Games with attendance: {games_with_attendance}")
            
        except Exception as e:
            print(f"❌ Error processing Season {target_season}: {e}")
    
    # Show final database stats for Season 68
    import sqlite3
    with sqlite3.connect(db_manager.db_path) as conn:
        cursor = conn.cursor()
        
        # Stats by game type for Season 68
        cursor.execute("""
            SELECT 
                game_type,
                COUNT(*) as total_games,
                COUNT(CASE WHEN total_attendance IS NOT NULL THEN 1 END) as games_with_attendance,
                AVG(CASE WHEN total_attendance IS NOT NULL THEN total_attendance END) as avg_attendance
            FROM games 
            WHERE season = 68
            GROUP BY game_type 
            ORDER BY total_games DESC
        """)
        game_type_stats = cursor.fetchall()
        
        print(f"\n📊 Season 68 Summary by Game Type:")
        for game_type, total, with_att, avg_att in game_type_stats:
            avg_str = f"{avg_att:,.0f}" if avg_att else "N/A"
            print(f"  {game_type}: {total} games, {with_att} with attendance (avg: {avg_str})")


if __name__ == "__main__":
    main()
