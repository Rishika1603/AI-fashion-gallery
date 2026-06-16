import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { X, Shirt, Camera } from 'lucide-react';

interface TryOnModalProps {
    isOpen: boolean;
    onClose: () => void;
    productImage: string;
    onTryOn: (file: File) => Promise<Blob>; // Function to call API
}

const TryOnModal: React.FC<TryOnModalProps> = ({ isOpen, onClose, productImage, onTryOn }) => {
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [preview, setPreview] = useState<string | null>(null);
    const [resultImage, setResultImage] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const onDrop = useCallback((acceptedFiles: File[]) => {
        const file = acceptedFiles[0];
        if (file) {
            setSelectedFile(file);
            setPreview(URL.createObjectURL(file));
            setError(null);
            setResultImage(null);
        }
    }, []);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: {
            'image/*': ['.jpeg', '.jpg', '.png']
        },
        maxFiles: 1,
        multiple: false
    });

    const handleTryOn = async () => {
        if (!selectedFile) return;

        setIsLoading(true);
        setError(null);
        try {
            const blob = await onTryOn(selectedFile);
            const url = URL.createObjectURL(blob);
            setResultImage(url);
        } catch (err) {
            console.error(err);
            setError("Failed to generate try-on result. Please try again.");
        } finally {
            setIsLoading(false);
        }
    };

    const handleReset = () => {
        setSelectedFile(null);
        setPreview(null);
        setResultImage(null);
        setError(null);
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 premium-blur p-4">
            <div className="glass-card bg-black/40 rounded-3xl w-full max-w-4xl overflow-hidden shadow-2xl flex flex-col max-h-[90vh] border border-white/10">

                {/* Header */}
                <div className="p-6 border-b border-white/10 flex justify-between items-center premium-blur bg-white/5">
                    <h2 className="text-2xl font-black text-gradient flex items-center gap-3">
                        <Shirt className="w-6 h-6 text-violet-400" />
                        Virtual Try-On Studio
                    </h2>
                    <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-full transition-colors">
                        <X className="w-6 h-6 text-white/70 hover:text-white" />
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8 h-full">

                        {/* Left: Inputs */}
                        <div className="space-y-6">
                            {/* Product Preview */}
                            <div className="flex items-center gap-4 p-4 bg-white/5 premium-blur rounded-2xl border border-white/10">
                                <img src={productImage} alt="Garment" className="w-16 h-16 rounded-xl object-cover bg-black" />
                                <div>
                                    <p className="text-sm font-medium text-slate-400">Selected Garment</p>
                                    <p className="text-base font-bold text-white">Ready to wear</p>
                                </div>
                            </div>

                            {/* User Photo Upload */}
                            {!preview ? (
                                <div
                                    {...getRootProps()}
                                    className={`border-2 border-dashed rounded-3xl h-64 flex flex-col items-center justify-center cursor-pointer transition-all premium-blur
                    ${isDragActive ? 'border-violet-500 bg-violet-500/10' : 'border-white/20 hover:border-violet-400/50 hover:bg-white/5'}
                  `}
                                >
                                    <input {...getInputProps()} />
                                    <div className="p-5 bg-white/5 rounded-full mb-4 shadow-inner border border-white/10">
                                        <Camera className="w-8 h-8 text-violet-400" />
                                    </div>
                                    <p className="font-bold text-white text-lg">Upload your photo</p>
                                    <p className="text-sm text-slate-400 mt-2">Full body shot works best</p>
                                </div>
                            ) : (
                                <div className="relative rounded-3xl overflow-hidden border border-white/10 h-96 bg-black/40 flex items-center justify-center premium-blur shadow-inner">
                                    <img src={preview} alt="You" className="max-h-full max-w-full object-contain" />
                                    {!resultImage && !isLoading && (
                                        <button
                                            onClick={handleReset}
                                            className="absolute top-4 right-4 p-2 bg-black/50 hover:bg-black/80 text-white rounded-full transition-all border border-white/20"
                                        >
                                            <X size={18} />
                                        </button>
                                    )}
                                </div>
                            )}
                        </div>

                        {/* Right: Result / Action */}
                        <div className="flex flex-col items-center justify-center relative">
                            {/* Divider for mobile */}
                            <div className="md:hidden w-full h-px bg-white/10 my-4"></div>

                            {!resultImage ? (
                                <div className="h-full w-full flex flex-col items-center justify-center text-center p-8 bg-white/5 premium-blur rounded-3xl border border-white/10">
                                    {isLoading ? (
                                        <div className="flex flex-col items-center gap-4">
                                            <div className="w-16 h-16 border-4 border-white/10 border-t-violet-500 rounded-full animate-spin"></div>
                                            <p className="text-xl font-bold animate-pulse text-gradient">Generating your look...</p>
                                            <p className="text-sm text-slate-400">This might take a moment.</p>
                                        </div>
                                    ) : (
                                        <>
                                            <div className="w-32 h-32 bg-violet-500/20 rounded-full mb-6 blur-2xl absolute"></div>
                                            <h3 className="text-2xl font-black text-white relative z-10 mb-2">See the magic happen!</h3>
                                            <p className="text-slate-400 mb-8 max-w-xs relative z-10 leading-relaxed text-lg">
                                                Upload your photo on the left and click "Try On" to generate your new look.
                                            </p>
                                            <button
                                                onClick={handleTryOn}
                                                disabled={!selectedFile}
                                                className={`px-10 py-4 rounded-full font-bold shadow-xl transition-all relative z-10
                                    ${!selectedFile
                                                        ? 'bg-white/10 text-white/40 cursor-not-allowed border border-white/5'
                                                        : 'bg-gradient-to-r from-violet-600 to-cyan-600 text-white hover:scale-105 active:scale-95 shadow-violet-500/30'}
                                `}
                                            >
                                                Generate Try-On
                                            </button>
                                            {error && (
                                                <p className="mt-6 text-rose-400 font-medium px-4 py-2 bg-rose-500/10 rounded-lg">{error}</p>
                                            )}
                                        </>
                                    )}
                                </div>
                            ) : (
                                <div className="h-full w-full flex flex-col gap-5">
                                    <h3 className="text-2xl font-black text-white">Your New Look ✨</h3>
                                    <div className="flex-1 relative rounded-3xl overflow-hidden border border-white/20 bg-black/40 flex items-center justify-center group shadow-2xl premium-blur">
                                        <img src={resultImage} alt="Try On Result" className="max-h-full max-w-full object-contain" />
                                        <a
                                            href={resultImage}
                                            download="fashion-tryon.png"
                                            className="absolute bottom-6 right-6 bg-white/10 premium-blur border border-white/20 text-white px-6 py-3 rounded-full font-bold shadow-xl hover:bg-white/20 transition-all opacity-0 group-hover:opacity-100"
                                        >
                                            Download
                                        </a>
                                    </div>
                                    <button
                                        onClick={handleReset}
                                        className="w-full py-4 border border-white/10 rounded-full text-white font-bold hover:bg-white/5 transition-all bg-white/5 premium-blur shadow-lg"
                                    >
                                        Try Another Photo
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default TryOnModal;
