const API = "https://api.stripe.com/v1";

/**
 * Stripe amounts are integers in the currency's SMALLEST unit, so $12.34 is
 * 1234. The divisor depends on the currency, and getting it wrong is a silent
 * 100x error: most currencies use 2 decimals, a set has NO decimal subunit
 * (JPY, KRW, VND, ...) where the number is already the whole unit, and a few
 * use 3 (BHD, KWD). https://docs.stripe.com/currencies#zero-decimal
 */
const ZERO_DECIMAL = new Set([
  "bif", "clp", "djf", "gnf", "jpy", "kmf", "krw", "mga", "pyg", "rwf",
  "ugx", "vnd", "vuv", "xaf", "xof", "xpf"
]);
const THREE_DECIMAL = new Set(["bhd", "jod", "kwd", "omr", "tnd"]);

export function decimalsFor(currency: string): number {
  const c = String(currency ?? "").trim().toLowerCase();
  if (ZERO_DECIMAL.has(c)) return 0;
  if (THREE_DECIMAL.has(c)) return 3;
  return 2;
}

export function toMajorUnits(amount: unknown, currency: string): number | null {
  if (typeof amount !== "number" || !Number.isFinite(amount)) return null;
  const places = decimalsFor(currency);
  if (places === 0) return amount;
  // Round-trip through toFixed so 1234/100 is 12.34 and not 12.340000000000002.
  return Number((amount / 10 ** places).toFixed(places));
}

