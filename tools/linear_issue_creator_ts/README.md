# Linear Issue Creator (TypeScript)

A TypeScript tool that creates a Linear issue on a chosen team through the [Linear GraphQL API](https://developers.linear.app/docs/graphql/working-with-the-graphql-api).

It resolves the team first, so a typo fails loudly instead of filing the issue somewhere unexpected.

## Prerequisites

A Linear **personal API key** with write access to the target team's issues. Create one at [linear.app/settings/api](https://linear.app/settings/api), then either:

- Set it as the `LINEAR_API_KEY` environment variable, or
- Pass it as the `apiKey` parameter.

## Parameters

| Parameter | Type | Required | Description | Default |
| :--- | :--- | :--- | :--- | :--- |
| `team` | `string` | Yes | Team key (`ENG`) or exact name (`Engineering`) | — |
| `title` | `string` | Yes | Issue title, 255 characters or fewer | — |
| `description` | `string` | No | Markdown body for the issue | — |
| `priority` | `string` | No | `none`, `urgent`, `high`, `medium`, `low`, or `0`-`4` | — |
| `apiKey` | `string` | No | Linear API key; falls back to `LINEAR_API_KEY` | — |

## What it returns

- `id`, `identifier` (e.g. `ENG-42`), `title`, `url`
- `priority` and `priority_label`
- `state` — the workflow state name, e.g. `Todo`
- `team_key`

## Usage

```ts
import { runTool } from "./index.ts";

const result = await runTool(
  "ENG",
  "Rate-limit the public search endpoint",
  "We saw 429s during the launch.\n\n- add a token bucket\n- return Retry-After",
  "high"
);

if (result.success && result.data) {
  console.log(`created ${result.data.identifier}: ${result.data.url}`);
} else {
  console.error(result.error);
}
```

### CLI

```bash
npm install
LINEAR_API_KEY=lin_api_xxx npx ts-node index.ts ENG "Example issue" "Body" high
```

### Tests

```bash
npm test
```

## Notes

- **A rejected operation arrives as HTTP 200.** GraphQL reports a failed mutation inside an `errors` array with a success status code, so `response.ok` alone would read a rejected `issueCreate` as a success. The `errors` array is checked on every response and turned into an error string, including its `extensions.code` (e.g. `AUTHENTICATION_ERROR`).
- **The auth header is the key, not `Bearer <key>`.** Linear's personal API keys go in `Authorization` as-is; the `Bearer` prefix that Stripe and most REST APIs want is rejected here.
- **Priority `0` is a value, not "unset".** Linear's scale is 0 `none`, 1 `urgent`, 2 `high`, 3 `medium`, 4 `low`. When no priority is passed the field is omitted from the mutation entirely, so the team's own default applies rather than being pinned to `none`.
- **The team is resolved before the issue is created**, by key first and then by a listing so an exact name works too. A near miss (`EN` for `ENG`) returns "no team matched" rather than filing against the wrong team.
- The title's 255 character limit is checked locally, so an over-long title fails without a round trip.
