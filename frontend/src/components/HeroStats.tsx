import { StockData } from "@/lib/data-parser";
import type { ReactNode } from "react";
import { BarChart3, Target, ShieldAlert, Gauge } from "lucide-react";
import { EducationTooltip, Definitions } from "./EducationTooltip";

export function HeroStats({ data }: { data: StockData[] }) {
  if (!data || data.length === 0) return null;

  const buyZones = data.filter(d => d["Alert Status"].startsWith("BUY-ZONE"));
  const closest = [...data]
    .filter(d => d["Price Premium to Entry"] !== null)
    .sort((a, b) => (a["Price Premium to Entry"] as number) - (b["Price Premium to Entry"] as number))[0];
  const specialized = data.filter(d => d["Verification Required"].length > 0).length;

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
      <StatCard 
        title="Total Screened"
        value={data.length.toString()}
        icon={<BarChart3 className="w-5 h-5 text-slate-400" />}
        tooltipContent={Definitions.totalScreened}
      />
      <StatCard 
        title="Buy Zones"
        value={buyZones.length.toString()}
        subtitle={buyZones.length ? "Requires filing verification" : "No qualifying entry today"}
        icon={<Target className="w-5 h-5 text-emerald-400" />}
        valueClass="text-emerald-400"
        tooltipContent={Definitions.topOpp}
      />
      <StatCard 
        title="Closest to Entry"
        value={closest ? closest.Ticker : "N/A"}
        subtitle={closest?.["Price Premium to Entry"] !== null ? `${closest["Price Premium to Entry"]?.toFixed(1)}% above entry` : undefined}
        icon={<Gauge className="w-5 h-5 text-amber-400" />}
        valueClass="text-amber-400"
      />
      <StatCard 
        title="Specialized Models"
        value={specialized.toString()}
        subtitle="Manual filing checks required"
        icon={<ShieldAlert className="w-5 h-5 text-blue-400" />}
        valueClass="text-blue-400"
      />
    </div>
  );
}

interface StatCardProps {
  title: string;
  value: string;
  subtitle?: string;
  icon: ReactNode;
  valueClass?: string;
  tooltipContent?: string;
}

function StatCard({ title, value, subtitle, icon, valueClass = "text-slate-50", tooltipContent }: StatCardProps) {
  return (
    <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-5 flex flex-col justify-between backdrop-blur-md shadow-[0_4px_20px_-4px_rgba(0,0,0,0.5)]">
      <div className="flex items-center justify-between mb-3">
        {tooltipContent ? (
          <EducationTooltip content={tooltipContent}>
            <h3 className="text-sm font-medium text-slate-400 uppercase tracking-wider mb-0 block">{title}</h3>
          </EducationTooltip>
        ) : (
          <h3 className="text-sm font-medium text-slate-400 uppercase tracking-wider">{title}</h3>
        )}
        {icon}
      </div>
      <div>
        <div className={`text-3xl font-bold font-mono tracking-tight ${valueClass}`}>{value}</div>
        {subtitle && <div className="text-xs text-slate-500 mt-1.5 truncate uppercase">{subtitle}</div>}
      </div>
    </div>
  );
}
