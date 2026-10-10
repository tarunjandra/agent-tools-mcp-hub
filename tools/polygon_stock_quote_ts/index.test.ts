import assert from "node:assert/strict";
import test from "node:test";
import { isForexTicker, nanosToMillis, normaliseTicker, parseSnapshot, toNumber } from "./index.ts";

// Polygon's snapshot payload as it actually arrives: `updated` in nanoseconds,
// day/prevDay bars beside todaysChange rather than inside them.

test("nanosToMillis converts Polygon's nanosecond stamps", () => {
  assert.equal(nanosToMillis(1_700_000_000_000_000_000), 1_700_000_000_000);
  assert.equal(nanosToMillis("1700000000000000000"), 1_700_000_000_000);
  assert.equal(nanosToMillis(undefined), 0);
  assert.equal(nanosToMillis("junk"), 0);
});

test("toNumber handles Polygon's numbers and strings", () => {
  assert.equal(toNumber(189.5), 189.5);
  assert.equal(toNumber("189.5"), 189.5);
  assert.equal(toNumber(null), 0);
  assert.equal(toNumber(undefined), 0);
  assert.equal(toNumber(NaN), 0);
});

test("forex tickers are recognised from the C: prefix or a bare pair", () => {
  assert.ok(isForexTicker("C:EURUSD"));
  assert.ok(isForexTicker("eurusd"));
  assert.ok(!isForexTicker("AAPL"));
  assert.ok(!isForexTicker("BRK.B"));
});

test("normaliseTicker prefixes a bare forex pair and leaves equities alone", () => {
  assert.equal(normaliseTicker("eurusd"), "C:EURUSD");
  assert.equal(normaliseTicker("c:eurusd"), "C:EURUSD");
  assert.equal(normaliseTicker("aapl"), "AAPL");
  assert.equal(normaliseTicker(" brk.b "), "BRK.B");
  assert.equal(normaliseTicker(""), "");
});

test("parseSnapshot reads the day bar, the change and the live price", () => {
  const quote = parseSnapshot(
    {
      status: "OK",
      ticker: {
        ticker: "AAPL",
        todaysChange: 1.2,
        todaysChangePerc: 0.64,
        updated: 1_700_000_000_000_000_000,
        day: { o: 188.9, h: 190.1, l: 188.2, c: 189.5, v: 1_234_567 },
        prevDay: { o: 188.0, h: 189.0, l: 187.5, c: 188.3, v: 987_654 },
        lastTrade: { p: 189.6, s: 100, t: 1_700_000_000_000_000_000 }
      }
    },
    "stocks"
  );
  assert.deepEqual(quote, {
    ticker: "AAPL",
    market: "stocks",
    price: 189.6,
    change: 1.2,
    change_percent: 0.64,
    open: 188.9,
    high: 190.1,
    low: 188.2,
    close: 189.5,
    volume: 1_234_567,
    prev_close: 188.3,
    updated: 1_700_000_000_000
  });
});

test("parseSnapshot falls back to the day close when there is no last trade", () => {
  const quote = parseSnapshot(
    { ticker: { ticker: "AAPL", updated: 1_700_000_000_000_000_000, day: { c: 189.5 } } },
    "stocks"
  );
  assert.equal(quote?.price, 189.5);
  assert.equal(quote?.change, null);
  assert.equal(quote?.change_percent, null);
  assert.equal(quote?.high, null);
});

test("parseSnapshot keeps a missing field null instead of a misleading zero", () => {
  const quote = parseSnapshot({ ticker: { ticker: "AAPL", day: { c: 0 } } }, "stocks");
  assert.equal(quote?.close, 0);
  assert.equal(quote?.open, null);
  assert.equal(quote?.prev_close, null);
  assert.equal(quote?.volume, null);
  assert.equal(quote?.updated, 0);
});

test("parseSnapshot returns null when the body carries no ticker", () => {
  assert.equal(parseSnapshot({ status: "OK" }, "stocks"), null);
  assert.equal(parseSnapshot(null, "stocks"), null);
  assert.equal(parseSnapshot({ ticker: "AAPL" }, "stocks"), null);
});

test("parseSnapshot tags the market it was asked for", () => {
  const quote = parseSnapshot({ ticker: { ticker: "C:EURUSD", day: {} } }, "forex");
  assert.equal(quote?.market, "forex");
  assert.equal(quote?.ticker, "C:EURUSD");
});
