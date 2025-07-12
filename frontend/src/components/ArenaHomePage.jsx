import React, { useState, useEffect } from 'react';
import { arenaService } from '../services/arenaService';
import ArenaDetailView from './ArenaDetailView';
import LoadingSpinner from './LoadingSpinner';
import './ArenaHomePage.css';

const ArenaHomePage = ({ onLoadingChange }) => {
  const [userArenaData, setUserArenaData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [syncing, setSyncing] = useState(false);
  const [sidebarExpanded, setSidebarExpanded] = useState(false);

  // Simplified loading notification - just notify once when we finish loading
  useEffect(() => {
    if (onLoadingChange && !loading && userArenaData) {
      onLoadingChange(false);
    }
  }, [loading, userArenaData, onLoadingChange]);

  useEffect(() => {
    const fetchUserArena = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const data = await arenaService.getUserCurrentArena();
        setUserArenaData(data);
      } catch (err) {
        console.error('ArenaHomePage: Error fetching user arena:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchUserArena();
  }, []);

  const handleSyncTeamInfo = async () => {
    try {
      setSyncing(true);
      setError(null);
      
      // Force refresh team info from BB API and update cache
      await arenaService.syncUserTeamInfo();
      
      // Refetch user arena data with updated team info
      const data = await arenaService.getUserCurrentArena();
      setUserArenaData(data);
    } catch (err) {
      console.error('Error syncing team info:', err);
      setError(`Failed to sync team info: ${err.message}`);
    } finally {
      setSyncing(false);
    }
  };

  if (loading) {
    // Don't render anything during loading - parent App component will show loading spinner
    return null;
  }

  if (error) {
    return (
      <div className="arena-home-error">
        <h2>Unable to Load Your Arena</h2>
        <p>{error}</p>
        <p>Make sure:</p>
        <ul>
          <li>Your BuzzerBeater credentials are configured in the environment file</li>
          <li>The backend server is running</li>
          <li>Your team has arena data collected</li>
        </ul>
      </div>
    );
  }

  if (!userArenaData || !userArenaData.arena) {
    return (
      <div className="arena-home-no-data">
        <h2>No Arena Data Found</h2>
        <p>No arena data found for your team: <strong>{userArenaData?.userTeam?.name || 'Unknown Team'}</strong></p>
        <p>Try collecting arena data first using the Arena Collector tool.</p>
      </div>
    );
  }

  const { arena, userTeam } = userArenaData;

  return (
    <div className={`arena-home-page ${sidebarExpanded ? 'sidebar-expanded' : 'sidebar-collapsed'}`}>
      <div className="arena-home-header">
        <div className="team-info">
          <div className="team-main-info">
            <div className="team-name-line">
              <h1>{userTeam.name}</h1>
              {userTeam.short_name && (
                <span className="team-short-name">({userTeam.short_name})</span>
              )}
              <div className="team-details">
                {userTeam.owner && <span>Owner: {userTeam.owner}</span>}
                {userTeam.league && <span>League: {userTeam.league}</span>}
              </div>
            </div>
          </div>
          <button 
            className={`sync-button ${syncing ? 'syncing' : ''}`}
            onClick={handleSyncTeamInfo}
            disabled={syncing}
            title="Sync team info from BuzzerBeater"
          >
            ↻
          </button>
        </div>
      </div>
      
      <div className="arena-detail-container">
        <ArenaDetailView 
          arena={arena} 
          showBackButton={false}
          title={`${userTeam.name} Arena`}
          onSidebarExpandedChange={setSidebarExpanded}
        />
      </div>
    </div>
  );
};

export default ArenaHomePage;
