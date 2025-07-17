"""BuzzerBeater API integration endpoints."""

import logging
import os
import traceback
from datetime import datetime
from typing import Any, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from bb_arena_optimizer.collecting.pricing_service import HistoricalPricingService

logger = logging.getLogger(__name__)

# Request/Response models
class BBAPIRequest(BaseModel):
    """Request model for BuzzerBeater API calls."""
    league_id: int
    season: int | None = None


class BBAPIResponse(BaseModel):
    """Response model for BuzzerBeater API calls."""
    success: bool
    message: str
    arenas_collected: int
    arenas_skipped: int
    prices_collected: int
    prices_skipped: int
    failed_teams: List[int]


class PriceCollectionResponse(BaseModel):
    """Response model for price collection operations."""
    
    success: bool
    message: str
    prices_collected: int
    prices_skipped: int
    failed_teams: List[int]


class SeasonResponse(BaseModel):
    """Response model for season data."""
    
    id: int | None
    season_number: int | None
    start_date: str | None
    end_date: str | None
    created_at: str | None


class SeasonsListResponse(BaseModel):
    """Response model for list of seasons."""
    
    seasons: list[SeasonResponse]
    current_season: int | None


# Create router
router = APIRouter(prefix="/api/bb", tags=["buzzerbeater-api"])


