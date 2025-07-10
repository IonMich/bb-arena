import React, { useState, useEffect, useCallback } from 'react';
import { arenaService } from '../services/arenaService';
import ArenaDetailView from './ArenaDetailView';
import BBArenaCollector from './BBArenaCollector';
import './ArenaViewer.css';

const ArenaViewer = () => {
  const [arenas, setArenas] = useState([]);
  const [selectedArena, setSelectedArena] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentPage, setCurrentPage] = useState(0);
  const [totalCount, setTotalCount] = useState(0);
  const [viewMode, setViewMode] = useState('list'); // 'list' or 'court'
  
  const itemsPerPage = 20;

  const fetchArenas = useCallback(async () => {
    try {
      setLoading(true);
      const offset = currentPage * itemsPerPage;
      const response = await arenaService.getArenas(itemsPerPage, offset);
      setArenas(response.arenas);
      setTotalCount(response.total_count);
      setError(null);
    } catch (err) {
      setError('Failed to fetch arenas. Make sure the backend server is running.');
      console.error('Error fetching arenas:', err);
    } finally {
      setLoading(false);
    }
  }, [currentPage]);

  useEffect(() => {
    fetchArenas();
  }, [fetchArenas]);

  const handleArenaSelect = (arena) => {
    setSelectedArena(arena);
    setViewMode('court');
  };

  const handleBackToList = () => {
    setViewMode('list');
    setSelectedArena(null);
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString();
  };

  const formatNumber = (number) => {
    return number?.toLocaleString() || '0';
  };

  const totalPages = Math.ceil(totalCount / itemsPerPage);

  if (viewMode === 'court' && selectedArena) {
    return (
      <ArenaDetailView 
        selectedArena={selectedArena}
        onBackToList={handleBackToList}
      />
    );
  }

  return (
    <div className="arena-viewer">
      <div className="arena-list-header">
        <h2>Saved Arenas from Database</h2>
        <p>Total arenas: {formatNumber(totalCount)}</p>
      </div>

      {/* BuzzerBeater Arena Collector */}
      <BBArenaCollector onDataCollected={fetchArenas} />

      {loading && (
        <div className="loading">Loading arenas...</div>
      )}

      {error && (
        <div className="error">
          <p>{error}</p>
          <button onClick={fetchArenas} className="retry-button">
            Retry
          </button>
        </div>
      )}

      {!loading && !error && (
        <>
          <div className="arena-grid">
            {arenas.map((arena) => (
              <div 
                key={arena.id} 
                className="arena-card"
                onClick={() => handleArenaSelect(arena)}
              >
                <div className="arena-card-header">
                  <h3>{arena.arena_name || `Arena ${arena.id}`}</h3>
                  <div className="team-info">
                    <span className="team-id">Team: {arena.team_id}</span>
                    <span className="latest-indicator">Latest Snapshot</span>
                  </div>
                </div>
                
                <div className="arena-card-body">
                  <div className="capacity-grid">
                    <div className="capacity-item">
                      <span className="capacity-label">Courtside</span>
                      <span className="capacity-value">{formatNumber(arena.courtside_capacity)}</span>
                    </div>
                    <div className="capacity-item">
                      <span className="capacity-label">Lower Tier</span>
                      <span className="capacity-value">{formatNumber(arena.lower_tier_capacity)}</span>
                    </div>
                    <div className="capacity-item">
                      <span className="capacity-label">Luxury Boxes</span>
                      <span className="capacity-value">{formatNumber(arena.luxury_boxes_capacity)}</span>
                    </div>
                    <div className="capacity-item">
                      <span className="capacity-label">Bleachers</span>
                      <span className="capacity-value">{formatNumber(arena.bleachers_capacity)}</span>
                    </div>
                  </div>
                  
                  <div className="arena-card-footer">
                    <div className="total-capacity">
                      Total: {formatNumber(arena.total_capacity)}
                    </div>
                    <div className="created-date">
                      {formatDate(arena.created_at)}
                    </div>
                    {arena.expansion_in_progress && (
                      <div className="expansion-badge">
                        Expansion in Progress
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {totalPages > 1 && (
            <div className="pagination">
              <button 
                onClick={() => setCurrentPage(prev => Math.max(0, prev - 1))}
                disabled={currentPage === 0}
                className="pagination-button"
              >
                Previous
              </button>
              
              <span className="pagination-info">
                Page {currentPage + 1} of {totalPages}
              </span>
              
              <button 
                onClick={() => setCurrentPage(prev => Math.min(totalPages - 1, prev + 1))}
                disabled={currentPage === totalPages - 1}
                className="pagination-button"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default ArenaViewer;
