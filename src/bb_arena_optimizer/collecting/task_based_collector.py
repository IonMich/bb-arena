"""
Task-based data collection system for BuzzerBeater arena data.

This module implements a DAG-based approach where each task has clear inputs/outputs
and can be executed independently with proper dependency management.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Set, Optional, Any, Tuple
from dataclasses import dataclass
import json
from pathlib import Path

from ..api.client import BuzzerBeaterAPI
from ..storage.database import DatabaseManager
from ..storage.collector import DataCollectionService

logger = logging.getLogger(__name__)


@dataclass
class TaskResult:
    """Result of a task execution."""
    task_name: str
    success: bool
    data: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    items_processed: int = 0
    

@dataclass
class RateLimitConfig:
    """Configuration for API rate limiting."""
    requests_per_minute: int = 25
    min_delay_between_requests: float = 2.5
    max_delay_between_requests: float = 4.0
    
    
class TaskBasedCollector:
    """
    Task-based data collector that executes data collection as a DAG of tasks.
    
    Each task has clear inputs/outputs and can be executed independently.
    """
    
    def __init__(
        self,
        api: BuzzerBeaterAPI,
        db_manager: DatabaseManager,
        rate_config: Optional[RateLimitConfig] = None
    ):
        self.api = api
        self.db_manager = db_manager
        self.collector = DataCollectionService(db_manager)
        self.rate_config = rate_config or RateLimitConfig()
        
        # State tracking
        self.last_request_time = 0.0
        self.request_count = 0
        
    async def task_1_collect_team_ids(
        self,
        countries: List[int],
        seasons: List[int],
        max_league_level: int = 3
    ) -> TaskResult:
        """
        Task 1: Collect all team_ids that participated in specified seasons 
        in any of the top leagues in specified countries.
        
        Args:
            countries: List of country IDs to collect from
            seasons: List of season numbers to collect (e.g., [68, 69])
            max_league_level: Maximum league level to include (1=top, 2=second, 3=third)
            
        Returns:
            TaskResult with data containing set of team_ids
        """
        start_time = time.time()
        task_name = f"collect_team_ids_seasons_{'-'.join(map(str, seasons))}"
        
        logger.info(f"🎯 Task 1: Collecting team IDs from seasons {seasons}")
        logger.info(f"   - Countries: {countries}")
        logger.info(f"   - League levels: 1-{max_league_level}")
        
        try:
            all_team_ids: Set[int] = set()
            leagues_processed = 0
            
            for country_id in countries:
                logger.info(f"🌍 Processing country {country_id}")
                
                # Get all leagues for this country (levels 1-3)
                leagues = self.api.get_leagues(country_id, max_league_level)
                
                if not leagues:
                    logger.warning(f"No leagues found for country {country_id}")
                    continue
                
                logger.info(f"   Found {len(leagues)} leagues")
                
                # Process each league
                for league in leagues:
                    league_id = league["id"]
                    league_name = league["name"]
                    league_level = league["level"]
                    
                    logger.info(f"   📊 Processing {league_name} (ID: {league_id}, Level: {league_level})")
                    
                    # Get standings for each specified season
                    for season in seasons:
                        try:
                            logger.debug(f"      Getting standings for season {season}")
                            standings = self.api.get_league_standings(league_id, season)
                            
                            if not standings or "teams" not in standings:
                                logger.warning(f"      No standings found for league {league_id}, season {season}")
                                continue
                            
                            teams = standings["teams"]
                            season_team_ids = set()
                            
                            for team in teams:
                                team_id_str = team.get("id")
                                if team_id_str:
                                    try:
                                        team_id = int(team_id_str)
                                        all_team_ids.add(team_id)
                                        season_team_ids.add(team_id)
                                    except ValueError:
                                        logger.warning(f"Invalid team ID: {team_id_str}")
                            
                            logger.info(f"      ✅ Season {season}: {len(season_team_ids)} teams")
                            
                            # Rate limiting
                            await self._respect_rate_limits()
                            
                        except Exception as e:
                            logger.error(f"      ❌ Error getting standings for league {league_id}, season {season}: {e}")
                            continue
                    
                    leagues_processed += 1
                    
                    # Progress update
                    if leagues_processed % 10 == 0:
                        logger.info(f"   📈 Processed {leagues_processed} leagues, found {len(all_team_ids)} unique teams so far")
            
            execution_time = time.time() - start_time
            
            logger.info(f"✅ Task 1 completed!")
            logger.info(f"   - Processed {leagues_processed} leagues")
            logger.info(f"   - Found {len(all_team_ids)} unique teams")
            logger.info(f"   - Execution time: {execution_time:.1f}s")
            
            return TaskResult(
                task_name=task_name,
                success=True,
                data=all_team_ids,
                execution_time=execution_time,
                items_processed=len(all_team_ids)
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"❌ Task 1 failed: {e}")
            
            return TaskResult(
                task_name=task_name,
                success=False,
                error=str(e),
                execution_time=execution_time
            )
    
    async def task_2_collect_team_info(self, team_ids: Set[int]) -> TaskResult:
        """
        Task 2: Collect team_info for all specified teams.
        
        Args:
            team_ids: Set of team IDs to collect info for
            
        Returns:
            TaskResult with summary of collection
        """
        start_time = time.time()
        task_name = "collect_team_info"
        
        logger.info(f"📋 Task 2: Collecting team info for {len(team_ids)} teams")
        
        try:
            successful_collections = 0
            failed_collections = 0
            failed_teams = []
            
            for i, team_id in enumerate(team_ids, 1):
                logger.debug(f"[{i}/{len(team_ids)}] Collecting team info for team {team_id}")
                
                try:
                    # Get team info from API
                    team_data = self.api.get_team_info(team_id)
                    
                    if team_data:
                        # Create TeamInfo object and store in database
                        from ..storage.models import TeamInfo
                        
                        # Use a generic username for mass collection (could be improved)
                        username = f"fetched_for_{team_id}"
                        team_info = TeamInfo.from_api_data(team_data, username)
                        
                        # Store in database
                        self.db_manager.save_team_info(team_info)
                        
                        logger.debug(f"✅ Saved team info for {team_id}: {team_data.get('name', 'Unknown')}")
                        successful_collections += 1
                    else:
                        logger.warning(f"❌ No team info returned for team {team_id}")
                        failed_collections += 1
                        failed_teams.append(team_id)
                    
                    # Rate limiting
                    await self._respect_rate_limits()
                    
                except Exception as e:
                    logger.error(f"❌ Error collecting team info for team {team_id}: {e}")
                    failed_collections += 1
                    failed_teams.append(team_id)
                
                # Progress updates
                if i % 25 == 0:
                    progress = i / len(team_ids)
                    logger.info(f"   📈 Progress: {progress:.1%} ({i}/{len(team_ids)}) - "
                               f"Success: {successful_collections}, Failed: {failed_collections}")
            
            execution_time = time.time() - start_time
            success_rate = successful_collections / len(team_ids) if team_ids else 0
            
            logger.info(f"✅ Task 2 completed!")
            logger.info(f"   - Successful: {successful_collections}/{len(team_ids)} ({success_rate:.1%})")
            logger.info(f"   - Failed: {failed_collections}")
            logger.info(f"   - Execution time: {execution_time:.1f}s")
            
            if failed_teams:
                logger.warning(f"   Failed team IDs: {failed_teams[:10]}{'...' if len(failed_teams) > 10 else ''}")
            
            return TaskResult(
                task_name=task_name,
                success=success_rate > 0.8,  # Consider success if >80% successful
                data={
                    "successful": successful_collections,
                    "failed": failed_collections,
                    "failed_teams": failed_teams,
                    "success_rate": success_rate
                },
                execution_time=execution_time,
                items_processed=successful_collections
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"❌ Task 2 failed: {e}")
            
            return TaskResult(
                task_name=task_name,
                success=False,
                error=str(e),
                execution_time=execution_time
            )
    
    async def task_3_collect_arena_snapshots(self, team_ids: Set[int]) -> TaskResult:
        """
        Task 3: Collect arena snapshots and price snapshots for all specified teams.
        
        Args:
            team_ids: Set of team IDs to collect arena data for
            
        Returns:
            TaskResult with summary of collection
        """
        start_time = time.time()
        task_name = "collect_arena_snapshots"
        
        logger.info(f"🏟️ Task 3: Collecting arena snapshots for {len(team_ids)} teams")
        
        try:
            successful_collections = 0
            failed_collections = 0
            failed_teams = []
            
            for i, team_id in enumerate(team_ids, 1):
                logger.debug(f"[{i}/{len(team_ids)}] Collecting arena data for team {team_id}")
                
                try:
                    # Use the existing arena data collection method
                    success = self.collector.collect_arena_data(self.api, str(team_id))
                    
                    if success:
                        logger.debug(f"✅ Collected arena data for team {team_id}")
                        successful_collections += 1
                    else:
                        logger.warning(f"❌ Failed to collect arena data for team {team_id}")
                        failed_collections += 1
                        failed_teams.append(team_id)
                    
                    # Rate limiting
                    await self._respect_rate_limits()
                    
                except Exception as e:
                    logger.error(f"❌ Error collecting arena data for team {team_id}: {e}")
                    failed_collections += 1
                    failed_teams.append(team_id)
                
                # Progress updates
                if i % 25 == 0:
                    progress = i / len(team_ids)
                    logger.info(f"   📈 Progress: {progress:.1%} ({i}/{len(team_ids)}) - "
                               f"Success: {successful_collections}, Failed: {failed_collections}")
            
            execution_time = time.time() - start_time
            success_rate = successful_collections / len(team_ids) if team_ids else 0
            
            logger.info(f"✅ Task 3 completed!")
            logger.info(f"   - Successful: {successful_collections}/{len(team_ids)} ({success_rate:.1%})")
            logger.info(f"   - Failed: {failed_collections}")
            logger.info(f"   - Execution time: {execution_time:.1f}s")
            
            if failed_teams:
                logger.warning(f"   Failed team IDs: {failed_teams[:10]}{'...' if len(failed_teams) > 10 else ''}")
            
            return TaskResult(
                task_name=task_name,
                success=success_rate > 0.8,  # Consider success if >80% successful
                data={
                    "successful": successful_collections,
                    "failed": failed_collections,
                    "failed_teams": failed_teams,
                    "success_rate": success_rate
                },
                execution_time=execution_time,
                items_processed=successful_collections
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"❌ Task 3 failed: {e}")
            
            return TaskResult(
                task_name=task_name,
                success=False,
                error=str(e),
                execution_time=execution_time
            )
    
    async def task_5_collect_home_games(
        self, 
        team_ids: Set[int], 
        seasons: List[int],
        max_teams_parallel: int = 3
    ) -> TaskResult:
        """
        Task 5: Collect home games for all specified teams and seasons.
        
        Args:
            team_ids: Set of team IDs to collect games for
            seasons: List of season numbers to collect games for (e.g., [68, 69])
            max_teams_parallel: Maximum number of teams to process in parallel
            
        Returns:
            TaskResult with summary of collection
        """
        start_time = time.time()
        task_name = "collect_home_games"
        
        logger.info(f"🏈 Task 5: Collecting home games for {len(team_ids)} teams, seasons {seasons}")
        logger.info(f"   - Max teams in parallel: {max_teams_parallel}")
        
        try:
            total_games_collected = 0
            total_games_skipped = 0
            failed_teams = []
            
            # Convert team_ids to list for batching
            team_list = list(team_ids)
            
            # Process teams in batches for controlled parallelization
            for batch_start in range(0, len(team_list), max_teams_parallel):
                batch_end = min(batch_start + max_teams_parallel, len(team_list))
                batch_teams = team_list[batch_start:batch_end]
                
                logger.info(f"   📦 Processing batch {batch_start//max_teams_parallel + 1}: teams {batch_teams}")
                
                # Create tasks for this batch
                batch_tasks = []
                for team_id in batch_teams:
                    task = self._collect_team_games_for_seasons(team_id, seasons)
                    batch_tasks.append(task)
                
                # Run batch in parallel
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                # Process batch results
                for i, result in enumerate(batch_results):
                    team_id = batch_teams[i]
                    
                    if isinstance(result, Exception):
                        logger.error(f"❌ Team {team_id} failed: {result}")
                        failed_teams.append(team_id)
                    else:
                        games_collected, games_skipped = result
                        total_games_collected += games_collected
                        total_games_skipped += games_skipped
                        logger.debug(f"✅ Team {team_id}: {games_collected} collected, {games_skipped} skipped")
                
                # Brief pause between batches to respect rate limits
                if batch_end < len(team_list):
                    logger.debug(f"   ⏸️ Pause between batches...")
                    await asyncio.sleep(2.0)
            
            execution_time = time.time() - start_time
            successful_teams = len(team_ids) - len(failed_teams)
            success_rate = successful_teams / len(team_ids) if team_ids else 0
            
            logger.info(f"✅ Task 5 completed!")
            logger.info(f"   - Successful teams: {successful_teams}/{len(team_ids)} ({success_rate:.1%})")
            logger.info(f"   - Total games collected: {total_games_collected}")
            logger.info(f"   - Total games skipped (already stored): {total_games_skipped}")
            logger.info(f"   - Failed teams: {len(failed_teams)}")
            logger.info(f"   - Execution time: {execution_time:.1f}s")
            
            if failed_teams:
                logger.warning(f"   Failed team IDs: {failed_teams[:10]}{'...' if len(failed_teams) > 10 else ''}")
            
            return TaskResult(
                task_name=task_name,
                success=success_rate > 0.8,  # Consider success if >80% successful
                data={
                    "successful_teams": successful_teams,
                    "failed_teams": len(failed_teams),
                    "failed_team_ids": failed_teams,
                    "success_rate": success_rate,
                    "total_games_collected": total_games_collected,
                    "total_games_skipped": total_games_skipped,
                    "seasons": seasons
                },
                execution_time=execution_time,
                items_processed=total_games_collected
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"❌ Task 5 failed: {e}")
            
            return TaskResult(
                task_name=task_name,
                success=False,
                error=str(e),
                execution_time=execution_time
            )
    
    async def _collect_team_games_for_seasons(self, team_id: int, seasons: List[int]) -> Tuple[int, int]:
        """
        Helper method to collect home games for one team across multiple seasons.
        
        Args:
            team_id: Team ID to collect games for
            seasons: List of seasons to collect
            
        Returns:
            Tuple of (games_collected, games_skipped)
        """
        total_collected = 0
        total_skipped = 0
        
        for season in seasons:
            try:
                # Get team schedule for this season
                schedule_data = self.api.get_schedule(team_id, season)
                
                if not schedule_data or 'games' not in schedule_data:
                    logger.warning(f"No schedule data for team {team_id}, season {season}")
                    continue
                
                # Debug: log first game to see available fields
                if schedule_data['games']:
                    first_game = schedule_data['games'][0]
                    logger.info(f"🔍 Sample game data for team {team_id}, season {season}: {first_game}")
                    
                    # Debug: show home vs away game breakdown
                    total_games = len(schedule_data['games'])
                    home_games_count = sum(1 for g in schedule_data['games'] if g.get('home'))
                    away_games_count = total_games - home_games_count
                    logger.info(f"🏠 Team {team_id} season {season}: {total_games} total games ({home_games_count} home, {away_games_count} away)")
                else:
                    logger.info(f"⚠️ No games found in schedule for team {team_id}, season {season}")
                
                # Filter for completed home games only (exclude neutral games and future games)
                home_games = []
                for game in schedule_data['games']:
                    # Only process home games (where this team is the home team)
                    if not game.get('home'):
                        continue  # Skip away games entirely
                    
                    # Skip neutral and BBM games  
                    if game.get('type') in ['bbm', 'pl.rsneutral']:
                        continue
                    
                    # Must have a game ID
                    if not game.get('id'):
                        continue
                    
                    # Must be a completed game
                    if not self._is_game_completed(game, season):
                        continue
                    
                    home_games.append(game)
                
                logger.info(f"🏀 Team {team_id} season {season}: {len(home_games)} completed home games found")
                
                # Check which games are already stored with attendance data
                existing_games = self.db_manager.get_games_for_team(str(team_id))
                games_with_attendance = {
                    game.game_id for game in existing_games 
                    if game.total_attendance is not None
                }
                
                # Filter to games that need collection (not stored OR missing attendance data)
                games_to_collect = [
                    game for game in home_games 
                    if game['id'] not in games_with_attendance
                ]
                
                logger.info(f"📥 Team {team_id} season {season}: {len(games_to_collect)} new games to collect ({len(home_games) - len(games_to_collect)} already stored)")
                
                # Collect each game using the same pattern as frontend "Collect remaining"
                season_collected = 0
                if games_to_collect:
                    logger.info(f"🎯 Team {team_id} season {season}: Starting collection of {len(games_to_collect)} games...")
                
                for i, game in enumerate(games_to_collect, 1):
                    try:
                        # Progress update every 5 games or for the last game
                        if i % 5 == 0 or i == len(games_to_collect):
                            logger.info(f"   🏈 Team {team_id}: Collecting game {i}/{len(games_to_collect)} (ID: {game['id']})")
                        
                        # Use the same game collection pattern as the backend API endpoint
                        success = await self._collect_single_game(game['id'])
                        
                        if success:
                            season_collected += 1
                            if i % 5 == 0 or i == len(games_to_collect):
                                logger.info(f"   ✅ Team {team_id}: {season_collected}/{i} games collected successfully")
                        else:
                            logger.warning(f"   ❌ Team {team_id}: Failed to collect game {game['id']}")
                        
                        # Rate limiting between individual games
                        await self._respect_rate_limits()
                        
                    except Exception as e:
                        logger.error(f"   💥 Team {team_id}: Error collecting game {game['id']}: {e}")
                        continue
                
                total_collected += season_collected
                total_skipped += len(home_games) - len(games_to_collect)
                
                # Summary for this season
                if games_to_collect:
                    success_rate = season_collected / len(games_to_collect) if games_to_collect else 0
                    logger.info(f"🏁 Team {team_id} season {season}: Completed! {season_collected}/{len(games_to_collect)} games collected ({success_rate:.1%})")
                
                # Extra delay between seasons for the same team
                if len(seasons) > 1:
                    await asyncio.sleep(1.0)
                    
            except Exception as e:
                logger.error(f"Error collecting season {season} for team {team_id}: {e}")
                continue
        
        return total_collected, total_skipped
    
    async def task_6_update_game_pricing(self, team_ids: Set[int]) -> TaskResult:
        """
        Task 6: Update game pricing from arena webpage for all teams.
        
        This task depends on Task 5 completing successfully and having games in the database.
        No parallelization - processes teams sequentially to avoid overwhelming the server.
        
        Args:
            team_ids: Set of team IDs to update pricing for
            
        Returns:
            TaskResult with summary of pricing updates
        """
        start_time = time.time()
        task_name = "update_game_pricing"
        
        logger.info(f"💰 Task 6: Updating game pricing for {len(team_ids)} teams")
        logger.info(f"   - Processing teams sequentially (no parallelization)")
        
        try:
            total_periods_created = 0
            total_games_updated = 0
            successful_teams = 0
            failed_teams = []
            
            for i, team_id in enumerate(sorted(team_ids), 1):
                logger.info(f"💰 Team {i}/{len(team_ids)}: Updating pricing for team {team_id}")
                
                try:
                    # Call the core pricing update logic
                    periods_created, games_updated = await self._update_team_pricing(team_id)
                    
                    total_periods_created += periods_created
                    total_games_updated += games_updated
                    successful_teams += 1
                    
                    logger.info(f"✅ Team {team_id}: {periods_created} periods created, {games_updated} games updated")
                    
                    # Rate limiting between teams
                    await self._respect_rate_limits()
                    
                except Exception as e:
                    logger.error(f"❌ Team {team_id}: Error updating pricing: {e}")
                    failed_teams.append(team_id)
                    continue
            
            execution_time = time.time() - start_time
            success_rate = successful_teams / len(team_ids) if team_ids else 0
            
            logger.info(f"✅ Task 6 completed!")
            logger.info(f"   - Successful teams: {successful_teams}/{len(team_ids)} ({success_rate:.1%})")
            logger.info(f"   - Total periods created: {total_periods_created}")
            logger.info(f"   - Total games updated: {total_games_updated}")
            logger.info(f"   - Failed teams: {len(failed_teams)}")
            logger.info(f"   - Execution time: {execution_time:.1f}s")
            
            if failed_teams:
                logger.warning(f"   Failed team IDs: {failed_teams[:10]}{'...' if len(failed_teams) > 10 else ''}")
            
            return TaskResult(
                task_name=task_name,
                success=success_rate > 0.8,  # Consider success if >80% successful
                data={
                    "successful_teams": successful_teams,
                    "failed_teams": len(failed_teams),
                    "failed_team_ids": failed_teams,
                    "success_rate": success_rate,
                    "total_periods_created": total_periods_created,
                    "total_games_updated": total_games_updated
                },
                execution_time=execution_time,
                items_processed=total_games_updated
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"❌ Task 6 failed: {e}")
            
            return TaskResult(
                task_name=task_name,
                success=False,
                error=str(e),
                execution_time=execution_time
            )
    
    async def _update_team_pricing(self, team_id: int) -> Tuple[int, int]:
        """Update pricing for a single team using the existing collecting logic.
        
        Args:
            team_id: Team ID to update pricing for
            
        Returns:
            Tuple of (periods_created, games_updated)
        """
        try:
            from ..api.routers.collecting import ArenaUpdateRequest, update_pricing_from_arena_webpage
            
            # Create request object as expected by the function
            request = ArenaUpdateRequest(team_id=team_id)
            
            # Call the existing function
            response = await update_pricing_from_arena_webpage(request)
            
            return response.periods_created, response.games_updated
            
        except Exception as e:
            logger.error(f"Error updating pricing for team {team_id}: {e}")
            raise
    
    def _is_game_completed(self, game: dict, season: int) -> bool:
        """
        Check if a game is completed by looking for scores in the schedule data.
        
        Args:
            game: Game data from schedule API
            season: Season number being processed
            
        Returns:
            True if game has been played (has scores), False if future game
        """
        # The schedule parser currently sets scores to None, but let's check if the raw data has them
        # First, try the parsed fields (though they're currently always None)
        home_score = game.get('score_home')
        away_score = game.get('score_away')
        
        # Game is completed if both scores are present and are numbers
        if (home_score is not None and away_score is not None and
            isinstance(home_score, (int, float)) and isinstance(away_score, (int, float))):
            return True
        
        # If the parser didn't extract scores, check other possible score fields
        # that might be in the game data
        for score_field in ['home_score', 'away_score', 'score', 'scores']:
            if score_field in game and game[score_field] is not None:
                return True
        
        # Check if there's a 'completed' or 'finished' flag
        if game.get('completed') or game.get('finished') or game.get('played'):
            return True
        
        # For completed historical seasons, all games should be finished
        # Since the schedule parser doesn't extract scores, but we know historical games are completed
        if season <= 68:  # Completed historical seasons
            logger.debug(f"Game {game.get('id')} is from completed season {season} - assuming completed")
            return True
        
        # For current/future seasons, we need proper score detection
        # For debugging: log what fields are available (only for first few games)
        if not hasattr(self, '_debug_logged'):
            self._debug_logged = True
            logger.info(f"🔍 Game {game.get('id', 'unknown')} fields: {list(game.keys())}")
            logger.info(f"🔍 Game {game.get('id', 'unknown')} data: {game}")
        
        # If no score indicators found, assume it's a future game
        return False
    
    async def _collect_single_game(self, game_id: str) -> bool:
        """
        Collect a single game using the same pattern as the backend API endpoint.
        
        Args:
            game_id: Game ID to collect
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if we already have this game with attendance data
            stored_game = self.db_manager.get_game_by_id(game_id)
            if stored_game and stored_game.total_attendance is not None:
                logger.debug(f"Game {game_id} already has attendance data, skipping")
                return True
            
            # Fetch boxscore data from API
            boxscore_data = self.api.get_boxscore(game_id)
            if not boxscore_data:
                logger.warning(f"No boxscore data returned for game {game_id}")
                return False
            
            # Extract required data (same logic as backend API endpoint)
            attendance_data = boxscore_data.get("attendance")
            home_team_id = boxscore_data.get("home_team_id")
            away_team_id = boxscore_data.get("away_team_id")
            
            # Validate required fields
            if (attendance_data and 
                home_team_id is not None and 
                away_team_id is not None and 
                isinstance(home_team_id, int) and home_team_id > 0 and
                isinstance(away_team_id, int) and away_team_id > 0):
                
                # BBAPI never provides season, so always calculate it from the game date
                final_season = None
                game_date_str = boxscore_data.get("date")
                
                if game_date_str and isinstance(game_date_str, str):
                    try:
                        # Parse the game date
                        if game_date_str.endswith('Z'):
                            parsed_game_date = datetime.fromisoformat(game_date_str.replace('Z', '+00:00'))
                        else:
                            parsed_game_date = datetime.fromisoformat(game_date_str)
                        
                        # Get all seasons from database to find which season this game belongs to
                        all_seasons = self.db_manager.get_all_seasons()
                        for season in all_seasons:
                            if season.start_date and season.end_date:
                                if season.start_date <= parsed_game_date <= season.end_date:
                                    final_season = season.season_number
                                    break
                            elif season.start_date and not season.end_date:
                                # Current season with no end date
                                if season.start_date <= parsed_game_date:
                                    final_season = season.season_number
                                    break
                                    
                        if final_season is None:
                            logger.warning(f"Could not determine season for game {game_id} with date {parsed_game_date}")
                            return False  # Skip this game if we can't determine season
                                    
                    except Exception as date_parse_error:
                        logger.warning(f"Could not parse date for game {game_id}: {date_parse_error}")
                        return False  # Skip this game if we can't parse the date
                else:
                    logger.warning(f"No valid date provided for game {game_id}")
                    return False  # Skip this game if no date
                
                # Prepare game data for GameRecord creation (same format as backend API)
                game_data_for_record = {
                    "id": game_id,
                    "type": boxscore_data.get("type", ""),
                    "season": final_season,
                    "date": boxscore_data.get("date"),
                    "attendance": attendance_data,
                    "ticket_revenue": boxscore_data.get("revenue")
                }
                
                # Create GameRecord using the factory method (same as backend API)
                from ..storage.models import GameRecord
                game_record = GameRecord.from_api_data(
                    game_data_for_record,
                    home_team_id=home_team_id,
                    away_team_id=away_team_id
                )
                
                # Save to database
                saved_id = self.db_manager.save_game_record(game_record)
                logger.debug(f"Successfully saved game {game_id} with database ID {saved_id}")
                return True
            else:
                logger.warning(f"Invalid or missing data for game {game_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error collecting game {game_id}: {e}")
            return False
    
    async def task_4_collect_team_history(self, team_ids: Set[int]) -> TaskResult:
        """
        Task 4: Collect team_history for all specified teams.
        
        Args:
            team_ids: Set of team IDs to collect history for
            
        Returns:
            TaskResult with summary of collection
        """
        start_time = time.time()
        task_name = "collect_team_history"
        
        logger.info(f"📚 Task 4: Collecting team history for {len(team_ids)} teams")
        
        try:
            successful_collections = 0
            failed_collections = 0
            failed_teams = []
            total_history_entries = 0
            
            for i, team_id in enumerate(team_ids, 1):
                logger.debug(f"[{i}/{len(team_ids)}] Collecting team history for team {team_id}")
                
                try:
                    # Get team history from webpage
                    history_data = self.api.get_team_history_from_webpage(team_id)
                    
                    if history_data:
                        # Convert dictionary data to TeamLeagueHistory objects
                        from ..storage.models import TeamLeagueHistory
                        
                        history_objects = []
                        for entry in history_data:
                            history_obj = TeamLeagueHistory.from_webpage_data(
                                team_id=str(team_id),
                                season=entry['season'],
                                team_name=entry['team_name'],
                                league_id=entry['league_id'],
                                league_name=entry['league_name'],
                                league_level=entry.get('league_level'),
                                achievement=entry.get('achievement'),
                                is_active_team=entry.get('is_active_team', True)
                            )
                            history_objects.append(history_obj)
                        
                        # Store history objects in database
                        self.db_manager.save_team_league_history(team_id, history_objects)
                        
                        total_history_entries += len(history_objects)
                        logger.debug(f"✅ Saved {len(history_objects)} history entries for team {team_id}")
                        successful_collections += 1
                    else:
                        logger.warning(f"❌ No team history returned for team {team_id}")
                        failed_collections += 1
                        failed_teams.append(team_id)
                    
                    # Rate limiting - extra delay for web scraping
                    await asyncio.sleep(self.rate_config.min_delay_between_requests + 1.0)
                    
                except Exception as e:
                    logger.error(f"❌ Error collecting team history for team {team_id}: {e}")
                    failed_collections += 1
                    failed_teams.append(team_id)
                
                # Progress updates
                if i % 25 == 0:
                    progress = i / len(team_ids)
                    logger.info(f"   📈 Progress: {progress:.1%} ({i}/{len(team_ids)}) - "
                               f"Success: {successful_collections}, Failed: {failed_collections}")
            
            execution_time = time.time() - start_time
            success_rate = successful_collections / len(team_ids) if team_ids else 0
            
            logger.info(f"✅ Task 4 completed!")
            logger.info(f"   - Successful: {successful_collections}/{len(team_ids)} ({success_rate:.1%})")
            logger.info(f"   - Failed: {failed_collections}")
            logger.info(f"   - Total history entries collected: {total_history_entries}")
            logger.info(f"   - Execution time: {execution_time:.1f}s")
            
            if failed_teams:
                logger.warning(f"   Failed team IDs: {failed_teams[:10]}{'...' if len(failed_teams) > 10 else ''}")
            
            return TaskResult(
                task_name=task_name,
                success=success_rate > 0.8,  # Consider success if >80% successful
                data={
                    "successful": successful_collections,
                    "failed": failed_collections,
                    "failed_teams": failed_teams,
                    "success_rate": success_rate,
                    "total_history_entries": total_history_entries
                },
                execution_time=execution_time,
                items_processed=successful_collections
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"❌ Task 4 failed: {e}")
            
            return TaskResult(
                task_name=task_name,
                success=False,
                error=str(e),
                execution_time=execution_time
            )
    
    async def _respect_rate_limits(self):
        """Implement rate limiting between API calls."""
        current_time = time.time()
        
        # Calculate delay based on configuration
        time_since_last = current_time - self.last_request_time
        min_delay = self.rate_config.min_delay_between_requests
        
        if time_since_last < min_delay:
            delay = min_delay - time_since_last
            await asyncio.sleep(delay)
        
        self.last_request_time = time.time()
        self.request_count += 1
        
        # Additional rate limiting per minute
        if self.request_count % self.rate_config.requests_per_minute == 0:
            logger.debug(f"Rate limit: Made {self.request_count} requests, brief pause")
            await asyncio.sleep(2.0)
    
    def save_task_result(self, result: TaskResult, output_dir: Optional[str] = None):
        """Save task result to disk for analysis/debugging."""
        if output_dir is None:
            output_dir = "task_results"
        
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{result.task_name}_{timestamp}.json"
        
        result_data = {
            "task_name": result.task_name,
            "success": result.success,
            "execution_time": result.execution_time,
            "items_processed": result.items_processed,
            "error": result.error,
            "timestamp": timestamp,
            # Convert sets to lists for JSON serialization
            "data": list(result.data) if isinstance(result.data, set) else result.data
        }
        
        with open(output_path / filename, 'w') as f:
            json.dump(result_data, f, indent=2)
        
        logger.info(f"💾 Saved task result to {output_path / filename}")


