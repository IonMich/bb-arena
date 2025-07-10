"""FastAPI server for serving arena data from the database."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ..storage.database import DatabaseManager
from ..storage.models import ArenaSnapshot

logger = logging.getLogger(__name__)


class ArenaResponse(BaseModel):
    """Response model for arena data."""
    
    id: int
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

# Initialize database manager
db_manager = DatabaseManager()


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "BB Arena Optimizer API"}


@app.get("/arenas", response_model=ArenaListResponse)
async def get_arenas(limit: int = 50, offset: int = 0):
    """Get list of all arena snapshots."""
    try:
        arenas = db_manager.get_arena_snapshots(limit=limit, offset=offset)
        total_count = db_manager.get_arena_snapshots_count()
        
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
