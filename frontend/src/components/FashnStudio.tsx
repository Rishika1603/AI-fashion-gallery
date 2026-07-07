import React, { useState, useEffect, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { X, Shirt, Sparkles, Crop, Video, Eraser, User, Box, Image as ImageIcon, Loader2, Camera } from 'lucide-react';
import {
    getFashnStatus,
    fashnTryOn,
    fashnProductToModel,
    fashnFaceToModel,
    fashnModelCreate,
    fashnEdit,
    fashnReframe,
    fashnImageToVideo,
    fashnBackgroundRemove,
} from '../api';

type FeatureId =
    | 'tryon-max'
    | 'product-to-model'
    | 'face-to-model'
    | 'model-create'
    | 'edit'
    | 'reframe'
    | 'image-to-video'
    | 'background-remove';

interface FashnStudioProps {
    onClose: () => void;
}

const FEATURE_META: Record<FeatureId, { name: string; icon: React.ReactNode; color: string; description: string }> = {
    'tryon-max': {
        name: 'Virtual Try-On',
        icon: <Shirt className="w-5 h-5" />,
        color: 'violet',
        description: 'Place a garment on a model photo',
    },
    'product-to-model': {
        name: 'Product to Model',
        icon: <Box className="w-5 h-5" />,
        color: 'blue',
        description: 'Generate a model wearing your product',
    },
    'face-to-model': {
        name: 'Face to Model',
        icon: <User className="w-5 h-5" />,
        color: 'emerald',
        description: 'Turn a selfie into a try-on avatar',
    },
    'model-create': {
        name: 'Model Create',
        icon: <Sparkles className="w-5 h-5" />,
        color: 'amber',
        description: 'Create AI model from photos',
    },
    edit: {
        name: 'Edit',
        icon: <ImageIcon className="w-5 h-5" />,
        color: 'pink',
        description: 'Restyle, adjust, or fix details',
    },
    reframe: {
        name: 'Reframe',
        icon: <Crop className="w-5 h-5" />,
        color: 'cyan',
        description: 'Change aspect ratio with AI',
    },
    'image-to-video': {
        name: 'Image to Video',
        icon: <Video className="w-5 h-5" />,
        color: 'rose',
        description: 'Animate a still image into video',
    },
    'background-remove': {
        name: 'Background Remove',
        icon: <Eraser className="w-5 h-5" />,
        color: 'orange',
        description: 'Remove background to transparent PNG',
    },
};

const ASPECT_RATIOS = ['1:1', '3:4', '4:3', '4:5', '9:16', '16:9', '2:3', '3:2', '21:9'];

const FashnStudio: React.FC<FashnStudioProps> = ({ onClose }) => {
    const [activeFeature, setActiveFeature] = useState<FeatureId>('tryon-max');
    const [isAvailable, setIsAvailable] = useState<boolean | null>(null);

    // Shared state
    const [resultUrl, setResultUrl] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Feature-specific inputs
    const [inputFile1, setInputFile1] = useState<File | null>(null);
    const [inputFile2, setInputFile2] = useState<File | null>(null);
    const [preview1, setPreview1] = useState<string | null>(null);
    const [preview2, setPreview2] = useState<string | null>(null);
    const [promptText, setPromptText] = useState('');
    const [aspectRatio, setAspectRatio] = useState('1:1');
    const [modelName, setModelName] = useState('');
    const [duration, setDuration] = useState<number>(5);
    const [resolution, setResolution] = useState('1k');
    const [generationMode, setGenerationMode] = useState<string>('');
    const [numImages, setNumImages] = useState(1);
    const [videoUrl, setVideoUrl] = useState<string | null>(null);

    useEffect(() => {
        (async () => {
            try {
                const status = await getFashnStatus();
                setIsAvailable(status.available);
            } catch {
                setIsAvailable(false);
            }
        })();
    }, []);

    const resetInputs = useCallback(() => {
        setInputFile1(null);
        setInputFile2(null);
        setPreview1(null);
        setPreview2(null);
        setResultUrl(null);
        setVideoUrl(null);
        setError(null);
        setPromptText('');
        setAspectRatio('1:1');
        setModelName('');
        setDuration(5);
        setResolution('1k');
        setGenerationMode('');
        setNumImages(1);
    }, []);

    useEffect(() => {
        resetInputs();
    }, [activeFeature, resetInputs]);

    // Dropzone hooks
    const dz1 = useDropzone({
        onDrop: (files) => {
            if (files[0]) { setInputFile1(files[0]); setPreview1(URL.createObjectURL(files[0])); setError(null); setResultUrl(null); setVideoUrl(null); }
        },
        accept: { 'image/*': ['.jpeg', '.jpg', '.png', '.webp'] },
        maxFiles: 1,
        multiple: false,
    });

    const dz2 = useDropzone({
        onDrop: (files) => {
            if (files[0]) { setInputFile2(files[0]); setPreview2(URL.createObjectURL(files[0])); setError(null); }
        },
        accept: { 'image/*': ['.jpeg', '.jpg', '.png', '.webp'] },
        maxFiles: 1,
        multiple: false,
    });

    const handleRun = async () => {
        setIsLoading(true);
        setError(null);
        setResultUrl(null);
        setVideoUrl(null);
        try {
            let blob: Blob;
            let data: any;

            switch (activeFeature) {
                case 'tryon-max': {
                    if (!inputFile1 || !inputFile2) throw new Error('Both garment and model images are required');
                    blob = await fashnTryOn(inputFile1, inputFile2, { prompt: promptText || undefined, resolution, generation_mode: generationMode || undefined, num_images: numImages });
                    setResultUrl(URL.createObjectURL(blob));
                    break;
                }
                case 'product-to-model': {
                    if (!inputFile1) throw new Error('Product image is required');
                    blob = await fashnProductToModel(inputFile1, { prompt: promptText || undefined, faceReferenceFile: inputFile2 || undefined, aspect_ratio: aspectRatio !== '1:1' ? aspectRatio : undefined, resolution });
                    setResultUrl(URL.createObjectURL(blob));
                    break;
                }
                case 'face-to-model': {
                    if (!inputFile1) throw new Error('Face image is required');
                    blob = await fashnFaceToModel(inputFile1, { prompt: promptText || undefined, aspect_ratio: aspectRatio, resolution });
                    setResultUrl(URL.createObjectURL(blob));
                    break;
                }
                case 'model-create': {
                    if (!inputFile1) throw new Error('Model image is required');
                    data = await fashnModelCreate(inputFile1, modelName || undefined);
                    setResultUrl(null);
                    setVideoUrl(null);
                    setIsLoading(false);
                    alert(`Model creation started!\nPrediction ID: ${data.prediction_id}\nStatus: ${data.status}`);
                    return;
                }
                case 'edit': {
                    if (!inputFile1) throw new Error('Image is required');
                    if (!promptText) throw new Error('Edit prompt is required');
                    blob = await fashnEdit(inputFile1, promptText, { maskFile: inputFile2 || undefined, resolution, generation_mode: generationMode || undefined });
                    setResultUrl(URL.createObjectURL(blob));
                    break;
                }
                case 'reframe': {
                    if (!inputFile1) throw new Error('Image is required');
                    blob = await fashnReframe(inputFile1, aspectRatio, { resolution });
                    setResultUrl(URL.createObjectURL(blob));
                    break;
                }
                case 'image-to-video': {
                    if (!inputFile1) throw new Error('Image is required');
                    data = await fashnImageToVideo(inputFile1, { prompt: promptText || undefined, duration, resolution: resolution.startsWith('1k') ? '720p' : resolution });
                    setVideoUrl(data.video_url);
                    setResultUrl(null);
                    break;
                }
                case 'background-remove': {
                    if (!inputFile1) throw new Error('Image is required');
                    blob = await fashnBackgroundRemove(inputFile1);
                    setResultUrl(URL.createObjectURL(blob));
                    break;
                }
            }
        } catch (err: any) {
            const msg = err?.response?.data?.detail || err?.message || 'An error occurred';
            setError(msg);
        } finally {
            setIsLoading(false);
        }
    };

    // Render top nav
    const renderNav = () => (
        <div className="flex flex-wrap gap-2 p-4 border-b border-white/10 bg-white/[0.02]">
            {(Object.entries(FEATURE_META) as [FeatureId, typeof FEATURE_META[FeatureId]][]).map(([key, meta]) => {
                const isActive = activeFeature === key;
                const colorMap: Record<string, string> = {
                    violet: isActive ? 'bg-violet-500/20 text-violet-300 border-violet-500/40' : 'text-white/50 hover:text-white/80 hover:bg-white/5',
                    blue: isActive ? 'bg-blue-500/20 text-blue-300 border-blue-500/40' : 'text-white/50 hover:text-white/80 hover:bg-white/5',
                    emerald: isActive ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40' : 'text-white/50 hover:text-white/80 hover:bg-white/5',
                    amber: isActive ? 'bg-amber-500/20 text-amber-300 border-amber-500/40' : 'text-white/50 hover:text-white/80 hover:bg-white/5',
                    pink: isActive ? 'bg-pink-500/20 text-pink-300 border-pink-500/40' : 'text-white/50 hover:text-white/80 hover:bg-white/5',
                    cyan: isActive ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40' : 'text-white/50 hover:text-white/80 hover:bg-white/5',
                    rose: isActive ? 'bg-rose-500/20 text-rose-300 border-rose-500/40' : 'text-white/50 hover:text-white/80 hover:bg-white/5',
                    orange: isActive ? 'bg-orange-500/20 text-orange-300 border-orange-500/40' : 'text-white/50 hover:text-white/80 hover:bg-white/5',
                };
                return (
                    <button
                        key={key}
                        onClick={() => setActiveFeature(key)}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-sm border transition-all ${colorMap[meta.color]} ${isActive ? 'border' : 'border-transparent'}`}
                        title={meta.description}
                    >
                        {meta.icon}
                        <span className="hidden sm:inline">{meta.name}</span>
                    </button>
                );
            })}
        </div>
    );

    // Render dropzone for a single image
    const renderDropZone = (dz: typeof dz1, label: string, required: boolean = true) => (
        <div
            {...dz.getRootProps()}
            className={`border-2 border-dashed rounded-2xl p-4 text-center cursor-pointer transition-all ${dz.isDragActive ? 'border-violet-400 bg-violet-500/10' : 'border-white/20 hover:border-violet-400/60 hover:bg-white/5'}`}
        >
            <input {...dz.getInputProps()} />
            {dz.acceptedFiles[0] ? (
                <div className="flex items-center justify-center gap-3">
                    <Camera className="w-5 h-5 text-violet-400 shrink-0" />
                    <span className="text-sm text-white/70 truncate">{dz.acceptedFiles[0].name}</span>
                </div>
            ) : (
                <div className="flex flex-col items-center gap-1 py-2">
                    <Camera className="w-6 h-6 text-white/30" />
                    <p className="text-sm text-white/40">{label} {required && <span className="text-red-400">*</span>}</p>
                </div>
            )}
        </div>
    );

    // Render feature-specific inputs
    const renderInputs = () => {
        switch (activeFeature) {
            case 'tryon-max':
                return (
                    <div className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="text-xs text-white/50 mb-1.5 block">Garment Image *</label>
                                {renderDropZone(dz1, 'Garment photo', true)}
                            </div>
                            <div>
                                <label className="text-xs text-white/50 mb-1.5 block">Model Image *</label>
                                {renderDropZone(dz2, 'Model/person photo', true)}
                            </div>
                        </div>
                        <input type="text" placeholder="Optional prompt (e.g. tuck in shirt)" value={promptText} onChange={e => setPromptText(e.target.value)} className="w-full px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white text-sm placeholder-white/40 focus:outline-none focus:border-violet-400/60" />
                    </div>
                );
            case 'product-to-model':
                return (
                    <div className="space-y-4">
                        <div>
                            <label className="text-xs text-white/50 mb-1.5 block">Product Image *</label>
                            {renderDropZone(dz1, 'Product photo', true)}
                        </div>
                        <div>
                            <label className="text-xs text-white/50 mb-1.5 block">Face Reference (optional)</label>
                            {renderDropZone(dz2, 'Face to guide model identity', false)}
                        </div>
                        <input type="text" placeholder="Prompt (e.g. studio background, casual)" value={promptText} onChange={e => setPromptText(e.target.value)} className="w-full px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white text-sm placeholder-white/40 focus:outline-none focus:border-violet-400/60" />
                        <select value={aspectRatio} onChange={e => setAspectRatio(e.target.value)} className="w-full px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white text-sm focus:outline-none focus:border-violet-400/60">
                            <option value="">Auto (from image)</option>
                            {ASPECT_RATIOS.map(r => <option key={r} value={r}>{r}</option>)}
                        </select>
                    </div>
                );
            case 'face-to-model':
                return (
                    <div className="space-y-4">
                        <div>
                            <label className="text-xs text-white/50 mb-1.5 block">Face / Headshot Image *</label>
                            {renderDropZone(dz1, 'Selfie or headshot', true)}
                        </div>
                        <input type="text" placeholder="Body type guidance (e.g. athletic build)" value={promptText} onChange={e => setPromptText(e.target.value)} className="w-full px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white text-sm placeholder-white/40 focus:outline-none focus:border-violet-400/60" />
                        <select value={aspectRatio} onChange={e => setAspectRatio(e.target.value)} className="w-full px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white text-sm focus:outline-none focus:border-violet-400/60">
                            {['2:3', '1:1', '4:5', '3:4', '9:16'].map(r => <option key={r} value={r}>{r}</option>)}
                        </select>
                    </div>
                );
            case 'model-create':
                return (
                    <div className="space-y-4">
                        <div>
                            <label className="text-xs text-white/50 mb-1.5 block">Model Photos *</label>
                            {renderDropZone(dz1, 'Model images', true)}
                        </div>
                        <input type="text" placeholder="Model name (optional)" value={modelName} onChange={e => setModelName(e.target.value)} className="w-full px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white text-sm placeholder-white/40 focus:outline-none focus:border-violet-400/60" />
                    </div>
                );
            case 'edit':
                return (
                    <div className="space-y-4">
                        <div>
                            <label className="text-xs text-white/50 mb-1.5 block">Source Image *</label>
                            {renderDropZone(dz1, 'Image to edit', true)}
                        </div>
                        <div>
                            <label className="text-xs text-white/50 mb-1.5 block">Mask (optional)</label>
                            {renderDropZone(dz2, 'Region mask (white=edit, black=keep)', false)}
                        </div>
                        <textarea placeholder="Edit prompt * — describe what to change" value={promptText} onChange={e => setPromptText(e.target.value)} rows={3} className="w-full px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white text-sm placeholder-white/40 focus:outline-none focus:border-violet-400/60" />
                    </div>
                );
            case 'reframe':
                return (
                    <div className="space-y-4">
                        <div>
                            <label className="text-xs text-white/50 mb-1.5 block">Source Image *</label>
                            {renderDropZone(dz1, 'Image to reframe', true)}
                        </div>
                        <select value={aspectRatio} onChange={e => setAspectRatio(e.target.value)} className="w-full px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white text-sm focus:outline-none focus:border-violet-400/60">
                            {ASPECT_RATIOS.map(r => <option key={r} value={r}>{r}</option>)}
                        </select>
                    </div>
                );
            case 'image-to-video':
                return (
                    <div className="space-y-4">
                        <div>
                            <label className="text-xs text-white/50 mb-1.5 block">Source Image *</label>
                            {renderDropZone(dz1, 'Image to animate', true)}
                        </div>
                        <input type="text" placeholder="Motion guidance (optional)" value={promptText} onChange={e => setPromptText(e.target.value)} className="w-full px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white text-sm placeholder-white/40 focus:outline-none focus:border-violet-400/60" />
                        <div className="flex gap-4">
                            <div className="flex-1">
                                <label className="text-xs text-white/50 mb-1.5 block">Duration</label>
                                <select value={duration} onChange={e => setDuration(Number(e.target.value))} className="w-full px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white text-sm focus:outline-none focus:border-violet-400/60">
                                    <option value={5}>5 seconds</option>
                                    <option value={10}>10 seconds</option>
                                </select>
                            </div>
                            <div className="flex-1">
                                <label className="text-xs text-white/50 mb-1.5 block">Resolution</label>
                                <select value={resolution} onChange={e => setResolution(e.target.value)} className="w-full px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white text-sm focus:outline-none focus:border-violet-400/60">
                                    <option value="480p">480p</option>
                                    <option value="720p">720p</option>
                                    <option value="1080p">1080p</option>
                                </select>
                            </div>
                        </div>
                    </div>
                );
            case 'background-remove':
                return (
                    <div className="space-y-4">
                        <div>
                            <label className="text-xs text-white/50 mb-1.5 block">Source Image *</label>
                            {renderDropZone(dz1, 'Image to remove background from', true)}
                        </div>
                    </div>
                );
            default:
                return null;
        }
    };

    // Render common options
    const renderOptions = () => {
        if (activeFeature === 'model-create' || activeFeature === 'background-remove') return null;
        const isVideo = activeFeature === 'image-to-video';
        return (
            <div className="flex flex-wrap gap-3 pt-2">
                {!isVideo && activeFeature !== 'reframe' && activeFeature !== 'face-to-model' && activeFeature !== 'product-to-model' && (
                    <select value={generationMode} onChange={e => setGenerationMode(e.target.value)} className="px-3 py-2 rounded-xl bg-white/5 border border-white/10 text-white text-xs focus:outline-none focus:border-violet-400/60">
                        <option value="">Quality: auto</option>
                        <option value="fast">Fast</option>
                        <option value="balanced">Balanced</option>
                        <option value="quality">Quality</option>
                    </select>
                )}
                {(activeFeature === 'tryon-max' || activeFeature === 'edit') && (
                    <select value={numImages} onChange={e => setNumImages(Number(e.target.value))} className="px-3 py-2 rounded-xl bg-white/5 border border-white/10 text-white text-xs focus:outline-none focus:border-violet-400/60">
                        {[1, 2, 3, 4].map(n => <option key={n} value={n}>{n} image{n > 1 ? 's' : ''}</option>)}
                    </select>
                )}
                <select value={resolution} onChange={e => setResolution(e.target.value)} className="px-3 py-2 rounded-xl bg-white/5 border border-white/10 text-white text-xs focus:outline-none focus:border-violet-400/60">
                    {isVideo
                        ? [['480p', '480p'], ['720p', '720p'], ['1080p', '1080p']].map(([v, l]) => <option key={v} value={v}>{l}</option>)
                        : [['1k', '1K (~1MP)'], ['2k', '2K (~4MP)'], ['4k', '4K (~16MP)']].map(([v, l]) => <option key={v} value={v}>{l}</option>)
                    }
                </select>
            </div>
        );
    };

    if (isAvailable === false) {
        return (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 premium-blur p-4">
                <div className="glass-card bg-black/40 rounded-3xl w-full max-w-md overflow-hidden shadow-2xl border border-white/10 p-8 text-center">
                    <Shirt className="w-12 h-12 mx-auto mb-4 text-violet-400" />
                    <h2 className="text-xl font-bold text-white mb-2">Fashn.ai Studio</h2>
                    <p className="text-white/50 text-sm mb-6">Fashn.ai service is not configured. Set <code className="bg-white/10 px-2 py-0.5 rounded text-violet-300">FASHN_API_KEY</code> in your backend .env file.</p>
                    <button onClick={onClose} className="px-6 py-2.5 rounded-xl bg-white/10 hover:bg-white/20 text-white text-sm transition-all">Close</button>
                </div>
            </div>
        );
    }

    const meta = FEATURE_META[activeFeature];

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 premium-blur p-2 sm:p-4">
            <div className="glass-card bg-black/40 rounded-3xl w-full max-w-5xl overflow-hidden shadow-2xl flex flex-col max-h-[96vh] border border-white/10">

                {/* Header */}
                <div className="p-4 sm:p-5 border-b border-white/10 flex justify-between items-center premium-blur bg-white/5 shrink-0">
                    <div className="flex items-center gap-3">
                        <span className="text-2xl">{meta?.icon}</span>
                        <div>
                            <h2 className="text-lg sm:text-xl font-black text-gradient">{meta?.name || 'Fashn.ai Studio'}</h2>
                            <p className="text-xs text-white/40">{meta?.description}</p>
                        </div>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-full transition-colors">
                        <X className="w-5 h-5 text-white/70 hover:text-white" />
                    </button>
                </div>

                {/* Feature nav */}
                <div className="overflow-x-auto shrink-0 scrollbar-hide">
                    {renderNav()}
                </div>

                {/* Body */}
                <div className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-5">
                    {/* Inputs */}
                    <div className="bg-white/[0.03] rounded-2xl p-4 border border-white/5">
                        <h3 className="text-sm font-semibold text-white/60 mb-3 uppercase tracking-wider">Inputs</h3>
                        {renderInputs()}
                        {renderOptions()}
                    </div>

                    {/* Run button */}
                    <button
                        onClick={handleRun}
                        disabled={isLoading}
                        className="w-full py-3 rounded-2xl bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-500 hover:to-purple-500 disabled:from-violet-600/30 disabled:to-purple-600/30 disabled:cursor-not-allowed text-white font-bold text-sm transition-all flex items-center justify-center gap-2"
                    >
                        {isLoading ? (
                            <><Loader2 className="w-5 h-5 animate-spin" /> Processing...</>
                        ) : (
                            <><Sparkles className="w-5 h-5" /> Run {meta?.name || 'Feature'}</>
                        )}
                    </button>

                    {/* Error */}
                    {error && (
                        <div className="bg-red-500/10 border border-red-500/30 rounded-2xl p-4 text-sm text-red-300">
                            {error}
                        </div>
                    )}

                    {/* Result */}
                    {resultUrl && (
                        <div className="bg-white/[0.03] rounded-2xl p-4 border border-white/5">
                            <h3 className="text-sm font-semibold text-white/60 mb-3 uppercase tracking-wider">Result</h3>
                            <div className="flex items-center justify-center">
                                <img src={resultUrl} alt="Result" className="max-w-full max-h-[50vh] rounded-xl shadow-lg" />
                            </div>
                            <div className="flex gap-2 mt-3">
                                <a href={resultUrl} download="fashn-result.png" className="flex-1 py-2 rounded-xl bg-white/10 hover:bg-white/20 text-white text-sm text-center transition-all">Download</a>
                            </div>
                        </div>
                    )}

                    {/* Video result */}
                    {videoUrl && (
                        <div className="bg-white/[0.03] rounded-2xl p-4 border border-white/5">
                            <h3 className="text-sm font-semibold text-white/60 mb-3 uppercase tracking-wider">Result Video</h3>
                            <div className="flex items-center justify-center">
                                <video src={videoUrl} controls autoPlay muted loop className="max-w-full max-h-[50vh] rounded-xl shadow-lg" />
                            </div>
                            <div className="flex gap-2 mt-3">
                                <a href={videoUrl} target="_blank" rel="noopener noreferrer" className="flex-1 py-2 rounded-xl bg-white/10 hover:bg-white/20 text-white text-sm text-center transition-all">Open Video</a>
                            </div>
                        </div>
                    )}

                    {/* Preview images */}
                    {(preview1 || preview2) && !resultUrl && !videoUrl && (
                        <div className="bg-white/[0.03] rounded-2xl p-4 border border-white/5">
                            <h3 className="text-sm font-semibold text-white/60 mb-3 uppercase tracking-wider">Previews</h3>
                            <div className="flex gap-3 flex-wrap">
                                {preview1 && <img src={preview1} alt="Input 1" className="h-24 rounded-xl border border-white/10" />}
                                {preview2 && <img src={preview2} alt="Input 2" className="h-24 rounded-xl border border-white/10" />}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default FashnStudio;
