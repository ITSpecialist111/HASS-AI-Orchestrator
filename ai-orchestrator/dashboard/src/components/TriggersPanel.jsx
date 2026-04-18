import React, { useEffect, useState, useCallback } from 'react';
import { Zap, Plus, Trash2, Play, Clock, Activity, Loader2 } from 'lucide-react';

const EMPTY_FORM = {
    name: '',
    type: 'cron',
    goal_template: '',
    enabled: true,
    cron: '@daily',
    entity_id: '',
    state_pattern: '',
    sustained_seconds: 0,
    cooldown_seconds: 600,
    mode: 'auto',
};

/**
 * TriggersPanel — list, create, fire and inspect proactive triggers
 * (Phase 8 / Milestone F).
 */
export function TriggersPanel() {
    const [triggers, setTriggers] = useState([]);
    const [fires, setFires] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [creating, setCreating] = useState(false);
    const [form, setForm] = useState(EMPTY_FORM);
    const [busy, setBusy] = useState(null);

    const refresh = useCallback(async () => {
        try {
            const [tRes, fRes] = await Promise.all([
                fetch('api/triggers'),
                fetch('api/triggers/fires?limit=50'),
            ]);
            if (!tRes.ok) throw new Error(`triggers ${tRes.status}`);
            if (!fRes.ok) throw new Error(`fires ${fRes.status}`);
            const tData = await tRes.json();
            const fData = await fRes.json();
            setTriggers(tData.triggers || tData || []);
            setFires(fData.fires || fData || []);
            setLoading(false);
        } catch (e) {
            setError(e.message);
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        refresh();
        const id = setInterval(refresh, 5000);
        return () => clearInterval(id);
    }, [refresh]);

    const submit = async () => {
        setBusy('create');
        try {
            const payload = { ...form };
            if (payload.type === 'cron') {
                delete payload.entity_id;
                delete payload.state_pattern;
                delete payload.sustained_seconds;
            } else {
                delete payload.cron;
            }
            const res = await fetch('api/triggers', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            if (!res.ok) {
                const body = await res.text();
                throw new Error(`${res.status}: ${body}`);
            }
            setForm(EMPTY_FORM);
            setCreating(false);
            await refresh();
        } catch (e) {
            setError(e.message);
        } finally {
            setBusy(null);
        }
    };

    const remove = async (id) => {
        setBusy(`del-${id}`);
        try {
            await fetch(`api/triggers/${id}`, { method: 'DELETE' });
            await refresh();
        } finally {
            setBusy(null);
        }
    };

    const fire = async (id) => {
        setBusy(`fire-${id}`);
        try {
            await fetch(`api/triggers/${id}/fire`, { method: 'POST' });
            await refresh();
        } finally {
            setBusy(null);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center gap-2 text-slate-500">
                <Loader2 size={16} className="animate-spin" /> Loading triggers…
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
                        <Zap size={20} className="text-amber-400" /> Triggers
                    </h2>
                    <p className="text-slate-500 text-sm">
                        Proactive cron and state-change triggers that wake the deep reasoner.
                    </p>
                </div>
                <button
                    onClick={() => setCreating(c => !c)}
                    className="flex items-center gap-2 px-3 py-1.5 rounded text-xs font-semibold bg-purple-600 hover:bg-purple-500 text-white"
                >
                    <Plus size={12} />
                    New trigger
                </button>
            </div>

            {error && (
                <div className="bg-red-500/5 border border-red-500/20 rounded-xl px-4 py-3 text-sm text-red-400">
                    {error}
                </div>
            )}

            {creating && (
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                        <Field label="Name">
                            <input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })}
                                className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-sm text-slate-200" />
                        </Field>
                        <Field label="Type">
                            <select value={form.type} onChange={e => setForm({ ...form, type: e.target.value })}
                                className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-sm text-slate-200">
                                <option value="cron">cron</option>
                                <option value="state">state</option>
                            </select>
                        </Field>
                        {form.type === 'cron' ? (
                            <Field label="Cron expression">
                                <input value={form.cron} onChange={e => setForm({ ...form, cron: e.target.value })}
                                    placeholder="@daily, @nightly, 0 9 * * 1-5"
                                    className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-sm text-slate-200 font-mono" />
                            </Field>
                        ) : (
                            <>
                                <Field label="Entity ID">
                                    <input value={form.entity_id} onChange={e => setForm({ ...form, entity_id: e.target.value })}
                                        placeholder="binary_sensor.front_door"
                                        className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-sm text-slate-200 font-mono" />
                                </Field>
                                <Field label="State pattern">
                                    <input value={form.state_pattern} onChange={e => setForm({ ...form, state_pattern: e.target.value })}
                                        placeholder="on, off, ~^un (regex)"
                                        className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-sm text-slate-200 font-mono" />
                                </Field>
                                <Field label="Sustained seconds">
                                    <input type="number" value={form.sustained_seconds}
                                        onChange={e => setForm({ ...form, sustained_seconds: Number(e.target.value) })}
                                        className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-sm text-slate-200" />
                                </Field>
                            </>
                        )}
                        <Field label="Cooldown seconds">
                            <input type="number" value={form.cooldown_seconds}
                                onChange={e => setForm({ ...form, cooldown_seconds: Number(e.target.value) })}
                                className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-sm text-slate-200" />
                        </Field>
                    </div>
                    <Field label="Goal template">
                        <textarea rows={2} value={form.goal_template}
                            onChange={e => setForm({ ...form, goal_template: e.target.value })}
                            placeholder="Investigate {entity_id} ({reason})"
                            className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-sm text-slate-200 font-mono" />
                    </Field>
                    <div className="flex items-center justify-end gap-2">
                        <button onClick={() => { setCreating(false); setForm(EMPTY_FORM); }}
                            className="px-3 py-1.5 rounded text-xs text-slate-400 hover:text-slate-200">
                            Cancel
                        </button>
                        <button onClick={submit} disabled={busy === 'create'}
                            className="px-3 py-1.5 rounded text-xs font-semibold bg-purple-600 hover:bg-purple-500 text-white disabled:bg-slate-800 disabled:text-slate-600">
                            {busy === 'create' ? 'Saving…' : 'Save'}
                        </button>
                    </div>
                </div>
            )}

            <div className="space-y-2">
                {triggers.length === 0 && (
                    <div className="text-slate-500 text-sm">No triggers configured yet.</div>
                )}
                {triggers.map(t => (
                    <div key={t.id} className="bg-slate-900 border border-slate-800 rounded-xl p-3 flex items-center gap-3">
                        <div className={`w-2 h-2 rounded-full ${t.enabled ? 'bg-green-400' : 'bg-slate-600'}`} />
                        <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                                <span className="font-mono text-sm text-slate-200 truncate">{t.name}</span>
                                <span className="px-1.5 py-0.5 rounded text-[10px] uppercase font-bold bg-slate-800 text-slate-400">
                                    {t.type}
                                </span>
                            </div>
                            <div className="text-xs text-slate-500 font-mono truncate">
                                {t.type === 'cron' ? t.cron : `${t.entity_id} = ${t.state_pattern || '*'}`}
                                {t.sustained_seconds ? ` · sustain ${t.sustained_seconds}s` : ''}
                                {` · cooldown ${t.cooldown_seconds}s`}
                            </div>
                        </div>
                        <button onClick={() => fire(t.id)} disabled={busy === `fire-${t.id}`}
                            className="p-1.5 rounded text-slate-400 hover:text-amber-400 hover:bg-slate-800"
                            title="Fire now">
                            {busy === `fire-${t.id}` ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
                        </button>
                        <button onClick={() => remove(t.id)} disabled={busy === `del-${t.id}`}
                            className="p-1.5 rounded text-slate-400 hover:text-red-400 hover:bg-slate-800"
                            title="Delete">
                            <Trash2 size={14} />
                        </button>
                    </div>
                ))}
            </div>

            <div>
                <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2 mb-2">
                    <Activity size={14} className="text-blue-400" /> Recent fires
                </h3>
                <div className="space-y-1">
                    {fires.length === 0 && (
                        <div className="text-slate-500 text-xs">No fires yet.</div>
                    )}
                    {fires.map(f => (
                        <div key={f.id} className="bg-slate-900 border border-slate-800 rounded px-3 py-2 text-xs flex items-center gap-3">
                            <Clock size={12} className="text-slate-500 shrink-0" />
                            <span className="font-mono text-slate-500 shrink-0">
                                {new Date(f.timestamp).toLocaleTimeString()}
                            </span>
                            <span className="font-mono text-slate-300 truncate">{f.trigger_id}</span>
                            <span className={`px-1.5 py-0.5 rounded text-[10px] uppercase font-bold ml-auto shrink-0
                                ${f.status === 'executed' ? 'bg-green-500/10 text-green-400 border border-green-500/20'
                                : f.status === 'awaiting_approval' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                                : f.status === 'error' ? 'bg-red-500/10 text-red-400 border border-red-500/20'
                                : 'bg-slate-800 text-slate-400'}`}>
                                {f.status}
                            </span>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}

function Field({ label, children }) {
    return (
        <label className="block">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1">{label}</span>
            {children}
        </label>
    );
}