# Convenience functions for running individual tasks

async def run_team_discovery_task(
    api: BuzzerBeaterAPI,
    db_manager: DatabaseManager,
    countries: List[int],
    seasons: List[int] = [68, 69],
    max_league_level: int = 3
) -> Set[int]:
    """
    Run just the team discovery task and return the team IDs.
    
    Args:
        api: Authenticated BuzzerBeater API client
        db_manager: Database manager instance
        countries: List of country IDs to collect from
        seasons: List of season numbers to collect
        max_league_level: Maximum league level to include
        
    Returns:
        Set of team IDs discovered
    """
    collector = TaskBasedCollector(api, db_manager)
    result = await collector.task_1_collect_team_ids(countries, seasons, max_league_level)
    
    if result.success:
        logger.info(f"✅ Team discovery successful: {len(result.data)} teams found")
        return result.data
    else:
        logger.error(f"❌ Team discovery failed: {result.error}")
        return set()


async def run_parallel_info_arena_history_tasks(
    api: BuzzerBeaterAPI,
    db_manager: DatabaseManager,
    team_ids: Set[int]
) -> Tuple[TaskResult, TaskResult, TaskResult]:
    """
    Run team info, arena snapshot, and team history collection in parallel.
    
    Args:
        api: Authenticated BuzzerBeater API client
        db_manager: Database manager instance
        team_ids: Set of team IDs to collect data for
        
    Returns:
        Tuple of (team_info_result, arena_result, history_result)
    """
    collector = TaskBasedCollector(api, db_manager)
    
    # Run all three tasks in parallel
    logger.info(f"🚀 Running team info, arena, and history collection in parallel for {len(team_ids)} teams")
    
    team_info_task = collector.task_2_collect_team_info(team_ids)
    arena_task = collector.task_3_collect_arena_snapshots(team_ids)
    history_task = collector.task_4_collect_team_history(team_ids)
    
    results = await asyncio.gather(team_info_task, arena_task, history_task)
    
    return results[0], results[1], results[2]


