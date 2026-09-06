"use client";
import { useMemo, useState } from "react";
import { StockData } from "@/lib/data-parser";
import { formatCurrency, getColorForPiotroski, getColorForMoS } from "@/lib/formatters";
import { ArrowUpDown, ExternalLink, Search, ShieldAlert } from "lucide-react";
import { EducationTooltip, Definitions } from "./EducationTooltip";

type SortKey = keyof StockData;

export function ScreenerGrid({ data }: { data: StockData[] }) {
  const [sortKey, setSortKey] = useState<SortKey>("Margin of Safety");
  const [sortAsc, setSortAsc] = useState(false);
  const [alertFilter, setAlertFilter] = useState("ALL");
  const [query, setQuery] = useState("");

  const sortedData = useMemo(() => data.filter((row) => {
    const matchesAlert = alertFilter === "ALL" || row["Alert Status"].startsWith(alertFilter);
    const needle = query.trim().toLowerCase();
    const matchesQuery = !needle || row.Ticker.toLowerCase().includes(needle)
      || row.Company.toLowerCase().includes(needle) || row.Sector.toLowerCase().includes(needle);
    return matchesAlert && matchesQuery;
  }).sort((a, b) => {
    let aVal = a[sortKey];
    let bVal = b[sortKey];

    if (aVal === null) aVal = -Infinity;
    if (bVal === null) bVal = -Infinity;

    if (typeof aVal === 'string' && typeof bVal === 'string') {
      return sortAsc ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
    }
    
    return sortAsc ? (aVal as number) - (bVal as number) : (bVal as number) - (aVal as number);
  }), [alertFilter, data, query, sortAsc, sortKey]);

  if (!data || data.length === 0) return null;

  const alertBadge = (status: string) => {
    if (status.startsWith("BUY-ZONE")) return "border-emerald-500/40 bg-emerald-500/10 text-emerald-300";
    if (status.startsWith("NEAR")) return "border-amber-500/40 bg-amber-500/10 text-amber-300";
    return "border-slate-700 bg-slate-800/60 text-slate-400";
  };

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortAsc(!sortAsc);
    } else {
      setSortKey(key);
      setSortAsc(false);
    }
  };

  const renderHeader = (label: string, sortableKey: SortKey, tooltipContent?: string) => (
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
      <div className="p-4 border-b border-slate-800 bg-slate-900/60 flex flex-col lg:flex-row lg:items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-300 tracking-widest uppercase flex items-center">
            <span className="w-2.5 h-2.5 rounded-full bg-indigo-500 mr-2 shadow-[0_0_8px_rgba(99,102,241,0.8)]"></span>
            Eligible Research Watchlist
          </h3>
          <p className="text-xs text-slate-500 mt-1">{sortedData.length} of {data.length} names shown</p>
        </div>
        <div className="flex flex-col sm:flex-row gap-2">
          <div className="flex rounded-lg border border-slate-700 overflow-hidden" aria-label="Filter by alert status">
            {["ALL", "BUY-ZONE", "NEAR", "WAIT"].map((filter) => (
              <button key={filter} type="button" onClick={() => setAlertFilter(filter)}
                className={`px-3 py-2 text-[11px] font-mono transition-colors ${alertFilter === filter ? "bg-indigo-500/20 text-indigo-200" : "bg-slate-900 text-slate-500 hover:text-slate-300"}`}>
                {filter}
              </button>
            ))}
          </div>
          <label className="relative">
            <span className="sr-only">Search ticker, company or sector</span>
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search watchlist"
              className="w-full sm:w-56 rounded-lg border border-slate-700 bg-slate-950 py-2 pl-9 pr-3 text-xs text-slate-200 outline-none placeholder:text-slate-600 focus:border-indigo-500" />
          </label>
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left relative min-w-[1450px]">
          <thead>
            <tr>
              {renderHeader("Ticker", "Ticker")}
              {renderHeader("Company", "Company")}
              {renderHeader("Status", "Alert Status")}
              {renderHeader("Price", "Current Price")}
              {renderHeader("20% Entry", "Research Entry Price (20% MoS)", "Research entry price equals 80% of conservative intrinsic value.")}
              {renderHeader("Above Entry", "Price Premium to Entry")}
              {renderHeader("Int. Value", "Intrinsic Value", Definitions.intrinsicValue)}
              {renderHeader("MoS %", "Margin of Safety", Definitions.mos)}
              {renderHeader("Model", "Sector Model")}
              {renderHeader("ROIC", "ROIC", Definitions.roic)}
              {renderHeader("F-Score", "Piotroski F-Score", Definitions.fScore)}
              {renderHeader("Verify", "Verification Required")}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/50 font-mono">
            {sortedData.map((row, i) => (
              <tr key={`${row.Ticker}-${i}`} className="hover:bg-slate-800/60 transition-colors group">
                <td className="p-3 font-bold text-slate-200">
                  {row["Source URL"] ? <a href={row["Source URL"]} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 hover:text-indigo-300">{row.Ticker}<ExternalLink className="h-3 w-3" /></a> : row.Ticker}
                </td>
                <td className="p-3 text-slate-400 font-sans text-xs truncate max-w-[140px]" title={row.Company}>{row.Company}</td>
                <td className="p-3"><span className={`inline-flex rounded-md border px-2 py-1 text-[10px] font-bold tracking-wide ${alertBadge(row["Alert Status"])}`}>{row["Alert Status"].split(":")[0]}</span></td>
                <td className="p-3 text-slate-300">{formatCurrency(row["Current Price"])}</td>
                <td className="p-3 text-emerald-300/80">{formatCurrency(row["Research Entry Price (20% MoS)"])}</td>
                <td className="p-3 text-amber-300/80">{row["Price Premium to Entry"] !== null ? `${row["Price Premium to Entry"].toFixed(1)}%` : "N/A"}</td>
                <td className="p-3 text-slate-400">{formatCurrency(row["Intrinsic Value"])}</td>
                <td className={`p-3 ${getColorForMoS(row["Margin of Safety"])}`}>
                  {row["Margin of Safety"] !== null ? `${row["Margin of Safety"].toFixed(1)}%` : 'N/A'}
                </td>
                <td className="p-3 text-xs text-blue-300 uppercase">{row["Sector Model"].replace("_", " ")}</td>
                <td className="p-3 text-amber-400/90">{row.ROIC !== null ? `${row.ROIC.toFixed(1)}%` : 'N/A'}</td>
                <td className={`p-3 ${getColorForPiotroski(row["Piotroski F-Score"])}`}>
                  {row["Piotroski F-Score"] !== null ? row["Piotroski F-Score"] : 'N/A'}
                </td>
                <td className="p-3 max-w-[280px]">
                  {row["Verification Required"] ? (
                    <span title={row["Verification Required"]} className="flex items-start gap-1.5 text-xs text-amber-300/80 font-sans cursor-help"><ShieldAlert className="h-4 w-4 shrink-0" /><span className="line-clamp-2">{row["Verification Required"]}</span></span>
                  ) : <span className="text-xs text-slate-600 font-sans">Standard filing review</span>}
                </td>
              </tr>
            ))}
            {sortedData.length === 0 && (
              <tr><td colSpan={12} className="p-8 text-center text-slate-500 font-sans">No names match these filters.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
