import assert from "node:assert/strict";
import test from "node:test";
import { clampLimit, normaliseSymbol, parseDepthSide, parseTicker, parseTrades, toNumber } from "./index.ts";

// Binance sends every number as a string, so the fixtures below keep them as
// strings on purpose: a test that passed JS numbers here would not exercise the
// parsing that the live API depends on.

test("toNumber reads Binance's string numbers and rejects junk", () => {
  assert.equal(toNumber("95000.00000000"), 95000);
  assert.equal(toNumber("-1.25"), -1.25);
  assert.equal(toNumber(42), 42);
  assert.equal(toNumber(""), 0);
  assert.equal(toNumber("abc"), 0);
  assert.equal(toNumber(null), 0);
  assert.equal(toNumber(undefined), 0);
  assert.equal(toNumber(NaN), 0);
});

test("parseDepthSide keeps Binance's order and totals the levels", () => {
  const side = parseDepthSide(
    [
      ["95000.00", "1.5"],
      ["94999.00", "2.0"],
      ["94998.00", "0.5"]
    ],
    3
  );
  assert.deepEqual(side.levels.map((level) => level.price), [95000, 94999, 94998]);
  assert.equal(side.price, 95000);
  assert.equal(side.quantity, 1.5);
  assert.equal(side.depth_base, 4);
  assert.equal(side.depth_quote, 95000 * 1.5 + 94999 * 2 + 94998 * 0.5);
});

test("parseDepthSide stops at the requested limit", () => {
  const side = parseDepthSide([["10", "1"], ["9", "1"], ["8", "1"], ["7", "1"]], 2);
  assert.equal(side.levels.length, 2);
  assert.equal(side.depth_base, 2);
});

test("parseDepthSide drops rows it cannot read instead of counting a zero level", () => {
  const side = parseDepthSide([["10", "1"], null, ["11"], ["9", "2"]], 5);
  assert.equal(side.levels.length, 2);
  assert.deepEqual(side.levels.map((level) => level.price), [10, 9]);
});

test("parseDepthSide tolerates a body that is not an array", () => {
  assert.deepEqual(parseDepthSide(undefined, 5).levels, []);
  assert.equal(parseDepthSide({}, 5).depth_base, 0);
});

test("parseTicker maps every 24h statistic off the string payload", () => {
  const stats = parseTicker({
    lastPrice: "95000.00",
    priceChange: "-500.00",
    priceChangePercent: "-0.52",
    highPrice: "96000.00",
    lowPrice: "94000.00",
    openPrice: "95500.00",
    volume: "1234.5",
    quoteVolume: "117000000.00",
    bidPrice: "94999.00",
    askPrice: "95001.00"
  });
  assert.deepEqual(stats, {
    price: 95000,
    change_24h: -500,
    change_24h_percent: -0.52,
    high_24h: 96000,
    low_24h: 94000,
    open_24h: 95500,
    volume_24h_base: 1234.5,
    volume_24h_quote: 117000000,
    bid: 94999,
    ask: 95001
  });
});

test("parseTicker falls back to zero on a partial payload", () => {
  assert.equal(parseTicker({ lastPrice: "10" }).high_24h, 0);
});

test("parseTrades maps isBuyerMaker to the aggressor side", () => {
  const trades = parseTrades(
    [
      { price: "95000.00", qty: "0.01", quoteQty: "950.00", time: 1_700_000_000_000, isBuyerMaker: true },
      { price: "95001.00", qty: "0.02", quoteQty: "1900.02", time: 1_700_000_001_000, isBuyerMaker: false }
    ],
    10
  );
  // A buyer that is the maker means the SELLER hit the bid, so it reads as a sell.
  assert.equal(trades[0].side, "sell");
  assert.equal(trades[1].side, "buy");
  assert.equal(trades[0].price, 95000);
  assert.equal(trades[1].quote_quantity, 1900.02);
});

test("parseTrades honours the limit and tolerates a non-array body", () => {
  const rows = Array.from({ length: 5 }, (_, i) => ({ price: "1", qty: "1", isBuyerMaker: false }));
  assert.equal(parseTrades(rows, 2).length, 2);
  assert.deepEqual(parseTrades(null, 5), []);
});

test("normaliseSymbol accepts the shapes people write", () => {
  assert.equal(normaliseSymbol("btcusdt"), "BTCUSDT");
  assert.equal(normaliseSymbol(" BTC/USDT "), "BTCUSDT");
  assert.equal(normaliseSymbol("btc-usdt"), "BTCUSDT");
  assert.equal(normaliseSymbol("eth_btc"), "ETHBTC");
  assert.equal(normaliseSymbol(""), "");
});

test("clampLimit holds the 1-100 range Binance accepts", () => {
  assert.equal(clampLimit(10), 10);
  assert.equal(clampLimit("25"), 25);
  assert.equal(clampLimit(0), 1);
  assert.equal(clampLimit(-5), 1);
  assert.equal(clampLimit(500), 100);
  assert.equal(clampLimit("abc"), 10);
  assert.equal(clampLimit(undefined), 10);
  assert.equal(clampLimit(7.9), 7);
});
