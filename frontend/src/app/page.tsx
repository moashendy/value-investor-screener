"use client";
import { useEffect, useState, useCallback } from "react";
import { fetchData, StockData } from "@/lib/data-parser";
import { HeroStats } from "@/components/HeroStats";
import { MagicQuadrant } from "@/components/MagicQuadrant";
import { ScreenerGrid } from "@/components/ScreenerGrid";
import { SectorBarChart } from "@/components/SectorBarChart";

export default function DashboardPage() {
  const [data, setData] = useState<StockData[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(() => {
    fetchData().then((res) => {
      setData(res);
      setLoading(false);
    });
  }, []);

  useEffect(() => {
    loadData();
    window.addEventListener('dashboard-force-refetch', loadData);
    return () => window.removeEventListener('dashboard-force-refetch', loadData);
  }, [loadData]);

  // Only show the big loading screen on absolute initial mount
  if (loading && data.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-950 text-slate-400 font-mono">
        <div className="animate-pulse flex flex-col items-center">
          <div className="w-8 h-8 border-t-2 border-emerald-500 rounded-full animate-spin mb-4" />
          Loading Quantitative Data Terminal...
        </div>
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-slate-950 p-4 md:p-6 lg:p-8 selection:bg-emerald-500/30">
      <div className="max-w-[1800px] mx-auto space-y-6">
        
        <header className="flex flex-col md:flex-row md:items-end justify-between border-b border-slate-800/80 pb-4 mb-4">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold text-slate-50 uppercase tracking-widest flex items-center drop-shadow-md">
              <span className="w-3 h-3 bg-emerald-500 rounded-sm mr-3 shadow-[0_0_12px_rgba(16,185,129,0.8)]"></span>
              Quant Value Terminal
            </h1>
            <p className="text-slate-500 text-xs mt-2 uppercase tracking-widest font-mono flex items-center">
              <span>System: Active</span>
              <span className="mx-2 text-slate-700">|</span> 
              <span>Data Target: latest_screener.csv</span>
            </p>
          </div>
          <div className="text-right mt-4 md:mt-0 font-mono text-xs text-slate-500 flex flex-col items-end">
            <span className="flex items-center text-emerald-500">
              CRON AUTOMATION ACTIVE <span className="ml-2 animate-pulse text-lg leading-none">●</span>
            </span>
            <span className="mt-1 opacity-60">Syncs Daily @ 17:00 EST</span>
          </div>
        </header>

        <HeroStats data={data} />
        
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 w-full">
          <MagicQuadrant data={data} />
          <SectorBarChart data={data} />
        </div>

        <ScreenerGrid data={data} />
        
      </div>
    </main>
  );
}
