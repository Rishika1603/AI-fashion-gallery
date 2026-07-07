import { useState } from 'react';
import { AnimatePresence } from 'framer-motion';
import Gallery from './components/Gallery';
import SearchOverlay from './components/SearchOverlay';
import Results from './components/Results';
import type { SearchResult, ScreenState } from './types';
import { searchByPhoto as apiSearchByPhoto } from './api';
import ChatBot from './components/ChatBot';

import AdminPanel from './components/AdminPanel';

function App() {
  const [screen, setScreen] = useState<ScreenState>('GALLERY');
  const [showOverlay, setShowOverlay] = useState(false);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [showAdminPanel, setShowAdminPanel] = useState(false);
  const [adminKey, setAdminKey] = useState<string | null>(null);

  const handleStartSearch = () => {
    setShowOverlay(true);
  };

  const handleSearch = async (file: File) => {
    setIsSearching(true);
    try {
      await new Promise(resolve => setTimeout(resolve, 2500));
      const searchResults = await apiSearchByPhoto(file);
      setResults(searchResults);
      setScreen('RESULTS');
      setShowOverlay(false);
    } catch (error) {
      console.error('Search failed', error);
      alert('Search failed. Please try again.');
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className="min-h-screen bg-transparent text-white overflow-x-hidden selection:bg-violet-500/30">
      <AnimatePresence mode="wait">
        {screen === 'GALLERY' && (
          <Gallery key="gallery" onStartSearch={handleStartSearch} />
        )}

        {screen === 'RESULTS' && (
          <Results
            key="results"
            results={results}
            onBack={() => setScreen('GALLERY')}
            onRetry={() => setShowOverlay(true)}
          />
        )}

        {showOverlay && (
          <SearchOverlay
            key="overlay"
            onClose={() => setShowOverlay(false)}
            onSearch={handleSearch}
            isSearching={isSearching}
          />
        )}
      </AnimatePresence>

      {/* Bottom action buttons */}
      <div className="fixed bottom-6 right-6 z-40 flex flex-col items-end gap-3">
        {/* Admin Panel button */}
        {screen === 'GALLERY' && (
          <button
            onClick={() => setShowAdminPanel(true)}
            className="px-4 py-2.5 rounded-2xl bg-white/5 border border-white/10 hover:bg-white/10 text-white/80 text-sm font-bold shadow-lg backdrop-blur-xl transition-all flex items-center gap-2"
          >
            <span>🛡️</span> Admin
          </button>
        )}
      </div>

      {showAdminPanel && (
        <AdminPanel
          isOpen={showAdminPanel}
          onClose={() => setShowAdminPanel(false)}
          adminKey={adminKey}
          onSetAdminKey={setAdminKey}
        />
      )}

      <ChatBot />
    </div>
  );
}

export default App;
