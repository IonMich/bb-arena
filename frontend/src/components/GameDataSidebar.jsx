import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { arenaService } from '../services/arenaService';
import LoadingSpinner from './LoadingSpinner';
import './GameDataSidebar.css';

const GameDataSidebar = ({ 
  teamId, 
  onGameSelect, 
  selectedGame, 
  onStoredGamesUpdate,
  appData,
  onExpandedChange,
  teamLeagueHistory,
  currentLeagueInfo,
  onLeagueHistoryUpdate,
  onSeasonChange,
  refreshKey
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
  const [teamSeasonsData, setTeamSeasonsData] = useState(null);

  // Get seasons data from appData or use fallbacks
  const seasonsData = appData?.seasons || { current: 69, min: 54, max: 69 };
  const currentSeason = seasonsData.current;
  
  // Use team-specific minimum season if available, otherwise fall back to appData
  const teamMinSeason = teamSeasonsData?.team_min_season;
  const effectiveMinSeason = teamMinSeason || seasonsData.min;
  const minSeason = extendedRange ? 5 : effectiveMinSeason;
  const maxSeason = seasonsData.max;

  // Initialize season to current season when appData is available
  useEffect(() => {
    if (currentSeason && !season) {
      setSeason(currentSeason);
      setDebouncedSeason(currentSeason);
    }
  }, [currentSeason, season]);

  // Fetch team-specific seasons data when teamId changes
  useEffect(() => {
    const fetchTeamSeasons = async () => {
      if (!teamId) return;
      
      try {
        const teamSeasons = await arenaService.getSeasonsForTeam(teamId);
        setTeamSeasonsData(teamSeasons);
      } catch (error) {
        console.warn('Could not fetch team-specific seasons, using fallback:', error);
        // Keep teamSeasonsData as null to use fallback
      }
    };

    fetchTeamSeasons();
  }, [teamId]);

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

  // Define fetchTeamSchedule as a useCallback so it can be used in multiple useEffects
  const fetchTeamSchedule = useCallback(async (seasonNumber = null) => {
    if (!teamId) return;
    
    try {
      setLoading(true);
      setError(null);
      
      // Use current season if no specific season provided
      const targetSeason = seasonNumber || currentSeason;
      if (!targetSeason) return; // Wait for current season to be loaded
      
      // Fetch both team schedule and stored games in parallel
      const [scheduleData, storedGamesData] = await Promise.all([
        arenaService.getTeamSchedule(teamId, targetSeason),
        arenaService.getTeamStoredGames(teamId, targetSeason, 500)
      ]);
      
      // Filter for home games only (excluding BBM games which are played in neutral venues) and sort by date
      console.log(scheduleData);
      const homeGames = scheduleData.games
        .filter(game => game.home && game.type !== 'bbm' && game.type !== 'pl.rsneutral')
        .sort((a, b) => new Date(a.date) - new Date(b.date));
      
      // Create a map of stored games by ID for efficient lookup
      const storedGamesMap = new Map();
      const storedGameIds = new Set();
      
      storedGamesData.games.forEach(storedGame => {
        storedGamesMap.set(storedGame.id, storedGame);
        storedGameIds.add(storedGame.id);
      });
      
      // Merge schedule data with stored game data (including revenue)
      const enrichedGames = homeGames.map(game => {
        const storedGame = storedGamesMap.get(game.id);
        if (storedGame) {
          // Merge schedule data with stored data, prioritizing stored data for attendance/revenue
          return {
            ...game,
            calculated_revenue: storedGame.calculated_revenue,
            attendance: storedGame.attendance,
            pricing: storedGame.pricing
          };
        }
        return game;
      });
      
      setGames(enrichedGames);
      
      // Use the new accurate check-stored endpoint for precise stored status
      const allGameIds = homeGames.map(g => g.id);
      
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
      
      // Auto-collect league history for past seasons if missing (not for current season)
      // Current season data comes from team_info table, not from team history webpage
      if (targetSeason !== currentSeason) {
        try {
          // Always notify parent to ensure historical data is available for past seasons
          if (onLeagueHistoryUpdate) {
            // Trigger parent to fetch/refresh historical data for this season
            onLeagueHistoryUpdate();
          }
          
          // Check current league history state for the target season
          const currentHistory = await arenaService.getTeamLeagueHistory(teamId, false);
          const hasSeasonData = currentHistory?.history?.some(entry => entry.season === targetSeason);
          
          if (!hasSeasonData) {
            console.log(`[GameDataSidebar] No historical league data found for team ${teamId} season ${targetSeason}, attempting to collect from team history webpage...`);
            try {
              const collectResult = await arenaService.collectTeamLeagueHistory(teamId);
              console.log('[GameDataSidebar] Team league history collection result:', collectResult);
              
              // Notify parent component again if collection was successful
              if (collectResult.success && onLeagueHistoryUpdate) {
                onLeagueHistoryUpdate();
              }
            } catch (collectError) {
              console.warn('[GameDataSidebar] Failed to auto-collect team league history:', collectError);
              // Don't show error to user for automatic collection - it's best effort
            }
          }
        } catch (historyCheckError) {
          console.warn('[GameDataSidebar] Failed to check league history for auto-collection:', historyCheckError);
        }
      } else {
        // Skip auto-collection for current season - use team_info data instead
      }
      
    } catch (err) {
      setError('Failed to fetch team schedule');
      console.error('Error fetching schedule:', err);
    } finally {
      setLoading(false);
    }
  }, [teamId, currentSeason, onLeagueHistoryUpdate]);

  useEffect(() => {
    // Only fetch if we have teamId and a debounced season
    if (teamId && debouncedSeason) {
      fetchTeamSchedule(debouncedSeason);
    }
  }, [teamId, debouncedSeason, fetchTeamSchedule]);

  // Refresh game data when refreshKey changes (e.g., after pricing collection)
  useEffect(() => {
    if (refreshKey > 0 && teamId && debouncedSeason) {
      console.log('Refreshing game data due to external trigger (refreshKey:', refreshKey, ')');
      fetchTeamSchedule(debouncedSeason);
    }
  }, [refreshKey, teamId, debouncedSeason, fetchTeamSchedule]);

  const handleSeasonChange = (e) => {
    const newSeason = parseInt(e.target.value);
    setSeason(newSeason);
    
    // Notify parent component about season change
    if (onSeasonChange) {
      onSeasonChange(newSeason);
    }
    // fetchTeamSchedule will be called automatically via useEffect
  };

  const handleSeasonNavigation = (direction) => {
    if (!season) return;
    
    const newSeason = direction === 'prev' ? season - 1 : season + 1;
    
    // Check bounds
    if (newSeason < minSeason || newSeason > maxSeason) return;
    
    setSeason(newSeason);
    
    // Notify parent component about season change
    if (onSeasonChange) {
      onSeasonChange(newSeason);
    }
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
        calculated_revenue: boxscoreData.calculated_revenue,
        pricing: boxscoreData.pricing,
        season: season || currentSeason // Add season context
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
        error: 'Failed to load attendance data',
        season: season || currentSeason // Add season context
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

  // Get league name for a specific season (memoized to prevent excessive calls)
  const getLeagueNameForSeason = useMemo(() => {
    return (seasonNumber) => {
      if (!seasonNumber) return null;
      
      // For current season, get league name from team_info directly
      if (seasonNumber === currentSeason && currentLeagueInfo?.league_name) {
        return currentLeagueInfo.league_name;
      }
      
      // For past seasons, check historical data
      if (!teamLeagueHistory?.history) return null;
      const seasonEntry = teamLeagueHistory.history.find(entry => entry.season === seasonNumber);
      return seasonEntry?.league_name || null;
    };
  }, [currentSeason, currentLeagueInfo?.league_name, teamLeagueHistory?.history]);

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
    // For league games, try to include the league name
    if (type?.startsWith('league.')) {
      let baseLabel;
      
      switch (type) {
        case 'league.rs':
          baseLabel = 'League';
          break;
        case 'league.rs.tv':
          baseLabel = 'League (TV)';
          break;
        case 'league.relegation':
          baseLabel = 'Relegation';
          break;
        case 'league.quarterfinal':
          baseLabel = 'Quarterfinal';
          break;
        case 'league.semifinal':
          baseLabel = 'Semifinal';
          break;
        case 'league.final':
          baseLabel = 'Final';
          break;
        case 'league.playoffs':
          baseLabel = 'Playoffs';
          break;
        default:
          baseLabel = 'League';
      }
      
      // Use the league name from the current season context (since all games in this view are from the same season)
      const currentLeagueName = getLeagueNameForSeason(season || currentSeason);
      if (currentLeagueName) {
        return `${baseLabel} - ${currentLeagueName}`;
      }
      
      return baseLabel;
    }
    
    switch (type) {
      case 'cup': return 'Cup';
      case 'scrimmage': return 'Scrimmage';
      default: return type;
    }
  };

  return (
    <div className={`game-data-sidebar ${expanded ? 'expanded' : 'collapsed'}`}>
      <div className="sidebar-header">
        <h3>🏀 Game Data</h3>
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
                <span>
                  Season: {season || currentSeason || 'Loading...'}
                  {(() => {
                    const leagueName = getLeagueNameForSeason(season || currentSeason);
                    return leagueName ? ` - ${leagueName}` : '';
                  })()}
                </span>
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
                        <div className="game-main-row">
                          <div className="game-details">
                            <div className="opponent">vs {game.opponent}</div>
                            <div className="game-type">{getGameTypeLabel(game.type)}</div>
                            <div className="game-id">ID: {game.id}</div>
                          </div>
                          {(() => {
                            // Use calculated_revenue from server, or calculate client-side if needed
                            let displayRevenue = game.calculated_revenue;
                            
                            if (!displayRevenue && game.pricing && game.attendance) {
                              displayRevenue = 0;
                              if (game.pricing.bleachers && game.attendance.bleachers) {
                                displayRevenue += game.pricing.bleachers * game.attendance.bleachers;
                              }
                              if (game.pricing.lower_tier && game.attendance.lower_tier) {
                                displayRevenue += game.pricing.lower_tier * game.attendance.lower_tier;
                              }
                              if (game.pricing.courtside && game.attendance.courtside) {
                                displayRevenue += game.pricing.courtside * game.attendance.courtside;
                              }
                              if (game.pricing.luxury_boxes && game.attendance.luxury_boxes) {
                                displayRevenue += game.pricing.luxury_boxes * game.attendance.luxury_boxes;
                              }
                              // Only use calculated revenue if we actually have some components
                              if (displayRevenue === 0) displayRevenue = null;
                            }
                            
                            return displayRevenue ? (
                              <div className="game-revenue">
                                ${displayRevenue.toLocaleString()}
                              </div>
                            ) : null;
                          })()}
                        </div>
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

export default GameDataSidebar;
