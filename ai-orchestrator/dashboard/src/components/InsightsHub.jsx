import React, { useState } from 'react';
import { Activity, BarChart3 } from 'lucide-react';
import { AnalyticsCharts } from './AnalyticsCharts';
import { DecisionStream } from './DecisionStream';

export function InsightsHub({ decisions, dailyStats, performance }) {
    const [tab, setTab] = useState('activity');

    return (
        <div className="cp-page">
            <header className="cp-page-header">
                <div>
                    <div className="cp-eyebrow"><BarChart3 size={14} /> Explainability</div>
                    <h1>Activity and outcomes</h1>
                    <p>Understand what happened, which guarded tools ran, and how the system is performing over time.</p>
                </div>
            </header>
            <div className="cp-segmented" role="tablist" aria-label="Insight sections">
                <button id="insights-tab-activity" type="button" role="tab" aria-selected={tab === 'activity'} aria-controls="insights-panel" className={tab === 'activity' ? 'is-active' : ''} onClick={() => setTab('activity')}>
                    <Activity size={15} /> Activity
                </button>
                <button id="insights-tab-performance" type="button" role="tab" aria-selected={tab === 'performance'} aria-controls="insights-panel" className={tab === 'performance' ? 'is-active' : ''} onClick={() => setTab('performance')}>
                    <BarChart3 size={15} /> Performance
                </button>
            </div>
            <div id="insights-panel" role="tabpanel" aria-labelledby={`insights-tab-${tab}`}>
                {tab === 'activity'
                    ? <DecisionStream decisions={decisions} />
                    : <AnalyticsCharts dailyData={dailyStats} performanceData={performance} />}
            </div>
        </div>
    );
}
