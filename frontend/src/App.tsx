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
  const getInitialTab = (): 'persona' | 'capture' | 'graph' | 'ask' | 'history' => {
    const hash = window.location.hash.replace('#', '') as any;
    if (hash && ['persona', 'capture', 'graph', 'ask', 'history'].includes(hash)) {
      return hash;
    }
    const saved = localStorage.getItem('secondself_active_tab') as any;
    if (saved && ['persona', 'capture', 'graph', 'ask', 'history'].includes(saved)) {
      return saved;
    }
    return 'persona';
  };

  const [activeTab, setActiveTab] = useState<'persona' | 'capture' | 'graph' | 'ask' | 'history'>(getInitialTab);
  const [serverStatus, setServerStatus] = useState<'healthy' | 'offline' | 'checking'>('checking');
  const [stats, setStats] = useState({ notes_count: 0, links_count: 0 });

  const handleTabChange = (tab: 'persona' | 'capture' | 'graph' | 'ask' | 'history') => {
    setActiveTab(tab);
    localStorage.setItem('secondself_active_tab', tab);
    window.location.hash = tab;
  };

  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.replace('#', '') as any;
      if (hash && ['persona', 'capture', 'graph', 'ask', 'history'].includes(hash)) {
        setActiveTab(hash);
        localStorage.setItem('secondself_active_tab', hash);
      }
    };

    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

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
        setActiveTab={handleTabChange}
        stats={stats}
        serverStatus={serverStatus}
      />
      <main className="main-content">
        {activeTab === 'persona' && <PersonaPage />}
        {activeTab === 'capture' && <CapturePage />}
        {activeTab === 'graph' && <GraphPage />}
        {activeTab === 'ask' && <AskPage />}
        {activeTab === 'history' && <HistoryPage />}
      </main>
    </div>
  );
};

export default App;