@router.post("/collect-arenas", response_model=BBAPIResponse)
async def collect_arenas_from_bb(request: BBAPIRequest):
    """Collect arena data from BuzzerBeater API for all teams in the specified league."""
    from ...storage.database import DatabaseManager
    from ...storage.models import ArenaSnapshot, PriceSnapshot
    from ...api.client import BuzzerBeaterAPI
    
    username = os.getenv("BB_USERNAME")
    security_code = os.getenv("BB_SECURITY_CODE")
    
    if not username or not security_code:
        raise HTTPException(
            status_code=500, 
            detail="BuzzerBeater credentials not configured. Please set BB_USERNAME and BB_SECURITY_CODE environment variables."
        )
    
    try:
        db_manager = DatabaseManager("bb_arena_data.db")
        arenas_collected = 0
        arenas_skipped = 0
        prices_collected = 0
        prices_skipped = 0
        failed_teams = []
        
        with BuzzerBeaterAPI(username, security_code) as api:
            # First, get the league standings to get all team IDs
            logger.info(f"Fetching league standings for league {request.league_id}")
            standings_data = api.get_league_standings(request.league_id, request.season)
            
            if not standings_data or not standings_data.get("teams"):
                raise HTTPException(
                    status_code=404,
                    detail=f"No teams found in league {request.league_id} or league does not exist"
                )
            
            team_ids = [int(team["id"]) for team in standings_data["teams"] if team["id"]]
            logger.info(f"Found {len(team_ids)} teams in league {request.league_id}")
            
            # Now collect arena data for each team
            for team_id in team_ids:
                try:
                    logger.info(f"Fetching arena data for team {team_id}")
                    arena_data = api.get_arena_info(team_id)
                    
                    if arena_data:
                        # Create arena snapshot from API data
                        arena_snapshot = ArenaSnapshot.from_api_data(arena_data)
                        
                        # Save to database with deduplication
                        saved_id, was_saved = db_manager.save_arena_snapshot_smart(arena_snapshot)
                        
                        if was_saved:
                            arenas_collected += 1
                            logger.info(f"Successfully saved new arena data for team {team_id}")
                        else:
                            arenas_skipped += 1
                            logger.info(f"Skipped duplicate arena data for team {team_id}")
                        
                        # Also save price snapshot if we have price data
                        if arena_data.get("prices"):
                            try:
                                price_snapshot = PriceSnapshot.from_api_data(arena_data, team_id=str(team_id))
                                
                                # Check if we already have this price data (smart deduplication)
                                existing_prices = db_manager.get_price_history(str(team_id), limit=1)
                                should_save_price = True
                                
                                if existing_prices:
                                    latest_price = existing_prices[0]
                                    # Skip if prices haven't changed
                                    if (latest_price.bleachers_price == price_snapshot.bleachers_price and
                                        latest_price.lower_tier_price == price_snapshot.lower_tier_price and
                                        latest_price.courtside_price == price_snapshot.courtside_price and
                                        latest_price.luxury_boxes_price == price_snapshot.luxury_boxes_price):
                                        should_save_price = False
                                
                                if should_save_price:
                                    price_id = db_manager.save_price_snapshot(price_snapshot)
                                    prices_collected += 1
                                    logger.info(f"Successfully saved new price data for team {team_id} with ID {price_id}")
                                else:
                                    prices_skipped += 1
                                    logger.info(f"Skipped unchanged price data for team {team_id}")
                                    
                            except Exception as price_error:
                                logger.warning(f"Failed to save price snapshot for team {team_id}: {price_error}")
                    else:
                        logger.warning(f"No arena data received for team {team_id}")
                        failed_teams.append(team_id)
                        
                except Exception as e:
                    logger.error(f"Error fetching arena data for team {team_id}: {e}")
                    failed_teams.append(team_id)
        
        league_name = standings_data.get("league_info", {}).get("league_name", f"League {request.league_id}")
        
        # Create comprehensive message
        arena_msg = f"Collected {arenas_collected} new arenas (skipped {arenas_skipped} duplicates)"
        price_msg = f"Collected {prices_collected} new price snapshots (skipped {prices_skipped} duplicates)"
        full_message = f"{arena_msg}, {price_msg} from {league_name}"
        
        return BBAPIResponse(
            success=True,
            message=full_message,
            arenas_collected=arenas_collected,
            arenas_skipped=arenas_skipped,
            prices_collected=prices_collected,
            prices_skipped=prices_skipped,
            failed_teams=failed_teams
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error collecting arenas from BuzzerBeater API: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to collect arena data: {str(e)}")


@router.post("/historical-pricing/collect/{team_id}", response_model=PriceCollectionResponse)
async def collect_team_pricing_data(team_id: str, force_update: bool = False):
    """Collect enhanced pricing data for a specific team using improved period-based logic.
    
    This endpoint uses the enhanced collection method that includes:
    - Official games from the team's arena webpage  
    - Additional home games (friendlies) from the database within pricing periods
    - Timezone-aware safe zone logic for ambiguous friendly game timing
    - Period-based pricing with precise boundaries and snapshots
    
    Args:
        team_id: The team ID to collect pricing for
        force_update: If True, update games even if they already have pricing
    """
    from ...storage.database import DatabaseManager
    from ...collecting.team_arena_collector import TeamArenaCollector
    from ...collecting.improved_pricing_service import ImprovedPricingService
    
    try:
        logger.info(f"Starting improved pricing collection for team {team_id}")
        
        # Initialize components using improved logic
        db_manager = DatabaseManager("bb_arena_data.db")
        collector = TeamArenaCollector()
        improved_service = ImprovedPricingService(db_manager)
        
        # Collect arena data using enhanced collection
        collection_result = collector.collect_team_arena_data_enhanced(team_id, db_manager)
        
        if not collection_result.success:
            raise ValueError(f"Collection failed: {collection_result.error_message}")
        
        # Update games using improved period-based pricing logic
        update_result = improved_service.update_games_with_period_based_pricing(team_id, collection_result, force_update)
        
        # Format result to match expected structure
        result = {
            "success": True,
            "collection_result": {
                "last_10_games_found": collection_result.last_10_games_found,
                "additional_games_found": collection_result.additional_games_found, 
                "price_changes_found": collection_result.price_changes_found
            },
            "update_result": update_result
        }
        
        # Close the collector to clean up resources
        collector.close()
        
        if result["success"]:
            collection_result = result["collection_result"]
            update_result = result["update_result"]
            
            message_parts = []
            
            # Collection summary
            official_games = collection_result.get("last_10_games_found", 0)
            additional_games = collection_result.get("additional_games_found", 0)
            price_changes = collection_result.get("price_changes_found", 0)
            
            if official_games > 0:
                message_parts.append(f"{official_games} official games from arena page")
            if additional_games > 0:
                message_parts.append(f"{additional_games} additional games (friendlies) from database")
            if price_changes > 0:
                message_parts.append(f"{price_changes} price changes found")
            
            # Update summary using improved service results
            total_updated = update_result.get("total_games_updated", 0)
            periods_processed = update_result.get("periods_processed", 0)
            
            if total_updated > 0:
                message_parts.append(f"Updated {total_updated} games using period-based pricing")
            if periods_processed > 0:
                message_parts.append(f"Analyzed {periods_processed} pricing periods")
            
            # Add period breakdown if available
            period_summary = update_result.get("period_summary", [])
            if period_summary:
                updated_periods = [p for p in period_summary if p.get("status") == "updated"]
                if updated_periods:
                    period_details = []
                    for period in updated_periods:
                        games_count = len(period.get("games_updated", []))
                        period_details.append(f"Period {period['period_number']}: {games_count} games")
                    if period_details:
                        message_parts.append(f"Details: {', '.join(period_details)}")
            
            success_message = f"Improved pricing collection for team {team_id}: " + "; ".join(message_parts)
            
            logger.info(success_message)
            
            return PriceCollectionResponse(
                success=True,
                message=success_message,
                prices_collected=total_updated,
                prices_skipped=0,
                failed_teams=[]
            )
        else:
            error_message = f"Collection failed for team {team_id}: {result.get('error', 'Unknown error')}"
            logger.error(error_message)
            return PriceCollectionResponse(
                success=False,
                message=error_message,
                prices_collected=0,
                prices_skipped=0,
                failed_teams=[]
            )
            
    except Exception as e:
        error_message = f"Error during pricing collection for team {team_id}: {str(e)}"
        logger.error(error_message)
        raise HTTPException(status_code=500, detail=error_message)

@router.post("/collect-prices", response_model=PriceCollectionResponse)
async def collect_prices_from_bb(request: BBAPIRequest):
    """Collect price data from BuzzerBeater API for all teams in the specified league."""
    from ...storage.database import DatabaseManager
    from ...storage.models import PriceSnapshot
    from ...api.client import BuzzerBeaterAPI
    
    username = os.getenv("BB_USERNAME")
    security_code = os.getenv("BB_SECURITY_CODE")
    
    if not username or not security_code:
        raise HTTPException(
            status_code=500, 
            detail="BuzzerBeater credentials not configured. Please set BB_USERNAME and BB_SECURITY_CODE environment variables."
        )
    
    try:
        db_manager = DatabaseManager("bb_arena_data.db")
        prices_collected = 0
        prices_skipped = 0
        failed_teams = []
        
        with BuzzerBeaterAPI(username, security_code) as api:
            # First, get the league standings to get all team IDs
            logger.info(f"Fetching league standings for league {request.league_id}")
            standings_data = api.get_league_standings(request.league_id, request.season)
            
            if not standings_data or not standings_data.get("teams"):
                raise HTTPException(
                    status_code=404,
                    detail=f"No teams found in league {request.league_id} or league does not exist"
                )
            
            team_ids = [int(team["id"]) for team in standings_data["teams"] if team["id"]]
            logger.info(f"Found {len(team_ids)} teams in league {request.league_id}")
            
            # Now collect price data for each team
            for team_id in team_ids:
                try:
                    logger.info(f"Fetching arena data for team {team_id} to get current prices")
                    arena_data = api.get_arena_info(team_id)
                    
                    if arena_data and arena_data.get("prices"):
                        # Create price snapshot from API data
                        price_snapshot = PriceSnapshot.from_api_data(arena_data, team_id=str(team_id))
                        
                        # Check if we already have this price data
                        existing_prices = db_manager.get_price_history(str(team_id), limit=1)
                        should_save = True
                        
                        if existing_prices:
                            latest_price = existing_prices[0]
                            # Skip if prices haven't changed
                            if (latest_price.bleachers_price == price_snapshot.bleachers_price and
                                latest_price.lower_tier_price == price_snapshot.lower_tier_price and
                                latest_price.courtside_price == price_snapshot.courtside_price and
                                latest_price.luxury_boxes_price == price_snapshot.luxury_boxes_price):
                                should_save = False
                        
                        if should_save:
                            # Save to database
                            price_id = db_manager.save_price_snapshot(price_snapshot)
                            prices_collected += 1
                            logger.info(f"Successfully saved new price data for team {team_id} with ID {price_id}")
                        else:
                            prices_skipped += 1
                            logger.info(f"Skipped unchanged price data for team {team_id}")
                    else:
                        logger.warning(f"No price data received for team {team_id}")
                        failed_teams.append(team_id)
                        
                except Exception as e:
                    logger.error(f"Error fetching price data for team {team_id}: {e}")
                    failed_teams.append(team_id)
        
        league_name = standings_data.get("league_info", {}).get("league_name", f"League {request.league_id}")
        
        return PriceCollectionResponse(
            success=True,
            message=f"Collected {prices_collected} new price snapshots from {league_name} (skipped {prices_skipped} duplicates)",
            prices_collected=prices_collected,
            prices_skipped=prices_skipped,
            failed_teams=failed_teams
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error collecting prices from BuzzerBeater API: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to collect price data: {str(e)}")


@router.get("/seasons", response_model=SeasonsListResponse)
async def get_seasons():
    """Get all seasons, updating from API if needed."""
    from ...storage.database import DatabaseManager
    from ...storage.models import Season
    from ...api.client import BuzzerBeaterAPI
    
    try:
        db_manager = DatabaseManager("bb_arena_data.db")
        
        # Check if we need to update seasons
        if db_manager.should_update_seasons():
            logger.info("Updating seasons from BBAPI")
            
            # Get API credentials
            username = os.getenv("BB_USERNAME")
            security_code = os.getenv("BB_SECURITY_CODE")
            
            if not username or not security_code:
                logger.warning("BB API credentials not configured, using cached seasons only")
            else:
                try:
                    # Fetch seasons from API
                    with BuzzerBeaterAPI(username, security_code) as api:
                        seasons_data = api.get_seasons()
                        
                        # Convert to Season objects and save
                        seasons = [Season.from_api_data(season) for season in seasons_data["seasons"]]
                        db_manager.save_seasons(seasons)
                        
                        logger.info(f"Updated {len(seasons)} seasons from API")
                        
                except Exception as e:
                    logger.error(f"Failed to update seasons from API: {e}")
        
        # Get seasons from database
        seasons = db_manager.get_all_seasons()
        current_season_obj = db_manager.get_current_season()
        
        # Convert to response format
        seasons_response: list[SeasonResponse] = []
        for season in seasons:
            seasons_response.append(SeasonResponse(
                id=season.id,
                season_number=season.season_number,
                start_date=season.start_date.isoformat() if season.start_date else None,
                end_date=season.end_date.isoformat() if season.end_date else None,
                created_at=season.created_at.isoformat() if season.created_at else None,
            ))
        
        return SeasonsListResponse(
            seasons=seasons_response,
            current_season=current_season_obj.season_number if current_season_obj else None
        )
        
    except Exception as e:
        logger.error(f"Error fetching seasons: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch seasons: {str(e)}")


@router.post("/seasons/update")
async def force_update_seasons():
    """Force update seasons from BBAPI."""
    from ...storage.database import DatabaseManager
    from ...storage.models import Season
    from ...api.client import BuzzerBeaterAPI
    
    try:
        # Get API credentials
        username = os.getenv("BB_USERNAME")
        security_code = os.getenv("BB_SECURITY_CODE")
        
        if not username or not security_code:
            raise HTTPException(status_code=500, detail="BB API credentials not configured")
        
        # Fetch seasons from API
        with BuzzerBeaterAPI(username, security_code) as api:
            seasons_data = api.get_seasons()
            
            # Convert to Season objects and save
            seasons = [Season.from_api_data(season) for season in seasons_data["seasons"]]
            db_manager = DatabaseManager("bb_arena_data.db")
            db_manager.save_seasons(seasons)
            
            logger.info(f"Force updated {len(seasons)} seasons from API")
            
            return {"message": f"Updated {len(seasons)} seasons", "seasons_count": len(seasons)}
        
    except Exception as e:
        logger.error(f"Error force updating seasons: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update seasons: {str(e)}")


@router.get("/standings")
async def get_league_standings(leagueid: int, season: int | None = None):
    """Get league standings which includes team information."""
    from ...api.client import BuzzerBeaterAPI
    
    username = os.getenv("BB_USERNAME")
    security_code = os.getenv("BB_SECURITY_CODE")
    
    if not username or not security_code:
        raise HTTPException(status_code=500, detail="API credentials not configured")
    
    try:
        with BuzzerBeaterAPI(username, security_code) as api:
            standings_data = api.get_league_standings(leagueid, season)
            
            if standings_data is None:
                raise HTTPException(status_code=404, detail="Failed to fetch standings")
            
            return standings_data
            
    except Exception as e:
        logger.error(f"Error fetching standings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch standings: {str(e)}")