async def run_parallel_info_arena_history_games_tasks(
    api: BuzzerBeaterAPI,
    db_manager: DatabaseManager,
    team_ids: Set[int],
    seasons: List[int] = [68, 69]
) -> Tuple[TaskResult, TaskResult, TaskResult, TaskResult]:
    """
    Run team info, arena snapshot, team history, and home games collection in parallel.
    
    Args:
        api: Authenticated BuzzerBeater API client
        db_manager: Database manager instance
        team_ids: Set of team IDs to collect data for
        seasons: List of seasons for game collection
        
    Returns:
        Tuple of (team_info_result, arena_result, history_result, games_result)
    """
    collector = TaskBasedCollector(api, db_manager)
    
    # Run all four tasks in parallel
    logger.info(f"🚀 Running team info, arena, history, and games collection in parallel for {len(team_ids)} teams")
    
    team_info_task = collector.task_2_collect_team_info(team_ids)
    arena_task = collector.task_3_collect_arena_snapshots(team_ids)
    history_task = collector.task_4_collect_team_history(team_ids)
    games_task = collector.task_5_collect_home_games(team_ids, seasons)
    
    results = await asyncio.gather(team_info_task, arena_task, history_task, games_task)
    
    return results[0], results[1], results[2], results[3]


async def run_complete_data_collection_pipeline(
    api: BuzzerBeaterAPI,
    db_manager: DatabaseManager,
    team_ids: Set[int],
    seasons: List[int] = [68, 69],
    include_pricing_update: bool = True
) -> Tuple[TaskResult, TaskResult, TaskResult, TaskResult, TaskResult]:
    """
    Run the complete data collection pipeline: team discovery, then parallel collection, 
    then sequential pricing updates.
    
    Args:
        api: Authenticated BuzzerBeater API client
        db_manager: Database manager instance
        team_ids: Set of team IDs to collect data for
        seasons: List of seasons for game collection
        include_pricing_update: Whether to run Task 6 (pricing updates)
        
    Returns:
        Tuple of (team_info_result, arena_result, history_result, games_result, pricing_result)
        If include_pricing_update is False, pricing_result will be None
    """
    collector = TaskBasedCollector(api, db_manager)
    
    # Phase 1: Run tasks 2, 3, 4, 5 in parallel
    logger.info(f"🚀 Phase 1: Running team info, arena, history, and games collection in parallel for {len(team_ids)} teams")
    
    team_info_task = collector.task_2_collect_team_info(team_ids)
    arena_task = collector.task_3_collect_arena_snapshots(team_ids)
    history_task = collector.task_4_collect_team_history(team_ids)
    games_task = collector.task_5_collect_home_games(team_ids, seasons)
    
    team_info_result, arena_result, history_result, games_result = await asyncio.gather(
        team_info_task, arena_task, history_task, games_task
    )
    
    # Phase 2: Run pricing updates sequentially (depends on games being collected)
    pricing_result = None
    if include_pricing_update and games_result.success:
        logger.info(f"🚀 Phase 2: Running pricing updates sequentially for {len(team_ids)} teams")
        pricing_result = await collector.task_6_update_game_pricing(team_ids)
    elif include_pricing_update and not games_result.success:
        logger.warning("⚠️ Skipping pricing updates because game collection failed")
    
    return team_info_result, arena_result, history_result, games_result, pricing_result


