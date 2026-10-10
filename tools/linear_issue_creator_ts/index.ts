const API = "https://api.linear.app/graphql";

/**
 * Linear's priority scale is an integer, and 0 is a real value ("No priority")
 * rather than "unset" -- so it is named here instead of being passed through as
 * a bare number nobody can read back.
 */
export const PRIORITY_LABELS: Record<number, string> = {
  0: "none",
  1: "urgent",
  2: "high",
  3: "medium",
  4: "low"
};

export function priorityLabel(value: unknown): string {
  const n = typeof value === "number" ? value : Number.parseInt(String(value ?? ""), 10);
  return PRIORITY_LABELS[n] ?? "unknown";
}

/** Accept the label too, so a caller can pass "urgent" as easily as 1. */
export function parsePriority(value: unknown): number | null {
  if (value === undefined || value === null || value === "") return null;
  if (typeof value === "number") {
    return Number.isInteger(value) && value >= 0 && value <= 4 ? value : null;
  }
  const text = String(value).trim().toLowerCase();
  if (/^[0-4]$/.test(text)) return Number.parseInt(text, 10);
  const hit = Object.entries(PRIORITY_LABELS).find(([, label]) => label === text);
  return hit ? Number.parseInt(hit[0], 10) : null;
}

export function teamIdFor(nodes: unknown, wanted: string): string | null {
  const rows = Array.isArray(nodes) ? (nodes as Array<Record<string, unknown>>) : [];
  const target = String(wanted ?? "").trim().toLowerCase();
  if (!target) return null;
  const exact = rows.find((t) => {
    const key = typeof t.key === "string" ? t.key.toLowerCase() : "";
    const name = typeof t.name === "string" ? t.name.toLowerCase() : "";
    return key === target || name === target;
  });
  if (exact) return typeof exact.id === "string" ? exact.id : null;
  // A team is identified by KEY in Linear's UI, so a near miss on the key (when
  // the caller passed a name) is still worth reporting as not-found rather than
  // silently creating the issue somewhere else.
  return null;
}

export interface CreatedIssue {
  id: string;
  identifier: string;
  title: string;
  url: string | null;
  priority: number;
  priority_label: string;
  state: string | null;
  team_key: string | null;
}

export function parseCreatedIssue(payload: unknown): CreatedIssue | null {
  const data = (payload as { data?: unknown })?.data as Record<string, unknown> | undefined;
  const created = data?.issueCreate as Record<string, unknown> | undefined;
  const issue = created?.issue as Record<string, unknown> | undefined;
  if (!issue || typeof issue.id !== "string") return null;
  const priority = typeof issue.priority === "number" ? issue.priority : 0;
  const state = (issue.state ?? {}) as Record<string, unknown>;
  const team = (issue.team ?? {}) as Record<string, unknown>;
  return {
    id: issue.id,
    identifier: typeof issue.identifier === "string" ? issue.identifier : "",
    title: typeof issue.title === "string" ? issue.title : "",
    url: typeof issue.url === "string" ? issue.url : null,
    priority,
    priority_label: priorityLabel(priority),
    state: typeof state.name === "string" ? state.name : null,
    team_key: typeof team.key === "string" ? team.key : null
  };
}

/**
 * The `errors` array a GraphQL response carries, flattened into a sentence.
 * Linear answers a failed operation with HTTP 200 and this array, so checking
 * `response.ok` alone would report success on a rejected mutation.
 */
export function graphQlErrors(payload: unknown): string[] {
  const errors = (payload as { errors?: unknown })?.errors;
  if (!Array.isArray(errors)) return [];
  return errors.map((e) => {
    const err = (e ?? {}) as Record<string, unknown>;
    const code = (err.extensions as Record<string, unknown> | undefined)?.code;
    const message = typeof err.message === "string" ? err.message : "unknown error";
    return code ? `${message} (${String(code)})` : message;
  });
}

const TEAM_QUERY = `query TeamByKey($key: String!) {
  teams(filter: { key: { eq: $key } }, first: 1) { nodes { id key name } }
}`;

const TEAM_LIST_QUERY = `query Teams {
  teams(first: 50) { nodes { id key name } }
}`;

const ISSUE_CREATE = `mutation CreateIssue($input: IssueCreateInput!) {
  issueCreate(input: $input) {
    success
    issue { id identifier title url priority state { name } team { key } }
  }
}`;

export interface LinearIssueResult {
  success: boolean;
  data?: CreatedIssue & { source: string };
  error?: string;
}

interface GraphQlResponse {
  data?: unknown;
  errors?: unknown;
}

