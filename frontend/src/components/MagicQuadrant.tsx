"use client";
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Cell } from 'recharts';
import { StockData } from '@/lib/data-parser';

export function MagicQuadrant({ data }: { data: StockData[] }) {
  const validData = data.filter(d => d["Margin of Safety"] !== null && d.ROIC !== null);

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const pData = payload[0].payload as StockData;
      return (
        <div className="bg-slate-900 border border-slate-700 p-3 rounded-lg shadow-2xl text-sm font-mono z-50">
          <p className="font-bold text-slate-50 mb-1 pb-1 border-b border-slate-800 uppercase">{pData.Ticker} - <span className="text-xs text-slate-400 font-sans">{pData.Company}</span></p>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1 mt-2">
            <span className="text-slate-400">MoS</span>
            <span className={((pData["Margin of Safety"] || 0) > 0) ? "text-emerald-400 text-right" : "text-rose-400 text-right"}>{pData["Margin of Safety"]?.toFixed(1)}%</span>
            <span className="text-slate-400">ROIC</span>
            <span className={((pData.ROIC || 0) > 10) ? "text-amber-400 text-right" : "text-slate-300 text-right"}>{pData.ROIC?.toFixed(1)}%</span>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-5 h-[400px] flex flex-col relative w-full overflow-hidden shadow-[0_4px_20px_-4px_rgba(0,0,0,0.5)] backdrop-blur-md">
      <h3 className="text-sm font-semibold text-slate-300 mb-4 tracking-widest uppercase flex items-center shrink-0">
        <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 mr-2 shadow-[0_0_8px_rgba(16,185,129,0.8)]"></span>
        Value / Quality Quadrant
      </h3>
      <div className="flex-1 w-full relative -ml-4 min-h-0">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 10, right: 20, bottom: 20, left: -20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
            <XAxis 
              type="number" 
              dataKey="Margin of Safety" 
              name="Margin of Safety" 
              tick={{ fill: '#64748b', fontSize: 11, fontFamily: 'var(--font-jetbrains-mono)' }}
              tickFormatter={(v) => `${v}%`}
              axisLine={{ stroke: '#334155' }}
              tickLine={false}
            />
            <YAxis 
              type="number" 
              dataKey="ROIC" 
              name="ROIC" 
              tick={{ fill: '#64748b', fontSize: 11, fontFamily: 'var(--font-jetbrains-mono)' }}
              tickFormatter={(v) => `${v}%`}
              axisLine={{ stroke: '#334155' }}
              tickLine={false}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ strokeDasharray: '3 3', stroke: '#475569' }} />
            <ReferenceLine y={15} stroke="#64748b" strokeDasharray="3 3" label={{ value: "Quality", fill: "#475569", fontSize: 10, position: 'insideTopLeft' }} />
            <ReferenceLine x={20} stroke="#64748b" strokeDasharray="3 3" label={{ value: "Value", fill: "#475569", fontSize: 10, position: 'insideTopRight' }} />
            
            <Scatter name="Stocks" data={validData}>
              {validData.map((entry, index) => {
                const isTopRight = (entry["Margin of Safety"] || 0) > 20 && (entry.ROIC || 0) > 15;
                const isPositive = (entry["Margin of Safety"] || 0) > 0;
                return (
                  <Cell 
                    key={`cell-${index}`} 
                    fill={isTopRight ? '#10b981' : isPositive ? '#3b82f6' : '#475569'}
                    className={isTopRight ? "drop-shadow-[0_0_6px_rgba(16,185,129,0.9)]" : (isPositive ? "opacity-90" : "opacity-40")}
                  />
                );
              })}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
