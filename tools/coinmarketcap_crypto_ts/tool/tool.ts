import type {
  Asset as ApiAsset,
  Quote,
  ListingSuccess,
  FiatMapSuccess,
  SortKey,
  APIError,
  Status as APIStatus,
} from './api-types.ts'

// ref: https://coinmarketcap.com/api/documentation/pro-api-reference/keyless-public-api
const defaultBaseUrl = (apiKey?: string) => {
  const hardCoded = apiKey
    ? 'https://pro-api.coinmarketcap.com'
    : 'https://pro-api.coinmarketcap.com/public-api'

  return process.env.CMC_BASE_URL || hardCoded
}

// consistent with other tools in agent-tools-mcp-hub
const USER_AGENT =
  'AgentToolsHub/1.0 (https://github.com/tarunjandra/agent-tools-mcp-hub)'

// flattened, simplified version of API type
export interface Asset extends Pick<ApiAsset, 'name' | 'slug' | 'symbol'> {
  quote: Quote
}

// unless you pay, querying more than one currency returns an error:
interface ListingOpts {
  limit?: number // default 10, max 100
  currency?: string // 'USD,EUR,BTC,...'
  rankBy?: SortKey
}

interface CmcError {
  name: 'CmcError'
  message: string
  details: Record<string, any>
}

const isCmcError = (err: unknown): err is CmcError =>
  !!err && typeof err === 'object' && 'name' in err && err.name === 'CmcError'

// convert a Response object to a plain Record<string, any> for logging/testing
const toPlainResponse = (r: Response) => ({
  status: r.status,
  statusText: r.statusText,
  headers: Object.fromEntries(r.headers.entries()),
  ok: r.ok,
  redirected: r.redirected,
  type: r.type,
  url: r.url,
})
type PlainResponse = ReturnType<typeof toPlainResponse>

// returned by listCurrencies (/v1/fiat/map)
interface Fiat {
  name: string
  sign: string
  symbol: string
}

// common shape for tool return values
type SuccessResult<T> = {
  success: true
  data: T
  // this should be defined unless we short-circuit the API and return cached data
  // (see the listCurrencies command in runTool)
  apiStatus?: APIStatus
  plainResponse?: PlainResponse
  runningLog?: string[]
}
type ErrorResult = {
  success: false
  error: string | { name: string; message: string; details?: Record<string, any> }
  runningLog?: string[]
}

// Utilities to work with tool return values
type Wrap<T> = Promise<SuccessResult<T>>
type Unwrap<T extends Wrap<any>> = Awaited<T>['data']

// doesn't work:
// type Unwrap<T extends Wrap<any>> = T extends Wrap<infer R> ? R : never

// Defines the tool interfaces
interface ToolMap {
  rankAssets: (opts?: ListingOpts) => Wrap<Asset[]>
  listCurrencies: () => Wrap<Fiat[]>
  dumpAssets: (opts?: ListingOpts) => Wrap<ApiAsset[]>
}

type ToolAction = keyof ToolMap
type ToolData<T extends ToolAction> = Unwrap<ReturnType<ToolMap[T]>>

interface ToolParams<T extends ToolAction> extends ListingOpts {
  action?: T
}

