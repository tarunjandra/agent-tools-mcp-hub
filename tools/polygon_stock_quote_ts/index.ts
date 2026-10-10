const API = "https://api.polygon.io";

/**
 * Polygon reports `updated` and every trade timestamp in NANOSECONDS. Handing
 * that straight back invites `new Date(1700000000000000000)`, which is a year
 * far outside the valid range; milliseconds is what a caller expects.
 */
export function nanosToMillis(value: unknown): number {
  const nanos = typeof value === "number" ? value : Number.parseFloat(String(value ?? ""));
  return Number.isFinite(nanos) ? Math.round(nanos / 1e6) : 0;
}

export function toNumber(value: unknown): number {
  if (typeof value === "number") return Number.isFinite(value) ? value : 0;
  if (typeof value !== "string") return 0;
  const parsed = Number.parseFloat(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function optNumber(value: unknown): number | null {
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  if (typeof value !== "string" || value.trim() === "") return null;
  const parsed = Number.parseFloat(value);
  return Number.isFinite(parsed) ? parsed : null;
}

/**
 * Polygon splits its snapshot endpoints by market, and the ticker itself says
 * which one to use: forex pairs are written `C:EURUSD`. A bare six-letter pair
 * (`EURUSD`) is what people type, so it is read as forex and prefixed; anything
 * else is treated as a US equity.
 */
export function isForexTicker(raw: string): boolean {
  const t = String(raw ?? "").trim().toUpperCase();
  return t.startsWith("C:") || /^[A-Z]{6}$/.test(t);
}

export function normaliseTicker(raw: string): string {
  const t = String(raw ?? "").trim().toUpperCase();
  if (!t) return "";
  if (t.startsWith("C:")) return t;
  if (/^[A-Z]{6}$/.test(t)) return `C:${t}`;
  return t;
}

export interface Quote {
  ticker: string;
  market: "stocks" | "forex";
  price: number;
  change: number | null;
  change_percent: number | null;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number | null;
  volume: number | null;
  prev_close: number | null;
  /** Epoch milliseconds, converted from Polygon's nanoseconds. */
  updated: number;
}

/**
 * Flatten the snapshot. `todaysChange` / `todaysChangePerc` sit beside the bar
 * data rather than inside it, and a ticker that has not traded today arrives
 * with an empty `day` object -- so every field is optional and a missing one
 * stays `null` instead of collapsing to a misleading 0.
 */
export function parseSnapshot(payload: unknown, market: "stocks" | "forex"): Quote | null {
  const ticker = (payload as { ticker?: unknown })?.ticker;
  if (!ticker || typeof ticker !== "object") return null;
  const t = ticker as Record<string, unknown>;
  const day = (t.day ?? {}) as Record<string, unknown>;
  const prevDay = (t.prevDay ?? {}) as Record<string, unknown>;
  const lastTrade = (t.lastTrade ?? {}) as Record<string, unknown>;

  const close = optNumber(day.c);
  const lastPrice = optNumber(lastTrade.p);
  const prevClose = optNumber(prevDay.c);
  const change = optNumber(t.todaysChange);
  const changePercent = optNumber(t.todaysChangePerc);

  return {
    ticker: typeof t.ticker === "string" ? t.ticker : "",
    market,
    // Prefer the last trade, which is the live price; the day close is the
    // fallback for a quote fetched outside trading hours.
    price: lastPrice ?? close ?? 0,
    change,
    change_percent: changePercent,
    open: optNumber(day.o),
    high: optNumber(day.h),
    low: optNumber(day.l),
    close,
    volume: optNumber(day.v),
    prev_close: prevClose,
    updated: nanosToMillis(t.updated)
  };
}

export interface PolygonQuoteResult {
  success: boolean;
  data?: Quote & { source: string };
  error?: string;
}

async function request<T>(path: string, apiKey: string): Promise<T> {
  const url = `${API}${path}${path.includes("?") ? "&" : "?"}apiKey=${encodeURIComponent(apiKey)}`;
  let response: Response;
  try {
    response = await fetch(url, {
      headers: { Accept: "application/json" },
      signal: AbortSignal.timeout(15_000)
    });
  } catch (error) {
    throw new Error(
      `Network error contacting Polygon.io: ${error instanceof Error ? error.message : String(error)}`
    );
  }
  if (!response.ok) {
    // Polygon puts the useful part -- "Unknown API Key", "NOT_AUTHORIZED" -- in
    // its own fields, so they are surfaced rather than reduced to the status.
    let detail = "";
    try {
      const body = (await response.json()) as { error?: string; message?: string };
      detail = body?.error || body?.message || "";
    } catch {
      detail = "";
    }
    throw new Error(`Polygon.io returned HTTP ${response.status}${detail ? `: ${detail}` : ""}`);
  }
  return (await response.json()) as T;
}

/**
 * Fetch a snapshot quote: current price, today's change and percentage, the
 * day's OHLC, volume and the previous close.
 *
 * Needs a Polygon.io API key (the free tier covers end-of-day and delayed
 * snapshots). Pass it in, or set POLYGON_API_KEY.
 *
 * @param ticker US equity (AAPL, MSFT) or forex pair (C:EURUSD, or just EURUSD).
 * @param apiKey Polygon.io key; falls back to the POLYGON_API_KEY env var.
 */
export async function runTool(ticker: string, apiKey?: string): Promise<PolygonQuoteResult> {
  const key = String(apiKey ?? process.env.POLYGON_API_KEY ?? "").trim();
  if (!key) {
    return {
      success: false,
      error:
        "A Polygon.io API key is required. Pass apiKey or set the POLYGON_API_KEY environment variable (https://polygon.io/dashboard/api-keys)."
    };
  }

  const symbol = normaliseTicker(ticker);
  if (!symbol || !/^(C:[A-Z]{6}|[A-Z][A-Z.\-]{0,9})$/.test(symbol)) {
    return {
      success: false,
      error: `ticker must be a US equity (AAPL) or a forex pair (C:EURUSD), got "${String(ticker ?? "")}".`
    };
  }

  const market: "stocks" | "forex" = isForexTicker(symbol) ? "forex" : "stocks";
  const path =
    market === "forex"
      ? `/v2/snapshot/locale/global/markets/forex/tickers/${encodeURIComponent(symbol)}`
      : `/v2/snapshot/locale/us/markets/stocks/tickers/${encodeURIComponent(symbol)}`;

  try {
    const payload = await request<unknown>(path, key);
    const quote = parseSnapshot(payload, market);
    if (!quote) {
      // A 200 with no `ticker` body means the symbol resolved to nothing.
      return { success: false, error: `No snapshot returned for "${symbol}". Check the ticker.` };
    }
    return { success: true, data: { ...quote, source: API } };
  } catch (error) {
    return { success: false, error: error instanceof Error ? error.message : String(error) };
  }
}

if (typeof require !== "undefined" && typeof module !== "undefined" && require.main === module) {
  runTool(process.argv[2] ?? "AAPL", process.argv[3]).then((result) =>
    console.log(JSON.stringify(result, null, 2))
  );
}
