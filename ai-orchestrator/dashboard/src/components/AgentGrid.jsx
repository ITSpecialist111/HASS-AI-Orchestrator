import React from 'react';
import { Cpu, Thermometer, Lightbulb, Shield, Zap, RefreshCw } from 'lucide-react';

const AgentCard = ({ agent }) => {
    const getIcon = (id) => {
        switch (id) {
            case 'heating': return <Thermometer className="text-orange-500" />;
            case 'cooling': return <Zap className="text-blue-500" />;
            case 'lighting': return <Lightbulb className="text-yellow-500" />;
            case 'security': return <Shield className="text-red-500" />;
            default: return <Cpu className="text-slate-400" />;
        }
    };

    const getStatusColor = (status) => {
        switch (status) {
            case 'deciding': return 'border-green-500 shadow-[0_0_15px_rgba(34,197,94,0.3)]';
            case 'idle': return 'border-slate-600';
            case 'error': return 'border-red-500';
            default: return 'border-slate-700';
        }
    };

    const isThinking = agent.status === 'deciding';

    return (
        <div className={`bg-slate-800 rounded-xl p-4 border transition-all duration-300 ${getStatusColor(agent.status)}`}>
            <div className="flex justify-between items-start mb-3">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-slate-900 rounded-lg">
                        {getIcon(agent.agent_id)}
                    </div>
                    <div>
                        <h3 className="font-semibold text-slate-100">{agent.name}</h3>
                        <p className="text-xs text-slate-400">{agent.model}</p>
                    </div>
                </div>
                {isThinking && (
                    <div className="flex items-center gap-1 text-green-400 text-xs animate-pulse">
                        <RefreshCw size={12} className="animate-spin" />
                        Thinking
                    </div>
                )}
            </div>

            <div className="space-y-2">
                <div className="flex justify-between text-sm">
                    <span className="text-slate-500">Status</span>
                    <span className={`capitalize ${isThinking ? 'text-green-400' : 'text-slate-300'}`}>
                        {agent.status}
                    </span>
                </div>

                <div className="flex justify-between text-sm">
                    <span className="text-slate-500">Last Action</span>
                    <span className="text-slate-300 text-xs max-w-[120px] truncate text-right">
                        {agent.last_decision ? new Date(agent.last_decision).toLocaleTimeString() : 'Never'}
                    </span>
                </div>
            </div>

            {/* Mini Activity Bar (Visual Flair) */}
            <div className="mt-4 flex gap-1 h-1">
                {[...Array(5)].map((_, i) => (
                    <div
                        key={i}
                        className={`flex-1 rounded-full ${Math.random() > 0.5 ? 'bg-slate-700' : 'bg-slate-800'}`}
                    />
                ))}
            </div>
        </div>
    );
};

export const AgentGrid = ({ agents }) => {
    if (!agents || agents.length === 0) return null;

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            {agents.map(agent => (
                <AgentCard key={agent.agent_id} agent={agent} />
            ))}
        </div>
    );
};
