import React, { useState } from 'react';
import ArenaDesigner from './components/ArenaDesigner';
import ArenaViewer from './components/ArenaViewer';
import './App.css';

function App() {
  const [currentView, setCurrentView] = useState('designer'); // 'designer' or 'viewer'

  return (
    <div className="App">
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

      {currentView === 'designer' ? <ArenaDesigner /> : <ArenaViewer />}
    </div>
  );
}

export default App;
