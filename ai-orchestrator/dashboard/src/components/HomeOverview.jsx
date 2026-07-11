import React, { useMemo, useState } from 'react';
import {
    ArrowRight,
    Bot,
    CheckCircle2,
    CircleAlert,
    Clock3,
    House,
    ShieldCheck,
    Sparkles,
    Wifi,
    WifiOff,
} from 'lucide-react';

const formatTime = (value) => {
    if (!value) return 'Not yet';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return 'Unknown';
    const elapsed = Date.now() - date.getTime();
    if (elapsed < 60_000) return 'Just now';
    if (elapsed < 3_600_000) return `${Math.max(1, Math.floor(elapsed / 60_000))}m ago`;
    if (elapsed < 86_400_000) return `${Math.floor(elapsed / 3_600_000)}h ago`;
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
};

const activitySummary = (decision) => {
    const tools = decision?.decision?.actions?.map(action => action.tool).filter(Boolean) || [];
    if (tools.length) return tools.join(', ');
    if (decision?.action && !['No Action', 'None'].includes(decision.action)) return decision.action;
    return decision?.reasoning || 'Home state observed — no action required';
};

export function HomeOverview({
    agents = [],
    decisions = [],
    pendingPlans = [],
    connected,
    reasoningInfo,
    onStartGoal,
    onNavigate,
}) {
    const [goal, setGoal] = useState('');
    const activeAgents = useMemo(
        () => agents.filter(agent => agent.status !== 'error').length,
        [agents],
    );
    const recentDecisions = decisions.slice(0, 5);

    const submitGoal = (event) => {
        event.preventDefault();
        if (!goal.trim()) return;
        onStartGoal(goal.trim());
    };

    return (
        <div className="cp-page">
            <header className="cp-page-header">
                <div>
                    <div className="cp-eyebrow"><House size={14} /> Home operations</div>
                    <h1>{connected ? 'Good to see you. Your home is connected.' : 'The control layer needs your attention.'}</h1>
                    <p>Ask for an outcome, review the exact plan, and let guarded tools handle the mechanics.</p>
                </div>
                <div className={`cp-health-chip ${connected ? 'is-success' : 'is-danger'}`}>
                    {connected ? <Wifi size={16} /> : <WifiOff size={16} />}
                    <span>{connected ? 'Live connection' : 'Connection unavailable'}</span>
                </div>
            </header>

            <section className="cp-command-card" aria-labelledby="home-command-title">
                <div className="cp-command-copy">
                    <span className="cp-icon-tile"><Sparkles size={20} /></span>
                    <div>
                        <h2 id="home-command-title">What should the home accomplish?</h2>
                        <p>Use natural language. The orchestrator observes first and keeps every physical action inside deterministic policy.</p>
                    </div>
                </div>
                <form onSubmit={submitGoal} className="cp-command-form">
                    <label className="cp-sr-only" htmlFor="home-goal">Goal for the orchestrator</label>
                    <textarea
                        id="home-goal"
                        value={goal}
                        onChange={event => setGoal(event.target.value)}
                        rows={2}
                        placeholder="For example: make the downstairs comfortable for movie night, but do not unlock anything."
                    />
                    <button className="cp-button cp-button--primary" disabled={!goal.trim()} type="submit">
                        Plan this goal <ArrowRight size={16} />
                    </button>
                </form>
                <div className="cp-suggestion-row" aria-label="Suggested goals">
                    {[
                        'Check the whole-home status',
                        'Prepare a safe night routine',
                        'Find avoidable energy use',
                    ].map(suggestion => (
                        <button key={suggestion} type="button" onClick={() => setGoal(suggestion)}>
                            {suggestion}
                        </button>
                    ))}
                </div>
            </section>

            <section className="cp-metric-grid" aria-label="Operational summary">
                <article className="cp-metric-card">
                    <span className={`cp-metric-icon ${connected ? 'is-success' : 'is-danger'}`}>
                        {connected ? <CheckCircle2 size={18} /> : <CircleAlert size={18} />}
                    </span>
                    <div><strong>{connected ? 'Online' : 'Offline'}</strong><span>Home Assistant link</span></div>
                </article>
                <article className="cp-metric-card">
                    <span className="cp-metric-icon"><Bot size={18} /></span>
                    <div><strong>{activeAgents} / {agents.length}</strong><span>Agents available</span></div>
                </article>
                <button className="cp-metric-card cp-metric-card--action" onClick={() => onNavigate('review')} type="button">
                    <span className={`cp-metric-icon ${pendingPlans.length ? 'is-warning' : 'is-success'}`}>
                        <ShieldCheck size={18} />
                    </span>
                    <div><strong>{pendingPlans.length}</strong><span>Plans awaiting review</span></div>
                    <ArrowRight size={16} />
                </button>
                <article className="cp-metric-card">
                    <span className="cp-metric-icon"><Sparkles size={18} /></span>
                    <div>
                        <strong>{reasoningInfo?.default_profile || 'balanced'}</strong>
                        <span>{reasoningInfo?.model || 'Reasoning model loading'}</span>
                    </div>
                </article>
            </section>

            <div className="cp-two-column">
                <section className="cp-card" aria-labelledby="review-heading">
                    <div className="cp-section-heading">
                        <div><span className="cp-eyebrow">Human authority</span><h2 id="review-heading">Needs your review</h2></div>
                        <button className="cp-text-button" onClick={() => onNavigate('review')} type="button">View all <ArrowRight size={14} /></button>
                    </div>
                    {pendingPlans.length === 0 ? (
                        <div className="cp-empty-state cp-empty-state--compact">
                            <CheckCircle2 size={22} />
                            <div><strong>Nothing is waiting</strong><span>Risky actions will pause here before execution.</span></div>
                        </div>
                    ) : (
                        <div className="cp-list">
                            {pendingPlans.slice(0, 3).map(plan => (
                                <button key={plan.id} className="cp-list-row cp-list-row--button" onClick={() => onNavigate('review')} type="button">
                                    <span className="cp-list-icon is-warning"><ShieldCheck size={16} /></span>
                                    <span className="cp-list-main"><strong>{plan.goal}</strong><small>{plan.risk_summary || `${plan.mutating_count || 0} proposed changes`}</small></span>
                                    <span className="cp-pill is-warning">Review</span>
                                </button>
                            ))}
                        </div>
                    )}
                </section>

                <section className="cp-card" aria-labelledby="activity-heading">
                    <div className="cp-section-heading">
                        <div><span className="cp-eyebrow">Recent activity</span><h2 id="activity-heading">What the system has done</h2></div>
                        <button className="cp-text-button" onClick={() => onNavigate('insights')} type="button">Inspect <ArrowRight size={14} /></button>
                    </div>
                    {recentDecisions.length === 0 ? (
                        <div className="cp-empty-state cp-empty-state--compact">
                            <Clock3 size={22} />
                            <div><strong>No recent activity</strong><span>New observations and outcomes will appear here.</span></div>
                        </div>
                    ) : (
                        <div className="cp-list">
                            {recentDecisions.map((decision, index) => (
                                <div className="cp-list-row" key={`${decision.timestamp || 'event'}-${index}`}>
                                    <span className="cp-list-icon"><Clock3 size={16} /></span>
                                    <span className="cp-list-main"><strong>{activitySummary(decision)}</strong><small>{decision.agent_id || 'Orchestrator'} · {formatTime(decision.timestamp)}</small></span>
                                </div>
                            ))}
                        </div>
                    )}
                </section>
            </div>

            <section className="cp-card" aria-labelledby="agents-heading">
                <div className="cp-section-heading">
                    <div><span className="cp-eyebrow">Coverage</span><h2 id="agents-heading">Specialist agents</h2></div>
                    <button className="cp-text-button" onClick={() => onNavigate('automation')} type="button">Manage agents <ArrowRight size={14} /></button>
                </div>
                <div className="cp-agent-strip">
                    {agents.length === 0 ? (
                        <div className="cp-empty-state cp-empty-state--compact"><Bot size={22} /><div><strong>No agents loaded</strong><span>Check configuration or create a specialist.</span></div></div>
                    ) : agents.map(agent => (
                        <article className="cp-agent-summary" key={agent.agent_id}>
                            <span className={`cp-status-dot ${agent.status === 'error' ? 'is-danger' : agent.status === 'deciding' ? 'is-active' : ''}`} />
                            <div><strong>{agent.name}</strong><span>{agent.status || 'idle'} · {formatTime(agent.last_decision)}</span></div>
                        </article>
                    ))}
                </div>
            </section>
        </div>
    );
}
