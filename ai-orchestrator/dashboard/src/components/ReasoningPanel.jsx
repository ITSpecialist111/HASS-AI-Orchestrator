
import React, { useState, useEffect } from 'react';
import { Brain, Play, Loader2, Clock, Wrench, Info, Zap, ShieldCheck, XCircle, Coins } from 'lucide-react';
import { ReasoningTrace } from './ReasoningTrace';

export function ReasoningPanel({ reasoningEvents = [] }) {
    const [goal, setGoal] = useState('');
    const [running, setRunning] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState(null);
    const [info, setInfo] = useState(null);
    const [mode, setMode] = useState('auto');
    const [planAction, setPlanAction] = useState(null);

    // Fetch reasoning agent info on mount
    useEffect(() => {
        fetch('api/reasoning/info')
            .then(res => {
                if (!res.ok) throw new Error(`Status ${res.status}`);
                return res.json();
            })
            .then(data => setInfo(data))
            .catch(err => console.error("Failed to fetch reasoning info:", err));
    }, []);

    const handleRun = async () => {
        if (!goal.trim() || running) return;

        setRunning(true);
        setResult(null);
        setError(null);

        try {
            const res = await fetch('api/reasoning/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ goal: goal.trim(), mode }),
            });

            if (!res.ok) {
                const errText = await res.text();
                throw new Error(`API Error ${res.status}: ${errText}`);
            }

            const data = await res.json();
            setResult(data);
        } catch (e) {
            setError(e.message);
        } finally {
            setRunning(false);
        }
    };

    const handlePlanAction = async (action) => {
        const planId = result?.plan?.id;
        if (!planId || planAction) return;
        setPlanAction(action);
        setError(null);
        try {
            const res = await fetch(`api/reasoning/plans/${planId}/${action}`, { method: 'POST' });
            if (!res.ok) throw new Error(`Plan ${action} failed: ${res.status} ${await res.text()}`);
            const data = await res.json();
            setResult(prev => ({
                ...prev,
                plan: { ...prev.plan, status: data.status },
                execution_results: data.execution_results ?? prev.execution_results,
            }));
        } catch (e) {
            setError(e.message);
        } finally {
            setPlanAction(null);
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleRun();
        }
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div>
                <h2 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
                    <Brain size={20} className="text-purple-400" /> Deep Reasoning
                </h2>
                <p className="text-slate-500 text-sm">Run multi-step reasoning goals with tool access</p>
            </div>

            {/* Info Bar */}
            {info && (
                <div className="flex items-center gap-4 px-4 py-3 bg-slate-900 border border-slate-800 rounded-xl text-sm">
                    <div className="flex items-center gap-2 text-slate-400">
                        <Info size={14} className="text-slate-500" />
                        <span className="font-medium text-slate-300">{info.name || info.agent_id || 'Reasoning Agent'}</span>
                    </div>
                    <div className="w-px h-4 bg-slate-800" />
                    <div className="flex items-center gap-1.5 text-slate-500">
                        <Zap size={12} />
                        <span className="font-mono text-xs">
                            {info.backend || 'unknown'}{info.model ? ` / ${info.model}` : ''}{info.reasoning_effort ? ` · ${info.reasoning_effort}` : ''}
                        </span>
                    </div>
                    <div className="w-px h-4 bg-slate-800" />
                    <div className="flex items-center gap-1.5 text-slate-500">
                        <Wrench size={12} />
                        <span className="font-mono text-xs">{info.tool_count ?? '?'} tools</span>
                    </div>
                    {info.external_mcp_connected && (
                        <>
                            <div className="w-px h-4 bg-slate-800" />
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold tracking-wide uppercase bg-green-500/10 text-green-400 border border-green-500/20">
                                MCP Connected
                            </span>
                        </>
                    )}
                    <div className="ml-auto">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wide uppercase border
                            ${info.status === 'ready' || info.status === 'active' || info.status === 'idle'
                                ? 'bg-green-500/10 text-green-400 border-green-500/20'
                                : 'bg-slate-700/30 text-slate-400 border-slate-700'
                            }`}>
                            {info.status || 'unknown'}
                        </span>
                    </div>
                </div>
            )}

            {/* Goal Input */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
                <div className="p-4 space-y-3">
                    <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider">
                        Goal
                    </label>
                    <div className="flex items-center gap-2" role="group" aria-label="Reasoning mode">
                        {[
                            ['auto', 'Auto', 'Reads first; executes routine actions and pauses risky plans.'],
                            ['plan', 'Plan only', 'Observe and prepare a reviewable plan without changing the home.'],
                        ].map(([value, label, title]) => (
                            <button
                                key={value}
                                type="button"
                                title={title}
                                onClick={() => setMode(value)}
                                disabled={running}
                                className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors ${mode === value
                                    ? 'bg-purple-500/15 text-purple-300 border-purple-500/40'
                                    : 'bg-slate-950 text-slate-500 border-slate-800 hover:text-slate-300'
                                }`}
                            >
                                {label}
                            </button>
                        ))}
                        <span className="text-xs text-slate-600 ml-1">
                            Direct execution is intentionally unavailable.
                        </span>
                    </div>
                    <textarea
                        value={goal}
                        onChange={(e) => setGoal(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Describe the goal for the reasoning agent... e.g. 'Determine the optimal heating schedule for this week based on the weather forecast and occupancy patterns'"
                        rows={3}
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-3 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/20 resize-none font-mono"
                        disabled={running}
                    />
                    <div className="flex items-center justify-between">
                        <span className="text-xs text-slate-600">Press Enter to run, Shift+Enter for newline</span>
                        <button
                            onClick={handleRun}
                            disabled={!goal.trim() || running}
                            className={`flex items-center gap-2 px-5 py-2 rounded-lg text-sm font-semibold transition-all duration-200
                                ${!goal.trim() || running
                                    ? 'bg-slate-800 text-slate-600 cursor-not-allowed'
                                    : 'bg-gradient-to-r from-purple-600 to-blue-600 text-white hover:from-purple-500 hover:to-blue-500 shadow-lg shadow-purple-900/20 hover:shadow-purple-900/40'
                                }`}
                        >
                            {running ? (
                                <>
                                    <Loader2 size={16} className="animate-spin" />
                                    Running...
                                </>
                            ) : (
                                <>
                                    <Play size={16} />
                                    Run
                                </>
                            )}
                        </button>
                    </div>
                </div>
            </div>

            {/* Error Display */}
            {error && (
                <div className="bg-red-500/5 border border-red-500/20 rounded-xl px-4 py-3 text-sm text-red-400">
                    <span className="font-semibold">Error:</span> {error}
                </div>
            )}

            {/* Result Summary */}
            {result && (
                <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
                    <div className="px-4 py-3 bg-slate-900/80 border-b border-slate-800 flex items-center gap-2">
                        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Result</span>
                        <span className={`ml-2 px-2 py-0.5 rounded text-[10px] font-bold tracking-wide uppercase border
                            ${result.stopped_reason === 'final'
                                ? 'bg-green-500/10 text-green-400 border-green-500/20'
                                : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                            }`}>
                            {result.stopped_reason || 'done'}
                        </span>
                    </div>

                    {/* Stats row */}
                    <div className="flex items-center gap-6 px-4 py-3 border-b border-slate-800/50 text-sm">
                        <div className="flex items-center gap-1.5 text-slate-400">
                            <Brain size={14} className="text-purple-400" />
                            <span className="font-mono text-xs">{result.iterations ?? '?'} iterations</span>
                        </div>
                        {(result.successful_tool_calls != null || result.failed_tool_calls != null) && (
                            <div className="flex items-center gap-1.5 text-slate-400">
                                <ShieldCheck size={14} className="text-emerald-400" />
                                <span className="font-mono text-xs">
                                    {result.successful_tool_calls ?? 0} ok / {result.failed_tool_calls ?? 0} failed
                                </span>
                            </div>
                        )}
                        {(result.usage?.input_tokens || result.usage?.output_tokens) && (
                            <div className="flex items-center gap-1.5 text-slate-400">
                                <Coins size={14} className="text-amber-400" />
                                <span className="font-mono text-xs">
                                    {(result.usage.input_tokens ?? 0).toLocaleString()} in / {(result.usage.output_tokens ?? 0).toLocaleString()} out
                                </span>
                            </div>
                        )}
                        <div className="flex items-center gap-1.5 text-slate-400">
                            <Wrench size={14} className="text-blue-400" />
                            <span className="font-mono text-xs">{result.tool_calls ?? '?'} tool calls</span>
                        </div>
                        {result.duration_ms != null && (
                            <div className="flex items-center gap-1.5 text-slate-400">
                                <Clock size={14} className="text-slate-500" />
                                <span className="font-mono text-xs">
                                    {result.duration_ms >= 1000
                                        ? `${(result.duration_ms / 1000).toFixed(1)}s`
                                        : `${result.duration_ms}ms`
                                    }
                                </span>
                            </div>
                        )}
                    </div>

                    {/* Answer */}
                    <div className="p-4">
                        <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Answer</h4>
                        <div className="text-sm text-slate-200 leading-relaxed whitespace-pre-wrap bg-slate-950 p-4 rounded-lg border border-slate-800">
                            {result.answer || 'No answer returned.'}
                        </div>
                    </div>

                    {result.plan && (
                        <div className="p-4 pt-0">
                            <div className="bg-slate-950 border border-slate-800 rounded-lg p-4 space-y-3">
                                <div className="flex items-start gap-3">
                                    <ShieldCheck size={18} className="text-purple-400 mt-0.5" />
                                    <div>
                                        <h4 className="text-sm font-semibold text-slate-200">Deterministic plan</h4>
                                        <p className="text-xs text-slate-500 mt-1">{result.plan.risk_summary}</p>
                                    </div>
                                    <span className="ml-auto px-2 py-0.5 rounded text-[10px] uppercase font-bold bg-slate-800 text-slate-400 border border-slate-700">
                                        {result.plan.status}
                                    </span>
                                </div>
                                {result.plan.status === 'pending' && result.plan.mutating_count > 0 && (
                                    <div className="flex gap-2 pt-1">
                                        <button
                                            onClick={() => handlePlanAction('execute')}
                                            disabled={!!planAction}
                                            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-emerald-600/20 text-emerald-300 border border-emerald-500/30 text-xs font-semibold hover:bg-emerald-600/30 disabled:opacity-50"
                                        >
                                            {planAction === 'execute' ? <Loader2 size={13} className="animate-spin" /> : <ShieldCheck size={13} />}
                                            Approve & execute exact plan
                                        </button>
                                        <button
                                            onClick={() => handlePlanAction('reject')}
                                            disabled={!!planAction}
                                            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-red-500/10 text-red-300 border border-red-500/20 text-xs font-semibold hover:bg-red-500/20 disabled:opacity-50"
                                        >
                                            <XCircle size={13} /> Reject
                                        </button>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* Live Reasoning Trace */}
            {(reasoningEvents.length > 0 || (result && result.trace)) && (
                <ReasoningTrace reasoningEvents={reasoningEvents.length > 0 ? reasoningEvents : (result.trace || [])} />
            )}
        </div>
    );
}
