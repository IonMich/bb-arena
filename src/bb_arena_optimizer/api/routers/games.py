"""Game-related API endpoints."""

import logging
import os
import traceback
from datetime import datetime
from typing import Any, List

from fastapi import APIRouter, HTTPException
from dotenv import load_dotenv

from ...storage.database import DatabaseManager
from ...storage.models import GameRecord
from ...api.client import BuzzerBeaterAPI

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/bb", tags=["games"])


@router.get("/team/{team_id}/schedule")
async def get_team_schedule(team_id: int, season: int | None = None):
    """Get team schedule from BuzzerBeater API."""
    username = os.getenv("BB_USERNAME")
    security_code = os.getenv("BB_SECURITY_CODE")
    
    if not username or not security_code:
        raise HTTPException(
            status_code=500, 
            detail="BuzzerBeater credentials not configured."
        )
    
    try:
        with BuzzerBeaterAPI(username, security_code) as api:
            schedule_data = api.get_schedule(team_id, season)
            
            if not schedule_data:
                raise HTTPException(
                    status_code=404,
                    detail=f"No schedule found for team {team_id}"
                )
            
            return schedule_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching team {team_id} schedule: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch schedule: {str(e)}")

@router.get("/team/{team_id}/games")
async def get_team_stored_games(team_id: int, season: int | None = None, limit: int = 100):
    """Get stored games for a team from the database."""
    try:
        db_manager = DatabaseManager("bb_arena_data.db")
        games = db_manager.get_games_for_team(str(team_id), limit=limit)
        
        # Filter by season if provided
        if season is not None:
            games = [game for game in games if game.season == season]
        
        # Convert to response format
        games_data = []
        for game in games:
            game_data: dict[str, Any] = {
                "id": game.game_id,
                "home_team_id": game.home_team_id,
                "away_team_id": game.away_team_id,
                "date": game.date.isoformat() if game.date else None,
                "type": game.game_type,
                "season": game.season,
                "score_home": game.score_home,
                "score_away": game.score_away,
                "neutral_arena": game.neutral_arena
            }
            
            # Add attendance if available
            if game.total_attendance is not None:
                game_data["attendance"] = {
                    "bleachers": game.bleachers_attendance,
                    "lower_tier": game.lower_tier_attendance,
                    "courtside": game.courtside_attendance,
                    "luxury_boxes": game.luxury_boxes_attendance
                }
                game_data["calculated_revenue"] = game.calculated_revenue
            
            # Add pricing if available
            pricing_fields = [
                ("bleachers_price", getattr(game, "bleachers_price", None)),
                ("lower_tier_price", getattr(game, "lower_tier_price", None)),
                ("courtside_price", getattr(game, "courtside_price", None)),
                ("luxury_boxes_price", getattr(game, "luxury_boxes_price", None))
            ]
            
            # Only include pricing if at least one price is available
            if any(price is not None for _, price in pricing_fields):
                game_data["pricing"] = {
                    "bleachers": getattr(game, "bleachers_price", None),
                    "lower_tier": getattr(game, "lower_tier_price", None),
                    "courtside": getattr(game, "courtside_price", None),
                    "luxury_boxes": getattr(game, "luxury_boxes_price", None)
                }
                
            games_data.append(game_data)
        
        return {"games": games_data}
        
    except Exception as e:
        logger.error(f"Error fetching stored games for team {team_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch stored games: {str(e)}")


@router.post("/team/{team_id}/games/check-stored")
async def check_games_stored(team_id: int, game_ids: List[str]):
    """Check which games from a list are already stored in the database."""
    try:
        db_manager = DatabaseManager("bb_arena_data.db")
        stored_games = {}
        for game_id in game_ids:
            game = db_manager.get_game_by_id(game_id)
            stored_games[game_id] = game is not None
        
        return {"stored_games": stored_games}
        
    except Exception as e:
        logger.error(f"Error checking stored games for team {team_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check stored games: {str(e)}")


@router.get("/team/{team_id}/games/home-count")
async def get_team_home_games_count(team_id: int, season: int | None = None):
    """Get count of stored home games for a team, optionally filtered by season."""
    try:
        db_manager = DatabaseManager("bb_arena_data.db")
        games = db_manager.get_games_for_team(str(team_id), limit=10000)  # High limit to get all games
        
        # Filter for home games (games where the specified team is the home team, excluding neutral venue games)
        home_games = [game for game in games if game.home_team_id == team_id and not game.neutral_arena]
        
        if season is not None:
            # Filter by specific season
            home_games = [game for game in home_games if game.season == season]
            return {"team_id": team_id, "season": season, "home_games_count": len(home_games)}
        else:
            # Group by season and return breakdown
            season_breakdown: dict[int, int] = {}
            for game in home_games:
                if game.season:
                    season_breakdown[game.season] = season_breakdown.get(game.season, 0) + 1
            
            total_count = len(home_games)
            return {
                "team_id": team_id, 
                "total_home_games_count": total_count,
                "breakdown_by_season": season_breakdown
            }
        
    except Exception as e:
        logger.error(f"Error fetching home games count for team {team_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch home games count: {str(e)}")


