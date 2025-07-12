import React, { useState, useEffect } from 'react';
import { arenaService } from '../services/arenaService';
import LoadingSpinner from './LoadingSpinner';
import './GameAttendanceSidebar.css';

const GameAttendanceSidebar = ({ 
  teamId, 
  onGameSelect, 
  selectedGame, 
  onStoredGamesUpdate,
  appData,
  onExpandedChange
}) => {
  const [games, setGames] = useState([]);
  const [storedGames, setStoredGames] = useState(new Set());
  const [season, setSeason] = useState(null);
  const [debouncedSeason, setDebouncedSeason] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingGame, setLoadingGame] = useState(null);
  const [collectingAll, setCollectingAll] = useState(false);
  const [error, setError] = useState(null);
  const [expanded, setExpanded] = useState(true);
  const [showSeasonMenu, setShowSeasonMenu] = useState(false);
  const [extendedRange, setExtendedRange] = useState(false);

  // Get seasons data from appData or use fallbacks
  const seasonsData = appData?.seasons || { current: 69, min: 54, max: 69 };
  const currentSeason = seasonsData.current;
  const minSeason = extendedRange ? 5 : seasonsData.min;
  const maxSeason = seasonsData.max;

  // Initialize season to current season when appData is available
  useEffect(() => {
    if (currentSeason && !season) {
      setSeason(currentSeason);
      setDebouncedSeason(currentSeason);
    }
  }, [currentSeason, season]);

  // Notify parent of expanded state changes
  useEffect(() => {
    if (onExpandedChange) {
      onExpandedChange(expanded);
    }
  }, [expanded, onExpandedChange]);

  // Debounce season changes to avoid excessive API calls
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSeason(season);
    }, 500); // 500ms debounce

    return () => clearTimeout(timer);
  }, [season]);

  useEffect(() => {
    const fetchTeamSchedule = async (seasonNumber = null) => {
      if (!teamId) return;
      
      try {
        setLoading(true);
        setError(null);
        
        // Use current season if no specific season provided
        const targetSeason = seasonNumber || currentSeason;
        if (!targetSeason) return; // Wait for current season to be loaded
        
        // Fetch team schedule
        const scheduleData = await arenaService.getTeamSchedule(teamId, targetSeason);
        
        // Filter for home games only (excluding BBM games which are played in neutral venues) and sort by date
        const homeGames = scheduleData.games
          .filter(game => game.home && game.type !== 'bbm')
          .sort((a, b) => new Date(a.date) - new Date(b.date));
        
        setGames(homeGames);
        
        // Use the new accurate check-stored endpoint for precise stored status
        const allGameIds = homeGames.map(g => g.id);
        console.log('Schedule game IDs:', allGameIds);
        console.log('Total games in schedule:', homeGames.length);
        
        if (allGameIds.length > 0) {
          // Check all games at once with the accurate endpoint
          const storedStatus = await arenaService.checkGamesStored(teamId, allGameIds);
          const verifiedStoredIds = new Set();
          
          Object.entries(storedStatus).forEach(([gameId, isStored]) => {
            if (isStored) {
              verifiedStoredIds.add(gameId);
            }
          });
          
          console.log(`Accurate check found ${verifiedStoredIds.size} stored games out of ${allGameIds.length} total games`);
          console.log('Stored game IDs:', Array.from(verifiedStoredIds));
          
          setStoredGames(verifiedStoredIds);
        } else {
          setStoredGames(new Set());
        }
        
      } catch (err) {
        setError('Failed to fetch team schedule');
        console.error('Error fetching schedule:', err);
      } finally {
        setLoading(false);
      }
    };

    // Only fetch if we have teamId and a debounced season
    if (teamId && debouncedSeason) {
      fetchTeamSchedule(debouncedSeason);
    }
  }, [teamId, debouncedSeason, currentSeason]);

  const handleSeasonChange = (e) => {
    const newSeason = parseInt(e.target.value);
    setSeason(newSeason);
    // fetchTeamSchedule will be called automatically via useEffect
  };

  const handleSeasonNavigation = (direction) => {
    if (!season) return;
    
    const newSeason = direction === 'prev' ? season - 1 : season + 1;
    
    // Check bounds
    if (newSeason < minSeason || newSeason > maxSeason) return;
    
    setSeason(newSeason);
  };

  const handleSeasonMenuToggle = (e) => {
    e.stopPropagation();
    setShowSeasonMenu(!showSeasonMenu);
  };

  const handleExtendRange = () => {
    setExtendedRange(true);
    setShowSeasonMenu(false);
  };

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = () => {
      setShowSeasonMenu(false);
    };

    if (showSeasonMenu) {
      document.addEventListener('click', handleClickOutside);
      return () => document.removeEventListener('click', handleClickOutside);
    }
  }, [showSeasonMenu]);

  const handleGameClick = async (game) => {
    try {
      setLoadingGame(game.id);
      const startTime = Date.now();
      
      // Check if game is already known to be stored to avoid unnecessary API calls
      const wasAlreadyKnownStored = storedGames.has(game.id);
      
      const boxscoreData = await arenaService.getGameBoxscore(game.id);
      const loadTime = Date.now() - startTime;
      const wasFromDatabase = loadTime < 200;
      
      onGameSelect({
        ...game,
        attendance: boxscoreData.attendance,
        revenue: boxscoreData.revenue
      });
      
      // Update stored status if it changed
      if (!wasAlreadyKnownStored) {
        const storedStatus = await arenaService.checkGamesStored(teamId, [game.id]);
        if (storedStatus[game.id]) {
          setStoredGames(prev => new Set([...prev, game.id]));
        }
      }
      
      // Only update parent component if we newly stored a game (not already known as stored)
      if (!wasFromDatabase && !wasAlreadyKnownStored && onStoredGamesUpdate) {
        await onStoredGamesUpdate();
      }
    } catch (err) {
      console.error('Error fetching game attendance:', err);
      onGameSelect({
        ...game,
        attendance: null,
        error: 'Failed to load attendance data'
      });
    } finally {
      setLoadingGame(null);
    }
  };

  const handleCollectAllGames = async () => {
    try {
      setCollectingAll(true);
      setError(null);
      const completedGames = games.filter(game => {
        const gameDate = new Date(game.date);
        return gameDate < new Date() && !storedGames.has(game.id);
      });
      if (completedGames.length === 0) {
        setError('No completed games to collect');
        return;
      }
      let collected = 0;
      let failed = 0;
      for (const game of completedGames) {
        try {
          await arenaService.getGameBoxscore(game.id);
          // Re-check stored status after fetch
          const storedStatus = await arenaService.checkGamesStored(teamId, [game.id]);
          if (storedStatus[game.id]) {
            setStoredGames(prev => new Set([...prev, game.id]));
            collected++;
          } else {
            failed++;
          }
          await new Promise(resolve => setTimeout(resolve, 200));
        } catch (err) {
          console.error(`Failed to collect game ${game.id}:`, err);
          failed++;
        }
      }
      if (failed === 0) {
        setError(null);
      } else {
        setError(`Collected ${collected} games, ${failed} failed`);
      }
      if (onStoredGamesUpdate) {
        await onStoredGamesUpdate();
      }
    } catch (err) {
      setError('Failed to collect games');
      console.error('Error collecting games:', err);
    } finally {
      setCollectingAll(false);
    }
  };

  // Calculate collect button state
  const getCollectButtonInfo = () => {
    const completedGames = games.filter(game => {
      const gameDate = new Date(game.date);
      return gameDate < new Date();
    });
    
    const completedButNotStored = completedGames.filter(game => !storedGames.has(game.id));
    
    const totalGames = games.length;
    const storedCount = games.filter(game => storedGames.has(game.id)).length;
    const remainingToCollect = completedButNotStored.length;
    
    const allStored = remainingToCollect === 0 && completedGames.length > 0;
    const noCompletedGames = completedGames.length === 0;
    
    let buttonText = '📥 Collect All Remaining';
    let isDisabled = collectingAll;
    let title = 'Manually collect attendance data for all completed games that are not yet stored';
    
    if (noCompletedGames) {
      buttonText = '📥 No completed games';
      isDisabled = true;
      title = 'No completed games to collect';
    } else if (allStored) {
      buttonText = '✅ All collected';
      isDisabled = true;
      title = 'All completed games already have attendance data stored';
    } else if (remainingToCollect > 0) {
      buttonText = `📥 Collect ${remainingToCollect} Remaining`;
      title = `Manually collect attendance for ${remainingToCollect} completed games (${storedCount}/${totalGames} already stored). Games will turn green as they are collected.`;
    }
    
    return { buttonText, isDisabled, title, remainingToCollect, storedCount, totalGames };
  };

  const collectButtonInfo = getCollectButtonInfo();

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: '2-digit'
    });
  };

  const formatTime = (dateString) => {
    if (!dateString) return '';
    return new Date(dateString).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getGameTypeLabel = (type) => {
    switch (type) {
      case 'league.rs': return 'League';
      case 'league.playoffs': return 'Playoffs';
      case 'cup': return 'Cup';
      case 'scrimmage': return 'Scrimmage';
      default: return type;
    }
  };

  return (
    <div className={`game-attendance-sidebar ${expanded ? 'expanded' : 'collapsed'}`}>
      <div className="sidebar-header">
        <h3>🏀 Game Attendance</h3>
        <button 
          className="toggle-button"
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? '▶' : '◀'}
        </button>
      </div>

      {expanded && (
        <div className="sidebar-content">
          <div className="season-selector">
            <label htmlFor="season-slider">
              <div className="season-header">
                <span>Season: {season || currentSeason || 'Loading...'}</span>
                <div className="season-nav-buttons">
                  <button 
                    className="season-nav-button"
                    onClick={() => handleSeasonNavigation('prev')}
                    disabled={!season || season <= minSeason}
                    title="Previous season"
                  >
                    ‹
                  </button>
                  <button 
                    className="season-nav-button"
                    onClick={() => handleSeasonNavigation('next')}
                    disabled={!season || season >= maxSeason}
                    title="Next season"
                  >
                    ›
                  </button>
                </div>
              </div>
              <input
                id="season-slider"
                type="range"
                min={minSeason}
                max={maxSeason}
                value={season || currentSeason || maxSeason}
                onChange={handleSeasonChange}
                className="season-slider"
              />
              <div className="season-range-labels">
                <span>{minSeason}</span>
                <span>{maxSeason}</span>
              </div>
            </label>
            <div className="field-help-container">
              <span className="field-help">Use slider to select season</span>
              <div className="season-menu-container">
                <button 
                  className="season-menu-button"
                  onClick={handleSeasonMenuToggle}
                  title="Season options"
                  hidden={extendedRange || minSeason <= 5}
                >
                  ⋯
                </button>
                {showSeasonMenu && (
                  <div className="season-menu">
                    <button 
                      className="season-menu-item"
                      onClick={handleExtendRange}
                      disabled={extendedRange}
                    >
                      {extendedRange ? '✓ Extended' : 'Extend to Past'}
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>

          {loading && (
            <LoadingSpinner size="medium" message="Loading games..." />
          )}

          {error && (
            <div className="error">{error}</div>
          )}

          {!loading && !error && (
            <div className="games-list">
              <div className="games-header">
                <span className="games-count">Home Games ({games.length})</span>
                <button 
                  className="collect-all-button"
                  onClick={handleCollectAllGames}
                  disabled={collectButtonInfo.isDisabled}
                  title={collectButtonInfo.title}
                >
                  {collectButtonInfo.buttonText}
                </button>
              </div>
              
              {games.length === 0 ? (
                <div className="no-games">No home games found</div>
              ) : (
                games.map((game) => {
                  const isSelected = selectedGame?.id === game.id;
                  const isLoading = loadingGame === game.id;
                  const isStored = storedGames.has(game.id);
                  const gameDate = new Date(game.date);
                  const isCompleted = gameDate < new Date();
                  
                  return (
                    <div
                      key={game.id}
                      id={`game-${game.id}`}
                      className={`game-item ${isSelected ? 'selected' : ''} ${!isCompleted ? 'upcoming' : ''} ${isLoading ? 'loading' : ''} ${isStored ? 'stored' : ''}`}
                      onClick={() => !isLoading && handleGameClick(game)}
                    >
                      <div className="game-date">
                        <span className="date">{formatDate(game.date)}</span>
                        <span className="time">{formatTime(game.date)}</span>
                      </div>
                      
                      <div className="game-info">
                        <div className="opponent">vs {game.opponent}</div>
                        <div className="game-type">{getGameTypeLabel(game.type)}</div>
                        <div className="game-id">ID: {game.id}</div>
                      </div>
                      
                      {!isCompleted && (
                        <div className="upcoming-badge">Upcoming</div>
                      )}
                      
                      {isLoading && (
                        <div className="loading-indicator">
                          ⏳
                        </div>
                      )}
                      
                      {isStored && !isLoading && (
                        <div className="stored-indicator">
                          💾
                        </div>
                      )}
                      
                      {isCompleted && !isLoading && !isStored && (
                        <div className="attendance-indicator">
                          📊
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default GameAttendanceSidebar;
