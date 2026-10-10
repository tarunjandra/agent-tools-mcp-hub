# Binance Spot Ticker & Order Book (TypeScript)

A TypeScript tool that returns 24h price statistics, L2 order-book depth (bids/asks) and recent trades for any Binance spot pair.

It uses the Binance public spot REST API (`/api/v3`), which needs **no API key** and no signing for these endpoints, so the tool runs out of the box. It is read-only.

## Parameters

| Parameter | Type | Required | Description | Default |
| :--- | :--- | :--- | :--- | :--- |
| `symbol` | `string` | Yes | Binance spot pair, e.g. `BTCUSDT` or `ETHUSDT`. `BTC/USDT` and `btc-usdt` are normalised for you | — |
| `limit` | `number` | No | Order-book levels and recent trades to return per side, `1`-`100` | `10` |

## What it returns

- `price`, `change_24h`, `change_24h_percent`, `open_24h`, `high_24h`, `low_24h`
- `volume_24h_base` and `volume_24h_quote`
- `best_bid`, `best_ask` and `spread`
- `bids` / `asks`, each with the top `limit` `levels`, plus `depth_base` and `depth_quote` summed across them
- `recent_trades`, each tagged `buy` or `sell` by the aggressor side

Every numeric field is returned as a number. Binance sends them as strings, so they are parsed at the edge — a malformed level is dropped rather than counted as a zero.

## Usage

```ts
import { runTool } from "./index.ts";

const result = await runTool("BTCUSDT", 5);
if (result.success && result.data) {
  const d = result.data;
  console.log(`${d.symbol}: ${d.price} (${d.change_24h_percent}% 24h)`);
  console.log(`bid ${d.best_bid} / ask ${d.best_ask} spread ${d.spread}`);
  console.log(`top bid ${d.bids.levels[0].price} x ${d.bids.levels[0].quantity}`);
} else {
  console.error(result.error);
}
```

### CLI

```bash
npm install
npx ts-node index.ts BTCUSDT 5
```

### Tests

```bash
npm test
```

## Notes

- Both sides of the book are requested at the same `limit`, so `depth_base` and `depth_quote` describe equal-depth amounts and can be compared directly.
- `recent_trades[].side` is the **aggressor** side. Binance reports `isBuyerMaker`, and a maker buyer means the seller crossed the spread, so that trade is labelled a sell.
- A low-liquidity pair can answer with an empty book; the tool reports zero levels rather than failing.
