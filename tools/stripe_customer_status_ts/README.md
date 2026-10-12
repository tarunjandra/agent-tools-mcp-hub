# Stripe Customer & Payment Status Inspector (TypeScript)

A TypeScript tool that answers "is this customer in good standing?" — balance, delinquency flag, recent payment attempts and charges with their failure reasons, and a one-line verdict.

It only reads.

> Invoices are **not** here on purpose: [`tools/stripe_invoice_fetcher_ts/`](../stripe_invoice_fetcher_ts/) already covers those. This tool answers the customer-health question instead.

## Prerequisites

A Stripe **secret key**. Create a *restricted* key with read-only access to Customers, PaymentIntents and Charges at [dashboard.stripe.com/apikeys](https://dashboard.stripe.com/apikeys) rather than using the account's live secret key — nothing here writes. Then either:

- Set it as the `STRIPE_SECRET_KEY` environment variable, or
- Pass it as the `apiKey` parameter.

## Parameters

| Parameter | Type | Required | Description | Default |
| :--- | :--- | :--- | :--- | :--- |
| `customer` | `string` | Yes | Customer id (`cus_...`) | — |
| `limit` | `number` | No | Payment attempts and charges to return, `1`-`100` | `10` |
| `apiKey` | `string` | No | Stripe secret key; falls back to `STRIPE_SECRET_KEY` | — |

## What it returns

`data.customer`:

- `balance` — **signed**, in the major unit, plus `balance_direction` (`credit` / `owed` / `settled`)
- `delinquent` — Stripe's own flag
- `email`, `name`, `currency`, `default_payment_method`, `created`, `livemode`

`data.payments[]` — PaymentIntents with `status`, `amount`, `created` and `failure`

`data.charges[]` — charges with `paid`, `status`, `amount`, `amount_refunded` and `failure`

`data.health` — `{ healthy, reason }`

## Usage

```ts
import { runTool } from "./index.ts";

const result = await runTool("cus_XXXXXXXXXXXXXX", 5);
if (result.success && result.data) {
  const { customer, health, payments } = result.data;
  console.log(`${customer.id}: ${health.healthy ? "OK" : "ATTENTION"} — ${health.reason}`);
  console.log(`balance ${customer.balance} ${customer.currency} (${customer.balance_direction})`);
  for (const p of payments.filter((p) => p.failure)) {
    console.log(`  ${p.status} ${p.amount} — ${p.failure}`);
  }
} else {
  console.error(result.error);
}
```

### CLI

```bash
npm install
STRIPE_SECRET_KEY=sk_test_xxx npx ts-node index.ts cus_XXXXXXXXXXXXXX 5
```

### Tests

```bash
npm test
```

## Notes

- **The balance sign is the meaning.** Stripe sends `balance` as a signed integer in the smallest currency unit: **negative is credit the customer holds**, positive is what they owe. Reported raw, an agent would invert the most common case, so both the signed value and a named `balance_direction` are returned.
- **Amounts convert per currency.** Most currencies divide by 100, but a set has no decimal subunit at all (JPY, KRW, VND, …) and a few use 3 (BHD, KWD). Dividing those by 100 is a silent 100x error; the divisor is chosen from the currency.
- **The health verdict uses three signals, not one.** A customer can be non-delinquent with a failed attempt still in flight, so `delinquent`, the unpaid-status set, and a positive balance are each checked, in that order, and the reason names whichever fired.
- **`isUnpaid` encodes Stripe's state machine** (`requires_payment_method`, `requires_confirmation`, `requires_action`, `requires_capture`, `processing`, `canceled`) so a caller does not have to memorise it to answer "is this paid?".
- Failure reasons are taken from whichever field Stripe filled — `failure_message` on a charge, `outcome.reason`, or `last_payment_error.message` / `decline_code` / `code` on a PaymentIntent.
- **Stripe's own message is passed through**, e.g. `Stripe returned HTTP 404: No such customer (invalid_request_error)`. A malformed id is rejected before the request.
