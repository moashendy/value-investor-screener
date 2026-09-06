"use client";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { StockData } from '@/lib/data-parser';

type SectorPoint = { name: string; avgMoS: number };
type SectorTooltipProps = {
  active?: boolean;
  payload?: Array<{ payload: SectorPoint }>;
};

function SectorTooltip({ active, payload }: SectorTooltipProps) {
  if (active && payload?.length) {
    const pData = payload[0].payload;
    return (
      <div className="bg-slate-900 border border-slate-700 p-2.5 rounded-lg text-sm font-mono shadow-2xl z-50">
        <p className="font-bold text-slate-50 mb-1 pb-1 border-b border-slate-800 uppercase">{pData.name}</p>
        <p className="text-slate-400 mt-1">Median MoS: <span className={pData.avgMoS > 0 ? "text-emerald-400 font-bold" : "text-rose-400 font-bold"}>{pData.avgMoS.toFixed(1)}%</span></p>
      </div>
    );
  }
  return null;
}

export function SectorBarChart({ data }: { data: StockData[] }) {
  const sectorData = data.reduce((acc, curr) => {
    if (!curr.Sector || curr.Sector === "Unknown") return acc;
    if (!acc[curr.Sector]) acc[curr.Sector] = [];
    if (curr["Margin of Safety"] !== null) {
      acc[curr.Sector].push(curr["Margin of Safety"]);
    }
    return acc;
  }, {} as Record<string, number[]>);

  const formattedData = Object.entries(sectorData)
    .map(([sector, values]) => {
      const ordered = [...values].sort((a, b) => a - b);
      const middle = Math.floor(ordered.length / 2);
      const median = ordered.length % 2 ? ordered[middle] : (ordered[middle - 1] + ordered[middle]) / 2;
      return { name: sector, avgMoS: median };
    })
    .sort((a, b) => b.avgMoS - a.avgMoS)
    .slice(0, 8);

  return (
    <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-5 h-[400px] flex flex-col relative w-full min-w-0 overflow-hidden shadow-[0_4px_20px_-4px_rgba(0,0,0,0.5)] backdrop-blur-md">
      <h3 className="text-sm font-semibold text-slate-300 mb-4 tracking-widest uppercase flex items-center shrink-0">
        <span className="w-2.5 h-2.5 rounded-full bg-blue-500 mr-2 shadow-[0_0_8px_rgba(59,130,246,0.8)]"></span>
        Sector Median Value
      </h3>
      <div className="flex-1 w-full min-w-0 relative -ml-4 min-h-0">
        <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0} initialDimension={{ width: 600, height: 300 }}>
          <BarChart data={formattedData} layout="vertical" margin={{ top: 10, right: 20, bottom: 0, left: 70 }}>
            <XAxis type="number" tick={{ fill: '#64748b', fontSize: 11, fontFamily: 'var(--font-jetbrains-mono)' }} tickFormatter={(v) => `${v}%`} axisLine={{ stroke: '#334155' }} />
            <YAxis type="category" dataKey="name" tick={{ fill: '#94a3b8', fontSize: 10, fontWeight: 500 }} axisLine={{ stroke: '#334155' }} tickLine={false} width={90} />
            <Tooltip content={<SectorTooltip />} cursor={{ fill: '#1e293b' }} />
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