export function makeCoinMarketCapTool({
  apiKey = process.env.CMC_API_KEY,
  baseUrl = defaultBaseUrl(apiKey),
}: {
  apiKey?: string
  baseUrl?: string
} = {}) {
  const runningLog: string[] = []
  runningLog.push(
    apiKey
      ? 'CoinMarketCap API key extracted from environment. API calls will be authenticated.'
      : 'No CoinMarketCap API key found in environment. The keyless API will be used.',
  )

  const toolMap: ToolMap = {
    rankAssets: cmcGetAssets,
    listCurrencies: cmcGetFiatCurrencies,
    dumpAssets: cmcDumpAssets,
  } as const

  return { runTool }

  async function runTool<T extends ToolAction = 'rankAssets'>({
    action = 'rankAssets' as T,
    ...opts
  }: ToolParams<T>): Promise<SuccessResult<ToolData<T>> | ErrorResult> {
    try {
      switch (action) {
        case 'rankAssets':
        case 'dumpAssets': {
          const result = await toolMap[action](opts)
          return { ...result, runningLog }
        }
        case 'listCurrencies': {
          if (!apiKey) {
            const data = (await import('./currencies.js')).default
            runningLog.push(
              'Returning cached fiat currency data because the live endpoint requires an API key.',
            )
            return { success: true, data, runningLog }
          }
          const result = await toolMap[action](opts)
          return { ...result, runningLog }
        }

        default: {
          return {
            success: false,
            error: `Unknown action: ${action}. Try 'rankAssets' or 'listCurrencies'.`,
            runningLog,
          }
        }
      }
    } catch (err) {
      if (err instanceof Error) {
        return {
          success: false,
          error: { name: err.name, message: err.message },
          runningLog,
        }
      }
      if (isCmcError(err)) {
        return {
          success: false,
          error: { ...err },
          runningLog,
        }
      }

      // fallback for unrecognized errors
      return {
        success: false,
        error: `${err}`,
        runningLog,
      }
    }
  }

  // use typescript function overloads to allow for a plain-response-returning variant
  // while keeping other calls strongly typed. This could also work for `runTool` variants
  // (currently uses a generic to which a parameter is assigned).
  async function cmcFetch(
    url: string | URL,
    init: RequestInit | undefined,
    raw: true,
  ): Promise<Response>

  async function cmcFetch<T>(
    url: string | URL,
    init?: RequestInit,
    raw?: boolean,
  ): Promise<T>

  async function cmcFetch<T>(
    url: string | URL,
    init?: RequestInit,
    raw = false,
  ): Promise<T | Response> {
    const res = await fetch(url, { ...init, headers: buildHeaders(init?.headers) })
    if (raw) {
      return res
    }

    /**
     * Exceeding rate limit; could implement retry with back-off
     *
     * if (res.status === 429)
     */

    if (!res.ok) {
      const apiError = (await res.json()) as APIError
      const error: CmcError = {
        name: 'CmcError',
        message: apiError.status.error_message,
        details: {
          httpStatus: res.status,
          httpStatusText: res.statusText,
          ...apiError.status,
        },
      }
      // this layer throws; errors are handled in `runTool`
      throw error
    }

    return res.json() as Promise<T>
  }

  // ref: https://coinmarketcap.com/api/documentation/guides/standards-and-conventions
  function buildHeaders(init?: RequestInit['headers']) {
    const headers = new Headers(init)
    headers.set('Accept', 'application/json')
    headers.set('Accept-Encoding', 'deflate, gzip')
    headers.set('User-Agent', USER_AGENT)
    if (apiKey) {
      headers.set('X-CMC_PRO_API_KEY', apiKey)
    }

    return headers
  }

  function cleanAsset(rawAsset: ApiAsset): Asset {
    // rawAsset.quote is an array with one item when one currency was requested
    const [quote] = rawAsset.quote
    if (!quote) {
      throw new Error('Asset returned by CoinMarketCap API did not contain quote data.')
    }
    return {
      name: rawAsset.name,
      slug: rawAsset.slug,
      symbol: rawAsset.symbol,
      quote,
    }
  }

  function cmcAssetsUrl(opts: ListingOpts = {}) {
    const { limit = 10, currency } = opts
    const params = new URLSearchParams({
      limit: limit.toString(),
    })
    if (currency) {
      params.set('convert', currency)
    }
    return `${baseUrl}/v3/cryptocurrency/listings/latest?${params}`
  }

  // top {limit} cryptocurrencies ranked by {rankBy} (default market_cap)
  async function cmcGetAssets(opts?: ListingOpts): Promise<SuccessResult<Asset[]>> {
    const { rankBy } = opts ?? {}
    return cmcFetch<ListingSuccess>(cmcAssetsUrl(opts)).then((r) => {
      const apiStatus = r.status
      const data = r.data.map(cleanAsset)

      type SortFn = (a: Asset, b: Asset) => number
      let sortFn: SortFn | undefined

      if (rankBy === 'name' || rankBy === 'symbol')
        sortFn = (a, b) => a[rankBy].localeCompare(b[rankBy])
      else if (rankBy) {
        sortFn = (a, b) => b.quote[rankBy] - a.quote[rankBy]
      }
      return {
        success: true,
        data: sortFn ? data.sort(sortFn) : data,
        apiStatus,
      }
    })
  }

  async function cmcGetFiatCurrencies(): Promise<SuccessResult<Fiat[]>> {
    const res = await cmcFetch<FiatMapSuccess>(`${baseUrl}/v1/fiat/map?limit=30`)
    const apiStatus = res.status
    const data = res.data.map(({ name, sign, symbol }) => ({ name, sign, symbol }))

    return {
      success: true,
      data,
      apiStatus,
    }
  }

  // returns the Response (converted to a plain object) and the unmodified body
  // for logging or testing
  async function cmcDumpAssets(opts?: ListingOpts): Promise<SuccessResult<ApiAsset[]>> {
    const response = await cmcFetch(cmcAssetsUrl(opts), undefined, true)

    const plainResponse = toPlainResponse(response)
    const json = (await response.json()) as ListingSuccess

    return {
      success: true,
      plainResponse,
      data: json.data,
      apiStatus: json.status,
    }
  }
}

export const formatAsset = (data: Asset) => {
  const { name, slug, symbol, quote } = data

  const currencyFmt = (() => {
    const opts: Intl.NumberFormatOptions = {
      currency: quote.symbol,
      style: 'currency',
      notation: 'compact',
      maximumSignificantDigits: 4,
    }
    try {
      return new Intl.NumberFormat([], opts)
    } catch {
      return new Intl.NumberFormat([], {
        ...opts,
        currency: 'USD',
      })
    }
  })()

  const percentFmt = new Intl.NumberFormat([], {
    style: 'percent',
    maximumSignificantDigits: 4,
    maximumFractionDigits: 3,
  })

  const percentKeys = [
    'percent_change_1h',
    'percent_change_24h',
    'percent_change_7d',
    'percent_change_30d',
    'percent_change_60d',
    'percent_change_90d',
  ] as const
  const currencyKeys = ['price', 'market_cap', 'volume_24h'] as const

  type PercentKey = (typeof percentKeys)[number]
  type CurrencyKey = (typeof currencyKeys)[number]

  const percentDict = Object.fromEntries(
    percentKeys.map((key) => [key, percentFmt.format(data.quote[key] / 100)]),
  ) as Record<PercentKey, string>
  const currencyDict = Object.fromEntries(
    currencyKeys.map((key) => [key, currencyFmt.format(data.quote[key])]),
  ) as Record<CurrencyKey, string>

  return {
    name,
    slug,
    symbol,
    ...currencyDict,
    ...percentDict,
  }
}
