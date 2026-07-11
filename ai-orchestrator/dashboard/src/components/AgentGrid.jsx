import React, { useState } from 'react';
import {
    Activity,
    Bot,
    Clock3,
    Cpu,
    Lightbulb,
    Plus,
    Shield,
    Thermometer,
    Zap,
} from 'lucide-react';
import AgentDetails from './AgentDetails';

const iconFor = agentId => {
    if (agentId === 'heating') return Thermometer;
    if (agentId === 'cooling') return Zap;
    if (agentId === 'lighting') return Lightbulb;
    if (agentId === 'security') return Shield;
    return Cpu;
};

const formatTime = value => {
    if (!value) return 'No decisions yet';
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? 'Unknown' : date.toLocaleString([], { dateStyle: 'short', timeStyle: 'short' });
};

const statusTone = status => {
    if (status === 'error') return 'is-danger';
    if (status === 'deciding') return 'is-active';
    if (status === 'connected' || status === 'ready') return 'is-success';
    return '';
};

export const AgentGrid = ({ agents = [], onAgentCreate }) => {
    const [selectedAgent, setSelectedAgent] = useState(null);

    return (
        <>
            <section className="cp-card">
                <div className="cp-section-heading">
                    <div><span className="cp-eyebrow">Specialist coverage</span><h2>Configured agents</h2></div>
                    <span className="cp-pill">{agents.length} total</span>
                </div>

                {agents.length === 0 ? (
                    <div className="cp-empty-state">
                        <Activity size={26} />
                        <div><strong>No specialist agents are active</strong><span>Create an agent or check the persistent configuration.</span></div>
                        <button className="cp-button cp-button--primary" type="button" onClick={onAgentCreate}><Plus size={15} /> New agent</button>
                    </div>
                ) : (
                    <div className="cp-agent-grid">
                        {agents.map(agent => {
                            const Icon = iconFor(agent.agent_id);
                            return (
                                <button className="cp-agent-card" type="button" key={agent.agent_id} onClick={() => setSelectedAgent(agent)}>
                                    <span className="cp-agent-icon"><Icon size={19} /></span>
                                    <span className="cp-agent-card-title">
                                        <strong>{agent.name || agent.agent_id}</strong>
                                        <small><span className={`cp-status-dot ${statusTone(agent.status)}`} /> {agent.status || 'idle'}</small>
                                    </span>
                                    <span className="cp-pill">{String(agent.model || 'local').split(':')[0]}</span>
                                    <span className="cp-agent-card-meta"><Clock3 size={13} /> Last decision: {formatTime(agent.last_decision)}</span>
                                    <span className="cp-agent-card-note"><Bot size={13} /> {agent.status === 'deciding' ? 'Evaluating current state…' : 'Ready for the next event'}</span>
                                </button>
                            );
                        })}
                        <button className="cp-add-card" type="button" onClick={onAgentCreate}>
                            <span><Plus size={20} /></span>
                            <strong>Create a specialist</strong>
                            <small>Describe the responsibility; review the generated blueprint.</small>
                        </button>
                    </div>
                )}
            </section>

            {selectedAgent && (
                <AgentDetails
                    agent={selectedAgent}
                    onClose={() => setSelectedAgent(null)}
                    onDelete={() => setSelectedAgent(null)}
                />
            )}
        </>
    );
};