# Legacy function for backward compatibility
async def run_parallel_info_and_arena_tasks(
    api: BuzzerBeaterAPI,
    db_manager: DatabaseManager,
    team_ids: Set[int]
) -> Tuple[TaskResult, TaskResult]:
    """
    Run team info and arena snapshot collection in parallel (legacy function).
    
    Args:
        api: Authenticated BuzzerBeater API client
        db_manager: Database manager instance
        team_ids: Set of team IDs to collect data for
        
    Returns:
        Tuple of (team_info_result, arena_result)
    """
    collector = TaskBasedCollector(api, db_manager)
    
    # Run both tasks in parallel
    logger.info(f"🚀 Running team info and arena collection in parallel for {len(team_ids)} teams")
    
    team_info_task = collector.task_2_collect_team_info(team_ids)
    arena_task = collector.task_3_collect_arena_snapshots(team_ids)
    
    results = await asyncio.gather(team_info_task, arena_task)
    
    return results[0], results[1]


# Example usage
async def main():
    """Example usage of the task-based collector."""
    
    # Initialize API and database
    api = BuzzerBeaterAPI("username", "security_code")
    db_manager = DatabaseManager("bb_arena_data.db")
    
    try:
        # Login
        if not api.login():
            raise Exception("Failed to login to BuzzerBeater API")
        
        # Example: Collect data for top 3 countries
        countries = [99, 7, 10]  # Utopia, Spain, Italy
        seasons = [68, 69]
        
        logger.info(f"🚀 Starting task-based collection")
        logger.info(f"   - Countries: {countries}")
        logger.info(f"   - Seasons: {seasons}")
        
        # Task 1: Discover teams
        team_ids = await run_team_discovery_task(api, db_manager, countries, seasons)
        
        if not team_ids:
            logger.error("❌ No teams discovered, stopping")
            return
        
        # Tasks 2-6: Complete data collection pipeline 
        team_info_result, arena_result, history_result, games_result, pricing_result = await run_complete_data_collection_pipeline(
            api, db_manager, team_ids, seasons
        )
        
        # Summary
        logger.info(f"🎉 Complete task-based collection pipeline completed!")
        logger.info(f"   - Teams discovered: {len(team_ids)}")
        logger.info(f"   - Team info success: {team_info_result.success}")
        logger.info(f"   - Arena data success: {arena_result.success}")
        logger.info(f"   - Team history success: {history_result.success}")
        logger.info(f"   - Home games success: {games_result.success}")
        if pricing_result:
            logger.info(f"   - Game pricing success: {pricing_result.success}")
            if pricing_result.data:
                logger.info(f"   - Games with updated pricing: {pricing_result.data.get('total_games_updated', 0)}")
        else:
            logger.info(f"   - Game pricing: SKIPPED")
        
    finally:
        api.logout()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())