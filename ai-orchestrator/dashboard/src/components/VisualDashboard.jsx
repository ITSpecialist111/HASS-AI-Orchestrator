import React, { useEffect, useRef, useState } from 'react';
import { RefreshCw, Layout, Zap, Sparkles, X } from 'lucide-react';

const GENERATION_TIMEOUT_MS = 195_000;

export const VisualDashboard = () => {
    const [loading, setLoading] = useState(false);
    const [lastRefresh, setLastRefresh] = useState(new Date().toLocaleTimeString());
    const [error, setError] = useState(null);
    const [prompt, setPrompt] = useState("");
    const requestRef = useRef(null);

    useEffect(() => () => requestRef.current?.abort(), []);

    const refreshDashboard = async () => {
        if (loading) {
            requestRef.current?.abort();
            return;
        }
        const controller = new AbortController();
        let timedOut = false;
        requestRef.current = controller;
        const timeout = window.setTimeout(() => {
            timedOut = true;
            controller.abort();
        }, GENERATION_TIMEOUT_MS);
        setLoading(true);
        setError(null);
        try {
            let res;
            if (prompt.trim()) {
                res = await fetch('api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: `Generate a visual dashboard with this instruction: ${prompt}` }),
                    signal: controller.signal,
                });
            } else {
                res = await fetch('api/dashboard/refresh', { method: 'POST', signal: controller.signal });
            }
            if (!res.ok) throw new Error(`${res.status}: ${await res.text() || res.statusText}`);

            // Reload iframe by updating key
            setLastRefresh(new Date().toLocaleTimeString());
            setPrompt("");
        } catch (err) {
            setError(err.name === 'AbortError'
                ? (timedOut ? 'Dashboard generation timed out. Try a faster model or simpler request.' : 'Dashboard generation was cancelled.')
                : err.message);
        } finally {
            window.clearTimeout(timeout);
            if (requestRef.current === controller) requestRef.current = null;
            setLoading(false);
        }
    };

    return (
        <div className="flex min-w-0 flex-col space-y-4 lg:h-[calc(100vh-160px)]">
            {/* Header / Controls */}
            <div className="flex flex-col gap-4 bg-slate-900 p-4 rounded-xl border border-slate-800 shadow-lg lg:flex-row lg:items-center lg:justify-between">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-blue-500/20 rounded-lg">
                        <Layout className="text-blue-400" size={20} />
                    </div>
                    <div>
                        <h2 className="text-lg font-bold text-white">Dynamic Visual Dashboard</h2>
                        <p className="text-xs text-slate-500 flex items-center gap-1">
                            <Sparkles size={10} /> AI-Generated • Last updated: {lastRefresh}
                        </p>
                    </div>
                </div>

                <div className="flex w-full min-w-0 flex-1 flex-col gap-3 sm:flex-row sm:items-center lg:ml-8 lg:max-w-2xl">
                    <div className="relative min-w-0 flex-1">
                        <input
                            type="text"
                            aria-label="Dashboard design instruction"
                            value={prompt}
                            onChange={(e) => setPrompt(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && refreshDashboard()}
                            placeholder="e.g. 'Cyberpunk style' or 'Focus on Energy'"
                            className="w-full bg-slate-950 border border-slate-700 rounded-lg py-2 pl-4 pr-10 text-sm text-slate-200 focus:outline-none focus:border-blue-500 transition-all"
                        />
                        <Sparkles size={14} className="absolute right-3 top-2.5 text-slate-600" />
                    </div>
                    {error && <span className="text-xs text-red-400 font-medium">⚠️ {error}</span>}
                    <button
                        type="button"
                        onClick={refreshDashboard}
                        className={`flex shrink-0 items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium text-white transition-all group ${loading ? 'bg-red-600 hover:bg-red-500' : 'bg-blue-600 hover:bg-blue-500'}`}
                    >
                        {loading ? <X size={16} /> : <RefreshCw size={16} className="group-hover:rotate-180 transition-transform duration-500" />}
                        {loading ? 'Cancel generation' : (prompt ? 'Update Design' : 'Refresh Data')}
                    </button>
                </div>
            </div>

            {/* Iframe Container */}
            <div className="relative min-h-[420px] flex-1 overflow-hidden rounded-2xl border border-slate-800 bg-slate-900 shadow-2xl group lg:min-h-0">
                <iframe
                    src="api/dashboard/dynamic"
                    key={lastRefresh}
                    sandbox="allow-scripts"
                    referrerPolicy="no-referrer"
                    className="w-full h-full border-none"
                    title="AI Visual Dashboard"
                />

                {/* Overlay Hint */}
                <div className="absolute top-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity">
                    <div className="bg-slate-950/80 px-3 py-1.5 rounded-full border border-slate-700 text-[10px] text-slate-400 flex items-center gap-2">
                        <Zap size={10} className="text-amber-500" /> Use Chat to customize this view
                    </div>
                </div>
            </div>
        </div>
    );
};
