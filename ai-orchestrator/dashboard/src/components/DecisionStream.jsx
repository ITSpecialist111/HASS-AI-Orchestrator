
import React, { useState } from 'react';
import { Terminal, Filter, Clock, ChevronDown, ChevronRight, Brain } from 'lucide-react';

export function DecisionStream({ decisions }) {
    const [showHeartbeats, setShowHeartbeats] = useState(false);
    const [expandedRow, setExpandedRow] = useState(null);

    // Filter decisions based on "No Action" if heartbeats toggled off
    const filteredDecisions = decisions.filter(d => {
        if (showHeartbeats) return true;
        // Keep if there's an action OR if the result looks interesting (not just '-')
        // Also check if 'decision.actions' exists and is not empty (Phase 2 schema)
        const hasComplexAction = d.decision?.actions && d.decision.actions.length > 0;
        const hasSimpleAction = d.action && d.action !== 'No Action' && d.action !== 'None';
        return hasComplexAction || hasSimpleAction;
    });

    return (
        <div className="space-y-4">
            {/* Header / Filter Toolbar */}
            <div className="flex items-center justify-between mb-4">
                <div>
                    <h2 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
                        <Terminal size={20} className="text-blue-400" /> Decision Stream
                    </h2>
                    <p className="text-slate-500 text-sm">Real-time agent reasoning and execution logs</p>
                </div>

                <button
                    onClick={() => setShowHeartbeats(!showHeartbeats)}
                    className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium border transition-colors
            ${showHeartbeats
                            ? 'bg-blue-500/10 border-blue-500/30 text-blue-400'
                            : 'bg-slate-800/50 border-slate-700 text-slate-400 hover:text-slate-300'}`}
                >
                    <Filter size={14} />
                    {showHeartbeats ? 'Hiding Heartbeats' : 'Showing Heartbeats'}
                </button>
            </div>

            {/* Log Container */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
                {/* Table Header */}
                <div className="grid grid-cols-12 gap-4 px-4 py-3 bg-slate-900/80 border-b border-slate-800 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    <div className="col-span-1">Box</div> {/* Expand Toggle */}
                    <div className="col-span-2">Time</div>
                    <div className="col-span-2">Agent</div>
                    <div className="col-span-3">Reasoning</div>
                    <div className="col-span-2">Action</div>
                    <div className="col-span-2">Result</div>
                </div>

                {/* Table Body */}
                <div className="divide-y divide-slate-800/50">
                    {filteredDecisions.length === 0 ? (
                        <div className="p-8 text-center text-slate-500 text-sm">
                            No relevant decisions found. Waiting for agents...
                        </div>
                    ) : (
                        filteredDecisions.map((d, i) => {
                            const isExpanded = expandedRow === i;
                            const hasAction = (d.decision?.actions?.length > 0) || (d.action && d.action !== 'No Action');

                            return (
                                <div key={i} className={`group transition-colors ${hasAction ? 'bg-blue-500/5 hover:bg-blue-500/10' : 'hover:bg-slate-800/30'}`}>
                                    {/* Row Content */}
                                    <div
                                        className="grid grid-cols-12 gap-4 px-4 py-3 text-sm items-center cursor-pointer"
                                        onClick={() => setExpandedRow(isExpanded ? null : i)}
                                    >
                                        <div className="col-span-1 flex justify-center text-slate-600">
                                            {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                                        </div>

                                        <div className="col-span-2 font-mono text-xs text-slate-500 flex items-center gap-1">
                                            {new Date(d.timestamp).toLocaleTimeString()}
                                        </div>

                                        <div className="col-span-2">
                                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wide uppercase border
                         ${(d.agent_id || '').includes('security') ? 'bg-red-500/10 text-red-400 border-red-500/20' :
                                                    (d.agent_id || '').includes('heating') ? 'bg-orange-500/10 text-orange-400 border-orange-500/20' :
                                                        'bg-blue-500/10 text-blue-400 border-blue-500/20'
                                                }`}>
                                                {d.agent_id || 'Unknown'}
                                            </span>
                                        </div>

                                        <div className="col-span-3 text-slate-300 truncate font-medium flex items-center gap-1.5">
                                            {/* Try to extract reasoning or thought */}
                                            {d.reasoning ? (
                                                <>
                                                    <Brain size={12} className="text-purple-400" />
                                                    <span className="italic text-slate-400">{d.reasoning}</span>
                                                </>
                                            ) : (
                                                <span className="text-slate-600 italic">No reasoning logged</span>
                                            )}
                                        </div>

                                        <div className="col-span-2">
                                            {hasAction ? (
                                                <span className="text-blue-400 font-semibold">
                                                    {d.decision?.actions ? d.decision.actions.map(a => a.tool).join(', ') : d.action}
                                                </span>
                                            ) : (
                                                <span className="text-slate-600">Idle</span>
                                            )}
                                        </div>

                                        <div className="col-span-2 text-slate-500 font-mono text-xs truncate">
                                            {JSON.stringify(d.result || d.execution_results || '-')}
                                        </div>
                                    </div>

                                    {/* Expanded Details */}
                                    {isExpanded && (
                                        <div className="px-14 py-4 bg-slate-900/50 border-t border-slate-800 border-dashed">
                                            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Full Payload</h4>
                                            <pre className="text-xs font-mono text-slate-400 whitespace-pre-wrap break-all bg-slate-950 p-3 rounded-lg border border-slate-800 overflow-x-auto">
                                                {JSON.stringify(d, null, 2)}
                                            </pre>
                                        </div>
                                    )}
                                </div>
                            );
                        })
                    )}
                </div>
            </div>
        </div>
    );
}
