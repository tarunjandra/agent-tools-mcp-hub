import fs from 'node:fs'
import prompts from 'prompts'
import { makeCoinMarketCapTool, formatAsset, type Asset } from './tool.js'

// use `npm run demo -- --no-env` to disable reading .env (mainly for testing)
if (process.argv[2] !== '--no-env') {
  if (fs.existsSync('.env')) {
    process.loadEnvFile('.env')
  }
}

const { runTool } = makeCoinMarketCapTool()
// number of assets to fetch for demo
const LIMIT = 6

console.log('Fetching currencies from CoinMarketCap API...')

const currencies = await runTool({ action: 'listCurrencies' }).then((r) => {
  if (!r.success) {
    throw r.error
  }

  return r.data.slice(0, 20).map(({ name, sign, symbol }) => ({
    description: `${name} (${sign})`,
    title: symbol,
  }))
})

console.log('Done.')
console.log('Choose a metric for ranking assets, and an output currency.\n')

const response = await prompts([
  {
    type: 'select',
    name: 'rankBy',
    message: 'Rank by:',
    choices: [
      { title: 'Market Cap', value: 'market_cap' }, // description
      { title: 'Name', value: 'name' },
      { title: 'Symbol', value: 'symbol' },
      { title: 'Price', value: 'price' },
      { title: 'Volume (24h)', value: 'volume_24h' },
      { title: 'Pct. Change (1h)', value: 'percent_change_1h' },
      { title: 'Pct. Change (24h)', value: 'percent_change_24h' },
      { title: 'Pct. Change (7d)', value: 'percent_change_7d' },
      { title: 'Pct. Change (30d)', value: 'percent_change_30d' },
      { title: 'Pct. Change (60d)', value: 'percent_change_60d' },
      { title: 'Pct. Change (90d)', value: 'percent_change_90d' },
    ],
    initial: 0, // Index of the default selection
  },
  {
    type: 'autocomplete',
    name: 'currency',
    message: 'Output currency',
    choices: currencies,
  },
])

if (!response.rankBy || !response.currency) {
  console.log('Demo canceled. Exiting.')
  process.exit()
}

const result = await runTool({
  limit: LIMIT,
  currency: response.currency,
  rankBy: response.rankBy,
})

const displayKeys = [
  'name',
  'symbol',
  'price',
  'market_cap',
  'volume_24h',
  `${response.rankBy}`.startsWith('percent_change')
    ? `${response.rankBy}`
    : 'percent_change_24h',
]

const extractKeys = (keys: string[], obj: Record<string, any>) =>
  Object.fromEntries(Object.entries(obj).filter(([key]) => keys.includes(key)))

const reallyFormatAsset = (asset: Asset) => extractKeys(displayKeys, formatAsset(asset))

if (result.success) {
  console.log({
    ...result,
    data: result.data.map(reallyFormatAsset),
  })
} else {
  console.error(result)
}

console.log(
  `\nDemo limited to top ${LIMIT} assets. Up to 100 can be requested using the API.\n`,
)
