/**
 * Service for fetching arena data from the backend API
 */

import { validateGameRecord } from '../types/GameRecord.js';

const API_BASE_URL = 'http://localhost:8000';

class ArenaService {
  /**
   * Fetch all arenas with pagination
   */
  async getArenas(limit = 50, offset = 0) {
    try {
      const response = await fetch(`${API_BASE_URL}/arenas?limit=${limit}&offset=${offset}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching arenas:', error);
      throw error;
    }
  }

  /**
   * Fetch a specific arena by ID
   */
  async getArena(arenaId) {
    try {
      const response = await fetch(`${API_BASE_URL}/arenas/${arenaId}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error(`Error fetching arena ${arenaId}:`, error);
      throw error;
    }
  }

  /**
   * Fetch arenas for a specific team
   */
  async getTeamArenas(teamId, limit = 50) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
      
      const response = await fetch(`${API_BASE_URL}/arenas/team/${teamId}?limit=${limit}`, {
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      return data;
    } catch (error) {
      console.error(`Error fetching team ${teamId} arenas:`, error);
      throw error;
    }
  }

  /**
   * Get the user's current arena (latest arena for their team)
   */
  async getUserCurrentArena() {
    try {
      // First try to get cached team info (much faster)
      let userTeam;
      try {
        userTeam = await this.getCachedTeamInfo();
      } catch {
        // If no cached info, fall back to smart team info (which will sync if needed)
        console.log('No cached team info found, fetching from API...');
        userTeam = await this.getUserTeamInfo();
      }

      if (!userTeam || !userTeam.id) {
        throw new Error('User team information not available');
      }

      // Get the latest arena for this team (limit=1 to get most recent)
      const teamArenas = await this.getTeamArenas(userTeam.id, 1);
      
      if (!teamArenas.arenas || teamArenas.arenas.length === 0) {
        return null; // No arena found for this team
      }

      return {
        arena: teamArenas.arenas[0],
        userTeam: userTeam
      };
    } catch (error) {
      console.error('Error fetching user current arena:', error);
      throw error;
    }
  }

  /**
   * Collect arena data from BuzzerBeater API
   */
  async collectArenasFromBB(leagueId, season = null) {
    try {
      const requestBody = {
        league_id: leagueId
      };
      
      if (season) {
        requestBody.season = season;
      }

      const response = await fetch(`${API_BASE_URL}/api/bb/collect-arenas`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error collecting arenas from BuzzerBeater API:', error);
      throw error;
    }
  }

  /**
   * Fetch arena history for a specific team
   */
  async getTeamArenaHistory(teamId, limit = 50) {
    try {
      const response = await fetch(`${API_BASE_URL}/arenas/team/${teamId}/history?limit=${limit}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error(`Error fetching team ${teamId} arena history:`, error);
      throw error;
    }
  }

  /**
   * Fetch team schedule from BuzzerBeater API
   */
  async getTeamSchedule(teamId, season = null) {
    try {
      const url = season 
        ? `${API_BASE_URL}/api/bb/team/${teamId}/schedule?season=${season}`
        : `${API_BASE_URL}/api/bb/team/${teamId}/schedule`;
        
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error(`Error fetching team ${teamId} schedule:`, error);
      throw error;
    }
  }

  /**
   * Get game data from database only (no BB API call)
   * @param {string} gameId - Game ID to fetch
   * @returns {Promise<import('../types/GameRecord.js').GameRecord|null>} GameRecord or null if not found
   */
  async getGameFromDB(gameId) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/bb/game/${gameId}/stored`);
      if (response.status === 404) {
        return null; // Game not found in database
      }
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      return validateGameRecord(data);
    } catch (error) {
      console.error(`Error fetching stored game ${gameId}:`, error);
      throw error;
    }
  }

  /**
   * Fetch game from BB API and store to database
   * @param {string} gameId - Game ID to fetch
   * @returns {Promise<import('../types/GameRecord.js').GameRecord>} GameRecord from BB API
   */
  async fetchAndStoreGameFromBB(gameId) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/bb/game/${gameId}/fetch`, {
        method: 'POST'
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      return validateGameRecord(data);
    } catch (error) {
      console.error(`Error fetching and storing game ${gameId} from BB:`, error);
      throw error;
    }
  }

  /**
   * Get game data with smart caching - tries database first, then BB API
   * @param {string} gameId - Game ID to fetch
   * @returns {Promise<{gameRecord: import('../types/GameRecord.js').GameRecord, fromCache: boolean}>}
   */
  async getGameSmart(gameId) {
    try {
      // Try database first
      const cachedGame = await this.getGameFromDB(gameId);
      if (cachedGame) {
        return { gameRecord: cachedGame, fromCache: true };
      }
      
      // Fetch from BB API if not in database
      const freshGame = await this.fetchAndStoreGameFromBB(gameId);
      return { gameRecord: freshGame, fromCache: false };
    } catch (error) {
      console.error(`Error in smart game fetch for ${gameId}:`, error);
      throw error;
    }
  }

  /**
   * Fetch stored games for a specific team
   */
  async getTeamStoredGames(teamId, season = null, limit = 200) {
    try {
      const url = season 
        ? `${API_BASE_URL}/api/bb/team/${teamId}/games?season=${season}&limit=${limit}`
        : `${API_BASE_URL}/api/bb/team/${teamId}/games?limit=${limit}`;
        
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error(`Error fetching stored games for team ${teamId}:`, error);
      throw error;
    }
  }

  /**
   * Get seasons data
   */
  async getSeasons() {
    try {
      const response = await fetch(`${API_BASE_URL}/api/bb/seasons`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching seasons:', error);
      throw error;
    }
  }

  /**
   * Get seasons data with team-specific minimum season based on creation date
   */
  async getSeasonsForTeam(teamId) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/bb/seasons/team/${teamId}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error(`Error fetching seasons for team ${teamId}:`, error);
      throw error;
    }
  }

  /**
   * Force update seasons from BBAPI
   */
  async updateSeasons() {
    try {
      const response = await fetch(`${API_BASE_URL}/api/bb/seasons/update`, {
        method: 'POST'
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Error updating seasons:', error);
      throw error;
    }
  }

  /**
   * Get user's team information (uses smart caching)
   */
  async getUserTeamInfo() {
    try {
      const response = await fetch(`${API_BASE_URL}/api/bb/team-info/smart`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching user team info:', error);
      throw error;
    }
  }

  /**
   * Get cached team information from database
   */
  async getCachedTeamInfo() {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
      
      const response = await fetch(`${API_BASE_URL}/api/bb/team-info/cached`, {
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error fetching cached team info:', error);
      throw error;
    }
  }

  /**
   * Sync team information from BuzzerBeater API and cache it
   */
  async syncUserTeamInfo() {
    try {
      const response = await fetch(`${API_BASE_URL}/api/bb/team-info/sync`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Error syncing team info:', error);
      throw error;
    }
  }

  /**
   * Get league standings for current season to get league info
   */
  async getLeagueInfo(leagueId, season = null) {
    try {
      const params = new URLSearchParams({ leagueid: leagueId });
      if (season) params.append('season', season);
      
      const response = await fetch(`${API_BASE_URL}/api/bb/standings?${params}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching league info:', error);
      throw error;
    }
  }

