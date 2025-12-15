import React from 'react';
import { Brain, Database, FileText } from 'lucide-react';

export const KnowledgeVisualizer = ({ lastRetrieval }) => {
    // If no retrieval in last 10 seconds, show idle state
    const isRecent = lastRetrieval && (Date.now() - new Date(lastRetrieval.timestamp).getTime() < 10000);

    return (
        <div className="bg-slate-800 p-4 rounded-lg border border-slate-700 mb-6 relative overflow-hidden">
            {/* Background Pulse Effect when active */}
            {isRecent && (
                <div className="absolute inset-0 bg-purple-500/10 animate-pulse pointer-events-none" />
            )}

            <div className="flex items-center gap-3 mb-3 relative z-10">
                <div className={`p-2 rounded-lg transition-colors duration-500 ${isRecent ? 'bg-purple-600 text-white' : 'bg-slate-900 text-slate-500'}`}>
                    <Brain size={24} className={isRecent ? 'animate-bounce' : ''} />
                </div>
                <div>
                    <h3 className="text-lg font-semibold text-slate-200">Context Awareness</h3>
                    <p className="text-xs text-slate-400">
                        {isRecent ? 'Retrieving Knowledge...' : 'Monitoring Agent Memory'}
                    </p>
                </div>
            </div>

            {/* Visualization of Sources */}
            <div className="flex gap-4 mb-2 relative z-10">
                <div className={`flex items-center gap-2 text-xs px-3 py-1.5 rounded-full border ${isRecent ? 'border-purple-500/50 bg-purple-500/10 text-purple-200' : 'border-slate-700 text-slate-500'}`}>
                    <Database size={12} />
                    <span>Vector Store</span>
                </div>
                <div className={`flex items-center gap-2 text-xs px-3 py-1.5 rounded-full border ${isRecent ? 'border-blue-500/50 bg-blue-500/10 text-blue-200' : 'border-slate-700 text-slate-500'}`}>
                    <FileText size={12} />
                    <span>Manuals</span>
                </div>
            </div>

            {/* Last Retrieval Content */}
            {lastRetrieval && (
                <div className="mt-3 p-3 bg-slate-900/50 rounded border border-slate-700 text-xs font-mono text-slate-300 relative z-10">
                    <div className="flex justify-between items-center mb-1">
                        <span className="text-purple-400 font-bold">QUERY:</span>
                        <span className="text-slate-500">{new Date(lastRetrieval.timestamp).toLocaleTimeString()}</span>
                    </div>
                    <p className="truncate opacity-80 mb-2">"{lastRetrieval.query}"</p>

                    <div className="text-blue-400 font-bold mb-1">RETRIEVED:</div>
                    <div className="space-y-1">
                        {lastRetrieval.results.slice(0, 2).map((res, idx) => (
                            <p key={idx} className="truncate pl-2 border-l-2 border-slate-600">
                                {res.content}
                            </p>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};
