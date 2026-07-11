import React, { useEffect, useRef, useState } from 'react';
import { Cpu, Key, Loader2, Settings, ShieldCheck, Wand2, X } from 'lucide-react';
import { useDialogFocus } from './useDialogFocus';

const DEFAULT_GEMINI_DASHBOARD_MODEL = 'gemini-3.5-flash';

export const SettingsModal = ({ onClose, currentConfig, onUpdate }) => {
    const [config, setConfig] = useState(currentConfig || { dry_run_mode: true });
    const [loading, setLoading] = useState(null);
    const [error, setError] = useState(null);
    const closeRef = useRef(null);
    const dialogRef = useDialogFocus(onClose, closeRef);

    useEffect(() => {
        if (currentConfig) setConfig(currentConfig);
    }, [currentConfig]);

    const updateConfigField = async (field, value) => {
        setLoading(field);
        setError(null);
        try {
            const response = await fetch('api/config', {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ [field]: value }),
            });
            if (!response.ok) throw new Error(`${response.status}: ${await response.text()}`);
            const data = await response.json();
            const next = { ...config, ...data, [field]: data[field] ?? value };
            setConfig(next);
            onUpdate?.(next);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(null);
        }
    };

    return (
        <div className="cp-modal-backdrop" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) onClose(); }}>
            <section ref={dialogRef} className="cp-modal" role="dialog" aria-modal="true" aria-labelledby="settings-title" tabIndex={-1}>
                <header className="cp-modal-header">
                    <span className="cp-icon-tile"><Settings size={18} /></span>
                    <div><h2 id="settings-title">Runtime settings</h2><p>Immediate controls for this session. Persistent defaults remain in the add-on configuration.</p></div>
                    <button ref={closeRef} className="cp-icon-button" type="button" onClick={onClose} aria-label="Close settings"><X size={19} /></button>
                </header>

                <div className="cp-modal-body">
                    {error && <div className="cp-alert is-danger" role="alert">{error}</div>}
                    <article className="cp-setting-card">
                        <span className={`cp-setting-icon ${config.dry_run_mode ? 'is-warning' : 'is-success'}`}><ShieldCheck size={19} /></span>
                        <div><strong>Global simulation mode</strong><p>When on, Home Assistant mutations are simulated. Per-run plan approval remains active regardless of this setting.</p></div>
                        <button
                            className={`cp-switch ${config.dry_run_mode ? 'is-on' : ''}`}
                            type="button"
                            role="switch"
                            aria-checked={!!config.dry_run_mode}
                            onClick={() => updateConfigField('dry_run_mode', !config.dry_run_mode)}
                            disabled={!!loading}
                        >
                            <span />
                            <em>{config.dry_run_mode ? 'Simulation on' : 'Live tools'}</em>
                        </button>
                    </article>

                    <article className="cp-setting-card">
                        <span className="cp-setting-icon"><Wand2 size={19} /></span>
                        <div><strong>Gemini dashboard generation</strong><p>Optional provider for visual dashboard generation only. It does not replace the deterministic home action kernel.</p></div>
                        <button
                            className={`cp-switch ${config.use_gemini_for_dashboard ? 'is-on' : ''}`}
                            type="button"
                            role="switch"
                            aria-checked={!!config.use_gemini_for_dashboard}
                            onClick={() => updateConfigField('use_gemini_for_dashboard', !config.use_gemini_for_dashboard)}
                            disabled={!!loading}
                        >
                            <span />
                            <em>{config.use_gemini_for_dashboard ? 'Enabled' : 'Disabled'}</em>
                        </button>
                    </article>

                    <div className="cp-settings-grid">
                        <label className="cp-field">
                            <span><Key size={13} /> Gemini API key</span>
                            <input type="password" defaultValue="" onBlur={event => { if (event.target.value) updateConfigField('gemini_api_key', event.target.value); }} placeholder="Leave blank to keep current key" />
                        </label>
                        <label className="cp-field">
                            <span><Wand2 size={13} /> Dashboard model</span>
                            <input defaultValue={config.gemini_model_name || DEFAULT_GEMINI_DASHBOARD_MODEL} onBlur={event => updateConfigField('gemini_model_name', event.target.value)} />
                        </label>
                    </div>

                    <section className="cp-runtime-facts" aria-label="Runtime information">
                        <h3>Runtime information</h3>
                        <dl>
                            <div><dt><Cpu size={14} /> Reasoning model</dt><dd>{config.deep_reasoning_model || config.orchestrator_model || 'gemma4:e4b'}</dd></div>
                            <div><dt>Default profile</dt><dd>{config.reasoning_default_profile || 'balanced'}</dd></div>
                            <div><dt>Ollama host</dt><dd>{config.ollama_host || 'http://localhost:11434'}</dd></div>
                            <div><dt>Release</dt><dd>{config.version || 'unknown'}</dd></div>
                        </dl>
                    </section>
                </div>

                <footer className="cp-modal-footer">
                    {loading && <span><Loader2 size={14} className="cp-spin" /> Saving runtime change…</span>}
                    <button className="cp-button cp-button--primary" type="button" onClick={onClose}>Done</button>
                </footer>
            </section>
        </div>
    );
};
