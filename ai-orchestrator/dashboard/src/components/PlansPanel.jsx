import React, { useMemo, useState } from 'react';
import {
    CheckCircle2,
    ChevronDown,
    ChevronRight,
    Clock3,
    Loader2,
    RotateCcw,
    ShieldCheck,
    XCircle,
} from 'lucide-react';

const formatDate = (value) => {
    if (!value) return 'Unknown time';
    const date = new Date(value);
    return Number.isNaN(date.getTime())
        ? value
        : date.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });
};

const statusTone = (status) => {
    if (status === 'pending' || status === 'approved' || status === 'executing') return 'is-warning';
    if (status === 'executed') return 'is-success';
    if (status === 'rejected' || status === 'executed_with_errors') return 'is-danger';
    return '';
};

export function PlansPanel({ plans = [], loading, error, onRefresh, onPlanUpdated }) {
    const [filter, setFilter] = useState('pending');
    const [expanded, setExpanded] = useState(null);
    const [busy, setBusy] = useState(null);
    const [actionError, setActionError] = useState(null);

    const visiblePlans = useMemo(() => {
        if (filter === 'all') return plans;
        if (filter === 'history') return plans.filter(plan => !['pending', 'approved', 'executing'].includes(plan.status));
        return plans.filter(plan => ['pending', 'approved', 'executing'].includes(plan.status));
    }, [filter, plans]);

    const act = async (plan, action) => {
        setBusy(`${plan.id}:${action}`);
        setActionError(null);
        try {
            const response = await fetch(`api/reasoning/plans/${plan.id}/${action}`, { method: 'POST' });
            if (!response.ok) throw new Error(`${response.status}: ${await response.text()}`);
            await response.json();
            await onPlanUpdated?.();
        } catch (err) {
            setActionError(err.message);
        } finally {
            setBusy(null);
        }
    };

    return (
        <div className="cp-page">
            <header className="cp-page-header">
                <div>
                    <div className="cp-eyebrow"><ShieldCheck size={14} /> Human authority</div>
                    <h1>Plans and approvals</h1>
                    <p>Review the exact recorded intent. Approval replays this plan; it never asks the model to improvise a second time.</p>
                </div>
                <button className="cp-button cp-button--secondary" type="button" onClick={onRefresh} disabled={loading}>
                    <RotateCcw size={15} className={loading ? 'cp-spin' : ''} /> Refresh
                </button>
            </header>

            <div className="cp-segmented" role="tablist" aria-label="Plan filters">
                {[
                    ['pending', 'Needs review'],
                    ['history', 'History'],
                    ['all', 'All plans'],
                ].map(([value, label]) => (
                    <button
                        key={value}
                        id={`plan-filter-${value}`}
                        type="button"
                        role="tab"
                        aria-selected={filter === value}
                        aria-controls="plan-filter-panel"
                        className={filter === value ? 'is-active' : ''}
                        onClick={() => setFilter(value)}
                    >
                        {label}
                    </button>
                ))}
            </div>

            {(error || actionError) && <div className="cp-alert is-danger" role="alert"><XCircle size={16} /> {actionError || error}</div>}

            <section id="plan-filter-panel" className="cp-plan-list" role="tabpanel" aria-labelledby={`plan-filter-${filter}`} aria-live="polite">
                {loading && plans.length === 0 ? (
                    <div className="cp-empty-state"><Loader2 className="cp-spin" size={24} /><div><strong>Loading plans</strong><span>Reading the durable review queue.</span></div></div>
                ) : visiblePlans.length === 0 ? (
                    <div className="cp-empty-state"><CheckCircle2 size={26} /><div><strong>No plans in this view</strong><span>New high-impact proposals pause here automatically.</span></div></div>
                ) : visiblePlans.map(plan => {
                    const isExpanded = expanded === plan.id;
                    const pending = plan.status === 'pending';
                    return (
                        <article className="cp-plan-card" key={plan.id}>
                            <button
                                type="button"
                                className="cp-plan-summary"
                                onClick={() => setExpanded(isExpanded ? null : plan.id)}
                                aria-expanded={isExpanded}
                            >
                                <span className={`cp-plan-risk ${statusTone(plan.status)}`}><ShieldCheck size={19} /></span>
                                <span className="cp-plan-copy">
                                    <strong>{plan.goal || 'Untitled plan'}</strong>
                                    <small>{plan.risk_summary || `${plan.mutating_count || 0} deterministic steps`} · {formatDate(plan.timestamp)}</small>
                                </span>
                                <span className={`cp-pill ${statusTone(plan.status)}`}>{String(plan.status || 'unknown').replaceAll('_', ' ')}</span>
                                {isExpanded ? <ChevronDown size={17} /> : <ChevronRight size={17} />}
                            </button>

                            {isExpanded && (
                                <div className="cp-plan-details">
                                    <div className="cp-plan-facts">
                                        <span><strong>{plan.mutating_count || plan.intents?.length || 0}</strong> recorded changes</span>
                                        <span><strong>{plan.high_impact_count || 0}</strong> high-impact</span>
                                        <span><strong>{plan.iterations || 0}</strong> reasoning steps</span>
                                        <span><Clock3 size={13} /> {plan.duration_ms ? `${(plan.duration_ms / 1000).toFixed(1)}s` : '—'}</span>
                                    </div>

                                    {plan.answer && <div className="cp-plan-explanation"><span>Why this plan</span><p>{plan.answer}</p></div>}

                                    <ol className="cp-intent-list">
                                        {(plan.intents || []).map((intent, index) => (
                                            <li key={intent.idempotency_key || `${plan.id}-${index}`}>
                                                <span className="cp-intent-number">{index + 1}</span>
                                                <div>
                                                    <strong>{String(intent.tool_name || 'action').replaceAll('_', ' ')}</strong>
                                                    <small>{intent.classification_reason || `${intent.impact_level || 'unknown'} impact`}</small>
                                                    <details>
                                                        <summary>Technical parameters</summary>
                                                        <pre>{JSON.stringify(intent.arguments || {}, null, 2)}</pre>
                                                    </details>
                                                </div>
                                                <span className={`cp-pill ${intent.impact_level === 'high' ? 'is-danger' : intent.impact_level === 'medium' ? 'is-warning' : ''}`}>
                                                    {intent.impact_level || 'unknown'}
                                                </span>
                                            </li>
                                        ))}
                                    </ol>

                                    {pending && (
                                        <div className="cp-plan-actions">
                                            <button className="cp-button cp-button--primary" type="button" onClick={() => act(plan, 'execute')} disabled={!!busy}>
                                                {busy === `${plan.id}:execute` ? <Loader2 size={15} className="cp-spin" /> : <ShieldCheck size={15} />}
                                                Approve exact plan
                                            </button>
                                            <button className="cp-button cp-button--danger" type="button" onClick={() => act(plan, 'reject')} disabled={!!busy}>
                                                <XCircle size={15} /> Reject
                                            </button>
                                        </div>
                                    )}
                                </div>
                            )}
                        </article>
                    );
                })}
            </section>
        </div>
    );
}
