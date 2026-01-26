import { StockData } from "@/lib/data-parser";
import { TrendingUp, BarChart3, Target, Calculator } from "lucide-react";
import { EducationTooltip, Definitions } from "./EducationTooltip";

export function HeroStats({ data }: { data: StockData[] }) {
  if (!data || data.length === 0) return null;

  const totalAnalyzed = data.length;
  
  const validForOpp = data.filter(d => d["Margin of Safety"] !== null && d.ROIC !== null);
  const topOpp = [...validForOpp].sort((a, b) => {
    const aScore = (a["Margin of Safety"] as number) * (a.ROIC as number);
    const bScore = (b["Margin of Safety"] as number) * (b.ROIC as number);
    return bScore - aScore;
  })[0];

  const overvaluedCount = data.filter(d => (d["Margin of Safety"] || 0) < 0).length;

  const avgRoic = data.reduce((acc, curr) => acc + (curr.ROIC || 0), 0) / (totalAnalyzed || 1);

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
      <StatCard 
        title="Total Screened"
        value={totalAnalyzed.toString()}
        icon={<BarChart3 className="w-5 h-5 text-slate-400" />}
        tooltipContent={Definitions.totalScreened}
      />
      <StatCard 
        title="Top Opportunity"
        value={topOpp ? topOpp.Ticker : "N/A"}
        subtitle={topOpp ? `${topOpp.Company}` : undefined}
        icon={<Target className="w-5 h-5 text-emerald-400" />}
        valueClass="text-emerald-400"
        tooltipContent={Definitions.topOpp}
      />
      <StatCard 
        title="Overvalued Targets"
        value={overvaluedCount.toString()}
        icon={<TrendingUp className="w-5 h-5 text-rose-400" />}
        valueClass="text-rose-400"
      />
      <StatCard 
        title="Avg ROIC (Universe)"
        value={`${avgRoic.toFixed(1)}%`}
        icon={<Calculator className="w-5 h-5 text-amber-400" />}
        tooltipContent={Definitions.roic}
      />
    </div>
  );
}

function StatCard({ title, value, subtitle, icon, valueClass = "text-slate-50", tooltipContent }: any) {
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
