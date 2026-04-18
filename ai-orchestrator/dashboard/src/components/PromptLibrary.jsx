import React, { useEffect, useState } from 'react';
import { Sparkles, Play, Loader2, AlertCircle, ChevronDown, ChevronRight } from 'lucide-react';

/**
 * PromptLibrary — lists prompts discovered on the connected external
 * MCP server (e.g. OpenClaw HASS_MCP) and lets the operator fire any
 * of them as a one-click reasoning goal.
 */
export function PromptLibrary() {
    const [prompts, setPrompts] = useState([]);
    const [connected, setConnected] = useState(false);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [expanded, setExpanded] = useState(null);
    const [args, setArgs] = useState({});
    const [running, setRunning] = useState(null);
    const [results, setResults] = useState({});

    useEffect(() => {
        let cancelled = false;
        fetch('api/reasoning/prompts')
            .then(r => r.json())
            .then(data => {
                if (cancelled) return;
                setPrompts(data.prompts || []);
                setConnected(!!data.connected);
                setLoading(false);
            })
            .catch(err => {
                if (cancelled) return;
                setError(err.message);
                setLoading(false);
            });
        return () => { cancelled = true; };
    }, []);

    const runPrompt = async (name) => {
        setRunning(name);
        setResults(prev => ({ ...prev, [name]: null }));
        try {
            const res = await fetch(`api/reasoning/prompts/${encodeURIComponent(name)}/run`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ arguments: args[name] || {}, mode: 'auto' }),
            });
            if (!res.ok) {
                const body = await res.text();
                throw new Error(`${res.status}: ${body}`);
            }
            const data = await res.json();
            setResults(prev => ({ ...prev, [name]: data }));
        } catch (e) {
            setResults(prev => ({ ...prev, [name]: { error: e.message } }));
        } finally {
            setRunning(null);
        }
    };

    const updateArg = (promptName, argName, value) => {
        setArgs(prev => ({
            ...prev,
            [promptName]: { ...(prev[promptName] || {}), [argName]: value },
        }));
    };

    if (loading) {
        return (
            <div className="flex items-center gap-2 text-slate-500">
                <Loader2 size={16} className="animate-spin" /> Loading prompt library…
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div>
                <h2 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
                    <Sparkles size={20} className="text-amber-400" /> Prompt Library
                </h2>
                <p className="text-slate-500 text-sm">
                    One-click workflows discovered on the connected external MCP server.
                </p>
            </div>

            {!connected && (
                <div className="bg-amber-500/5 border border-amber-500/20 rounded-xl px-4 py-3 text-sm text-amber-300 flex items-center gap-2">
                    <AlertCircle size={16} />
                    External MCP not connected — no prompts available.
                </div>
            )}

            {error && (
                <div className="bg-red-500/5 border border-red-500/20 rounded-xl px-4 py-3 text-sm text-red-400">
                    {error}
                </div>
            )}

            {connected && prompts.length === 0 && (
                <div className="text-slate-500 text-sm">
                    Connected MCP server exposes no prompts.
                </div>
            )}

            <div className="space-y-3">
                {prompts.map(p => {
                    const isOpen = expanded === p.name;
                    const isRunning = running === p.name;
                    const result = results[p.name];
                    return (
                        <div key={p.name} className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
                            <button
                                onClick={() => setExpanded(isOpen ? null : p.name)}
                                className="w-full px-4 py-3 flex items-center gap-3 hover:bg-slate-900/60 transition"
                            >
                                {isOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                                <span className="font-mono text-sm text-slate-200">{p.name}</span>
                                {p.description && (
                                    <span className="text-xs text-slate-500 ml-2 truncate">{p.description}</span>
                                )}
                            </button>

                            {isOpen && (
                                <div className="px-4 pb-4 space-y-3 border-t border-slate-800/50">
                                    {(p.arguments || []).length > 0 && (
                                        <div className="space-y-2 pt-3">
                                            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                                                Arguments
                                            </div>
                                            {p.arguments.map(arg => (
                                                <div key={arg.name} className="flex items-center gap-2">
                                                    <label className="text-xs text-slate-400 w-32 shrink-0 font-mono">
                                                        {arg.name}{arg.required ? ' *' : ''}
                                                    </label>
                                                    <input
                                                        type="text"
                                                        value={(args[p.name] || {})[arg.name] || ''}
                                                        onChange={e => updateArg(p.name, arg.name, e.target.value)}
                                                        placeholder={arg.description || ''}
                                                        className="flex-1 bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs text-slate-200 font-mono"
                                                    />
                                                </div>
                                            ))}
                                        </div>
                                    )}

                                    <button
                                        onClick={() => runPrompt(p.name)}
                                        disabled={isRunning}
                                        className={`flex items-center gap-2 px-4 py-1.5 rounded text-xs font-semibold transition
                                            ${isRunning
                                                ? 'bg-slate-800 text-slate-600 cursor-not-allowed'
                                                : 'bg-gradient-to-r from-purple-600 to-blue-600 text-white hover:from-purple-500 hover:to-blue-500'
                                            }`}
                                    >
                                        {isRunning ? <Loader2 size={12} className="animate-spin" /> : <Play size={12} />}
                                        {isRunning ? 'Running…' : 'Run'}
                                    </button>

                                    {result && result.error && (
                                        <div className="bg-red-500/5 border border-red-500/20 rounded px-3 py-2 text-xs text-red-400">
                                            {result.error}
                                        </div>
                                    )}

                                    {result && !result.error && (
                                        <div className="bg-slate-950 border border-slate-800 rounded p-3 space-y-2">
                                            <div className="flex items-center gap-3 text-xs text-slate-500">
                                                <span className="font-mono">{result.iterations} iterations</span>
                                                <span className="font-mono">{result.tool_calls} tool calls</span>
                                                <span className="font-mono">
                                                    {result.duration_ms >= 1000
                                                        ? `${(result.duration_ms / 1000).toFixed(1)}s`
                                                        : `${result.duration_ms}ms`}
                                                </span>
                                                {result.executed_inline && (
                                                    <span className="px-2 py-0.5 rounded bg-green-500/10 text-green-400 border border-green-500/20 text-[10px] uppercase">
                                                        executed
                                                    </span>
                                                )}
                                                {result.plan && result.plan.requires_approval && (
                                                    <span className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 text-[10px] uppercase">
                                                        awaiting approval
                                                    </span>
                                                )}
                                            </div>
                                            <div className="text-sm text-slate-200 whitespace-pre-wrap">
                                                {result.answer}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
