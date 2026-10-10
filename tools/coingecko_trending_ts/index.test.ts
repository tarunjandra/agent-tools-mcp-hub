import assert from "node:assert/strict";
import test from "node:test";
import { clampLimit, parseGlobal, parseTrending, percent24h, toNumber } from "./index.ts";

// CoinGecko's payload is reproduced here in the shapes it actually sends: the
// trending entry wraps everything in `item`, nests the 24h change under
// `price_change_percentage_24h.usd`, and stringifies the market caps.

test("toNumber reads CoinGecko's numeric strings and rejects junk", () => {
  assert.equal(toNumber("1234567890.12"), 1234567890.12);
  assert.equal(toNumber(42), 42);
  assert.equal(toNumber(null), 0);
  assert.equal(toNumber(""), 0);
  assert.equal(toNumber("n/a"), 0);
  assert.equal(toNumber(NaN), 0);
});

test("percent24h unwraps the nested usd object the trending endpoint sends", () => {
  assert.equal(percent24h({ usd: 5.67 }), 5.67);
  assert.equal(percent24h(-3.2), -3.2);
  assert.equal(percent24h("-1.5"), -1.5);
});

test("percent24h reports null rather than a misleading zero", () => {
  // A coin with no 24h figure must not read as "flat".
  assert.equal(percent24h(null), null);
  assert.equal(percent24h(undefined), null);
  assert.equal(percent24h({}), null);
  assert.equal(percent24h({ usd: null }), null);
  assert.equal(percent24h("abc"), null);
  assert.equal(percent24h(NaN), null);
});

test("parseTrending merges item and item.data into one flat coin", () => {
  const coins = parseTrending({
    coins: [
      {
        item: {
          id: "bitcoin",
          name: "Bitcoin",
          symbol: "btc",
          market_cap_rank: 1,
          thumb: "https://example.test/btc.png",
          data: { price: 95000.5, price_change_percentage_24h: { usd: 1.25 } }
        }
      }
    ]
  });
  assert.deepEqual(coins, [
    {
      id: "bitcoin",
      name: "Bitcoin",
      symbol: "BTC",
      market_cap_rank: 1,
      price_usd: 95000.5,
      change_24h_percent: 1.25,
      thumb: "https://example.test/btc.png"
    }
  ]);
});

test("parseTrending keeps a coin whose rank is missing", () => {
  const coins = parseTrending({
    coins: [{ item: { id: "newcoin", name: "New", symbol: "new", market_cap_rank: null, data: { price: "0.01", price_change_percentage_24h: { usd: 300 } } } }]
  });
  assert.equal(coins[0].market_cap_rank, null);
  assert.equal(coins[0].price_usd, 0.01);
  assert.equal(coins[0].change_24h_percent, 300);
});

test("parseTrending falls back to the small icon when there is no thumb", () => {
  const coins = parseTrending({ coins: [{ item: { id: "x", small: "https://example.test/s.png" } }] });
  assert.equal(coins[0].thumb, "https://example.test/s.png");
});

test("parseTrending survives a malformed row without losing the others", () => {
  const coins = parseTrending({ coins: [{ item: { id: "ok", symbol: "ok" } }, null, "junk"] });
  assert.equal(coins.length, 3);
  assert.equal(coins[0].id, "ok");
  assert.equal(coins[1].id, "");
  assert.equal(coins[2].name, "");
});

test("parseTrending tolerates a body with no coins array", () => {
  assert.deepEqual(parseTrending(undefined), []);
  assert.deepEqual(parseTrending({}), []);
  assert.deepEqual(parseTrending({ coins: "nope" }), []);
});

test("parseGlobal reads the usd slices and the BTC/ETH dominance", () => {
  const stats = parseGlobal({
    data: {
      active_cryptocurrencies: 17000,
      markets: 1200,
      total_market_cap: { usd: 3500000000000, eur: 3200000000000 },
      total_volume: { usd: 150000000000 },
      market_cap_percentage: { btc: 54.3, eth: 12.1, usdt: 4.2 },
      market_cap_change_percentage_24h_usd: -1.42,
      updated_at: 1700000000
    }
  });
  assert.deepEqual(stats, {
    total_market_cap_usd: 3500000000000,
    total_volume_usd: 150000000000,
    market_cap_change_24h_percent: -1.42,
    btc_dominance_percent: 54.3,
    eth_dominance_percent: 12.1,
    active_cryptocurrencies: 17000,
    markets: 1200,
    updated_at: 1700000000
  });
});

test("parseGlobal returns zeros on an empty body instead of throwing", () => {
  const stats = parseGlobal({});
  assert.equal(stats.total_market_cap_usd, 0);
  assert.equal(stats.btc_dominance_percent, 0);
});

test("clampLimit holds the 1-50 range the free tier tolerates", () => {
  assert.equal(clampLimit(10), 10);
  assert.equal(clampLimit("7"), 7);
  assert.equal(clampLimit(0), 1);
  assert.equal(clampLimit(999), 50);
  assert.equal(clampLimit("abc"), 10);
  assert.equal(clampLimit(undefined), 10);
  assert.equal(clampLimit(3.9), 3);
});
