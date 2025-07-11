import React, { useState, useEffect, useCallback } from 'react';
import { arenaService } from '../services/arenaService';
import ArenaDesigner from './ArenaDesigner';
import GameAttendanceSidebar from './GameAttendanceSidebar';
import './ArenaDetailView.css';

const ArenaDetailView = ({ selectedArena, onBackToList, appData = null }) => {
  const [arenaHistory, setArenaHistory] = useState([]);
  const [selectedSnapshot, setSelectedSnapshot] = useState(selectedArena);
  const [selectedGame, setSelectedGame] = useState(null);
  const [storedGamesCount, setStoredGamesCount] = useState(null); // null means loading
  const [storedGamesBreakdown, setStoredGamesBreakdown] = useState({});
  const [showStoredGamesPopover, setShowStoredGamesPopover] = useState(false);
  const [error, setError] = useState(null);

  const fetchStoredGamesBreakdown = useCallback(async () => {
    if (!selectedArena?.team_id) return;
    
    try {
      // Use the efficient backend endpoint that queries the database directly
      const teamId = selectedArena.team_id;
      const countData = await arenaService.getHomeGamesCountRobust(teamId);
      
      console.log(`Robust breakdown for team ${teamId}:`, countData.breakdown_by_season);
      setStoredGamesBreakdown(countData.breakdown_by_season || {});
      setStoredGamesCount(countData.total_home_games_count || 0);
    } catch (error) {
      console.error('Error fetching stored games breakdown:', error);
      setStoredGamesBreakdown({});
    }
  }, [selectedArena?.team_id]);

  useEffect(() => {
    const fetchArenaHistory = async () => {
      if (!selectedArena?.team_id) return;
      
      try {
        // Get arena history without loading state for better UX
        const [historyResponse] = await Promise.all([
          arenaService.getTeamArenaHistory(selectedArena.team_id)
        ]);
        
        setArenaHistory(historyResponse.arenas);
        
        // Fetch stored games breakdown (this will also set the correct total count)
        await fetchStoredGamesBreakdown();
        
        setError(null);
      } catch (err) {
        setError('Failed to fetch arena history');
        console.error('Error fetching arena history:', err);
      }
    };

    fetchArenaHistory();
  }, [selectedArena, fetchStoredGamesBreakdown]);

  const areSnapshotsIdentical = (snapshot1, snapshot2) => {
    return (
      snapshot1.bleachers_capacity === snapshot2.bleachers_capacity &&
      snapshot1.lower_tier_capacity === snapshot2.lower_tier_capacity &&
      snapshot1.courtside_capacity === snapshot2.courtside_capacity &&
      snapshot1.luxury_boxes_capacity === snapshot2.luxury_boxes_capacity &&
      snapshot1.expansion_in_progress === snapshot2.expansion_in_progress
    );
  };

  // Group identical snapshots together
  const groupSnapshots = (snapshots) => {
    if (!snapshots || snapshots.length === 0) return [];
    
    const sortedSnapshots = [...snapshots].sort((a, b) => 
      new Date(b.created_at) - new Date(a.created_at)
    );
    
    const groups = [];
    let currentGroup = {
      snapshots: [sortedSnapshots[0]],
      representative: sortedSnapshots[0],
      startDate: sortedSnapshots[0].created_at,
      endDate: sortedSnapshots[0].created_at
    };
    
    for (let i = 1; i < sortedSnapshots.length; i++) {
      const current = sortedSnapshots[i];
      
      if (areSnapshotsIdentical(current, currentGroup.representative)) {
        // Add to current group
        currentGroup.snapshots.push(current);
        currentGroup.endDate = current.created_at; // Earlier date
      } else {
        // Start new group
        groups.push(currentGroup);
        currentGroup = {
          snapshots: [current],
          representative: current,
          startDate: current.created_at,
          endDate: current.created_at
        };
      }
    }
    
    groups.push(currentGroup);
    return groups;
  };

  // Find the appropriate snapshot group for a given game date
  const findSnapshotForGame = (gameDate, snapshotGroups) => {
    if (!gameDate || !snapshotGroups.length) return null;
    
    const gameDateObj = new Date(gameDate);
    
    // Find the group that was valid at the time of the game
    for (const group of snapshotGroups) {
      const groupStartDate = new Date(group.startDate);
      const groupEndDate = new Date(group.endDate);
      
      // Check if game date falls within this group's validity period
      if (gameDateObj >= groupEndDate && gameDateObj <= groupStartDate) {
        return group.representative;
      }
    }
    
    // If no exact match, find the closest group before the game date
    let closestGroup = null;
    let smallestDifference = Infinity;
    
    for (const group of snapshotGroups) {
      const groupEndDate = new Date(group.endDate);
      if (groupEndDate <= gameDateObj) {
        const difference = gameDateObj - groupEndDate;
        if (difference < smallestDifference) {
          smallestDifference = difference;
          closestGroup = group;
        }
      }
    }
    
    return closestGroup ? closestGroup.representative : snapshotGroups[0].representative;
  };

  const snapshotGroups = groupSnapshots(arenaHistory);
  const hasMultipleDistinctGroups = snapshotGroups.length > 1;

  const handleSnapshotChange = (snapshotId) => {
    // Find the snapshot in any group
    for (const group of snapshotGroups) {
      const snapshot = group.snapshots.find(arena => arena.id === parseInt(snapshotId));
      if (snapshot) {
        setSelectedSnapshot(snapshot);
        break;
      }
    }
  };

  // Auto-select snapshot when game is selected
  useEffect(() => {
    if (selectedGame && selectedGame.date && snapshotGroups.length > 0) {
      const appropriateSnapshot = findSnapshotForGame(selectedGame.date, snapshotGroups);
      if (appropriateSnapshot && appropriateSnapshot.id !== selectedSnapshot?.id) {
        setSelectedSnapshot(appropriateSnapshot);
      }
    }
  }, [selectedGame, snapshotGroups, selectedSnapshot?.id]);

  const updateStoredGamesCount = async () => {
    if (!selectedArena?.team_id) return;
    
    try {
      // Just refresh the breakdown, which will update the count automatically
      await fetchStoredGamesBreakdown();
    } catch (err) {
      console.error('Error updating stored games count:', err);
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

  const getSnapshotGroupLabel = (group) => {
    const startDate = formatDate(group.startDate);
    const endDate = formatDate(group.endDate);
    const count = group.snapshots.length;
    
    if (group.snapshots.length === 1) {
      return `${startDate}`;
    } else {
      return `${endDate} - ${startDate} (${count} snapshots)`;
    }
  };

  // Function to determine known capacities based on arena history
  const getKnownCapacities = () => {
    if (arenaHistory.length < 2) {
      return {
        bleachers: null,
        lower_tier: null,
        courtside: null,
        luxury_boxes: null
      };
    }
    
    // Find the snapshot closest before and after the selected game date
    const selectedGameDate = selectedGame?.date ? new Date(selectedGame.date) : null;
    
    if (!selectedGameDate) {
      return {
        bleachers: null,
        lower_tier: null,
        courtside: null,
        luxury_boxes: null
      };
    }
    
    let beforeSnapshot = null;
    let afterSnapshot = null;
    
    // Sort snapshots by date
    const sortedSnapshots = [...arenaHistory].sort((a, b) => 
      new Date(a.created_at) - new Date(b.created_at)
    );
    
    for (let i = 0; i < sortedSnapshots.length; i++) {
      const snapshotDate = new Date(sortedSnapshots[i].created_at);
      
      if (snapshotDate <= selectedGameDate) {
        beforeSnapshot = sortedSnapshots[i];
      } else if (!afterSnapshot && snapshotDate > selectedGameDate) {
        afterSnapshot = sortedSnapshots[i];
        break;
      }
    }
    
    // If we don't have both before and after snapshots, use latest available
    if (!beforeSnapshot && !afterSnapshot) {
      return {
        bleachers: selectedSnapshot?.bleachers_capacity,
        lower_tier: selectedSnapshot?.lower_tier_capacity,
        courtside: selectedSnapshot?.courtside_capacity,
        luxury_boxes: selectedSnapshot?.luxury_boxes_capacity
      };
    }
    
    const before = beforeSnapshot || afterSnapshot;
    const after = afterSnapshot || beforeSnapshot;
    
    return {
      bleachers: before.bleachers_capacity === after.bleachers_capacity ? before.bleachers_capacity : null,
      lower_tier: before.lower_tier_capacity === after.lower_tier_capacity ? before.lower_tier_capacity : null,
      courtside: before.courtside_capacity === after.courtside_capacity ? before.courtside_capacity : null,
      luxury_boxes: before.luxury_boxes_capacity === after.luxury_boxes_capacity ? before.luxury_boxes_capacity : null
    };
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
            <div 
              className="stored-games-container"
              onMouseEnter={() => setShowStoredGamesPopover(true)}
              onMouseLeave={() => setShowStoredGamesPopover(false)}
            >
              <span>Stored Home Games: {storedGamesCount !== null ? storedGamesCount : '...'}</span>
              
              {showStoredGamesPopover && Object.keys(storedGamesBreakdown).length > 0 && (
                <div className="stored-games-popover">
                  <div className="popover-header">Stored Home Games by Season</div>
                  <div className="popover-content">
                    {Object.entries(storedGamesBreakdown)
                      .sort(([a], [b]) => parseInt(b) - parseInt(a))
                      .map(([season, count]) => (
                        <div key={season} className="season-breakdown">
                          <span className="season-label">Season {season}:</span>
                          <span className="game-count">{count} home games</span>
                        </div>
                      ))}
                  </div>
                  <div className="popover-total">
                    Total: {Object.values(storedGamesBreakdown).reduce((sum, count) => sum + count, 0)} home games
                  </div>
                </div>
              )}
            </div>
            <span>Current View: {formatDate(selectedSnapshot?.created_at)}</span>
          </div>
        </div>
      </div>

      {hasMultipleDistinctGroups && (
        <div className="snapshot-selector">
          <h3>Arena History ({arenaHistory.length} snapshots, {snapshotGroups.length} distinct configurations)</h3>
          <div className="snapshot-controls">
            <label htmlFor="snapshot-select">
              Select configuration:
              <select 
                id="snapshot-select"
                value={selectedSnapshot?.id || ''}
                onChange={(e) => handleSnapshotChange(e.target.value)}
              >
                {snapshotGroups.map((group) => (
                  <option key={group.representative.id} value={group.representative.id}>
                    {getSnapshotGroupLabel(group)} - Capacity: {formatNumber(group.representative.total_capacity)}
                  </option>
                ))}
              </select>
            </label>
          </div>
          
          <div className="snapshot-timeline">
            {snapshotGroups.map((group, index) => {
              const isSelected = group.snapshots.some(arena => arena.id === selectedSnapshot?.id);
              const isLatest = index === 0;
              
              return (
                <div 
                  key={group.representative.id}
                  className={`timeline-item ${isSelected ? 'selected' : ''} changed`}
                  onClick={() => setSelectedSnapshot(group.representative)}
                >
                  <div className="timeline-date">
                    {group.snapshots.length === 1 ? (
                      formatDate(group.representative.created_at)
                    ) : (
                      `${formatDate(group.endDate)} - ${formatDate(group.startDate)}`
                    )}
                  </div>
                  <div className="timeline-capacity">
                    Total: {formatNumber(group.representative.total_capacity)}
                    <span className="change-indicator">📊</span>
                    {group.snapshots.length > 1 && (
                      <span className="snapshot-count">({group.snapshots.length} snapshots)</span>
                    )}
                  </div>
                  {isLatest && <span className="latest-badge">Latest</span>}
                </div>
              );
            })}
          </div>

          {selectedGame && (
            <div className="auto-selection-notice">
              <span className="info-icon">ℹ️</span>
              Arena configuration automatically selected based on game date ({formatDate(selectedGame.date)})
            </div>
          )}
        </div>
      )}

      {!hasMultipleDistinctGroups && arenaHistory.length > 1 && (
        <div className="snapshot-info">
          <p className="single-config-notice">
            <span className="info-icon">✅</span>
            Arena configuration has remained unchanged across {arenaHistory.length} snapshots 
            (verified from {formatDate(snapshotGroups[0]?.endDate)} to {formatDate(snapshotGroups[0]?.startDate)})
          </p>
        </div>
      )}

      {error && (
        <div className="error">{error}</div>
      )}

      {selectedSnapshot && (
        <div className="arena-detail-content">
          <GameAttendanceSidebar 
            teamId={selectedSnapshot.team_id}
            onGameSelect={setSelectedGame}
            selectedGame={selectedGame}
            onStoredGamesUpdate={updateStoredGamesCount}
            appData={appData}
          />
          
          {/* Selected Game Info Panel */}
          {selectedGame && (
            <div className="selected-game-panel">
              <h3>🏀 Game Attendance Visualization</h3>
              <div className="game-info-grid">
                <div className="game-basic-info">
                  <p><strong>Opponent:</strong> {selectedGame.opponent}</p>
                  <p><strong>Date:</strong> {new Date(selectedGame.date).toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric'
                  })}</p>
                  <p><strong>Type:</strong> {selectedGame.type?.replace('league.', '').replace('rs', 'Regular Season') || 'Unknown'}</p>
                </div>
                
                {selectedGame.attendance && (
                  <div className="attendance-summary">
                    <h4>Attendance Summary</h4>
                    {(() => {
                      const knownCapacities = getKnownCapacities();
                      return (
                        <div className="attendance-grid">
                          <div className="attendance-item">
                            <span className="seat-type">Bleachers:</span>
                            <span className="seat-count">
                              {selectedGame.attendance.bleachers?.toLocaleString() || '0'}
                              {knownCapacities.bleachers ? 
                                ` / ${knownCapacities.bleachers.toLocaleString()}` :
                                ` / ${selectedSnapshot?.bleachers_capacity?.toLocaleString() || '?'}`
                              }
                            </span>
                            {!knownCapacities.bleachers && (
                              <span className="capacity-uncertain">±</span>
                            )}
                          </div>
                          <div className="attendance-item">
                            <span className="seat-type">Courtside:</span>
                            <span className="seat-count">
                              {selectedGame.attendance.courtside?.toLocaleString() || '0'}
                              {knownCapacities.courtside ? 
                                ` / ${knownCapacities.courtside.toLocaleString()}` :
                                ` / ${selectedSnapshot?.courtside_capacity?.toLocaleString() || '?'}`
                              }
                            </span>
                            {!knownCapacities.courtside && (
                              <span className="capacity-uncertain">±</span>
                            )}
                          </div>
                          <div className="attendance-item">
                            <span className="seat-type">Lower Tier:</span>
                            <span className="seat-count">
                              {selectedGame.attendance.lower_tier?.toLocaleString() || '0'}
                              {knownCapacities.lower_tier ? 
                                ` / ${knownCapacities.lower_tier.toLocaleString()}` :
                                ` / ${selectedSnapshot?.lower_tier_capacity?.toLocaleString() || '?'}`
                              }
                            </span>
                            {!knownCapacities.lower_tier && (
                              <span className="capacity-uncertain">±</span>
                            )}
                          </div>
                          <div className="attendance-item">
                            <span className="seat-type">Luxury Boxes:</span>
                            <span className="seat-count">
                              {selectedGame.attendance.luxury_boxes?.toLocaleString() || '0'}
                              {knownCapacities.luxury_boxes ? 
                                ` / ${knownCapacities.luxury_boxes.toLocaleString()}` :
                                ` / ${selectedSnapshot?.luxury_boxes_capacity?.toLocaleString() || '?'}`
                              }
                            </span>
                            {!knownCapacities.luxury_boxes && (
                              <span className="capacity-uncertain">±</span>
                            )}
                          </div>
                          <div className="attendance-item total">
                            <span className="seat-type">Total:</span>
                            <span className="seat-count">
                              {((selectedGame.attendance.bleachers || 0) +
                                (selectedGame.attendance.courtside || 0) + 
                                (selectedGame.attendance.lower_tier || 0) + 
                                (selectedGame.attendance.luxury_boxes || 0)).toLocaleString()}
                              {` / ${((knownCapacities.bleachers || selectedSnapshot?.bleachers_capacity || 0) +
                                     (knownCapacities.courtside || selectedSnapshot?.courtside_capacity || 0) +
                                     (knownCapacities.lower_tier || selectedSnapshot?.lower_tier_capacity || 0) +
                                     (knownCapacities.luxury_boxes || selectedSnapshot?.luxury_boxes_capacity || 0)).toLocaleString()}`}
                            </span>
                          </div>
                        </div>
                      );
                    })()}
                  </div>
                )}
                
                {selectedGame.revenue && (
                  <div className="revenue-info">
                    <p><strong>Revenue:</strong> ${selectedGame.revenue.toLocaleString()}</p>
                  </div>
                )}
                
                {selectedGame.error && (
                  <div className="game-error">
                    ⚠️ {selectedGame.error}
                  </div>
                )}
              </div>
            </div>
          )}
          
          <ArenaDesigner 
            initialSeatCounts={{
              courtside: selectedSnapshot.courtside_capacity,
              lowerTierTotal: selectedSnapshot.lower_tier_capacity,
              luxuryBoxCount: selectedSnapshot.luxury_boxes_capacity,
            }}
            readonly={true}
            attendanceData={selectedGame?.attendance}
            knownCapacities={selectedGame ? getKnownCapacities() : null}
          />
        </div>
      )}
    </div>
  );
};

export default ArenaDetailView;
