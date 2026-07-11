import React, { useEffect, useRef, useState } from 'react';
import {
    ArrowRight,
    Brain,
    CheckCircle2,
    Clock3,
    Coins,
    Gauge,
    Info,
    Loader2,
    Play,
    ShieldCheck,
    Sparkles,
    Square,
    Wrench,
    XCircle,
    Zap,
} from 'lucide-react';
import { PromptLibrary } from './PromptLibrary';
import { ReasoningTrace } from './ReasoningTrace';

const FALLBACK_PROFILES = [
    {
        name: 'rapid',
        label: 'Rapid',
        description: 'Fast status checks and simple routines.',
        thinking: false,
        max_run_seconds: 60,
    },
    {
        name: 'balanced',
        label: 'Balanced',
        description: 'Thoughtful everyday planning with bounded latency.',
        thinking: true,
        max_run_seconds: 180,
    },
    {
        name: 'deep',
        label: 'Deep',
        description: 'Extended analysis for complex, multi-system goals.',
        thinking: true,
        max_run_seconds: 420,
    },
];

const PROFILE_ICONS = { rapid: Zap, balanced: Gauge, deep: Brain };

const readEventStream = async (response, onEvent) => {
    if (!response.body) throw new Error('Streaming is unavailable in this browser.');
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    const consumeBlock = block => {
        if (!block.trim()) return false;
        let eventType = 'message';
        const dataLines = [];
        block.split(/\r?\n/).forEach(line => {
            if (line.startsWith('event:')) eventType = line.slice(6).trim();
            if (line.startsWith('data:')) dataLines.push(line.slice(5).trim());
        });
        if (!dataLines.length) return false;
        const raw = dataLines.join('\n');
        let payload = {};
        try { payload = raw ? JSON.parse(raw) : {}; } catch { payload = { content: raw }; }
        onEvent(eventType, payload);
        return eventType === 'done';
    };

    while (true) {
        const { value, done } = await reader.read();
        buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
        const blocks = buffer.split(/\r?\n\r?\n/);
        buffer = blocks.pop() || '';
        if (blocks.some(consumeBlock)) {
            await reader.cancel();
            return;
        }
        if (done) break;
    }
    consumeBlock(buffer);
};

const normaliseTrace = trace => (trace || []).map((step, index) => ({
    id: `result-${index}`,
    type: 'iteration',
    iteration: step.iteration || index + 1,
    content: step.thought || '',
    tool_calls: step.tool_calls || [],
    tool_results: step.tool_results || [],
    duration_ms: step.duration_ms,
    status: 'complete',
}));

