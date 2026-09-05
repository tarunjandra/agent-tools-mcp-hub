/**
 * Initially generated with:
 *   BASEURL=https://pro-api.coinmarketcap.com/public-api
 *   ENDPOINT="${BASEURL}/v3/cryptocurrency/listings/latest?limit=10&convert=USD"
 *   curl -s "$ENDPOINT" | npx quicktype -l ts
 *
 * Runtime helpers removed and substantial manual edits made.
 */

// ISO UTC (2026-09-02T05:49:00.000Z)
type Timestamp = string

export interface ListingSuccess {
  data: Asset[]
  status: SuccessStatus
}

export interface FiatMapSuccess {
  data: FiatMap[]
  status: SuccessStatus
}

export interface FiatMap {
  id: number
  name: string
  sign: string
  symbol: string
}

export interface APIError {
  status: Status
}

export interface Status {
  timestamp: Timestamp
  error_code: string | number
  error_message: string
  elapsed: number
  credit_count: number
}

interface SuccessStatus extends Status {
  error_code: 0 | '0'
  error_message: ''
}

export interface Asset {
  tags: string[]
  id: number
  name: string
  symbol: string
  slug: string
  date_added: Timestamp
  last_updated: Timestamp
  quote: Quote[]
}

export interface Quote {
  id: number
  symbol: string
  price: number
  volume_24h: number
  volume_change_24h: number
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
  last_updated: Timestamp
}

export type SortKey =
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
