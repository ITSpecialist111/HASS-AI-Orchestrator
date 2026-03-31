import React, { useState, useEffect } from 'react';
import { X, Shield, Terminal, Settings, Cpu, Key, Wand2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';

export const SettingsModal = ({ onClose, currentConfig, onUpdate }) => {
    const { t } = useTranslation();
    const [config, setConfig] = useState(currentConfig || { dry_run_mode: true });
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (currentConfig) setConfig(currentConfig);
    }, [currentConfig]);

    const updateConfigField = async (field, value) => {
        setLoading(true);
        try {
            const res = await fetch('api/config', {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ [field]: value })
            });
            if (res.ok) {
                const data = await res.json();
                setConfig(prev => ({ ...prev, ...data }));
                if (onUpdate) onUpdate({ ...config, ...data });
            }
        } catch (e) {
            console.error(`Failed to update ${field}`, e);
        } finally {
            setLoading(false);
        }
    };

    const handleToggleDryRun = () => updateConfigField('dry_run_mode', !config.dry_run_mode);
    const handleToggleGeminiDashboard = () => updateConfigField('use_gemini_for_dashboard', !config.use_gemini_for_dashboard);

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
            <div className="bg-slate-900 border border-slate-700 rounded-xl max-w-lg w-full shadow-2xl overflow-hidden">
                <div className="p-4 border-b border-slate-700 flex justify-between items-center bg-slate-800/50">
                    <h2 className="text-lg font-bold text-white flex items-center gap-2">
                        <Settings size={20} className="text-purple-400" />
                        {t('settings.title')}
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
                                <h3 className="font-semibold text-slate-200">{t('settings.dryRunMode')}</h3>
                            </div>
                            <div className="flex items-center gap-3">
                                <span className={`text-xs font-mono px-2 py-0.5 rounded ${config.dry_run_mode ? 'bg-amber-500/20 text-amber-300' : 'bg-green-500/20 text-green-300'}`}>
                                    {config.dry_run_mode ? t('settings.enabled') : t('settings.disabled')}
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
                            {t('settings.dryRunDescription')}
                        </p>
                        <div className="text-[10px] text-slate-500 italic border-t border-slate-700/50 pt-2">
                            {t('settings.dryRunNote')}
                        </div>
                    </div>

                    {/* Gemini Settings */}
                    <div className="bg-slate-800/30 rounded-lg p-4 border border-slate-700/50 space-y-4">
                        <div className="flex justify-between items-center">
                            <div className="flex items-center gap-2">
                                <Wand2 size={18} className={config.use_gemini_for_dashboard ? 'text-blue-400' : 'text-slate-400'} />
                                <h3 className="font-semibold text-slate-200">{t('settings.useGemini')}</h3>
                            </div>
                            <button
                                onClick={handleToggleGeminiDashboard}
                                disabled={loading}
                                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${config.use_gemini_for_dashboard ? 'bg-blue-600' : 'bg-slate-700'}`}
                            >
                                <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${config.use_gemini_for_dashboard ? 'translate-x-6' : 'translate-x-1'}`} />
                            </button>
                        </div>

                        <div className="space-y-3">
                            <div>
                                <label className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-1 block">{t('settings.geminiApiKey')}</label>
                                <div className="flex gap-2">
                                    <input
                                        type="password"
                                        defaultValue={config.gemini_api_key || ""}
                                        onBlur={(e) => updateConfigField('gemini_api_key', e.target.value)}
                                        className="bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-slate-300 w-full focus:outline-none focus:border-blue-500/50"
                                        placeholder={t('settings.geminiApiKeyPlaceholder')}
                                    />
                                </div>
                            </div>
                            <div>
                                <label className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-1 block">{t('settings.geminiModel')}</label>
                                <input
                                    type="text"
                                    defaultValue={config.gemini_model_name || "gemini-robotics-er-1.5-preview"}
                                    onBlur={(e) => updateConfigField('gemini_model_name', e.target.value)}
                                    className="bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-slate-300 w-full focus:outline-none focus:border-blue-500/50"
                                />
                                <p className="text-[10px] text-slate-500 mt-1">{t('settings.geminiModelHint')}</p>
                            </div>
                        </div>
                    </div>

                    {/* Metadata (Read Only) */}
                    <div className="space-y-2">
                        <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide">{t('settings.systemInfo')}</h4>
                        <div className="grid grid-cols-2 gap-3">
                            <div className="bg-slate-950 p-3 rounded border border-slate-800">
                                <span className="block text-[10px] text-slate-500 mb-1">{t('settings.ollamaHost')}</span>
                                <div className="text-xs text-slate-300 truncate font-mono">{config.ollama_host}</div>
                            </div>
                            <div className="bg-slate-950 p-3 rounded border border-slate-800">
                                <span className="block text-[10px] text-slate-500 mb-1">{t('settings.orchestratorModel')}</span>
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
                        {t('settings.close')}
                    </button>
                </div>
            </div>
        </div>
    );
};