async function graphql(
  query: string,
  variables: Record<string, unknown>,
  apiKey: string
): Promise<GraphQlResponse> {
  let response: Response;
  try {
    response = await fetch(API, {
      method: "POST",
      headers: {
        // Linear personal API keys go in Authorization as-is. Prefixing them
        // with "Bearer" is the usual REST habit and Linear rejects it.
        Authorization: apiKey,
        "Content-Type": "application/json",
        Accept: "application/json"
      },
      body: JSON.stringify({ query, variables }),
      signal: AbortSignal.timeout(15_000)
    });
  } catch (error) {
    throw new Error(
      `Network error contacting Linear: ${error instanceof Error ? error.message : String(error)}`
    );
  }

  if (!response.ok) {
    let detail = "";
    try {
      const body = (await response.json()) as { errors?: Array<{ message?: string }> };
      detail = body?.errors?.[0]?.message ?? "";
    } catch {
      detail = "";
    }
    throw new Error(`Linear returned HTTP ${response.status}${detail ? `: ${detail}` : ""}`);
  }

  const payload = (await response.json()) as GraphQlResponse;
  const problems = graphQlErrors(payload);
  if (problems.length > 0) throw new Error(`Linear rejected the request: ${problems.join("; ")}`);
  return payload;
}

/**
 * Create an issue on a Linear team.
 *
 * Needs a Linear personal API key with write access to the team's issues
 * (https://linear.app/settings/api).
 *
 * The team is resolved by key ("ENG") or name first, so a typo fails with
 * "no team matched" instead of creating the issue on the wrong team.
 *
 * @param team        Team key or name, e.g. "ENG" or "Engineering".
 * @param title       Issue title.
 * @param description Optional markdown body.
 * @param priority    "none" | "urgent" | "high" | "medium" | "low", or 0-4.
 * @param apiKey      Linear API key; falls back to LINEAR_API_KEY.
 */
export async function runTool(
  team: string,
  title: string,
  description?: string,
  priority?: unknown,
  apiKey?: string
): Promise<LinearIssueResult> {
  const key = String(apiKey ?? process.env.LINEAR_API_KEY ?? "").trim();
  if (!key) {
    return {
      success: false,
      error:
        "A Linear API key is required. Pass apiKey or set the LINEAR_API_KEY environment variable (https://linear.app/settings/api)."
    };
  }

  const teamWanted = String(team ?? "").trim();
  if (!teamWanted) return { success: false, error: "team is required (its key, e.g. ENG)." };

  const issueTitle = String(title ?? "").trim();
  if (!issueTitle) return { success: false, error: "title must not be empty." };
  if (issueTitle.length > 255) return { success: false, error: "title must be 255 characters or fewer." };

  const wantedPriority = parsePriority(priority);
  if (priority !== undefined && priority !== null && priority !== "" && wantedPriority === null) {
    return {
      success: false,
      error: `priority must be one of ${Object.values(PRIORITY_LABELS).join(", ")} or an integer 0-4; got "${String(priority)}".`
    };
  }

  try {
    let teamId: string | null = null;
    if (/^[A-Za-z0-9]{2,10}$/.test(teamWanted)) {
      const byKey = await graphql(TEAM_QUERY, { key: teamWanted.toUpperCase() }, key);
      teamId = teamIdFor((byKey.data as { teams?: { nodes?: unknown } })?.teams?.nodes, teamWanted);
    }
    if (!teamId) {
      // Fall back to a listing so a caller who passed the team NAME still works.
      const all = await graphql(TEAM_LIST_QUERY, {}, key);
      teamId = teamIdFor((all.data as { teams?: { nodes?: unknown } })?.teams?.nodes, teamWanted);
    }
    if (!teamId) {
      return {
        success: false,
        error: `No Linear team matched "${teamWanted}". Use the team key (e.g. "ENG") or its exact name.`
      };
    }

    const input: Record<string, unknown> = { teamId, title: issueTitle };
    const body = String(description ?? "").trim();
    if (body) input.description = body;
    if (wantedPriority !== null) input.priority = wantedPriority;

    const created = await graphql(ISSUE_CREATE, { input }, key);
    const issue = parseCreatedIssue(created);
    if (!issue) {
      return { success: false, error: "Linear accepted the mutation but returned no issue." };
    }
    return { success: true, data: { ...issue, source: API } };
  } catch (error) {
    return { success: false, error: error instanceof Error ? error.message : String(error) };
  }
}

if (typeof require !== "undefined" && typeof module !== "undefined" && require.main === module) {
  runTool(process.argv[2] ?? "ENG", process.argv[3] ?? "Example issue", process.argv[4], process.argv[5]).then(
    (result) => console.log(JSON.stringify(result, null, 2))
  );
}
