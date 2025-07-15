import React, { useState, useEffect, useCallback } from 'react';
import { arenaService } from '../services/arenaService';
// import ArenaDesigner from './ArenaDesigner'; // Temporarily disabled - moved to ArenaDesignerIntegration.jsx
import GameDataSidebar from './GameDataSidebar';
import './ArenaDetailView/ArenaDetailView.css';

const ArenaDetailView = ({ 
  selectedArena, 
  arena,
  onBackToList, 
  showBackButton = true,
  title,
  appData = null,
  onSidebarExpandedChange
}) => {
  const [arenaHistory, setArenaHistory] = useState([]);
  const [selectedSnapshot, setSelectedSnapshot] = useState(arena || selectedArena);
  const [selectedGame, setSelectedGame] = useState(null);
  const [storedGamesCount, setStoredGamesCount] = useState(null); // null means loading
  const [storedGamesBreakdown, setStoredGamesBreakdown] = useState({});
  const [showStoredGamesPopover, setShowStoredGamesPopover] = useState(false);
  const [prefixMaxAttendance, setPrefixMaxAttendance] = useState(null);
  const [error, setError] = useState(null);

  // Handle sidebar state changes for parent callback
  const handleSidebarExpandedChange = (expanded) => {
    if (onSidebarExpandedChange) {
      onSidebarExpandedChange(expanded);
    }
  };

  // Use either arena or selectedArena prop
  const currentArena = arena || selectedArena;

  // Update selected snapshot when arena prop changes
  useEffect(() => {
    if (arena) {
      setSelectedSnapshot(arena);
    } else if (selectedArena) {
      setSelectedSnapshot(selectedArena);
    }
  }, [arena, selectedArena]);

  // Close popover when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (showStoredGamesPopover && !event.target.closest('.stored-games-container')) {
        setShowStoredGamesPopover(false);
      }
    };

    if (showStoredGamesPopover) {
      document.addEventListener('click', handleClickOutside);
      return () => document.removeEventListener('click', handleClickOutside);
    }
  }, [showStoredGamesPopover]);

  const fetchStoredGamesBreakdown = useCallback(async () => {
    if (!currentArena?.team_id) return;
    
    try {
      // Use the efficient backend endpoint that queries the database directly
      const teamId = currentArena.team_id;
      const countData = await arenaService.getHomeGamesCountRobust(teamId);
      
      console.log(`Robust breakdown for team ${teamId}:`, countData.breakdown_by_season);
      setStoredGamesBreakdown(countData.breakdown_by_season || {});
      setStoredGamesCount(countData.total_home_games_count || 0);
    } catch (error) {
      console.error('Error fetching stored games breakdown:', error);
      setStoredGamesBreakdown({});
    }
  }, [currentArena?.team_id]);

  useEffect(() => {
    const fetchArenaHistory = async () => {
      if (!currentArena?.team_id) return;
      
      try {
        // Get arena history without loading state for better UX
        const [historyResponse] = await Promise.all([
          arenaService.getTeamArenaHistory(currentArena.team_id)
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
  }, [currentArena?.team_id, fetchStoredGamesBreakdown]);

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

  // Fetch prefix max attendance when game is selected
  useEffect(() => {
    const fetchPrefixMaxAttendance = async () => {
      if (!selectedGame?.date || !currentArena?.team_id) {
        setPrefixMaxAttendance(null);
        return;
      }
      
      try {
        const data = await arenaService.getPrefixMaxAttendance(currentArena.team_id, selectedGame.date);
        setPrefixMaxAttendance(data.prefix_max_attendance);
      } catch (error) {
        console.error('Error fetching prefix max attendance:', error);
        setPrefixMaxAttendance(null);
      }
    };

    fetchPrefixMaxAttendance();
  }, [selectedGame?.date, currentArena?.team_id]);

  const updateStoredGamesCount = async () => {
    if (!currentArena?.team_id) return;
    
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
    
    // We can only consider a capacity "known" if we have snapshots both before and after
    // the game date that show the same capacity, OR if we have a snapshot from exactly
    // the game date or very close to it
    if (!beforeSnapshot || !afterSnapshot) {
      // If we only have snapshots from one side of the game date, 
      // we cannot be certain about the exact capacities at game time
      return {
        bleachers: null,
        lower_tier: null,
        courtside: null,
        luxury_boxes: null
      };
    }
    
    // Only return known capacities if they're identical before and after the game
    return {
      bleachers: beforeSnapshot.bleachers_capacity === afterSnapshot.bleachers_capacity ? beforeSnapshot.bleachers_capacity : null,
      lower_tier: beforeSnapshot.lower_tier_capacity === afterSnapshot.lower_tier_capacity ? beforeSnapshot.lower_tier_capacity : null,
      courtside: beforeSnapshot.courtside_capacity === afterSnapshot.courtside_capacity ? beforeSnapshot.courtside_capacity : null,
      luxury_boxes: beforeSnapshot.luxury_boxes_capacity === afterSnapshot.luxury_boxes_capacity ? beforeSnapshot.luxury_boxes_capacity : null
    };
  };

  // Function to determine if a capacity is effectively "known" based on attendance and snapshots
  const getEffectiveCapacities = () => {
    const knownCapacities = getKnownCapacities();
    const attendance = selectedGame?.attendance;
    
    if (!attendance || !selectedSnapshot) {
      return knownCapacities;
    }
    
    const result = { ...knownCapacities };
    
    // If attendance equals the capacity from our snapshot, and we only have snapshots after the game,
    // then we can be certain this was the actual capacity (can't sell more seats than exist)
    const checkAttendanceEqualsCapacity = (attendanceValue, snapshotCapacity, knownCapacity, prefixMax) => {
      if (knownCapacity !== null) return knownCapacity; // Already known from history
      if (attendanceValue === snapshotCapacity) return snapshotCapacity; // Attendance = capacity means it's known
      
      // Check if prefix max provides a tighter bound than current attendance
      // If historical max > current attendance and historical max = snapshot capacity,
      // then we know the capacity was at least the historical max
      if (prefixMax && prefixMax > attendanceValue && prefixMax === snapshotCapacity) {
        return snapshotCapacity; // Historical evidence confirms this capacity
      }
      
      return null; // Still uncertain
    };
    
    const prefixMax = prefixMaxAttendance || {};
    
    result.bleachers = checkAttendanceEqualsCapacity(
      attendance.bleachers, 
      selectedSnapshot.bleachers_capacity, 
      knownCapacities.bleachers,
      prefixMax.bleachers
    );
    result.courtside = checkAttendanceEqualsCapacity(
      attendance.courtside, 
      selectedSnapshot.courtside_capacity, 
      knownCapacities.courtside,
      prefixMax.courtside
    );
    result.lower_tier = checkAttendanceEqualsCapacity(
      attendance.lower_tier, 
      selectedSnapshot.lower_tier_capacity, 
      knownCapacities.lower_tier,
      prefixMax.lower_tier
    );
    result.luxury_boxes = checkAttendanceEqualsCapacity(
      attendance.luxury_boxes, 
      selectedSnapshot.luxury_boxes_capacity, 
      knownCapacities.luxury_boxes,
      prefixMax.luxury_boxes
    );
    
    return result;
  };

  // Helper function to generate informative tooltips for uncertain capacities
  const getCapacityTooltip = (sectionName, attendance, snapshotCapacity, prefixMax) => {
    const parts = ['Capacity at game time uncertain'];
    
    // Add information about the upper bound
    parts.push(`Upper bound: ≤${snapshotCapacity?.toLocaleString()} (from later arena snapshot)`);
    
    // Calculate the maximum (most restrictive) lower bound
    const attendanceBound = attendance || 0;
    const prefixMaxBound = prefixMax || 0;
    const maxLowerBound = Math.max(attendanceBound, prefixMaxBound);
    
    if (maxLowerBound > 0) {
      let boundSource = '';
      if (attendanceBound === maxLowerBound && prefixMaxBound === maxLowerBound) {
        boundSource = 'actual attendance and max previous attendance';
      } else if (attendanceBound === maxLowerBound) {
        boundSource = 'actual attendance at this game';
      } else {
        boundSource = 'max attendance in previous games';
      }
      
      parts.push(`Lower bound: ≥${maxLowerBound.toLocaleString()} (from ${boundSource})`);
    }
    
    return parts.join('\n');
  };

  return (
    <div className="arena-detail-view">
      <div className="detail-header">
        {showBackButton && onBackToList && (
          <button onClick={onBackToList} className="back-button">
            ← Back to Arena List
          </button>
        )}
        
        <div className="arena-title">
          <h2>{title || selectedSnapshot?.arena_name || `Arena ${selectedSnapshot?.id}`}</h2>
          <div className="arena-meta">
            <span>Team ID: {selectedSnapshot?.team_id}</span>
            <span>Total Capacity: {formatNumber(selectedSnapshot?.total_capacity)}</span>
            <div 
              className={`stored-games-container ${showStoredGamesPopover ? 'active' : ''}`}
              onClick={(e) => {
                e.stopPropagation();
                setShowStoredGamesPopover(!showStoredGamesPopover);
              }}
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
          <GameDataSidebar 
            teamId={selectedSnapshot.team_id}
            onGameSelect={setSelectedGame}
            selectedGame={selectedGame}
            onStoredGamesUpdate={updateStoredGamesCount}
            appData={appData}
            onExpandedChange={handleSidebarExpandedChange}
          />
          
          {/* Selected Game Info Panel */}
          {selectedGame && (
            <div className="selected-game-panel">
              <h3>🏀 Game Data Visualization</h3>
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
                  <div className="game-data-summary">
                    <h4>Game Data Summary</h4>
                    {(() => {
                      const effectiveCapacities = getEffectiveCapacities();
                      const prefixMax = prefixMaxAttendance || {};
                      const pricing = selectedGame.pricing || {};
                      
                      // Calculate totals
                      const totalAttendance = (selectedGame.attendance.bleachers || 0) +
                                            (selectedGame.attendance.courtside || 0) + 
                                            (selectedGame.attendance.lower_tier || 0) + 
                                            (selectedGame.attendance.luxury_boxes || 0);
                      
                      const totalCapacity = (effectiveCapacities.bleachers || selectedSnapshot?.bleachers_capacity || 0) +
                                          (effectiveCapacities.courtside || selectedSnapshot?.courtside_capacity || 0) +
                                          (effectiveCapacities.lower_tier || selectedSnapshot?.lower_tier_capacity || 0) +
                                          (effectiveCapacities.luxury_boxes || selectedSnapshot?.luxury_boxes_capacity || 0);
                      
                      // Calculate revenue breakdown if we have both attendance and pricing
                      let totalRevenue = 0;
                      const revenueBreakdown = {};
                      if (pricing.bleachers && selectedGame.attendance.bleachers) {
                        revenueBreakdown.bleachers = pricing.bleachers * selectedGame.attendance.bleachers;
                        totalRevenue += revenueBreakdown.bleachers;
                      }
                      if (pricing.lower_tier && selectedGame.attendance.lower_tier) {
                        revenueBreakdown.lower_tier = pricing.lower_tier * selectedGame.attendance.lower_tier;
                        totalRevenue += revenueBreakdown.lower_tier;
                      }
                      if (pricing.courtside && selectedGame.attendance.courtside) {
                        revenueBreakdown.courtside = pricing.courtside * selectedGame.attendance.courtside;
                        totalRevenue += revenueBreakdown.courtside;
                      }
                      if (pricing.luxury_boxes && selectedGame.attendance.luxury_boxes) {
                        revenueBreakdown.luxury_boxes = pricing.luxury_boxes * selectedGame.attendance.luxury_boxes;
                        totalRevenue += revenueBreakdown.luxury_boxes;
                      }
                      
                      return (
                        <div className="game-data-table">
                          <table className="data-table">
                            <thead>
                              <tr>
                                <th>Metric</th>
                                <th>Bleachers</th>
                                <th>Lower Tier</th>
                                <th>Courtside</th>
                                <th>Luxury Boxes</th>
                                <th>Total</th>
                              </tr>
                            </thead>
                            <tbody>
                              {/* Pricing Row */}
                              {Object.keys(pricing).length > 0 && (
                                <tr className="pricing-row">
                                  <td className="metric-label">Price</td>
                                  <td className="price-cell">
                                    {pricing.bleachers ? `$${pricing.bleachers}` : '-'}
                                  </td>
                                  <td className="price-cell">
                                    {pricing.lower_tier ? `$${pricing.lower_tier}` : '-'}
                                  </td>
                                  <td className="price-cell">
                                    {pricing.courtside ? `$${pricing.courtside}` : '-'}
                                  </td>
                                  <td className="price-cell">
                                    {pricing.luxury_boxes ? `$${pricing.luxury_boxes}` : '-'}
                                  </td>
                                  <td className="price-cell total-cell">
                                    -
                                  </td>
                                </tr>
                              )}
                              
                              {/* Attendance Row */}
                              <tr className="attendance-row">
                                <td className="metric-label">Attendance</td>
                                <td className="attendance-cell">
                                  <div className="attendance-value">
                                    {selectedGame.attendance.bleachers?.toLocaleString() || '0'}
                                    {effectiveCapacities.bleachers ? 
                                      ` / ${effectiveCapacities.bleachers.toLocaleString()}` :
                                      ` / `}
                                    {!effectiveCapacities.bleachers && (
                                      <span 
                                        className="capacity-estimate" 
                                        title={getCapacityTooltip('Bleachers', selectedGame.attendance.bleachers, selectedSnapshot?.bleachers_capacity, prefixMax.bleachers)}
                                      >
                                        ≤{selectedSnapshot?.bleachers_capacity?.toLocaleString() || '?'}
                                      </span>
                                    )}
                                  </div>
                                </td>
                                <td className="attendance-cell">
                                  <div className="attendance-value">
                                    {selectedGame.attendance.lower_tier?.toLocaleString() || '0'}
                                    {effectiveCapacities.lower_tier ? 
                                      ` / ${effectiveCapacities.lower_tier.toLocaleString()}` :
                                      ` / `}
                                    {!effectiveCapacities.lower_tier && (
                                      <span 
                                        className="capacity-estimate" 
                                        title={getCapacityTooltip('Lower Tier', selectedGame.attendance.lower_tier, selectedSnapshot?.lower_tier_capacity, prefixMax.lower_tier)}
                                      >
                                        ≤{selectedSnapshot?.lower_tier_capacity?.toLocaleString() || '?'}
                                      </span>
                                    )}
                                  </div>
                                </td>
                                <td className="attendance-cell">
                                  <div className="attendance-value">
                                    {selectedGame.attendance.courtside?.toLocaleString() || '0'}
                                    {effectiveCapacities.courtside ? 
                                      ` / ${effectiveCapacities.courtside.toLocaleString()}` :
                                      ` / `}
                                    {!effectiveCapacities.courtside && (
                                      <span 
                                        className="capacity-estimate" 
                                        title={getCapacityTooltip('Courtside', selectedGame.attendance.courtside, selectedSnapshot?.courtside_capacity, prefixMax.courtside)}
                                      >
                                        ≤{selectedSnapshot?.courtside_capacity?.toLocaleString() || '?'}
                                      </span>
                                    )}
                                  </div>
                                </td>
                                <td className="attendance-cell">
                                  <div className="attendance-value">
                                    {selectedGame.attendance.luxury_boxes?.toLocaleString() || '0'}
                                    {effectiveCapacities.luxury_boxes ? 
                                      ` / ${effectiveCapacities.luxury_boxes.toLocaleString()}` :
                                      ` / `}
                                    {!effectiveCapacities.luxury_boxes && (
                                      <span 
                                        className="capacity-estimate" 
                                        title={getCapacityTooltip('Luxury Boxes', selectedGame.attendance.luxury_boxes, selectedSnapshot?.luxury_boxes_capacity, prefixMax.luxury_boxes)}
                                      >
                                        ≤{selectedSnapshot?.luxury_boxes_capacity?.toLocaleString() || '?'}
                                      </span>
                                    )}
                                  </div>
                                </td>
                                <td className="attendance-cell total-cell">
                                  <div className="attendance-value">
                                    {totalAttendance.toLocaleString()} / {totalCapacity.toLocaleString()}
                                  </div>
                                </td>
                              </tr>
                              
                              {/* Revenue Row */}
                              {(Object.keys(revenueBreakdown).length > 0 || selectedGame.revenue) && (
                                <tr className="revenue-row">
                                  <td className="metric-label">Revenue</td>
                                  <td className="revenue-cell">
                                    {revenueBreakdown.bleachers ? `$${revenueBreakdown.bleachers.toLocaleString()}` : '-'}
                                  </td>
                                  <td className="revenue-cell">
                                    {revenueBreakdown.lower_tier ? `$${revenueBreakdown.lower_tier.toLocaleString()}` : '-'}
                                  </td>
                                  <td className="revenue-cell">
                                    {revenueBreakdown.courtside ? `$${revenueBreakdown.courtside.toLocaleString()}` : '-'}
                                  </td>
                                  <td className="revenue-cell">
                                    {revenueBreakdown.luxury_boxes ? `$${revenueBreakdown.luxury_boxes.toLocaleString()}` : '-'}
                                  </td>
                                  <td className="revenue-cell total-cell">
                                    {selectedGame.revenue ? 
                                      `$${selectedGame.revenue.toLocaleString()}` : 
                                      (totalRevenue > 0 ? `$${totalRevenue.toLocaleString()}` : '-')}
                                  </td>
                                </tr>
                              )}
                            </tbody>
                          </table>
                          
                          {/* Revenue Note */}
                          {selectedGame.revenue && selectedGame.type !== 'league.rs' && (
                            <div className="revenue-note">
                              <span className="info-icon">ℹ️</span>
                              <span className="note-text">
                                Revenue calculation only applies to regular season home league games
                              </span>
                            </div>
                          )}
                        </div>
                      );
                    })()}
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
          
          {/* ArenaDesigner temporarily disabled - preserved in ArenaDesignerIntegration.jsx for future use
          <ArenaDesigner 
            initialSeatCounts={{
              courtside: selectedSnapshot.courtside_capacity,
              lowerTierTotal: selectedSnapshot.lower_tier_capacity,
              luxuryBoxCount: selectedSnapshot.luxury_boxes_capacity,
            }}
            readonly={true}
            attendanceData={selectedGame?.attendance}
            knownCapacities={selectedGame ? getEffectiveCapacities() : null}
          />
          */}
        </div>
      )}
    </div>
  );
};

export default ArenaDetailView;