  /**
   * Initialize app with essential data (seasons, user team, current league)
   */
  async initializeApp() {
    try {
      // Fetch seasons and user team info in parallel
      const [seasonsData, userTeamData] = await Promise.all([
        this.getSeasons(),
        this.getUserTeamInfo()
      ]);

      // Get current season info
      const currentSeason = seasonsData.current_season;
      const validSeasons = seasonsData.seasons.filter(s => s.season_number && s.season_number > 0);

      // Try to get league info if we have user team data
      let leagueInfo = null;
      if (userTeamData && userTeamData.league_id) {
        try {
          leagueInfo = await this.getLeagueInfo(userTeamData.league_id, currentSeason);
        } catch (error) {
          console.warn('Could not fetch league info:', error);
        }
      }

      return {
        seasons: {
          all: validSeasons,
          current: currentSeason,
          min: Math.max(1, (currentSeason || 69) - 15),
          max: currentSeason || 69
        },
        userTeam: userTeamData,
        league: leagueInfo,
        initialized: true
      };
    } catch (error) {
      console.error('Error initializing app:', error);
      // Return fallback data
      return {
        seasons: {
          all: [],
          current: 69,
          min: 54,
          max: 69
        },
        userTeam: null,
        league: null,
        initialized: false,
        error: error.message
      };
    }
  }

  /**
   * Check if a game is stored in the database
   */
  async isGameStored(gameId) {
    try {
      const game = await this.getGameFromDB(gameId);
      return game !== null;
    } catch {
      // If there's an error, assume it's not stored
      return false;
    }
  }

  /**
   * Check if games are stored across multiple seasons
   */
  async findStoredGamesAcrossSeasons(teamId, gameIds, currentSeason) {
    const storedGameIds = new Set();
    
    // First try to get ALL stored games (no season filter) to bypass pagination issues
    try {
      console.log('Checking all stored games (no season filter) for comprehensive verification');
      const allStoredGames = await this.getTeamStoredGames(teamId, null, 1000); // High limit, no season
      allStoredGames.games.forEach(game => {
        if (gameIds.includes(game.id)) {
          console.log(`Found game ${game.id} in comprehensive stored games check`);
          storedGameIds.add(game.id);
        }
      });
    } catch (error) {
      console.warn('Could not check all stored games:', error.message);
    }
    
    // Also check a few seasons around the current one as backup
    const seasonsToCheck = [
      currentSeason,
      currentSeason - 1,
      currentSeason + 1
    ].filter(season => season > 0);
    
    for (const season of seasonsToCheck) {
      try {
        const storedGames = await this.getTeamStoredGames(teamId, season, 500); // Higher limit
        storedGames.games.forEach(game => {
          if (gameIds.includes(game.id)) {
            storedGameIds.add(game.id);
          }
        });
      } catch (error) {
        console.warn(`Could not check stored games for season ${season}:`, error.message);
      }
    }
    
    return storedGameIds;
  }

