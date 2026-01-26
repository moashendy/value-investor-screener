import Papa from 'papaparse';

export interface StockData {
  Ticker: string;
  Company: string;
  Sector: string;
  "Current Price": number | null;
  "Intrinsic Value": number | null;
  "Margin of Safety": number | null;
  "MoS %": string;
  "MoS Band": string;
  "Piotroski F-Score": number | null;
  ROIC: number | null;
  "EV/FCF Yield": number | null;
  "Normalized EPS": number | null;
  "Interest Coverage": string;
  "Debt/Equity": number | null;
  "Altman Z-Score": number | null;
  "WACC": number | null;
}

const parseNumber = (val: string | undefined): number | null => {
  if (!val || val === "N/A" || val.trim() === "") return null;
  const parsed = parseFloat(val.replace(/[%,]/g, ""));
  return isNaN(parsed) ? null : parsed;
};

export const fetchData = async (): Promise<StockData[]> => {
  try {
    // Append timestamp to strictly bypass browser/Next.js memory caches when refreshing data
    const url = `/data/latest_screener.csv?t=${Date.now()}`;
    const response = await fetch(url, { cache: "no-store" });
    const csvText = await response.text();
    
    return new Promise((resolve, reject) => {
      Papa.parse(csvText, {
        header: true,
        skipEmptyLines: true,
        complete: (results) => {
          const formatted = results.data.map((row: any) => ({
            Ticker: row.Ticker || "Unknown",
            Company: row.Company || "Unknown",
            Sector: row.Sector || "Unknown",
            "Current Price": parseNumber(row["Current Price"]),
            "Intrinsic Value": parseNumber(row["Intrinsic Value"]),
            "Margin of Safety": parseNumber(row["Margin of Safety"]),
            "MoS %": row["MoS %"] || "N/A",
            "MoS Band": row["MoS Band"] || "N/A",
            "Piotroski F-Score": parseNumber(row["Piotroski F-Score"]),
            ROIC: parseNumber(row["ROIC"]),
            "EV/FCF Yield": parseNumber(row["EV/FCF Yield"]),
            "Normalized EPS": parseNumber(row["Normalized EPS"]),
            "Interest Coverage": row["Interest Coverage"] || "N/A",
            "Debt/Equity": parseNumber(row["Debt/Equity"]),
            "Altman Z-Score": parseNumber(row["Altman Z-Score"]),
            "WACC": parseNumber(row["WACC"]),
          }));
          resolve(formatted);
        },
        error: (error: Error) => {
          console.error("CSV Parse Error: ", error);
          reject(error);
        },
      });
    });
  } catch (error) {
    console.error("Failed to fetch or parse CSV:", error);
    return [];
  }
};
