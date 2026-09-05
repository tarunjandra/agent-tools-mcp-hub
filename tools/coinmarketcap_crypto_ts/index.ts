import fs from 'node:fs'
import { makeCoinMarketCapTool } from './tool/tool.js'

if (fs.existsSync('.env')) {
  process.loadEnvFile('.env')
}

const { runTool } = makeCoinMarketCapTool()

export { makeCoinMarketCapTool, runTool }
