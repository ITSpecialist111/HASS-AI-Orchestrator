import React, { useState, useRef, useEffect } from 'react';
import { MessageCircle, X, Send, Sparkles, Zap, Command, ChevronRight, Activity } from 'lucide-react';

export const ChatAssistant = () => {
    const [isOpen, setIsOpen] = useState(false);
    const [messages, setMessages] = useState([
        { role: 'system', content: 'Hello! I am your AI Orchestrator. How can I help you today?' }
    ]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const messagesEndRef = useRef(null);
    const [showQuickActions, setShowQuickActions] = useState(false);

    // Auto-scroll to bottom
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    const handleSend = async (text = input) => {
        if (!text.trim()) return;

        // Add User Message
        const userMsg = { role: 'user', content: text };
        setMessages(prev => [...prev, userMsg]);
        setInput('');
        setLoading(true);
        setIsOpen(true); // Ensure open if triggered via quick action

        try {
            const res = await fetch('api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            });

            const data = await res.json();

            // Add AI Response
            const aiMsg = {
                role: 'assistant',
                content: data.response,
                actions: data.actions_executed
            };
            setMessages(prev => [...prev, aiMsg]);

        } catch (e) {
            setMessages(prev => [...prev, { role: 'error', content: "Sorry, I couldn't reach the orchestrator." }]);
        } finally {
            setLoading(false);
        }
    };

    const QuickAction = ({ icon: Icon, label, query }) => (
        <button
            onClick={(e) => {
                e.stopPropagation();
                handleSend(query);
            }}
            className="flex items-center gap-3 w-full p-2 hover:bg-slate-700/50 rounded-lg transition-colors group text-left"
        >
            <div className="p-2 bg-slate-800 rounded-lg group-hover:bg-blue-500/20 group-hover:text-blue-400 transition-colors text-slate-400">
                <Icon size={16} />
            </div>
            <span className="text-sm text-slate-300 group-hover:text-white transition-colors">{label}</span>
            <ChevronRight size={14} className="ml-auto text-slate-600 group-hover:text-blue-400 opacity-0 group-hover:opacity-100 transition-all" />
        </button>
    );

    return (
        <>
            {/* Floating Buttion & Quick Actions Container */}
            <div className="fixed bottom-24 right-8 z-50 flex flex-col items-end gap-4">
                {/* Quick Actions Menu (Fade in on hover) */}
                <div className={`
                    bg-slate-900/90 backdrop-blur-md border border-slate-700 p-2 rounded-xl shadow-2xl mb-2 min-w-[240px]
                    transition-all duration-300 origin-bottom-right
                    ${showQuickActions && !isOpen ? 'opacity-100 scale-100 translate-y-0' : 'opacity-0 scale-95 translate-y-4 pointer-events-none'}
                `}>
                    <div className="px-3 py-2 text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">Quick Actions</div>
                    <QuickAction icon={Zap} label="Turn off all lights" query="Turn off all lights in the house" />
                    <QuickAction icon={Shield} label="Arm Security System" query="Arm the security system" />
                    <QuickAction icon={Activity} label="System Status" query="What is the current status of the house?" />
                    <QuickAction icon={Thermometer} label="Optimize Heating" query="Set heating to 20C everywhere" />
                    <QuickAction icon={Server} label="Visual Dashboard" query="Generate a visual dashboard for my house" />
                </div>

                <button
                    onClick={() => setIsOpen(!isOpen)}
                    onMouseEnter={() => setShowQuickActions(true)}
                    onMouseLeave={() => setShowQuickActions(false)}
                    className={`
                        w-14 h-14 rounded-full shadow-lg flex items-center justify-center transition-all duration-300
                        ${isOpen ? 'bg-slate-800 rotate-90 text-slate-400' : 'bg-blue-600 hover:bg-blue-500 text-white animate-pulse-slow'}
                    `}
                >
                    {isOpen ? <X size={24} /> : <MessageCircle size={28} />}
                </button>
            </div>

            {/* Chat Interface */}
            {isOpen && (
                <div className="fixed bottom-24 right-6 w-96 max-w-[calc(100vw-3rem)] h-[600px] max-h-[calc(100vh-8rem)] bg-slate-900/95 backdrop-blur-xl border border-slate-700 rounded-2xl shadow-2xl flex flex-col overflow-hidden z-40 animate-in slide-in-from-bottom-10 fade-in duration-300">

                    {/* Header */}
                    <div className="p-4 border-b border-slate-700/50 bg-slate-800/30 flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                            <Sparkles size={16} className="text-white" />
                        </div>
                        <div>
                            <h3 className="font-bold text-slate-100">AI Assistant</h3>
                            <div className="flex items-center gap-1.5">
                                <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                                <span className="text-xs text-slate-400">Online • Orchestrator</span>
                            </div>
                        </div>
                    </div>

                    {/* Messages */}
                    <div className="flex-1 overflow-y-auto p-4 space-y-4">
                        {messages.map((msg, idx) => (
                            <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                <div className={`
                                    max-w-[85%] rounded-2xl p-3 text-sm leading-relaxed
                                    ${msg.role === 'user'
                                        ? 'bg-blue-600 text-white rounded-tr-sm'
                                        : 'bg-slate-800 text-slate-200 border border-slate-700 rounded-tl-sm'}
                                `}>
                                    <p className="whitespace-pre-wrap">{msg.content}</p>

                                    {/* Action Results */}
                                    {msg.actions && msg.actions.length > 0 && (
                                        <div className="mt-3 pt-3 border-t border-slate-700/50 space-y-2">
                                            <div className="text-xs font-bold text-slate-500 uppercase flex items-center gap-1">
                                                <Command size={10} /> Executed Actions
                                            </div>
                                            {msg.actions.map((action, i) => (
                                                <div key={i} className="bg-black/20 rounded p-2 text-xs font-mono text-green-400 border border-slate-700/50 break-all">
                                                    ✓ {action.tool || "Action"}
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}
                        {loading && (
                            <div className="flex justify-start">
                                <div className="bg-slate-800 rounded-2xl p-4 border border-slate-700 rounded-tl-sm flex gap-1">
                                    <span className="w-2 h-2 bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                                    <span className="w-2 h-2 bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                                    <span className="w-2 h-2 bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
                                </div>
                            </div>
                        )}
                        <div ref={messagesEndRef} />
                    </div>

                    {/* Input */}
                    <div className="p-4 border-t border-slate-700/50 bg-slate-800/30">
                        <form
                            onSubmit={(e) => { e.preventDefault(); handleSend(); }}
                            className="relative"
                        >
                            <input
                                type="text"
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                placeholder="Ask me anything..."
                                className="w-full bg-slate-950 border border-slate-700 rounded-xl py-3 pl-4 pr-12 text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all font-sans"
                            />
                            <button
                                type="submit"
                                disabled={!input.trim() || loading}
                                className="absolute right-2 top-2 p-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-500 disabled:opacity-50 disabled:hover:bg-blue-600 transition-colors"
                            >
                                <Send size={16} />
                            </button>
                        </form>
                    </div>
                </div>
            )}
        </>
    );
};

// Icon imports need to be comprehensive
import { Shield, Thermometer, Server } from 'lucide-react';
