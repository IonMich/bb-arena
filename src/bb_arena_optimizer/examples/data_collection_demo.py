"""Example script for collecting and storing BuzzerBeater data."""

import os

from dotenv import load_dotenv

from bb_arena_optimizer.api.client import BuzzerBeaterAPI
from bb_arena_optimizer.storage import DatabaseManager, DataCollectionService
from bb_arena_optimizer.utils.logging_config import setup_logging


def main() -> None:
    """Demonstrate data collection and storage."""
    logger = setup_logging()
    load_dotenv()

    username = os.getenv("BB_USERNAME")
    security_code = os.getenv("BB_SECURITY_CODE")

    if not username or not security_code:
        print("Error: BB_USERNAME and BB_SECURITY_CODE must be set in .env file")
        return

    print("BuzzerBeater Data Collection Demo")
    print("=" * 40)

    # Initialize database
    db_manager = DatabaseManager("bb_arena_data.db")
    collector = DataCollectionService(db_manager)

    try:
        with BuzzerBeaterAPI(username, security_code) as api:
            print("\n📊 Collecting current data snapshot...")

            # Collect all current data
            results = collector.collect_full_data_snapshot(api)

            print("\nCollection Results:")
            for data_type, success in results.items():
                status = "✅ Success" if success else "❌ Failed"
                print(f"  {data_type.capitalize()}: {status}")

            # Get team info to show what we're collecting for
            print("\n🏀 Team Information:")
            team_info = api.get_team_info()
            if team_info:
                print(f"  Team: {team_info.get('name', 'Unknown')}")
                print(f"  Owner: {team_info.get('owner', 'Unknown')}")
                print(f"  League: {team_info.get('league', 'Unknown')}")

            # Show database statistics
            print("\n📈 Database Statistics:")
            stats = db_manager.get_database_stats()
            print(f"  Arena Snapshots: {stats['arena_snapshots']}")
            print(f"  Price Snapshots: {stats['price_snapshots']}")
            print(f"  Total Games: {stats['total_games']}")
            print(f"  Unique Teams: {stats['unique_teams']}")
            if stats["earliest_game"] and stats["latest_game"]:
                print(
                    f"  Game Date Range: {stats['earliest_game']} to {stats['latest_game']}"
                )

            # Show recent games if available
            if team_info and team_info.get("id"):
                team_id = str(team_info["id"])
                recent_games = db_manager.get_games_for_team(team_id, limit=5)

                print(f"\n🎮 Recent Games for Team {team_id}:")
                if recent_games:
                    for game in recent_games:
                        home_away = "vs" if game.is_home else "@"
                        score = ""
                        if game.score_home is not None and game.score_away is not None:
                            if game.is_home:
                                score = f" ({game.score_home}-{game.score_away})"
                            else:
                                score = f" ({game.score_away}-{game.score_home})"

                        revenue_info = ""
                        if game.ticket_revenue:
                            revenue_info = f" | Revenue: ${game.ticket_revenue:,.2f}"

                        print(
                            f"  {game.date} {home_away} {game.opponent}{score}{revenue_info}"
                        )
                else:
                    print("  No games found in database")

                # Show pricing history
                price_history = db_manager.get_price_history(team_id, limit=3)
                print("\n💰 Recent Pricing History:")
                if price_history:
                    for price in price_history:
                        print(
                            f"  {price.created_at}: "
                            f"Bleachers: ${price.bleachers_price or 'N/A'}, "
                            f"Lower: ${price.lower_tier_price or 'N/A'}, "
                            f"Courtside: ${price.courtside_price or 'N/A'}, "
                            f"Luxury: ${price.luxury_boxes_price or 'N/A'}"
                        )
                else:
                    print("  No pricing history found")

                # Collect completed games attendance data
                print("\n🏟️ Collecting completed games data...")
                print("Raw API output for verification:")
                print("=" * 50)
                
                # Get first few games to show raw output
                recent_games = db_manager.get_games_for_team(team_id, limit=3)
                
                for i, game in enumerate(recent_games):
                    print(f"\nGame {i+1}: {game.game_id}")
                    print(f"Date: {game.date}")
                    print(f"Opponent: {game.opponent}")
                    print(f"Home: {game.is_home}")
                    
                    try:
                        # Get raw boxscore data
                        boxscore = api.get_boxscore(game.game_id)
                        
                        if boxscore:
                            print(f"RAW BOXSCORE DATA:")
                            print(f"  game_id in response: {boxscore.get('game_id')}")
                            print(f"  attendance: {boxscore.get('attendance')}")
                            print(f"  scores: {boxscore.get('scores')}")
                            print(f"  revenue: {boxscore.get('revenue')}")
                            print(f"  teams: {boxscore.get('teams')}")
                            
                            # Check if this looks like placeholder data
                            if boxscore.get('attendance'):
                                att = boxscore['attendance']
                                total = sum(att.values())
                                
                                if total == 2720:
                                    print(f"⚠️  PLACEHOLDER DATA DETECTED (2,720 total)")
                                    print(f"    This is simulated/template data, not real attendance")
                                elif total > 5000:
                                    print(f"✅ LOOKS LIKE REAL DATA ({total:,} total)")
                                else:
                                    print(f"🤔 UNUSUAL ATTENDANCE ({total:,} total)")
                        else:
                            print(f"No boxscore data returned")
                            
                    except Exception as e:
                        print(f"Error getting boxscore: {e}")
                
                print("\n" + "="*50)
                
                # Also show schedule data for season 68
                print(f"\nTesting Season 68 schedule data:")
                try:
                    schedule68 = api.get_schedule(season=68)
                    if schedule68 and schedule68.get('games'):
                        games68 = schedule68['games']
                        print(f"✅ Found {len(games68)} games in Season 68")
                        
                        # Show first few games
                        for i, game in enumerate(games68[:3]):
                            print(f"  {i+1}. {game.get('date')} vs {game.get('opponent')} (ID: {game.get('id')})")
                            
                            # Test boxscore for season 68 game
                            try:
                                boxscore68 = api.get_boxscore(game.get('id'))
                                if boxscore68 and boxscore68.get('attendance'):
                                    att68 = boxscore68['attendance']
                                    total68 = sum(att68.values())
                                    print(f"      Season 68 attendance: {total68:,}")
                                    
                                    if total68 != 2720:
                                        print(f"      🎉 REAL HISTORICAL DATA FOUND!")
                                    else:
                                        print(f"      🔄 Also placeholder data")
                                else:
                                    print(f"      No attendance data")
                            except Exception as e:
                                print(f"      Error: {e}")
                    else:
                        print(f"❌ No Season 68 data found")
                except Exception as e:
                    print(f"❌ Season 68 error: {e}")
                
                completed_success = collector.collect_completed_games_data(api, team_id)
                if completed_success:
                    print("  ✅ Completed games data collection successful")
                else:
                    print("  ❌ Completed games data collection failed")

    except Exception as e:
        logger.error(f"Error during data collection: {e}")
        print(f"❌ Error: {e}")

    print("\n📁 Data stored in: bb_arena_data.db")
    print("You can now use this data for analysis without making API calls!")


if __name__ == "__main__":
    main()
