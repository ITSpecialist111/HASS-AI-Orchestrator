import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { Activity, Clock, CheckCircle } from 'lucide-react';

export const AnalyticsCharts = ({ dailyData, performanceData }) => {
    if (!dailyData || dailyData.length === 0) {
        return <div className="text-gray-400">No analytics data available</div>;
    }

    return (
        <div className="space-y-6">
            {/* Activity Chart */}
            <div className="bg-slate-800 p-4 rounded-lg border border-slate-700">
                <h3 className="text-lg font-semibold mb-4 text-slate-200 flex items-center gap-2">
                    <Activity size={20} />
                    Weekly Agent Activity
                </h3>
                <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={dailyData}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                            <XAxis dataKey="date" stroke="#94a3b8" fontSize={12} />
                            <YAxis stroke="#94a3b8" fontSize={12} />
                            <Tooltip
                                contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f1f5f9' }}
                                itemStyle={{ color: '#f1f5f9' }}
                            />
                            <Legend />
                            {/* Dynamically generate bars for each agent found in data */}
                            {dailyData.length > 0 && Object.keys(dailyData[0])
                                .filter(key => key !== 'date')
                                .map((agentId, index) => {
                                    // Deterministic color generation
                                    const hue = (index * 137.508) % 360; // Golden angle approx
                                    const color = `hsl(${hue}, 70%, 50%)`;
                                    return (
                                        <Bar
                                            key={agentId}
                                            dataKey={agentId}
                                            fill={color}
                                            name={agentId.charAt(0).toUpperCase() + agentId.slice(1)}
                                            stackId="a"
                                        />
                                    );
                                })
                            }
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </div>

            {/* Performance Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {Object.entries(performanceData || {}).map(([agent, stats]) => (
                    <div key={agent} className="bg-slate-800 p-4 rounded-lg border border-slate-700">
                        <h4 className="font-medium text-slate-300 capitalize mb-2">{agent} Agent</h4>
                        <div className="grid grid-cols-2 gap-2 text-sm">
                            <div className="flex items-center gap-2 text-slate-400">
                                <Clock size={14} />
                                <span>Decisions (24h)</span>
                            </div>
                            <div className="text-right text-slate-200">{stats.decisions_24h}</div>

                            <div className="flex items-center gap-2 text-slate-400">
                                <CheckCircle size={14} />
                                <span>Error Rate</span>
                            </div>
                            <div className={`text-right ${stats.error_rate > 0.05 ? 'text-red-400' : 'text-green-400'}`}>
                                {(stats.error_rate * 100).toFixed(0)}%
                            </div>

                            <div className="col-span-2 mt-2 pt-2 border-t border-slate-700 flex justify-between">
                                <span className="text-slate-500">Top Tool</span>
                                <code className="text-xs bg-slate-900 px-2 py-1 rounded text-blue-300">
                                    {stats.top_tool}
                                </code>
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};
