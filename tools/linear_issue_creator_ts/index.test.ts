import assert from "node:assert/strict";
import test from "node:test";
import {
  graphQlErrors,
  parseCreatedIssue,
  parsePriority,
  priorityLabel,
  runTool,
  teamIdFor
} from "./index.ts";

// Two Linear behaviours drive most of these: priority 0 is a real value ("No
// priority") rather than "unset", and a rejected GraphQL operation comes back
// as HTTP 200 with an `errors` array, so `response.ok` alone proves nothing.

test("priorityLabel names Linear's scale, including 0", () => {
  assert.equal(priorityLabel(0), "none");
  assert.equal(priorityLabel(1), "urgent");
  assert.equal(priorityLabel(2), "high");
  assert.equal(priorityLabel(3), "medium");
  assert.equal(priorityLabel(4), "low");
  assert.equal(priorityLabel(9), "unknown");
  assert.equal(priorityLabel("2"), "high");
  assert.equal(priorityLabel(undefined), "unknown");
});

test("parsePriority accepts both the integer and the label", () => {
  assert.equal(parsePriority(1), 1);
  assert.equal(parsePriority("2"), 2);
  assert.equal(parsePriority("urgent"), 1);
  assert.equal(parsePriority("LOW"), 4);
  assert.equal(parsePriority("none"), 0);
});

test("parsePriority leaves an absent priority unset rather than defaulting it", () => {
  // undefined must stay null so the mutation omits `priority` entirely and
  // Linear applies the team's own default, not "none".
  assert.equal(parsePriority(undefined), null);
  assert.equal(parsePriority(null), null);
  assert.equal(parsePriority(""), null);
});

test("parsePriority rejects out-of-range and unknown values", () => {
  assert.equal(parsePriority(5), null);
  assert.equal(parsePriority(-1), null);
  assert.equal(parsePriority(1.5), null);
  assert.equal(parsePriority("banana"), null);
});

test("teamIdFor matches a team by key or by name, case-insensitively", () => {
  const nodes = [
    { id: "t1", key: "ENG", name: "Engineering" },
    { id: "t2", key: "DES", name: "Design" }
  ];
  assert.equal(teamIdFor(nodes, "ENG"), "t1");
  assert.equal(teamIdFor(nodes, "eng"), "t1");
  assert.equal(teamIdFor(nodes, "Engineering"), "t1");
  assert.equal(teamIdFor(nodes, "design"), "t2");
});

test("teamIdFor returns null rather than guessing a near match", () => {
  const nodes = [{ id: "t1", key: "ENG", name: "Engineering" }];
  assert.equal(teamIdFor(nodes, "EN"), null);
  assert.equal(teamIdFor(nodes, "Platform"), null);
  assert.equal(teamIdFor(nodes, ""), null);
  assert.equal(teamIdFor("junk", "ENG"), null);
  assert.equal(teamIdFor(undefined, "ENG"), null);
});

test("parseCreatedIssue flattens the issueCreate payload", () => {
  const issue = parseCreatedIssue({
    data: {
      issueCreate: {
        success: true,
        issue: {
          id: "abc-123",
          identifier: "ENG-42",
          title: "Ship the thing",
          url: "https://linear.app/acme/issue/ENG-42",
          priority: 2,
          state: { name: "Todo" },
          team: { key: "ENG" }
        }
      }
    }
  });
  assert.deepEqual(issue, {
    id: "abc-123",
    identifier: "ENG-42",
    title: "Ship the thing",
    url: "https://linear.app/acme/issue/ENG-42",
    priority: 2,
    priority_label: "high",
    state: "Todo",
    team_key: "ENG"
  });
});

test("parseCreatedIssue returns null when no issue came back", () => {
  assert.equal(parseCreatedIssue({ data: { issueCreate: { success: false } } }), null);
  assert.equal(parseCreatedIssue({ data: {} }), null);
  assert.equal(parseCreatedIssue(null), null);
});

test("parseCreatedIssue tolerates a partial issue", () => {
  const issue = parseCreatedIssue({ data: { issueCreate: { issue: { id: "x" } } } });
  assert.equal(issue?.identifier, "");
  assert.equal(issue?.priority, 0);
  assert.equal(issue?.priority_label, "none");
  assert.equal(issue?.state, null);
  assert.equal(issue?.url, null);
});

test("graphQlErrors surfaces the message and its code", () => {
  assert.deepEqual(
    graphQlErrors({ errors: [{ message: "Access denied", extensions: { code: "AUTHENTICATION_ERROR" } }] }),
    ["Access denied (AUTHENTICATION_ERROR)"]
  );
  assert.deepEqual(graphQlErrors({ errors: [{ message: "Team not found" }] }), ["Team not found"]);
  assert.deepEqual(graphQlErrors({ data: {} }), []);
  assert.deepEqual(graphQlErrors(undefined), []);
});

// The guards below return before any request, so they hold offline.

test("runTool refuses without a key, naming the env var", async () => {
  const saved = process.env.LINEAR_API_KEY;
  delete process.env.LINEAR_API_KEY;
  const result = await runTool("ENG", "Title");
  assert.equal(result.success, false);
  assert.match(result.error ?? "", /LINEAR_API_KEY/);
  if (saved !== undefined) process.env.LINEAR_API_KEY = saved;
});

test("runTool requires a team and a non-empty title", async () => {
  const noTeam = await runTool("  ", "Title", undefined, undefined, "lin_api_x");
  assert.match(noTeam.error ?? "", /team is required/);

  const noTitle = await runTool("ENG", "   ", undefined, undefined, "lin_api_x");
  assert.match(noTitle.error ?? "", /title must not be empty/);
});

test("runTool rejects a title over Linear's 255 character limit", async () => {
  const result = await runTool("ENG", "x".repeat(256), undefined, undefined, "lin_api_x");
  assert.equal(result.success, false);
  assert.match(result.error ?? "", /255/);
});

test("runTool rejects a priority it cannot map", async () => {
  const result = await runTool("ENG", "Title", undefined, "banana", "lin_api_x");
  assert.equal(result.success, false);
  assert.match(result.error ?? "", /none, urgent, high, medium, low/);
});
