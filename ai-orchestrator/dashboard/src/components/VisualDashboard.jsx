import React, { useState, useEffect } from 'react';
import { RefreshCw, Layout, Zap, Sparkles } from 'lucide-react';

export const VisualDashboard = () => {
    const [loading, setLoading] = useState(false);
    const [lastRefresh, setLastRefresh] = useState(new Date().toLocaleTimeString());
    const [error, setError] = useState(null);
    const [prompt, setPrompt] = useState("");

    const refreshDashboard = async () => {
        setLoading(true);
        setError(null);
        try {
            if (prompt.trim()) {
                await fetch('api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: `Generate a visual dashboard with this instruction: ${prompt}` })
                });
            } else {
                const res = await fetch('api/dashboard/refresh', { method: 'POST' });
                if (!res.ok) throw new Error("Failed to refresh dashboard");
            }

            // Reload iframe by updating key
            setLastRefresh(new Date().toLocaleTimeString());
            setPrompt("");
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex flex-col h-[calc(100vh-160px)] space-y-4">
            {/* Header / Controls */}
            <div className="flex justify-between items-center bg-slate-900 p-4 rounded-xl border border-slate-800 shadow-lg">
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

                <div className="flex items-center gap-4 flex-1 max-w-2xl ml-8">
                    <div className="relative flex-1">
                        <input
                            type="text"
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
                        onClick={refreshDashboard}
                        disabled={loading}
                        className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-800 text-white rounded-lg text-sm font-medium transition-all group shrink-0"
                    >
                        <RefreshCw size={16} className={`${loading ? 'animate-spin' : 'group-hover:rotate-180 transition-transform duration-500'}`} />
                        {loading ? 'Generating...' : (prompt ? 'Update Design' : 'Refresh Data')}
                    </button>
                </div>
            </div>

            {/* Iframe Container */}
            <div className="flex-1 bg-slate-900 rounded-2xl border border-slate-800 shadow-2xl relative overflow-hidden group">
                <iframe
                    src="api/dashboard/dynamic"
                    key={lastRefresh}
                    className="w-full h-full border-none"
                    title="AI Visual Dashboard"
                />

                {/* Overlay Hint */}
                <div className="absolute top-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity">
                    <div className="bg-slate-950/80 backdrop-blur-md px-3 py-1.5 rounded-full border border-slate-700 text-[10px] text-slate-400 flex items-center gap-2">
                        <Zap size={10} className="text-amber-500" /> Use Chat to customize this view
                    </div>
                </div>
            </div>
        </div>
    );
};
