import React, { useState, useEffect } from 'react';
import { arenaService } from '../services/arenaService';
import ArenaDesigner from './ArenaDesigner';
import './ArenaDetailView.css';

const ArenaDetailView = ({ selectedArena, onBackToList }) => {
  const [arenaHistory, setArenaHistory] = useState([]);
  const [selectedSnapshot, setSelectedSnapshot] = useState(selectedArena);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchArenaHistory = async () => {
      if (!selectedArena?.team_id) return;
      
      try {
        setLoading(true);
        const response = await arenaService.getTeamArenaHistory(selectedArena.team_id);
        setArenaHistory(response.arenas);
        setError(null);
      } catch (err) {
        setError('Failed to fetch arena history');
        console.error('Error fetching arena history:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchArenaHistory();
  }, [selectedArena]);

  const handleSnapshotChange = (snapshotId) => {
    const snapshot = arenaHistory.find(arena => arena.id === parseInt(snapshotId));
    if (snapshot) {
      setSelectedSnapshot(snapshot);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatNumber = (number) => {
    return number?.toLocaleString() || '0';
  };

  const getSnapshotLabel = (arena, index) => {
    const date = formatDate(arena.created_at);
    const isLatest = index === 0;
    return `${date}${isLatest ? ' (Latest)' : ''}`;
  };

  const hasArenaDataChanged = (current, previous) => {
    if (!previous) return false;
    
    return (
      current.bleachers_capacity !== previous.bleachers_capacity ||
      current.lower_tier_capacity !== previous.lower_tier_capacity ||
      current.courtside_capacity !== previous.courtside_capacity ||
      current.luxury_boxes_capacity !== previous.luxury_boxes_capacity ||
      current.expansion_in_progress !== previous.expansion_in_progress
    );
  };

  return (
    <div className="arena-detail-view">
      <div className="detail-header">
        <button onClick={onBackToList} className="back-button">
          ← Back to Arena List
        </button>
        
        <div className="arena-title">
          <h2>{selectedSnapshot?.arena_name || `Arena ${selectedSnapshot?.id}`}</h2>
          <div className="arena-meta">
            <span>Team ID: {selectedSnapshot?.team_id}</span>
            <span>Total Capacity: {formatNumber(selectedSnapshot?.total_capacity)}</span>
            <span>Current View: {formatDate(selectedSnapshot?.created_at)}</span>
          </div>
        </div>
      </div>

      {arenaHistory.length > 1 && (
        <div className="snapshot-selector">
          <h3>Arena History ({arenaHistory.length} snapshots)</h3>
          <div className="snapshot-controls">
            <label htmlFor="snapshot-select">
              Select snapshot:
              <select 
                id="snapshot-select"
                value={selectedSnapshot?.id || ''}
                onChange={(e) => handleSnapshotChange(e.target.value)}
              >
                {arenaHistory.map((arena, index) => (
                  <option key={arena.id} value={arena.id}>
                    {getSnapshotLabel(arena, index)}
                  </option>
                ))}
              </select>
            </label>
          </div>
          
          <div className="snapshot-timeline">
            {arenaHistory.map((arena, index) => {
              const isSelected = arena.id === selectedSnapshot?.id;
              const isChanged = hasArenaDataChanged(arena, arenaHistory[index + 1]);
              
              return (
                <div 
                  key={arena.id}
                  className={`timeline-item ${isSelected ? 'selected' : ''} ${isChanged ? 'changed' : ''}`}
                  onClick={() => setSelectedSnapshot(arena)}
                >
                  <div className="timeline-date">{formatDate(arena.created_at)}</div>
                  <div className="timeline-capacity">
                    Total: {formatNumber(arena.total_capacity)}
                    {isChanged && <span className="change-indicator">📊</span>}
                  </div>
                  {index === 0 && <span className="latest-badge">Latest</span>}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {loading && (
        <div className="loading">Loading arena history...</div>
      )}

      {error && (
        <div className="error">{error}</div>
      )}

      {selectedSnapshot && (
        <ArenaDesigner 
          initialSeatCounts={{
            courtside: selectedSnapshot.courtside_capacity,
            lowerTierTotal: selectedSnapshot.lower_tier_capacity,
            luxuryBoxCount: selectedSnapshot.luxury_boxes_capacity,
          }}
          readonly={true}
        />
      )}
    </div>
  );
};

export default ArenaDetailView;
