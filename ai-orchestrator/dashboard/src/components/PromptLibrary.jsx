import React, { useEffect, useState } from 'react';
import {
    AlertCircle,
    CheckCircle2,
    ChevronDown,
    ChevronRight,
    Loader2,
    Play,
    Sparkles,
} from 'lucide-react';

export function PromptLibrary({ defaultProfile = 'balanced', onResult }) {
    const [prompts, setPrompts] = useState([]);
    const [externalConnected, setExternalConnected] = useState(false);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [expanded, setExpanded] = useState(null);
    const [args, setArgs] = useState({});
    const [running, setRunning] = useState(null);
    const [results, setResults] = useState({});

    useEffect(() => {
        let cancelled = false;
        fetch('api/reasoning/prompts')
            .then(response => {
                if (!response.ok) throw new Error(`${response.status}: ${response.statusText}`);
                return response.json();
            })
            .then(data => {
                if (cancelled) return;
                setPrompts(data.prompts || []);
                setExternalConnected(!!data.external_connected);
                setLoading(false);
            })
            .catch(err => {
                if (cancelled) return;
                setError(err.message);
                setLoading(false);
            });
        return () => { cancelled = true; };
    }, []);

    const updateArg = (promptName, argName, value) => {
        setArgs(previous => ({
            ...previous,
            [promptName]: { ...(previous[promptName] || {}), [argName]: value },
        }));
    };

    const runPrompt = async prompt => {
        setRunning(prompt.name);
        setResults(previous => ({ ...previous, [prompt.name]: null }));
        try {
            const response = await fetch(`api/reasoning/prompts/${encodeURIComponent(prompt.name)}/run`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    arguments: args[prompt.name] || {},
                    mode: 'auto',
                    profile: defaultProfile,
                }),
            });
            if (!response.ok) throw new Error(`${response.status}: ${await response.text()}`);
            const data = await response.json();
            setResults(previous => ({ ...previous, [prompt.name]: data }));
            onResult?.(data);
        } catch (err) {
            setResults(previous => ({ ...previous, [prompt.name]: { error: err.message } }));
        } finally {
            setRunning(null);
        }
    };

    return (
        <section className="cp-workflow-library" aria-labelledby="workflow-heading">
            <div className="cp-section-heading">
                <div><span className="cp-eyebrow"><Sparkles size={13} /> Reusable goals</span><h2 id="workflow-heading">Workflow library</h2></div>
                <span className="cp-pill">{prompts.length} available</span>
            </div>
            <p className="cp-section-intro">Run a curated workflow with the currently selected {defaultProfile} profile. Native workflows work without an external MCP server.</p>

            {!externalConnected && prompts.some(prompt => prompt.source === 'external') && (
                <div className="cp-alert is-warning"><AlertCircle size={15} /> External workflows are temporarily unavailable; native workflows remain ready.</div>
            )}
            {error && <div className="cp-alert is-danger"><AlertCircle size={15} /> {error}</div>}
            {loading && <div className="cp-empty-state cp-empty-state--compact"><Loader2 size={18} className="cp-spin" /> Loading workflows…</div>}
            {!loading && !prompts.length && <div className="cp-empty-state cp-empty-state--compact">No workflows are configured.</div>}

            <div className="cp-workflow-grid">
                {prompts.map(prompt => {
                    const open = expanded === prompt.name;
                    const active = running === prompt.name;
                    const result = results[prompt.name];
                    return (
                        <article className="cp-workflow-card" key={prompt.name}>
                            <button className="cp-workflow-summary" type="button" onClick={() => setExpanded(open ? null : prompt.name)} aria-expanded={open}>
                                <span className="cp-icon-tile"><Sparkles size={16} /></span>
                                <span><strong>{prompt.title || prompt.name.replaceAll('_', ' ')}</strong><small>{prompt.description || 'Curated home workflow'}</small></span>
                                <span className="cp-pill">{prompt.source || 'native'}</span>
                                {open ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
                            </button>
                            {open && (
                                <div className="cp-workflow-detail">
                                    {(prompt.arguments || []).map(argument => (
                                        <label className="cp-field" key={argument.name}>
                                            <span>{argument.name}{argument.required ? ' *' : ''}</span>
                                            <input
                                                type="text"
                                                value={(args[prompt.name] || {})[argument.name] || ''}
                                                onChange={event => updateArg(prompt.name, argument.name, event.target.value)}
                                                placeholder={argument.description || ''}
                                                required={argument.required}
                                            />
                                        </label>
                                    ))}
                                    <button className="cp-button cp-button--primary" type="button" onClick={() => runPrompt(prompt)} disabled={active}>
                                        {active ? <Loader2 size={14} className="cp-spin" /> : <Play size={14} />}
                                        {active ? 'Running workflow' : `Run ${defaultProfile}`}
                                    </button>
                                    {result?.error && <div className="cp-alert is-danger"><AlertCircle size={14} /> {result.error}</div>}
                                    {result && !result.error && (
                                        <div className="cp-workflow-result">
                                            <CheckCircle2 size={16} />
                                            <div><strong>{result.plan?.requires_approval ? 'Plan ready for review' : 'Workflow complete'}</strong><p>{result.answer}</p></div>
                                        </div>
                                    )}
                                </div>
                            )}
                        </article>
                    );
                })}
            </div>
        </section>
    );
}