export function ReasoningPanel({ initialGoal = '', onRunComplete, onOpenPlans }) {
    const [goal, setGoal] = useState(initialGoal);
    const [running, setRunning] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState(null);
    const [info, setInfo] = useState(null);
    const [mode, setMode] = useState('auto');
    const [profile, setProfile] = useState('balanced');
    const [events, setEvents] = useState([]);
    const [phase, setPhase] = useState('Ready for a goal');
    const [planAction, setPlanAction] = useState(null);
    const [showWorkflows, setShowWorkflows] = useState(false);
    const abortRef = useRef(null);

    useEffect(() => {
        if (initialGoal) setGoal(initialGoal);
    }, [initialGoal]);

    useEffect(() => {
        let cancelled = false;
        fetch('api/reasoning/info')
            .then(response => {
                if (!response.ok) throw new Error(`Status ${response.status}`);
                return response.json();
            })
            .then(data => {
                if (cancelled) return;
                setInfo(data);
                if (data.default_profile) setProfile(data.default_profile);
            })
            .catch(err => {
                if (!cancelled) setError(`Reasoning service unavailable: ${err.message}`);
            });
        return () => { cancelled = true; };
    }, []);

    useEffect(() => () => abortRef.current?.abort(), []);

    const profiles = info?.profiles?.length ? info.profiles : FALLBACK_PROFILES;

    const appendEvent = event => setEvents(previous => [...previous, {
        id: `${Date.now()}-${previous.length}`,
        ...event,
    }]);

    const handleStreamEvent = (eventType, payload) => {
        if (eventType === 'start') {
            setPhase(payload.profile === 'rapid' ? 'Checking current state' : 'Observing the home');
            appendEvent({ type: 'start', content: `Started ${payload.profile || profile} run`, status: 'complete' });
        } else if (eventType === 'recall') {
            setPhase('Reviewing relevant experience');
            appendEvent({
                type: 'recall',
                content: payload.recalled?.length
                    ? `Used ${payload.recalled.length} relevant past run${payload.recalled.length === 1 ? '' : 's'}.`
                    : 'No previous run was needed for this goal.',
                status: 'complete',
            });
        } else if (eventType === 'thought') {
            setPhase('Reasoning over observations');
            appendEvent({
                type: 'model',
                iteration: payload.iteration,
                content: payload.content || 'Reasoning step completed; selecting the next grounded action.',
                usage: payload.usage,
                status: 'complete',
            });
        } else if (eventType === 'tool_call') {
            setPhase(`Using ${String(payload.name || 'a guarded tool').replaceAll('_', ' ')}`);
            appendEvent({
                type: 'tool',
                iteration: payload.iteration,
                name: payload.name,
                arguments: payload.arguments,
                result: payload.result,
                status: payload.result?.ok === false ? 'error' : 'complete',
            });
        } else if (eventType === 'plan') {
            setPhase(payload.plan?.requires_approval ? 'Preparing your review' : 'Finalising the outcome');
            if (payload.plan) appendEvent({ type: 'plan', plan: payload.plan, content: payload.plan.risk_summary, status: 'complete' });
        } else if (eventType === 'final') {
            setResult(payload.data || payload);
            setPhase('Run complete');
        } else if (eventType === 'error') {
            throw new Error(payload.error || 'The reasoning run failed.');
        }
    };

    const handleRun = async () => {
        if (!goal.trim() || running) return;
        const controller = new AbortController();
        abortRef.current = controller;
        setRunning(true);
        setResult(null);
        setEvents([]);
        setError(null);
        setPhase('Starting guarded run');

        try {
            const response = await fetch('api/reasoning/stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ goal: goal.trim(), mode, profile }),
                signal: controller.signal,
            });
            if (!response.ok) throw new Error(`${response.status}: ${await response.text()}`);
            await readEventStream(response, handleStreamEvent);
            onRunComplete?.();
        } catch (err) {
            if (err.name === 'AbortError') {
                setPhase('Run cancelled');
                appendEvent({ type: 'cancelled', content: 'The operator cancelled this run.', status: 'error' });
            } else {
                setError(err.message);
                setPhase('Run stopped');
            }
        } finally {
            abortRef.current = null;
            setRunning(false);
        }
    };

    const cancelRun = () => abortRef.current?.abort();

    const handlePlanAction = async action => {
        const planId = result?.plan?.id;
        if (!planId || planAction) return;
        setPlanAction(action);
        setError(null);
        try {
            const response = await fetch(`api/reasoning/plans/${planId}/${action}`, { method: 'POST' });
            if (!response.ok) throw new Error(`${response.status}: ${await response.text()}`);
            const data = await response.json();
            setResult(previous => ({
                ...previous,
                plan: { ...previous.plan, status: data.status },
                execution_results: data.execution_results ?? previous.execution_results,
            }));
            onRunComplete?.();
        } catch (err) {
            setError(err.message);
        } finally {
            setPlanAction(null);
        }
    };

    const trace = events.length ? events : normaliseTrace(result?.trace);
    const selectedProfile = profiles.find(item => item.name === profile);

    return (
        <div className="cp-page">
            <header className="cp-page-header">
                <div>
                    <div className="cp-eyebrow"><Brain size={14} /> Goal workspace</div>
                    <h1>Ask the home to accomplish an outcome</h1>
                    <p>Choose the depth. Observation, tool validation, action order, and approval policy remain deterministic in every profile.</p>
                </div>
                {info && (
                    <div className="cp-model-chip" title={`${info.tool_count || 0} guarded tools available`}>
                        <span className="cp-status-dot is-success" />
                        <span><strong>{info.model || 'Model ready'}</strong><small>{info.backend} · {info.tool_count || 0} tools</small></span>
                    </div>
                )}
            </header>

            <section className="cp-run-composer" aria-labelledby="goal-heading">
                <div className="cp-composer-section">
                    <div className="cp-section-label"><span>1</span><div><strong id="goal-heading">Describe the outcome</strong><small>State constraints and what success looks like.</small></div></div>
                    <label className="cp-sr-only" htmlFor="reasoning-goal">Goal</label>
                    <textarea
                        id="reasoning-goal"
                        value={goal}
                        onChange={event => setGoal(event.target.value)}
                        onKeyDown={event => {
                            if (event.key === 'Enter' && !event.shiftKey) {
                                event.preventDefault();
                                handleRun();
                            }
                        }}
                        placeholder="Example: investigate why the upstairs is cold, compare recent temperatures and occupancy, then prepare the safest corrective plan."
                        rows={4}
                        disabled={running}
                    />
                </div>

                <div className="cp-composer-section">
                    <div className="cp-section-label"><span>2</span><div><strong>Choose reasoning depth</strong><small>{info?.backend === 'ollama' && String(info?.model || '').startsWith('gemma4') ? 'Same Gemma 4 E4B model; different thinking and time budgets.' : 'Same selected provider; different bounded run depth.'}</small></div></div>
                    <div className="cp-profile-grid" role="radiogroup" aria-label="Reasoning profile">
                        {profiles.map(item => {
                            const Icon = PROFILE_ICONS[item.name] || Brain;
                            const selected = profile === item.name;
                            return (
                                <button
                                    type="button"
                                    role="radio"
                                    aria-checked={selected}
                                    className={`cp-profile-card ${selected ? 'is-selected' : ''}`}
                                    onClick={() => setProfile(item.name)}
                                    disabled={running}
                                    key={item.name}
                                >
                                    <span className="cp-profile-icon"><Icon size={18} /></span>
                                    <span><strong>{item.label || item.name}</strong><small>{item.description}</small></span>
                                    <em>{item.thinking ? 'Thinking on' : 'Low latency'}</em>
                                </button>
                            );
                        })}
                    </div>
                </div>

                <div className="cp-composer-footer">
                    <div className="cp-mode-control">
                        <span>Action policy</span>
                        <div className="cp-segmented cp-segmented--compact" role="radiogroup" aria-label="Action policy">
                            <button type="button" role="radio" aria-checked={mode === 'auto'} className={mode === 'auto' ? 'is-active' : ''} onClick={() => setMode('auto')} disabled={running}>Auto-safe</button>
                            <button type="button" role="radio" aria-checked={mode === 'plan'} className={mode === 'plan' ? 'is-active' : ''} onClick={() => setMode('plan')} disabled={running}>Plan only</button>
                        </div>
                        <span className="cp-mode-help"><ShieldCheck size={14} /> High-impact changes always pause for approval.</span>
                    </div>
                    <div className="cp-run-actions">
                        <button className="cp-button cp-button--secondary" type="button" onClick={() => setShowWorkflows(value => !value)} disabled={running}>
                            <Sparkles size={15} /> Workflows
                        </button>
                        {running ? (
                            <button className="cp-button cp-button--danger" type="button" onClick={cancelRun}><Square size={14} /> Cancel</button>
                        ) : (
                            <button className="cp-button cp-button--primary cp-button--large" type="button" onClick={handleRun} disabled={!goal.trim()}>
                                <Play size={16} /> Run {selectedProfile?.label || profile} <ArrowRight size={15} />
                            </button>
                        )}
                    </div>
                </div>
            </section>

            {showWorkflows && <PromptLibrary defaultProfile={profile} onResult={onRunComplete} />}

            {error && <div className="cp-alert is-danger" role="alert"><XCircle size={17} /><span><strong>Run could not continue</strong>{error}</span></div>}

            {(running || events.length > 0) && (
                <section className="cp-active-run" aria-live="polite">
                    <div className="cp-active-run-heading">
                        <span className={`cp-run-orb ${running ? 'is-running' : 'is-complete'}`}>
                            {running ? <Loader2 size={19} className="cp-spin" /> : <CheckCircle2 size={19} />}
                        </span>
                        <div><span className="cp-eyebrow">{running ? 'Active run' : 'Latest run'}</span><h2>{phase}</h2></div>
                        <span className="cp-pill">{profile}</span>
                    </div>
                    <ReasoningTrace reasoningEvents={trace} running={running} />
                </section>
            )}

            {result && (
                <section className="cp-result-card">
                    <div className="cp-result-heading">
                        <div><span className="cp-eyebrow">Outcome</span><h2>{result.stopped_reason === 'final' ? 'Goal completed' : 'Run finished with limits'}</h2></div>
                        <span className={`cp-pill ${result.stopped_reason === 'final' ? 'is-success' : 'is-warning'}`}>{result.stopped_reason || 'done'}</span>
                    </div>
                    <div className="cp-result-metrics">
                        <span><Brain size={15} /><strong>{result.iterations ?? 0}</strong> steps</span>
                        <span><Wrench size={15} /><strong>{result.successful_tool_calls ?? result.tool_calls ?? 0}</strong> tools succeeded</span>
                        <span><Clock3 size={15} /><strong>{result.duration_ms >= 1000 ? `${(result.duration_ms / 1000).toFixed(1)}s` : `${result.duration_ms || 0}ms`}</strong></span>
                        {(result.usage?.input_tokens || result.usage?.output_tokens) && (
                            <span><Coins size={15} /><strong>{((result.usage.input_tokens || 0) + (result.usage.output_tokens || 0)).toLocaleString()}</strong> tokens</span>
                        )}
                    </div>
                    <div className="cp-answer">
                        <span>What the home found</span>
                        <p>{result.answer || 'No answer was returned.'}</p>
                    </div>

                    {result.plan && (
                        <div className="cp-inline-plan">
                            <span className={`cp-plan-risk ${result.plan.requires_approval ? 'is-warning' : 'is-success'}`}><ShieldCheck size={20} /></span>
                            <div>
                                <strong>{result.plan.requires_approval ? 'Your approval is required' : 'Deterministic plan completed'}</strong>
                                <p>{result.plan.risk_summary || `${result.plan.mutating_count || 0} exact actions recorded.`}</p>
                            </div>
                            <span className="cp-pill">{String(result.plan.status || 'pending').replaceAll('_', ' ')}</span>
                            {result.plan.status === 'pending' && result.plan.mutating_count > 0 && (
                                <div className="cp-inline-plan-actions">
                                    <button className="cp-button cp-button--primary" type="button" onClick={() => handlePlanAction('execute')} disabled={!!planAction}>
                                        {planAction === 'execute' ? <Loader2 size={14} className="cp-spin" /> : <ShieldCheck size={14} />} Approve exact plan
                                    </button>
                                    <button className="cp-button cp-button--danger" type="button" onClick={() => handlePlanAction('reject')} disabled={!!planAction}><XCircle size={14} /> Reject</button>
                                </div>
                            )}
                            {result.plan.status === 'pending' && <button className="cp-text-button" type="button" onClick={onOpenPlans}>Open detailed review <ArrowRight size={13} /></button>}
                        </div>
                    )}
                </section>
            )}

            <aside className="cp-safety-note">
                <Info size={16} />
                <p><strong>What “thinking” means here:</strong> model reasoning can be enabled for harder goals, but private scratch work is not shown or fed back into later turns. You see grounded observations, guarded tool calls, exact plans, and outcomes.</p>
            </aside>
        </div>
    );
}