function str(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function optNum(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

/**
 * A customer's balance is signed, and the sign is the meaning: a NEGATIVE
 * balance is credit the customer holds (they are owed money), a positive one is
 * what they owe. Reporting the raw integer without that would invert the answer
 * for the most common case, so the direction is named explicitly.
 */
export type BalanceDirection = "credit" | "owed" | "settled";

export interface CustomerStatus {
  id: string;
  email: string | null;
  name: string | null;
  currency: string | null;
  /** In the major unit, signed as Stripe sends it. */
  balance: number | null;
  balance_direction: BalanceDirection;
  /** Stripe's own flag: true when a recent payment was not collected. */
  delinquent: boolean;
  default_payment_method: string | null;
  created: number | null;
  livemode: boolean;
}

export function parseCustomer(raw: unknown): CustomerStatus | null {
  const c = (raw ?? {}) as Record<string, unknown>;
  if (typeof c.id !== "string") return null;
  const currency = str(c.currency) || "";
  const rawBalance = optNum(c.balance);
  const balance = rawBalance === null ? null : toMajorUnits(rawBalance, currency || "usd");
  return {
    id: c.id,
    email: typeof c.email === "string" ? c.email : null,
    name: typeof c.name === "string" ? c.name : null,
    currency: currency ? currency.toUpperCase() : null,
    balance,
    balance_direction:
      balance === null || balance === 0 ? "settled" : balance < 0 ? "credit" : "owed",
    delinquent: c.delinquent === true,
    default_payment_method: typeof c.default_payment_method === "string" ? c.default_payment_method : null,
    created: optNum(c.created),
    livemode: c.livemode === true
  };
}

export interface PaymentAttempt {
  id: string;
  status: string;
  amount: number | null;
  currency: string;
  created: number | null;
  /** Why it did not go through, when Stripe says so. */
  failure: string | null;
}

/**
 * PaymentIntent statuses that mean the money has NOT arrived, so a caller does
 * not have to memorise Stripe's state machine to answer "is this paid?".
 */
const UNPAID_STATUSES = new Set([
  "requires_payment_method",
  "requires_confirmation",
  "requires_action",
  "requires_capture",
  "processing",
  "canceled"
]);

export function isUnpaid(status: string): boolean {
  return UNPAID_STATUSES.has(String(status ?? "").trim().toLowerCase());
}

/** Payment attempts, newest first, each with the failure reason pulled out. */
export function parsePaymentIntents(payload: unknown): PaymentAttempt[] {
  const data = (payload as { data?: unknown })?.data;
  const rows = Array.isArray(data) ? data : [];
  return rows.map((row) => {
    const pi = (row ?? {}) as Record<string, unknown>;
    const lastError = (pi.last_payment_error ?? {}) as Record<string, unknown>;
    const currency = str(pi.currency) || "usd";
    const failure =
      str(lastError.message) ||
      str((lastError.decline_code as string) ?? "") ||
      str((lastError.code as string) ?? "") ||
      null;
    return {
      id: str(pi.id),
      status: str(pi.status),
      amount: toMajorUnits(optNum(pi.amount), currency),
      currency: currency.toUpperCase(),
      created: optNum(pi.created),
      failure
    };
  });
}

export interface ChargeSummary {
  id: string;
  paid: boolean;
  status: string;
  amount: number | null;
  amount_refunded: number | null;
  currency: string;
  created: number | null;
  failure: string | null;
}

/** Charges, with the failure reason taken from whichever field Stripe filled. */
export function parseCharges(payload: unknown): ChargeSummary[] {
  const data = (payload as { data?: unknown })?.data;
  const rows = Array.isArray(data) ? data : [];
  return rows.map((row) => {
    const ch = (row ?? {}) as Record<string, unknown>;
    const outcome = (ch.outcome ?? {}) as Record<string, unknown>;
    const currency = str(ch.currency) || "usd";
    return {
      id: str(ch.id),
      paid: ch.paid === true,
      status: str(ch.status),
      amount: toMajorUnits(optNum(ch.amount), currency),
      amount_refunded: toMajorUnits(optNum(ch.amount_refunded), currency),
      currency: currency.toUpperCase(),
      created: optNum(ch.created),
      failure: str(ch.failure_message) || str(outcome.reason) || null
    };
  });
}

/**
 * The one-line verdict a caller actually wants: is this customer in good
 * standing? Built from three signals rather than one, because Stripe can report
 * a clean customer with a failed payment attempt in flight.
 */
export function paymentHealth(customer: CustomerStatus, attempts: PaymentAttempt[]): {
  healthy: boolean;
  reason: string;
} {
  if (customer.delinquent) return { healthy: false, reason: "customer is flagged delinquent by Stripe" };
  const stuck = attempts.filter((a) => isUnpaid(a.status));
  if (stuck.length > 0) {
    return {
      healthy: false,
      reason: `${stuck.length} payment attempt(s) not completed, most recent status "${stuck[0].status}"`
    };
  }
  if (customer.balance_direction === "owed") {
    return { healthy: false, reason: `outstanding balance of ${customer.balance} ${customer.currency ?? ""}`.trim() };
  }
  return { healthy: true, reason: "no failed or in-flight payment attempts" };
}

export interface CustomerInspectorResult {
  success: boolean;
  data?: {
    customer: CustomerStatus;
    payments: PaymentAttempt[];
    charges: ChargeSummary[];
    health: { healthy: boolean; reason: string };
    source: string;
  };
  error?: string;
}

async function request<T>(path: string, query: string, apiKey: string): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API}${path}${query}`, {
      headers: { Authorization: `Bearer ${apiKey}`, Accept: "application/json" },
      signal: AbortSignal.timeout(15_000)
    });
  } catch (error) {
    throw new Error(
      `Network error contacting Stripe: ${error instanceof Error ? error.message : String(error)}`
    );
  }
  if (!response.ok) {
    // Stripe explains itself under error.message ("No such customer"), and that
    // is the only thing that says which parameter was wrong.
    let detail = "";
    try {
      const body = (await response.json()) as { error?: { message?: string; type?: string } };
      const message = body?.error?.message;
      const type = body?.error?.type;
      detail = [message, type && `(${type})`].filter(Boolean).join(" ");
    } catch {
      detail = "";
    }
    throw new Error(`Stripe returned HTTP ${response.status}${detail ? `: ${detail}` : ""}`);
  }
  return (await response.json()) as T;
}

/**
 * Inspect a customer's standing: balance, delinquency flag, recent payment
 * attempts and charges, and a one-line health verdict.
 *
 * Deliberately does not list invoices -- `tools/stripe_invoice_fetcher_ts/`
 * already covers those, and repeating it here would be two tools answering the
 * same question.
 *
 * @param customer Customer id (`cus_...`).
 * @param limit    Payment attempts and charges to return, 1-100, default 10.
 * @param apiKey   Stripe secret key; falls back to STRIPE_SECRET_KEY.
 */
export async function runTool(customer: string, limit: unknown = 10, apiKey?: string): Promise<CustomerInspectorResult> {
  const key = String(apiKey ?? process.env.STRIPE_SECRET_KEY ?? "").trim();
  if (!key) {
    return {
      success: false,
      error:
        "A Stripe secret key is required. Pass apiKey or set the STRIPE_SECRET_KEY environment variable (https://dashboard.stripe.com/apikeys)."
    };
  }

  const id = String(customer ?? "").trim();
  if (!id) return { success: false, error: "customer is required (a cus_... id)." };
  if (!/^cus_[A-Za-z0-9_]+$/.test(id)) {
    return { success: false, error: `customer must look like "cus_...", got "${id}".` };
  }

  const parsed = typeof limit === "number" ? limit : Number.parseInt(String(limit ?? ""), 10);
  const size = Number.isFinite(parsed) ? Math.min(100, Math.max(1, Math.trunc(parsed))) : 10;

  try {
    const [customerPayload, intentsPayload, chargesPayload] = await Promise.all([
      request<unknown>(`/customers/${encodeURIComponent(id)}`, "", key),
      request<unknown>("/payment_intents", `?customer=${encodeURIComponent(id)}&limit=${size}`, key),
      request<unknown>("/charges", `?customer=${encodeURIComponent(id)}&limit=${size}`, key)
    ]);

    const parsedCustomer = parseCustomer(customerPayload);
    if (!parsedCustomer) {
      return { success: false, error: `No customer returned for "${id}". Check the id.` };
    }
    const payments = parsePaymentIntents(intentsPayload);
    const charges = parseCharges(chargesPayload);

    return {
      success: true,
      data: {
        customer: parsedCustomer,
        payments,
        charges,
        health: paymentHealth(parsedCustomer, payments),
        source: API
      }
    };
  } catch (error) {
    return { success: false, error: error instanceof Error ? error.message : String(error) };
  }
}

if (typeof require !== "undefined" && typeof module !== "undefined" && require.main === module) {
  runTool(process.argv[2] ?? "cus_XXXXXXXXXXXXXX", process.argv[3] ?? 10).then((result) =>
    console.log(JSON.stringify(result, null, 2))
  );
}
