# Stripe Invoice Fetcher (TypeScript)

A TypeScript tool that fetches Stripe invoices and their payment status — one invoice by id, or a filtered list for a customer.

It only reads, and works with any Stripe account by passing a key.

## Prerequisites

A Stripe **secret key**. Create a *restricted* key with read-only access to Invoices and Customers at [dashboard.stripe.com/apikeys](https://dashboard.stripe.com/apikeys) rather than using the account's live secret key — nothing here writes. Then either:

- Set it as the `STRIPE_SECRET_KEY` environment variable, or
- Pass it as the `apiKey` parameter.

## Parameters

| Parameter | Type | Required | Description | Default |
| :--- | :--- | :--- | :--- | :--- |
| `invoice` | `string` | No | A specific invoice id (`in_...`). Takes precedence over `customer` | — |
| `customer` | `string` | No | Customer id (`cus_...`) to list that customer's invoices | — |
| `status` | `string` | No | `draft`, `open`, `paid`, `uncollectible` or `void` | — |
| `limit` | `number` | No | Invoices to return, `1`-`100` | `10` |
| `apiKey` | `string` | No | Stripe secret key; falls back to `STRIPE_SECRET_KEY` | — |

Either `invoice` or `customer` is required.

## What it returns

For each invoice:

- `id`, `number`, `status`, `paid`
- `amount_due`, `amount_paid`, `amount_remaining` — **in the major unit**, converted (see below)
- `currency` (upper-case), `decimals` — how many decimals the amounts carry
- `customer_id`, `customer_email`, `customer_name`
- `created`, `due_date` — epoch **milliseconds**
- `hosted_invoice_url`, `invoice_pdf`

## Usage

```ts
import { runTool } from "./index.ts";

const result = await runTool(undefined, "cus_XXXXXXXXXXXXXX", "open", 5);
if (result.success && result.data) {
  for (const invoice of result.data.invoices) {
    console.log(`${invoice.number} ${invoice.status} ${invoice.amount_due} ${invoice.currency}`);
  }
  if (result.data.has_more) console.log("more invoices available");
} else {
  console.error(result.error);
}

// One invoice by id
const one = await runTool("in_1A2b3C");
```

### CLI

```bash
npm install
STRIPE_SECRET_KEY=sk_test_xxx npx ts-node index.ts cus_XXXXXXXXXXXXXX open 5
```

### Tests

```bash
npm test
```

## Notes

- **Amounts are converted out of Stripe's smallest unit — by currency.** Stripe sends a $12.34 invoice as `1234`. Most currencies divide by 100, but a set of currencies has no decimal subunit at all (JPY, KRW, VND, …) where `1234` already means 1234 yen, and a few use 3 (BHD, KWD). Dividing those by 100 would be off by 100x, so the divisor is chosen per currency and echoed back as `decimals`. See [Stripe's currency docs](https://docs.stripe.com/currencies#zero-decimal).
- **Timestamps are Unix seconds.** `created` and `due_date` are returned as epoch milliseconds, so `new Date(invoice.created)` is correct as written.
- **`paid` and `status` are both surfaced.** Stripe's boolean `paid` is the one to branch on; `status` carries extra human states (`draft`, `void`, `uncollectible`) that the flag does not distinguish.
- **An empty filter is dropped, not sent.** `status=` would be read by Stripe as a filter on the empty string and answer with an empty list, so unset filters are omitted from the query entirely.
- **Stripe's own message is passed through**, e.g. `Stripe returned HTTP 404: No such customer (invalid_request_error)`, since the fix differs per message. Malformed ids and unknown statuses are rejected before the request goes out.
