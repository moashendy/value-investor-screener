export const formatCurrency = (val: number | null) => {
  if (val === null) return "N/A";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(val);
};

export const formatPercentNumber = (val: number | null) => {
  if (val === null) return "N/A";
  return new Intl.NumberFormat("en-US", {
    style: "percent",
    maximumFractionDigits: 1,
  }).format(val / 100);
};

export const getColorForPiotroski = (score: number | null) => {
  if (score === null) return "text-slate-400";
  if (score >= 7) return "text-emerald-400 font-bold";
  if (score >= 5) return "text-amber-400 font-semibold";
  return "text-rose-400 font-bold";
};

export const getColorForMoS = (mosValue: number | null) => {
  if (mosValue === null) return "text-slate-400";
  if (mosValue > 20) return "text-emerald-500 font-bold";
  if (mosValue > 0) return "text-emerald-400 font-semibold";
  return "text-rose-500 font-bold";
};

export const getColorForZScore = (score: number | null) => {
  if (score === null) return "text-slate-400";
  if (score < 1.81) return "text-rose-500 font-bold";
  if (score > 2.99) return "text-emerald-400";
  return "text-slate-300"; // Grey zone
};
