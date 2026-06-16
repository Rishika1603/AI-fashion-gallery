import { useState } from 'react';
import { AnimatePresence } from 'framer-motion';
import Gallery from './components/Gallery';
import SearchOverlay from './components/SearchOverlay';
import Results from './components/Results';
import type { SearchResult, ScreenState } from './types';
import { searchByPhoto as apiSearchByPhoto } from './api';
import ChatBot from './components/ChatBot';

function App() {
  const [screen, setScreen] = useState<ScreenState>('GALLERY');
  const [showOverlay, setShowOverlay] = useState(false);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  const handleStartSearch = () => {
    setShowOverlay(true);
  };

  const handleSearch = async (file: File) => {
    setIsSearching(true);
    try {
      // Simulate network delay for AI processing effect
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
      <ChatBot />
    </div>
  );
}

export default App;
