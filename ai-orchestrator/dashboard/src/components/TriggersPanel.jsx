import React, { useCallback, useEffect, useState } from 'react';
import {
    Activity,
    Clock3,
    Loader2,
    Play,
    Plus,
    Trash2,
    X,
    Zap,
} from 'lucide-react';

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
            const [triggerResponse, fireResponse] = await Promise.all([
                fetch('api/triggers'),
                fetch('api/triggers/fires?limit=50'),
            ]);
            if (!triggerResponse.ok) throw new Error(`Triggers: ${triggerResponse.status}`);
            if (!fireResponse.ok) throw new Error(`History: ${fireResponse.status}`);
            const triggerData = await triggerResponse.json();
            const fireData = await fireResponse.json();
            setTriggers(triggerData.triggers || triggerData || []);
            setFires(fireData.fires || fireData || []);
            setError(null);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        refresh();
        const timer = window.setInterval(refresh, 5000);
        return () => window.clearInterval(timer);
    }, [refresh]);

    const submit = async event => {
        event.preventDefault();
        setBusy('create');
        setError(null);
        try {
            const payload = { ...form };
            if (payload.type === 'cron') {
                delete payload.entity_id;
                delete payload.state_pattern;
                delete payload.sustained_seconds;
            } else {
                delete payload.cron;
            }
            const response = await fetch('api/triggers', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            if (!response.ok) throw new Error(`${response.status}: ${await response.text()}`);
            setForm(EMPTY_FORM);
            setCreating(false);
            await refresh();
        } catch (err) {
            setError(err.message);
        } finally {
            setBusy(null);
        }
    };

    const invoke = async (id, action) => {
        setBusy(`${action}-${id}`);
        setError(null);
        try {
            const response = await fetch(`api/triggers/${id}${action === 'fire' ? '/fire' : ''}`, {
                method: action === 'fire' ? 'POST' : 'DELETE',
            });
            if (!response.ok) throw new Error(`${response.status}: ${await response.text()}`);
            await refresh();
        } catch (err) {
            setError(err.message);
        } finally {
            setBusy(null);
        }
    };

    if (loading) return <div className="cp-empty-state"><Loader2 size={20} className="cp-spin" /> Loading proactive routines…</div>;

    return (
        <div className="cp-trigger-stack">
            <section className="cp-card">
                <div className="cp-section-heading">
                    <div><span className="cp-eyebrow"><Zap size={13} /> Proactive goals</span><h2>Configured triggers</h2></div>
                    <button className="cp-button cp-button--primary" type="button" onClick={() => setCreating(value => !value)}>
                        {creating ? <X size={15} /> : <Plus size={15} />} {creating ? 'Close form' : 'New trigger'}
                    </button>
                </div>
                <p className="cp-section-intro">Triggers wake the reasoning kernel. They do not bypass the selected action policy or approval gates.</p>
                {error && <div className="cp-alert is-danger" role="alert">{error}</div>}

                {creating && (
                    <form className="cp-trigger-form" onSubmit={submit}>
                        <Field label="Name"><input value={form.name} onChange={event => setForm({ ...form, name: event.target.value })} required /></Field>
                        <Field label="Trigger type">
                            <select value={form.type} onChange={event => setForm({ ...form, type: event.target.value })}>
                                <option value="cron">Schedule</option>
                                <option value="state">Entity state</option>
                            </select>
                        </Field>
                        {form.type === 'cron' ? (
                            <Field label="Schedule"><input value={form.cron} onChange={event => setForm({ ...form, cron: event.target.value })} placeholder="@daily or 0 9 * * 1-5" required /></Field>
                        ) : (
                            <>
                                <Field label="Entity ID"><input value={form.entity_id} onChange={event => setForm({ ...form, entity_id: event.target.value })} placeholder="binary_sensor.front_door" required /></Field>
                                <Field label="State pattern"><input value={form.state_pattern} onChange={event => setForm({ ...form, state_pattern: event.target.value })} placeholder="on, off, or ~^un" /></Field>
                                <Field label="Must remain for (seconds)"><input type="number" min="0" value={form.sustained_seconds} onChange={event => setForm({ ...form, sustained_seconds: Number(event.target.value) })} /></Field>
                            </>
                        )}
                        <Field label="Cooldown (seconds)"><input type="number" min="0" value={form.cooldown_seconds} onChange={event => setForm({ ...form, cooldown_seconds: Number(event.target.value) })} /></Field>
                        <Field label="Action policy">
                            <select value={form.mode} onChange={event => setForm({ ...form, mode: event.target.value })}>
                                <option value="auto">Auto-safe</option>
                                <option value="plan">Plan only</option>
                            </select>
                        </Field>
                        <Field label="Goal" wide><textarea rows={3} value={form.goal_template} onChange={event => setForm({ ...form, goal_template: event.target.value })} placeholder="Investigate {entity_id} ({reason}) and prepare the safest response." required /></Field>
                        <div className="cp-form-actions">
                            <button className="cp-button cp-button--secondary" type="button" onClick={() => { setCreating(false); setForm(EMPTY_FORM); }}>Cancel</button>
                            <button className="cp-button cp-button--primary" type="submit" disabled={busy === 'create'}>{busy === 'create' ? <Loader2 size={14} className="cp-spin" /> : <Plus size={14} />} Save trigger</button>
                        </div>
                    </form>
                )}

                {!triggers.length ? (
                    <div className="cp-empty-state cp-empty-state--compact"><Zap size={22} /><div><strong>No proactive triggers yet</strong><span>Create one for schedules or meaningful state changes.</span></div></div>
                ) : (
                    <div className="cp-trigger-list">
                        {triggers.map(trigger => (
                            <article className="cp-trigger-row" key={trigger.id}>
                                <span className={`cp-status-dot ${trigger.enabled ? 'is-success' : ''}`} />
                                <div><strong>{trigger.name}</strong><small>{trigger.type === 'cron' ? trigger.cron : `${trigger.entity_id} → ${trigger.state_pattern || 'any state'}`} · {trigger.mode || 'auto'} policy</small></div>
                                <span className="cp-pill">{trigger.type === 'cron' ? 'Schedule' : 'State'}</span>
                                <button className="cp-icon-button" type="button" onClick={() => invoke(trigger.id, 'fire')} disabled={!!busy} aria-label={`Run ${trigger.name} now`} title="Run now">
                                    {busy === `fire-${trigger.id}` ? <Loader2 size={15} className="cp-spin" /> : <Play size={15} />}
                                </button>
                                <button className="cp-icon-button is-danger" type="button" onClick={() => invoke(trigger.id, 'delete')} disabled={!!busy} aria-label={`Delete ${trigger.name}`} title="Delete trigger"><Trash2 size={15} /></button>
                            </article>
                        ))}
                    </div>
                )}
            </section>

            <section className="cp-card">
                <div className="cp-section-heading"><div><span className="cp-eyebrow"><Activity size={13} /> Audit trail</span><h2>Recent trigger runs</h2></div></div>
                {!fires.length ? <div className="cp-empty-state cp-empty-state--compact">No trigger runs recorded yet.</div> : (
                    <div className="cp-list">
                        {fires.map(fire => (
                            <div className="cp-list-row" key={fire.id}>
                                <span className="cp-list-icon"><Clock3 size={15} /></span>
                                <span className="cp-list-main"><strong>{fire.trigger_id}</strong><small>{new Date(fire.timestamp).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}</small></span>
                                <span className={`cp-pill ${fire.status === 'executed' ? 'is-success' : fire.status === 'error' ? 'is-danger' : fire.status === 'awaiting_approval' ? 'is-warning' : ''}`}>{String(fire.status || 'unknown').replaceAll('_', ' ')}</span>
                            </div>
                        ))}
                    </div>
                )}
            </section>
        </div>
    );
}

function Field({ label, wide = false, children }) {
    return <label className={`cp-field ${wide ? 'is-wide' : ''}`}><span>{label}</span>{children}</label>;
}
