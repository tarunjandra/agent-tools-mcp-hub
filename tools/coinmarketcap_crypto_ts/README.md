# CoinMarketCap Top Crypto & Market Cap Explorer

A TypeScript integration that fetches top cryptocurrency listings from the [CoinMarketCap API](https://coinmarketcap.com/api/documentation/), with price data in the user's preferred currency. Results can be ranked by market cap (default), price, price change (1h, 24h, 7d, 30d, 60d, 90d), and 24h trading volume.

No API key is required, but one can be supplied via the `CMC_API_KEY` environment variable. (It's unlikely to make a difference, other than more aggressive rate-limiting on the public endpoint.)

## Installation and usage

### Run the demo

```bash
cd tools/coinmarketcap_crypto_ts
npm install

# If you have a CoinMarketCap API key:
export CMC_API_KEY=KEY
npm run demo
```

### Use from your own project

```bash
# set to the location of this repository's tools directory on your system:
TOOLS_DIR="agent-tools-mcp-hub/tools"
npm install "file:$TOOLS_DIR/coinmarketcap_crypto_ts"
```

```ts
// myscript.ts
// see below for a more complete example with error handling

import { runTool } from 'coinmarketcap-crypto-ts'

const result = await runTool({
  // all defaults:
  action: 'rankAssets',
  limit: 10,
  currency: 'USD',
  rankBy: 'market_cap', // (see SortKey definition)
})

console.log(result.data)
```

### Usage notes

- If you have a CoinMarketCap API key, set `CMC_API_KEY` in your environment. (This package will attempt to load a `.env` file in the current directory.)
- This package is not currently distributed with pre-built JavaScript, so please use a TypeScript runtime.
  - `bun myscript.ts`
  - `npx tsx myscript.ts`

## Parameters

*All parameters are optional:*

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `action`   | `'rankAssets' \| 'listCurrencies'` | `'rankAssets'` | The action to run. |
| `limit`    | `number` | 10  | Number of assets to fetch from CoinMarketCap. |
| `currency` | `string` | USD | Currency in which to display results.<br>(See [example](#longer-example) for code to list supported currency symbols.) |
| `rankBy`   | `SortKey` (see below) | `'market_cap'` | Rank assets by this metric. |

Valid values for `rankBy`:

```ts
type SortKey =
  | 'market_cap'
  | 'name'
  | 'symbol'
  | 'price'
  | 'volume_24h'
  | 'percent_change_1h'
  | 'percent_change_24h'
  | 'percent_change_7d'
  | 'percent_change_30d'
  | 'percent_change_60d'
  | 'percent_change_90d'
```

## Longer example

```ts
import { runTool } from 'coinmarketcap-crypto-ts'

const currencyResult = await runTool({ action: 'listCurrencies' })
if (!currencyResult.success) {
  throw currencyResult.error
}

for (const { symbol } of currencyResult.data) {
  console.log(symbol) // fiat currencies that can be passed to `rankAssets` to control output
}

const result = await runTool({
  action: 'rankAssets',
  rankBy: 'volume_24h',
})
if (!result.success) {
  throw result.error
}

const { data: assets, apiStatus } = result
console.log(assets) // an array of crypto assets
console.log(apiStatus) // returned by the CoinMarketCap API.

for (const asset of assets) {
  console.log(asset.quote) // live data in the requested currency
}
```

## Return types

On success:
- `runTool({ action: 'rankAssets' })` returns `SuccessResult<Asset[]>`
- `runTool({ action: 'listCurrencies' })` returns `SuccessResult<Fiat[]>`

On error, `runTool` always returns an `ErrorResult` (it does not throw). For most errors, details can be inspected via `error.details` on the response. See the [CoinMarketCap docs](https://coinmarketcap.com/api/documentation/guides/errors-and-rate-limits) for information about specific error codes and rate limits.

```ts
/**
 * Simplified interfaces. (Complete definitions in tool/tool.ts and tool/api-types.ts)
 */

type SuccessResult<T> = {
  success: true
  data: T
  apiStatus?: APIStatus
}
type ErrorResult = {
  success: false
  error: string | { name: string; message: string; details?: Record<string, any> }
}

// from raw CoinMarketCap response.
// ref: https://coinmarketcap.com/api/documentation/guides/errors-and-rate-limits
interface APIStatus {
  error_code: string | number
  error_message: string
  elapsed: number
  credit_count: number
}

interface Fiat {
  name: string
  sign: string
  symbol: string
}

interface Asset {
  name: string
  symbol: string
  slug: string
  quote: Quote[]
}

interface Quote {
  symbol: string
  price: number
  volume_24h: number
  cex_volume_24h: number
  dex_volume_24h: number
  percent_change_1h: number
  percent_change_24h: number
  percent_change_7d: number
  percent_change_30d: number
  percent_change_60d: number
  percent_change_90d: number
  market_cap: number
  market_cap_dominance: number
  fully_diluted_market_cap: number
  minted_market_cap: number
}
```
