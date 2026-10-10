# Polygon.io Real-Time Stock Quote (TypeScript)

A TypeScript tool that returns a snapshot quote for a US equity or forex pair: current price, today's change and percentage, the day's open/high/low, volume and the previous close.

It uses Polygon.io's snapshot endpoints. The free tier covers delayed and end-of-day snapshots, which is enough for an agent checking where a symbol sits today.

## Prerequisites

A Polygon.io API key is required. Create one at [polygon.io/dashboard/api-keys](https://polygon.io/dashboard/api-keys) and either:

- Set it as the `POLYGON_API_KEY` environment variable, or
- Pass it as the `apiKey` parameter.

## Parameters

| Parameter | Type | Required | Description | Default |
| :--- | :--- | :--- | :--- | :--- |
| `ticker` | `string` | Yes | US equity (`AAPL`, `MSFT`) or forex pair (`C:EURUSD`, or a bare `EURUSD`) | — |
| `apiKey` | `string` | No | Polygon.io key; falls back to `POLYGON_API_KEY` | — |

## What it returns

- `price` — the last trade price, falling back to the day close outside trading hours
- `change`, `change_percent`, `prev_close`
- `open`, `high`, `low`, `close`, `volume`
- `updated` — epoch **milliseconds**
- `market` — `stocks` or `forex`, the endpoint the quote came from

A field Polygon has no value for is `null`, never `0`, so "not traded today" cannot be mistaken for a flat price.

## Usage

```ts
import { runTool } from "./index.ts";

const result = await runTool("AAPL");
if (result.success && result.data) {
  const q = result.data;
  console.log(`${q.ticker} ${q.price} (${q.change_percent}%)`);
  console.log(`day ${q.low} - ${q.high}, prev close ${q.prev_close}`);
} else {
  console.error(result.error);
}

// Forex works the same way.
const fx = await runTool("EURUSD");
```

### CLI

```bash
npm install
POLYGON_API_KEY=your_key_here npx ts-node index.ts AAPL
```

### Tests

```bash
npm test
```

## Notes

- **Timestamps are converted.** Polygon reports `updated` and every trade time in nanoseconds. Passed through raw, `new Date(...)` on that value is a year far outside the valid range, so it is divided down to milliseconds at the edge.
- **The ticker picks the endpoint.** Polygon serves equities and forex from different snapshot paths. `C:EURUSD` is the forex spelling, and a bare six-letter pair is prefixed for you, so `runTool("EURUSD")` resolves to the right market.
- **Errors keep Polygon's wording.** An invalid key comes back as `{ success: false, error: "Polygon.io returned HTTP 403: Unknown API Key" }` rather than a bare status code, because the fix differs per message.
- Free-tier quotes are delayed. Nothing here is a trading feed; it is a convenience lookup for an agent.
