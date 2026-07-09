import React, { useState, useCallback, useEffect, useRef } from 'react';
import { useDropzone } from 'react-dropzone';
import { X, Shirt, Camera, Send, Clock, CheckCircle, XCircle, Shield, Loader2 } from 'lucide-react';
import { submitTryOnRequest, listTryOnRequests, requestTryOnAccess, checkTryOnAccess } from '../api';
import type { TryOnRequestItem } from '../api';

interface TryOnModalProps {
    isOpen: boolean;
    onClose: () => void;
    productImage: string;
    sessionId?: string;
    onTryOn?: (file: File) => Promise<Blob>;
}

type GateState = 'loading' | 'none' | 'pending' | 'approved' | 'rejected';

const TryOnModal: React.FC<TryOnModalProps> = ({ isOpen, onClose, productImage, sessionId, onTryOn }) => {
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [preview, setPreview] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [requests, setRequests] = useState<TryOnRequestItem[]>([]);
    const [requestSuccess, setRequestSuccess] = useState(false);
    const [viewResult, setViewResult] = useState<string | null>(null);
    const [directResult, setDirectResult] = useState<string | null>(null);
    const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

    // Gate state
    const [gateState, setGateState] = useState<GateState>('loading');
    const [gateNote, setGateNote] = useState<string | null>(null);
    const [isSendingRequest, setIsSendingRequest] = useState(false);

    // Generate a persistent session ID if none provided
    const effectiveSessionId = useRef<string>(
        sessionId || localStorage.getItem('tryon_session_id') || (() => {
            const id = 'session_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8);
            localStorage.setItem('tryon_session_id', id);
            return id;
        })()
    ).current;

    // Check access on mount
    useEffect(() => {
        if (!isOpen) return;
        if (onTryOn) {
            // Direct mode — no gate
            setGateState('approved');
            return;
        }
        checkAccess();
    }, [isOpen]);

    const checkAccess = async () => {
        setGateState('loading');
        setError(null);
        try {
            const result = await checkTryOnAccess(effectiveSessionId);
            setGateState(result.status as GateState);
            setGateNote(result.admin_note || null);
        } catch (e) {
            // If endpoint fails, let user through (graceful degradation)
            console.warn('Access check failed, granting access:', e);
            setGateState('approved');
        }
    };

    const handleSendRequest = async () => {
        setIsSendingRequest(true);
        setError(null);
        try {
            const result = await requestTryOnAccess(effectiveSessionId);
            setGateState('pending');
        } catch (err: any) {
            setError(err?.response?.data?.detail || 'Failed to send request. Try again.');
        } finally {
            setIsSendingRequest(false);
        }
    };

    const onDrop = useCallback((acceptedFiles: File[]) => {
        const file = acceptedFiles[0];
        if (file) {
            setSelectedFile(file);
            setPreview(URL.createObjectURL(file));
            setError(null);
            setRequestSuccess(false);
            setViewResult(null);
        }
    }, []);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: { 'image/*': ['.jpeg', '.jpg', '.png'] },
        maxFiles: 1,
        multiple: false
    });

    const fetchRequests = useCallback(async () => {
        try {
            const items = await listTryOnRequests(effectiveSessionId);
            setRequests(items);
            const completed = items.find(r => r.status === 'completed' && r.result_url);
            if (completed && completed.result_url) {
                setViewResult(completed.result_url);
            }
        } catch (e) {
            // silent — polling errors are expected
        }
    }, [effectiveSessionId]);

    useEffect(() => {
        if (requestSuccess) {
            fetchRequests();
            pollRef.current = setInterval(fetchRequests, 5000);
        }
        return () => {
            if (pollRef.current) clearInterval(pollRef.current);
        };
    }, [requestSuccess, fetchRequests]);

    const handleRequest = async () => {
        if (!selectedFile) return;
        setIsLoading(true);
        setError(null);
        try {
            // Direct mode (onTryOn provided) — execute immediately
            if (onTryOn) {
                const blob = await onTryOn(selectedFile);
                setDirectResult(URL.createObjectURL(blob));
                return;
            }

            // Admin-approval mode — submit and poll
            const garmentResp = await fetch(productImage);
            const garmentBlob = await garmentResp.blob();
            const garmentFile = new File([garmentBlob], 'garment.png', { type: 'image/png' });

            await submitTryOnRequest(effectiveSessionId, selectedFile, garmentFile);
            setRequestSuccess(true);
            await fetchRequests();
        } catch (err: any) {
            console.error(err);
            setError(err?.response?.data?.detail || "Failed to submit request. Try again.");
        } finally {
            setIsLoading(false);
        }
    };

    const latestStatus = requests[0];

    const handleReset = () => {
        setSelectedFile(null);
        setPreview(null);
        setError(null);
        setRequestSuccess(false);
        setViewResult(null);
        if (pollRef.current) clearInterval(pollRef.current);
    };

    if (!isOpen) return null;

    // ── Gate Screen (shown when not yet approved) ──────────────────────

    const renderGate = () => {
        if (gateState === 'loading') {
            return (
                <div className="h-full w-full flex items-center justify-center">
                    <Loader2 className="w-8 h-8 text-violet-400 animate-spin" />
                </div>
            );
        }

        if (gateState === 'pending') {
            return (
                <div className="h-full w-full flex flex-col items-center justify-center text-center p-8 bg-white/5 premium-blur rounded-3xl border border-white/10">
                    <div className="w-20 h-20 bg-amber-500/20 rounded-full flex items-center justify-center mb-6">
                        <Clock className="w-10 h-10 text-amber-400" />
                    </div>
                    <h3 className="text-2xl font-black text-white mb-2">Request Sent ✓</h3>
                    <p className="text-slate-400 mb-4 max-w-sm leading-relaxed">
                        Your access request has been submitted. An admin will review it shortly.
                        You'll be able to use the Virtual Try-On once approved.
                    </p>
                    <div className="flex items-center gap-2 text-amber-400 text-sm mb-4">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span>Waiting for admin approval...</span>
                    </div>
                    <button
                        onClick={checkAccess}
                        className="px-6 py-3 border border-white/10 rounded-full text-white font-bold hover:bg-white/5 transition-all bg-white/5 text-sm"
                    >
                        Check Status
                    </button>
                </div>
            );
        }

        if (gateState === 'rejected') {
            return (
                <div className="h-full w-full flex flex-col items-center justify-center text-center p-8 bg-white/5 premium-blur rounded-3xl border border-white/10">
                    <div className="w-20 h-20 bg-rose-500/20 rounded-full flex items-center justify-center mb-6">
                        <XCircle className="w-10 h-10 text-rose-400" />
                    </div>
                    <h3 className="text-2xl font-black text-white mb-2">Access Declined</h3>
                    <p className="text-slate-400 mb-6 max-w-sm leading-relaxed">
                        {gateNote || 'Admin did not approve your access request.'}
                    </p>
                    <button
                        onClick={handleSendRequest}
                        className="px-8 py-3 bg-gradient-to-r from-violet-600 to-cyan-600 text-white rounded-full font-bold hover:scale-105 transition-all"
                    >
                        Request Again
                    </button>
                </div>
            );
        }

        // gateState === 'none' — Show the gate message + Send Request
        return (
            <div className="h-full w-full flex flex-col items-center justify-center text-center p-8 bg-white/5 premium-blur rounded-3xl border border-white/10">
                <div className="w-32 h-32 bg-amber-500/20 rounded-full mb-6 blur-2xl absolute"></div>
                <div className="w-20 h-20 bg-amber-500/20 rounded-full flex items-center justify-center mb-6 relative z-10">
                    <Shield className="w-10 h-10 text-amber-400" />
                </div>
                <h3 className="text-2xl font-black text-white relative z-10 mb-3">
                    Virtual Try-On
                </h3>
                <p className="text-amber-300 font-bold text-lg relative z-10 mb-3">
                    You need admin approval to use this feature as the tokens are limited.
                </p>
                <p className="text-slate-400 mb-8 max-w-sm relative z-10 leading-relaxed">
                    Click the button below to send an access request to the admin.
                    Once approved, you'll be able to upload your photo and try on garments.
                </p>
                <button
                    onClick={handleSendRequest}
                    disabled={isSendingRequest}
                    className={`px-10 py-4 rounded-full font-bold shadow-xl transition-all relative z-10 flex items-center gap-2
                        ${isSendingRequest
                            ? 'bg-white/10 text-white/40 cursor-not-allowed border border-white/5'
                            : 'bg-gradient-to-r from-amber-600 to-orange-600 text-white hover:scale-105 active:scale-95 shadow-amber-500/30'}
                    `}
                >
                    {isSendingRequest ? (
                        <>
                            <Loader2 className="w-5 h-5 animate-spin" />
                            Sending...
                        </>
                    ) : (
                        <>
                            <Send className="w-5 h-5" />
                            Send Request
                        </>
                    )}
                </button>
                {error && (
                    <p className="mt-6 text-rose-400 font-medium px-4 py-2 bg-rose-500/10 rounded-lg">{error}</p>
                )}
            </div>
        );
    };

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
                    {gateState !== 'approved' ? (
                        /* Show gate screen only (left side empty) */
                        <div className="max-w-md mx-auto py-8">
                            {renderGate()}
                        </div>
                    ) : (
                        /* Show full try-on UI */
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
                                        {!viewResult && !isLoading && (
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

                            {/* Right: Status / Action */}
                            <div className="flex flex-col items-center justify-center relative">
                                <div className="md:hidden w-full h-px bg-white/10 my-4"></div>

                                {viewResult || directResult ? (
                                    /* Show completed result */
                                    <div className="h-full w-full flex flex-col gap-5">
                                        <h3 className="text-2xl font-black text-white">Your New Look ✨</h3>
                                        <div className="flex-1 relative rounded-3xl overflow-hidden border border-white/20 bg-black/40 flex items-center justify-center group shadow-2xl premium-blur">
                                            <img src={directResult || viewResult || ''} alt="Try On Result" className="max-h-full max-w-full object-contain" />
                                            <a
                                                href={directResult || viewResult || ''}
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
                                ) : requestSuccess && latestStatus ? (
                                    /* Show request status */
                                    <div className="h-full w-full flex flex-col items-center justify-center text-center p-8 bg-white/5 premium-blur rounded-3xl border border-white/10">
                                        {latestStatus.status === 'pending' && (
                                            <>
                                                <div className="w-20 h-20 bg-amber-500/20 rounded-full flex items-center justify-center mb-6">
                                                    <Clock className="w-10 h-10 text-amber-400" />
                                                </div>
                                                <h3 className="text-2xl font-black text-white mb-2">Awaiting Admin Approval</h3>
                                                <p className="text-slate-400 mb-4 max-w-sm leading-relaxed">
                                                    Your try-on request has been submitted. An admin will review it shortly.
                                                </p>
                                                <div className="flex items-center gap-2 text-amber-400 text-sm">
                                                    <Loader2 className="w-4 h-4 animate-spin" />
                                                    <span>Auto-refreshing every 5s...</span>
                                                </div>
                                                <p className="mt-6 px-5 py-3 bg-amber-500/10 border border-amber-500/20 rounded-xl text-amber-300 text-sm">
                                                    Try-on credits are limited — admin gates usage to save tokens.
                                                </p>
                                            </>
                                        )}
                                        {latestStatus.status === 'rejected' && (
                                            <>
                                                <div className="w-20 h-20 bg-rose-500/20 rounded-full flex items-center justify-center mb-6">
                                                    <XCircle className="w-10 h-10 text-rose-400" />
                                                </div>
                                                <h3 className="text-2xl font-black text-white mb-2">Request Declined</h3>
                                                <p className="text-slate-400 mb-2 max-w-sm leading-relaxed">
                                                    {latestStatus.admin_note || 'Admin did not approve this request.'}
                                                </p>
                                                <button
                                                    onClick={handleReset}
                                                    className="mt-6 px-8 py-3 border border-white/10 rounded-full text-white font-bold hover:bg-white/5 transition-all bg-white/5"
                                                >
                                                    Try Again
                                                </button>
                                            </>
                                        )}
                                        {latestStatus.status === 'completed' && latestStatus.result_url && (
                                            <>
                                                <div className="w-20 h-20 bg-green-500/20 rounded-full flex items-center justify-center mb-6">
                                                    <CheckCircle className="w-10 h-10 text-green-400" />
                                                </div>
                                                <h3 className="text-2xl font-black text-white mb-2">Approved!</h3>
                                                <button
                                                    onClick={() => setViewResult(latestStatus.result_url!)}
                                                    className="mt-4 px-8 py-3 bg-gradient-to-r from-violet-600 to-cyan-600 text-white rounded-full font-bold hover:scale-105 transition-all"
                                                >
                                                    View Result
                                                </button>
                                            </>
                                        )}
                                    </div>
                                ) : (
                                    /* Default: submission form */
                                    <div className="h-full w-full flex flex-col items-center justify-center text-center p-8 bg-white/5 premium-blur rounded-3xl border border-white/10">
                                        {isLoading ? (
                                            <div className="flex flex-col items-center gap-4">
                                                <div className="w-16 h-16 border-4 border-white/10 border-t-violet-500 rounded-full animate-spin"></div>
                                                <p className="text-xl font-bold animate-pulse text-gradient">Submitting request...</p>
                                            </div>
                                        ) : (
                                            <>
                                                <div className="w-32 h-32 bg-violet-500/20 rounded-full mb-6 blur-2xl absolute"></div>
                                                <h3 className="text-2xl font-black text-white relative z-10 mb-2">Try On a New Look</h3>
                                                <p className="text-slate-400 mb-8 max-w-xs relative z-10 leading-relaxed text-lg">
                                                    Upload your photo on the left, then submit for admin approval.
                                                </p>
                                                <button
                                                    onClick={handleRequest}
                                                    disabled={!selectedFile}
                                                    className={`px-10 py-4 rounded-full font-bold shadow-xl transition-all relative z-10 flex items-center gap-2
                                            ${!selectedFile
                                                            ? 'bg-white/10 text-white/40 cursor-not-allowed border border-white/5'
                                                            : 'bg-gradient-to-r from-violet-600 to-cyan-600 text-white hover:scale-105 active:scale-95 shadow-violet-500/30'}
                                        `}
                                                >
                                                    <Send className="w-5 h-5" />
                                                    {onTryOn ? 'Try On Now' : 'Request Admin Approval'}
                                                </button>
                                                {error && (
                                                    <p className="mt-6 text-rose-400 font-medium px-4 py-2 bg-rose-500/10 rounded-lg">{error}</p>
                                                )}
                                                <p className="mt-4 text-xs text-slate-500 max-w-xs">
                                                    Admin will review your request before running the try-on to conserve API credits.
                                                </p>
                                            </>
                                        )}
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default TryOnModal;
