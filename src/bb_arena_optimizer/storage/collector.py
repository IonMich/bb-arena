"""Data collection service for gathering and storing BuzzerBeater data."""

import logging

from ..api.client import BuzzerBeaterAPI
from .database import DatabaseManager
from .models import ArenaSnapshot, PriceSnapshot

logger = logging.getLogger(__name__)


class DataCollectionService:
    """Service for collecting data from API and storing in database."""

    def __init__(self, db_manager: DatabaseManager):
        """Initialize data collection service.

        Args:
            db_manager: Database manager instance
        """
        self.db_manager = db_manager

    def collect_arena_data(
        self, api: BuzzerBeaterAPI, team_id: str | None = None
    ) -> bool:
        """Collect current arena information and store it.

        Args:
            api: Authenticated BuzzerBeater API client
            team_id: Optional team ID (defaults to current user's team)

        Returns:
            True if data was collected successfully, False otherwise
        """
        try:
            logger.info(f"Collecting arena data for team {team_id or 'current'}")

            # Get arena info from API
            team_id_int = int(team_id) if team_id else None
            arena_data = api.get_arena_info(team_id_int)
            if not arena_data:
                logger.error("Failed to get arena data from API")
                return False

            # Store arena snapshot
            arena_snapshot = ArenaSnapshot.from_api_data(arena_data)
            arena_id = self.db_manager.save_arena_snapshot(arena_snapshot)
            logger.info(f"Saved arena snapshot with ID {arena_id}")

            # Store current pricing snapshot
            price_snapshot = PriceSnapshot.from_api_data(
                arena_data, team_id=arena_data.get("team_id")
            )
            price_id = self.db_manager.save_price_snapshot(price_snapshot)
            logger.info(f"Saved price snapshot with ID {price_id}")

            return True

        except Exception as e:
            logger.error(f"Error collecting arena data: {e}")
            return False