@router.get("/team/{team_id}/games/prefix-max-attendance")
async def get_prefix_max_attendance(team_id: int, up_to_date: str):
    """Get maximum attendance for each section from all home games up to a specific date."""
    try:
        # Validate date format
        try:
            datetime.fromisoformat(up_to_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)")
        
        db_manager = DatabaseManager("bb_arena_data.db")
        prefix_max = db_manager.get_prefix_max_attendance(str(team_id), up_to_date)
        
        # Also get total count of games used for this calculation
        games = db_manager.get_games_for_team(str(team_id), limit=10000)
        home_games_before_date = [
            game for game in games 
            if str(game.home_team_id) == str(team_id) 
            and game.date 
            and game.date.isoformat() < up_to_date
            and game.total_attendance is not None
            and not game.neutral_arena
        ]
        
        return {
            "team_id": team_id,
            "up_to_date": up_to_date,
            "prefix_max_attendance": prefix_max,
            "games_analyzed": len(home_games_before_date),
            "description": f"Maximum attendance in each section from {len(home_games_before_date)} home games before {up_to_date}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching prefix max attendance for team {team_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch prefix max attendance: {str(e)}")


@router.get("/game/{game_id}/stored")
async def get_game_from_db(game_id: str):
    """Get game data from database only (no BB API call)."""
    try:
        db_manager = DatabaseManager("bb_arena_data.db")
        stored_game = db_manager.get_game_by_id(game_id)
        
        if not stored_game:
            raise HTTPException(
                status_code=404,
                detail=f"Game {game_id} not found in database"
            )
        
        return stored_game.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching stored game {game_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch stored game: {str(e)}")


@router.post("/game/{game_id}/fetch")
async def fetch_and_store_game_from_bb(game_id: str):
    """Fetch game from BB API and store to database."""
    username = os.getenv("BB_USERNAME")
    security_code = os.getenv("BB_SECURITY_CODE")
    
    if not username or not security_code:
        raise HTTPException(
            status_code=500, 
            detail="BuzzerBeater credentials not configured."
        )
    
    try:
        db_manager = DatabaseManager("bb_arena_data.db")
        
        # Fetch from BB API
        with BuzzerBeaterAPI(username, security_code) as api:
            boxscore_data = api.get_boxscore(game_id)
            
            if not boxscore_data:
                raise HTTPException(
                    status_code=404,
                    detail=f"No boxscore found for game {game_id} in BB API"
                )
            
            # Calculate season from game date using database seasons
            calculated_season = None
            game_date_str = boxscore_data["start_date"]
            if game_date_str:
                try:
                    # Parse the game date
                    if game_date_str.endswith('Z'):
                        parsed_game_date = datetime.fromisoformat(game_date_str.replace('Z', '+00:00'))
                    else:
                        parsed_game_date = datetime.fromisoformat(game_date_str)
                    
                    # Get all seasons from database to find which season this game belongs to
                    all_seasons = db_manager.get_all_seasons()
                    for season in all_seasons:
                        if season.start_date and season.end_date:
                            if season.start_date <= parsed_game_date <= season.end_date:
                                calculated_season = season.season_number
                                break
                        elif season.start_date and not season.end_date:
                            # Current season with no end date
                            if season.start_date <= parsed_game_date:
                                calculated_season = season.season_number
                            
                    if calculated_season is None:
                        logger.warning(f"Could not determine season for game {game_id} with date {parsed_game_date}")
                        
                except Exception as date_parse_error:
                    logger.warning(f"Could not parse game date '{game_date_str}' for season calculation: {date_parse_error}")
            
            if calculated_season is None:
                raise HTTPException(
                    status_code=422,
                    detail=f"Cannot determine season for game {game_id}. Unable to store game without season information."
                )
            
            # Convert to GameRecord and store (null values won't overwrite existing data)
            game_record = GameRecord.from_api_data(boxscore_data, season=calculated_season)
            saved_id = db_manager.save_game_record(game_record)
            
            # Return the stored record (which includes any preserved existing data)
            stored_game = db_manager.get_game_by_id(game_id)
            if not stored_game:
                raise HTTPException(status_code=500, detail="Failed to retrieve stored game record")
            
            logger.info(f"Successfully fetched and stored game {game_id} with database ID {saved_id}")
            return stored_game.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching and storing game {game_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch and store game: {str(e)}")
