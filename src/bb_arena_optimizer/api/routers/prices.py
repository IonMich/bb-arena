"""Price-related API endpoints."""

import logging
import sqlite3
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

logger = logging.getLogger(__name__)

# Response models
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


# Create router
router = APIRouter(prefix="/prices", tags=["prices"])


@router.get("", response_model=PriceListResponse)
async def get_price_snapshots(limit: int = 50, offset: int = 0):
    """Get list of latest price snapshots (one per team)."""
    from ...storage.database import DatabaseManager
    
    try:
        db_manager = DatabaseManager("bb_arena_data.db")
        
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


@router.get("/team/{team_id}")
async def get_team_price_history(team_id: str, limit: int = 50):
    """Get price history for a specific team."""
    from ...storage.database import DatabaseManager
    
    try:
        db_manager = DatabaseManager("bb_arena_data.db")
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


@router.get("/historical/team/{team_id}", response_model=PriceListResponse)
async def get_historical_price_snapshots(team_id: str, limit: int = 50, offset: int = 0):
    """Get historical price snapshots for a specific team."""
    from ...storage.database import DatabaseManager
    
    try:
        db_manager = DatabaseManager("bb_arena_data.db")
        
        with sqlite3.connect(db_manager.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM price_snapshots
                WHERE team_id = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (team_id, limit, offset))
            
            prices = cursor.fetchall()
            
            # Get total count
            cursor = conn.execute("""
                SELECT COUNT(*) FROM price_snapshots
                WHERE team_id = ?
            """, (team_id,))
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
        logger.error(f"Error fetching historical price snapshots for team {team_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/historical", response_model=PriceListResponse)
async def get_all_historical_price_snapshots(limit: int = 50, offset: int = 0):
    """Get historical price snapshots for all teams."""
    from ...storage.database import DatabaseManager
    
    try:
        db_manager = DatabaseManager("bb_arena_data.db")
        
        with sqlite3.connect(db_manager.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM price_snapshots
                ORDER BY created_at DESC
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
        logger.error(f"Error fetching all historical price snapshots: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
