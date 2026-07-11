import React, { useEffect, useRef, useState } from 'react';
import {
    ArrowRight,
    Brain,
    Loader2,
    MessageCircle,
    Send,
    ShieldCheck,
    Sparkles,
    X,
    Zap,
} from 'lucide-react';

const QUICK_GOALS = [
    'Give me a concise whole-home status',
    'Check whether any lights were left on unnecessarily',
    'Prepare a safe night routine for review',
];

export const ChatAssistant = ({ onOpenPlans }) => {
    const [open, setOpen] = useState(false);
    const [messages, setMessages] = useState([
        { role: 'assistant', content: 'Ask about the home or request an outcome. Guarded tools and approval policy apply here too.' },
    ]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [profile, setProfile] = useState('rapid');
    const endRef = useRef(null);
    const inputRef = useRef(null);

    useEffect(() => {
        endRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, loading]);

    useEffect(() => {
        if (open) inputRef.current?.focus();
    }, [open]);

    const send = async (text = input) => {
        const message = text.trim();
        if (!message || loading) return;
        setMessages(previous => [...previous, { role: 'user', content: message }]);
        setInput('');
        setLoading(true);
        setOpen(true);
        try {
            const response = await fetch('api/reasoning/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ goal: message, mode: 'auto', profile }),
            });
            if (!response.ok) throw new Error(`${response.status}: ${await response.text()}`);
            const data = await response.json();
            setMessages(previous => [...previous, {
                role: 'assistant',
                content: data.answer || 'The run completed without a written answer.',
                plan: data.plan,
                profile: data.profile,
                duration: data.duration_ms,
            }]);
        } catch (error) {
            setMessages(previous => [...previous, { role: 'error', content: `The goal could not run: ${error.message}` }]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <>
            <button className={`cp-chat-launcher ${open ? 'is-open' : ''}`} type="button" onClick={() => setOpen(value => !value)} aria-label={open ? 'Close assistant' : 'Open assistant'} aria-expanded={open}>
                {open ? <X size={21} /> : <MessageCircle size={22} />}
            </button>

            {open && (
                <section className="cp-chat" role="dialog" aria-label="Home assistant">
                    <header className="cp-chat-header">
                        <span className="cp-icon-tile"><Sparkles size={17} /></span>
                        <div><strong>Quick ask</strong><small>Deterministic tools enabled</small></div>
                        <div className="cp-chat-profile" role="group" aria-label="Chat reasoning profile">
                            <button type="button" className={profile === 'rapid' ? 'is-active' : ''} onClick={() => setProfile('rapid')}><Zap size={12} /> Rapid</button>
                            <button type="button" className={profile === 'balanced' ? 'is-active' : ''} onClick={() => setProfile('balanced')}><Brain size={12} /> Balanced</button>
                        </div>
                    </header>

                    <div className="cp-chat-messages" aria-live="polite">
                        {messages.map((message, index) => (
                            <div className={`cp-chat-message is-${message.role}`} key={index}>
                                <p>{message.content}</p>
                                {message.plan?.requires_approval && message.plan.status === 'pending' && (
                                    <button className="cp-chat-plan" type="button" onClick={onOpenPlans}>
                                        <ShieldCheck size={14} /> Exact plan needs review <ArrowRight size={13} />
                                    </button>
                                )}
                                {message.plan && !message.plan.requires_approval && (
                                    <span className="cp-chat-meta"><ShieldCheck size={12} /> Routine plan handled by policy · {message.profile}</span>
                                )}
                            </div>
                        ))}
                        {loading && <div className="cp-chat-message is-assistant is-loading"><Loader2 size={15} className="cp-spin" /> Running guarded {profile} goal…</div>}
                        <div ref={endRef} />
                    </div>

                    {messages.length === 1 && (
                        <div className="cp-chat-suggestions">
                            {QUICK_GOALS.map(goal => <button type="button" key={goal} onClick={() => send(goal)}>{goal}</button>)}
                        </div>
                    )}

                    <form className="cp-chat-form" onSubmit={event => { event.preventDefault(); send(); }}>
                        <label className="cp-sr-only" htmlFor="quick-ask">Ask the home</label>
                        <input ref={inputRef} id="quick-ask" value={input} onChange={event => setInput(event.target.value)} placeholder="Ask or request an outcome…" disabled={loading} />
                        <button type="submit" disabled={!input.trim() || loading} aria-label="Send goal"><Send size={16} /></button>
                    </form>
                </section>
            )}
        </>
    );
};
