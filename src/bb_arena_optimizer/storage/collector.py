"""Data collection service for gathering and storing BuzzerBeater data."""

import logging
from datetime import datetime, timezone, UTC as datetime_utc
from typing import Any

from ..api.client import BuzzerBeaterAPI
from .database import DatabaseManager
from .models import ArenaSnapshot, GameRecord, PriceSnapshot

logger = logging.getLogger(__name__)


class DataCollectionService:
    """Service for collecting data from API and storing in database."""

    def __init__(self, db_manager: DatabaseManager):
        """Initialize data collection service.

        Args:
            db_manager: Database manager instance
        """
        self.db_manager = db_manager

    def collect_arena_data(
        self, api: BuzzerBeaterAPI, team_id: str | None = None
    ) -> bool:
        """Collect current arena information and store it.

        Args:
            api: Authenticated BuzzerBeater API client
            team_id: Optional team ID (defaults to current user's team)

        Returns:
            True if data was collected successfully, False otherwise
        """
        try:
            logger.info(f"Collecting arena data for team {team_id or 'current'}")

            # Get arena info from API
            team_id_int = int(team_id) if team_id else None
            arena_data = api.get_arena_info(team_id_int)
            if not arena_data:
                logger.error("Failed to get arena data from API")
                return False

            # Store arena snapshot
            arena_snapshot = ArenaSnapshot.from_api_data(arena_data)
            arena_id = self.db_manager.save_arena_snapshot(arena_snapshot)
            logger.info(f"Saved arena snapshot with ID {arena_id}")

            # Store current pricing snapshot
            price_snapshot = PriceSnapshot.from_api_data(
                arena_data, team_id=arena_data.get("team_id")
            )
            price_id = self.db_manager.save_price_snapshot(price_snapshot)
            logger.info(f"Saved price snapshot with ID {price_id}")

            return True

        except Exception as e:
            logger.error(f"Error collecting arena data: {e}")
            return False

    def collect_schedule_data(
        self,
        api: BuzzerBeaterAPI,
        team_id: str | None = None,
        season: int | None = None,
    ) -> bool:
        """Collect schedule data and store games.

        Args:
            api: Authenticated BuzzerBeater API client
            team_id: Optional team ID (defaults to current user's team)
            season: Optional season number (defaults to current season)

        Returns:
            True if data was collected successfully, False otherwise
        """
        try:
            logger.info(
                f"Collecting schedule data for team {team_id or 'current'}, season {season or 'current'}"
            )

            # Get schedule from API
            team_id_int = int(team_id) if team_id else None
            schedule_data = api.get_schedule(team_id_int, season)
            if not schedule_data:
                logger.error("Failed to get schedule data from API")
                return False

            # Use the team ID from the schedule response if we don't have one
            actual_team_id = team_id or schedule_data.get("team_id")

            games_saved = 0
            for game_data in schedule_data.get("games", []):
                try:
                    # Validate game data before processing
                    if not game_data or not isinstance(game_data, dict):
                        logger.warning(f"Skipping invalid game data: {game_data}")
                        continue
                    
                    game_id = game_data.get("id", "unknown")
                    if not game_id:
                        logger.warning("Skipping game with no ID")
                        continue
                    # Create game record - determine home/away team
                    is_home = game_data.get("home", False)
                    if is_home:
                        home_team_id = int(actual_team_id) if actual_team_id else 0
                        away_team_id = 0  # Will need to be determined later or from opponent data
                    else:
                        home_team_id = 0  # Will need to be determined later or from opponent data  
                        away_team_id = int(actual_team_id) if actual_team_id else 0
                    
                    game_record = GameRecord.from_api_data(game_data, home_team_id, away_team_id)

                    # Save to database
                    self.db_manager.save_game_record(game_record)
                    games_saved += 1

                except ValueError as e:
                    logger.warning(
                        f"Invalid game data for game {game_data.get('id', 'unknown') if isinstance(game_data, dict) else 'unknown'}: {e}"
                    )
                    continue
                except Exception as e:
                    logger.warning(
                        f"Failed to save game {game_data.get('id', 'unknown') if isinstance(game_data, dict) else 'unknown'}: {e}"
                    )
                    continue

            logger.info(f"Saved {games_saved} games to database")
            return games_saved > 0

        except Exception as e:
            logger.error(f"Error collecting schedule data: {e}")
            return False

    def collect_economy_data(self, api: BuzzerBeaterAPI) -> dict[str, Any] | None:
        """Collect economy data for revenue analysis.

        Args:
            api: Authenticated BuzzerBeater API client

        Returns:
            Economy data dictionary or None if error
        """
        try:
            logger.info("Collecting economy data")

            economy_data = api.get_economy_info()
            if not economy_data:
                logger.error("Failed to get economy data from API")
                return None

            # Extract match revenues and try to update game records
            for transaction in economy_data.get("transactions", []):
                if transaction.get("type") == "matchRevenue":
                    # Try to extract match ID and update the corresponding game
                    description = transaction.get("description", "")
                    if "Match " in description:
                        try:
                            match_id = description.split("Match ")[1].split(")")[0]
                            revenue = transaction.get("amount", 0.0)

                            # Update the game record with revenue data
                            self._update_game_revenue(match_id, revenue)

                        except (IndexError, ValueError) as e:
                            logger.warning(
                                f"Could not parse match ID from '{description}': {e}"
                            )

            return economy_data

        except Exception as e:
            logger.error(f"Error collecting economy data: {e}")
            return None

    def _update_game_revenue(self, game_id: str, revenue: float) -> None:
        """Update game record with revenue data.

        Args:
            game_id: Game ID to update
            revenue: Revenue amount
        """
        try:
            # This is a simplified update - in a real implementation, you might want
            # to fetch the existing record and update only the revenue field
            import sqlite3

            with sqlite3.connect(self.db_manager.db_path) as conn:
                conn.execute(
                    """
                    UPDATE games 
                    SET ticket_revenue = ?, updated_at = ?
                    WHERE game_id = ?
                """,
                    (revenue, datetime.now(datetime_utc), game_id),
                )
                conn.commit()
                logger.debug(f"Updated revenue for game {game_id}: ${revenue}")

        except Exception as e:
            logger.warning(f"Failed to update revenue for game {game_id}: {e}")

    def collect_full_data_snapshot(
        self, api: BuzzerBeaterAPI, team_id: str | None = None
    ) -> dict[str, bool]:
        """Collect a complete snapshot of current data.

        Args:
            api: Authenticated BuzzerBeater API client
            team_id: Optional team ID (defaults to current user's team)

        Returns:
            Dictionary indicating success/failure of each data collection
        """
        results = {}

        logger.info("Starting full data collection snapshot")

        # Collect arena data
        results["arena"] = self.collect_arena_data(api, team_id)

        # Collect current season schedule
        results["schedule"] = self.collect_schedule_data(api, team_id)

        # Collect economy data
        economy_data = self.collect_economy_data(api)
        results["economy"] = economy_data is not None

        successful_collections = sum(results.values())
        total_collections = len(results)

        logger.info(
            f"Data collection complete: {successful_collections}/{total_collections} successful"
        )

        return results

    def store_game_with_pricing(
        self,
        game_data: dict[str, Any],
        current_prices: dict[str, Any],
        team_id: str | None = None,
    ) -> bool:
        """Store a game record with associated pricing information.

        This is useful when you know the prices that were active during a specific game.

        Args:
            game_data: Game data from API
            current_prices: Pricing data from API
            team_id: Team ID

        Returns:
            True if stored successfully, False otherwise
        """
        try:
            # Create and save game record - determine home/away team  
            is_home = game_data.get("home", False)
            team_id_int = int(team_id) if team_id else 0
            if is_home:
                home_team_id = team_id_int
                away_team_id = 0  # Will need to be determined later
            else:
                home_team_id = 0  # Will need to be determined later
                away_team_id = team_id_int
                
            game_record = GameRecord.from_api_data(game_data, home_team_id, away_team_id)

            # Add pricing information to the game record
            game_record.bleachers_price = current_prices.get("bleachers")
            game_record.lower_tier_price = current_prices.get("lower_tier")
            game_record.courtside_price = current_prices.get("courtside")
            game_record.luxury_boxes_price = current_prices.get("luxury_boxes")

            game_id = self.db_manager.save_game_record(game_record)

            # Also create a price snapshot (arena-level pricing, not game-specific)
            price_snapshot = PriceSnapshot.from_api_data(
                {"prices": current_prices}, team_id=team_id
            )
            price_id = self.db_manager.save_price_snapshot(price_snapshot)

            logger.info(
                f"Saved game {game_record.game_id} with pricing (game_id: {game_id}, price_id: {price_id})"
            )
            return True

        except Exception as e:
            logger.error(f"Error storing game with pricing: {e}")
            return False

    def collect_completed_games_data(self, api: BuzzerBeaterAPI, team_id: str | None = None) -> bool:
        """Collect attendance and revenue data for completed games.

        Args:
            api: Authenticated BuzzerBeater API client
            team_id: Optional team ID to filter games

        Returns:
            True if data was collected successfully, False otherwise
        """
        try:
            logger.info("Collecting attendance data for completed games")

            # Get all games from database that might be completed
            games = self.db_manager.get_games_for_team(team_id) if team_id else []
            
            if not games:
                logger.info("No games found in database")
                return True

            completed_games_updated = 0
            
            for game in games:
                # Skip if we already have attendance data
                if game.total_attendance and game.total_attendance > 0:
                    continue
                
                # Skip if game is clearly in the future (add extra buffer for timezone issues)
                now = datetime.now(timezone.utc)
                if game.date and game.date > now:
                    logger.debug(f"Skipping future game {game.game_id} ({game.date})")
                    continue
                
                try:
                    logger.info(f"Checking boxscore for completed game {game.game_id}")
                    
                    # Get boxscore data for this game
                    boxscore_data = api.get_boxscore(game.game_id)
                    
                    if not boxscore_data:
                        logger.debug(f"No boxscore data available for game {game.game_id}")
                        continue
                    
                    # CRITICAL: Verify we got data for the correct game
                    returned_game_id = boxscore_data.get("game_id")
                    if returned_game_id and str(returned_game_id) != str(game.game_id):
                        logger.warning(
                            f"Game ID mismatch! Requested {game.game_id}, "
                            f"got {returned_game_id}. Skipping to avoid wrong data."
                        )
                        continue
                    
                    # Check if we got attendance data
                    attendance = boxscore_data.get("attendance", {})
                    scores = boxscore_data.get("scores", {})
                    revenue = boxscore_data.get("revenue")
                    
                    if attendance or scores or revenue:
                        # Update the game record with new data
                        if attendance:
                            game.bleachers_attendance = attendance.get("bleachers")
                            game.lower_tier_attendance = attendance.get("lower_tier") 
                            game.courtside_attendance = attendance.get("courtside")
                            game.luxury_boxes_attendance = attendance.get("luxury_boxes")
                            
                            # Calculate total attendance
                            total = sum(v for v in attendance.values() if v is not None)
                            if total > 0:
                                game.total_attendance = total
                        
                        if scores:
                            game.score_home = scores.get("home")
                            game.score_away = scores.get("away")
                        
                        if revenue:
                            game.ticket_revenue = revenue
                        
                        # Save updated game record
                        self.db_manager.save_game_record(game)
                        completed_games_updated += 1
                        logger.info(f"Updated game {game.game_id} with attendance/score data")
                    
                except Exception as e:
                    logger.warning(f"Error getting boxscore for game {game.game_id}: {e}")
                    continue

            logger.info(f"Updated {completed_games_updated} completed games with attendance data")
            return True

        except Exception as e:
            logger.error(f"Error collecting completed games data: {e}")
            return False
