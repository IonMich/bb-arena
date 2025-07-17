#!/usr/bin/env python3
"""Improved pricing service with precise period-based logic and timezone handling."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass
import pytz

from .team_arena_collector import GamePricingData, CollectionResult
from ..storage.database import DatabaseManager
from ..storage.models import GameRecord

logger = logging.getLogger(__name__)


@dataclass
class PricingPeriod:
    """Represents a pricing period with start/end dates and applicable prices."""
    
    start_date: Optional[datetime]
    end_date: Optional[datetime]  
    prices: Optional[Dict[str, int]]  # {bleachers, lower_tier, courtside, luxury_boxes}
    period_type: str  # "before_updates", "between_updates", "after_updates"
    description: str
    has_price_snapshot: bool = False
    # New fields for timezone handling
    arena_timezone: Optional[str] = None
    # Safe zone: games in this range can be safely assigned period pricing
    safe_zone_start: Optional[datetime] = None  # UTC start of safe period
    safe_zone_end: Optional[datetime] = None    # UTC end of safe period


class ImprovedPricingService:
    """Improved pricing service with precise period-based logic and timezone handling."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def detect_arena_timezone(self, collection_result: CollectionResult) -> str:
        """Detect the timezone used by the arena webpage.
        
        For now, we'll assume US Eastern Time since BuzzerBeater is primarily US-based.
        In the future, this could be enhanced to extract timezone from HTTP headers.
        
        Args:
            collection_result: Collection result that might contain timezone hints
            
        Returns:
            Timezone name (e.g., 'US/Eastern')
        """
        # Default assumption - could be enhanced with actual detection
        return 'US/Eastern'
    
    def create_danger_zone_for_date(self, local_date: datetime, timezone_name: str) -> Tuple[datetime, datetime]:
        """Create UTC danger zone boundaries for a local date without time.
        
        Since the arena webpage only shows dates like "05/27/2025" without specific times,
        we create a danger zone that spans the entire day in the local timezone.
        
        Args:
            local_date: Date from arena webpage (naive datetime)
            timezone_name: Timezone name like "US/Eastern"
            
        Returns:
            Tuple of (utc_start, utc_end) for the danger zone
        """
        try:
            tz = pytz.timezone(timezone_name)
            
            # Get just the date part
            date_only = local_date.date()
            
            # Create start and end of day in local timezone
            local_start = tz.localize(datetime.combine(date_only, datetime.min.time()))
            local_end = tz.localize(datetime.combine(date_only, datetime.max.time()))
            
            # Convert to UTC
            utc_start = local_start.astimezone(pytz.UTC).replace(tzinfo=None)
            utc_end = local_end.astimezone(pytz.UTC).replace(tzinfo=None)
            
            return utc_start, utc_end
        except Exception as e:
            logger.warning(f"Failed to create danger zone for {local_date} in {timezone_name}: {e}")
            # Fallback: assume 24-hour window around the date
            return local_date, local_date + timedelta(days=1)
    
    def is_game_in_safe_zone(self, game: GameRecord, period: PricingPeriod) -> bool:
        """Check if a game falls within the safe zone of a pricing period.
        
        A game is in the safe zone if it's clearly after the start ambiguity period
        and clearly before the end ambiguity period.
        
        Args:
            game: Game record with UTC timestamp
            period: Pricing period with safe zone boundaries
            
        Returns:
            True if game is in safe zone and pricing can be safely determined
        """
        if not period.safe_zone_start or not period.safe_zone_end or not game.date:
            return False
        
        game_utc = game.date.replace(tzinfo=None) if game.date.tzinfo else game.date
        
        return (period.safe_zone_start <= game_utc <= period.safe_zone_end)
    
    def analyze_pricing_periods(self, team_id: str, collection_result: CollectionResult) -> List[PricingPeriod]:
        """Analyze the collection result to determine precise pricing periods with timezone awareness.
        
        Args:
            team_id: Team ID
            collection_result: Result from arena collection
            
        Returns:
            List of pricing periods with their applicable prices and timezone info
        """
        periods = []
        
        # Detect the arena webpage timezone
        arena_timezone = self.detect_arena_timezone(collection_result)
        logger.info(f"Using arena timezone: {arena_timezone}")
        
        # Extract price updates and games from collection
        price_updates = [g for g in collection_result.games_data if g.is_price_change]
        official_games = [g for g in collection_result.games_data if not g.is_price_change and not g.is_additional_game]
        
        # Sort by table row index to maintain arena webpage temporal order
        # CRITICAL: Lower row index = appeared earlier in table = happened later chronologically
        # Higher row index = appeared later in table = happened earlier chronologically
        price_updates.sort(key=lambda x: x.table_row_index if x.table_row_index is not None else float('inf'))
        official_games.sort(key=lambda x: x.table_row_index if x.table_row_index is not None else float('inf'))
        
        if not price_updates:
            # No price updates found - but we can check for recent price snapshots in database
            if official_games:
                # For no-updates case, we want the actual earliest and latest games by date
                # not by table position (since table position reflects chronological order backwards)
                earliest_game = min(official_games, key=lambda x: x.date if x.date else datetime.min)
                latest_game = max(official_games, key=lambda x: x.date if x.date else datetime.min)
                
                # Try to get current pricing from database price snapshots
                current_prices = None
                
                # Look for any recent price snapshots (for no-price-updates case, any recent snapshot is valid)
                price_snapshots = self.db_manager.get_price_history(team_id, limit=10)
                
                if price_snapshots:
                    # For teams with no price updates, use the most recent price snapshot
                    # This represents the current pricing that should apply to all games
                    snapshot = price_snapshots[0]  # Most recent snapshot
                    snapshot_date = snapshot.created_at.replace(tzinfo=None) if snapshot.created_at.tzinfo else snapshot.created_at
                    earliest_date = earliest_game.date.replace(tzinfo=None) if earliest_game.date.tzinfo else earliest_game.date
                    
                    current_prices = {
                        'bleachers': snapshot.bleachers_price,
                        'lower_tier': snapshot.lower_tier_price,
                        'courtside': snapshot.courtside_price,
                        'luxury_boxes': snapshot.luxury_boxes_price
                    }
                    logger.info(f"Found suitable price snapshot from {snapshot_date} for no-updates period (earliest game: {earliest_date})")
                else:
                    logger.info(f"No price snapshots found for team {team_id}")
                
                # If no suitable price snapshot found, try to extract from collection result
                if current_prices is None:
                    for item in collection_result.games_data:
                        if (item.bleachers_price is not None or 
                            item.lower_tier_price is not None or 
                            item.courtside_price is not None or 
                            item.luxury_boxes_price is not None):
                            current_prices = {
                                'bleachers': item.bleachers_price,
                                'lower_tier': item.lower_tier_price,
                                'courtside': item.courtside_price,
                                'luxury_boxes': item.luxury_boxes_price
                            }
                            logger.info(f"Found pricing from collection data")
                            break
                
                has_pricing = current_prices is not None
                description_suffix = " (current pricing available)" if has_pricing else " (no current pricing found)"
                
                periods.append(PricingPeriod(
                    start_date=earliest_game.date,
                    end_date=datetime.now(),
                    prices=current_prices,
                    period_type="no_updates",
                    description=f"No price updates found - current pricing applies from {earliest_game.date} to now{description_suffix}",
                    has_price_snapshot=has_pricing,
                    arena_timezone=arena_timezone,
                    safe_zone_start=earliest_game.date if has_pricing else None,  # Safe for entire period if we have pricing
                    safe_zone_end=datetime.now() if has_pricing else None
                ))
            
            return periods
        
        # Get the earliest and latest dates from arena webpage
        earliest_arena_date = None
        latest_arena_date = None
        
        all_arena_dates = []
        for item in collection_result.games_data:
            if item.date:
                # Normalize to naive datetime for comparison
                normalized_date = item.date.replace(tzinfo=None) if item.date.tzinfo else item.date
                all_arena_dates.append(normalized_date)
        
        if all_arena_dates:
            earliest_arena_date = min(all_arena_dates)
            latest_arena_date = max(all_arena_dates)
        
        # Period 1: Before earliest price update (oldest price update)
        earliest_price_update = price_updates[-1]  # Highest table index = earliest chronologically
        if earliest_arena_date and earliest_price_update.date:
            # Normalize price update date
            update_date = earliest_price_update.date.replace(tzinfo=None) if earliest_price_update.date.tzinfo else earliest_price_update.date
            
            # Check for price snapshots that fall within this period
            current_prices = None
            
            # Look for price snapshots that fall within this period (before the price update)
            price_snapshots = self.db_manager.get_price_history(team_id, limit=10)
            
            for snapshot in price_snapshots:
                # Check if this snapshot falls within the "before" period
                snapshot_date = snapshot.created_at.replace(tzinfo=None) if snapshot.created_at.tzinfo else snapshot.created_at
                earliest_date = earliest_arena_date.replace(tzinfo=None) if earliest_arena_date.tzinfo else earliest_arena_date
                update_date_normalized = update_date.replace(tzinfo=None) if update_date.tzinfo else update_date
                
                if earliest_date <= snapshot_date < update_date_normalized:
                    current_prices = {
                        'bleachers': snapshot.bleachers_price,
                        'lower_tier': snapshot.lower_tier_price,
                        'courtside': snapshot.courtside_price,
                        'luxury_boxes': snapshot.luxury_boxes_price
                    }
                    logger.info(f"Found suitable price snapshot from {snapshot_date} for 'before' period ({earliest_date} to {update_date_normalized})")
                    break
            
            has_pricing = current_prices is not None
            description_suffix = " (price snapshot available)" if has_pricing else " (no price snapshot found)"
            
            # For "before" periods, safe zone logic applies if we have pricing
            danger_start, danger_end = self.create_danger_zone_for_date(update_date, arena_timezone)
            safe_zone_start = earliest_arena_date if has_pricing else None
            safe_zone_end = danger_start if has_pricing else None  # Safe until start of danger zone
            
            periods.append(PricingPeriod(
                start_date=earliest_arena_date,
                end_date=update_date,
                prices=current_prices,
                period_type="before_updates",
                description=f"Before earliest price update ({earliest_arena_date.date()} to {update_date.date()}){description_suffix}",
                has_price_snapshot=has_pricing,
                arena_timezone=arena_timezone,
                safe_zone_start=safe_zone_start,
                safe_zone_end=safe_zone_end
            ))
        
        # Periods between price updates (process in reverse order since array is sorted latest-first)
        for i in range(len(price_updates) - 1, 0, -1):
            current_update = price_updates[i]      # Earlier price update (higher table index)
            next_update = price_updates[i - 1]     # Later price update (lower table index)
            
            if current_update.date and next_update.date:
                # Normalize dates
                current_date = current_update.date.replace(tzinfo=None) if current_update.date.tzinfo else current_update.date
                next_date = next_update.date.replace(tzinfo=None) if next_update.date.tzinfo else next_update.date
                
                prices = {
                    'bleachers': current_update.bleachers_price,
                    'lower_tier': current_update.lower_tier_price,
                    'courtside': current_update.courtside_price,
                    'luxury_boxes': current_update.luxury_boxes_price
                }
                
                # Create danger zones for both boundary dates
                start_danger_start, start_danger_end = self.create_danger_zone_for_date(current_date, arena_timezone)
                end_danger_start, end_danger_end = self.create_danger_zone_for_date(next_date, arena_timezone)
                
                # Safe zone is between the end of start danger zone and start of end danger zone
                safe_start = start_danger_end
                safe_end = end_danger_start
                
                # Only create safe zone if there's actually a gap
                if safe_start < safe_end:
                    safe_zone_start = safe_start
                    safe_zone_end = safe_end
                else:
                    # No safe zone - entire period is ambiguous
                    safe_zone_start = None
                    safe_zone_end = None
                
                periods.append(PricingPeriod(
                    start_date=current_date,
                    end_date=next_date,
                    prices=prices,
                    period_type="between_updates",
                    description=f"Between price updates {len(price_updates) - i} and {len(price_updates) - i + 1} ({current_date.date()} to {next_date.date()})",
                    has_price_snapshot=True,
                    arena_timezone=arena_timezone,
                    safe_zone_start=safe_zone_start,
                    safe_zone_end=safe_zone_end
                ))
        
        # Period after latest price update (most recent price update)
        latest_price_update = price_updates[0]  # Lowest table index = latest chronologically
        if latest_price_update.date:
            # Normalize date
            latest_date = latest_price_update.date.replace(tzinfo=None) if latest_price_update.date.tzinfo else latest_price_update.date
            
            prices = {
                'bleachers': latest_price_update.bleachers_price,
                'lower_tier': latest_price_update.lower_tier_price,
                'courtside': latest_price_update.courtside_price,
                'luxury_boxes': latest_price_update.luxury_boxes_price
            }
            
            # For "after" periods, safe zone starts after the start danger zone
            start_danger_start, start_danger_end = self.create_danger_zone_for_date(latest_date, arena_timezone)
            
            periods.append(PricingPeriod(
                start_date=latest_date,
                end_date=datetime.now(),
                prices=prices,
                period_type="after_updates",
                description=f"After latest price update ({latest_date.date()} to now)",
                has_price_snapshot=True,
                arena_timezone=arena_timezone,
                safe_zone_start=start_danger_end,  # Safe after the start danger zone
                safe_zone_end=datetime.now()      # Safe until now
            ))
        
        return periods
    
    def get_precise_game_timing(self, game_id: str) -> Optional[datetime]:
        """Get precise game timing from database if available.
        
        For official games, we can extract the exact start time (usually 8pm ET).
        This helps create more precise period boundaries.
        """
        game = self.db_manager.get_game_by_id(game_id)
        if game and game.date:
            return game.date
        return None
    
    def find_games_in_period(self, team_id: str, period: PricingPeriod, collection_result: CollectionResult, include_friendlies: bool = True) -> List[GameRecord]:
        """Find all games (official + friendlies) that fall within a pricing period.
        
        Args:
            team_id: Team ID
            period: Pricing period to search within
            include_friendlies: Whether to include friendly/cup games from database
            
        Returns:
            List of games that fall within the period
        """
        games_in_period = []
        
        if not period.start_date or not period.end_date:
            return games_in_period
        
        # Get all home games for the team from database
        stored_games = self.db_manager.get_games_for_team(team_id, limit=1000)
        home_games = [g for g in stored_games if g.home_team_id == int(team_id)]
        
        for game in home_games:
            if game.date:
                game_date = game.date.replace(tzinfo=None) if game.date.tzinfo else game.date
                period_start = period.start_date.replace(tzinfo=None) if period.start_date.tzinfo else period.start_date
                period_end = period.end_date.replace(tzinfo=None) if period.end_date.tzinfo else period.end_date
                
                # Convert game timestamp to local date for comparison with arena page dates
                # This handles timezone conversion issues where games at 8pm ET on 6/24 
                # are stored as 6/25 00:00 UTC but should be categorized as 6/24 games
                if period.arena_timezone:
                    try:
                        tz = pytz.timezone(period.arena_timezone)
                        # Convert UTC game time to local timezone
                        game_utc = pytz.UTC.localize(game_date) if game_date.tzinfo is None else game_date
                        game_local = game_utc.astimezone(tz)
                        game_local_date = game_local.date()
                        
                        # Compare using local dates to match arena page categorization
                        period_start_date = period_start.date()
                        period_end_date = period_end.date()
                        
                        # CRITICAL FIX: Use table position to determine temporal order, not dates
                        # Games with HIGHER row index than a price update happened BEFORE the price update
                        # Games with LOWER row index than a price update happened AFTER the price update
                        
                        # Find corresponding arena game data for this database game to get table position
                        game_table_position = None
                        for arena_game in collection_result.games_data:
                            # Try to match by game ID if available, or by date and opponent
                            if (arena_game.game_id and str(game.game_id) == arena_game.game_id) or \
                               (arena_game.date and arena_game.opponent and 
                                game_local_date == arena_game.date.date() if arena_game.date else False):
                                game_table_position = arena_game.table_row_index
                                break
                        
                        # If we found table position, use it for period assignment
                        if game_table_position is not None:
                            if period.period_type == "before_updates":
                                # For "before" periods, include games with HIGHER table index than the price update
                                # We need to compare against the EARLIEST price update on the end date (highest table index)
                                price_update_position = None
                                for price_update in [p for p in collection_result.games_data if p.is_price_change]:
                                    if price_update.date and period.end_date and \
                                       price_update.date.date() == period.end_date.date():
                                        # For "before" periods, we want the earliest price update (highest table index)
                                        if price_update_position is None or price_update.table_row_index > price_update_position:
                                            price_update_position = price_update.table_row_index
                                
                                if price_update_position is not None and game_table_position > price_update_position:
                                    games_in_period.append(game)
                                    continue
                            elif period.period_type == "after_updates":
                                # For "after" periods, include games with LOWER table index than the price update
                                # We need to compare against the LATEST price update on the start date (lowest table index)
                                price_update_position = None
                                for price_update in [p for p in collection_result.games_data if p.is_price_change]:
                                    if price_update.date and period.start_date and \
                                       price_update.date.date() == period.start_date.date():
                                        # For "after" periods, we want the latest price update (lowest table index)
                                        if price_update_position is None or price_update.table_row_index < price_update_position:
                                            price_update_position = price_update.table_row_index
                                
                                if price_update_position is not None and game_table_position < price_update_position:
                                    games_in_period.append(game)
                                continue
                            elif period.period_type == "between_updates":
                                # For "between" periods, games are assigned based on table position relative to BOTH boundaries
                                # The game should be between the two price updates chronologically
                                # Since table position reflects reverse chronological order:
                                # - Game should have LOWER table index than start period price update (happened after start)
                                # - Game should have HIGHER table index than end period price update (happened before end)
                                
                                # Find price updates at period boundaries
                                start_price_position = None
                                end_price_position = None
                                
                                for price_update in [p for p in collection_result.games_data if p.is_price_change]:
                                    if price_update.date and period.start_date and \
                                       price_update.date.date() == period.start_date.date():
                                        # For start boundary, want the latest update (lowest table index)
                                        if start_price_position is None or price_update.table_row_index < start_price_position:
                                            start_price_position = price_update.table_row_index
                                    
                                    if price_update.date and period.end_date and \
                                       price_update.date.date() == period.end_date.date():
                                        # For end boundary, want the earliest update (highest table index)
                                        if end_price_position is None or price_update.table_row_index > end_price_position:
                                            end_price_position = price_update.table_row_index
                                
                                # Check if game falls between the price updates chronologically
                                game_in_between = True
                                if start_price_position is not None:
                                    # Game should have happened AFTER start price update (lower table index)
                                    game_in_between = game_in_between and (game_table_position < start_price_position)
                                if end_price_position is not None:
                                    # Game should have happened BEFORE end price update (higher table index)
                                    game_in_between = game_in_between and (game_table_position > end_price_position)
                                
                                if game_in_between:
                                    games_in_period.append(game)
                                continue
                            
                            # If we have table position data, we've handled the assignment above
                            # Don't fall through to date-based logic
                            continue
                        
                        # Fallback to date-based comparison for games not found in arena data
                        # BUT: only assign games to periods where we can be certain based on date alone
                        # Skip games that fall on the same date as period boundaries (ambiguous)
                        
                        if period.period_type == "before_updates":
                            # For "before" periods, only include games that are clearly before the price update date
                            # Do NOT include games on the same day as the price update (ambiguous without table position)
                            if period_start_date <= game_local_date < period_end_date:
                                games_in_period.append(game)
                        elif period.period_type == "after_updates":
                            # For "after" periods, only include games that are clearly after the price update date
                            # Do NOT include games on the same day as the price update (ambiguous without table position)
                            if period_start_date < game_local_date < period_end_date:
                                games_in_period.append(game)
                        else:
                            # For "between" periods, use standard date range (no ambiguity)
                            if period_start_date <= game_local_date < period_end_date:
                                games_in_period.append(game)
                        continue
                    except Exception as e:
                        logger.warning(f"Failed to convert game {game.game_id} to local timezone: {e}")
                        # Fall back to UTC comparison
                
                # Fallback to original UTC timestamp comparison
                if period_start <= game_date < period_end:
                    games_in_period.append(game)
        
        return games_in_period
    
    def is_friendly_game(self, game: GameRecord, collection_result: CollectionResult) -> bool:
        """Determine if a game is a friendly (not in arena webpage) or official game.
        
        Args:
            game: Game record from database
            collection_result: Collection result from arena webpage
            
        Returns:
            True if game is a friendly (not found in arena webpage), False if official
        """
        # Check if this game was marked as additional during collection
        for game_data in collection_result.games_data:
            if (game_data.is_additional_game and 
                game_data.game_id and 
                game_data.game_id == str(game.game_id)):
                return True
        
        # If not marked as additional, it's likely an official game
        # (or we couldn't determine its status)
        return False
    
    def update_games_with_period_based_pricing(self, team_id: str, collection_result: CollectionResult, force_update: bool = False) -> dict:
        """Update games using the improved period-based pricing logic.
        
        This implements the precise logic you described:
        1. Analyze pricing periods from arena webpage
        2. For each period, find applicable games
        3. Update games only if we have price snapshots for that period
        4. Apply safe zone logic only to friendly games
        
        Args:
            team_id: The team ID to update
            collection_result: Result from collecting arena data
            force_update: If True, update games even if they already have pricing
        """
        logger.info(f"Starting period-based pricing update for team {team_id}")
        
        # Analyze pricing periods
        periods = self.analyze_pricing_periods(team_id, collection_result)
        
        total_updated = 0
        period_summary = []
        
        for i, period in enumerate(periods):
            logger.info(f"Processing period {i+1}: {period.description}")
            
            # Find games in this period
            games_in_period = self.find_games_in_period(team_id, period, collection_result)
            
            period_info = {
                'period_number': i + 1,
                'description': period.description,
                'games_found': [game.game_id for game in games_in_period],
                'games_updated': [],
                'has_pricing': period.has_price_snapshot,
                'pricing_applied': None
            }
            
            if not games_in_period:
                logger.info(f"  No games found in period {i+1}")
                period_info['status'] = 'no_games'
            elif not period.has_price_snapshot:
                logger.info(f"  Found {len(games_in_period)} games but no price snapshot available for period {i+1}")
                period_info['status'] = 'no_pricing'
                for game in games_in_period:
                    logger.debug(f"    Skipping game {game.game_id} (no price snapshot)")
            else:
                # We have both games and pricing - update them!
                logger.info(f"  Found {len(games_in_period)} games with pricing available for period {i+1}")
                
                games_updated_in_period = 0
                games_updated_list = []
                games_skipped_with_pricing = 0
                games_skipped_danger_zone = 0
                
                for game in games_in_period:
                    # Check if game already has pricing (skip only if force_update is False)
                    has_existing_pricing = any([
                        game.bleachers_price, game.lower_tier_price,
                        game.courtside_price, game.luxury_boxes_price
                    ])
                    
                    if has_existing_pricing and not force_update:
                        logger.debug(f"    Game {game.game_id} already has pricing - skipping")
                        games_skipped_with_pricing += 1
                        continue
                    
                    # Determine if this is a friendly game
                    is_friendly = self.is_friendly_game(game, collection_result)
                    
                    # Check if game is in safe zone (ONLY for friendly games)
                    if is_friendly and not self.is_game_in_safe_zone(game, period):
                        game_utc = game.date.replace(tzinfo=None) if game.date.tzinfo else game.date
                        logger.debug(f"    Friendly game {game.game_id} is not in safe zone - skipping")
                        logger.debug(f"      Game time (UTC): {game_utc}")
                        if period.safe_zone_start and period.safe_zone_end:
                            logger.debug(f"      Safe zone: {period.safe_zone_start} to {period.safe_zone_end}")
                        else:
                            logger.debug(f"      No safe zone defined for this period")
                        games_skipped_danger_zone += 1
                        continue
                    
                    # Log what type of game we're updating
                    game_type = "friendly" if is_friendly else "official"
                    logger.debug(f"    Updating {game_type} game {game.game_id}")
                    
                    # Update with period pricing
                    game.bleachers_price = period.prices['bleachers']
                    game.lower_tier_price = period.prices['lower_tier']
                    game.courtside_price = period.prices['courtside']
                    game.luxury_boxes_price = period.prices['luxury_boxes']
                    game.updated_at = datetime.now()
                    
                    # Save the updated game to database
                    try:
                        self.db_manager.save_game_record(game)
                        games_updated_in_period += 1
                        games_updated_list.append(game.game_id)
                        total_updated += 1
                        logger.info(f"    Updated game {game.game_id} with pricing: "
                                   f"${period.prices['bleachers']}/${period.prices['lower_tier']}/"
                                   f"${period.prices['courtside']}/${period.prices['luxury_boxes']}")
                    except Exception as e:
                        logger.warning(f"    Failed to update game {game.game_id}: {e}")
                
                period_info['games_updated'] = games_updated_list
                
                # Set appropriate status based on what happened
                if games_updated_in_period > 0:
                    period_info['status'] = 'updated'
                elif games_skipped_with_pricing > 0 and games_skipped_danger_zone > 0:
                    period_info['status'] = 'already_priced_and_outside_safe_zone'
                elif games_skipped_with_pricing > 0:
                    period_info['status'] = 'already_priced'
                elif games_skipped_danger_zone > 0:
                    period_info['status'] = 'outside_safe_zone'
                else:
                    period_info['status'] = 'no_updates_needed'
                    
                period_info['pricing_applied'] = period.prices
                period_info['games_skipped_existing_pricing'] = games_skipped_with_pricing
                period_info['games_skipped_danger_zone'] = games_skipped_danger_zone
            
            period_summary.append(period_info)
        
        logger.info(f"Period-based pricing update complete for team {team_id}: {total_updated} games updated")
        
        return {
            'success': True,
            'total_games_updated': total_updated,
            'periods_processed': len(periods),
            'period_summary': period_summary,
            'pricing_periods': [
                {
                    'start': p.start_date.isoformat() if p.start_date else None,
                    'end': p.end_date.isoformat() if p.end_date else None,
                    'type': p.period_type,
                    'description': p.description,
                    'has_pricing': p.has_price_snapshot
                }
                for p in periods
            ]
        }
