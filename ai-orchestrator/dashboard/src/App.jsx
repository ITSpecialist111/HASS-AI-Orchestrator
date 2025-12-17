import { useState, useEffect } from 'react'
import { Layout } from './components/Layout'
import { AgentGrid } from './components/AgentGrid'
import { AnalyticsCharts } from './components/AnalyticsCharts'
import { AgentFactory } from './components/AgentFactory'
import { DecisionStream } from './components/DecisionStream'
import { ChatAssistant } from './components/ChatAssistant'
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

    // ... (WebSocket code unchanged) ...

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

    // ... (fetchDecisions, fetchAnalytics unchanged) ...

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
                    initialBlueprint={pendingBlueprint}
                    onAgentCreated={() => {
                        fetchAgents()
                        setActiveTab('live') // Redirect to live view after creation
                    }}
                />
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
