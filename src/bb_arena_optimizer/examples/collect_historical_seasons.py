"""Collect historical data for the past 5 seasons with enhanced metadata."""

import os
import time
from datetime import datetime
from dotenv import load_dotenv
from bb_arena_optimizer.api.client import BuzzerBeaterAPI
from bb_arena_optimizer.storage.database import DatabaseManager
from bb_arena_optimizer.storage.models import GameRecord


def main() -> None:
    """Collect historical data for the past 5 seasons."""
    load_dotenv()
    
    username = os.getenv("BB_USERNAME")
    security_code = os.getenv("BB_SECURITY_CODE")
    
    if not username or not security_code:
        print("❌ Please set BB_USERNAME and BB_SECURITY_CODE in .env file")
        return
    
    print("🏀 Historical Data Collection - Past 5 Seasons")
    print("=" * 60)
    
    # Initialize database (this will run migrations)
    db_manager = DatabaseManager("bb_arena_data.db")
    
    # Current season is 69 (July 2025), so collect seasons 64-68
    current_season = 69
    seasons_to_collect = list(range(current_season - 5, current_season))  # [64, 65, 66, 67, 68]
    
    print(f"Collecting data for seasons: {seasons_to_collect}")
    print()
    
    total_games_collected = 0
    total_games_with_attendance = 0
    
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
        
        for season in seasons_to_collect:
            print(f"🎯 Season {season}")
            print("-" * 40)
            
            try:
                # Get season schedule to determine date range and game metadata
                print(f"📅 Getting Season {season} schedule...")
                schedule_data = api.get_schedule(season=season)
                
                if not schedule_data or not schedule_data.get('games'):
                    print(f"❌ Could not get Season {season} schedule")
                    continue
                
                season_games = schedule_data['games']
                print(f"Found {len(season_games)} games in Season {season} schedule")
                
                # Process games from the schedule
                season_games_collected = 0
                season_games_with_attendance = 0
                
                for i, game in enumerate(season_games):
                    game_id = str(game.get('id', ''))
                    if not game_id:
                        continue
                        
                    print(f"  Game {i+1}/{len(season_games)}: {game_id}")
                    
                    try:
                        # Check if we already have this game with attendance
                        import sqlite3
                        with sqlite3.connect(db_manager.db_path) as conn:
                            cursor = conn.cursor()
                            cursor.execute(
                                "SELECT total_attendance FROM games WHERE game_id = ?", 
                                (game_id,)
                            )
                            existing_attendance = cursor.fetchone()
                        
                        if existing_attendance and existing_attendance[0] is not None:
                            print(f"    ✅ Already has attendance ({existing_attendance[0]:,})")
                            season_games_collected += 1
                            season_games_with_attendance += 1
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
                        boxscore_data = api.get_boxscore(game_id)
                        
                        # Create game record with enhanced metadata
                        game_record = GameRecord(
                            game_id=game_id,
                            team_id=team_id,
                            date=game_date,
                            opponent=game.get('opponent'),
                            is_home=game.get('home', False),
                            game_type=game_type,
                            season=season,
                            division=division,
                            country=country,
                            cup_round=cup_round,
                            created_at=datetime.now()
                        )
                        
                        if boxscore_data:
                            # Verify game ID match
                            returned_id = str(boxscore_data.get("game_id", ""))
                            if returned_id != game_id:
                                print(f"    🚨 ID mismatch: got {returned_id}, expected {game_id}")
                                continue
                            
                            # Add attendance and scores from boxscore
                            attendance = boxscore_data.get("attendance", {})
                            scores = boxscore_data.get("scores", {})
                            
                            if isinstance(attendance, dict):
                                game_record.bleachers_attendance = attendance.get("bleachers")
                                game_record.lower_tier_attendance = attendance.get("lower_tier")
                                game_record.courtside_attendance = attendance.get("courtside")
                                game_record.luxury_boxes_attendance = attendance.get("luxury_boxes")
                                
                                total_att = sum(v for v in attendance.values() if isinstance(v, (int, float)))
                                if total_att > 0:
                                    game_record.total_attendance = int(total_att)
                                    print(f"    ✅ Attendance: {total_att:,}")
                                    season_games_with_attendance += 1
                                else:
                                    print(f"    ℹ️  No attendance data")
                            
                            if isinstance(scores, dict):
                                game_record.score_home = scores.get("home")
                                game_record.score_away = scores.get("away")
                        else:
                            print(f"    ⚠️  No boxscore data available")
                        
                        # Save to database
                        db_manager.save_game_record(game_record)
                        season_games_collected += 1
                        
                        # Small delay to be respectful to the API
                        time.sleep(0.1)
                        
                    except Exception as e:
                        print(f"    ❌ Error processing game {game_id}: {e}")
                        continue
                
                print(f"\n✅ Season {season} complete:")
                print(f"   Games collected: {season_games_collected}")
                print(f"   Games with attendance: {season_games_with_attendance}")
                print()
                
                total_games_collected += season_games_collected
                total_games_with_attendance += season_games_with_attendance
                
            except Exception as e:
                print(f"❌ Error processing Season {season}: {e}")
                continue
    
    print("🎉 Historical Collection Complete!")
    print("=" * 60)
    print(f"✅ Total games collected: {total_games_collected}")
    print(f"✅ Total games with attendance: {total_games_with_attendance}")
    
    # Show final database stats
    import sqlite3
    with sqlite3.connect(db_manager.db_path) as conn:
        cursor = conn.cursor()
        
        # Overall stats
        cursor.execute("SELECT COUNT(*) FROM games")
        total_db_games = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM games WHERE total_attendance IS NOT NULL")
        total_db_attendance = cursor.fetchone()[0]
        
        # Stats by season
        cursor.execute("""
            SELECT 
                season,
                COUNT(*) as total_games,
                COUNT(CASE WHEN total_attendance IS NOT NULL THEN 1 END) as games_with_attendance,
                COUNT(DISTINCT division) as divisions,
                COUNT(DISTINCT country) as countries
            FROM games 
            WHERE season IS NOT NULL
            GROUP BY season 
            ORDER BY season
        """)
        season_stats = cursor.fetchall()
        
        print(f"\n📊 Database Summary:")
        print(f"   Total games in database: {total_db_games}")
        print(f"   Games with attendance: {total_db_attendance}")
        print(f"\n📈 By Season:")
        for season, total, with_att, divisions, countries in season_stats:
            print(f"   Season {season}: {total} games, {with_att} with attendance")
            print(f"                  {divisions} divisions, {countries} countries")


if __name__ == "__main__":
    main()
