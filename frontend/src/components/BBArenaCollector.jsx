import React, { useState } from 'react';
import { arenaService } from '../services/arenaService';
import './BBArenaCollector.css';

const BBArenaCollector = ({ onDataCollected }) => {
  const [leagueId, setLeagueId] = useState('');
  const [season, setSeason] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!leagueId.trim()) {
      setError('Please enter a league ID');
      return;
    }

    const leagueIdInt = parseInt(leagueId.trim());
    const seasonInt = season.trim() ? parseInt(season.trim()) : null;

    if (isNaN(leagueIdInt)) {
      setError('Please enter a valid league ID (number)');
      return;
    }

    if (season.trim() && isNaN(seasonInt)) {
      setError('Please enter a valid season number');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await arenaService.collectArenasFromBB(leagueIdInt, seasonInt);
      setResult(response);
      
      // Call callback if provided to refresh the arena list
      if (onDataCollected) {
        onDataCollected();
      }
    } catch (err) {
      setError(err.message || 'Failed to collect arena data');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setLeagueId('');
    setSeason('');
    setResult(null);
    setError(null);
  };

  return (
    <div className="bb-arena-collector">
      <div className="collector-header">
        <h3>🏀 Collect Arena Data from BuzzerBeater</h3>
        <p>Automatically download current arena information for all teams in your league</p>
      </div>

      <form onSubmit={handleSubmit} className="collector-form">
        <div className="form-group">
          <label htmlFor="league-id">
            League ID:
            <input
              id="league-id"
              type="number"
              value={leagueId}
              onChange={(e) => setLeagueId(e.target.value)}
              placeholder="Enter league ID (e.g., 123)"
              disabled={loading}
            />
          </label>
          <span className="field-help">
            The ID of the league you want to collect arena data for
          </span>
        </div>

        <div className="form-group">
          <label htmlFor="season">
            Season (optional):
            <input
              id="season"
              type="number"
              value={season}
              onChange={(e) => setSeason(e.target.value)}
              placeholder="Enter season number (leave empty for current season)"
              disabled={loading}
            />
          </label>
          <span className="field-help">
            Optional: specify a season number, or leave empty for current season
          </span>
        </div>

        <div className="form-actions">
          <button 
            type="submit" 
            className="collect-button"
            disabled={loading}
          >
            {loading ? 'Collecting...' : 'Collect Arena Data'}
          </button>
          
          <button 
            type="button" 
            className="reset-button"
            onClick={handleReset}
            disabled={loading}
          >
            Reset
          </button>
        </div>
      </form>

      {loading && (
        <div className="loading-indicator">
          <div className="spinner"></div>
          <p>Fetching league standings and collecting arena data...</p>
        </div>
      )}

      {error && (
        <div className="error-message">
          <strong>Error:</strong> {error}
        </div>
      )}

      {result && (
        <div className="success-message">
          <h4>✅ Collection Complete!</h4>
          <div className="result-details">
            <p><strong>New arenas collected:</strong> {result.arenas_collected}</p>
            <p><strong>Duplicates skipped:</strong> {result.arenas_skipped}</p>
            {result.failed_teams && result.failed_teams.length > 0 && (
              <p><strong>Failed teams:</strong> {result.failed_teams.join(', ')}</p>
            )}
            <p><strong>Message:</strong> {result.message}</p>
          </div>
        </div>
      )}

      <div className="collector-info">
        <div className="note">
          <strong>Note:</strong> Make sure your BuzzerBeater credentials are configured in the server environment. The system will automatically discover all teams in the league - no need to manually enter team IDs!
        </div>
      </div>
    </div>
  );
};

export default BBArenaCollector;
