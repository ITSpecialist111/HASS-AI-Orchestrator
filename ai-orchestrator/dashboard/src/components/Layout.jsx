
import React, { useEffect, useState } from 'react';
import {
    BarChart3,
    Bell,
    Brain,
    ChevronRight,
    CheckSquare,
    CircleHelp,
    Grid3X3,
    Home,
    Menu,
    Moon,
    Settings,
    ShieldCheck,
    Sun,
    Wand2,
    X,
    Zap,
} from 'lucide-react';
import { SettingsModal } from './SettingsModal';

const NAV_ITEMS = [
    { id: 'home', label: 'Home', hint: 'Status and priorities', icon: Home, group: 'Overview' },
    { id: 'run', label: 'Ask & run', hint: 'Set a goal', icon: Brain, group: 'Operations' },
    { id: 'review', label: 'Action center', hint: 'Review exact plans', icon: CheckSquare, group: 'Operations' },
    { id: 'automation', label: 'Automation', hint: 'Agents and triggers', icon: Zap, group: 'Management' },
    { id: 'insights', label: 'Advanced insights', hint: 'Activity and outcomes', icon: BarChart3, group: 'Management' },
    { id: 'studio', label: 'Dashboard studio', hint: 'Human dashboards', icon: Wand2, group: 'Management' },
];

export function Layout({
    children,
    activeView,
    onViewChange,
    connected,
    pendingCount = 0,
    version = 'v0.13.6',
}) {
    const [showSettings, setShowSettings] = useState(false);
    const [config, setConfig] = useState(null);
    const [appVersion, setAppVersion] = useState(version);
    const [mobileOpen, setMobileOpen] = useState(false);
    const [navCollapsed, setNavCollapsed] = useState(false);
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

    const toggleNavigation = () => {
        if (window.matchMedia('(max-width: 820px)').matches) {
            setMobileOpen(value => !value);
            return;
        }
        setNavCollapsed(value => !value);
    };

    const activeItem = NAV_ITEMS.find(item => item.id === activeView) || NAV_ITEMS[0];
    const simulationMode = config?.dry_run_mode !== false;

    return (
        <div className={`cp-app-shell ${navCollapsed ? 'is-nav-collapsed' : ''}`}>
            <header className="ms-global-header">
                <div className="ms-global-brand">
                    <button className="ms-app-launcher" type="button" onClick={toggleNavigation} aria-label={navCollapsed ? 'Expand navigation' : 'Collapse navigation'}>
                        <Grid3X3 size={17} />
                    </button>
                    <button className="ms-product-name" type="button" onClick={() => navigate('home')}>
                        <ShieldCheck size={19} />
                        <strong>Home Orchestrator</strong>
                    </button>
                </div>

                <div className={`ms-mode-banner ${simulationMode ? 'is-simulation' : 'is-live'}`}>
                    {simulationMode ? 'Simulation mode' : 'Live control'}
                </div>

                <div className="ms-global-actions">
                    <button type="button" onClick={() => navigate('review')} aria-label={`${pendingCount} plans awaiting review`} title="Action center">
                        <Bell size={17} />
                        {pendingCount > 0 && <span className="ms-notification-count">{pendingCount}</span>}
                    </button>
                    <button type="button" onClick={toggleTheme} aria-label={`Use ${theme === 'dark' ? 'light' : 'dark'} theme`} title="Change theme">
                        {theme === 'dark' ? <Sun size={17} /> : <Moon size={17} />}
                    </button>
                    <button type="button" onClick={() => setShowSettings(true)} aria-label="Open settings" title="Settings">
                        <Settings size={17} />
                    </button>
                    <span className="ms-user-avatar" aria-label="Home Orchestrator">HO</span>
                </div>
            </header>

            {mobileOpen && <button className="cp-drawer-backdrop" type="button" onClick={() => setMobileOpen(false)} aria-label="Close navigation" />}

            <aside className={`cp-sidebar ${mobileOpen ? 'is-open' : ''}`} aria-label="Primary navigation">
                <div className="cp-sidebar-brand">
                    <button className="cp-nav-collapse" type="button" onClick={toggleNavigation} aria-label={navCollapsed ? 'Expand navigation' : 'Collapse navigation'}>
                        <Menu size={18} />
                        <span>Navigation</span>
                    </button>
                    <button className="cp-icon-button cp-drawer-close" type="button" onClick={() => setMobileOpen(false)} aria-label="Close navigation">
                        <X size={19} />
                    </button>
                </div>

                <nav className="cp-nav">
                    {NAV_ITEMS.map((item, index) => {
                        const Icon = item.icon;
                        const isActive = activeView === item.id;
                        const showGroup = index === 0 || NAV_ITEMS[index - 1].group !== item.group;
                        return (
                            <React.Fragment key={item.id}>
                                {showGroup && <span className="cp-nav-label">{item.group}</span>}
                                <button
                                    type="button"
                                    className={`cp-nav-item ${isActive ? 'is-active' : ''}`}
                                    onClick={() => navigate(item.id)}
                                    aria-current={isActive ? 'page' : undefined}
                                    title={navCollapsed ? item.label : undefined}
                                >
                                    <Icon size={17} />
                                    <span><strong>{item.label}</strong><small>{item.hint}</small></span>
                                    {item.id === 'review' && pendingCount > 0 && <em>{pendingCount}</em>}
                                </button>
                            </React.Fragment>
                        );
                    })}
                </nav>

                <div className="cp-sidebar-footer">
                    <div className="cp-runtime-status">
                        <span className={`cp-status-dot ${connected ? 'is-success' : 'is-danger'}`} />
                        <span><strong>{connected ? 'System connected' : 'Connection lost'}</strong><small>{connected ? 'Live updates enabled' : 'Attempting to reconnect'}</small></span>
                    </div>
                    <span className="cp-version">Home control portal · {appVersion}</span>
                </div>
            </aside>

            <main className="cp-main" id="main-content">
                <div className="ms-command-bar">
                    <div className="ms-breadcrumb" aria-label="Breadcrumb">
                        <span>Home Orchestrator</span>
                        <ChevronRight size={13} />
                        <strong>{activeItem.label}</strong>
                    </div>
                    <div className="ms-command-actions">
                        <button type="button" onClick={() => navigate('home')}>
                            <span className={`cp-status-dot ${connected ? 'is-success' : 'is-danger'}`} />
                            {connected ? 'System health' : 'Connection issue'}
                        </button>
                        <button type="button" onClick={() => navigate('review')}>
                            <CheckSquare size={15} /> Action center
                        </button>
                        <button type="button" onClick={() => setShowSettings(true)}>
                            <CircleHelp size={15} /> Portal settings
                        </button>
                    </div>
                </div>
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
