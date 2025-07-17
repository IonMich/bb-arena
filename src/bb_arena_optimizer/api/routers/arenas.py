"""Arena-related API endpoints."""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

logger = logging.getLogger(__name__)

# Response models
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


# Create router
router = APIRouter(prefix="/arenas", tags=["arenas"])


@router.get("", response_model=ArenaListResponse)
async def get_arenas(limit: int = 50, offset: int = 0):
    """Get list of latest arena snapshots (one per team)."""
    from ...storage.database import DatabaseManager
    
    try:
        db_manager = DatabaseManager("bb_arena_data.db")
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


@router.get("/{arena_id}", response_model=ArenaResponse)
async def get_arena(arena_id: int):
    """Get a specific arena by ID."""
    from ...storage.database import DatabaseManager
    
    try:
        db_manager = DatabaseManager("bb_arena_data.db")
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


@router.get("/team/{team_id}")
async def get_team_arenas(team_id: str, limit: int = 50):
    """Get arena snapshots for a specific team."""
    from ...storage.database import DatabaseManager
    
    try:
        db_manager = DatabaseManager("bb_arena_data.db")
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


@router.get("/team/{team_id}/history")
async def get_team_arena_history(team_id: str, limit: int = 50):
    """Get all arena snapshots for a specific team (history view)."""
    from ...storage.database import DatabaseManager
    
    try:
        db_manager = DatabaseManager("bb_arena_data.db")
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
