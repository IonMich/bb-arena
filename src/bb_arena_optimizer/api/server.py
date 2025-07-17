"""FastAPI server for serving arena data from the database."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from ..storage.database import DatabaseManager
from .routers import team_league_history, arenas, prices, buzzerbeater, games, teams

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Initialize database manager
db_manager = DatabaseManager("bb_arena_data.db")

# Check if level 1 leagues are populated
def check_level_1_leagues():
    """Check if the level 1 leagues table is populated, and populate it if empty."""
    try:
        import sqlite3
        with sqlite3.connect("bb_arena_data.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM league_hierarchy WHERE league_level = 1")
            count = cursor.fetchone()[0]
            
            if count == 0:
                logger.info("📊 Level 1 leagues table is empty, populating automatically...")
                
                try:
                    # Import and use the existing populate function
                    from ..storage.utils.team_utils import TeamInfoManager
                    team_manager = TeamInfoManager("bb_arena_data.db")
                    
                    # Populate level 1 leagues (limit to 110 countries to be reasonable)
                    results = team_manager.populate_all_level_1_leagues(max_country_id=110)
                    
                    logger.info(f"✅ Successfully populated {results['total_leagues']} level 1 leagues from {results['successful']} countries")
                    if results['failed'] > 0:
                        logger.warning(f"⚠️  Failed to fetch leagues for {results['failed']} countries")
                        
                except Exception as e:
                    logger.error(f"❌ Failed to auto-populate level 1 leagues: {e}")
                    logger.warning("⚠️  League level detection will rely only on regex parsing")
                    logger.info("💡 You can manually run 'python populate_level_1_leagues.py' to populate the data")
            else:
                logger.info(f"✅ Level 1 leagues database populated with {count} leagues")
                
    except Exception as e:
        logger.warning(f"Could not check level 1 leagues table: {e}")

# Check level 1 leagues on startup
check_level_1_leagues()

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

# Include routers
app.include_router(arenas.router)
app.include_router(prices.router)
app.include_router(buzzerbeater.router)
app.include_router(team_league_history.router)
app.include_router(games.router)
app.include_router(teams.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "BB Arena Optimizer API"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "BB Arena Optimizer API"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
