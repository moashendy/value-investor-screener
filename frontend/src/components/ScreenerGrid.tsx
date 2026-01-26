"use client";
import { useState } from "react";
import { StockData } from "@/lib/data-parser";
import { formatCurrency, getColorForPiotroski, getColorForMoS, getColorForZScore } from "@/lib/formatters";
import { ArrowUpDown } from "lucide-react";
import { EducationTooltip, Definitions } from "./EducationTooltip";

type SortKey = keyof StockData;

export function ScreenerGrid({ data }: { data: StockData[] }) {
  const [sortKey, setSortKey] = useState<SortKey>("Margin of Safety");
  const [sortAsc, setSortAsc] = useState(false);

  if (!data || data.length === 0) return null;

  const sortedData = [...data].sort((a, b) => {
    let aVal = a[sortKey];
    let bVal = b[sortKey];

    if (aVal === null) aVal = -Infinity;
    if (bVal === null) bVal = -Infinity;

    if (typeof aVal === 'string' && typeof bVal === 'string') {
      return sortAsc ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
    }
    
    return sortAsc ? (aVal as number) - (bVal as number) : (bVal as number) - (aVal as number);
  });

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortAsc(!sortAsc);
    } else {
      setSortKey(key);
      setSortAsc(false);
    }
  };

  const Th = ({ label, sortableKey, tooltipContent }: { label: string, sortableKey: SortKey, tooltipContent?: string }) => (
    <th 
      className="p-2.5 md:p-3 text-left font-semibold text-slate-400 text-xs uppercase tracking-wider cursor-pointer hover:bg-slate-800/50 hover:text-slate-200 transition-colors whitespace-nowrap group sticky top-0 bg-slate-900/90 backdrop-blur-md z-10 box-border border-b border-slate-800"
      onClick={() => handleSort(sortableKey)}
    >
      <div className="flex items-center space-x-1">
        {tooltipContent ? (
          <EducationTooltip content={tooltipContent} showIcon={false}>
            {label}
          </EducationTooltip>
        ) : (
          <span>{label}</span>
        )}
        <ArrowUpDown className={`w-3 h-3 ml-1 ${sortKey === sortableKey ? 'text-blue-400' : 'text-slate-600 opacity-0 group-hover:opacity-100'}`} />
      </div>
    </th>
  );

  return (
    <div className="bg-slate-900/40 border border-slate-800 rounded-xl overflow-hidden shadow-[0_4px_20px_-4px_rgba(0,0,0,0.5)] backdrop-blur-md flex flex-col">
      <div className="p-4 border-b border-slate-800 bg-slate-900/60 sticky top-0 z-20">
        <h3 className="text-sm font-semibold text-slate-300 tracking-widest uppercase flex items-center">
          <span className="w-2.5 h-2.5 rounded-full bg-indigo-500 mr-2 shadow-[0_0_8px_rgba(99,102,241,0.8)]"></span>
          Data Terminal
        </h3>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left relative min-w-[1000px]">
          <thead>
            <tr>
              <Th label="Ticker" sortableKey="Ticker" />
              <Th label="Company" sortableKey="Company" />
              <Th label="Price" sortableKey="Current Price" />
              <Th label="Int. Value" sortableKey="Intrinsic Value" tooltipContent={Definitions.intrinsicValue} />
              <Th label="MoS %" sortableKey="Margin of Safety" tooltipContent={Definitions.mos} />
              <Th label="ROIC" sortableKey="ROIC" tooltipContent={Definitions.roic} />
              <Th label="F-Score" sortableKey="Piotroski F-Score" tooltipContent={Definitions.fScore} />
              <Th label="Z-Score" sortableKey="Altman Z-Score" tooltipContent={Definitions.zScore} />
              <Th label="EV/FCF" sortableKey="EV/FCF Yield" tooltipContent={Definitions.evFcf} />
              <Th label="WACC" sortableKey="WACC" tooltipContent={Definitions.wacc} />
              <Th label="D/E" sortableKey="Debt/Equity" />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/50 font-mono">
            {sortedData.map((row, i) => (
              <tr key={`${row.Ticker}-${i}`} className="hover:bg-slate-800/60 transition-colors group">
                <td className="p-3 font-bold text-slate-200">{row.Ticker}</td>
                <td className="p-3 text-slate-400 font-sans text-xs truncate max-w-[140px]" title={row.Company}>{row.Company}</td>
                <td className="p-3 text-slate-300">{formatCurrency(row["Current Price"])}</td>
                <td className="p-3 text-slate-400">{formatCurrency(row["Intrinsic Value"])}</td>
                <td className={`p-3 ${getColorForMoS(row["Margin of Safety"])}`}>
                  {row["Margin of Safety"] !== null ? `${row["Margin of Safety"].toFixed(1)}%` : 'N/A'}
                </td>
                <td className="p-3 text-amber-400/90">{row.ROIC !== null ? `${row.ROIC.toFixed(1)}%` : 'N/A'}</td>
                <td className={`p-3 ${getColorForPiotroski(row["Piotroski F-Score"])}`}>
                  {row["Piotroski F-Score"] !== null ? row["Piotroski F-Score"] : 'N/A'}
                </td>
                <td className={`p-3 ${getColorForZScore(row["Altman Z-Score"])}`}>
                  {row["Altman Z-Score"] !== null ? row["Altman Z-Score"].toFixed(2) : 'N/A'}
                </td>
                <td className="p-3 text-slate-400">{row["EV/FCF Yield"] !== null ? `${row["EV/FCF Yield"].toFixed(1)}%` : 'N/A'}</td>
                <td className="p-3 text-slate-400">{row.WACC !== null ? `${row.WACC.toFixed(1)}%` : 'N/A'}</td>
                <td className="p-3 text-slate-500">{row["Debt/Equity"] !== null ? row["Debt/Equity"].toFixed(2) : 'N/A'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
