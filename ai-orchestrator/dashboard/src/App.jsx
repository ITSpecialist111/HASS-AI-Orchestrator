import { useState, useEffect } from 'react'
import { LayoutDashboard, BarChart3, Settings } from 'lucide-react'
import { AgentGrid } from './components/AgentGrid'
import { AnalyticsCharts } from './components/AnalyticsCharts'
import { KnowledgeVisualizer } from './components/KnowledgeVisualizer'
import { AgentFactory } from './components/AgentFactory'
import './index.css'

function App() {
    const [agents, setAgents] = useState([])
    const [decisions, setDecisions] = useState([])
    const [dailyStats, setDailyStats] = useState([])
    const [performance, setPerformance] = useState({})
    const [lastRetrieval, setLastRetrieval] = useState(null)
    const [connected, setConnected] = useState(false)
    const [activeTab, setActiveTab] = useState('live')

    // Fetch initial data
    useEffect(() => {
        fetchAgents()
        fetchDecisions()
        fetchAnalytics()
    }, [])

    // WebSocket connection
    useEffect(() => {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
        const wsUrl = `${protocol}//${window.location.host}/ws`
        const websocket = new WebSocket(wsUrl)

        websocket.onopen = () => setConnected(true)
        websocket.onclose = () => setConnected(false)

        websocket.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data)

                if (msg.type === 'status') {
                    // Initial status, maybe reload agents
                    fetchAgents()
                } else if (msg.type === 'agent_update') {
                    // Update single agent status in list
                    setAgents(prev => prev.map(a =>
                        a.agent_id === msg.data.agent_id ? { ...a, ...msg.data } : a
                    ))
                } else if (msg.type === 'decision') {
                    setDecisions(prev => [msg.data, ...prev.slice(0, 19)])
                    // Refresh analytics occasionally or simply increment local counter?
                    // For now, re-fetch implies accurate but chatty. Let's just re-fetch agents to update "last action"
                    fetchAgents()
                } else if (msg.type === 'knowledge_retrieval') {
                    setLastRetrieval({
                        ...msg.data,
                        timestamp: new Date().toISOString()
                    })
                }
            } catch (e) {
                console.error("WS Parse Error", e)
            }
        }

        return () => websocket.close()
    }, [])

    const fetchAgents = async () => {
        try {
            const res = await fetch('/api/agents')
            const data = await res.json()
            setAgents(data)
        } catch (e) { console.error(e) }
    }

    const fetchDecisions = async () => {
        try {
            const res = await fetch('/api/decisions?limit=20')
            const data = await res.json()
            setDecisions(data)
        } catch (e) { console.error(e) }
    }

    const fetchAnalytics = async () => {
        try {
            const [dailyRes, perfRes] = await Promise.all([
                fetch('/api/stats/daily'),
                fetch('/api/stats/performance')
            ])
            setDailyStats(await dailyRes.json())
            setPerformance(await perfRes.json())
        } catch (e) { console.error(e) }
    }

    return (
        <div className="min-h-screen bg-slate-950 text-slate-200 font-sans selection:bg-purple-500/30">
            {/* Header */}
            <header className="bg-slate-900/50 backdrop-blur border-b border-slate-800 sticky top-0 z-50">
                <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="bg-gradient-to-br from-purple-600 to-blue-600 w-8 h-8 rounded-lg flex items-center justify-center font-bold text-white shadow-lg shadow-purple-900/20">
                            AI
                        </div>
                        <h1 className="font-bold text-xl tracking-tight text-slate-100">
                            Orchestrator <span className="text-slate-500 font-normal">Command</span>
                        </h1>
                    </div>

                    <div className="flex items-center gap-4">
                        <div className={`flex items-center gap-2 text-xs px-3 py-1.5 rounded-full border ${connected ? 'border-green-500/30 bg-green-500/10 text-green-400' : 'border-red-500/30 bg-red-500/10 text-red-400'}`}>
                            <div className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`} />
                            {connected ? 'System Online' : 'disconnected'}
                        </div>
                    </div>
                </div>
            </header>

            <main className="max-w-7xl mx-auto px-4 py-8">
                {/* Knowledge Visualization (RAG Feedback) */}
                <KnowledgeVisualizer lastRetrieval={lastRetrieval} />

                {/* Tabs */}
                <div className="flex gap-4 mb-6 border-b border-slate-800">
                    <button
                        onClick={() => setActiveTab('live')}
                        className={`pb-3 flex items-center gap-2 text-sm font-medium transition-colors ${activeTab === 'live' ? 'text-purple-400 border-b-2 border-purple-400' : 'text-slate-500 hover:text-slate-300'}`}
                    >
                        <LayoutDashboard size={16} /> Live Ops
                    </button>
                    <button
                        onClick={() => setActiveTab('analytics')}
                        className={`pb-3 flex items-center gap-2 text-sm font-medium transition-colors ${activeTab === 'analytics' ? 'text-purple-400 border-b-2 border-purple-400' : 'text-slate-500 hover:text-slate-300'}`}
                    >
                        <BarChart3 size={16} /> Analytics
                    </button>
                </div>

                {activeTab === 'live' ? (
                    <>
                        {/* Live Agent Grid */}
                        <AgentGrid agents={agents} />

                        {/* Recent Decisions Table */}
                        <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
                            <div className="p-4 border-b border-slate-700 flex justify-between items-center">
                                <h3 className="font-semibold text-slate-200">Decision Stream</h3>
                                <span className="text-xs text-slate-500">Real-time</span>
                            </div>
                            <div className="overflow-x-auto">
                                <table className="w-full text-sm text-left">
                                    <thead className="text-xs text-slate-400 uppercase bg-slate-900/50">
                                        <tr>
                                            <th className="px-6 py-3">Time</th>
                                            <th className="px-6 py-3">Agent</th>
                                            <th className="px-6 py-3">Action</th>
                                            <th className="px-6 py-3">Result</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-slate-700">
                                        {decisions.map((d, i) => (
                                            <tr key={i} className="hover:bg-slate-700/30 transition-colors">
                                                <td className="px-6 py-4 font-mono text-xs text-slate-500">
                                                    {new Date(d.timestamp).toLocaleTimeString()}
                                                </td>
                                                <td className="px-6 py-4">
                                                    <span className={`px-2 py-1 rounded text-xs font-medium capitalize 
                                                        ${d.agent_id === 'security' ? 'bg-red-900/30 text-red-400' :
                                                            d.agent_id === 'heating' ? 'bg-orange-900/30 text-orange-400' :
                                                                'bg-blue-900/30 text-blue-400'}`}>
                                                        {d.agent_id}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4 text-slate-300">
                                                    {(() => {
                                                        // Handle Phase 1 'action' string vs Phase 2 'decision.actions'
                                                        if (d.decision?.actions?.length > 0) {
                                                            return d.decision.actions.map(a => a.tool).join(', ')
                                                        }
                                                        return d.action || 'No Action'
                                                    })()}
                                                </td>
                                                <td className="px-6 py-4 text-slate-400 max-w-xs truncate">
                                                    {JSON.stringify(d.result || d.execution_results || '-')}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </>
                ) : (
                    /* Analytics View */
                    <AnalyticsCharts dailyData={dailyStats} performanceData={performance} />
                )}
            </main>

            {/* Phase 6: Agent Factory (The Wizard) */}
            <AgentFactory onAgentCreated={() => {
                fetchAgents();
                // Optional: Trigger global refresh or show toast
            }} />
        </div>
    )
}

export default App
