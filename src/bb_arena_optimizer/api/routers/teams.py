"""Team information API endpoints."""

import logging
import os

from fastapi import APIRouter, HTTPException
from dotenv import load_dotenv

from ...storage.database import DatabaseManager
from ...api.client import BuzzerBeaterAPI
from . import buzzerbeater

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/bb", tags=["teams"])


@router.get("/team-info")
async def get_user_team_info():
    """Get the current user's team information."""
    username = os.getenv("BB_USERNAME")
    security_code = os.getenv("BB_SECURITY_CODE")
    
    if not username or not security_code:
        raise HTTPException(status_code=500, detail="API credentials not configured")
    
    try:
        with BuzzerBeaterAPI(username, security_code) as api:
            team_data = api.get_team_info()
            
            if team_data is None:
                raise HTTPException(status_code=404, detail="Failed to fetch team information")
            
            return team_data
            
    except Exception as e:
        logger.error(f"Error fetching team info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch team info: {str(e)}")


@router.get("/team-info/cached")
async def get_cached_team_info():
    """Get cached team information from database."""
    username = os.getenv("BB_USERNAME")
    
    if not username:
        raise HTTPException(status_code=500, detail="BB_USERNAME not configured")
    
    try:
        db_manager = DatabaseManager("bb_arena_data.db")
        team_info = db_manager.get_team_info_by_username(username)
        
        if team_info is None:
            raise HTTPException(status_code=404, detail="No cached team info found. Please sync first.")
        
        # Convert to dict format matching the API response
        return {
            "id": team_info.bb_team_id,
            "name": team_info.team_name,
            "short_name": team_info.short_name,
            "owner": team_info.owner,
            "league_id": team_info.league_id,
            "league": team_info.league_name,
            "league_level": team_info.league_level,
            "country_id": team_info.country_id,
            "country": team_info.country_name,
            "rival_id": team_info.rival_id,
            "rival": team_info.rival_name,
            "create_date": team_info.create_date,
            "last_synced": team_info.last_synced.isoformat() if team_info.last_synced else None,
            "from_cache": True
        }
            
    except Exception as e:
        logger.error(f"Error fetching cached team info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch cached team info: {str(e)}")


@router.post("/team-info/sync")
async def sync_team_info():
    """Sync team information from BuzzerBeater API and cache it."""
    username = os.getenv("BB_USERNAME")
    security_code = os.getenv("BB_SECURITY_CODE")
    
    if not username or not security_code:
        raise HTTPException(status_code=500, detail="API credentials not configured")
    
    try:
        with BuzzerBeaterAPI(username, security_code) as api:
            team_data = api.get_team_info()
            
            if team_data is None:
                raise HTTPException(status_code=404, detail="Failed to fetch team information from BB API")
            
            # Save to database
            from ...storage.models import TeamInfo
            db_manager = DatabaseManager("bb_arena_data.db")
            team_info = TeamInfo.from_api_data(team_data, username)
            db_manager.save_team_info(team_info)
            
            # Return the same format as the direct API call but with cache info
            response_data = team_data.copy()
            response_data["last_synced"] = team_info.last_synced.isoformat() if team_info.last_synced else None
            response_data["from_cache"] = False
            
            return response_data
            
    except Exception as e:
        logger.error(f"Error syncing team info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to sync team info: {str(e)}")


@router.get("/team-info/smart")
async def get_smart_team_info():
    """Get team info intelligently - from cache if recent, otherwise sync from API."""
    username = os.getenv("BB_USERNAME")
    
    if not username:
        raise HTTPException(status_code=500, detail="BB_USERNAME not configured")
    
    try:
        db_manager = DatabaseManager("bb_arena_data.db")
        # Check if we should sync (no cache or cache is old)
        should_sync = db_manager.should_sync_team_info(username, hours_threshold=24)
        
        if should_sync:
            logger.info(f"Team info cache is stale for {username}, syncing from API")
            # Sync from API (this will also cache the result)
            return await sync_team_info()
        else:
            logger.info(f"Using cached team info for {username}")
            # Use cached data
            return await get_cached_team_info()
            
    except HTTPException:
        # Re-raise HTTP exceptions (like 404 from cached data)
        raise
    except Exception as e:
        logger.error(f"Error getting smart team info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get team info: {str(e)}")


@router.post("/team-info/sync/{team_id}")
async def sync_specific_team_info(team_id: str):
    """Sync team information for a specific team from BuzzerBeater API and cache it."""
    username = os.getenv("BB_USERNAME")
    security_code = os.getenv("BB_SECURITY_CODE")
    
    if not username or not security_code:
        raise HTTPException(status_code=500, detail="API credentials not configured")
    
    try:
        with BuzzerBeaterAPI(username, security_code) as api:
            team_data = api.get_team_info(int(team_id))
            
            if team_data is None:
                raise HTTPException(status_code=404, detail=f"Failed to fetch team information for team {team_id} from BB API")
            
            # Save to database (use a placeholder username since this isn't the user's team)
            from ...storage.models import TeamInfo
            db_manager = DatabaseManager("bb_arena_data.db")
            team_info = TeamInfo.from_api_data(team_data, f"fetched_for_{team_id}")
            db_manager.save_team_info(team_info)
            
            # Return the team data with cache info
            response_data = team_data.copy()
            response_data["last_synced"] = team_info.last_synced.isoformat() if team_info.last_synced else None
            response_data["from_cache"] = False
            
            return response_data
            
    except Exception as e:
        logger.error(f"Error syncing team info for team {team_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to sync team info for team {team_id}: {str(e)}")


@router.get("/seasons/team/{team_id}")
async def get_seasons_for_team(team_id: str):
    """Get seasons data with team-specific minimum season based on creation date."""
    try:
        # Get standard seasons data
        seasons_response = await buzzerbeater.get_seasons()
        
        # Get minimum season for this team based on creation date
        db_manager = DatabaseManager("bb_arena_data.db")
        min_season_for_team = db_manager.get_minimum_season_for_team(team_id)
        
        # If we don't have a team-specific minimum, try to sync the team info first
        if min_season_for_team is None:
            logger.info(f"No cached creation date for team {team_id}, attempting to sync team info")
            try:
                # Try to sync team info to get the creation date
                await sync_specific_team_info(team_id)
                # Try again to get the minimum season
                min_season_for_team = db_manager.get_minimum_season_for_team(team_id)
                logger.info(f"After sync, team {team_id} minimum season: {min_season_for_team}")
            except Exception as sync_error:
                logger.warning(f"Failed to sync team info for {team_id}: {sync_error}")
                # Continue with None - we'll fall back to no team-specific minimum
        
        # If we have a team-specific minimum, use it, otherwise use the existing minimum
        if min_season_for_team is not None:
            # Override the min season for this team
            return {
                "seasons": seasons_response.seasons,
                "current_season": seasons_response.current_season,
                "team_min_season": min_season_for_team,
                "team_id": team_id
            }
        else:
            # Fallback to standard response if no team creation date found
            return {
                "seasons": seasons_response.seasons,
                "current_season": seasons_response.current_season,
                "team_min_season": None,
                "team_id": team_id
            }
        
    except Exception as e:
        logger.error(f"Error fetching seasons for team {team_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch seasons for team: {str(e)}")
