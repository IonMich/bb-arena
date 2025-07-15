"""FastAPI server for serving arena data from the database."""

import logging
import os
import traceback
from datetime import datetime
from typing import Any, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from ..storage.database import DatabaseManager
from ..storage.models import ArenaSnapshot, GameRecord, PriceSnapshot, Season
from ..api.client import BuzzerBeaterAPI
from bb_arena_optimizer.collecting import HistoricalPricingService

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class ArenaResponse(BaseModel):
    """Response model for arena data."""
    
    id: int | None
    team_id: str | None
    arena_name: str | None
    bleachers_capacity: int
    lower_tier_capacity: int
    courtside_capacity: int
    luxury_boxes_capacity: int
    total_capacity: int
    expansion_in_progress: bool
    expansion_completion_date: str | None
    expansion_cost: float | None
    created_at: str


class ArenaListResponse(BaseModel):
    """Response model for list of arenas."""
    
    arenas: list[ArenaResponse]
    total_count: int


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


class PriceResponse(BaseModel):
    """Response model for price snapshot data."""
    
    id: int | None
    team_id: str | None
    bleachers_price: int | None
    lower_tier_price: int | None
    courtside_price: int | None
    luxury_boxes_price: int | None
    created_at: str


class PriceListResponse(BaseModel):
    """Response model for list of price snapshots."""
    
    prices: list[PriceResponse]
    total_count: int


class PriceCollectionResponse(BaseModel):
    """Response model for price collection operations."""
    
    success: bool
    message: str
    prices_collected: int
    prices_skipped: int
    failed_teams: List[int]


# Initialize database manager
db_manager = DatabaseManager("bb_arena_data.db")

# Initialize FastAPI app
app = FastAPI(
    title="BB Arena Optimizer API",
    description="API for managing and viewing BuzzerBeater arena data",
    version="1.0.0"
)

# Add CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "BB Arena Optimizer API"}


@app.get("/arenas", response_model=ArenaListResponse)
async def get_arenas(limit: int = 50, offset: int = 0):
    """Get list of latest arena snapshots (one per team)."""
    try:
        arenas = db_manager.get_latest_arena_snapshots(limit=limit, offset=offset)
        total_count = db_manager.get_latest_arena_snapshots_count()
        
        arena_responses = []
        for arena in arenas:
            arena_responses.append(ArenaResponse(
                id=arena.id,
                team_id=arena.team_id,
                arena_name=arena.arena_name,
                bleachers_capacity=arena.bleachers_capacity,
                lower_tier_capacity=arena.lower_tier_capacity,
                courtside_capacity=arena.courtside_capacity,
                luxury_boxes_capacity=arena.luxury_boxes_capacity,
                total_capacity=arena.total_capacity,
                expansion_in_progress=arena.expansion_in_progress,
                expansion_completion_date=arena.expansion_completion_date,
                expansion_cost=arena.expansion_cost,
                created_at=arena.created_at.isoformat() if arena.created_at else ""
            ))
        
        return ArenaListResponse(arenas=arena_responses, total_count=total_count)
    
    except Exception as e:
        logger.error(f"Error fetching arenas: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/arenas/{arena_id}", response_model=ArenaResponse)
