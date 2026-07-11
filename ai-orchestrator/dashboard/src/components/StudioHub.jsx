import React, { lazy, Suspense, useState } from 'react';
import { LayoutDashboard, Wand2 } from 'lucide-react';

const DashboardStudio = lazy(() => import('./DashboardStudio').then(module => ({ default: module.DashboardStudio })));
const VisualDashboard = lazy(() => import('./VisualDashboard').then(module => ({ default: module.VisualDashboard })));

export function StudioHub() {
    const [tab, setTab] = useState('studio');

    return (
        <div className="cp-page cp-page--wide">
            <header className="cp-page-header">
                <div>
                    <div className="cp-eyebrow"><Wand2 size={14} /> Visual workspace</div>
                    <h1>Dashboard studio</h1>
                    <p>Generate, refine, and safely preview purpose-built views for the people in your home.</p>
                </div>
            </header>
            <div className="cp-segmented" role="tablist" aria-label="Studio sections">
                <button id="studio-tab-studio" type="button" role="tab" aria-selected={tab === 'studio'} aria-controls="studio-panel" className={tab === 'studio' ? 'is-active' : ''} onClick={() => setTab('studio')}>
                    <Wand2 size={15} /> Saved studio
                </button>
                <button id="studio-tab-legacy" type="button" role="tab" aria-selected={tab === 'legacy'} aria-controls="studio-panel" className={tab === 'legacy' ? 'is-active' : ''} onClick={() => setTab('legacy')}>
                    <LayoutDashboard size={15} /> Live generated view
                </button>
            </div>
            <div id="studio-panel" role="tabpanel" aria-labelledby={`studio-tab-${tab}`}>
                <Suspense fallback={<div className="cp-empty-state">Loading studio…</div>}>
                    {tab === 'studio' ? <DashboardStudio /> : <VisualDashboard />}
                </Suspense>
            </div>
        </div>
    );
}
