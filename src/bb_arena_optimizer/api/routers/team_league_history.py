"""Team league history API endpoints."""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Response models
class TeamLeagueHistoryResponse(BaseModel):
    """Response model for team league history."""
    
    bb_team_id: str | None
    season: int | None
    team_name: str | None
    league_id: str | None
    league_name: str | None
    league_level: int | None
    achievement: str | None
    is_active_team: bool
    created_at: str | None


class TeamLeagueHistoryListResponse(BaseModel):
    """Response model for list of team league history entries."""
    
    history: list[TeamLeagueHistoryResponse]
    total_count: int
    active_count: int
    predecessor_count: int


# Create router
router = APIRouter(prefix="/api/bb/team", tags=["team-league-history"])


@router.get("/{team_id}/league-history", response_model=TeamLeagueHistoryListResponse)
async def get_team_league_history(team_id: str, active_only: bool = False):
    """Get team league history from database."""
    from ...storage.database import DatabaseManager
    
    try:
        logger.info(f"Received team_id: '{team_id}' (type: {type(team_id)})")
        
        # Validate and convert team_id
        if not team_id or not team_id.strip():
            raise HTTPException(status_code=400, detail="Team ID is required")
        
        try:
            team_id_int = int(team_id.strip())
        except ValueError as e:
            logger.error(f"Failed to convert team_id '{team_id}' to integer: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid team ID format: '{team_id}' must be a valid integer")
        
        if team_id_int <= 0:
            raise HTTPException(status_code=400, detail="Team ID must be a positive integer")
        
        logger.info(f"Converted team_id to integer: {team_id_int}")
        
        db_manager = DatabaseManager("bb_arena_data.db")
        history_entries = db_manager.get_team_league_history(team_id_int, active_only=active_only)
        
        logger.info(f"Retrieved {len(history_entries)} history entries for team {team_id_int}")
        
        # Convert to response format
        history_responses = []
        for entry in history_entries:
            history_responses.append(TeamLeagueHistoryResponse(
                bb_team_id=entry.bb_team_id,
                season=entry.season,
                team_name=entry.team_name,
                league_id=str(entry.league_id) if entry.league_id is not None else None,
                league_name=entry.league_name,
                league_level=entry.league_level,
                achievement=entry.achievement,
                is_active_team=entry.is_active_team,
                created_at=entry.created_at.isoformat() if entry.created_at else None
            ))
        
        # Calculate counts
        all_entries = db_manager.get_team_league_history(team_id_int, active_only=False)
        active_count = len([e for e in all_entries if e.is_active_team])
        predecessor_count = len([e for e in all_entries if not e.is_active_team])
        
        return TeamLeagueHistoryListResponse(
            history=history_responses,
            total_count=len(all_entries),
            active_count=active_count,
            predecessor_count=predecessor_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching team {team_id} league history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch team league history: {str(e)}")


@router.post("/{team_id}/league-history/collect")
async def collect_team_league_history(team_id: str):
    """Collect and store team league history from BuzzerBeater webpage."""
    from ...storage.database import DatabaseManager
    
    try:
        team_id_int = int(team_id)
        db_manager = DatabaseManager("bb_arena_data.db")
        success = db_manager.collect_team_history_from_webpage(team_id_int)
        
        if success:
            # Get the collected data for the response
            history_entries = db_manager.get_team_league_history(team_id_int, active_only=False)
            return {
                "success": True,
                "message": f"Successfully collected {len(history_entries)} league history entries",
                "total_entries": len(history_entries),
                "active_entries": len([e for e in history_entries if e.is_active_team]),
                "predecessor_entries": len([e for e in history_entries if not e.is_active_team])
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to collect team league history")
            
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid team ID format")
    except Exception as e:
        logger.error(f"Error collecting team {team_id} league history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to collect team league history: {str(e)}")


@router.get("/{team_id}/current-league")
async def get_team_current_league_info(team_id: str):
    """Get current league information for a team."""
    from ...storage.database import DatabaseManager
    
    try:
        team_id_int = int(team_id)
        db_manager = DatabaseManager("bb_arena_data.db")
        current_info = db_manager.get_team_current_league_info(team_id_int)
        
        if current_info:
            return current_info
        else:
            raise HTTPException(status_code=404, detail="No current league information found for team")
            
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid team ID format")
    except Exception as e:
        logger.error(f"Error fetching current league info for team {team_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch current league info: {str(e)}")
