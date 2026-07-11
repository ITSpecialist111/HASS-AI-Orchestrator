import { lazy, Suspense, useCallback, useEffect, useMemo, useState } from 'react'
import { CircleAlert, X } from 'lucide-react'
import { Layout } from './components/Layout'
import { ChatAssistant } from './components/ChatAssistant'
import { HomeOverview } from './components/HomeOverview'
import './index.css'

const AutomationHub = lazy(() => import('./components/AutomationHub').then(m => ({ default: m.AutomationHub })))
const InsightsHub = lazy(() => import('./components/InsightsHub').then(m => ({ default: m.InsightsHub })))
const PlansPanel = lazy(() => import('./components/PlansPanel').then(m => ({ default: m.PlansPanel })))
const ReasoningPanel = lazy(() => import('./components/ReasoningPanel').then(m => ({ default: m.ReasoningPanel })))
const StudioHub = lazy(() => import('./components/StudioHub').then(m => ({ default: m.StudioHub })))

const VALID_VIEWS = new Set(['home', 'run', 'review', 'automation', 'insights', 'studio'])

const initialView = () => {
    const candidate = window.location.hash.replace('#', '')
    return VALID_VIEWS.has(candidate) ? candidate : 'home'
}

function App() {
    const [agents, setAgents] = useState([])
    const [decisions, setDecisions] = useState([])
    const [dailyStats, setDailyStats] = useState([])
    const [performance, setPerformance] = useState({})
    const [plans, setPlans] = useState([])
    const [plansLoading, setPlansLoading] = useState(true)
    const [plansError, setPlansError] = useState(null)
    const [reasoningInfo, setReasoningInfo] = useState(null)
    const [connected, setConnected] = useState(false)
    const [homeAssistantConnected, setHomeAssistantConnected] = useState(false)
    const [activeView, setActiveView] = useState(initialView)
    const [draftGoal, setDraftGoal] = useState('')
    const [suggestions, setSuggestions] = useState([])
    const [globalError, setGlobalError] = useState(null)

    const requestJson = useCallback(async (url) => {
        const response = await fetch(url)
        if (!response.ok) throw new Error(`${response.status} ${response.statusText}`)
        return response.json()
    }, [])

    const fetchSuggestions = useCallback(async () => {
        try {
            const data = await requestJson('api/factory/suggestions')
            if (Array.isArray(data)) setSuggestions(data)
        } catch (_) { setSuggestions([]) }
    }, [requestJson])

    const fetchAgents = useCallback(async () => {
        try {
            const data = await requestJson('api/agents')
            if (Array.isArray(data)) setAgents(data)
        } catch (error) { setGlobalError(`Agent status unavailable: ${error.message}`) }
    }, [requestJson])

    const fetchDecisions = useCallback(async () => {
        try {
            const data = await requestJson('api/decisions?limit=50')
            if (Array.isArray(data)) setDecisions(data)
        } catch (error) { setGlobalError(`Activity unavailable: ${error.message}`) }
    }, [requestJson])

    const fetchAnalytics = useCallback(async () => {
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
        } catch (_) { /* Insights can render an empty state. */ }
    }, [])

    const fetchPlans = useCallback(async () => {
        setPlansLoading(true)
        setPlansError(null)
        try {
            const data = await requestJson('api/reasoning/plans?limit=100')
            setPlans(Array.isArray(data.plans) ? data.plans : [])
        } catch (error) {
            setPlansError(`Plan queue unavailable: ${error.message}`)
        } finally {
            setPlansLoading(false)
        }
    }, [requestJson])

    const fetchReasoningInfo = useCallback(async () => {
        try {
            setReasoningInfo(await requestJson('api/reasoning/info'))
        } catch (_) { setReasoningInfo(null) }
    }, [requestJson])

    const fetchHealth = useCallback(async () => {
        try {
            const data = await requestJson('api/health')
            setHomeAssistantConnected(!!data.home_assistant?.connected)
        } catch (_) {
            setHomeAssistantConnected(false)
        }
    }, [requestJson])

    useEffect(() => {
        fetchAgents()
        fetchDecisions()
        fetchAnalytics()
        fetchSuggestions()
        fetchPlans()
        fetchReasoningInfo()
        fetchHealth()
    }, [fetchAgents, fetchAnalytics, fetchDecisions, fetchHealth, fetchPlans, fetchReasoningInfo, fetchSuggestions])

    useEffect(() => {
        const onHashChange = () => {
            const next = window.location.hash.replace('#', '')
            if (VALID_VIEWS.has(next)) setActiveView(next)
        }
        window.addEventListener('hashchange', onHashChange)
        return () => window.removeEventListener('hashchange', onHashChange)
    }, [])

    const navigate = useCallback((view) => {
        if (!VALID_VIEWS.has(view)) return
        setActiveView(view)
        window.history.replaceState(null, '', `#${view}`)
    }, [])

    useEffect(() => {
        let socket
        let reconnectTimer
        let disposed = false
        let reconnectDelay = 3000

        const connect = () => {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
            const wsUrl = `${protocol}//${window.location.host}${window.location.pathname.replace(/\/$/, '')}/ws`
            socket = new WebSocket(wsUrl)
            socket.onopen = () => {
                reconnectDelay = 3000
                setConnected(true)
            }
            socket.onclose = () => {
                setConnected(false)
                if (!disposed) {
                    reconnectTimer = window.setTimeout(connect, reconnectDelay)
                    reconnectDelay = Math.min(30000, Math.round(reconnectDelay * 1.7))
                }
            }
            socket.onerror = () => socket.close()
            socket.onmessage = event => {
                try {
                    const message = JSON.parse(event.data)
                    if (message.type === 'status') fetchAgents()
                    if (message.type === 'agent_update') {
                        setAgents(previous => previous.map(agent =>
                            agent.agent_id === message.data.agent_id ? { ...agent, ...message.data } : agent
                        ))
                    }
                    if (message.type === 'decision') {
                        setDecisions(previous => [message.data, ...previous].slice(0, 50))
                        fetchAgents()
                    }
                    if (message.type === 'reasoning_event' && message.data?.type === 'plan') fetchPlans()
                } catch (_) { /* Ignore malformed third-party WebSocket data. */ }
            }
        }

        connect()
        return () => {
            disposed = true
            window.clearTimeout(reconnectTimer)
            socket?.close()
        }
    }, [fetchAgents, fetchPlans])

    useEffect(() => {
        const timer = window.setInterval(fetchPlans, 15000)
        return () => window.clearInterval(timer)
    }, [fetchPlans])

    useEffect(() => {
        const timer = window.setInterval(fetchHealth, 10000)
        return () => window.clearInterval(timer)
    }, [fetchHealth])

    const pendingPlans = useMemo(
        () => plans.filter(plan => ['pending', 'approved', 'executing'].includes(plan.status)),
        [plans],
    )

    const startGoal = goal => {
        setDraftGoal(goal)
        navigate('run')
    }

    const renderContent = () => {
        switch (activeView) {
            case 'home':
                return <HomeOverview
                    agents={agents}
                    decisions={decisions}
                    pendingPlans={pendingPlans}
                    connected={connected && homeAssistantConnected}
                    reasoningInfo={reasoningInfo}
                    onStartGoal={startGoal}
                    onNavigate={navigate}
                />
            case 'run':
                return <ReasoningPanel
                    initialGoal={draftGoal}
                    onRunComplete={() => {
                        fetchPlans()
                        fetchDecisions()
                        setDraftGoal('')
                    }}
                    onOpenPlans={() => navigate('review')}
                />
            case 'review':
                return <PlansPanel
                    plans={plans}
                    loading={plansLoading}
                    error={plansError}
                    onRefresh={fetchPlans}
                    onPlanUpdated={fetchPlans}
                />
            case 'automation':
                return <AutomationHub agents={agents} suggestions={suggestions} onAgentsChanged={fetchAgents} />
            case 'insights':
                return <InsightsHub decisions={decisions} dailyStats={dailyStats} performance={performance} />
            case 'studio':
                return <StudioHub />
            default:
                return null
        }
    }

    return (
        <Layout
            activeView={activeView}
            onViewChange={navigate}
            connected={connected && homeAssistantConnected}
            pendingCount={pendingPlans.length}
        >
            {globalError && (
                <div className="cp-global-alert" role="alert">
                    <CircleAlert size={16} />
                    <span>{globalError}</span>
                    <button type="button" onClick={() => setGlobalError(null)} aria-label="Dismiss alert"><X size={15} /></button>
                </div>
            )}
            <Suspense fallback={(
                <div className="cp-empty-state">Loading workspace…</div>
            )}>
                {renderContent()}
            </Suspense>
            <ChatAssistant onOpenPlans={() => navigate('review')} />
        </Layout>
    )
}

export default App
