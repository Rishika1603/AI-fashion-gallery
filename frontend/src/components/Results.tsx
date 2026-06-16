import React from 'react';
import { ChevronLeft, RefreshCw, SlidersHorizontal } from 'lucide-react';
import type { SearchResult } from '../types';
import ProductCard from './ProductCard';

interface ResultsProps {
    results: SearchResult[];
    onBack: () => void;
    onRetry: () => void;
}

const Results: React.FC<ResultsProps> = ({ results, onBack, onRetry }) => {
    return (
        <div className="max-w-7xl mx-auto px-4 pt-24 pb-12">
            {/* Search Header */}
            <div className="fixed top-0 left-0 right-0 z-50 premium-blur bg-black/30 border-b border-white/10 flex items-center justify-between px-6 py-4 text-white">
                <button
                    onClick={onBack}
                    className="p-2 rounded-full hover:bg-white/10 transition-colors"
                >
                    <ChevronLeft size={24} />
                </button>
                <h1 className="text-lg font-bold">Search Results</h1>
                <button className="p-2 rounded-full hover:bg-white/10 transition-colors">
                    <SlidersHorizontal size={20} />
                </button>
            </div>

            <div className="mb-12 mt-4">
                <div className="flex items-center justify-between mb-10 pt-8">
                    <div>
                        <h2 className="text-4xl font-black text-white mb-2">AI Matches Found</h2>
                        <p className="text-slate-400 text-lg">We found {results.length} styles inspired by your photo</p>
                    </div>
                    <button
                        onClick={onRetry}
                        className="flex items-center gap-2 text-violet-400 font-bold text-sm hover:text-violet-300 transition-colors"
                    >
                        <RefreshCw size={16} />
                        Try another photo
                    </button>
                </div>

                {results.length === 0 ? (
                    <div className="text-center py-20 bg-white/5 premium-blur rounded-[2.5rem] border border-dashed border-white/20">
                        <h3 className="text-2xl font-bold mb-2 text-white">No matches found</h3>
                        <p className="text-slate-400 mb-8">Try a clearer photo with better lighting</p>
                        <button
                            onClick={onRetry}
                            className="btn-primary shadow-violet-500/30"
                        >
                            Retry Search
                        </button>
                    </div>
                ) : (
                    <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 md:gap-8">
                        {results.map((result, idx) => (
                            <ProductCard
                                key={result.product.id || idx}
                                product={result.product}
                                isResult={true}
                                matchScore={result.match_score}
                            />
                        ))}
                    </div>
                )}
            </div>

            {results.length > 0 && (
                <div className="text-center py-12 border-t border-white/10 mt-12">
                    <p className="text-slate-400 mb-6">Didn't find exactly what you were looking for?</p>
                    <button
                        onClick={onBack}
                        className="px-8 py-4 bg-white/5 text-white font-bold rounded-full hover:bg-white/10 border border-white/20 transition-all premium-blur shadow-xl"
                    >
                        Back to Gallery
                    </button>
                </div>
            )}
        </div>
    );
};

export default Results;
