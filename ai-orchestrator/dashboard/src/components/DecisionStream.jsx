import React, { useMemo, useState } from 'react';
import {
    Activity,
    ChevronDown,
    ChevronRight,
    Clock3,
    Filter,
    ShieldCheck,
    Wrench,
} from 'lucide-react';

const hasAction = decision => (
    (decision?.decision?.actions?.length || 0) > 0
    || (decision?.action && !['No Action', 'None'].includes(decision.action))
);

const actionNames = decision => {
    const tools = decision?.decision?.actions?.map(action => action.tool).filter(Boolean) || [];
    if (tools.length) return tools.map(tool => tool.replaceAll('_', ' ')).join(', ');
    if (hasAction(decision)) return String(decision.action).replaceAll('_', ' ');
    return 'Observed — no change needed';
};

export function DecisionStream({ decisions = [] }) {
    const [showObservations, setShowObservations] = useState(false);
    const [expanded, setExpanded] = useState(null);
    const visible = useMemo(
        () => showObservations ? decisions : decisions.filter(hasAction),
        [decisions, showObservations],
    );

    return (
        <section className="cp-card">
            <div className="cp-section-heading">
                <div><span className="cp-eyebrow"><Activity size={13} /> Live record</span><h2>System activity</h2></div>
                <button className={`cp-filter-button ${showObservations ? 'is-active' : ''}`} type="button" onClick={() => setShowObservations(value => !value)}>
                    <Filter size={14} /> {showObservations ? 'All observations' : 'Changes only'}
                </button>
            </div>

            {visible.length === 0 ? (
                <div className="cp-empty-state"><Activity size={25} /><div><strong>No activity in this view</strong><span>{showObservations ? 'Waiting for the next agent event.' : 'Show all observations to include no-change checks.'}</span></div></div>
            ) : (
                <div className="cp-activity-feed">
                    {visible.map((decision, index) => {
                        const key = `${decision.timestamp || 'event'}-${index}`;
                        const open = expanded === key;
                        const changed = hasAction(decision);
                        return (
                            <article className="cp-activity-item" key={key}>
                                <button className="cp-activity-summary" type="button" onClick={() => setExpanded(open ? null : key)} aria-expanded={open}>
                                    <span className={`cp-activity-icon ${changed ? 'is-active' : ''}`}>{changed ? <Wrench size={16} /> : <ShieldCheck size={16} />}</span>
                                    <span className="cp-activity-copy">
                                        <strong>{actionNames(decision)}</strong>
                                        <small>{decision.reasoning || (changed ? 'Guarded action completed' : 'No action was necessary')}</small>
                                    </span>
                                    <span className="cp-activity-meta"><strong>{decision.agent_id || 'Orchestrator'}</strong><small><Clock3 size={12} /> {decision.timestamp ? new Date(decision.timestamp).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' }) : 'Unknown time'}</small></span>
                                    {decision.dry_run && <span className="cp-pill is-warning">Simulation</span>}
                                    {open ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                                </button>
                                {open && (
                                    <div className="cp-activity-detail">
                                        <span>Technical event payload</span>
                                        <pre>{JSON.stringify(decision, null, 2)}</pre>
                                    </div>
                                )}
                            </article>
                        );
                    })}
                </div>
            )}
        </section>
    );
}
