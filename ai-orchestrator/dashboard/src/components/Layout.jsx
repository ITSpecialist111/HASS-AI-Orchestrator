
import React, { useEffect, useState } from 'react';
import {
    BarChart3,
    Brain,
    CheckSquare,
    Home,
    Menu,
    Moon,
    Settings,
    Sun,
    Wand2,
    X,
    Zap,
} from 'lucide-react';
import { SettingsModal } from './SettingsModal';

const NAV_ITEMS = [
    { id: 'home', label: 'Home', hint: 'Status and priorities', icon: Home },
    { id: 'run', label: 'Ask & run', hint: 'Set a goal', icon: Brain },
    { id: 'review', label: 'Plans', hint: 'Review exact actions', icon: CheckSquare },
    { id: 'automation', label: 'Automation', hint: 'Agents and triggers', icon: Zap },
    { id: 'insights', label: 'Insights', hint: 'Activity and outcomes', icon: BarChart3 },
    { id: 'studio', label: 'Studio', hint: 'Human dashboards', icon: Wand2 },
];

export function Layout({
    children,
    activeView,
    onViewChange,
    connected,
    pendingCount = 0,
    version = 'v0.13.0',
}) {
    const [showSettings, setShowSettings] = useState(false);
    const [config, setConfig] = useState(null);
    const [appVersion, setAppVersion] = useState(version);
    const [mobileOpen, setMobileOpen] = useState(false);
    const [theme, setTheme] = useState(() => document.documentElement.dataset.theme || 'dark');

    useEffect(() => {
        fetch('api/config')
            .then(res => res.json())
            .then(data => {
                setConfig(data);
                if (data.version) setAppVersion(`v${data.version}`);
            })
            .catch(() => {});
    }, []);

    useEffect(() => {
        const closeOnEscape = event => {
            if (event.key === 'Escape') setMobileOpen(false);
        };
        window.addEventListener('keydown', closeOnEscape);
        return () => window.removeEventListener('keydown', closeOnEscape);
    }, []);

    const navigate = id => {
        onViewChange(id);
        setMobileOpen(false);
    };

    const toggleTheme = () => {
        const next = theme === 'dark' ? 'light' : 'dark';
        document.documentElement.dataset.theme = next;
        setTheme(next);
    };

    return (
        <div className="cp-app-shell">
            <header className="cp-mobile-header">
                <button className="cp-icon-button" type="button" onClick={() => setMobileOpen(true)} aria-label="Open navigation">
                    <Menu size={21} />
                </button>
                <button className="cp-mobile-brand" type="button" onClick={() => navigate('home')}>
                    <span className="cp-brand-mark">H</span>
                    <span>Home Orchestrator</span>
                </button>
                <span className={`cp-status-dot ${connected ? 'is-success' : 'is-danger'}`} aria-label={connected ? 'Connected' : 'Disconnected'} />
            </header>

            {mobileOpen && <button className="cp-drawer-backdrop" type="button" onClick={() => setMobileOpen(false)} aria-label="Close navigation" />}

            <aside className={`cp-sidebar ${mobileOpen ? 'is-open' : ''}`} aria-label="Primary navigation">
                <div className="cp-sidebar-brand">
                    <button className="cp-brand" type="button" onClick={() => navigate('home')}>
                        <span className="cp-brand-mark">H</span>
                        <span>
                            <strong>Home Orchestrator</strong>
                            <small>Human control layer</small>
                        </span>
                    </button>
                    <button className="cp-icon-button cp-drawer-close" type="button" onClick={() => setMobileOpen(false)} aria-label="Close navigation">
                        <X size={19} />
                    </button>
                </div>

                <nav className="cp-nav">
                    <span className="cp-nav-label">Workspace</span>
                    {NAV_ITEMS.map(item => {
                        const Icon = item.icon;
                        const isActive = activeView === item.id;
                        return (
                            <button
                                key={item.id}
                                type="button"
                                className={`cp-nav-item ${isActive ? 'is-active' : ''}`}
                                onClick={() => navigate(item.id)}
                                aria-current={isActive ? 'page' : undefined}
                            >
                                <Icon size={18} />
                                <span><strong>{item.label}</strong><small>{item.hint}</small></span>
                                {item.id === 'review' && pendingCount > 0 && <em>{pendingCount}</em>}
                            </button>
                        );
                    })}
                </nav>

                <div className="cp-sidebar-footer">
                    <div className="cp-runtime-status">
                        <span className={`cp-status-dot ${connected ? 'is-success' : 'is-danger'}`} />
                        <span><strong>{connected ? 'System connected' : 'Connection lost'}</strong><small>{connected ? 'Live updates enabled' : 'Attempting to reconnect'}</small></span>
                    </div>
                    <div className="cp-sidebar-actions">
                        <button className="cp-icon-button" type="button" onClick={toggleTheme} aria-label={`Use ${theme === 'dark' ? 'light' : 'dark'} theme`}>
                            {theme === 'dark' ? <Sun size={17} /> : <Moon size={17} />}
                        </button>
                        <button className="cp-settings-button" type="button" onClick={() => setShowSettings(true)}>
                            <Settings size={17} /><span>Settings</span>
                        </button>
                        <span className="cp-version">{appVersion}</span>
                    </div>
                </div>
            </aside>

            <main className="cp-main" id="main-content">
                <div className="cp-content">{children}</div>
            </main>

            {showSettings && (
                <SettingsModal
                    onClose={() => setShowSettings(false)}
                    currentConfig={config}
                    onUpdate={setConfig}
                />
            )}
        </div>
    );
}
