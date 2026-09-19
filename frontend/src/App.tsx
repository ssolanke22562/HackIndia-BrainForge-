import React, { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar.tsx';
import { CapturePage } from './pages/CapturePage.tsx';
import { GraphPage } from './pages/GraphPage.tsx';
import { AskPage } from './pages/AskPage.tsx';
import { HistoryPage } from './pages/HistoryPage.tsx';
import { PersonaPage } from './pages/PersonaPage.tsx';
import { apiUrl } from './config/api.ts';
import './styles/index.css';
import './styles/components.css';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'capture' | 'graph' | 'ask' | 'history' | 'persona'>('capture');
  const [serverStatus, setServerStatus] = useState<'healthy' | 'offline' | 'checking'>('checking');
  const [stats, setStats] = useState({ notes_count: 0, links_count: 0 });

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const res = await fetch(apiUrl('/health'));
        if (res.ok) {
          const data = await res.json();
          setServerStatus(data.status === 'healthy' ? 'healthy' : 'offline');
          if (data.stats) {
            setStats(data.stats);
          }
        } else {
          setServerStatus('offline');
        }
      } catch (err) {
        setServerStatus('offline');
      }
    };

    fetchHealth();
    const interval = setInterval(fetchHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="app-layout">
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        stats={stats}
        serverStatus={serverStatus}
      />
      <main className="main-content">
        {activeTab === 'capture' && <CapturePage />}
        {activeTab === 'graph' && <GraphPage />}
        {activeTab === 'ask' && <AskPage />}
        {activeTab === 'history' && <HistoryPage />}
        {activeTab === 'persona' && <PersonaPage />}
      </main>
    </div>
  );
};

export default App;
