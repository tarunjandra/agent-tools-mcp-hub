const API = "https://api.binance.com/api/v3";

/**
 * Binance returns every numeric field as a STRING, including the two-element
 * arrays of the depth book ("95000.00000000", "1.50000000"). Number() on those
 * works, but a missing or empty field must not become NaN and silently poison
 * every downstream calculation, so parsing goes through here.
 */
export function toNumber(value: unknown): number {
  if (typeof value === "number") return Number.isFinite(value) ? value : 0;
  if (typeof value !== "string") return 0;
  const parsed = Number.parseFloat(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

/** One price level of the order book, as Binance sends it: [price, quantity]. */
type RawLevel = [string, string];

export interface DepthLevel {
  price: number;
  quantity: number;
}

export interface DepthSide {
  price: number;
  quantity: number;
  /** Quantity summed across the returned levels. */
  depth_base: number;
  /** Cumulative notional (price x quantity) across the returned levels. */
  depth_quote: number;
  levels: DepthLevel[];
}

/**
 * Turn one side of the book into its top `limit` levels plus the totals a
 * trading agent actually asks for. Binance already returns the book sorted --
 * bids descending, asks ascending -- so the order is kept rather than re-sorted,
 * and rows it cannot parse are dropped instead of counted as a zero level.
 */
export function parseDepthSide(levels: unknown, limit: number): DepthSide {
  const rows = Array.isArray(levels) ? (levels as RawLevel[]) : [];
  const parsed: DepthLevel[] = [];
  for (const row of rows) {
    if (!Array.isArray(row) || row.length < 2) continue;
    parsed.push({ price: toNumber(row[0]), quantity: toNumber(row[1]) });
  }
  const kept = parsed.slice(0, Math.max(0, limit));
  return {
    price: kept[0]?.price ?? 0,
    quantity: kept[0]?.quantity ?? 0,
    depth_base: Number(kept.reduce((sum, level) => sum + level.quantity, 0).toFixed(8)),
    depth_quote: Number(kept.reduce((sum, level) => sum + level.price * level.quantity, 0).toFixed(2)),
    levels: kept
  };
}

export interface TickerStats {
  price: number;
  change_24h: number;
  change_24h_percent: number;
  high_24h: number;
  low_24h: number;
  open_24h: number;
  volume_24h_base: number;
  volume_24h_quote: number;
  bid: number;
  ask: number;
}

/** The 24h statistics, mapped off Binance's string-valued ticker payload. */
export function parseTicker(ticker: Record<string, unknown>): TickerStats {
  return {
    price: toNumber(ticker.lastPrice),
    change_24h: toNumber(ticker.priceChange),
    change_24h_percent: toNumber(ticker.priceChangePercent),
    high_24h: toNumber(ticker.highPrice),
    low_24h: toNumber(ticker.lowPrice),
    open_24h: toNumber(ticker.openPrice),
    volume_24h_base: toNumber(ticker.volume),
    volume_24h_quote: toNumber(ticker.quoteVolume),
    bid: toNumber(ticker.bidPrice),
    ask: toNumber(ticker.askPrice)
  };
}

export interface RecentTrade {
  price: number;
  quantity: number;
  quote_quantity: number;
  time: number;
  side: "buy" | "sell";
}

/**
 * Recent trades, normalised. `isBuyerMaker` is the aggressor flag: a maker
 * buyer means the SELLER hit the bid, so the trade reads as a sell.
 */
export function parseTrades(trades: unknown, limit: number): RecentTrade[] {
  const rows = Array.isArray(trades) ? (trades as Array<Record<string, unknown>>) : [];
  return rows.slice(0, Math.max(0, limit)).map((trade) => ({
    price: toNumber(trade.price),
    quantity: toNumber(trade.qty),
    quote_quantity: toNumber(trade.quoteQty),
    time: toNumber(trade.time),
    side: trade.isBuyerMaker ? "sell" : "buy"
  }));
}

/**
 * Binance symbols are upper-case and have no separator: BTCUSDT, ETHBTC. Accept
 * the forms people write (btcusdt, BTC/USDT, btc-usdt) and normalise the rest,
 * so a rejected symbol is clearly rejected rather than silently queried as an
 * empty string.
 */
export function normaliseSymbol(raw: string): string {
  return String(raw ?? "").trim().toUpperCase().replace(/[/\-_\s]/g, "");
}

export function clampLimit(value: unknown, fallback = 10): number {
  const parsed = typeof value === "number" ? value : Number.parseInt(String(value ?? ""), 10);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.min(100, Math.max(1, Math.trunc(parsed)));
}

export interface BinanceTickerResult {
  success: boolean;
  data?: {
    symbol: string;
    price: number;
    change_24h: number;
    change_24h_percent: number;
    high_24h: number;
    low_24h: number;
    open_24h: number;
    volume_24h_base: number;
    volume_24h_quote: number;
    best_bid: number;
    best_ask: number;
    spread: number;
    bids: DepthSide;
    asks: DepthSide;
    recent_trades: RecentTrade[];
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
      `Network error contacting Binance: ${error instanceof Error ? error.message : String(error)}`
    );
  }
  if (!response.ok) {
    // Binance answers an unknown symbol or a bad limit with 400 and a JSON
    // body; surfacing its own message is far more useful than the status alone.
    let detail = "";
    try {
      const body = (await response.json()) as { msg?: string };
      detail = body?.msg ? `: ${body.msg}` : "";
    } catch {
      detail = "";
    }
    throw new Error(`Binance API returned HTTP ${response.status}${detail}`);
  }
  return (await response.json()) as T;
}

/**
 * Fetch a spot pair's 24h statistics, L2 order-book depth and recent trades.
 *
 * The Binance spot REST API needs no key and no signing for these three
 * endpoints, so the tool works out of the box; it is read-only and public.
 *
 * @param symbol Trading pair, e.g. BTCUSDT (or btc-usdt, BTC/USDT).
 * @param limit  Depth levels and trades to return per side. 1-100, default 10.
 */
export async function runTool(symbol: string, limit: unknown = 10): Promise<BinanceTickerResult> {
  const pair = normaliseSymbol(symbol);
  if (!/^[A-Z0-9]{5,24}$/.test(pair)) {
    return {
      success: false,
      error: `symbol must be a Binance spot pair such as BTCUSDT (got "${String(symbol ?? "")}").`
    };
  }
  const depth = clampLimit(limit);

  try {
    const [ticker, book, trades] = await Promise.all([
      request<Record<string, unknown>>(`/ticker/24hr?symbol=${encodeURIComponent(pair)}`),
      request<{ bids?: unknown; asks?: unknown }>(
        `/depth?symbol=${encodeURIComponent(pair)}&limit=${depth}`
      ),
      request<unknown>(`/trades?symbol=${encodeURIComponent(pair)}&limit=${depth}`)
    ]);

    const stats = parseTicker(ticker);
    const bids = parseDepthSide(book?.bids, depth);
    const asks = parseDepthSide(book?.asks, depth);
    const bestBid = stats.bid || bids.price;
    const bestAsk = stats.ask || asks.price;

    return {
      success: true,
      data: {
        symbol: pair,
        price: stats.price,
        change_24h: stats.change_24h,
        change_24h_percent: stats.change_24h_percent,
        high_24h: stats.high_24h,
        low_24h: stats.low_24h,
        open_24h: stats.open_24h,
        volume_24h_base: stats.volume_24h_base,
        volume_24h_quote: stats.volume_24h_quote,
        best_bid: bestBid,
        best_ask: bestAsk,
        spread: Number((bestAsk - bestBid).toFixed(8)),
        bids,
        asks,
        recent_trades: parseTrades(trades, depth),
        source: "https://api.binance.com/api/v3"
      }
    };
  } catch (error) {
    return { success: false, error: error instanceof Error ? error.message : String(error) };
  }
}

if (typeof require !== "undefined" && typeof module !== "undefined" && require.main === module) {
  runTool(process.argv[2] ?? "BTCUSDT", process.argv[3] ?? 10).then((result) =>
    console.log(JSON.stringify(result, null, 2))
  );
}
