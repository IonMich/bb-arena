import React, { useState, useEffect } from 'react';
import ArenaDesigner from './components/ArenaDesigner';
import ArenaViewer from './components/ArenaViewer';
import LoadingSpinner from './components/LoadingSpinner';
import { arenaService } from './services/arenaService';
import './App.css';

function App() {
  const [currentView, setCurrentView] = useState('designer'); // 'designer' or 'viewer'
  const [appData, setAppData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Load essential app data on startup
  useEffect(() => {
    const initializeApp = async () => {
      try {
        setIsLoading(true);
        setError(null);
        
        const data = await arenaService.initializeApp();
        setAppData(data);
        
        if (!data.initialized) {
          setError(data.error || 'Failed to initialize application');
        }
      } catch (err) {
        console.error('Failed to initialize app:', err);
        setError(err.message || 'Failed to initialize application');
        // Set fallback data so app can still work
        setAppData({
          seasons: { all: [], current: 69, min: 54, max: 69 },
          userTeam: null,
          league: null,
          initialized: false
        });
      } finally {
        setIsLoading(false);
      }
    };

    initializeApp();
  }, []);

  return (
    <div className="App">
      {isLoading ? (
        <LoadingSpinner size="large" message="Initializing application..." />
      ) : (
        <>
          <nav className="app-nav">
            <button 
              className={`nav-button ${currentView === 'designer' ? 'active' : ''}`}
              onClick={() => setCurrentView('designer')}
            >
              Arena Designer
            </button>
            <button 
              className={`nav-button ${currentView === 'viewer' ? 'active' : ''}`}
              onClick={() => setCurrentView('viewer')}
            >
              Saved Arenas
            </button>
          </nav>

          {error && (
            <div className="app-error">
              <p>⚠️ {error}</p>
              <p>Some features may not work properly.</p>
            </div>
          )}

          {currentView === 'designer' ? (
            <ArenaDesigner />
          ) : (
            <ArenaViewer appData={appData} />
          )}
        </>
      )}
    </div>
  );
}

export default App;
