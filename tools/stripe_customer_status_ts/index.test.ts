import assert from "node:assert/strict";
import test from "node:test";
import {
  decimalsFor,
  isUnpaid,
  parseCharges,
  parseCustomer,
  parsePaymentIntents,
  paymentHealth,
  runTool,
  toMajorUnits
} from "./index.ts";

// Stripe sends amounts in the smallest currency unit and a customer balance that
// is SIGNED -- negative means the customer holds credit. Both are silent
// inversions/100x errors when handled naively, so they carry the coverage.

test("decimalsFor knows the zero- and three-decimal currencies", () => {
  assert.equal(decimalsFor("usd"), 2);
  assert.equal(decimalsFor("JPY"), 0);
  assert.equal(decimalsFor("krw"), 0);
  assert.equal(decimalsFor("kwd"), 3);
  assert.equal(decimalsFor("xyz"), 2);
  assert.equal(decimalsFor(""), 2);
});

test("toMajorUnits scales by the currency, so JPY is not divided", () => {
  assert.equal(toMajorUnits(1234, "usd"), 12.34);
  assert.equal(toMajorUnits(1234, "jpy"), 1234);
  assert.equal(toMajorUnits(1234, "kwd"), 1.234);
  assert.equal(toMajorUnits(5, "usd"), 0.05);
  assert.equal(toMajorUnits(null, "usd"), null);
  assert.equal(toMajorUnits("1234", "usd"), null);
});

test("parseCustomer keeps the sign of the balance and names its direction", () => {
  // Negative balance = credit the customer holds. Inverting this would tell an
  // agent the customer owes money when they are actually in credit.
  const credit = parseCustomer({ id: "cus_1", balance: -1250, currency: "usd" });
  assert.equal(credit?.balance, -12.5);
  assert.equal(credit?.balance_direction, "credit");

  const owed = parseCustomer({ id: "cus_2", balance: 1250, currency: "usd" });
  assert.equal(owed?.balance, 12.5);
  assert.equal(owed?.balance_direction, "owed");

  const settled = parseCustomer({ id: "cus_3", balance: 0, currency: "usd" });
  assert.equal(settled?.balance_direction, "settled");
});

test("parseCustomer reads the delinquency flag and upper-cases the currency", () => {
  const c = parseCustomer({
    id: "cus_1",
    email: "ada@example.com",
    name: "Ada",
    currency: "usd",
    delinquent: true,
    default_payment_method: "pm_1",
    created: 1_700_000_000,
    livemode: true
  });
  assert.equal(c?.delinquent, true);
  assert.equal(c?.currency, "USD");
  assert.equal(c?.email, "ada@example.com");
  assert.equal(c?.default_payment_method, "pm_1");
  assert.equal(c?.livemode, true);
});

test("parseCustomer keeps absent fields null and rejects a body with no id", () => {
  const c = parseCustomer({ id: "cus_1" });
  assert.equal(c?.balance, null);
  assert.equal(c?.balance_direction, "settled");
  assert.equal(c?.email, null);
  assert.equal(c?.delinquent, false);
  assert.equal(parseCustomer({ email: "x@y.z" }), null);
  assert.equal(parseCustomer(null), null);
});

test("isUnpaid covers Stripe's not-yet-paid statuses", () => {
  for (const s of ["requires_payment_method", "requires_confirmation", "requires_action", "requires_capture", "processing", "canceled"]) {
    assert.ok(isUnpaid(s), `${s} should read as unpaid`);
    assert.ok(isUnpaid(s.toUpperCase()), `${s} case-insensitively`);
  }
  assert.ok(!isUnpaid("succeeded"));
  assert.ok(!isUnpaid(""));
});

test("parsePaymentIntents converts amounts and lifts the failure reason", () => {
  const rows = parsePaymentIntents({
    data: [
      {
        id: "pi_1",
        status: "requires_payment_method",
        amount: 5000,
        currency: "usd",
        created: 1_700_000_000,
        last_payment_error: { message: "Your card was declined.", decline_code: "generic_decline" }
      },
      { id: "pi_2", status: "succeeded", amount: 1200, currency: "jpy", created: 1_700_000_100 }
    ]
  });
  assert.equal(rows[0].amount, 50);
  assert.equal(rows[0].failure, "Your card was declined.");
  // JPY is a zero-decimal currency, so 1200 means 1200 yen.
  assert.equal(rows[1].amount, 1200);
  assert.equal(rows[1].failure, null);
});