async def get_arena(arena_id: int):
    """Get a specific arena by ID."""
    try:
        arena = db_manager.get_arena_snapshot_by_id(arena_id)
        if not arena:
            raise HTTPException(status_code=404, detail="Arena not found")
        
        return ArenaResponse(
            id=arena.id,
            team_id=arena.team_id,
            arena_name=arena.arena_name,
            bleachers_capacity=arena.bleachers_capacity,
            lower_tier_capacity=arena.lower_tier_capacity,
            courtside_capacity=arena.courtside_capacity,
            luxury_boxes_capacity=arena.luxury_boxes_capacity,
            total_capacity=arena.total_capacity,
            expansion_in_progress=arena.expansion_in_progress,
            expansion_completion_date=arena.expansion_completion_date,
            expansion_cost=arena.expansion_cost,
            created_at=arena.created_at.isoformat() if arena.created_at else ""
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching arena {arena_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/arenas/team/{team_id}")
async def get_team_arenas(team_id: str, limit: int = 50):
    """Get arena snapshots for a specific team."""
    try:
        arenas = db_manager.get_arena_snapshots_by_team(team_id, limit=limit)
        
        arena_responses = []
        for arena in arenas:
            arena_responses.append(ArenaResponse(
                id=arena.id,
                team_id=arena.team_id,
                arena_name=arena.arena_name,
                bleachers_capacity=arena.bleachers_capacity,
                lower_tier_capacity=arena.lower_tier_capacity,
                courtside_capacity=arena.courtside_capacity,
                luxury_boxes_capacity=arena.luxury_boxes_capacity,
                total_capacity=arena.total_capacity,
                expansion_in_progress=arena.expansion_in_progress,
                expansion_completion_date=arena.expansion_completion_date,
                expansion_cost=arena.expansion_cost,
                created_at=arena.created_at.isoformat() if arena.created_at else ""
            ))
        
        return {"arenas": arena_responses, "team_id": team_id}
    
    except Exception as e:
        logger.error(f"Error fetching team {team_id} arenas: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/arenas/team/{team_id}/history")
async def get_team_arena_history(team_id: str, limit: int = 50):
    """Get all arena snapshots for a specific team (history view)."""
    try:
        arenas = db_manager.get_arena_snapshots_by_team(team_id, limit=limit)
        
        arena_responses = []
        for arena in arenas:
            arena_responses.append(ArenaResponse(
                id=arena.id,
                team_id=arena.team_id,
                arena_name=arena.arena_name,
                bleachers_capacity=arena.bleachers_capacity,
                lower_tier_capacity=arena.lower_tier_capacity,
                courtside_capacity=arena.courtside_capacity,
                luxury_boxes_capacity=arena.luxury_boxes_capacity,
                total_capacity=arena.total_capacity,
                expansion_in_progress=arena.expansion_in_progress,
                expansion_completion_date=arena.expansion_completion_date,
                expansion_cost=arena.expansion_cost,
                created_at=arena.created_at.isoformat() if arena.created_at else ""
            ))
        
        return {"arenas": arena_responses, "team_id": team_id, "total_snapshots": len(arena_responses)}
    
    except Exception as e:
        logger.error(f"Error fetching team {team_id} arena history: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/bb/collect-arenas", response_model=BBAPIResponse)
async def collect_arenas_from_bb(request: BBAPIRequest):
    """Collect arena data from BuzzerBeater API for all teams in the specified league."""
    username = os.getenv("BB_USERNAME")
    security_code = os.getenv("BB_SECURITY_CODE")
    
    if not username or not security_code:
        raise HTTPException(
            status_code=500, 
            detail="BuzzerBeater credentials not configured. Please set BB_USERNAME and BB_SECURITY_CODE environment variables."
        )
    
    try:
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
                                        logger.info(f"Skipped unchanged price data for team {team_id}")
                                
                                if should_save_price:
                                    price_id = db_manager.save_price_snapshot(price_snapshot)
                                    prices_collected += 1
                                    logger.info(f"Saved new price snapshot for team {team_id} with ID {price_id}")
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


@app.get("/api/bb/team/{team_id}/schedule")
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


@app.get("/api/bb/game/{game_id}/boxscore")
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
                "revenue": stored_game.ticket_revenue
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
                                        # Season with both start and end dates
                                        if season.start_date <= parsed_game_date <= season.end_date:
                                            calculated_season = season.season_number
                                            logger.info(f"Calculated season {calculated_season} for game {game_id} based on date {parsed_game_date}")
                                            break
                                    elif season.start_date and not season.end_date:
                                        # Current season with no end date
                                        if season.start_date <= parsed_game_date:
                                            calculated_season = season.season_number
                                            logger.info(f"Calculated season {calculated_season} for game {game_id} based on date {parsed_game_date} (current season)")
                                            break
                                        
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


@app.get("/api/bb/team/{team_id}/games")
async def get_team_stored_games(team_id: int, season: int | None = None, limit: int = 100):
    """Get stored games for a team from the database."""
    try:
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
                game_data["revenue"] = game.ticket_revenue
            
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


@app.post("/api/bb/team/{team_id}/games/check-stored")
async def check_games_stored(team_id: int, game_ids: List[str]):
    """Check which games from a list are already stored in the database."""
    try:
        stored_games = {}
        for game_id in game_ids:
            game = db_manager.get_game_by_id(game_id)
            stored_games[game_id] = game is not None
        
        return {"stored_games": stored_games}
        
    except Exception as e:
        logger.error(f"Error checking stored games for team {team_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check stored games: {str(e)}")


@app.get("/api/bb/team/{team_id}/games/home-count")
async def get_team_home_games_count(team_id: int, season: int | None = None):
    """Get count of stored home games for a team, optionally filtered by season."""
    try:
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


@app.get("/api/bb/seasons", response_model=SeasonsListResponse)
async def get_seasons():
    """Get all seasons, updating from API if needed."""
    try:
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


@app.post("/api/bb/seasons/update")
async def force_update_seasons():
    """Force update seasons from BBAPI."""
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
            db_manager.save_seasons(seasons)
            
            logger.info(f"Force updated {len(seasons)} seasons from API")
            
            return {"message": f"Updated {len(seasons)} seasons", "seasons_count": len(seasons)}
        
    except Exception as e:
        logger.error(f"Error force updating seasons: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update seasons: {str(e)}")


@app.get("/api/bb/team-info")
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


@app.get("/api/bb/team-info/cached")
async def get_cached_team_info():
    """Get cached team information from database."""
    username = os.getenv("BB_USERNAME")
    
    if not username:
        raise HTTPException(status_code=500, detail="BB_USERNAME not configured")
    
    try:
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
            "last_synced": team_info.last_synced.isoformat() if team_info.last_synced else None,
            "from_cache": True
        }
            
    except Exception as e:
        logger.error(f"Error fetching cached team info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch cached team info: {str(e)}")


@app.post("/api/bb/team-info/sync")
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
            from ..storage.models import TeamInfo
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


@app.get("/api/bb/team-info/smart")
async def get_smart_team_info():
    """Get team info intelligently - from cache if recent, otherwise sync from API."""
    username = os.getenv("BB_USERNAME")
    
    if not username:
        raise HTTPException(status_code=500, detail="BB_USERNAME not configured")
    
    try:
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


@app.get("/api/bb/standings")
async def get_league_standings(leagueid: int, season: int | None = None):
    """Get league standings which includes team information."""
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


@app.get("/prices", response_model=PriceListResponse)
async def get_price_snapshots(limit: int = 50, offset: int = 0):
    """Get list of latest price snapshots (one per team)."""
    try:
        import sqlite3
        with sqlite3.connect(db_manager.db_path) as conn:
            cursor = conn.execute("""
                SELECT p.* FROM price_snapshots p
                INNER JOIN (
                    SELECT team_id, MAX(created_at) as latest_date
                    FROM price_snapshots 
                    WHERE team_id IS NOT NULL
                    GROUP BY team_id
                ) latest ON p.team_id = latest.team_id AND p.created_at = latest.latest_date
                ORDER BY p.created_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))
            
            prices = cursor.fetchall()
            
            # Get total count
            cursor = conn.execute("""
                SELECT COUNT(DISTINCT team_id) FROM price_snapshots 
                WHERE team_id IS NOT NULL
            """)
            total_count = cursor.fetchone()[0]
        
        price_responses = []
        for price in prices:
            price_responses.append(PriceResponse(
                id=price[0],
                team_id=price[1],
                bleachers_price=price[2],
                lower_tier_price=price[3],
                courtside_price=price[4],
                luxury_boxes_price=price[5],
                created_at=price[6]
            ))
        
        return PriceListResponse(prices=price_responses, total_count=total_count)
    
    except Exception as e:
        logger.error(f"Error fetching price snapshots: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/prices/team/{team_id}")
async def get_team_price_history(team_id: str, limit: int = 50):
    """Get price history for a specific team."""
    try:
        price_history = db_manager.get_price_history(team_id, limit=limit)
        
        price_responses = []
        for price in price_history:
            price_responses.append(PriceResponse(
                id=price.id,
                team_id=price.team_id,
                bleachers_price=price.bleachers_price,
                lower_tier_price=price.lower_tier_price,
                courtside_price=price.courtside_price,
                luxury_boxes_price=price.luxury_boxes_price,
                created_at=price.created_at.isoformat() if price.created_at else ""
            ))
        
        return {"prices": price_responses, "team_id": team_id}
    
    except Exception as e:
        logger.error(f"Error fetching price history for team {team_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/bb/collect-prices", response_model=PriceCollectionResponse)
async def collect_prices_from_bb(request: BBAPIRequest):
    """Collect price data from BuzzerBeater API for all teams in the specified league."""
    username = os.getenv("BB_USERNAME")
    security_code = os.getenv("BB_SECURITY_CODE")
    
    if not username or not security_code:
        raise HTTPException(
            status_code=500, 
            detail="BuzzerBeater credentials not configured. Please set BB_USERNAME and BB_SECURITY_CODE environment variables."
        )
    
    try:
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


@app.get("/api/bb/team/{team_id}/games/prefix-max-attendance")
async def get_prefix_max_attendance(team_id: int, up_to_date: str):
    """Get maximum attendance for each section from all home games up to a specific date.
    
    This provides historical lower bounds for arena capacity based on actual attendance data.
    
    Args:
        team_id: Team ID to query
        up_to_date: ISO format date string (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
    
    Returns:
        Dictionary with max attendance for each section and metadata
    """
    try:
        # Validate date format
        try:
            datetime.fromisoformat(up_to_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)")
        
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

@app.get("/api/historical-pricing/status/{team_id}")
async def get_historical_pricing_status(team_id: str):
    """Get status of historical pricing data for a team.
    
    Returns information about games with pricing data vs games without.
    """
    try:
        # Get all games for the team
        games = db_manager.get_games_for_team(team_id, limit=1000)
        
        total_games = len(games)
        games_with_pricing = 0
        games_without_pricing = 0
        
        for game in games:
            has_any_pricing = any([
                game.bleachers_price is not None,
                game.lower_tier_price is not None,
                game.courtside_price is not None,
                game.luxury_boxes_price is not None
            ])
            
            if has_any_pricing:
                games_with_pricing += 1
            else:
                games_without_pricing += 1
        
        return {
            "team_id": team_id,
            "total_games": total_games,
            "games_with_pricing": games_with_pricing,
            "games_without_pricing": games_without_pricing,
            "pricing_coverage": round(games_with_pricing / total_games * 100, 1) if total_games > 0 else 0
        }
        
    except Exception as e:
        logger.error(f"Error getting pricing status for team {team_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get pricing status: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
