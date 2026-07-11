import React, { useState } from 'react';
import { Bot, Plus, Zap } from 'lucide-react';
import { AgentFactory } from './AgentFactory';
import { AgentGrid } from './AgentGrid';
import { TriggersPanel } from './TriggersPanel';

export function AutomationHub({ agents, suggestions, onAgentsChanged }) {
    const [tab, setTab] = useState('agents');
    const [factorySession, setFactorySession] = useState(0);
    const [factoryOpen, setFactoryOpen] = useState(false);

    const openFactory = () => {
        setFactorySession(value => value + 1);
        setFactoryOpen(true);
    };

    return (
        <div className="cp-page">
            <header className="cp-page-header">
                <div>
                    <div className="cp-eyebrow"><Zap size={14} /> Automation</div>
                    <h1>Agents and proactive routines</h1>
                    <p>Manage specialist coverage and the events that wake the deterministic reasoning kernel.</p>
                </div>
                {tab === 'agents' && (
                    <button className="cp-button cp-button--primary" type="button" onClick={openFactory}>
                        <Plus size={16} /> New agent
                    </button>
                )}
            </header>

            <div className="cp-segmented" role="tablist" aria-label="Automation sections">
                <button id="automation-tab-agents" type="button" role="tab" aria-selected={tab === 'agents'} aria-controls="automation-panel" className={tab === 'agents' ? 'is-active' : ''} onClick={() => setTab('agents')}>
                    <Bot size={15} /> Agents
                </button>
                <button id="automation-tab-triggers" type="button" role="tab" aria-selected={tab === 'triggers'} aria-controls="automation-panel" className={tab === 'triggers' ? 'is-active' : ''} onClick={() => setTab('triggers')}>
                    <Zap size={15} /> Triggers
                </button>
            </div>

            <div id="automation-panel" role="tabpanel" aria-labelledby={`automation-tab-${tab}`}>
                {tab === 'agents' ? (
                    <AgentGrid
                        agents={agents}
                        suggestions={suggestions}
                        onAgentCreate={openFactory}
                        onSuggestionClick={openFactory}
                    />
                ) : <TriggersPanel />}
            </div>

            {factoryOpen && (
                <AgentFactory
                    key={factorySession}
                    startOpen
                    launcher={false}
                    onDismiss={() => setFactoryOpen(false)}
                    onAgentCreated={() => {
                        setFactoryOpen(false);
                        onAgentsChanged?.();
                    }}
                />
            )}
        </div>
    );
}
