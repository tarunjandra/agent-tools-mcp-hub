import assert from "node:assert/strict";
import test from "node:test";
import {
  buildQuery,
  decimalsFor,
  parseInvoice,
  parseInvoiceList,
  runTool,
  secondsToMillis,
  toMajorUnits
} from "./index.ts";

// Stripe sends amounts as integers in the smallest currency unit and stamps
// times in Unix seconds. Both conversions are silent 100x / 1000x errors when
// they are wrong, so they carry most of the coverage here.

test("decimalsFor knows the zero- and three-decimal currencies", () => {
  assert.equal(decimalsFor("usd"), 2);
  assert.equal(decimalsFor("USD"), 2);
  assert.equal(decimalsFor("jpy"), 0);
  assert.equal(decimalsFor("KRW"), 0);
  assert.equal(decimalsFor("vnd"), 0);
  assert.equal(decimalsFor("kwd"), 3);
  assert.equal(decimalsFor("bhd"), 3);
  // An unknown code is a 2-decimal currency by convention, not a crash.
  assert.equal(decimalsFor("xyz"), 2);
  assert.equal(decimalsFor(""), 2);
});

test("toMajorUnits scales by the currency, so JPY is not divided", () => {
  assert.equal(toMajorUnits(1234, "usd"), 12.34);
  assert.equal(toMajorUnits(1234, "jpy"), 1234);
  assert.equal(toMajorUnits(1234, "kwd"), 1.234);
  assert.equal(toMajorUnits(0, "usd"), 0);
  assert.equal(toMajorUnits(5, "usd"), 0.05);
});

test("toMajorUnits reports null rather than zero for a missing amount", () => {
  assert.equal(toMajorUnits(null, "usd"), null);
  assert.equal(toMajorUnits(undefined, "usd"), null);
  assert.equal(toMajorUnits("1234", "usd"), null);
  assert.equal(toMajorUnits(NaN, "usd"), null);
});

test("secondsToMillis converts Stripe's Unix seconds", () => {
  assert.equal(secondsToMillis(1_700_000_000), 1_700_000_000_000);
  assert.equal(secondsToMillis("1700000000"), 1_700_000_000_000);
  assert.equal(secondsToMillis(undefined), 0);
  assert.equal(secondsToMillis("junk"), 0);
});

test("parseInvoice normalises an invoice and converts its amounts", () => {
  const invoice = parseInvoice({
    id: "in_1A2b3C",
    number: "INV-0001",
    status: "open",
    currency: "usd",
    amount_due: 1234,
    amount_paid: 0,
    amount_remaining: 1234,
    customer: "cus_1A2b3C",
    customer_email: "ada@example.com",
    customer_name: "Ada Lovelace",
    created: 1_700_000_000,
    due_date: 1_700_086_400,
    hosted_invoice_url: "https://invoice.stripe.com/i/1",
    invoice_pdf: "https://pay.stripe.com/invoice/1/pdf",
    paid: false
  });
  assert.equal(invoice.amount_due, 12.34);
  assert.equal(invoice.amount_paid, 0);
  assert.equal(invoice.amount_remaining, 12.34);
  assert.equal(invoice.currency, "USD");
  assert.equal(invoice.decimals, 2);
  assert.equal(invoice.created, 1_700_000_000_000);
  assert.equal(invoice.due_date, 1_700_086_400_000);
  assert.equal(invoice.paid, false);
  assert.equal(invoice.customer_email, "ada@example.com");
});

test("parseInvoice keeps a JPY amount whole and leaves absent fields null", () => {
  const invoice = parseInvoice({ id: "in_x", status: "paid", currency: "jpy", amount_paid: 5000, paid: true });
  assert.equal(invoice.amount_paid, 5000);
  assert.equal(invoice.decimals, 0);
  assert.equal(invoice.number, null);
  assert.equal(invoice.customer_email, null);
  assert.equal(invoice.due_date, null);
  assert.equal(invoice.hosted_invoice_url, null);
});

test("parseInvoice tolerates an empty body", () => {
  const invoice = parseInvoice({});
  assert.equal(invoice.id, "");
  assert.equal(invoice.currency, "USD");
  assert.equal(invoice.amount_due, null);
  assert.equal(invoice.paid, false);
});

test("parseInvoiceList reads data and has_more", () => {
  const list = parseInvoiceList({
    object: "list",
    has_more: true,
    data: [{ id: "in_1", currency: "usd", amount_due: 100 }, { id: "in_2", currency: "usd", amount_due: 200 }]
  });
  assert.equal(list.count, 2);
  assert.equal(list.has_more, true);
  assert.deepEqual(list.invoices.map((i) => i.id), ["in_1", "in_2"]);
  assert.equal(list.invoices[0].amount_due, 1);
});

test("parseInvoiceList tolerates a body with no data array", () => {
  assert.deepEqual(parseInvoiceList(null).invoices, []);
  assert.equal(parseInvoiceList({}).has_more, false);
});

test("buildQuery drops empty filters rather than sending status=", () => {
  assert.equal(buildQuery({ customer: "cus_1", status: undefined, limit: 10 }), "?customer=cus_1&limit=10");
  assert.equal(buildQuery({ customer: "cus_1", status: "" }), "?customer=cus_1");
  assert.equal(buildQuery({}), "");
});

// The guards below return before any request, so they hold offline too.

test("runTool refuses without a key, naming the env var", async () => {
  const saved = process.env.STRIPE_SECRET_KEY;
  delete process.env.STRIPE_SECRET_KEY;
  const result = await runTool(undefined, "cus_1");
  assert.equal(result.success, false);
  assert.match(result.error ?? "", /STRIPE_SECRET_KEY/);
  if (saved !== undefined) process.env.STRIPE_SECRET_KEY = saved;
});

test("runTool requires a target and rejects malformed ids", async () => {
  const noTarget = await runTool(undefined, undefined, undefined, 10, "sk_test_x");
  assert.match(noTarget.error ?? "", /invoice id .* or a customer id/);

  const badInvoice = await runTool("nope", undefined, undefined, 10, "sk_test_x");
  assert.match(badInvoice.error ?? "", /in_/);

  const badCustomer = await runTool(undefined, "nope", undefined, 10, "sk_test_x");
  assert.match(badCustomer.error ?? "", /cus_/);
});

test("runTool rejects a status Stripe does not define", async () => {
  const result = await runTool(undefined, "cus_1", "banana", 10, "sk_test_x");
  assert.equal(result.success, false);
  assert.match(result.error ?? "", /draft, open, paid, uncollectible, void/);
});
