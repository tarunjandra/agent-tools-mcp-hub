const API = "https://api.coingecko.com/api/v3";

/**
 * CoinGecko mixes its number shapes: some fields are numbers, some are numeric
 * strings (market caps arrive as "1234567890.12"), and a few are null when the
 * coin is too new to have a value. Everything numeric goes through here so a
 * null or a string can never reach a caller as NaN.
 */
export function toNumber(value: unknown): number {
  if (typeof value === "number") return Number.isFinite(value) ? value : 0;
  if (typeof value !== "string") return 0;
  const parsed = Number.parseFloat(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

/**
 * `/search/trending` nests the 24h change as `{ usd: n }`, while the price
 * endpoints return it as a bare number. Both shapes reach this helper, and a
 * coin with no 24h figure reports `null` rather than a misleading 0 -- "flat"
 * and "unknown" must not read the same.
 */
export function percent24h(value: unknown): number | null {
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  if (value && typeof value === "object") {
    const usd = (value as Record<string, unknown>).usd;
    return typeof usd === "number" && Number.isFinite(usd) ? usd : null;
  }
  if (typeof value === "string") {
    const parsed = Number.parseFloat(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function str(value: unknown): string {
  return typeof value === "string" ? value : "";
}

export interface TrendingCoin {
  id: string;
  name: string;
  symbol: string;
  market_cap_rank: number | null;
  price_usd: number;
  change_24h_percent: number | null;
  thumb: string;
}

/**
 * Flatten the trending payload. Every entry is wrapped in an `item` object, and
 * the fields a caller wants are split between `item` (identity, market cap
 * rank) and `item.data` (price, 24h change) -- the two are merged here so the
 * caller does not have to know which half a value came from.
 *
 * A junk entry becomes a coin with empty strings rather than throwing, because
 * one malformed row should not lose the other fourteen.
 */
export function parseTrending(payload: unknown): TrendingCoin[] {
  const coins = (payload as { coins?: unknown })?.coins;
  const rows = Array.isArray(coins) ? coins : [];
  return rows.map((row) => {
    const item = ((row as { item?: unknown })?.item ?? {}) as Record<string, unknown>;
    const data = (item.data ?? {}) as Record<string, unknown>;
    const rank = item.market_cap_rank;
    return {
      id: str(item.id),
      name: str(item.name),
      symbol: str(item.symbol).toUpperCase(),
      market_cap_rank: typeof rank === "number" && Number.isFinite(rank) ? rank : null,
      price_usd: toNumber(data.price),
      change_24h_percent: percent24h(data.price_change_percentage_24h),
      thumb: str(item.thumb) || str(item.small)
    };
  });
}

export interface GlobalStats {
  total_market_cap_usd: number;
  total_volume_usd: number;
  market_cap_change_24h_percent: number;
  btc_dominance_percent: number;
  eth_dominance_percent: number;
  active_cryptocurrencies: number;
  markets: number;
  updated_at: number;
}

/**
 * The global figures live under a `data` wrapper, and the currency-keyed maps
 * (`total_market_cap`, `market_cap_percentage`) hold every fiat unit CoinGecko
 * tracks. Only USD is read, and only BTC/ETH dominance is surfaced -- the two
 * the issue asks for.
 */
export function parseGlobal(payload: unknown): GlobalStats {
  const d = ((payload as { data?: unknown })?.data ?? {}) as Record<string, unknown>;
  const caps = (d.total_market_cap ?? {}) as Record<string, unknown>;
  const volumes = (d.total_volume ?? {}) as Record<string, unknown>;
  const dominance = (d.market_cap_percentage ?? {}) as Record<string, unknown>;
  return {
    total_market_cap_usd: toNumber(caps.usd),
    total_volume_usd: toNumber(volumes.usd),
    market_cap_change_24h_percent: toNumber(d.market_cap_change_percentage_24h_usd),
    btc_dominance_percent: toNumber(dominance.btc),
    eth_dominance_percent: toNumber(dominance.eth),
    active_cryptocurrencies: toNumber(d.active_cryptocurrencies),
    markets: toNumber(d.markets),
    updated_at: toNumber(d.updated_at)
  };
}

export function clampLimit(value: unknown, fallback = 10): number {
  const parsed = typeof value === "number" ? value : Number.parseInt(String(value ?? ""), 10);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.min(50, Math.max(1, Math.trunc(parsed)));
}

export interface TrendingResult {
  success: boolean;
  data?: {
    trending: TrendingCoin[];
    global: GlobalStats;
    source: string;
  };
  error?: string;
}

async function request<T>(path: string): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API}${path}`, {
      headers: { Accept: "application/json" },
      signal: AbortSignal.timeout(15_000)
    });
  } catch (error) {
    throw new Error(
      `Network error contacting CoinGecko: ${error instanceof Error ? error.message : String(error)}`
    );
  }
  if (!response.ok) {
    // The free tier answers 429 with its own message; passing that through beats
    // a bare status code, since the fix is "wait", not "check your request".
    let detail = "";
    try {
      const body = (await response.json()) as { error?: string; status?: { error_message?: string } };
      detail = body?.status?.error_message || body?.error || "";
    } catch {
      detail = "";
    }
    throw new Error(`CoinGecko API returned HTTP ${response.status}${detail ? `: ${detail}` : ""}`);
  }
  return (await response.json()) as T;
}

/**
 * Fetch the coins trending in CoinGecko searches, alongside the global market
 * cap, 24h volume and BTC/ETH dominance.
 *
 * Both endpoints are on CoinGecko's public tier and need no key.
 *
 * @param limit Trending coins to return, 1-50, default 10.
 */
export async function runTool(limit: unknown = 10): Promise<TrendingResult> {
  const count = clampLimit(limit);
  try {
    const [trending, global] = await Promise.all([
      request<unknown>("/search/trending"),
      request<unknown>("/global")
    ]);
    return {
      success: true,
      data: {
        trending: parseTrending(trending).slice(0, count),
        global: parseGlobal(global),
        source: API
      }
    };
  } catch (error) {
    return { success: false, error: error instanceof Error ? error.message : String(error) };
  }
}

if (typeof require !== "undefined" && typeof module !== "undefined" && require.main === module) {
  runTool(process.argv[2] ?? 10).then((result) => console.log(JSON.stringify(result, null, 2)));
}
