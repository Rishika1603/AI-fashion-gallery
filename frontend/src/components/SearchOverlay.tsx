import React, { useState, useRef } from 'react';
import { X, Upload, Camera, Sparkles } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import Lottie from 'lottie-react';
import loadingAnimation from '../assets/loading-animation.json';

interface SearchOverlayProps {
    onClose: () => void;
    onSearch: (file: File) => void;
    isSearching: boolean;
}

const SearchOverlay: React.FC<SearchOverlayProps> = ({ onClose, onSearch, isSearching }) => {
    const [dragActive, setDragActive] = useState(false);
    const [previewUrl, setPreviewUrl] = useState<string | null>(null);
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [error, setError] = useState<string | null>(null);
    const inputRef = useRef<HTMLInputElement>(null);

    // Paste support
    React.useEffect(() => {
        const handlePaste = (e: ClipboardEvent) => {
            if (e.clipboardData?.files?.[0]) {
                handleFile(e.clipboardData.files[0]);
            }
        };
        document.addEventListener('paste', handlePaste);
        return () => document.removeEventListener('paste', handlePaste);
    }, []);

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' || e.key === ' ') {
            onButtonClick();
        }
    };

    const handleDrag = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === "dragenter" || e.type === "dragover") {
            setDragActive(true);
        } else if (e.type === "dragleave") {
            setDragActive(false);
        }
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);
        if (e.dataTransfer.files?.[0]) {
            handleFile(e.dataTransfer.files[0]);
        }
    };

    const handleFile = (file: File) => {
        if (!file.type.startsWith('image/')) {
            setError('Please upload an image file (JPG, PNG)');
            return;
        }
        if (file.size > 10 * 1024 * 1024) {
            setError('File size too large (max 10MB)');
            return;
        }
        setError(null);
        setSelectedFile(file);
        const url = URL.createObjectURL(file);
        setPreviewUrl(url);
    };

    const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files?.[0]) {
            handleFile(e.target.files[0]);
        }
    };

    const onButtonClick = () => {
        inputRef.current?.click();
    };

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[100] bg-black/80 premium-blur flex items-center justify-center p-4"
        >
            <button
                onClick={onClose}
                className="absolute top-8 right-8 text-white/50 hover:text-white transition-colors p-2 hover:bg-white/10 rounded-full"
            >
                <X size={32} />
            </button>

            <div className="w-full max-w-2xl relative">
                {/* Decorative gradients */}
                <div className="absolute -top-20 -left-20 w-64 h-64 bg-violet-500/30 rounded-full blur-[100px] pointer-events-none" />
                <div className="absolute -bottom-20 -right-20 w-64 h-64 bg-cyan-500/30 rounded-full blur-[100px] pointer-events-none" />

                <AnimatePresence mode="wait">
                    {!previewUrl ? (
                        <motion.div
                            key="upload"
                            initial={{ scale: 0.9, opacity: 0, y: 20 }}
                            animate={{ scale: 1, opacity: 1, y: 0 }}
                            exit={{ scale: 0.95, opacity: 0, y: -20 }}
                            className="text-center relative z-10"
                        >
                            <div className="mb-10">
                                <motion.div
                                    className="w-28 h-28 mx-auto mb-8 relative group"
                                    whileHover={{ rotate: 15, scale: 1.1 }}
                                    transition={{ type: "spring", stiffness: 300, damping: 15 }}
                                >
                                    <div className="absolute inset-0 bg-gradient-to-tr from-violet-500 to-cyan-500 rounded-[2rem] shadow-[0_0_50px_rgba(139,92,246,0.4)] group-hover:shadow-[0_0_80px_rgba(6,182,212,0.6)] transition-all duration-500" />
                                    <div className="absolute inset-0.5 bg-black rounded-[1.9rem] flex items-center justify-center">
                                        <Camera size={48} className="text-white relative z-10" />
                                    </div>
                                </motion.div>
                                <h2 className="text-5xl font-black text-white mb-4 tracking-tight">Start Your Search</h2>
                                <p className="text-white/60 text-lg max-w-md mx-auto leading-relaxed">
                                    Upload a photo or paste from clipboard to find matching styles instantly
                                </p>
                            </div>

                            <motion.button
                                type="button"
                                onKeyDown={handleKeyDown}
                                animate={dragActive ? {
                                    scale: 1.02,
                                    backgroundColor: "rgba(139, 92, 246, 0.1)",
                                    borderColor: "rgba(139, 92, 246, 0.5)"
                                } : {
                                    scale: 1,
                                    backgroundColor: "rgba(255, 255, 255, 0.03)",
                                    borderColor: "rgba(255, 255, 255, 0.1)"
                                }}
                                className="w-full relative group cursor-pointer border-2 border-dashed rounded-[2.5rem] p-12 transition-all duration-300 hover:border-white/20 hover:bg-white/5 backdrop-blur-sm"
                                onDragEnter={handleDrag}
                                onDragLeave={handleDrag}
                                onDragOver={handleDrag}
                                onDrop={handleDrop}
                                onClick={onButtonClick}
                            >
                                <input
                                    ref={inputRef}
                                    type="file"
                                    className="hidden"
                                    accept="image/*"
                                    onChange={handleFileInput}
                                />

                                <div className="flex flex-col items-center gap-6">
                                    <div className="p-6 bg-gradient-to-br from-white/10 to-white/5 rounded-full text-white shadow-lg group-hover:scale-110 transition-transform duration-300 border border-white/5">
                                        <Upload size={32} />
                                    </div>
                                    <div>
                                        <div className="text-white text-xl font-bold mb-2">Drag & Drop or Click</div>
                                        <p className="text-white/40 text-sm font-medium">Supports PNG, JPG of any size</p>
                                    </div>
                                </div>
                            </motion.button>

                            {error && (
                                <motion.div
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    className="text-red-400 mt-4 font-medium flex items-center justify-center gap-2"
                                >
                                    <X size={16} /> {error}
                                </motion.div>
                            )}

                            <div className="mt-8 flex justify-center gap-3">
                                <span className="text-white/30 text-sm font-medium uppercase tracking-wider">Try with:</span>
                                {['Sneakers', 'Vintage Jacket', 'Summer Dress'].map(tag => (
                                    <span key={tag} className="text-white/50 text-sm hover:text-white transition-colors cursor-default">
                                        {tag}
                                    </span>
                                ))}
                            </div>
                        </motion.div>
                    ) : (
                        <motion.div
                            key="preview"
                            initial={{ scale: 0.9, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            className="flex flex-col items-center relative z-10"
                        >
                            <div className="relative aspect-[3/4] w-full max-w-sm rounded-[2rem] overflow-hidden shadow-2xl mb-8 group ring-4 ring-white/5">
                                <img src={previewUrl} className="w-full h-full object-cover" alt="Preview" />
                                <button
                                    onClick={() => { setPreviewUrl(null); setSelectedFile(null); }}
                                    className="absolute top-4 right-4 p-3 bg-black/50 backdrop-blur-md rounded-full text-white opacity-0 group-hover:opacity-100 transition-all hover:bg-black/70 hover:scale-110"
                                >
                                    <X size={20} />
                                </button>

                                {isSearching && (
                                    <div className="absolute inset-0 bg-black/60 backdrop-blur-md flex flex-col items-center justify-center p-8 text-center z-20">
                                        <div className="w-48 h-48 mb-6">
                                            <Lottie animationData={loadingAnimation} loop={true} />
                                        </div>
                                        <div className="text-white text-2xl font-black mb-2 animate-pulse tracking-tight">Analyzing Styles...</div>
                                        <div className="w-full max-w-[200px] h-1 bg-white/10 rounded-full mt-4 overflow-hidden">
                                            <motion.div
                                                initial={{ width: "0%" }}
                                                animate={{ width: "100%" }}
                                                transition={{ duration: 2, ease: "easeInOut", repeat: Infinity }}
                                                className="h-full bg-brand-primary"
                                            />
                                        </div>
                                    </div>
                                )}
                            </div>

                            {!isSearching && (
                                <div className="flex gap-4 w-full max-w-sm">
                                    <button
                                        onClick={() => { setPreviewUrl(null); setSelectedFile(null); }}
                                        className="flex-1 py-4 bg-white/5 border border-white/10 text-white font-bold rounded-2xl hover:bg-white/10 transition-all active:scale-95"
                                    >
                                        Retake
                                    </button>
                                    <button
                                        onClick={() => selectedFile && onSearch(selectedFile)}
                                        className="flex-[2] py-4 bg-gradient-to-r from-violet-600 to-cyan-600 text-white font-bold rounded-2xl shadow-xl shadow-violet-500/20 flex items-center justify-center gap-3 hover:brightness-110 active:scale-95 transition-all group"
                                    >
                                        <Sparkles size={20} className="group-hover:rotate-12 transition-transform" />
                                        Find Styles
                                    </button>
                                </div>
                            )}
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </motion.div>
    );
};

export default SearchOverlay;
