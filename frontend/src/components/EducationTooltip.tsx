"use client";
import * as Tooltip from '@radix-ui/react-tooltip';
import { Info } from 'lucide-react';

export function EducationTooltip({ 
  children, 
  content,
  showIcon = true
}: { 
  children: React.ReactNode, 
  content: string,
  showIcon?: boolean
}) {
  return (
    <Tooltip.Provider delayDuration={150}>
      <Tooltip.Root>
        <Tooltip.Trigger asChild>
          <span className="flex items-center gap-1.5 cursor-help group relative">
            <span className="border-b border-dashed border-slate-600 pb-0.5 group-hover:border-slate-300 group-hover:text-slate-200 transition-colors">
              {children}
            </span>
            {showIcon && <Info className="w-3 h-3 text-slate-500 group-hover:text-amber-400 transition-colors shrink-0" />}
          </span>
        </Tooltip.Trigger>
        <Tooltip.Portal>
          <Tooltip.Content 
            className="z-[100] bg-slate-900 border border-slate-700 px-3 py-2.5 rounded-lg shadow-2xl text-[13px] max-w-[280px] font-sans text-slate-300 leading-relaxed shadow-[0_10px_30px_rgba(0,0,0,0.8)]" 
            sideOffset={8}
            side="top"
          >
            {content}
            <Tooltip.Arrow className="fill-slate-700" width={11} height={5} />
          </Tooltip.Content>
        </Tooltip.Portal>
      </Tooltip.Root>
    </Tooltip.Provider>
  );
}

export const Definitions = {
  mos: "How much cheaper the stock price is compared to its true Intrinsic Value. Buy when high.",
  intrinsicValue: "The true mathematical worth of the company based on its cash flows, totally ignoring market hype.",
  fScore: "A 9-point checklist of financial momentum. 9 is perfect. < 5 is a failing grade (a 'value trap').",
  zScore: "Predicts bankruptcy risk. > 2.99 is Safe. < 1.81 means high risk of distress.",
  roic: "Return on Invested Capital. Measures business quality. Shows how much profit the company generates for every dollar sunk into assets.",
  evFcf: "Enterprise Value to Free Cash Flow. How much cash yield you get for buying the entire company, including its debt.",
  wacc: "Weighted Average Cost of Capital. The dynamic discount rate used to value the company based on its true market risk (Beta).",
  totalScreened: "The total amount of equities successfully parsed and valued in this backend run.",
  topOpp: "The highest ranking opportunity calculated by multiplying the basic Proxy MoS by the ROIC."
};
