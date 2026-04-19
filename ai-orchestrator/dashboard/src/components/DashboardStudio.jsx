import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
    Sparkles, Wand2, Pin, PinOff, Trash2, RefreshCw, Plus,
    Layers, GitBranch, Download, Copy, AlertCircle, X, Loader2
} from 'lucide-react';

/**
 * DashboardStudio (Phase 10A UI)
 *
 * "AI image generation, but for dashboards" — a gallery of generated
 * dashboards with prompt-to-design, iterate (refine an existing one),
 * variations (N parallel takes), and pin/delete.
 *
 * Live data binding is automatic: the backend injects a polling shim
 * into every saved dashboard, so iframes refresh values without the UI
 * doing anything.
 */
export const DashboardStudio = () => {
    const [dashboards, setDashboards] = useState([]);
    const [selected, setSelected] = useState(null); // dashboard id
    const [prompt, setPrompt] = useState('');
    const [iterateText, setIterateText] = useState('');
    const [variationCount, setVariationCount] = useState(3);
    const [provider, setProvider] = useState(''); // empty = backend default
    const [model, setModel] = useState('');
    const [busy, setBusy] = useState(false);
    const [busyKind, setBusyKind] = useState(null); // 'generate' | 'iterate' | 'variations'
    const [error, setError] = useState(null);
    const [iframeNonce, setIframeNonce] = useState(0);
    const promptRef = useRef(null);

    const refreshList = async () => {
        try {
            const res = await fetch('api/studio/dashboards');
            if (!res.ok) throw new Error(`Failed to list (${res.status})`);
            const data = await res.json();
            setDashboards(Array.isArray(data) ? data : []);
            // If our currently-selected dashboard was deleted elsewhere,
            // fall back to the newest one (or null).
            if (selected && !data.find(d => d.id === selected)) {
                setSelected(data[0]?.id || null);
            } else if (!selected && data.length > 0) {
                setSelected(data[0].id);
            }
        } catch (e) {
            setError(e.message);
        }
    };

    useEffect(() => { refreshList(); /* eslint-disable-next-line */ }, []);

    const callJson = async (url, opts = {}) => {
        const res = await fetch(url, {
            ...opts,
            headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) },
        });
        if (!res.ok) {
            const text = await res.text();
            throw new Error(`${res.status}: ${text || res.statusText}`);
        }
        return res.json();
    };

    const buildBody = (extra) => ({
        ...extra,
        ...(provider ? { provider } : {}),
        ...(model ? { model } : {}),
    });

    const onGenerate = async () => {
        if (!prompt.trim() || busy) return;
        setBusy(true); setBusyKind('generate'); setError(null);
        try {
            const meta = await callJson('api/studio/generate', {
                method: 'POST',
                body: JSON.stringify(buildBody({ prompt })),
            });
            await refreshList();
            setSelected(meta.id);
            setIframeNonce(n => n + 1);
            setPrompt('');
        } catch (e) { setError(e.message); }
        finally { setBusy(false); setBusyKind(null); }
    };

    const onIterate = async () => {
        if (!iterateText.trim() || !selected || busy) return;
        setBusy(true); setBusyKind('iterate'); setError(null);
        try {
            const meta = await callJson(`api/studio/dashboards/${selected}/iterate`, {
                method: 'POST',
                body: JSON.stringify(buildBody({ instruction: iterateText })),
            });
            await refreshList();
            setSelected(meta.id);
            setIframeNonce(n => n + 1);
            setIterateText('');
        } catch (e) { setError(e.message); }
        finally { setBusy(false); setBusyKind(null); }
    };

    const onVariations = async () => {
        if (!prompt.trim() || busy) return;
        setBusy(true); setBusyKind('variations'); setError(null);
        try {
            const metas = await callJson('api/studio/variations', {
                method: 'POST',
                body: JSON.stringify(buildBody({ prompt, n: Number(variationCount) || 3 })),
            });
            await refreshList();
            if (metas.length > 0) {
                setSelected(metas[0].id);
                setIframeNonce(n => n + 1);
            }
        } catch (e) { setError(e.message); }
        finally { setBusy(false); setBusyKind(null); }
    };

    const onPinToggle = async (id, pinned) => {
        try {
            await callJson(`api/studio/dashboards/${id}/${pinned ? 'unpin' : 'pin'}`, { method: 'POST' });
            await refreshList();
        } catch (e) { setError(e.message); }
    };

    const onDelete = async (id) => {
        if (!confirm('Delete this dashboard? Pinned dashboards are protected.')) return;
        try {
            const res = await fetch(`api/studio/dashboards/${id}`, { method: 'DELETE' });
            if (!res.ok) throw new Error(`Delete failed (${res.status})`);
            if (selected === id) setSelected(null);
            await refreshList();
        } catch (e) { setError(e.message); }
    };

    const onCopyPrompt = async (text) => {
        try { await navigator.clipboard.writeText(text || ''); } catch (e) { /* ignore */ }
    };

    const selectedMeta = useMemo(
        () => dashboards.find(d => d.id === selected) || null,
        [dashboards, selected]
    );

    const formatTs = (iso) => {
        try {
            const d = new Date(iso);
            return d.toLocaleString([], { dateStyle: 'short', timeStyle: 'short' });
        } catch { return iso; }
    };

    const variationsForSelected = useMemo(() => {
        if (!selectedMeta?.variation_of) return [];
        return dashboards.filter(d => d.variation_of === selectedMeta.variation_of);
    }, [dashboards, selectedMeta]);

    return (
        <div className="flex flex-col h-[calc(100vh-160px)] gap-4">
            {/* Header */}
            <div className="flex items-center justify-between bg-slate-900 p-4 rounded-xl border border-slate-800 shadow-lg">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-purple-500/20 rounded-lg">
                        <Wand2 className="text-purple-400" size={20} />
                    </div>
                    <div>
                        <h2 className="text-lg font-bold text-white">Dashboard Studio</h2>
                        <p className="text-xs text-slate-500 flex items-center gap-1">
                            <Sparkles size={10} /> Prompt-to-dashboard with iterate, variations and a saved gallery
                        </p>
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    <ProviderSelector provider={provider} onProvider={setProvider} model={model} onModel={setModel} />
                    <button
                        onClick={refreshList}
                        className="p-2 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors"
                        title="Refresh gallery"
                    >
                        <RefreshCw size={16} />
                    </button>
                </div>
            </div>

            {/* Prompt bar */}
            <div className="bg-slate-900 p-4 rounded-xl border border-slate-800 shadow-lg space-y-3">
                <div className="flex items-stretch gap-2">
                    <div className="relative flex-1">
                        <input
                            ref={promptRef}
                            type="text"
                            value={prompt}
                            onChange={(e) => setPrompt(e.target.value)}
                            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); onGenerate(); } }}
                            placeholder="Describe your dashboard… e.g. 'Energy hub with solar, battery, grid and a forecast chart'"
                            className="w-full bg-slate-950 border border-slate-700 rounded-lg py-2.5 pl-10 pr-4 text-sm text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-purple-500 transition-all"
                        />
                        <Sparkles size={14} className="absolute left-3 top-3 text-slate-500" />
                    </div>
                    <button
                        onClick={onGenerate}
                        disabled={busy || !prompt.trim()}
                        className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-500 disabled:bg-slate-800 disabled:text-slate-500 text-white rounded-lg text-sm font-medium transition-all shrink-0"
                    >
                        {busyKind === 'generate' ? <Loader2 size={16} className="animate-spin" /> : <Plus size={16} />}
                        Generate
                    </button>
                    <div className="flex items-stretch border border-slate-700 rounded-lg overflow-hidden shrink-0">
                        <select
                            value={variationCount}
                            onChange={(e) => setVariationCount(e.target.value)}
                            className="bg-slate-950 text-slate-300 text-sm px-2 border-r border-slate-700 focus:outline-none"
                            title="Number of variations"
                        >
                            {[2, 3, 4, 5, 6].map(n => <option key={n} value={n}>{n}×</option>)}
                        </select>
                        <button
                            onClick={onVariations}
                            disabled={busy || !prompt.trim()}
                            className="flex items-center gap-2 px-3 py-2 bg-slate-800 hover:bg-slate-700 disabled:bg-slate-900 disabled:text-slate-600 text-slate-200 text-sm font-medium transition-all"
                        >
                            {busyKind === 'variations' ? <Loader2 size={14} className="animate-spin" /> : <Layers size={14} />}
                            Variations
                        </button>
                    </div>
                </div>
                {error && (
                    <div className="flex items-start gap-2 text-xs text-red-300 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
                        <AlertCircle size={14} className="shrink-0 mt-0.5" />
                        <span className="flex-1">{error}</span>
                        <button onClick={() => setError(null)} className="text-red-300 hover:text-red-100"><X size={12} /></button>
                    </div>
                )}
            </div>

            {/* Main content: gallery + preview */}
            <div className="flex-1 grid grid-cols-12 gap-4 min-h-0">
                {/* Gallery sidebar */}
                <aside className="col-span-3 bg-slate-900 border border-slate-800 rounded-xl shadow-lg flex flex-col min-h-0">
                    <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between">
                        <h3 className="text-sm font-semibold text-slate-200">Gallery</h3>
                        <span className="text-xs text-slate-500">{dashboards.length}</span>
                    </div>
                    <div className="flex-1 overflow-y-auto p-2 space-y-1">
                        {dashboards.length === 0 && (
                            <div className="text-xs text-slate-500 text-center py-8 px-4">
                                No dashboards yet. Try a prompt like<br />
                                <span className="text-slate-400 italic">"Cosy living-room overview with lights and temperature"</span>
                            </div>
                        )}
                        {dashboards.map((d) => {
                            const isActive = d.id === selected;
                            return (
                                <button
                                    key={d.id}
                                    onClick={() => { setSelected(d.id); setIframeNonce(n => n + 1); }}
                                    className={`w-full text-left px-3 py-2.5 rounded-lg border transition-all group ${isActive
                                        ? 'bg-purple-500/10 border-purple-500/30 text-purple-100'
                                        : 'bg-slate-950/40 border-slate-800 text-slate-300 hover:border-slate-700 hover:bg-slate-800/50'
                                        }`}
                                >
                                    <div className="flex items-center justify-between gap-2">
                                        <div className="flex items-center gap-2 min-w-0 flex-1">
                                            {d.pinned && <Pin size={11} className="text-amber-400 shrink-0" />}
                                            {d.parent_id && <GitBranch size={11} className="text-blue-400 shrink-0" title="Iterated" />}
                                            {d.variation_of && <Layers size={11} className="text-emerald-400 shrink-0" title="Variation" />}
                                            <span className="text-sm font-medium truncate">{d.title}</span>
                                        </div>
                                    </div>
                                    <div className="text-[10px] text-slate-500 mt-1 flex items-center justify-between">
                                        <span>{formatTs(d.created_at)}</span>
                                        <span className="font-mono">{d.provider}</span>
                                    </div>
                                </button>
                            );
                        })}
                    </div>
                </aside>

                {/* Preview + tools */}
                <section className="col-span-9 flex flex-col min-h-0 gap-3">
                    {selectedMeta ? (
                        <>
                            {/* Selected meta + actions */}
                            <div className="bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 shadow-lg flex items-center justify-between gap-3">
                                <div className="min-w-0 flex-1">
                                    <div className="flex items-center gap-2">
                                        <h3 className="text-sm font-semibold text-white truncate">{selectedMeta.title}</h3>
                                        <span className="text-[10px] uppercase tracking-wider text-slate-500 font-mono">
                                            {selectedMeta.provider}/{selectedMeta.model}
                                        </span>
                                    </div>
                                    <p className="text-xs text-slate-500 truncate">
                                        {selectedMeta.prompt}
                                        {selectedMeta.instruction && <span className="text-slate-400"> → {selectedMeta.instruction}</span>}
                                    </p>
                                </div>
                                <div className="flex items-center gap-1 shrink-0">
                                    <button onClick={() => onCopyPrompt(selectedMeta.prompt)} title="Copy prompt"
                                        className="p-2 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg">
                                        <Copy size={14} />
                                    </button>
                                    <a href={`api/studio/dashboards/${selectedMeta.id}`} target="_blank" rel="noreferrer" title="Open standalone"
                                        className="p-2 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg">
                                        <Download size={14} />
                                    </a>
                                    <button onClick={() => onPinToggle(selectedMeta.id, selectedMeta.pinned)}
                                        title={selectedMeta.pinned ? 'Unpin' : 'Pin'}
                                        className={`p-2 rounded-lg ${selectedMeta.pinned ? 'text-amber-400 hover:bg-amber-500/10' : 'text-slate-400 hover:text-amber-300 hover:bg-slate-800'}`}>
                                        {selectedMeta.pinned ? <PinOff size={14} /> : <Pin size={14} />}
                                    </button>
                                    <button onClick={() => onDelete(selectedMeta.id)} title="Delete"
                                        disabled={selectedMeta.pinned}
                                        className="p-2 text-slate-400 hover:text-red-300 hover:bg-red-500/10 rounded-lg disabled:opacity-30 disabled:cursor-not-allowed">
                                        <Trash2 size={14} />
                                    </button>
                                </div>
                            </div>

                            {/* Iframe */}
                            <div className="flex-1 bg-slate-900 rounded-2xl border border-slate-800 shadow-2xl overflow-hidden min-h-0">
                                <iframe
                                    key={`${selectedMeta.id}-${iframeNonce}`}
                                    src={`api/studio/dashboards/${selectedMeta.id}`}
                                    className="w-full h-full border-none bg-slate-950"
                                    title={selectedMeta.title}
                                />
                            </div>

                            {/* Iterate bar */}
                            <div className="bg-slate-900 border border-slate-800 rounded-xl p-3 shadow-lg">
                                <div className="flex items-stretch gap-2">
                                    <div className="relative flex-1">
                                        <input
                                            type="text"
                                            value={iterateText}
                                            onChange={(e) => setIterateText(e.target.value)}
                                            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); onIterate(); } }}
                                            placeholder="Refine this dashboard… e.g. 'Make it darker and add a battery gauge'"
                                            className="w-full bg-slate-950 border border-slate-700 rounded-lg py-2 pl-10 pr-4 text-sm text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-blue-500 transition-all"
                                        />
                                        <GitBranch size={14} className="absolute left-3 top-2.5 text-slate-500" />
                                    </div>
                                    <button
                                        onClick={onIterate}
                                        disabled={busy || !iterateText.trim()}
                                        className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-800 disabled:text-slate-500 text-white rounded-lg text-sm font-medium transition-all shrink-0"
                                    >
                                        {busyKind === 'iterate' ? <Loader2 size={16} className="animate-spin" /> : <Wand2 size={16} />}
                                        Iterate
                                    </button>
                                </div>
                                {variationsForSelected.length > 1 && (
                                    <div className="mt-3 flex items-center gap-2 flex-wrap">
                                        <span className="text-[10px] uppercase tracking-wider text-slate-500">Variations:</span>
                                        {variationsForSelected.map((v, idx) => (
                                            <button
                                                key={v.id}
                                                onClick={() => { setSelected(v.id); setIframeNonce(n => n + 1); }}
                                                className={`text-xs px-2 py-1 rounded-md border transition-colors ${v.id === selected
                                                    ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-200'
                                                    : 'bg-slate-950/50 border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700'
                                                    }`}
                                            >
                                                #{idx + 1}
                                            </button>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </>
                    ) : (
                        <div className="flex-1 flex items-center justify-center bg-slate-900 border border-dashed border-slate-800 rounded-2xl">
                            <div className="text-center">
                                <Wand2 size={48} className="mx-auto text-slate-700 mb-4" />
                                <p className="text-slate-400 font-medium">Generate your first dashboard above</p>
                                <p className="text-slate-600 text-xs mt-1">Or pick "Variations" to get several at once</p>
                            </div>
                        </div>
                    )}
                </section>
            </div>
        </div>
    );
};

const ProviderSelector = ({ provider, onProvider, model, onModel }) => (
    <div className="flex items-center gap-2">
        <select
            value={provider}
            onChange={(e) => onProvider(e.target.value)}
            className="bg-slate-950 border border-slate-700 rounded-lg text-xs text-slate-300 px-2 py-1.5 focus:outline-none focus:border-purple-500"
            title="LLM provider (defaults to backend setting)"
        >
            <option value="">Default provider</option>
            <option value="ollama">Ollama</option>
            <option value="openai">OpenAI</option>
            <option value="github">GitHub Models</option>
            <option value="foundry">Foundry</option>
        </select>
        <input
            type="text"
            value={model}
            onChange={(e) => onModel(e.target.value)}
            placeholder="model (optional)"
            className="bg-slate-950 border border-slate-700 rounded-lg text-xs text-slate-300 px-2 py-1.5 w-36 focus:outline-none focus:border-purple-500 placeholder:text-slate-600"
        />
    </div>
);
