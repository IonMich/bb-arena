"""Team info and league history database operations."""

import sqlite3
from datetime import datetime, UTC as datetime_utc
from pathlib import Path
from typing import Any

from ..models import TeamInfo, LeagueHierarchy, TeamLeagueHistory
from ...utils.logging_config import get_logger

logger = get_logger(__name__)


class TeamInfoManager:
    """Manages team info and league history database operations."""
    
    def __init__(self, db_path: str | Path):
        """Initialize team info manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
    
    # Team Info Management Methods
    
    def save_team_info(self, team_info: TeamInfo) -> None:
        """Save or update team information in the database.
        
        Args:
            team_info: TeamInfo object to save
        """
        with sqlite3.connect(self.db_path) as conn:
            # Use INSERT OR REPLACE to handle updates
            conn.execute("""
                INSERT OR REPLACE INTO team_info (
                    bb_team_id, bb_username, team_name, short_name, owner,
                    league_id, league_name, league_level, country_id, country_name,
                    rival_id, rival_name, create_date, last_synced, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
                         COALESCE((SELECT created_at FROM team_info WHERE bb_username = ?), ?))
            """, (
                team_info.bb_team_id, team_info.bb_username, team_info.team_name,
                team_info.short_name, team_info.owner, team_info.league_id,
                team_info.league_name, team_info.league_level, team_info.country_id,
                team_info.country_name, team_info.rival_id, team_info.rival_name,
                team_info.create_date, team_info.last_synced, team_info.bb_username, team_info.created_at
            ))
            conn.commit()
            logger.info(f"Saved team info for user {team_info.bb_username}")

    def get_team_info_by_username(self, username: str) -> TeamInfo | None:
        """Get cached team information by BuzzerBeater username.
        
        Args:
            username: BuzzerBeater username
            
        Returns:
            TeamInfo object if found, None otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, bb_team_id, bb_username, team_name, short_name, owner,
                       league_id, league_name, league_level, country_id, country_name,
                       rival_id, rival_name, create_date, last_synced, created_at
                FROM team_info 
                WHERE bb_username = ?
            """, (username,))
            
            row = cursor.fetchone()
            if row:
                return TeamInfo(
                    id=row[0],
                    bb_team_id=row[1],
                    bb_username=row[2],
                    team_name=row[3],
                    short_name=row[4],
                    owner=row[5],
                    league_id=row[6],
                    league_name=row[7],
                    league_level=row[8],
                    country_id=row[9],
                    country_name=row[10],
                    rival_id=row[11],
                    rival_name=row[12],
                    create_date=row[13],
                    last_synced=datetime.fromisoformat(row[14]) if row[14] else None,
                    created_at=datetime.fromisoformat(row[15]) if row[15] else None
                )
            return None

    def should_sync_team_info(self, username: str, hours_threshold: int = 24) -> bool:
        """Check if team info should be synced based on last sync time.
        
        Args:
            username: BuzzerBeater username
            hours_threshold: Minimum hours between syncs
            
        Returns:
            True if sync is needed
        """
        team_info = self.get_team_info_by_username(username)
        if not team_info or not team_info.last_synced:
            return True
            
        time_since_sync = datetime.now(datetime_utc) - team_info.last_synced
        return time_since_sync.total_seconds() > (hours_threshold * 3600)

    # League Hierarchy Management Methods
    
    def save_league_hierarchy(self, leagues: list[LeagueHierarchy]) -> None:
        """Save league hierarchy data to database.
        
        Args:
            leagues: List of LeagueHierarchy objects to save
        """
        if not leagues:
            return
            
        with sqlite3.connect(self.db_path) as conn:
            for league in leagues:
                conn.execute("""
                    INSERT OR REPLACE INTO league_hierarchy (
                        country_id, country_name, league_id, league_name, league_level, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    league.country_id,
                    league.country_name,
                    league.league_id,
                    league.league_name,
                    league.league_level,
                    league.created_at.isoformat() if league.created_at else datetime.now(datetime_utc).isoformat()
                ))
            conn.commit()
            logger.info(f"Saved {len(leagues)} league hierarchy entries to database")

    def get_league_hierarchy_by_country(self, country_id: int) -> list[LeagueHierarchy]:
        """Get league hierarchy for a specific country.
        
        Args:
            country_id: Country ID to query
            
        Returns:
            List of LeagueHierarchy objects for the country
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT country_id, country_name, league_id, league_name, league_level, created_at
                FROM league_hierarchy 
                WHERE country_id = ?
                ORDER BY league_level, league_name
            """, (country_id,))
            
            leagues = []
            for row in cursor.fetchall():
                leagues.append(LeagueHierarchy(
                    country_id=row[0],
                    country_name=row[1],
                    league_id=row[2],
                    league_name=row[3],
                    league_level=row[4],
                    created_at=datetime.fromisoformat(row[5]) if row[5] else None
                ))
            
            return leagues

    def get_league_level(self, league_id: int) -> int | None:
        """Get the level for a specific league ID.
        
        Args:
            league_id: League ID to query
            
        Returns:
            League level (1 for I, 2 for II, etc.) or None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT league_level
                FROM league_hierarchy 
                WHERE league_id = ?
                LIMIT 1
            """, (league_id,))
            
            row = cursor.fetchone()
            return row[0] if row else None

    def populate_league_hierarchy_for_countries(self, country_ids: list[int]) -> None:
        """Populate league hierarchy for multiple countries by fetching level 1 leagues.
        
        Args:
            country_ids: List of country IDs to fetch leagues for
        """
        from ...api.client import BuzzerBeaterAPI
        
        api_client = BuzzerBeaterAPI()
        all_leagues = []
        
        for country_id in country_ids:
            try:
                # Fetch level 1 leagues for this country
                leagues_data = api_client.get_leagues(country_id=country_id, max_level=1)
                
                if leagues_data and 'leagues' in leagues_data:
                    for league_data in leagues_data['leagues']:
                        league = LeagueHierarchy(
                            country_id=country_id,
                            country_name=league_data.get('country', f'Country {country_id}'),
                            league_id=int(league_data['id']),
                            league_name=league_data['name'],
                            league_level=1,  # We're only fetching level 1
                            created_at=datetime.now(datetime_utc)
                        )
                        all_leagues.append(league)
                        
                logger.info(f"Fetched {len(leagues_data.get('leagues', []))} level 1 leagues for country {country_id}")
                        
            except Exception as e:
                logger.warning(f"Failed to fetch leagues for country {country_id}: {e}")
                continue
        
        if all_leagues:
            self.save_league_hierarchy(all_leagues)
            logger.info(f"Populated league hierarchy with {len(all_leagues)} leagues from {len(country_ids)} countries")

    def populate_all_level_1_leagues(self, max_country_id: int = 110) -> dict:
        """Populate league hierarchy with all level 1 leagues from all countries.
        
        Args:
            max_country_id: Maximum country ID to check (default 110)
            
        Returns:
            Dictionary with results: {'successful': int, 'failed': int, 'total_leagues': int}
        """
        import os
        from dotenv import load_dotenv
        from ...api.client import BuzzerBeaterAPI
        
        # Load environment variables for API access
        load_dotenv()
        username = os.getenv('BB_USERNAME')
        security_code = os.getenv('BB_SECURITY_CODE')
        
        if not username or not security_code:
            logger.error("BB_USERNAME and BB_SECURITY_CODE must be set in .env file")
            return {'successful': 0, 'failed': max_country_id, 'total_leagues': 0}
        
        api_client = BuzzerBeaterAPI(username, security_code)
        
        # Login to the API
        if not api_client.login():
            logger.error("Failed to authenticate with BuzzerBeater API")
            return {'successful': 0, 'failed': max_country_id, 'total_leagues': 0}
        
        results = {'successful': 0, 'failed': 0, 'total_leagues': 0}
        all_leagues = []
        
        logger.info(f"Starting bulk collection of level 1 leagues")
        
        # First, get all countries
        logger.info("Fetching countries from API...")
        countries = api_client.get_countries()
        
        if not countries:
            logger.error("Failed to fetch countries")
            return results
        
        # Filter countries by max_country_id
        filtered_countries = [c for c in countries if c['id'] <= max_country_id]
        logger.info(f"Processing {len(filtered_countries)} countries (filtered from {len(countries)} total)")
        
        for country in filtered_countries:
            country_id = country['id']
            country_name = country['name']
            
            try:
                params = {"countryid": country_id, "level": 1}
                root = api_client._make_request("leagues.aspx", params)
                
                if root is None:
                    logger.debug(f"No response for country {country_id} ({country_name})")
                    results['failed'] += 1
                    continue
                
                # Look for league elements
                league_elements = root.findall(".//league")
                
                if not league_elements:
                    logger.debug(f"No level 1 league found for country {country_id} ({country_name})")
                    results['failed'] += 1
                    continue
                
                # Process each league (should typically be just one for level 1)
                country_leagues_count = 0
                for league_elem in league_elements:
                    league_id = league_elem.get("id")
                    league_name = league_elem.text.strip() if league_elem.text else None
                    
                    if league_id and league_name:
                        league = LeagueHierarchy(
                            country_id=country_id,
                            country_name=country_name,
                            league_id=int(league_id),
                            league_name=league_name,
                            league_level=1,
                            created_at=datetime.now(datetime_utc)
                        )
                        all_leagues.append(league)
                        country_leagues_count += 1
                        results['total_leagues'] += 1
                
                if country_leagues_count > 0:
                    logger.debug(f"Found {country_leagues_count} level 1 league(s) for {country_name}")
                    results['successful'] += 1
                else:
                    results['failed'] += 1
                        
            except Exception as e:
                logger.warning(f"Failed to fetch level 1 league for country {country_id}: {e}")
                results['failed'] += 1
                continue
        
        if all_leagues:
            self.save_league_hierarchy(all_leagues)
            logger.info(f"Successfully populated league hierarchy with {len(all_leagues)} level 1 leagues from {results['successful']} countries")
        
        return results

    def is_league_level_1(self, league_id: int) -> bool:
        """Check if a league ID corresponds to a level 1 league.
        
        Args:
            league_id: League ID to check
            
        Returns:
            True if the league is level 1, False otherwise
        """
        if not league_id:
            return False
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT league_level
                    FROM league_hierarchy 
                    WHERE league_id = ? AND league_level = 1
                    LIMIT 1
                """, (league_id,))
                
                result = cursor.fetchone()
                return result is not None
        except Exception as e:
            logger.error(f"Error checking if league {league_id} is level 1: {e}")
            return False

    # Team League History Management Methods
    
    def save_team_league_history(self, team_id: int, history_entries: list[TeamLeagueHistory]) -> None:
        """Save team league history to database.
        
        Args:
            team_id: Team ID
            history_entries: List of TeamLeagueHistory objects
        """
        if not history_entries:
            return
            
        with sqlite3.connect(self.db_path) as conn:
            for entry in history_entries:
                conn.execute("""
                    INSERT OR REPLACE INTO team_league_history (
                        team_id, season, team_name, league_id, league_name, 
                        league_level, achievement, is_active_team, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    team_id,
                    entry.season,
                    entry.team_name,
                    entry.league_id,
                    entry.league_name,
                    entry.league_level,
                    entry.achievement,
                    entry.is_active_team,
                    entry.created_at.isoformat() if entry.created_at else datetime.now(datetime_utc).isoformat()
                ))
            conn.commit()
            logger.info(f"Saved {len(history_entries)} league history entries for team {team_id}")

    def get_team_league_history(self, team_id: int, active_only: bool = True) -> list[TeamLeagueHistory]:
        """Get team league history from database.
        
        Args:
            team_id: Team ID to query
            active_only: If True, only return active team entries (not predecessors)
            
        Returns:
            List of TeamLeagueHistory objects ordered by season descending
        """
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT team_id, season, team_name, league_id, league_name, 
                       league_level, achievement, is_active_team, created_at
                FROM team_league_history 
                WHERE team_id = ?
            """
            params = [team_id]
            
            if active_only:
                query += " AND is_active_team = 1"
                
            query += " ORDER BY season DESC"
            
            cursor = conn.execute(query, params)
            
            history = []
            for row in cursor.fetchall():
                history.append(TeamLeagueHistory(
                    bb_team_id=str(row[0]),
                    season=row[1],
                    team_name=row[2],
                    league_id=row[3],
                    league_name=row[4],
                    league_level=row[5],
                    achievement=row[6],
                    is_active_team=bool(row[7]),
                    created_at=datetime.fromisoformat(row[8]) if row[8] else None
                ))
            
            return history

    def get_team_current_league_info(self, team_id: int) -> dict | None:
        """Get the current league information for a team from team_info table.
        
        Args:
            team_id: Team ID to query
            
        Returns:
            Dictionary with league_id, league_name, league_level, team_name, last_synced 
            for the current season from team_info, or None if no info found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT league_id, league_name, league_level, team_name, last_synced, country_name
                    FROM team_info 
                    WHERE bb_team_id = ?
                """, (str(team_id),))
                
                result = cursor.fetchone()
                if result:
                    league_id, league_name, league_level, team_name, last_synced, country_name = result
                    
                    # Format league name to match historical data format (country + league name)
                    formatted_league_name = league_name
                    if country_name and league_name and not league_name.startswith(country_name):
                        formatted_league_name = f"{country_name} {league_name}"
                    
                    return {
                        'league_id': league_id,
                        'league_name': formatted_league_name,
                        'league_level': league_level,
                        'team_name': team_name,
                        'last_synced': last_synced
                    }
                return None
        except Exception as e:
            logger.error(f"Error getting current league info for team {team_id}: {e}")
            return None

    def collect_team_history_from_webpage(self, team_id: int) -> bool:
        """Collect and save team league history from BuzzerBeater webpage.
        
        Args:
            team_id: Team ID to collect history for
            
        Returns:
            True if successful, False otherwise
        """
        try:
            import os
            from dotenv import load_dotenv
            from ...api.client import BuzzerBeaterAPI
            from ..models import TeamLeagueHistory
            
            # Load environment variables
            load_dotenv()
            username = os.getenv('BB_USERNAME')
            security_code = os.getenv('BB_SECURITY_CODE')
            
            if not username or not security_code:
                logger.error("BB_USERNAME and BB_SECURITY_CODE must be set in .env file")
                return False
            
            api_client = BuzzerBeaterAPI(username, security_code)
            history_data = api_client.get_team_history_from_webpage(team_id)
            
            if history_data:
                # Convert dictionary data to TeamLeagueHistory objects
                history_entries = []
                for entry_dict in history_data:
                    history_entry = TeamLeagueHistory.from_webpage_data(
                        team_id=str(team_id),
                        season=entry_dict['season'],
                        team_name=entry_dict['team_name'],
                        league_id=entry_dict['league_id'],
                        league_name=entry_dict['league_name'],
                        league_level=entry_dict['league_level'],
                        achievement=entry_dict.get('achievement'),
                        is_active_team=entry_dict.get('is_active_team', True)
                    )
                    history_entries.append(history_entry)
                
                self.save_team_league_history(team_id, history_entries)
                logger.info(f"Successfully collected and saved {len(history_entries)} history entries for team {team_id}")
                return True
            else:
                logger.warning(f"No history entries found for team {team_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to collect team history for team {team_id}: {e}")
            return False

    def bulk_collect_team_histories(self, team_ids: list[int]) -> dict:
        """Collect team histories for multiple teams in bulk.
        
        Args:
            team_ids: List of team IDs to collect histories for
            
        Returns:
            Dictionary with results: {'successful': int, 'failed': int, 'details': list}
        """
        results = {'successful': 0, 'failed': 0, 'details': []}
        
        for team_id in team_ids:
            try:
                success = self.collect_team_history_from_webpage(team_id)
                if success:
                    results['successful'] += 1
                    results['details'].append({'team_id': team_id, 'status': 'success'})
                else:
                    results['failed'] += 1
                    results['details'].append({'team_id': team_id, 'status': 'failed', 'reason': 'no_data'})
                    
            except Exception as e:
                results['failed'] += 1
                results['details'].append({'team_id': team_id, 'status': 'failed', 'reason': str(e)})
                
        logger.info(f"Bulk collection completed: {results['successful']} successful, {results['failed']} failed")
        return results
