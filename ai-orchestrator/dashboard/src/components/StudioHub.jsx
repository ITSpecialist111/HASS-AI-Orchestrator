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
                <button type="button" role="tab" aria-selected={tab === 'studio'} className={tab === 'studio' ? 'is-active' : ''} onClick={() => setTab('studio')}>
                    <Wand2 size={15} /> Saved studio
                </button>
                <button type="button" role="tab" aria-selected={tab === 'legacy'} className={tab === 'legacy' ? 'is-active' : ''} onClick={() => setTab('legacy')}>
                    <LayoutDashboard size={15} /> Live generated view
                </button>
            </div>
            <Suspense fallback={<div className="cp-empty-state">Loading studio…</div>}>
                {tab === 'studio' ? <DashboardStudio /> : <VisualDashboard />}
            </Suspense>
        </div>
    );
}
