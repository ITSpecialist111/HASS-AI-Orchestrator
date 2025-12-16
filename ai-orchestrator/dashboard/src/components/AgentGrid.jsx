
import React from 'react';
import { Cpu, Thermometer, Lightbulb, Shield, Zap, RefreshCw, Activity, Clock } from 'lucide-react';

const AgentCard = ({ agent, onClick }) => {
    const getIcon = (id) => {
        switch (id) {
            case 'heating': return <Thermometer size={20} className="text-orange-400" />;
            case 'cooling': return <Zap size={20} className="text-blue-400" />;
            case 'lighting': return <Lightbulb size={20} className="text-yellow-400" />;
            case 'security': return <Shield size={20} className="text-red-400" />;
            default: return <Cpu size={20} className="text-purple-400" />;
        }
    };

    const getStatusStyles = (status) => {
        switch (status) {
            case 'deciding':
                return {
                    border: 'border-green-500/50',
                    badge: 'bg-green-500/20 text-green-400 border-green-500/30',
                    indicator: 'bg-green-500 animate-pulse'
                };
            case 'error':
                return {
                    border: 'border-red-500/50',
                    badge: 'bg-red-500/20 text-red-400 border-red-500/30',
                    indicator: 'bg-red-500'
                };
            default:
                return {
                    border: 'border-slate-700 hover:border-slate-600',
                    badge: 'bg-slate-700/50 text-slate-400 border-slate-600',
                    indicator: 'bg-slate-600'
                };
        }
    };

    const styles = getStatusStyles(agent.status);
    const isThinking = agent.status === 'deciding';

    return (
        <div
            onClick={() => onClick(agent)}
            className={`relative bg-slate-900 rounded-xl p-5 border transition-all duration-300 group overflow-hidden cursor-pointer hover:shadow-lg hover:shadow-purple-500/10 ${styles.border}`}
        >
            {/* Background Tech Elements */}
            <div className="absolute top-0 right-0 p-2 opacity-5">
                <Activity size={100} />
            </div>

            {/* Header */}
            <div className="relative flex justify-between items-start mb-4">
                <div className="flex items-center gap-3">
                    <div className="p-2.5 bg-slate-800/80 rounded-lg border border-slate-700 shadow-sm">
                        {getIcon(agent.agent_id)}
                    </div>
                    <div>
                        <h3 className="font-bold text-slate-100 tracking-tight text-sm group-hover:text-blue-400 transition-colors">{agent.name}</h3>
                        <div className="flex items-center gap-1.5 mt-0.5">
                            <span className={`w-1.5 h-1.5 rounded-full ${styles.indicator}`}></span>
                            <span className="text-[10px] text-slate-400 uppercase font-semibold tracking-wider font-mono">{agent.status}</span>
                        </div>
                    </div>
                </div>

                {/* Model Badge */}
                <div className="px-2 py-1 rounded text-[10px] bg-slate-800 border border-slate-700 text-slate-500 font-mono">
                    {agent.model.split(':')[0]}
                </div>
            </div>

            {/* Vital Stats / Info */}
            <div className="relative space-y-3">
                {/* Last Decision Time */}
                <div className="flex items-center gap-2 text-xs text-slate-400 bg-slate-950/30 p-2 rounded border border-slate-800/50">
                    <Clock size={12} className="text-slate-600" />
                    <span className="font-medium">Last Action:</span>
                    <span className="font-mono text-slate-300 ml-auto">
                        {agent.last_decision ? new Date(agent.last_decision).toLocaleTimeString() : '--:--:--'}
                    </span>
                </div>

                {/* Last Thought Snippet (Placeholder or Real if available) */}
                <div className="text-xs text-slate-400 italic border-l-2 border-purple-500/20 pl-2 py-0.5">
                    {isThinking ? (
                        <span className="text-green-400 animate-pulse flex items-center gap-1">
                            <RefreshCw size={10} className="animate-spin" /> Analyzing environment...
                        </span>
                    ) : (
                        <span>Waiting for next cycle...</span>
                    )}
                </div>
            </div>

            {/* Active Sparkline (Visual) */}
            <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-slate-800">
                <div className={`h-full transition-all duration-700 ${isThinking ? 'w-full bg-green-500 shadow-[0_0_10px_rgba(34,197,94,0.5)]' : 'w-0 bg-slate-600'}`}></div>
            </div>
        </div>
    );
};

import AgentDetails from './AgentDetails';

export const AgentGrid = ({ agents, onAgentCreate }) => {
    const [selectedAgent, setSelectedAgent] = React.useState(null);

    const handleAgentClick = (agent) => {
        setSelectedAgent(agent);
    };

    const handleClose = () => setSelectedAgent(null);

    // Provide a way to refresh if deleted - currently simpler to just reload or wait for websocket update
    // But optimistic removal is handled below for UI feel
    const handleDelete = (id) => {
        // Here we could callback to parent to filter agents, but WebSocket should update state
        setSelectedAgent(null);
    };

    if (!agents || agents.length === 0) {
        return (
            <div className="text-center py-12 text-slate-500 border border-dashed border-slate-800 rounded-xl bg-slate-900/30">
                <Activity className="mx-auto mb-3 opacity-20" size={48} />
                <p>No agents active. Check connection.</p>
            </div>
        );
    }

    return (
        <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mb-6">
                {agents.map(agent => (
                    <AgentCard key={agent.agent_id} agent={agent} onClick={handleAgentClick} />
                ))}

                {/* Add New Agent Card Place holder/Button */}
                <div
                    onClick={onAgentCreate}
                    className="group border border-dashed border-slate-800 bg-slate-900/30 rounded-xl flex flex-col items-center justify-center p-6 cursor-pointer hover:bg-slate-800/50 hover:border-purple-500/30 transition-all min-h-[160px]"
                >
                    <div className="w-10 h-10 rounded-full bg-slate-800 flex items-center justify-center mb-3 group-hover:bg-purple-500/20 group-hover:text-purple-400 transition-colors">
                        <span className="text-xl">+</span>
                    </div>
                    <span className="text-sm font-medium text-slate-400 group-hover:text-slate-200">New Agent</span>
                </div>
            </div>

            {selectedAgent && (
                <AgentDetails
                    agent={selectedAgent}
                    onClose={handleClose}
                    onDelete={handleDelete}
                />
            )}
        </>
    );
};
