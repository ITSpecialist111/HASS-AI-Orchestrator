import React from 'react';
import {
    Bar,
    BarChart,
    CartesianGrid,
    Legend,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from 'recharts';
import { Activity, CheckCircle2, Clock3, Wrench } from 'lucide-react';

export const AnalyticsCharts = ({ dailyData = [], performanceData = {} }) => {
    const agentKeys = dailyData.length
        ? Object.keys(dailyData[0]).filter(key => key !== 'date')
        : [];

    if (!dailyData.length && !Object.keys(performanceData).length) {
        return <div className="cp-empty-state"><Activity size={25} /><div><strong>No analytics yet</strong><span>Performance appears after agents begin recording decisions.</span></div></div>;
    }

    return (
        <div className="cp-insights-stack">
            {dailyData.length > 0 && (
                <section className="cp-card">
                    <div className="cp-section-heading"><div><span className="cp-eyebrow">Seven-day view</span><h2>Agent activity</h2></div></div>
                    <div className="cp-chart" aria-label="Weekly agent activity chart">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={dailyData}>
                                <CartesianGrid strokeDasharray="3 3" stroke="var(--cp-border)" />
                                <XAxis dataKey="date" stroke="var(--cp-text-muted)" fontSize={12} tickLine={false} axisLine={false} />
                                <YAxis stroke="var(--cp-text-muted)" fontSize={12} tickLine={false} axisLine={false} />
                                <Tooltip
                                    contentStyle={{ background: 'var(--cp-surface)', border: '1px solid var(--cp-border)', borderRadius: '10px', color: 'var(--cp-text)' }}
                                    itemStyle={{ color: 'var(--cp-text)' }}
                                    labelStyle={{ color: 'var(--cp-text-muted)' }}
                                />
                                <Legend wrapperStyle={{ color: 'var(--cp-text-muted)', fontSize: '12px' }} />
                                {agentKeys.map((agentId, index) => (
                                    <Bar
                                        key={agentId}
                                        dataKey={agentId}
                                        fill="var(--cp-link)"
                                        fillOpacity={Math.max(0.35, 1 - index * 0.12)}
                                        name={agentId.charAt(0).toUpperCase() + agentId.slice(1)}
                                        stackId="activity"
                                    />
                                ))}
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </section>
            )}

            <section className="cp-performance-grid" aria-label="Agent performance">
                {Object.entries(performanceData).map(([agent, stats]) => (
                    <article className="cp-performance-card" key={agent}>
                        <div className="cp-performance-heading"><span className="cp-icon-tile"><Activity size={16} /></span><div><strong>{agent} agent</strong><small>Last 24 hours</small></div></div>
                        <dl>
                            <div><dt><Clock3 size={14} /> Decisions</dt><dd>{stats.decisions_24h ?? 0}</dd></div>
                            <div><dt><CheckCircle2 size={14} /> Success health</dt><dd className={(stats.error_rate || 0) > 0.05 ? 'is-danger' : 'is-success'}>{Math.max(0, 100 - (stats.error_rate || 0) * 100).toFixed(0)}%</dd></div>
                            <div><dt><Wrench size={14} /> Most used tool</dt><dd>{stats.top_tool || '—'}</dd></div>
                        </dl>
                    </article>
                ))}
            </section>
        </div>
    );
};
