
import React from 'react';
import { LayoutDashboard, Activity, BarChart3, Bot, Settings, Server, Heart } from 'lucide-react';
import { useState, useEffect } from 'react';
import { SettingsModal } from './SettingsModal';

export function Layout({ children, activeTab, onTabChange, connected, version = "v0.9.14" }) {
    const [showSettings, setShowSettings] = useState(false);
    const [config, setConfig] = useState(null);

    const [appVersion, setAppVersion] = useState(version);

    // Load config for settings modal and version
    useEffect(() => {
        fetch('api/config')
            .then(res => res.json())
            .then(data => {
                setConfig(data);
                if (data.version) setAppVersion("v" + data.version);
            })
            .catch(err => console.error("Failed to load config", err));
    }, [showSettings]); // Also fetch on settings open, but ideally on mount too

    // Initial fetch
    useEffect(() => {
        fetch('api/config')
            .then(res => res.json())
            .then(data => {
                if (data.version) setAppVersion("v" + data.version);
            })
            .catch(e => console.error("Ver check failed", e));
    }, []);

    const menuItems = [
        { id: 'live', label: 'Command Centre', icon: LayoutDashboard },
        { id: 'stream', label: 'Decision Stream', icon: Activity },
        { id: 'analytics', label: 'Analytics', icon: BarChart3 },
        { id: 'factory', label: 'Agent Factory', icon: Bot },
        { id: 'visual', label: 'Visual Dashboard', icon: Server, isLink: true, url: 'api/dashboard/dynamic?refresh=true' },
    ];

    return (
        <div className="flex h-screen bg-slate-950 text-slate-100 font-sans overflow-hidden selection:bg-purple-500/30">
            {/* Sidebar */}
            <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col shrink-0 transition-all duration-300">
                {/* Brand */}
                <div className="p-6 flex items-center gap-3 border-b border-slate-800/50">
                    <div className="bg-gradient-to-br from-purple-600 to-blue-600 w-8 h-8 rounded-lg flex items-center justify-center font-bold text-white shadow-lg shadow-purple-900/20 shrink-0">
                        AI
                    </div>
                    <div>
                        <h1 className="font-bold text-lg tracking-tight leading-none">Orchestrator</h1>
                        <span className="text-xs text-slate-500 font-medium">Command Node</span>
                    </div>
                </div>

                {/* Navigation */}
                <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
                    {menuItems.map((item) => {
                        const Icon = item.icon;
                        const isActive = activeTab === item.id;
                        return (
                            <button
                                key={item.id}
                                onClick={() => {
                                    if (item.isLink) {
                                        // Handle Ingress pathing: Derive absolute URL from current relative base
                                        // Robust normalization: remove all trailing and leading slashes from parts before joining
                                        const cleanPath = window.location.pathname.replace(/\/+$/, '');
                                        const cleanItemUrl = item.url.replace(/^\/+/, '');
                                        const url = `${window.location.origin}${cleanPath}/${cleanItemUrl}`;
                                        window.open(url, '_blank');
                                    } else {
                                        onTabChange(item.id);
                                    }
                                }}
                                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 group
                  ${isActive
                                        ? 'bg-purple-500/10 text-purple-400 border border-purple-500/20 shadow-[0_0_15px_-3px_rgba(168,85,247,0.15)]'
                                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                                    }`}
                            >
                                <Icon size={18} className={isActive ? 'text-purple-400' : 'text-slate-500 group-hover:text-slate-300'} />
                                {item.label}
                            </button>
                        );
                    })}
                </nav>

                <div className="p-4 bg-slate-950/30 border-t border-slate-800 text-xs">
                    <div className="flex items-center justify-between mb-3">
                        <span className="text-slate-500 font-mono">{appVersion}</span>
                        <button
                            onClick={() => setShowSettings(true)}
                            className="text-slate-600 hover:text-slate-400 transition-colors p-1 hover:bg-slate-800 rounded"
                            title="Settings"
                        >
                            <Settings size={14} />
                        </button>
                    </div>

                    <div className={`flex items-center gap-2 px-3 py-2 rounded-md border transition-colors duration-300
            ${connected
                            ? 'bg-green-500/5 border-green-500/20 text-green-400'
                            : 'bg-red-500/5 border-red-500/20 text-red-500'
                        }`}>
                        <div className="relative flex items-center justify-center w-2 h-2">
                            <div className={`absolute w-full h-full rounded-full opacity-75 animate-ping ${connected ? 'bg-green-500' : 'bg-red-500'}`}></div>
                            <div className={`relative w-1.5 h-1.5 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`}></div>
                        </div>
                        <span className="font-semibold tracking-wide">{connected ? 'SYSTEM ONLINE' : 'DISCONNECTED'}</span>
                    </div>
                </div>
            </aside>

            {/* Main Content Area */}
            <main className="flex-1 overflow-y-auto bg-slate-950/50 relative">
                {/* Top Gradient Line */}
                <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-purple-500/20 to-transparent"></div>

                <div className="max-w-[1600px] mx-auto p-6 md:p-8">
                    {children}
                </div>
            </main>

            {/* Settings Modal */}
            {showSettings && (
                <SettingsModal
                    onClose={() => setShowSettings(false)}
                    currentConfig={config}
                />
            )}
        </div>
    );
}
