"use client";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { StockData } from '@/lib/data-parser';

export function SectorBarChart({ data }: { data: StockData[] }) {
  const sectorData = data.reduce((acc, curr) => {
    if (!curr.Sector || curr.Sector === "Unknown") return acc;
    if (!acc[curr.Sector]) acc[curr.Sector] = { sum: 0, count: 0 };
    if (curr["Margin of Safety"] !== null) {
      acc[curr.Sector].sum += curr["Margin of Safety"];
      acc[curr.Sector].count += 1;
    }
    return acc;
  }, {} as Record<string, { sum: number; count: number }>);

  const formattedData = Object.entries(sectorData)
    .map(([sector, stats]) => ({
      name: sector,
      avgMoS: stats.count > 0 ? stats.sum / stats.count : 0,
    }))
    .sort((a, b) => b.avgMoS - a.avgMoS)
    .slice(0, 8);

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const pData = payload[0].payload;
      return (
        <div className="bg-slate-900 border border-slate-700 p-2.5 rounded-lg text-sm font-mono shadow-2xl z-50">
          <p className="font-bold text-slate-50 mb-1 pb-1 border-b border-slate-800 uppercase">{pData.name}</p>
          <p className="text-slate-400 mt-1">Avg MoS: <span className={pData.avgMoS > 0 ? "text-emerald-400 font-bold" : "text-rose-400 font-bold"}>{pData.avgMoS.toFixed(1)}%</span></p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-5 h-[400px] flex flex-col relative w-full overflow-hidden shadow-[0_4px_20px_-4px_rgba(0,0,0,0.5)] backdrop-blur-md">
      <h3 className="text-sm font-semibold text-slate-300 mb-4 tracking-widest uppercase flex items-center shrink-0">
        <span className="w-2.5 h-2.5 rounded-full bg-blue-500 mr-2 shadow-[0_0_8px_rgba(59,130,246,0.8)]"></span>
        Sector Avg. Value
      </h3>
      <div className="flex-1 w-full relative -ml-4 min-h-0">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={formattedData} layout="vertical" margin={{ top: 10, right: 20, bottom: 0, left: 70 }}>
            <XAxis type="number" tick={{ fill: '#64748b', fontSize: 11, fontFamily: 'var(--font-jetbrains-mono)' }} tickFormatter={(v) => `${v}%`} axisLine={{ stroke: '#334155' }} />
            <YAxis type="category" dataKey="name" tick={{ fill: '#94a3b8', fontSize: 10, fontWeight: 500 }} axisLine={{ stroke: '#334155' }} tickLine={false} width={90} />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: '#1e293b' }} />
            <Bar dataKey="avgMoS" radius={[0, 4, 4, 0]}>
              {formattedData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.avgMoS > 0 ? '#10b981' : '#e11d48'} className="opacity-90 hover:opacity-100 transition-opacity" />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
