import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  X, Shield, CheckCircle, XCircle, Clock, RefreshCw,
  LogIn, Lock, ChevronDown, ChevronUp, Eye, EyeOff,
  Settings, Server, Database, Key, Sliders, Save, AlertTriangle
} from 'lucide-react';
import axios from 'axios';
import { adminGetPendingRequests, adminApproveTryOn, adminRejectTryOn, getAdminSettings, updateAdminSettings } from '../api';
import type { TryOnRequestItem, SettingItem } from '../api';

interface AdminPanelProps {
  isOpen: boolean;
  onClose: () => void;
  adminKey: string | null;
  onSetAdminKey: (key: string) => void;
}

const CATEGORY_ICONS: Record<string, typeof Key> = {
  'Vector DB': Database,
  'AI / LLM': Server,
  'Try-On': Sliders,
  Cloudinary: Settings,
  Database: Database,
  Admin: Key,
  App: Settings,
};

type Tab = 'requests' | 'credentials';

const AdminPanel: React.FC<AdminPanelProps> = ({ isOpen, onClose, adminKey, onSetAdminKey }) => {
  const [password, setPassword] = useState('');
  const [loginError, setLoginError] = useState('');
  const [pending, setPending] = useState<TryOnRequestItem[]>([]);
  const [processing, setProcessing] = useState<number | null>(null);
  const [rejectNotes, setRejectNotes] = useState<Record<number, string>>({});
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [tab, setTab] = useState<Tab>('requests');

  // Credentials state
  const [settings, setSettings] = useState<SettingItem[]>([]);
  const [edits, setEdits] = useState<Record<string, string>>({});
  const [revealed, setRevealed] = useState<Record<string, boolean>>({});
  const [settingsLoading, setSettingsLoading] = useState(false);
  const [settingsSaving, setSettingsSaving] = useState(false);
  const [settingsError, setSettingsError] = useState('');
  const [settingsSuccess, setSettingsSuccess] = useState('');
  const [confirmSave, setConfirmSave] = useState(false);

  const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

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

  useEffect(() => {
    if (adminKey && tab === 'credentials') {
      loadSettings();
    }
  }, [adminKey, tab]);

  const handleLogin = async () => {
    setLoginError('');
    if (!password.trim()) {
      setLoginError('Enter the admin password');
      return;
    }
    try {
      const resp = await axios.post(`${apiBase}/admin/login`, { password: password.trim() });
      onSetAdminKey(resp.data.token);
      setPassword('');
    } catch (e: any) {
      setLoginError(e?.response?.data?.detail || 'Invalid password');
    }
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

  // ── Credentials Manager ─────────────────────────────────────────────

  const loadSettings = async () => {
    if (!adminKey) return;
    setSettingsLoading(true);
    setSettingsError('');
    try {
      const data = await getAdminSettings(adminKey);
      setSettings(data.settings);
      setEdits({});
      setRevealed({});
      setConfirmSave(false);
      setSettingsSuccess('');
    } catch (e: any) {
      setSettingsError(e?.response?.data?.detail || 'Failed to load settings');
      if (e?.response?.status === 403 || e?.response?.status === 401) {
        onSetAdminKey('');
      }
    } finally {
      setSettingsLoading(false);
    }
  };

  const getOriginalValue = (key: string): string => {
    const s = settings.find(s => s.key === key);
    return s?.value || '';
  };

  const handleEditChange = (key: string, value: string) => {
    setEdits(prev => ({ ...prev, [key]: value }));
    setSettingsSuccess('');
    setSettingsError('');
  };

  const toggleReveal = (key: string) => {
    setRevealed(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const hasUnsavedChanges = (): boolean => {
    return Object.keys(edits).length > 0;
  };

  const canSave = (): boolean => {
    return hasUnsavedChanges() && !settingsSaving;
  };

  const handleSave = async () => {
    if (!adminKey || !canSave()) return;
    if (!confirmSave) {
      setConfirmSave(true);
      return;
    }
    setSettingsSaving(true);
    setSettingsError('');
    setSettingsSuccess('');
    try {
      const result = await updateAdminSettings(adminKey, edits);
      setSettingsSuccess(`${result.updated.length} setting(s) saved.${result.updated.includes('ADMIN_KEY') ? ' Admin password updated.' : ''} ${result.message}`);
      setEdits({});
      setConfirmSave(false);
      // Reload to show masked values
      setTimeout(() => loadSettings(), 1500);
    } catch (e: any) {
      setSettingsError(e?.response?.data?.detail || 'Failed to save settings');
      setConfirmSave(false);
    } finally {
      setSettingsSaving(false);
    }
  };

  const groupedSettings = settings.reduce<Record<string, SettingItem[]>>((acc, s) => {
    if (!acc[s.category]) acc[s.category] = [];
    acc[s.category].push(s);
    return acc;
  }, {});

  // Order categories
  const categoryOrder = ['Vector DB', 'AI / LLM', 'Try-On', 'Cloudinary', 'Database', 'Admin', 'App'];

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
            /* ══ Login Screen ══ */
            <div className="max-w-sm mx-auto py-12">
              <div className="flex justify-center mb-8">
                <div className="w-24 h-24 bg-amber-500/20 rounded-full flex items-center justify-center">
                  <Lock className="w-12 h-12 text-amber-400" />
                </div>
              </div>
              <h3 className="text-2xl font-black text-white text-center mb-2">Admin Access</h3>
              <p className="text-slate-400 text-center mb-8">Enter the admin password to manage the application</p>
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
            /* ══ Dashboard (authenticated) ══ */
            <div>
              {/* Tab Navigation */}
              <div className="flex gap-1 mb-6 bg-white/5 premium-blur rounded-2xl p-1 border border-white/10">
                <button
                  onClick={() => setTab('requests')}
                  className={`flex-1 py-3 px-4 rounded-xl font-bold text-sm transition-all flex items-center justify-center gap-2 ${
                    tab === 'requests'
                      ? 'bg-white/10 text-amber-300 shadow-sm'
                      : 'text-slate-400 hover:text-white hover:bg-white/5'
                  }`}
                >
                  <Clock className="w-4 h-4" />
                  Requests
                  {pending.length > 0 && (
                    <span className="px-2 py-0.5 bg-amber-500/20 text-amber-300 text-xs rounded-full">
                      {pending.length}
                    </span>
                  )}
                </button>
                <button
                  onClick={() => setTab('credentials')}
                  className={`flex-1 py-3 px-4 rounded-xl font-bold text-sm transition-all flex items-center justify-center gap-2 ${
                    tab === 'credentials'
                      ? 'bg-white/10 text-amber-300 shadow-sm'
                      : 'text-slate-400 hover:text-white hover:bg-white/5'
                  }`}
                >
                  <Key className="w-4 h-4" />
                  Credentials
                </button>
              </div>

              {/* ── Requests Tab ── */}
              {tab === 'requests' && (
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
                                  {req.request_type === 'access' ? 'Access Request' : 'Try-On Request'} #{req.id}
                                </p>
                                <p className="text-xs text-slate-400">
                                  {req.session_id} · {new Date(req.created_at).toLocaleString()}
                                </p>
                                {req.request_type === 'access' && (
                                  <p className="text-xs text-amber-400 mt-1">
                                    🔒 User requesting try-on access
                                  </p>
                                )}
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
                                  {req.request_type === 'access' ? 'Approve Access' : 'Approve & Run'}
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

              {/* ── Credentials Tab ── */}
              {tab === 'credentials' && (
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-xl font-bold text-white">Credentials & Settings</h3>
                    <div className="flex items-center gap-2">
                      {hasUnsavedChanges() && (
                        <span className="text-xs text-amber-400 bg-amber-500/10 px-3 py-1 rounded-full">
                          {Object.keys(edits).length} unsaved
                        </span>
                      )}
                      <button
                        onClick={loadSettings}
                        className="p-2 hover:bg-white/10 rounded-full transition-colors"
                        title="Refresh from .env"
                      >
                        <RefreshCw className={`w-5 h-5 text-slate-400 ${settingsLoading ? 'animate-spin' : ''}`} />
                      </button>
                    </div>
                  </div>
                  <p className="text-slate-500 text-sm mb-6">
                    Manage API keys, database URLs, and app configuration. Changes are saved to <code className="text-amber-400/80 bg-white/5 px-1.5 py-0.5 rounded text-xs">.env</code> — some may need a server restart.
                  </p>

                  {settingsLoading && settings.length === 0 ? (
                    <div className="text-center py-16 text-slate-500">
                      <div className="w-12 h-12 border-2 border-slate-500/30 border-t-amber-400 rounded-full animate-spin mx-auto mb-4" />
                      <p>Loading settings...</p>
                    </div>
                  ) : settingsError && settings.length === 0 ? (
                    <div className="text-center py-16">
                      <AlertTriangle className="w-12 h-12 text-rose-400/60 mx-auto mb-4" />
                      <p className="text-rose-400">{settingsError}</p>
                      <button onClick={loadSettings} className="mt-4 px-6 py-2 bg-white/10 rounded-xl text-sm hover:bg-white/20 transition-all">
                        Retry
                      </button>
                    </div>
                  ) : (
                    <div className="space-y-6">
                      {/* Settings grouped by category */}
                      {categoryOrder.map(cat => {
                        const items = groupedSettings[cat];
                        if (!items || items.length === 0) return null;
                        const Icon = CATEGORY_ICONS[cat] || Settings;
                        return (
                          <div key={cat}>
                            <div className="flex items-center gap-2 mb-3">
                              <Icon className="w-4 h-4 text-slate-400" />
                              <h4 className="text-sm font-bold text-slate-300 uppercase tracking-wider">{cat}</h4>
                            </div>
                            <div className="space-y-2">
                              {items.map(setting => {
                                const edited = setting.key in edits;
                                const currentDisplay = edited ? edits[setting.key] : setting.value;
                                const isRevealed = revealed[setting.key];
                                const showMask = setting.sensitive && !isRevealed && !edited;
                                const hasChanged = edited && edits[setting.key] !== getOriginalValue(setting.key);

                                return (
                                  <div
                                    key={setting.key}
                                    className={`bg-white/5 rounded-xl border transition-all ${
                                      hasChanged
                                        ? 'border-amber-500/40 bg-amber-500/5'
                                        : 'border-white/10 hover:border-white/20'
                                    }`}
                                  >
                                    <div className="p-4">
                                      <div className="flex items-start justify-between gap-2 mb-2">
                                        <div className="min-w-0">
                                          <label className="text-sm font-semibold text-white block truncate">
                                            {setting.label}
                                          </label>
                                          <p className="text-xs text-slate-500">{setting.description}</p>
                                        </div>
                                        <div className="flex items-center gap-1 shrink-0">
                                          {/* Reveal toggle for sensitive fields */}
                                          {setting.sensitive && (
                                            <button
                                              onClick={() => toggleReveal(setting.key)}
                                              className="p-1.5 hover:bg-white/10 rounded-lg transition-colors"
                                              title={isRevealed ? 'Hide value' : 'Show value'}
                                            >
                                              {isRevealed ? <EyeOff className="w-3.5 h-3.5 text-slate-400" /> : <Eye className="w-3.5 h-3.5 text-slate-400" />}
                                            </button>
                                          )}
                                          {/* Edit toggle */}
                                          <button
                                            onClick={() => {
                                              if (setting.key in edits) {
                                                const newEdits = { ...edits };
                                                delete newEdits[setting.key];
                                                setEdits(newEdits);
                                              } else {
                                                handleEditChange(setting.key, getOriginalValue(setting.key));
                                              }
                                            }}
                                            className={`p-1.5 rounded-lg transition-colors ${
                                              edited ? 'bg-amber-500/20 text-amber-400' : 'hover:bg-white/10 text-slate-400'
                                            }`}
                                            title={edited ? 'Cancel edit' : 'Edit'}
                                          >
                                            {edited ? <X className="w-3.5 h-3.5" /> : <Settings className="w-3.5 h-3.5" />}
                                          </button>
                                        </div>
                                      </div>

                                      {/* Value display / input */}
                                      {edited ? (
                                        <input
                                          type={setting.sensitive && !isRevealed ? 'password' : 'text'}
                                          value={edits[setting.key] || ''}
                                          onChange={e => handleEditChange(setting.key, e.target.value)}
                                          onFocus={e => e.target.select()}
                                          placeholder={`Enter ${setting.label}`}
                                          className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-white text-sm placeholder:text-slate-600 focus:outline-none focus:border-amber-500/50 focus:ring-2 focus:ring-amber-500/20 transition-all font-mono"
                                          autoFocus
                                        />
                                      ) : (
                                        <div className="px-4 py-2.5 bg-white/5 rounded-xl border border-white/5">
                                          <code className="text-sm text-slate-300 break-all font-mono">
                                            {showMask ? setting.value : (setting.value || <span className="text-slate-600 italic">not set</span>)}
                                          </code>
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        );
                      })}

                      {/* Status messages */}
                      {settingsError && (
                        <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl">
                          <p className="text-sm text-rose-400 flex items-center gap-2">
                            <AlertTriangle className="w-4 h-4 shrink-0" />
                            {settingsError}
                          </p>
                        </div>
                      )}
                      {settingsSuccess && (
                        <div className="p-4 bg-green-500/10 border border-green-500/20 rounded-xl">
                          <p className="text-sm text-green-400 flex items-center gap-2">
                            <CheckCircle className="w-4 h-4 shrink-0" />
                            {settingsSuccess}
                          </p>
                        </div>
                      )}

                      {/* Save bar */}
                      {hasUnsavedChanges() && (
                        <div className="sticky bottom-0 -mx-2 px-2 pt-4 pb-2 bg-gradient-to-t from-black/80 via-black/60 to-transparent">
                          <div className="bg-white/5 premium-blur rounded-2xl border border-white/10 p-4">
                            {confirmSave ? (
                              <div className="flex items-center justify-between">
                                <p className="text-sm text-amber-400 flex items-center gap-2">
                                  <AlertTriangle className="w-4 h-4" />
                                  Save {Object.keys(edits).length} change(s)? This writes directly to .env.
                                </p>
                                <div className="flex gap-2">
                                  <button
                                    onClick={() => setConfirmSave(false)}
                                    className="px-4 py-2 rounded-xl text-sm font-bold bg-white/10 text-slate-300 hover:bg-white/20 transition-all"
                                    disabled={settingsSaving}
                                  >
                                    Cancel
                                  </button>
                                  <button
                                    onClick={handleSave}
                                    disabled={settingsSaving}
                                    className="px-6 py-2 rounded-xl text-sm font-bold bg-gradient-to-r from-amber-600 to-orange-600 text-white hover:scale-[1.02] transition-all flex items-center gap-2 disabled:opacity-50"
                                  >
                                    {settingsSaving ? (
                                      <>
                                        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                        Saving...
                                      </>
                                    ) : (
                                      <>
                                        <Save className="w-4 h-4" />
                                        Confirm Save
                                      </>
                                    )}
                                  </button>
                                </div>
                              </div>
                            ) : (
                              <button
                                onClick={handleSave}
                                disabled={settingsSaving}
                                className="w-full py-3 rounded-xl font-bold bg-gradient-to-r from-amber-600 to-orange-600 text-white hover:scale-[1.01] transition-all flex items-center justify-center gap-2 disabled:opacity-50"
                              >
                                <Save className="w-5 h-5" />
                                Save {Object.keys(edits).length} Change{Object.keys(edits).length !== 1 ? 's' : ''}
                              </button>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
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
