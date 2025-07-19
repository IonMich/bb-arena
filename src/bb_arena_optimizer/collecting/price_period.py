"""
Arena Price Period Tests

Tests for the PricePeriod dataclass and its functionality.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Union, Set

# Import from proper module locations
from bb_arena_optimizer.storage.models import PriceSnapshot, GameRecord
from bb_arena_optimizer.collecting.arena_row import GameEvent, PriceChange
from bb_arena_optimizer.utils.datetime_utils import get_earliest_utc_for_date, get_latest_utc_for_date
from bb_arena_optimizer.storage.database import DatabaseManager


"""
This module creates PricePeriod objects that group GameEvent records based on
PriceChange events. Each period represents a time range with consistent ticket prices.

Key Components:
- PricePeriod: Represents a time period with consistent pricing
- PricePeriodBuilder: Service for creating periods from game event and price data
"""

from datetime import datetime, UTC as datetime_utc
from dataclasses import dataclass, field
from typing import List, Optional, Union, Set
import logging

logger = logging.getLogger(__name__)


def get_game_start_time_UTC(game_id: str, db_manager: DatabaseManager) -> datetime:
    """
    Get the exact timezone-aware datetime for a game by querying the database.
    
    Args:
        game_id: The game ID to query for
        db_manager: Database manager instance to use for the query
        
    Returns:
        datetime: Timezone-aware datetime of the game start time
        
    Raises:
        ValueError: If game_id is not found in the database
    """
    return db_manager.get_game_start_time_UTC(game_id)


def validate_games_in_database(game_events: List[GameEvent], db_manager: DatabaseManager) -> None:
    """
    Validate that all games in the list exist in the database.
    
    Args:
        game_events: List of GameEvent objects to validate
        db_manager: Database manager instance to use for validation
        
    Raises:
        ValueError: If any game ID is not found in the database
    """
    missing_games = []

    for game in game_events:
        # Convert game_id to int if it's a string for validation
        try:
            game_id_int = int(game.game_id) if isinstance(game.game_id, str) else game.game_id
            if not isinstance(game_id_int, int) or game_id_int <= 0:
                missing_games.append(f"Row {game.row_index}: invalid game_id {game.game_id}")
            else:
                # Query database to check if game exists (use original string game_id)
                try:
                    db_manager.get_game_start_time_UTC(game.game_id)
                except ValueError:
                    missing_games.append(f"Row {game.row_index}: game_id {game.game_id} not found in database")
        except (ValueError, TypeError):
            missing_games.append(f"Row {game.row_index}: invalid game_id format {game.game_id}")
    
    if missing_games:
        raise ValueError(
            f"Cannot create price period: some games not found in database:\n" +
            "\n".join(missing_games)
        )


@dataclass
class PricePeriod:
    """Represents a time period with consistent ticket pricing."""
    
    # Required fields (no defaults)
    period_id: int  # Sequential ID (0, 1, 2, ...)
    game_events: List[GameEvent]  # Games from arena table scraping
    db_manager: DatabaseManager  # Database manager for game time queries
    home_team_id: str  # Team ID for which this period applies
    price_snapshot: Optional[PriceSnapshot] = None  # Snapshot of prices at any point safely inside this period
    
    # Time boundaries - use price changes as boundaries for robustness
    start_price_change: Optional[PriceChange] = None  # Price change that starts this period (None for initial)
    end_price_change: Optional[PriceChange] = None    # Price change that ends this period (None for final)
    
    # Timezone context for the date_raw cells of the arena table
    timezone_str: str = "US/Eastern"
    
    # Database game records that fall within this period's time range
    other_home_games: List["GameRecord"] = field(default_factory=list)
    
    def __post_init__(self) -> None:
        """Validate and sort game events by row index."""
        # Validate that all games exist in the database
        validate_games_in_database(self.game_events, self.db_manager)

        # Sort games by row_index for consistent ordering
        self.game_events.sort(key=lambda x: x.row_index)
        
        # Validate that periods have either start_price_change or games (cannot be completely empty)
        if not self.start_price_change and not self.game_events:
            raise ValueError(
                "Invalid period: must have either start_price_change or games. "
                "Empty periods are not allowed."
            )
        
        # Validate that periods with no games don't have both price changes on the same date
        if (not self.game_events and
            self.start_price_change is not None and
            self.end_price_change is not None and
            self.start_price_change.date_raw == self.end_price_change.date_raw):
            raise ValueError(
                f"Invalid period: no games and both price changes on same date "
                f"({self.start_price_change.date_raw}). Such periods are meaningless."
            )
        
        # For periods without start_price_change, we need a price_snapshot for pricing
        # Now that we have home_team_id, we can query for snapshots even without games
        if self.start_price_change is None:            
            # If no price_snapshot provided, query database for one
            if self.price_snapshot is None:
                self._query_price_snapshot()
        
        # Query for other home games within this period's time range
        self.other_home_games = self._query_other_home_games()
        
        # Note: We don't validate pricing information here anymore
        # Periods without pricing will be filtered out by the builder
    
    def _query_price_snapshot(self) -> None:
        """
        Query database for a price snapshot within this period's time boundaries.
        
        This method is called during __post_init__ for periods without start_price_change.
        It uses the home_team_id field to query for snapshots within the safe time range.
        """
        # Get time boundaries for snapshot query
        try:
            start_time = self.safe_start
            end_time = self.safe_end
        except ValueError:
            # If we can't determine safe boundaries, skip snapshot query
            return
        
        # Query database for price snapshots within the time range
        try:
            snapshot = self.db_manager.get_price_snapshot_in_range(
                team_id=self.home_team_id,
                start_time=start_time,
                end_time=end_time
            )
            if snapshot:
                self.price_snapshot = snapshot
        except Exception:
            # If snapshot query fails, continue without snapshot
            # The validation will catch this if it's required
            pass
    
    def has_valid_pricing(self) -> bool:
        """
        Check if this period has valid pricing information.
        
        Returns:
            True if the period has either start_price_change or price_snapshot
        """
        return self.start_price_change is not None or self.price_snapshot is not None
    
    def _query_other_home_games(self) -> List["GameRecord"]:
        """
        Query database for other home games within this period's time range.
        
        Returns:
            List of GameRecord objects that fall within [safe_start, safe_end]
            and are not already in game_events
        """
        try:
            # Get time boundaries
            start_time = self.safe_start
            end_time = self.safe_end
            
            # Query database for games in time range
            candidate_games = self.db_manager.get_team_games_in_time_range(
                team_id=self.home_team_id,
                start_time=start_time,
                end_time=end_time,
                home_games_only=True
            )
            
            # Filter out games that are already in game_events
            existing_game_ids = {game.game_id for game in self.game_events}
            other_games = [game for game in candidate_games 
                          if game.game_id not in existing_game_ids]
            
            return other_games
            
        except Exception:
            # If query fails, return empty list
            return []
    
    @property
    def safe_start(self) -> datetime:
        """
        Get the latest possible UTC time for the period start. Timezone-aware.

        For periods that start with a price change, this returns the latest possible
        time on that date. This conservative approach ensures we don't accidentally
        include games that might not belong to this period.
        For initial periods, games are used to determine the start time.
        For non-initial periods, a combination of start_price_change and games is used.

        The result is bounded by the earliest game in the period to ensure
        safe_start <= safe_end.
        """
        if not self.start_price_change and not self.game_events:
            raise ValueError(
                "Period has no games and no start price change. "
                "This is not allowed as it would create an empty period."
            )
        
        # Calculate earliest game time if games exist
        earliest_game_time = None
        if self.game_events:
            earliest_game = max(self.game_events, key=lambda g: g.row_index)
            earliest_game_time = get_game_start_time_UTC(earliest_game.game_id, self.db_manager)
        
        # Calculate price change time if it exists
        price_change_time = None
        if self.start_price_change is not None:
            price_change_time = get_latest_utc_for_date(self.start_price_change.date_raw, self.timezone_str)
        
        # Return the appropriate time based on what's available
        if earliest_game_time is not None and price_change_time is not None:
            return min(earliest_game_time, price_change_time)
        elif earliest_game_time is not None:
            return earliest_game_time
        elif price_change_time is not None:
            return price_change_time
        else:
            # This should never happen due to the initial validation
            raise ValueError("No valid time source found for period start")

    @property
    def safe_end(self) -> datetime:
        """
        Get the earliest possible UTC time for the period end. Timezone-aware.
        
        For periods that end with a price change, this returns the earliest possible
        time on that date. This conservative approach ensures we don't accidentally
        include games that might not belong to this period.
        For final periods, the request time is used as the end time.
        For non-final periods, a combination of end_price_change and games is used.

        The result is bounded by the latest game in the period to ensure
        safe_start <= safe_end.
        """
        if not self.end_price_change and not self.game_events:
            raise ValueError(
                "Period has no games and no end price change. "
                "This is not allowed as it would create an empty period."
            )
        if self.end_price_change is not None:
            candidate_end = get_earliest_utc_for_date(self.end_price_change.date_raw, self.timezone_str)
        else:
            # last period, so ends with the request time
            return datetime.now(datetime_utc)

        # Bound by latest game in period (if any games exist)
        if self.game_events:
            latest_game = min(self.game_events, key=lambda g: g.row_index)
            latest_game_time = get_game_start_time_UTC(latest_game.game_id, self.db_manager)
            result = max(candidate_end, latest_game_time)
            return result

        return candidate_end
    
    @property
    def official_game_count(self) -> int:
        """Number of games from arena table scraping in this period."""
        return len(self.game_events)
    
    @property
    def total_game_count(self) -> int:
        """Total number of home games in this period (arena table + database games)."""
        return len(self.game_events) + len(self.other_home_games)
    
    def update_game_pricing(self) -> dict[str, bool]:
        """
        Update pricing for all games in this period using the period's pricing information.
        
        Uses pricing from start_price_change if available, otherwise from price_snapshot.
        Updates both game_events and other_home_games in the database.
        
        Returns:
            Dictionary mapping game_id to update success (True/False)
        """
        results: dict[str, bool] = {}
        
        # Determine pricing to use
        pricing_data = self._get_pricing_data()
        if not pricing_data:
            logger.warning(
                f"Period {self.period_id} has no pricing information available. "
                "Cannot update game pricing."
            )
            return results
        
        # Update pricing for game_events (from arena table scraping)
        for game_event in self.game_events:
            try:
                # Get the game record from database
                game_record = self.db_manager.get_game_by_id(game_event.game_id)
                if not game_record:
                    logger.warning(f"Game {game_event.game_id} not found in database")
                    results[game_event.game_id] = False
                    continue
                
                # Update pricing fields
                game_record.bleachers_price = pricing_data.get("bleachers_price")
                game_record.lower_tier_price = pricing_data.get("lower_tier_price")
                game_record.courtside_price = pricing_data.get("courtside_price")
                game_record.luxury_boxes_price = pricing_data.get("luxury_boxes_price")
                
                # Save to database
                success = self.db_manager.update_game_prices(game_record)
                results[game_event.game_id] = success
                
                if success:
                    logger.info(f"Updated pricing for game {game_event.game_id} in period {self.period_id}")
                else:
                    logger.warning(f"Failed to update pricing for game {game_event.game_id}")
                    
            except Exception as e:
                logger.error(f"Error updating pricing for game {game_event.game_id}: {e}")
                results[game_event.game_id] = False
        
        # Update pricing for other_home_games (from database)
        for game_record in self.other_home_games:
            try:
                # Update pricing fields
                game_record.bleachers_price = pricing_data.get("bleachers_price")
                game_record.lower_tier_price = pricing_data.get("lower_tier_price")
                game_record.courtside_price = pricing_data.get("courtside_price")
                game_record.luxury_boxes_price = pricing_data.get("luxury_boxes_price")
                
                # Save to database
                success = self.db_manager.update_game_prices(game_record)
                results[game_record.game_id] = success
                
                if success:
                    logger.info(f"Updated pricing for database game {game_record.game_id} in period {self.period_id}")
                else:
                    logger.warning(f"Failed to update pricing for database game {game_record.game_id}")
                    
            except Exception as e:
                logger.error(f"Error updating pricing for database game {game_record.game_id}: {e}")
                results[game_record.game_id] = False
        
        # Log summary
        total_games = len(results)
        successful_updates = sum(results.values())
        logger.info(
            f"Period {self.period_id} pricing update complete: "
            f"{successful_updates}/{total_games} games updated successfully"
        )
        
        return results
    
    def _get_pricing_data(self) -> dict[str, Optional[int]]:
        """
        Get pricing data for this period from start_price_change or price_snapshot.
        
        Returns:
            Dictionary with pricing data for all seating sections
        """
        if self.start_price_change is not None:
            # Use pricing from price change
            return {
                "bleachers_price": self.start_price_change.bleachers_price,
                "lower_tier_price": self.start_price_change.lower_tier_price,
                "courtside_price": self.start_price_change.courtside_price,
                "luxury_boxes_price": self.start_price_change.luxury_boxes_price,
            }
        elif self.price_snapshot is not None:
            # Use pricing from snapshot
            return {
                "bleachers_price": self.price_snapshot.bleachers_price,
                "lower_tier_price": self.price_snapshot.lower_tier_price,
                "courtside_price": self.price_snapshot.courtside_price,
                "luxury_boxes_price": self.price_snapshot.luxury_boxes_price,
            }
        else:
            # No pricing information available
            return {}

class PricePeriodBuilder:
    """Service for building PricePeriod objects from game event and price data."""
    
    def __init__(self, db_manager: DatabaseManager, home_team_id: str, timezone_str: str = "US/Eastern", request_time: Optional[datetime] = None):
        """
        Initialize the builder.
        
        Args:
            db_manager: Database manager instance to use for queries
            home_team_id: Team ID for which periods are being built
            timezone_str: Timezone for date conversions
            request_time: Time of HTTP request (defaults to now UTC)
        """
        self.db_manager = db_manager
        self.home_team_id = home_team_id
        self.timezone_str = timezone_str
        if request_time is None:
            self.request_time = datetime.now(datetime_utc)
        else:
            # Ensure request_time is timezone-aware
            if request_time.tzinfo is None:
                from datetime import timezone as tz
                self.request_time = request_time.replace(tzinfo=tz.utc)
            else:
                self.request_time = request_time
    
    def build_price_periods(
        self, 
        games: List[GameEvent], 
        price_changes: List[PriceChange]
    ) -> List[PricePeriod]:
        """
        Build price periods from games and price changes.
        
        Args:
            games: List of GameEvent objects
            price_changes: List of PriceChange objects
            
        Returns:
            List of PricePeriod objects in chronological order
        """
        if not games:
            raise ValueError("Cannot build price periods without any games")
        
        # Sort data by row index (chronological order, newest first)
        sorted_games = sorted(games, key=lambda x: x.row_index)
        sorted_price_changes = sorted(price_changes, key=lambda x: x.row_index)

        if not price_changes:
            # Scenario 1: No price changes - single period
            periods = self._build_single_period(sorted_games)
        
        elif len(price_changes) == 1:
            # Scenario 2: One price change - two periods
            periods = self._build_two_periods(
                sorted_games, sorted_price_changes[0]
            )
        
        else:
            # Scenario 3: Multiple price changes - multiple periods
            periods = self._build_multiple_periods(
                sorted_games, sorted_price_changes
            )
        
        # Check if we have any valid periods
        if not periods:
            raise ValueError(
                "Cannot build price periods: no periods have valid pricing information. "
                "This could be due to missing price snapshots for periods without price changes."
            )
        
        return periods
    
    def _build_single_period(
        self, 
        games: List[GameEvent]
    ) -> List[PricePeriod]:
        """Build a single period when there are no price changes."""
        period = PricePeriod(
            period_id=0,
            game_events=games.copy(),
            db_manager=self.db_manager,
            home_team_id=self.home_team_id,
            start_price_change=None,
            end_price_change=None,
            timezone_str=self.timezone_str
        )
        
        # Filter out periods without valid pricing
        if not period.has_valid_pricing():
            logger.warning(
                f"Filtering out period {period.period_id} due to missing pricing information. "
                f"Period has {len(period.game_events)} games but no price_snapshot could be found."
            )
            return []  # Return empty list if no valid pricing found
        
        return [period]
    
    def _build_two_periods(
        self, 
        games: List[GameEvent], 
        price_change: PriceChange,
    ) -> List[PricePeriod]:
        """Build two periods when there is exactly one price change."""
        # Split games by price change row index
        period1_games = [g for g in games if g.row_index > price_change.row_index]
        period2_games = [g for g in games if g.row_index < price_change.row_index]
        
        periods = []
        
        # Period 1: From start to price change (games after price change row)
        if period1_games or True:  # Always create period even if no games
            period1 = PricePeriod(
                period_id=0,
                game_events=period1_games,
                db_manager=self.db_manager,
                home_team_id=self.home_team_id,
                start_price_change=None,
                end_price_change=price_change,
                timezone_str=self.timezone_str
            )
            # Only add period if it has valid pricing
            if period1.has_valid_pricing():
                periods.append(period1)
            else:
                logger.warning(
                    f"Filtering out period 1 due to missing pricing information. "
                    f"Period has {len(period1.game_events)} games but no price_snapshot could be found."
                )
        
        # Period 2: From price change to end (games before price change row)
        period2 = PricePeriod(
            period_id=1,
            game_events=period2_games,
            db_manager=self.db_manager,
            home_team_id=self.home_team_id,
            start_price_change=price_change,
            end_price_change=None,
            timezone_str=self.timezone_str
        )
        # Period 2 should always have valid pricing since it has start_price_change
        periods.append(period2)
        
        # Renumber period IDs to be sequential after any filtered periods
        for idx, period in enumerate(periods):
            period.period_id = idx
        
        return periods
    
    def _build_multiple_periods(
        self, 
        games: List[GameEvent], 
        price_changes: List[PriceChange]
    ) -> List[PricePeriod]:
        """Build multiple periods when there are multiple price changes."""
        periods = []
        
        # Sort price changes by row index (chronological, oldest first)
        sorted_price_changes = sorted(price_changes, key=lambda x: x.row_index, reverse=True)
        
        # Create periods in chronological order
        
        for i, price_change in enumerate(sorted_price_changes):
            
            if i == 0:
                # First period: from start to first price change
                period_games = [g for g in games if g.row_index > price_change.row_index]
                
                period = PricePeriod(
                    period_id=i,
                    game_events=period_games,
                    db_manager=self.db_manager,
                    home_team_id=self.home_team_id,
                    start_price_change=None,
                    end_price_change=price_change,
                    timezone_str=self.timezone_str
                )
                # Only add period if it has valid pricing
                if period.has_valid_pricing():
                    periods.append(period)
                else:
                    logger.warning(
                        f"Filtering out initial period due to missing pricing information. "
                        f"Period has {len(period.game_events)} games but no price_snapshot could be found."
                    )
            
            # Create period starting from this price change
            if i == len(sorted_price_changes) - 1:
                # Last price change period: to final end time
                next_price_change = None
                period_games = [g for g in games if g.row_index < price_change.row_index]
            else:
                # Middle period: to next price change
                next_price_change = sorted_price_changes[i + 1]
                period_games = [g for g in games 
                              if next_price_change.row_index < g.row_index < price_change.row_index]
            
            # Skip creating meaningless periods (no games and same date price changes)
            if (not period_games and 
                next_price_change is not None and 
                price_change.date_raw == next_price_change.date_raw):
                continue  # Skip this period
            
            period = PricePeriod(
                period_id=i + 1,
                game_events=period_games,
                db_manager=self.db_manager,
                home_team_id=self.home_team_id,
                start_price_change=price_change,
                end_price_change=next_price_change,
                timezone_str=self.timezone_str
            )
            # Periods with start_price_change should always have valid pricing
            periods.append(period)
        
        # Renumber period IDs to be sequential after any skipped periods
        for idx, period in enumerate(periods):
            period.period_id = idx
        
        return periods


def build_price_periods_from_data(
    all_objects: List[Union[GameEvent, PriceChange]],
    db_manager: DatabaseManager,
    home_team_id: str,
    timezone_str: str = "US/Eastern",
    request_time: Optional[datetime] = None
) -> List[PricePeriod]:
    """
    Convenience function to build price periods from mixed data.
    
    Args:
        all_objects: Mixed list of GameEvent and PriceChange objects
        db_manager: Database manager instance to use for queries
        home_team_id: Team ID for which periods are being built
        timezone_str: Timezone for date conversions
        request_time: Time of HTTP request (defaults to now)
        
    Returns:
        List of PricePeriod objects in chronological order
    """
    # Separate games and price changes
    games = [obj for obj in all_objects if isinstance(obj, GameEvent)]
    price_changes = [obj for obj in all_objects if isinstance(obj, PriceChange)]
    
    # Build periods
    builder = PricePeriodBuilder(db_manager, home_team_id, timezone_str, request_time)
    try:
        return builder.build_price_periods(games, price_changes)
    except ValueError as e:
        if "no periods have valid pricing information" in str(e):
            # Return empty list rather than raising an error for missing pricing
            logger.warning(
                f"No valid price periods could be built due to missing pricing information. "
                f"Total games: {len(games)}, price changes: {len(price_changes)}"
            )
            return []
        else:
            # Re-raise other validation errors (like missing games)
            raise


