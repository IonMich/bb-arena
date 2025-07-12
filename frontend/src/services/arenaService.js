/**
 * Service for fetching arena data from the backend API
 */

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
      const response = await fetch(`${API_BASE_URL}/arenas/team/${teamId}?limit=${limit}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error(`Error fetching team ${teamId} arenas:`, error);
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
   * Fetch game boxscore from BuzzerBeater API
   */
  async getGameBoxscore(gameId) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/bb/game/${gameId}/boxscore`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error(`Error fetching game ${gameId} boxscore:`, error);
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
   * Get user's team information
   */
  async getUserTeamInfo() {
    try {
      const response = await fetch(`${API_BASE_URL}/api/bb/team-info`);
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
   * Check if a game is likely stored in the database by testing load time
   */
  async isGameStored(gameId) {
    try {
      const startTime = Date.now();
      await this.getGameBoxscore(gameId);
      const loadTime = Date.now() - startTime;
      
      // If it loads very quickly (< 200ms), it's likely from the database
      return loadTime < 200;
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
      const homeGames = scheduleData.games.filter(game => game.home && game.type !== 'bbm');
      
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
}

export const arenaService = new ArenaService();
