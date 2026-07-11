import React, { useState } from 'react';
import {
    Brain,
    CheckCircle2,
    ChevronDown,
    ChevronRight,
    Clock3,
    Database,
    Loader2,
    ShieldCheck,
    Wrench,
    XCircle,
} from 'lucide-react';

const eventMeta = event => {
    if (event.type === 'start') return { icon: Clock3, label: 'Run started' };
    if (event.type === 'recall') return { icon: Database, label: 'Relevant experience' };
    if (event.type === 'tool') return { icon: Wrench, label: String(event.name || 'Guarded tool').replaceAll('_', ' ') };
    if (event.type === 'plan') return { icon: ShieldCheck, label: 'Exact plan recorded' };
    if (event.type === 'cancelled') return { icon: XCircle, label: 'Run cancelled' };
    return { icon: Brain, label: event.iteration ? `Reasoning step ${event.iteration}` : 'Model update' };
};

export function ReasoningTrace({ reasoningEvents = [], running = false }) {
    const [expanded, setExpanded] = useState({});

    if (!reasoningEvents.length) return null;

    return (
        <div className="cp-timeline" aria-label="Run activity">
            {reasoningEvents.map((event, index) => {
                const meta = eventMeta(event);
                const Icon = meta.icon;
                const isOpen = !!expanded[event.id || index];
                const hasTechnicalDetails = event.type === 'tool'
                    || (event.tool_calls?.length || 0) > 0
                    || (event.tool_results?.length || 0) > 0;
                const failed = event.status === 'error' || event.result?.ok === false;
                return (
                    <article className={`cp-timeline-item ${failed ? 'is-danger' : ''}`} key={event.id || index}>
                        <span className="cp-timeline-line" aria-hidden="true" />
                        <span className="cp-timeline-icon"><Icon size={15} /></span>
                        <div className="cp-timeline-content">
                            <div className="cp-timeline-title">
                                <strong>{meta.label}</strong>
                                {event.duration_ms != null && <small>{event.duration_ms >= 1000 ? `${(event.duration_ms / 1000).toFixed(1)}s` : `${event.duration_ms}ms`}</small>}
                                {failed ? <span className="cp-pill is-danger">Failed safely</span> : <CheckCircle2 size={14} className="cp-success-icon" />}
                            </div>
                            {event.content && <p>{event.content}</p>}
                            {hasTechnicalDetails && (
                                <button
                                    className="cp-detail-toggle"
                                    type="button"
                                    onClick={() => setExpanded(previous => ({ ...previous, [event.id || index]: !isOpen }))}
                                    aria-expanded={isOpen}
                                >
                                    {isOpen ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
                                    {isOpen ? 'Hide technical detail' : 'Show technical detail'}
                                </button>
                            )}
                            {isOpen && (
                                <div className="cp-technical-detail">
                                    {event.type === 'tool' && (
                                        <>
                                            <div><span>Parameters</span><pre>{JSON.stringify(event.arguments || {}, null, 2)}</pre></div>
                                            <div><span>Guarded result</span><pre>{JSON.stringify(event.result || {}, null, 2)}</pre></div>
                                        </>
                                    )}
                                    {(event.tool_calls || []).map((call, callIndex) => (
                                        <div key={`call-${callIndex}`}><span>{call.name || call.tool || 'Tool call'}</span><pre>{JSON.stringify(call.arguments || call.args || {}, null, 2)}</pre></div>
                                    ))}
                                    {(event.tool_results || []).map((toolResult, resultIndex) => (
                                        <div key={`result-${resultIndex}`}><span>Result {resultIndex + 1}</span><pre>{JSON.stringify(toolResult, null, 2)}</pre></div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </article>
                );
            })}
            {running && (
                <article className="cp-timeline-item is-running">
                    <span className="cp-timeline-icon"><Loader2 size={15} className="cp-spin" /></span>
                    <div className="cp-timeline-content"><div className="cp-timeline-title"><strong>Working on the next grounded step</strong></div></div>
                </article>
            )}
        </div>
    );
}
