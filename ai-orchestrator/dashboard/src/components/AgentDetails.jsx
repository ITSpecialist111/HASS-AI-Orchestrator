import React, { useState, useEffect } from 'react';
import { X, Play, Trash2, Edit2, Check, ExternalLink, Activity, Save } from 'lucide-react';

const AgentDetails = ({ agent, onClose, onDelete }) => {
    const [activeTab, setActiveTab] = useState('overview');
    const [decisions, setDecisions] = useState([]);
    const [isEditing, setIsEditing] = useState(false);
    const [instruction, setInstruction] = useState(agent?.instruction || "");
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (agent?.agent_id) {
            fetchDecisions();
            setInstruction(agent.instruction || ""); // Reset on agent change
        }
    }, [agent]);

    const fetchDecisions = async () => {
        try {
            const res = await fetch(`/api/decisions?agent_id=${agent.agent_id}&limit=20`);
            const data = await res.json();
            setDecisions(data);
        } catch (e) {
            console.error("Failed to fetch decisions", e);
        }
    };

    const handleUpdate = async () => {
        setLoading(true);
        try {
            const res = await fetch(`/api/factory/agents/${agent.agent_id}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ instruction: instruction })
            });

            if (res.ok) {
                setIsEditing(false);
                // Trigger generic refresh? Or optimistic update?
                // For now, let's just close edit mode and show success
            } else {
                alert("Failed to update agent");
            }
        } catch (e) {
            console.error(e);
            alert("Error updating agent");
        } finally {
            setLoading(false);
        }
    };

    // Delete Confirmation State
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

    const handleDeleteClick = () => {
        setShowDeleteConfirm(true);
    };

    const confirmDelete = async () => {
        setLoading(true);
        try {
            const res = await fetch(`/api/factory/agents/${agent.agent_id}`, {
                method: 'DELETE'
            });
            if (res.ok) {
                onDelete(agent.agent_id);
                onClose();
                // Optional: Force reload if parent doesn't handle list update
                window.location.reload();
            } else {
                alert("Failed to delete agent. Server returned error.");
            }
        } catch (e) {
            alert("Failed to delete agent. Check connection.");
        } finally {
            setLoading(false);
            setShowDeleteConfirm(false);
        }
    };

    if (!agent) return null;

    return (
        <div className="fixed inset-0 z-50 overflow-hidden">
            <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />

            <div className="absolute inset-y-0 right-0 w-full max-w-2xl bg-slate-900 border-l border-slate-700 shadow-2xl flex flex-col transform transition-transform duration-300">

                {/* Header */}
                <div className="p-6 border-b border-slate-700 flex justify-between items-start bg-slate-800/50">
                    <div>
                        <div className="flex items-center gap-3 mb-2">
                            <div className={`w-3 h-3 rounded-full ${agent.status === 'deciding' ? 'bg-green-500 animate-pulse' : 'bg-slate-500'}`} />
                            <h2 className="text-2xl font-bold text-white">{agent.name}</h2>
                            <span className="text-xs px-2 py-0.5 rounded bg-slate-700 text-slate-300 font-mono">{agent.model}</span>
                        </div>
                        <p className="text-slate-400 text-sm">ID: {agent.agent_id}</p>
                    </div>
                    <div className="flex gap-2">
                        <button
                            onClick={handleDeleteClick}
                            className="p-2 text-red-400 hover:bg-red-400/10 rounded-lg transition-colors"
                            title="Delete Agent"
                        >
                            <Trash2 size={20} />
                        </button>
                        <button
                            onClick={onClose}
                            className="p-2 text-slate-400 hover:bg-slate-700/50 rounded-lg transition-colors"
                        >
                            <X size={24} />
                        </button>
                    </div>
                </div>

                {/* Delete Confirmation Overlay */}
                {showDeleteConfirm && (
                    <div className="absolute inset-0 z-10 bg-slate-900/90 flex items-center justify-center p-6 backdrop-blur-sm">
                        <div className="bg-slate-800 border border-red-500/30 rounded-xl p-6 max-w-sm w-full shadow-2xl">
                            <div className="flex flex-col items-center text-center">
                                <div className="w-12 h-12 rounded-full bg-red-500/20 text-red-500 flex items-center justify-center mb-4">
                                    <Trash2 size={24} />
                                </div>
                                <h3 className="text-xl font-bold text-white mb-2">Delete Agent?</h3>
                                <p className="text-slate-400 mb-6">
                                    Are you sure you want to permanently delete <strong>{agent.name}</strong>? This action cannot be undone.
                                </p>
                                <div className="flex gap-3 w-full">
                                    <button
                                        onClick={() => setShowDeleteConfirm(false)}
                                        className="flex-1 py-2 px-4 rounded-lg bg-slate-700 text-slate-200 hover:bg-slate-600 border border-slate-600 transition-colors font-medium"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        onClick={confirmDelete}
                                        disabled={loading}
                                        className="flex-1 py-2 px-4 rounded-lg bg-red-500 text-white hover:bg-red-600 transition-colors font-medium flex items-center justify-center gap-2"
                                    >
                                        {loading ? 'Deleting...' : 'Delete Forever'}
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
                {/* Tabs */}
                <div className="flex border-b border-slate-700 px-6">
                    <button
                        className={`py-4 px-4 text-sm font-medium border-b-2 transition-colors ${activeTab === 'overview' ? 'border-blue-500 text-blue-400' : 'border-transparent text-slate-400 hover:text-slate-200'}`}
                        onClick={() => setActiveTab('overview')}
                    >
                        Overview
                    </button>
                    <button
                        className={`py-4 px-4 text-sm font-medium border-b-2 transition-colors ${activeTab === 'history' ? 'border-blue-500 text-blue-400' : 'border-transparent text-slate-400 hover:text-slate-200'}`}
                        onClick={() => setActiveTab('history')}
                    >
                        History
                    </button>
                    <button
                        className={`py-4 px-4 text-sm font-medium border-b-2 transition-colors ${activeTab === 'json' ? 'border-blue-500 text-blue-400' : 'border-transparent text-slate-400 hover:text-slate-200'}`}
                        onClick={() => setActiveTab('json')}
                    >
                        Config (JSON)
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6">

                    {activeTab === 'overview' && (
                        <div className="space-y-8">
                            {/* Instructions Section */}
                            <div className="bg-slate-800/50 rounded-xl p-5 border border-slate-700/50">
                                <div className="flex justify-between items-center mb-4">
                                    <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                                        <Activity size={18} className="text-blue-400" /> Primary Instruction
                                    </h3>
                                    {!isEditing ? (
                                        <button
                                            onClick={() => setIsEditing(true)}
                                            className="text-xs flex items-center gap-1 text-slate-400 hover:text-white bg-slate-700/50 px-2 py-1 rounded transition-colors"
                                        >
                                            <Edit2 size={12} /> Edit
                                        </button>
                                    ) : (
                                        <div className="flex gap-2">
                                            <button
                                                onClick={() => setIsEditing(false)}
                                                className="text-xs text-slate-400 hover:text-white"
                                            >
                                                Cancel
                                            </button>
                                            <button
                                                onClick={handleUpdate}
                                                disabled={loading}
                                                className="text-xs flex items-center gap-1 text-green-400 hover:text-green-300 bg-green-400/10 px-2 py-1 rounded transition-colors"
                                            >
                                                <Save size={12} /> {loading ? 'Saving...' : 'Save'}
                                            </button>
                                        </div>
                                    )}
                                </div>

                                {isEditing ? (
                                    <textarea
                                        value={instruction}
                                        onChange={(e) => setInstruction(e.target.value)}
                                        className="w-full h-48 bg-slate-900/50 border border-slate-600 rounded-lg p-3 text-slate-200 focus:outline-none focus:border-blue-500 font-mono text-sm leading-relaxed"
                                    />
                                ) : (
                                    <div className="prose prose-invert max-w-none text-slate-300 text-sm whitespace-pre-wrap font-mono bg-slate-900/30 p-4 rounded-lg border border-slate-700/30">
                                        {agent.instruction || instruction}
                                    </div>
                                )}
                            </div>

                            {/* Entities Section */}
                            <div>
                                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                                    <ExternalLink size={18} className="text-purple-400" /> Assigned Entities
                                </h3>
                                {/* We don't have the entity list from GET /agents yet, only from Config or by inference. 
                             Backend update needed to return entities in AgentStatus if we want to show them here accurately.
                             For now, rely on what might be passed or show specific fallback.
                          */}
                                <div className="bg-slate-800/30 rounded-lg p-4 border border-slate-700/50 text-slate-400 text-sm italic text-center">
                                    Entity list is managed dynamically or via backend config.
                                    (Visual entity list coming in v0.9)
                                </div>
                            </div>
                        </div>
                    )}

                    {activeTab === 'history' && (
                        <div className="space-y-4">
                            {decisions.length === 0 ? (
                                <div className="text-center text-slate-500 py-10">No recent history found.</div>
                            ) : (
                                decisions.map((decision, idx) => (
                                    <div key={idx} className="bg-slate-800/40 p-4 rounded-lg border border-slate-700/50 text-sm">
                                        <div className="flex justify-between text-xs text-slate-500 mb-2">
                                            <span>{new Date(decision.timestamp).toLocaleTimeString()}</span>
                                            <span className={decision.dry_run ? 'text-amber-500' : 'text-slate-500'}>
                                                {decision.dry_run ? 'DRY RUN' : 'LIVE'}
                                            </span>
                                        </div>
                                        <div className="text-slate-300 mb-2 font-medium">
                                            {decision.reasoning || "No reasoning provided."}
                                        </div>
                                        {decision.action && (
                                            <div className="bg-black/20 p-2 rounded text-xs font-mono text-blue-300">
                                                {decision.action}
                                            </div>
                                        )}
                                    </div>
                                ))
                            )}
                        </div>
                    )}

                    {activeTab === 'json' && (
                        <pre className="text-xs font-mono text-slate-400 bg-black/30 p-4 rounded-lg overflow-x-auto">
                            {JSON.stringify(agent, null, 2)}
                        </pre>
                    )}

                </div>
            </div>
        </div>
    );
};

export default AgentDetails;
