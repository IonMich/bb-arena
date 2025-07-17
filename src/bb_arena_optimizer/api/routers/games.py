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


@router.get("/game/{game_id}/boxscore")
async def get_game_boxscore(game_id: str):
    """Get game boxscore with attendance from BuzzerBeater API and store it."""
    username = os.getenv("BB_USERNAME")
    security_code = os.getenv("BB_SECURITY_CODE")
    
    if not username or not security_code:
        raise HTTPException(
            status_code=500, 
            detail="BuzzerBeater credentials not configured."
        )
    
    try:
        db_manager = DatabaseManager("bb_arena_data.db")
        
        # Check if we already have this game stored
        stored_game = db_manager.get_game_by_id(game_id)
        
        if stored_game and stored_game.total_attendance is not None:
            # Return stored data if we have attendance info
            response_data = {
                "attendance": {
                    "bleachers": stored_game.bleachers_attendance,
                    "lower_tier": stored_game.lower_tier_attendance,
                    "courtside": stored_game.courtside_attendance,
                    "luxury_boxes": stored_game.luxury_boxes_attendance
                },
                "calculated_revenue": stored_game.calculated_revenue
            }
            
            # Include pricing info if available
            pricing_data = {}
            if stored_game.bleachers_price is not None:
                pricing_data["bleachers"] = stored_game.bleachers_price
            if stored_game.lower_tier_price is not None:
                pricing_data["lower_tier"] = stored_game.lower_tier_price
            if stored_game.courtside_price is not None:
                pricing_data["courtside"] = stored_game.courtside_price
            if stored_game.luxury_boxes_price is not None:
                pricing_data["luxury_boxes"] = stored_game.luxury_boxes_price
            
            if pricing_data:
                response_data["pricing"] = pricing_data
            
            return response_data
        
        # Fetch from API if not stored or missing attendance data
        with BuzzerBeaterAPI(username, security_code) as api:
            boxscore_data = api.get_boxscore(game_id)
            
            if not boxscore_data:
                raise HTTPException(
                    status_code=404,
                    detail=f"No boxscore found for game {game_id}"
                )
            
            # Store the game data if we have attendance information and required fields
            attendance_data = boxscore_data.get("attendance")
            home_team_id = boxscore_data.get("home_team_id")
            away_team_id = boxscore_data.get("away_team_id")
            
            # Validate required fields more strictly
            if (attendance_data and 
                home_team_id is not None and 
                away_team_id is not None and 
                isinstance(home_team_id, int) and home_team_id > 0 and
                isinstance(away_team_id, int) and away_team_id > 0):
                try:
                    # Get season information
                    api_season = boxscore_data.get("season")
                    calculated_season = None
                    
                    # If API doesn't provide season, try to calculate it from the game date
                    if api_season is None:
                        game_date_str = boxscore_data.get("date")
                        if game_date_str and isinstance(game_date_str, str):
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
                    
                    final_season = api_season if api_season is not None else calculated_season
                    
                    # Validate that we have the required information
                    if final_season is None:
                        logger.error(f"Cannot save game {game_id}: No season information available from API or calculable from date")
                        raise ValueError("Season information required but not available from API or calculable from date")
                    
                    # Validate that we have a game type
                    game_type = boxscore_data.get("type")
                    if not game_type:
                        logger.error(f"Cannot save game {game_id}: No game type provided by API")
                        raise ValueError("Game type required but not provided by API")
                    
                    # Validate that we have a date
                    game_date = boxscore_data.get("date")
                    if not game_date or not isinstance(game_date, str):
                        logger.error(f"Cannot save game {game_id}: No valid date provided by API")
                        raise ValueError("Game date required but not provided by API")
                    
                    # Debug logging
                    logger.info(f"About to save game {game_id}:")
                    logger.info(f"  home_team_id: {home_team_id} (type: {type(home_team_id)})")
                    logger.info(f"  away_team_id: {away_team_id} (type: {type(away_team_id)})")
                    logger.info(f"  attendance_data: {attendance_data}")
                    logger.info(f"  final_season: {final_season} (from API: {api_season}, calculated: {calculated_season})")
                    logger.info(f"  game_type: {game_type}")
                    logger.info(f"  game_date: {game_date}")
                    
                    # Create GameRecord from boxscore data using the proper factory method
                    # Prepare the game data in the format expected by from_api_data
                    game_data_for_record = {
                        "id": game_id,
                        "type": game_type,
                        "season": final_season,
                        "date": game_date,
                        "attendance": attendance_data,
                        "ticket_revenue": boxscore_data.get("revenue")
                    }
                    
                    logger.info(f"Game data for record creation: {game_data_for_record}")
                    
                    game_record = GameRecord.from_api_data(
                        game_data_for_record,
                        home_team_id=home_team_id,
                        away_team_id=away_team_id
                    )
                    
                    logger.info(f"Created GameRecord: game_id={game_record.game_id}, home={game_record.home_team_id}, away={game_record.away_team_id}, season={game_record.season}, type={game_record.game_type}, date={game_record.date}")
                    
                    # Save to database
                    saved_id = db_manager.save_game_record(game_record)
                    logger.info(f"Successfully saved game record for game {game_id} with database ID {saved_id} (Home: {home_team_id}, Away: {away_team_id})")
                    
                except Exception as save_error:
                    logger.error(f"Failed to save game record for {game_id}: {save_error}")
                    logger.error(f"Full traceback: {traceback.format_exc()}")
                    # Don't re-raise the error - just log it and continue to return the boxscore data
            else:
                missing_fields = []
                if not attendance_data:
                    missing_fields.append("attendance")
                if not home_team_id or not isinstance(home_team_id, int) or home_team_id <= 0:
                    missing_fields.append("valid home_team_id")
                if not away_team_id or not isinstance(away_team_id, int) or away_team_id <= 0:
                    missing_fields.append("valid away_team_id")
                logger.warning(f"Insufficient data to save game record for {game_id} - missing: {', '.join(missing_fields)}")
            
            return boxscore_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching game {game_id} boxscore: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch boxscore: {str(e)}")


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
