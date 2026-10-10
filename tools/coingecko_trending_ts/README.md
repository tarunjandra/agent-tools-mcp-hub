# CoinGecko Trending Coins & Global Market Stats (TypeScript)

A TypeScript tool that returns the coins trending in CoinGecko searches, alongside the global crypto market cap, 24h volume and BTC/ETH dominance.

It uses CoinGecko's free public API (`/search/trending` and `/global`), which needs **no API key**, so the tool runs out of the box. It is read-only.

## Parameters

| Parameter | Type | Required | Description | Default |
| :--- | :--- | :--- | :--- | :--- |
| `limit` | `number` | No | How many trending coins to return, `1`-`50` | `10` |

## What it returns

`data.trending[]`, one entry per coin:

- `id`, `name`, `symbol`, `thumb`
- `market_cap_rank` — `null` for a coin too new to be ranked
- `price_usd`
- `change_24h_percent` — `null` when CoinGecko has no 24h figure, so "flat" and "unknown" do not read the same

`data.global`:

- `total_market_cap_usd`, `total_volume_usd`, `market_cap_change_24h_percent`
- `btc_dominance_percent`, `eth_dominance_percent`
- `active_cryptocurrencies`, `markets`, `updated_at`

CoinGecko nests the 24h change as `{ usd: n }` on this endpoint but as a bare number elsewhere, and sends market caps as strings; both shapes are handled, so a caller always gets numbers or `null`.

## Usage

```ts
import { runTool } from "./index.ts";

const result = await runTool(5);
if (result.success && result.data) {
  for (const coin of result.data.trending) {
    const change = coin.change_24h_percent ?? "n/a";
    console.log(`#${coin.market_cap_rank ?? "?"} ${coin.symbol} $${coin.price_usd} (${change}% 24h)`);
  }
  const g = result.data.global;
  console.log(`market cap $${g.total_market_cap_usd}, BTC dominance ${g.btc_dominance_percent}%`);
} else {
  console.error(result.error);
}
```

### CLI

```bash
npm install
npx ts-node index.ts 5
```

### Tests

```bash
npm test
```

## Notes

- The free tier is rate limited. A `429` comes back as `{ success: false, error: "CoinGecko API returned HTTP 429: ..." }` carrying CoinGecko's own message, since the fix is to wait rather than to change the request.
- Trending rank is a **search** ranking, not market cap. `market_cap_rank` is the separate, real figure; the two are often very different for a coin that just spiked.
- Global dominance is read from the `usd` slice only. `market_cap_percentage` holds an entry for every fiat unit CoinGecko tracks; only `btc` and `eth` are surfaced.
