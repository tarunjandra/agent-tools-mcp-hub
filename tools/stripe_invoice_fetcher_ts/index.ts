const API = "https://api.stripe.com/v1";

/**
 * Stripe amounts are integers in the currency's SMALLEST unit, so a $12.34
 * invoice arrives as 1234. How many decimals that unit represents is per
 * currency, and getting it wrong is a silent 100x error:
 *
 *   - most currencies use 2 decimals (USD, EUR, ...)
 *   - a set of currencies has NO decimal subunit (JPY, KRW, VND, ...), where
 *     1234 already means 1234 yen and dividing would be wrong by 100
 *   - a few use 3 (BHD, KWD, ...)
 *
 * https://docs.stripe.com/currencies#zero-decimal
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

/** Convert a smallest-unit integer into the major unit a human reads. */
export function toMajorUnits(amount: unknown, currency: string): number | null {
  if (typeof amount !== "number" || !Number.isFinite(amount)) return null;
  const places = decimalsFor(currency);
  if (places === 0) return amount;
  return Number((amount / 10 ** places).toFixed(places));
}

/** Stripe stamps `created` in Unix SECONDS; JS dates want milliseconds. */
export function secondsToMillis(value: unknown): number {
  const seconds = typeof value === "number" ? value : Number.parseFloat(String(value ?? ""));
  return Number.isFinite(seconds) ? Math.round(seconds * 1000) : 0;
}

function str(value: unknown): string {
  return typeof value === "string" ? value : "";
}

export interface Invoice {
  id: string;
  number: string | null;
  status: string;
  currency: string;
  amount_due: number | null;
  amount_paid: number | null;
  amount_remaining: number | null;
  customer_id: string | null;
  customer_email: string | null;
  customer_name: string | null;
  created: number;
  due_date: number | null;
  hosted_invoice_url: string | null;
  invoice_pdf: string | null;
  paid: boolean;
  /** Amounts above are in the major unit, converted from Stripe's smallest. */
  decimals: number;
}

export function parseInvoice(raw: unknown): Invoice {
  const r = (raw ?? {}) as Record<string, unknown>;
  const currency = str(r.currency) || "usd";
  const dueDate = typeof r.due_date === "number" ? r.due_date : null;
  return {
    id: str(r.id),
    number: typeof r.number === "string" ? r.number : null,
    status: str(r.status),
    currency: currency.toUpperCase(),
    amount_due: toMajorUnits(r.amount_due, currency),
    amount_paid: toMajorUnits(r.amount_paid, currency),
    amount_remaining: toMajorUnits(r.amount_remaining, currency),
    customer_id: typeof r.customer === "string" ? r.customer : null,
    customer_email: typeof r.customer_email === "string" ? r.customer_email : null,
    customer_name: typeof r.customer_name === "string" ? r.customer_name : null,
    created: secondsToMillis(r.created),
    due_date: dueDate === null ? null : secondsToMillis(dueDate),
    hosted_invoice_url: typeof r.hosted_invoice_url === "string" ? r.hosted_invoice_url : null,
    invoice_pdf: typeof r.invoice_pdf === "string" ? r.invoice_pdf : null,
    // `paid` is Stripe's own flag and is the one to trust; `status` is the
    // human label and has more states (draft, void, uncollectible).
    paid: r.paid === true,
    decimals: decimalsFor(currency)
  };
}

export interface ListResult {
  invoices: Invoice[];
  has_more: boolean;
  count: number;
}

export function parseInvoiceList(payload: unknown): ListResult {
  const data = (payload as { data?: unknown })?.data;
  const rows = Array.isArray(data) ? data : [];
  return {
    invoices: rows.map(parseInvoice),
    has_more: (payload as { has_more?: unknown })?.has_more === true,
    count: rows.length
  };
}

/**
 * Stripe filters are plain query parameters. Empty and undefined values are
 * dropped rather than sent as `status=`, which Stripe would read as a filter on
 * the empty string and answer with an empty list.
 */
export function buildQuery(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    search.set(key, String(value));
  }
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

