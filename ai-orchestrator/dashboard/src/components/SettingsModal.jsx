import React, { useState, useEffect } from 'react';
import { X, Shield, Terminal, Settings } from 'lucide-react';

export const SettingsModal = ({ onClose, currentConfig, onUpdate }) => {
    const [config, setConfig] = useState(currentConfig || { dry_run_mode: true });
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (currentConfig) setConfig(currentConfig);
    }, [currentConfig]);

    const handleToggleDryRun = async () => {
        const newValue = !config.dry_run_mode;
        setLoading(true);
        try {
            const res = await fetch('api/config', {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ dry_run_mode: newValue })
            });
            if (res.ok) {
                const data = await res.json();
                setConfig(prev => ({ ...prev, dry_run_mode: data.dry_run_mode }));
                if (onUpdate) onUpdate({ ...config, dry_run_mode: data.dry_run_mode });
            }
        } catch (e) {
            console.error("Failed to update config", e);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
            <div className="bg-slate-900 border border-slate-700 rounded-xl max-w-lg w-full shadow-2xl overflow-hidden">
                <div className="p-4 border-b border-slate-700 flex justify-between items-center bg-slate-800/50">
                    <h2 className="text-lg font-bold text-white flex items-center gap-2">
                        <Settings size={20} className="text-purple-400" />
                        Settings
                    </h2>
                    <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">
                        <X size={24} />
                    </button>
                </div>

                <div className="p-6 space-y-6">
                    {/* Dry Run Toggle */}
                    <div className="bg-slate-800/30 rounded-lg p-4 border border-slate-700/50">
                        <div className="flex justify-between items-start mb-2">
                            <div className="flex items-center gap-2">
                                <Shield size={18} className={config.dry_run_mode ? 'text-amber-400' : 'text-slate-400'} />
                                <h3 className="font-semibold text-slate-200">Dry Run Mode</h3>
                            </div>
                            <div className="flex items-center gap-3">
                                <span className={`text-xs font-mono px-2 py-0.5 rounded ${config.dry_run_mode ? 'bg-amber-500/20 text-amber-300' : 'bg-green-500/20 text-green-300'}`}>
                                    {config.dry_run_mode ? 'ENABLED' : 'DISABLED'}
                                </span>
                                <button
                                    onClick={handleToggleDryRun}
                                    disabled={loading}
                                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 focus:ring-offset-slate-900 ${config.dry_run_mode ? 'bg-purple-600' : 'bg-slate-700'}`}
                                >
                                    <span
                                        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${config.dry_run_mode ? 'translate-x-6' : 'translate-x-1'}`}
                                    />
                                </button>
                            </div>
                        </div>
                        <p className="text-xs text-slate-400 leading-relaxed mb-3">
                            When enabled, the AI will make decisions and log them but acts as a "simulated" execution - no actual changes will be made to Home Assistant entities. Great for testing prompt safety without affecting your home.
                        </p>
                        <div className="text-[10px] text-slate-500 italic border-t border-slate-700/50 pt-2">
                            Note: Toggling this here applies immediately but resets on server restart unless changed in add-on configuration.
                        </div>
                    </div>

                    {/* Metadata (Read Only) */}
                    <div className="space-y-2">
                        <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide">System Info</h4>
                        <div className="grid grid-cols-2 gap-3">
                            <div className="bg-slate-950 p-3 rounded border border-slate-800">
                                <span className="block text-[10px] text-slate-500 mb-1">Ollama Host</span>
                                <div className="text-xs text-slate-300 truncate font-mono">{config.ollama_host}</div>
                            </div>
                            <div className="bg-slate-950 p-3 rounded border border-slate-800">
                                <span className="block text-[10px] text-slate-500 mb-1">Orchestrator Model</span>
                                <div className="text-xs text-slate-300 truncate font-mono">{config.orchestrator_model}</div>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="p-4 bg-slate-950 border-t border-slate-800 flex justify-end">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm transition-colors"
                    >
                        Close
                    </button>
                </div>
            </div>
        </div>
    );
};
