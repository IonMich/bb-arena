"""FastAPI server for serving arena data from the database."""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from ..storage.database import DatabaseManager
from ..storage.models import ArenaSnapshot
from ..api.client import BuzzerBeaterAPI

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
                    else:
                        logger.warning(f"No arena data received for team {team_id}")
                        failed_teams.append(team_id)
                        
                except Exception as e:
                    logger.error(f"Error fetching arena data for team {team_id}: {e}")
                    failed_teams.append(team_id)
        
        league_name = standings_data.get("league_info", {}).get("league_name", f"League {request.league_id}")
        
        return BBAPIResponse(
            success=True,
            message=f"Collected {arenas_collected} new arenas from {league_name} (skipped {arenas_skipped} duplicates)",
            arenas_collected=arenas_collected,
            arenas_skipped=arenas_skipped,
            failed_teams=failed_teams
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error collecting arenas from BuzzerBeater API: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to collect arena data: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
