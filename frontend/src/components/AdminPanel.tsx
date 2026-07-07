import React, { useState, useEffect, useCallback, useRef } from 'react';
import { X, Shield, CheckCircle, XCircle, Clock, RefreshCw, LogIn, Lock, ChevronDown, ChevronUp } from 'lucide-react';
import { adminGetPendingRequests, adminApproveTryOn, adminRejectTryOn } from '../api';
import type { TryOnRequestItem } from '../api';

interface AdminPanelProps {
    isOpen: boolean;
    onClose: () => void;
    adminKey: string | null;
    onSetAdminKey: (key: string) => void;
}

const AdminPanel: React.FC<AdminPanelProps> = ({ isOpen, onClose, adminKey, onSetAdminKey }) => {
    const [password, setPassword] = useState('');
    const [loginError, setLoginError] = useState('');
    const [pending, setPending] = useState<TryOnRequestItem[]>([]);
    const [processing, setProcessing] = useState<number | null>(null);
    const [rejectNotes, setRejectNotes] = useState<Record<number, string>>({});
    const [expandedId, setExpandedId] = useState<number | null>(null);
    const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

    const fetchPending = useCallback(async () => {
        if (!adminKey) return;
        try {
            const items = await adminGetPendingRequests(adminKey);
            setPending(items);
        } catch (e: any) {
            if (e?.response?.status === 403 || e?.response?.status === 401) {
                onSetAdminKey('');
            }
        }
    }, [adminKey, onSetAdminKey]);

    useEffect(() => {
        if (adminKey) {
            fetchPending();
            pollRef.current = setInterval(fetchPending, 8000);
        }
        return () => {
            if (pollRef.current) clearInterval(pollRef.current);
        };
    }, [adminKey, fetchPending]);

    const handleLogin = () => {
        setLoginError('');
        if (!password.trim()) {
            setLoginError('Enter the admin password');
            return;
        }
        onSetAdminKey(password.trim());
        setPassword('');
    };

    const handleApprove = async (id: number) => {
        if (!adminKey) return;
        setProcessing(id);
        try {
            await adminApproveTryOn(adminKey, id);
            await fetchPending();
        } catch (e: any) {
            console.error('Approve failed:', e);
            alert(e?.response?.data?.detail || 'Failed to approve');
        } finally {
            setProcessing(null);
        }
    };

    const handleReject = async (id: number) => {
        if (!adminKey) return;
        setProcessing(id);
        try {
            await adminRejectTryOn(adminKey, id, rejectNotes[id] || '');
            await fetchPending();
        } catch (e: any) {
            console.error('Reject failed:', e);
            alert(e?.response?.data?.detail || 'Failed to reject');
        } finally {
            setProcessing(null);
        }
    };

    const toggleExpand = async (id: number) => {
        if (expandedId === id) {
            setExpandedId(null);
            return;
        }
        setExpandedId(id);
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/80 premium-blur p-4">
            <div className="glass-card bg-black/40 rounded-3xl w-full max-w-3xl overflow-hidden shadow-2xl flex flex-col max-h-[90vh] border border-white/10">

                {/* Header */}
                <div className="p-6 border-b border-white/10 flex justify-between items-center premium-blur bg-white/5">
                    <h2 className="text-2xl font-black text-gradient flex items-center gap-3">
                        <Shield className="w-6 h-6 text-amber-400" />
                        Admin Panel
                    </h2>
                    <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-full transition-colors">
                        <X className="w-6 h-6 text-white/70 hover:text-white" />
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6">
                    {!adminKey ? (
                        /* Login Screen */
                        <div className="max-w-sm mx-auto py-12">
                            <div className="flex justify-center mb-8">
                                <div className="w-24 h-24 bg-amber-500/20 rounded-full flex items-center justify-center">
                                    <Lock className="w-12 h-12 text-amber-400" />
                                </div>
                            </div>
                            <h3 className="text-2xl font-black text-white text-center mb-2">Admin Access</h3>
                            <p className="text-slate-400 text-center mb-8">Enter the admin password to manage try-on requests</p>
                            <div className="space-y-4">
                                <input
                                    type="password"
                                    value={password}
                                    onChange={e => setPassword(e.target.value)}
                                    onKeyDown={e => e.key === 'Enter' && handleLogin()}
                                    placeholder="Admin password"
                                    className="w-full px-5 py-4 bg-white/5 border border-white/10 rounded-2xl text-white placeholder:text-slate-500 focus:outline-none focus:border-amber-500/50 focus:ring-2 focus:ring-amber-500/20 backdrop-blur-xl transition-all"
                                />
                                {loginError && <p className="text-rose-400 text-sm text-center">{loginError}</p>}
                                <button
                                    onClick={handleLogin}
                                    className="w-full py-4 bg-gradient-to-r from-amber-600 to-orange-600 text-white rounded-full font-bold hover:scale-[1.02] transition-all flex items-center justify-center gap-2"
                                >
                                    <LogIn className="w-5 h-5" />
                                    Login
                                </button>
                            </div>
                        </div>
                    ) : (
                        /* Dashboard */
                        <div>
                            <div className="flex items-center justify-between mb-6">
                                <div className="flex items-center gap-2">
                                    <h3 className="text-xl font-bold text-white">Pending Requests</h3>
                                    <span className="px-3 py-1 bg-amber-500/20 text-amber-300 text-sm rounded-full font-semibold">
                                        {pending.length}
                                    </span>
                                </div>
                                <button
                                    onClick={fetchPending}
                                    className="p-2 hover:bg-white/10 rounded-full transition-colors"
                                    title="Refresh"
                                >
                                    <RefreshCw className="w-5 h-5 text-slate-400" />
                                </button>
                            </div>

                            {pending.length === 0 ? (
                                <div className="text-center py-16 text-slate-500">
                                    <CheckCircle className="w-16 h-16 mx-auto mb-4 text-green-500/40" />
                                    <p className="text-xl font-bold text-white mb-2">All caught up!</p>
                                    <p>No pending try-on requests.</p>
                                </div>
                            ) : (
                                <div className="space-y-4">
                                    {pending.map(req => (
                                        <div key={req.id} className="bg-white/5 premium-blur rounded-2xl border border-white/10 overflow-hidden">
                                            {/* Summary row */}
                                            <div className="p-4 flex items-center justify-between">
                                                <div className="flex items-center gap-4">
                                                    <div className="p-2 bg-amber-500/20 rounded-full">
                                                        <Clock className="w-5 h-5 text-amber-400" />
                                                    </div>
                                                    <div>
                                                        <p className="text-sm font-medium text-white">
                                                            Request #{req.id}
                                                        </p>
                                                        <p className="text-xs text-slate-400">
                                                            {req.session_id} · {new Date(req.created_at).toLocaleString()}
                                                        </p>
                                                    </div>
                                                </div>
                                                <button
                                                    onClick={() => toggleExpand(req.id)}
                                                    className="p-1 hover:bg-white/10 rounded-full transition-colors"
                                                >
                                                    {expandedId === req.id ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                                                </button>
                                            </div>

                                            {/* Expanded detail */}
                                            {expandedId === req.id && (
                                                <div className="px-4 pb-4 border-t border-white/10 pt-4">
                                                    <p className="text-xs text-slate-400 mb-4">Request images are available when try-on runs</p>

                                                    <div className="flex items-center gap-3 mb-4">
                                                        <input
                                                            type="text"
                                                            value={rejectNotes[req.id] || ''}
                                                            onChange={e => setRejectNotes({ ...rejectNotes, [req.id]: e.target.value })}
                                                            placeholder="Rejection note (optional)"
                                                            className="flex-1 px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder:text-slate-500 text-sm focus:outline-none focus:border-amber-500/50"
                                                        />
                                                    </div>

                                                    <div className="flex gap-3">
                                                        <button
                                                            onClick={() => handleApprove(req.id)}
                                                            disabled={processing === req.id}
                                                            className={`flex-1 py-3 rounded-xl font-bold flex items-center justify-center gap-2 transition-all
                                                                ${processing === req.id
                                                                    ? 'bg-green-500/30 text-green-300'
                                                                    : 'bg-green-600/20 text-green-400 hover:bg-green-600/30 border border-green-500/20'}
                                                            `}
                                                        >
                                                            {processing === req.id ? (
                                                                <div className="w-5 h-5 border-2 border-white/20 border-t-green-400 rounded-full animate-spin" />
                                                            ) : <CheckCircle className="w-5 h-5" />}
                                                            Approve & Run
                                                        </button>
                                                        <button
                                                            onClick={() => handleReject(req.id)}
                                                            disabled={processing === req.id}
                                                            className={`flex-1 py-3 rounded-xl font-bold flex items-center justify-center gap-2 transition-all
                                                                ${processing === req.id
                                                                    ? 'bg-rose-500/30 text-rose-300'
                                                                    : 'bg-rose-600/20 text-rose-400 hover:bg-rose-600/30 border border-rose-500/20'}
                                                            `}
                                                        >
                                                            <XCircle className="w-5 h-5" />
                                                            Reject
                                                        </button>
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default AdminPanel;