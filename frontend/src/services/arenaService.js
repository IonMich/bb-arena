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
}

export const arenaService = new ArenaService();