export interface StripeInvoiceResult {
  success: boolean;
  data?: {
    invoices: Invoice[];
    has_more: boolean;
    scope: "invoice" | "customer" | "all";
    source: string;
  };
  error?: string;
}

async function request<T>(path: string, query: string, apiKey: string): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API}${path}${query}`, {
      headers: {
        Authorization: `Bearer ${apiKey}`,
        Accept: "application/json"
      },
      signal: AbortSignal.timeout(15_000)
    });
  } catch (error) {
    throw new Error(
      `Network error contacting Stripe: ${error instanceof Error ? error.message : String(error)}`
    );
  }
  if (!response.ok) {
    // Stripe nests a human message under error.message ("No such customer"),
    // and that text is the only thing that says which parameter was wrong.
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
 * Fetch Stripe invoices and their payment status, either one invoice by id or a
 * filtered list.
 *
 * Needs a Stripe secret key. Use a RESTRICTED key with read-only access to
 * Invoices and Customers rather than the account's live secret key -- this tool
 * only ever reads.
 *
 * @param invoice   A specific invoice id (`in_...`). Wins over `customer`.
 * @param customer  Customer id (`cus_...`) to list that customer's invoices.
 * @param status    `draft` | `open` | `paid` | `uncollectible` | `void`.
 * @param limit     1-100 invoices, default 10.
 * @param apiKey    Stripe secret key; falls back to STRIPE_SECRET_KEY.
 */
export async function runTool(
  invoice?: string,
  customer?: string,
  status?: string,
  limit: unknown = 10,
  apiKey?: string
): Promise<StripeInvoiceResult> {
  const key = String(apiKey ?? process.env.STRIPE_SECRET_KEY ?? "").trim();
  if (!key) {
    return {
      success: false,
      error:
        "A Stripe secret key is required. Pass apiKey or set the STRIPE_SECRET_KEY environment variable (https://dashboard.stripe.com/apikeys)."
    };
  }

  const invoiceId = String(invoice ?? "").trim();
  const customerId = String(customer ?? "").trim();
  if (!invoiceId && !customerId) {
    return {
      success: false,
      error: "Pass an invoice id (in_...) or a customer id (cus_...) to fetch."
    };
  }
  if (invoiceId && !/^in_[A-Za-z0-9_]+$/.test(invoiceId)) {
    return { success: false, error: `invoice must look like "in_...", got "${invoiceId}".` };
  }
  if (customerId && !/^cus_[A-Za-z0-9_]+$/.test(customerId)) {
    return { success: false, error: `customer must look like "cus_...", got "${customerId}".` };
  }

  const parsedLimit = typeof limit === "number" ? limit : Number.parseInt(String(limit ?? ""), 10);
  const size = Number.isFinite(parsedLimit) ? Math.min(100, Math.max(1, Math.trunc(parsedLimit))) : 10;

  const VALID_STATUS = ["draft", "open", "paid", "uncollectible", "void"];
  const wanted = String(status ?? "").trim().toLowerCase();
  if (wanted && !VALID_STATUS.includes(wanted)) {
    return {
      success: false,
      error: `status must be one of ${VALID_STATUS.join(", ")}; got "${status}".`
    };
  }

  try {
    if (invoiceId) {
      const payload = await request<unknown>(`/invoices/${encodeURIComponent(invoiceId)}`, "", key);
      const one = parseInvoice(payload);
      return {
        success: true,
        data: { invoices: [one], has_more: false, scope: "invoice", source: API }
      };
    }

    const query = buildQuery({ customer: customerId, status: wanted || undefined, limit: size });
    const payload = await request<unknown>("/invoices", query, key);
    const list = parseInvoiceList(payload);
    return {
      success: true,
      data: { invoices: list.invoices, has_more: list.has_more, scope: "customer", source: API }
    };
  } catch (error) {
    return { success: false, error: error instanceof Error ? error.message : String(error) };
  }
}

if (typeof require !== "undefined" && typeof module !== "undefined" && require.main === module) {
  runTool(undefined, process.argv[2] ?? "cus_XXXXXXXXXXXXXX", process.argv[3], process.argv[4] ?? 10).then(
    (result) => console.log(JSON.stringify(result, null, 2))
  );
}