  /**
   * Check which games from a list are already stored in the database
   */
  async checkGamesStored(teamId, gameIds) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/bb/team/${teamId}/games/check-stored`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(gameIds)
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result = await response.json();
      return result.stored_games;
    } catch (error) {
      console.error(`Error checking stored games for team ${teamId}:`, error);
      throw error;
    }
  }

  /**
   * Get robust home games count and breakdown directly from database
   */
  async getHomeGamesCountRobust(teamId, season = null) {
    try {
      const url = season 
        ? `${API_BASE_URL}/api/bb/team/${teamId}/games/home-count?season=${season}`
        : `${API_BASE_URL}/api/bb/team/${teamId}/games/home-count`;
        
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error(`Error fetching robust home games count for team ${teamId}:`, error);
      throw error;
    }
  }

  /**
   * Get comprehensive stored home games count for arena analysis
   * Uses the same logic as the sidebar for consistency
   */
  async getArenaStoredHomeGamesCount(teamId, targetSeason = null) {
    try {
      // Use the same approach as the sidebar to ensure consistency
      const currentSeason = targetSeason || 68; // Default to current season
      
      // Get team schedule to identify home games
      const scheduleData = await this.getTeamSchedule(teamId, currentSeason);
      if (!scheduleData?.games) {
        console.log(`No schedule data available for team ${teamId} season ${currentSeason}`);
        return 0;
      }
      
      // Filter for home games only (excluding BBM games which are played in neutral venues)
      const homeGames = scheduleData.games.filter(game => game.home && game.type !== 'bbm' && game.type !== 'pl.rsneutral');
      
      // Get all game IDs to check which ones are stored
      const gameIds = homeGames.map(game => game.id);
      
      if (gameIds.length === 0) {
        return 0;
      }
      
      // Check which games are actually stored using the robust endpoint
      const storedStatus = await this.checkGamesStored(teamId, gameIds);
      
      // Count stored home games
      const storedHomeGames = gameIds.filter(gameId => storedStatus[gameId]);
      
      console.log(`Arena count: Found ${storedHomeGames.length} stored home games for team ${teamId} season ${currentSeason}`);
      return storedHomeGames.length;
      
    } catch (error) {
      console.error(`Error getting arena stored home games count:`, error);
      return 0;
    }
  }

  /**
   * Get prefix max attendance for each section up to a specific date
   * This provides historical lower bounds for arena capacity
   */
  async getPrefixMaxAttendance(teamId, upToDate) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/bb/team/${teamId}/games/prefix-max-attendance?up_to_date=${encodeURIComponent(upToDate)}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error(`Error fetching prefix max attendance for team ${teamId}:`, error);
      throw error;
    }
  }


  /**
   * Get team league history
   */
  async getTeamLeagueHistory(teamId, activeOnly = false) {
    try {
      const params = new URLSearchParams({ active_only: activeOnly });
      const response = await fetch(`${API_BASE_URL}/api/bb/team/${teamId}/league-history?${params}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error(`Error fetching team league history for ${teamId}:`, error);
      throw error;
    }
  }

  /**
   * Get current league info for a team
   */
  async getTeamCurrentLeague(teamId) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/bb/team/${teamId}/current-league`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error(`Error fetching current league for team ${teamId}:`, error);
      throw error;
    }
  }

  /**
   * Collect team league history from BuzzerBeater webpage
   */
  async collectTeamLeagueHistory(teamId) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/bb/team/${teamId}/league-history/collect`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error(`Error collecting team league history for ${teamId}:`, error);
      throw error;
    }
  }

  /**
   * Collect team pricing data from arena webpage and update game pricing
   */
  async collectTeamPricingDataEnhanced(teamId) {
    try {
      const response = await fetch(`${API_BASE_URL}/collecting/update-pricing-from-arena`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          team_id: teamId
        })
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }
      
      const result = await response.json();
      
      // Transform the response to match the expected format in the frontend
      return {
        success: true,
        message: result.message,
        total_periods_processed: result.periods_created,
        total_games_found: result.games_updated, // Using games_updated as games_found
        total_games_price_updated: result.games_updated,
        errors: []
      };
    } catch (error) {
      console.error(`Error collecting team pricing data for ${teamId}:`, error);
      return {
        success: false,
        message: error.message || 'Unknown error occurred',
        total_periods_processed: 0,
        total_games_found: 0,
        total_games_price_updated: 0,
        errors: [error.message]
      };
    }
  }
}

export const arenaService = new ArenaService();
