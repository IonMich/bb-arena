"""Service for updating games with historical pricing data from collection."""

import logging
from datetime import datetime
from typing import List, Optional

from ..collecting.team_arena_collector import GamePricingData, CollectionResult
from ..storage.database import DatabaseManager
from ..storage.models import GameRecord

logger = logging.getLogger(__name__)


class HistoricalPricingService:
    """Service for collecting and storing historical pricing data from team arena pages."""
    
    def __init__(self, db_manager: DatabaseManager):
        """Initialize the service.
        
        Args:
            db_manager: Database manager instance
        """
        self.db_manager = db_manager
    
    def update_games_with_pricing_data(self, team_id: str, collection_result: CollectionResult) -> dict:
        """Update stored games with pricing data from collection.
        
        Args:
            team_id: Team ID that was collected
            collection_result: Result from collecting the team's arena page
            
        Returns:
            Dictionary with update statistics
        """
        if not collection_result.success:
            logger.error(f"Cannot update games for team {team_id}: collection failed - {collection_result.error_message}")
            return {
                "success": False,
                "error": collection_result.error_message,
                "games_updated": 0,
                "games_not_found": 0,
                "price_changes_processed": 0
            }
        
        logger.info(f"Updating games with pricing data for team {team_id}")
        
        games_updated = 0
        games_not_found = 0
        price_changes_processed = 0
        
        # Get all stored games for this team
        stored_games = self.db_manager.get_games_for_team(team_id, limit=1000)
        
        # Check if we have price updates or need to use current pricing
        price_updates = [g for g in collection_result.games_data if g.is_price_change]
        games = [g for g in collection_result.games_data if not g.is_price_change]
        
        if not price_updates:
            # Simple case: no price updates, use current pricing for all games
            logger.info(f"No price updates found for team {team_id}, using current price snapshots")
            
            # Get the latest price snapshot for this team
            price_snapshots = self.db_manager.get_price_history(team_id)
            if price_snapshots:
                # Get the most recent snapshot
                latest_snapshot = max(price_snapshots, key=lambda x: x.created_at or datetime.min)
                logger.debug(f"Using current pricing: B=${latest_snapshot.bleachers_price}, L=${latest_snapshot.lower_tier_price}, "
                           f"C=${latest_snapshot.courtside_price}, LB=${latest_snapshot.luxury_boxes_price}")
                
                # Apply current pricing to all collected games
                for game_data in games:
                    matched_game = self._find_matching_stored_game(game_data, stored_games)
                    
                    if matched_game:
                        # Create a pricing data object with current prices
                        pricing_data = GamePricingData(
                            bleachers_price=latest_snapshot.bleachers_price,
                            lower_tier_price=latest_snapshot.lower_tier_price,
                            courtside_price=latest_snapshot.courtside_price,
                            luxury_boxes_price=latest_snapshot.luxury_boxes_price,
                        )
                        
                        # Update the game with current pricing
                        updated = self._update_game_pricing(matched_game, pricing_data)
                        if updated:
                            games_updated += 1
                            logger.debug(f"Updated pricing for game {matched_game.game_id}")
                    else:
                        games_not_found += 1
                        logger.debug(f"Could not find stored game matching collected data: {game_data.opponent} on {game_data.date}")
            else:
                logger.warning(f"No price snapshots found for team {team_id}, cannot determine pricing")
                games_not_found = len(games)
        else:
            # Complex case: price updates found, use timeline-based pricing logic
            logger.info(f"Found {len(price_updates)} price updates for team {team_id}, using timeline-based pricing logic")
            
            # Process price changes first (for potential future use)
            for price_change in price_updates:
                price_changes_processed += 1
                self._process_price_change(team_id, price_change)
            
            # Categorize games relative to price update period
            oldest_price_update = min(price_updates, key=lambda x: x.date or datetime.max)
            newest_price_update = max(price_updates, key=lambda x: x.date or datetime.min)
            
            games_before_updates = [g for g in games if g.date and oldest_price_update.date and 
                                  g.date < oldest_price_update.date]
            games_after_updates = [g for g in games if g.date and newest_price_update.date and 
                                 g.date > newest_price_update.date]
            games_during_updates = [g for g in games if g not in games_before_updates and g not in games_after_updates]
            
            logger.debug(f"Games categorization: {len(games_before_updates)} before, {len(games_during_updates)} during, {len(games_after_updates)} after price updates")
            
            # Skip games before and after updates (cannot determine correct pricing)
            for game in games_before_updates + games_after_updates:
                games_not_found += 1
                logger.debug(f"Skipping game {game.opponent} on {game.date} (outside price update period)")
            
            # Process games during the price update period
            for game_data in games_during_updates:
                matched_game = self._find_matching_stored_game(game_data, stored_games)
                
                if matched_game:
                    # Find the most recent price update BEFORE this game
                    # Table is in REVERSE chronological order (newer events have smaller row indices)
                    # So for same-day events, LARGER row index means EARLIER in time
                    applicable_price = None
                    for price_update in sorted(price_updates, key=lambda x: (x.date or datetime.min, x.table_row_index or 0)):
                        if price_update.date and game_data.date:
                            # Price update must be before game date, OR same day but LATER in table (happened earlier)
                            if (price_update.date < game_data.date or 
                                (price_update.date.date() == game_data.date.date() and 
                                 (price_update.table_row_index or 0) > (game_data.table_row_index or 0))):
                                applicable_price = price_update
                    
                    if applicable_price:
                        # Create pricing data object with the applicable historical prices
                        pricing_data = GamePricingData(
                            bleachers_price=applicable_price.bleachers_price,
                            lower_tier_price=applicable_price.lower_tier_price,
                            courtside_price=applicable_price.courtside_price,
                            luxury_boxes_price=applicable_price.luxury_boxes_price,
                        )
                        
                        # Update the game with historical pricing
                        updated = self._update_game_pricing(matched_game, pricing_data)
                        if updated:
                            games_updated += 1
                            logger.debug(f"Updated pricing for game {matched_game.game_id} using {applicable_price.date} prices")
                    else:
                        games_not_found += 1
                        logger.debug(f"No applicable price found for game {game_data.opponent} on {game_data.date}")
                else:
                    games_not_found += 1
                    logger.debug(f"Could not find stored game matching collected data: {game_data.opponent} on {game_data.date}")
        
        result = {
            "success": True,
            "games_updated": games_updated,
            "games_not_found": games_not_found,
            "price_changes_processed": price_changes_processed,
            "total_collected_games": len([g for g in collection_result.games_data if not g.is_price_change])
        }
        
        logger.info(f"Pricing update complete for team {team_id}: {result}")
        return result
    
    def _find_matching_stored_game(self, collected_game: GamePricingData, stored_games: List[GameRecord]) -> Optional[GameRecord]:
        """Find a stored game that matches the collected game data.
        
        Args:
            collected_game: Game data from collection
            stored_games: List of stored games for the team
            
        Returns:
            Matching GameRecord or None
        """
        if not collected_game.date:
            return None
        
        # First try exact date match
        for game in stored_games:
            if game.date and game.date.date() == collected_game.date.date():
                return game
        
        # If no exact match, try date within 1 day (in case of timezone issues)
        from datetime import timedelta
        collected_date = collected_game.date.date()
        
        for game in stored_games:
            if game.date:
                game_date = game.date.date()
                if abs((game_date - collected_date).days) <= 1:
                    return game
        
        return None
    
    def _update_game_pricing(self, game: GameRecord, pricing_data: GamePricingData) -> bool:
        """Update a game record with pricing data.
        
        Args:
            game: Game record to update
            pricing_data: Pricing data from collection
            
        Returns:
            True if game was updated, False otherwise
        """
        updated = False
        
        # Update pricing fields if we have new data
        if pricing_data.bleachers_price is not None and game.bleachers_price != pricing_data.bleachers_price:
            game.bleachers_price = pricing_data.bleachers_price
            updated = True
        
        if pricing_data.lower_tier_price is not None and game.lower_tier_price != pricing_data.lower_tier_price:
            game.lower_tier_price = pricing_data.lower_tier_price
            updated = True
        
        if pricing_data.courtside_price is not None and game.courtside_price != pricing_data.courtside_price:
            game.courtside_price = pricing_data.courtside_price
            updated = True
        
        if pricing_data.luxury_boxes_price is not None and game.luxury_boxes_price != pricing_data.luxury_boxes_price:
            game.luxury_boxes_price = pricing_data.luxury_boxes_price
            updated = True
        
        if updated:
            game.updated_at = datetime.now()
            # Save the updated game to database
            self.db_manager.save_game_record(game)
            logger.debug(f"Updated pricing for game {game.game_id}")
        
        return updated
    
    def _process_price_change(self, team_id: str, price_change: GamePricingData):
        """Process a price change entry.
        
        This could be used to apply pricing retroactively to games around the price change date.
        
        Args:
            team_id: Team ID
            price_change: Price change data
        """
        if not price_change.date:
            logger.debug("Skipping price change without date")
            return
        
        logger.debug(f"Processed price change for team {team_id} on {price_change.date}: {price_change.price_change_note}")
        
        # TODO: Could implement logic to apply price changes to games
        # that occurred after this date but before the next price change
    
    def collect_and_update_team_pricing(self, team_id: str, collector_delay: float = 1.0) -> dict:
        """Collect pricing data for a team and update stored games.
        
        Args:
            team_id: Team ID to collect data for
            collector_delay: Delay between requests to be respectful to server
            
        Returns:
            Dictionary with collection and update results
        """
        from ..collecting.team_arena_collector import TeamArenaCollector
        
        logger.info(f"Starting pricing data collection for team {team_id}")
        
        try:
            # Collect the team's arena page
            with TeamArenaCollector(request_delay=collector_delay) as collector:
                collection_result = collector.collect_team_arena_data(team_id)
            
            if not collection_result.success:
                return {
                    "success": False,
                    "error": f"Collection failed: {collection_result.error_message}",
                    "team_id": team_id
                }
            
            # Update games with the collected data
            update_result = self.update_games_with_pricing_data(team_id, collection_result)
            
            # Combine results
            result = {
                "success": True,
                "team_id": team_id,
                "collection_result": {
                    "last_10_games_found": collection_result.last_10_games_found,
                    "price_changes_found": collection_result.price_changes_found
                },
                "update_result": update_result
            }
            
            logger.info(f"Completed pricing collection for team {team_id}: {result}")
            return result
            
        except Exception as e:
            error_msg = f"Error during pricing collection for team {team_id}: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "team_id": team_id
            }
    
    def collect_for_multiple_teams(self, team_ids: List[str], collector_delay: float = 1.5) -> dict:
        """Collect pricing data for multiple teams.
        
        Args:
            team_ids: List of team IDs to collect data for
            collector_delay: Delay between requests (increased for multiple teams)
            
        Returns:
            Dictionary with collection results for all teams
        """
        logger.info(f"Starting pricing collection for {len(team_ids)} teams")
        
        results: dict = {
            "success": True,
            "teams_processed": 0,
            "teams_successful": 0,
            "teams_failed": 0,
            "total_games_updated": 0,
            "team_results": [],
            "failed_teams": []
        }
        
        for team_id in team_ids:
            logger.info(f"Processing team {team_id} ({results['teams_processed'] + 1}/{len(team_ids)})")
            
            team_result = self.collect_and_update_team_pricing(team_id, collector_delay)
            results["team_results"].append(team_result)
            results["teams_processed"] += 1
            
            if team_result["success"]:
                results["teams_successful"] += 1
                if "update_result" in team_result:
                    results["total_games_updated"] += team_result["update_result"].get("games_updated", 0)
            else:
                results["teams_failed"] += 1
                results["failed_teams"].append({
                    "team_id": team_id,
                    "error": team_result.get("error", "Unknown error")
                })
        
        logger.info(f"Completed pricing collection: {results['teams_successful']}/{len(team_ids)} teams successful")
        return results
