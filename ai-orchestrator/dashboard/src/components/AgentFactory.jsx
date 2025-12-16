import React, { useState, useEffect } from 'react';
import { Bot, Wand2, Plus, Save, X, Lightbulb } from 'lucide-react';

export const AgentFactory = ({ onAgentCreated }) => {
    const [isOpen, setIsOpen] = useState(false);
    const [mode, setMode] = useState('prompt'); // prompt | review | loading
    const [prompt, setPrompt] = useState('');
    const [suggestions, setSuggestions] = useState([]);
    const [generatedConfig, setGeneratedConfig] = useState(null);
    const [error, setError] = useState(null);

    // Load suggestions on open
    useEffect(() => {
        if (isOpen) {
            loadSuggestions();
        }
    }, [isOpen]);

    const loadSuggestions = async () => {
        try {
            const res = await fetch('api/factory/suggestions');
            if (!res.ok) throw new Error(`API Error ${res.status}`);
            const data = await res.json();
            if (Array.isArray(data)) {
                setSuggestions(data);
            } else {
                console.warn("Suggestions API returned non-array:", data);
                setSuggestions([]);
            }
        } catch (e) {
            console.error("Failed to load suggestions:", e);
            setSuggestions([]);
        }
    };

    const handleGenerate = async (e) => {
        e.preventDefault();
        setMode('loading');
        setError(null);
        try {
            const res = await fetch('api/factory/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt })
            });

            if (!res.ok) {
                const text = await res.text();
                throw new Error(`Server Error ${res.status}: ${text}`);
            }

            const data = await res.json();
            setGeneratedConfig(data);
            setMode('review');
        } catch (err) {
            console.error(err);
            setError(`Failed to generate agent: ${err.message}`);
            setMode('prompt');
        }
    };

    const handleSave = async () => {
        setMode('loading');
        try {
            const res = await fetch('api/factory/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ config: generatedConfig })
            });

            if (res.ok) {
                setIsOpen(false);
                setMode('prompt');
                setPrompt('');
                setGeneratedConfig(null);
                if (onAgentCreated) onAgentCreated();
                alert("Agent Saved! Restart add-on to activate.");
            } else {
                const d = await res.json();
                setError(d.detail);
                setMode('review');
            }
        } catch (err) {
            setError('Failed to save.');
            setMode('review');
        }
    };

    if (!isOpen) {
        return (
            <button
                onClick={() => setIsOpen(true)}
                className="fixed bottom-8 right-8 bg-purple-600 hover:bg-purple-500 text-white p-4 rounded-full shadow-lg transition-transform hover:scale-110 flex items-center gap-2 group z-50"
            >
                <Plus size={24} />
                <span className="max-w-0 overflow-hidden group-hover:max-w-xs transition-all duration-300 whitespace-nowrap">
                    New Agent
                </span>
            </button>
        );
    }

    return (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-2xl shadow-2xl flex flex-col max-h-[90vh]">

                {/* Header */}
                <div className="p-6 border-b border-slate-800 flex justify-between items-center bg-slate-900 rounded-t-xl">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-purple-500/20 rounded-lg">
                            <Bot className="text-purple-400" size={24} />
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-white">Agent Factory</h2>
                            <p className="text-sm text-slate-400">The Architect will design your agent.</p>
                        </div>
                    </div>
                    <button onClick={() => setIsOpen(false)} className="text-slate-500 hover:text-white">
                        <X size={24} />
                    </button>
                </div>

                {/* Content */}
                <div className="p-6 overflow-y-auto flex-1">
                    {error && (
                        <div className="mb-4 p-3 bg-red-900/30 border border-red-800 rounded text-red-200 text-sm">
                            {error}
                        </div>
                    )}

                    {mode === 'prompt' && (
                        <div className="space-y-6">
                            {/* Manual Input */}
                            <form onSubmit={handleGenerate} className="space-y-3">
                                <label className="block text-sm font-medium text-slate-300">
                                    What should this agent do?
                                </label>
                                <div className="relative">
                                    <textarea
                                        value={prompt}
                                        onChange={(e) => setPrompt(e.target.value)}
                                        placeholder="e.g., 'Create a Movie Night Manager that dims the living room lights when the TV is playing.'"
                                        className="w-full h-32 bg-slate-800 border-slate-700 rounded-lg p-4 text-slate-200 placeholder-slate-500 focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none"
                                    />
                                    <div className="absolute bottom-3 right-3">
                                        <button
                                            type="submit"
                                            disabled={!prompt.trim()}
                                            className="bg-purple-600 hover:bg-purple-500 text-white px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                                        >
                                            <Wand2 size={16} /> Generate Plan
                                        </button>
                                    </div>
                                </div>
                            </form>

                            {/* Suggestions */}
                            {suggestions.length > 0 && (
                                <div className="space-y-3">
                                    <h3 className="text-sm font-medium text-slate-400 flex items-center gap-2">
                                        <Lightbulb size={16} /> Suggested for you
                                    </h3>
                                    <div className="grid grid-cols-1 gap-3">
                                        {suggestions.map((s, i) => (
                                            <button
                                                key={i}
                                                onClick={() => setPrompt(s.prompt)}
                                                className="text-left p-4 bg-slate-800/50 hover:bg-slate-800 border border-slate-700 rounded-lg transition-colors group"
                                            >
                                                <div className="font-medium text-slate-300 group-hover:text-purple-400 transition-colors">
                                                    {s.title}
                                                </div>
                                                <div className="text-sm text-slate-500 mt-1">{s.reason}</div>
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {mode === 'loading' && (
                        <div className="flex flex-col items-center justify-center py-12 space-y-4">
                            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
                            <p className="text-slate-400 animate-pulse">Architect is drafting blueprint...</p>
                        </div>
                    )}

                    {mode === 'review' && generatedConfig && (
                        <div className="space-y-4">
                            <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
                                <h3 className="font-medium text-slate-300 mb-2">Blueprint Review</h3>
                                <div className="space-y-3 text-sm">
                                    <div className="grid grid-cols-3 gap-2 items-center">
                                        <div className="text-slate-500">Name</div>
                                        <div className="col-span-2">
                                            <input
                                                type="text"
                                                value={generatedConfig.name}
                                                onChange={(e) => setGeneratedConfig({ ...generatedConfig, name: e.target.value })}
                                                className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-slate-200 text-sm focus:border-purple-500 outline-none"
                                            />
                                        </div>

                                        <div className="text-slate-500">ID</div>
                                        <div className="col-span-2">
                                            <input
                                                type="text"
                                                value={generatedConfig.id}
                                                onChange={(e) => setGeneratedConfig({ ...generatedConfig, id: e.target.value })}
                                                className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-slate-200 text-sm font-mono focus:border-purple-500 outline-none"
                                            />
                                        </div>

                                        <div className="text-slate-500 self-start pt-1">Entities</div>
                                        <div className="col-span-2 flex flex-wrap gap-1">
                                            {generatedConfig.entities.map(e => (
                                                <span key={e} className="px-2 py-0.5 bg-slate-700 rounded text-xs text-slate-300">
                                                    {e}
                                                </span>
                                            ))}
                                        </div>
                                    </div>

                                    <div className="pt-3 border-t border-slate-700">
                                        <div className="text-slate-500 mb-1">Instructions</div>
                                        <textarea
                                            value={generatedConfig.instruction}
                                            onChange={(e) => setGeneratedConfig({ ...generatedConfig, instruction: e.target.value })}
                                            className="w-full h-24 bg-slate-950 border border-slate-800 rounded p-3 text-slate-300 font-mono text-xs whitespace-pre-wrap outline-none focus:border-purple-500 resize-none"
                                        />
                                    </div>
                                </div>
                            </div>

                            <div className="flex gap-3 justify-end pt-4">
                                <button
                                    onClick={() => setMode('prompt')}
                                    className="px-4 py-2 text-slate-400 hover:text-white"
                                >
                                    Back
                                </button>
                                <button
                                    onClick={handleSave}
                                    className="bg-green-600 hover:bg-green-500 text-white px-6 py-2 rounded-lg font-medium flex items-center gap-2"
                                >
                                    <Save size={18} /> Approve & Deploy
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};
