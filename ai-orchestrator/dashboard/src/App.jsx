import { useState, useEffect } from 'react'
import { Layout } from './components/Layout'
import { AgentGrid } from './components/AgentGrid'
import { AnalyticsCharts } from './components/AnalyticsCharts'
import { AgentFactory } from './components/AgentFactory'
import { DecisionStream } from './components/DecisionStream'
import { ChatAssistant } from './components/ChatAssistant'
import { VisualDashboard } from './components/VisualDashboard'
import './index.css'

function App() {
    const [agents, setAgents] = useState([])
    const [decisions, setDecisions] = useState([])
    const [dailyStats, setDailyStats] = useState([])
    const [performance, setPerformance] = useState({})
    const [connected, setConnected] = useState(false)
    const [activeTab, setActiveTab] = useState('live') // 'live' | 'stream' | 'analytics' | 'factory'

    const [suggestions, setSuggestions] = useState([])
    const [pendingBlueprint, setPendingBlueprint] = useState(null)

    // Fetch initial data
    useEffect(() => {
        fetchAgents()
        fetchDecisions()
        fetchAnalytics()
        fetchSuggestions()
    }, [])

    // WebSocket connection
    useEffect(() => {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
        // Use relative path derivation for Ingress support
        const wsUrl = `${protocol}//${window.location.host}${window.location.pathname.replace(/\/$/, '')}/ws`
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
                    // Add new decision to top of list
                    setDecisions(prev => [msg.data, ...prev].slice(0, 50)) // Keep last 50
                    fetchAgents() // Update agent status/last action
                }
            } catch (e) {
                console.error("WS Parse Error", e)
            }
        }

        return () => websocket.close()
    }, [])

    const fetchSuggestions = async () => {
        try {
            const res = await fetch('api/factory/suggestions')
            if (res.ok) {
                const data = await res.json()
                if (Array.isArray(data)) setSuggestions(data)
            }
        } catch (e) { console.error("Fetch Suggestions Failed:", e) }
    }

    const fetchAgents = async () => {
        try {
            const res = await fetch('api/agents')
            if (!res.ok) throw new Error(`API Error ${res.status}: ${await res.text()}`)
            const data = await res.json()
            if (Array.isArray(data)) {
                setAgents(data)
            }
        } catch (e) { console.error("Fetch Agents Failed:", e) }
    }

    const fetchDecisions = async () => {
        try {
            const res = await fetch('api/decisions?limit=50')
            if (!res.ok) throw new Error(`API Error ${res.status}`)
            const data = await res.json()
            if (Array.isArray(data)) {
                setDecisions(data)
            }
        } catch (e) { console.error("Fetch Decisions Failed:", e) }
    }

    const fetchAnalytics = async () => {
        try {
            const [dailyRes, perfRes] = await Promise.all([
                fetch('api/stats/daily'),
                fetch('api/stats/performance')
            ])

            if (dailyRes.ok) {
                const d = await dailyRes.json()
                if (Array.isArray(d)) setDailyStats(d)
            }
            if (perfRes.ok) setPerformance(await perfRes.json())
        } catch (e) { console.error("Fetch Analytics Failed:", e) }
    }

    // Render active view
    const renderContent = () => {
        switch (activeTab) {
            case 'live':
                return (
                    <div className="space-y-6">
                        {/* High level status or summary could go here */}
                        <AgentGrid
                            agents={agents}
                            suggestions={suggestions}
                            onAgentCreate={() => {
                                setPendingBlueprint(null)
                                setActiveTab('factory')
                            }}
                            onSuggestionClick={(blueprint) => {
                                setPendingBlueprint(blueprint)
                                setActiveTab('factory')
                            }}
                        />
                    </div>
                )
            case 'stream':
                return <DecisionStream decisions={decisions} />
            case 'analytics':
                return <AnalyticsCharts dailyData={dailyStats} performanceData={performance} />
            case 'factory':
                return <AgentFactory
                    startOpen={true}
                    initialBlueprint={pendingBlueprint}
                    onAgentCreated={() => {
                        fetchAgents()
                        setActiveTab('live') // Redirect to live view after creation
                    }}
                />
            case 'visual':
                return <VisualDashboard />
            default:
                return <AgentGrid agents={agents} />
        }
    }

    return (
        <Layout
            activeTab={activeTab}
            onTabChange={setActiveTab}
            connected={connected}
        >
            {renderContent()}
            <ChatAssistant />
        </Layout>
    )
}

export default App
