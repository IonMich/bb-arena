"""BuzzerBeater API integration endpoints."""

import logging
import os
import traceback
from datetime import datetime
from typing import Any, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

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
