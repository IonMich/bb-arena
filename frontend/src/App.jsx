import React, { useState, useEffect, useCallback } from 'react';
import ArenaHomePage from './components/ArenaHomePage';
// import ArenaDesigner from './components/ArenaDesigner'; // Temporarily disabled
import ArenaViewer from './components/ArenaViewer';
import LoadingSpinner from './components/LoadingSpinner';
import { arenaService } from './services/arenaService';
import './App.css';

function App() {
  const [currentView, setCurrentView] = useState('home'); // 'home', 'viewer' (designer temporarily disabled)
  const [appData, setAppData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [homePageLoading, setHomePageLoading] = useState(false);

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

  const handleHomePageLoadingChange = useCallback((loading) => {
    setHomePageLoading(loading);
  }, []);

  // Show loading spinner if app is initializing OR if we're on home page and it hasn't loaded yet
  const shouldShowLoading = isLoading || (currentView === 'home' && homePageLoading);

  // Auto-hide loading after app initialization to prevent getting stuck
  useEffect(() => {
    if (!isLoading && currentView === 'home' && homePageLoading) {
      const timeout = setTimeout(() => {
        setHomePageLoading(false);
      }, 10000); // 10 second safety timeout
      
      return () => clearTimeout(timeout);
    }
  }, [isLoading, currentView, homePageLoading]);

  return (
    <div className="App">
      {!shouldShowLoading && (
        <nav className="app-nav">
          <button 
            className={`nav-button ${currentView === 'home' ? 'active' : ''}`}
            onClick={() => setCurrentView('home')}
          >
            My Arena
          </button>
          <button 
            className={`nav-button ${currentView === 'viewer' ? 'active' : ''}`}
            onClick={() => setCurrentView('viewer')}
          >
            All Arenas
          </button>
          {/* Arena Designer temporarily disabled
          <button 
            className={`nav-button ${currentView === 'designer' ? 'active' : ''}`}
            onClick={() => setCurrentView('designer')}
          >
            Arena Designer
          </button>
          */}
        </nav>
      )}

      {shouldShowLoading ? (
        <LoadingSpinner size="large" message={isLoading ? "Initializing application..." : "Loading your arena..."} />
      ) : (
        <>
          {error && (
            <div className="app-error">
              <p>⚠️ {error}</p>
              <p>Some features may not work properly.</p>
            </div>
          )}

          {currentView === 'home' ? (
            <ArenaHomePage onLoadingChange={handleHomePageLoadingChange} />
          ) : (
            <ArenaViewer appData={appData} />
          )}
          {/* Arena Designer view temporarily disabled
          ) : currentView === 'designer' ? (
            <ArenaDesigner />
          */}
        </>
      )}
    </div>
  );
}

export default App;