test("parsePaymentIntents falls back through decline_code then code", () => {
  const rows = parsePaymentIntents({
    data: [
      { id: "pi_1", status: "requires_payment_method", last_payment_error: { decline_code: "insufficient_funds" } },
      { id: "pi_2", status: "requires_payment_method", last_payment_error: { code: "card_declined" } }
    ]
  });
  assert.equal(rows[0].failure, "insufficient_funds");
  assert.equal(rows[1].failure, "card_declined");
});

test("parsePaymentIntents tolerates a body with no data array", () => {
  assert.deepEqual(parsePaymentIntents(null), []);
  assert.deepEqual(parsePaymentIntents({}), []);
});

test("parseCharges reads paid, refunds and the failure from either field", () => {
  const rows = parseCharges({
    data: [
      { id: "ch_1", paid: true, status: "succeeded", amount: 2000, amount_refunded: 500, currency: "usd", created: 1 },
      { id: "ch_2", paid: false, status: "failed", amount: 3000, amount_refunded: 0, currency: "usd", created: 2, failure_message: "Your card was declined." },
      { id: "ch_3", paid: false, status: "failed", amount: 100, currency: "usd", created: 3, outcome: { reason: "lost_card" } }
    ]
  });
  assert.equal(rows[0].amount, 20);
  assert.equal(rows[0].amount_refunded, 5);
  assert.equal(rows[0].paid, true);
  assert.equal(rows[1].failure, "Your card was declined.");
  assert.equal(rows[2].failure, "lost_card");
});

// The health verdict is what a caller branches on, so it is asserted directly.

const okCustomer = parseCustomer({ id: "cus_1", balance: 0, currency: "usd" })!;
const owedCustomer = parseCustomer({ id: "cus_1", balance: 500, currency: "usd" })!;
const delinquentCustomer = parseCustomer({ id: "cus_1", balance: 0, currency: "usd", delinquent: true })!;

test("paymentHealth prefers Stripe's delinquent flag over everything else", () => {
  const h = paymentHealth(delinquentCustomer, []);
  assert.equal(h.healthy, false);
  assert.match(h.reason, /delinquent/);
});

test("paymentHealth flags an in-flight or failed attempt on a clean customer", () => {
  const stuck = parsePaymentIntents({ data: [{ id: "pi_1", status: "requires_action" }] });
  const h = paymentHealth(okCustomer, stuck);
  assert.equal(h.healthy, false);
  assert.match(h.reason, /requires_action/);
});

test("paymentHealth flags a positive balance as money owed", () => {
  const h = paymentHealth(owedCustomer, []);
  assert.equal(h.healthy, false);
  assert.match(h.reason, /outstanding balance/);
});

test("paymentHealth calls a settled customer with only successful attempts healthy", () => {
  const attempts = parsePaymentIntents({ data: [{ id: "pi_1", status: "succeeded" }] });
  assert.deepEqual(paymentHealth(okCustomer, attempts), {
    healthy: true,
    reason: "no failed or in-flight payment attempts"
  });
});

test("a credit balance alone is not a problem", () => {
  const credit = parseCustomer({ id: "cus_1", balance: -900, currency: "usd" })!;
  assert.equal(paymentHealth(credit, []).healthy, true);
});

// Guards return before any request, so they hold offline.

test("runTool refuses without a key, naming the env var", async () => {
  const saved = process.env.STRIPE_SECRET_KEY;
  delete process.env.STRIPE_SECRET_KEY;
  const result = await runTool("cus_1");
  assert.equal(result.success, false);
  assert.match(result.error ?? "", /STRIPE_SECRET_KEY/);
  if (saved !== undefined) process.env.STRIPE_SECRET_KEY = saved;
});

test("runTool requires a cus_ id and rejects anything else", async () => {
  const missing = await runTool("  ", 10, "sk_test_x");
  assert.match(missing.error ?? "", /customer is required/);

  const bad = await runTool("in_1A2b3C", 10, "sk_test_x");
  assert.equal(bad.success, false);
  assert.match(bad.error ?? "", /cus_/);
});
