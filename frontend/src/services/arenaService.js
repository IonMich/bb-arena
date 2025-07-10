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
}

export const arenaService = new ArenaService();
