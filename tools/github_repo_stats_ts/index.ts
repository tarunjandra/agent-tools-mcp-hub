/**
 * GitHub Repository Stats & Releases Tool - TypeScript Implementation
 *
 * Fetches public repository statistics and release history via the GitHub REST API.
 * Works unauthenticated (60 requests/hour). Set GITHUB_TOKEN to raise the limit to 5,000/hour.
 */

const GITHUB_API = "https://api.github.com";

interface RepoStats {
  full_name: string;
  description: string;
  homepage: string;
  language: string;
  stars: number;
  forks: number;
  watchers: number;
  open_issues: number;
  license: string;
  topics: string[];
  default_branch: string;
  archived: boolean;
  created_at: string;
  pushed_at: string;
  repo_url: string;
}

interface ReleaseInfo {
  tag: string;
  name: string;
  published_at: string;
  is_prerelease: boolean;
  is_draft: boolean;
  author: string;
  asset_count: number;
  total_downloads: number;
  release_url: string;
}

interface ToolResult {
  success: boolean;
  data?: {
    stats?: RepoStats;
    latest_release?: ReleaseInfo | null;
    releases?: ReleaseInfo[];
    release_count?: number;
  };
  error?: string;
}

/** Raw GitHub API shapes (only the fields this tool reads). */
interface GitHubRepo {
  full_name: string;
  description: string | null;
  homepage: string | null;
  language: string | null;
  stargazers_count: number;
  forks_count: number;
  subscribers_count?: number;
  watchers_count: number;
  open_issues_count: number;
  license: { spdx_id?: string; name?: string } | null;
  topics?: string[];
  default_branch: string;
  archived: boolean;
  created_at: string;
  pushed_at: string;
  html_url: string;
}

interface GitHubReleaseAsset {
  download_count?: number;
}

interface GitHubRelease {
  tag_name: string;
  name: string | null;
  published_at: string | null;
  prerelease: boolean;
  draft: boolean;
  author?: { login?: string };
  assets?: GitHubReleaseAsset[];
  html_url: string;
}

/** Builds request headers, adding the optional token when one is present. */
function buildHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    "User-Agent": "AgentToolsHub/1.0",
    Accept: "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
  };

  const token = process.env.GITHUB_TOKEN;
  if (token && token.trim()) {
    headers.Authorization = `Bearer ${token.trim()}`;
  }

  return headers;
}

/** Validates and splits an "owner/repo" identifier. */
function parseRepo(repo: string): { owner: string; name: string } | null {
  if (!repo || !repo.trim()) return null;

  const cleaned = repo
    .trim()
    .replace(/^https?:\/\/github\.com\//i, "")
    .replace(/\/+$/, "")
    .replace(/\.git$/i, "")
    .replace(/\/+$/, "");

  const parts = cleaned.split("/");
  if (parts.length !== 2) return null;

  const [owner, name] = parts;
  if (!owner || !name) return null;

  return { owner, name };
}

/**
 * Shared request helper. Translates GitHub's HTTP responses into
 * descriptive errors instead of leaking raw status codes to the agent.
 */
async function githubRequest<T>(path: string): Promise<{ ok: true; data: T } | { ok: false; error: string }> {
  try {
    const response = await fetch(`${GITHUB_API}${path}`, { headers: buildHeaders() });

    if (!response.ok) {
      if (response.status === 404) {
        return { ok: false, error: `Repository not found, or it is private and the token cannot see it: ${path}` };
      }

      if (response.status === 401) {
        return { ok: false, error: "GITHUB_TOKEN was rejected by GitHub (401). Check that the token is valid and not expired." };
      }

      if (response.status === 403 || response.status === 429) {
        const remaining = response.headers.get("x-ratelimit-remaining");
        if (remaining === "0") {
          const reset = response.headers.get("x-ratelimit-reset");
          const resetAt = reset ? new Date(Number(reset) * 1000).toISOString() : "shortly";
          return {
            ok: false,
            error: `GitHub API rate limit exceeded (resets at ${resetAt}). Set a GITHUB_TOKEN environment variable to raise the limit from 60 to 5,000 requests/hour.`
          };
        }
        return { ok: false, error: `Access forbidden by GitHub (HTTP ${response.status}).` };
      }

      return { ok: false, error: `GitHub API error: HTTP ${response.status} ${response.statusText}` };
    }

    const data = (await response.json()) as T;
    return { ok: true, data };
  } catch (error) {
    return {
      ok: false,
      error: `Network error contacting GitHub: ${error instanceof Error ? error.message : String(error)}`
    };
  }
}

/** Maps a raw release payload into the tool's flattened shape. */
function mapRelease(release: GitHubRelease): ReleaseInfo {
  const assets = release.assets ?? [];
  return {
    tag: release.tag_name,
    name: release.name || release.tag_name,
    published_at: release.published_at ? release.published_at.split("T")[0] : "",
    is_prerelease: Boolean(release.prerelease),
    is_draft: Boolean(release.draft),
    author: release.author?.login || "",
    asset_count: assets.length,
    total_downloads: assets.reduce((sum, asset) => sum + (asset.download_count ?? 0), 0),
    release_url: release.html_url
  };
}

/** Fetches core repository statistics. */
async function getRepoStats(repo: string): Promise<ToolResult> {
  const parsed = parseRepo(repo);
  if (!parsed) {
    return { success: false, error: "Repository must be in 'owner/repo' format, e.g. 'tarunjandra/agent-tools-mcp-hub'." };
  }

  const result = await githubRequest<GitHubRepo>(`/repos/${parsed.owner}/${parsed.name}`);
  if (!result.ok) return { success: false, error: result.error };

  const r = result.data;
  return {
    success: true,
    data: {
      stats: {
        full_name: r.full_name,
        description: r.description || "",
        homepage: r.homepage || "",
        language: r.language || "",
        stars: r.stargazers_count,
        forks: r.forks_count,
        watchers: r.subscribers_count ?? r.watchers_count,
        open_issues: r.open_issues_count,
        license: r.license?.spdx_id || r.license?.name || "None",
        topics: r.topics ?? [],
        default_branch: r.default_branch,
        archived: r.archived,
        created_at: r.created_at.split("T")[0],
        pushed_at: r.pushed_at.split("T")[0],
        repo_url: r.html_url
      }
    }
  };
}

/** Fetches recent releases, newest first. */
async function getReleases(repo: string, limit: number = 5): Promise<ToolResult> {
  const parsed = parseRepo(repo);
  if (!parsed) {
    return { success: false, error: "Repository must be in 'owner/repo' format, e.g. 'tarunjandra/agent-tools-mcp-hub'." };
  }

  const safeLimit = Math.min(Math.max(Math.trunc(limit) || 5, 1), 30);
  const result = await githubRequest<GitHubRelease[]>(
    `/repos/${parsed.owner}/${parsed.name}/releases?per_page=${safeLimit}`
  );
  if (!result.ok) return { success: false, error: result.error };

  const releases = (result.data ?? []).map(mapRelease);
  const published = releases.filter((rel) => !rel.is_draft);

  return {
    success: true,
    data: {
      latest_release: published.length > 0 ? published[0] : null,
      releases,
      release_count: releases.length
    }
  };
}

/**
 * Main entry point.
 *
 * @param repo   Repository in "owner/repo" format (a full GitHub URL is also accepted).
 * @param action "stats" | "releases" | "all" (default "all").
 * @param limit  Number of releases to return, 1-30 (default 5).
 */
async function runTool(repo: string, action: string = "all", limit: number = 5): Promise<ToolResult> {
  const mode = (action || "all").toLowerCase();

  if (mode === "stats") return await getRepoStats(repo);
  if (mode === "releases") return await getReleases(repo, limit);

  if (mode !== "all") {
    return { success: false, error: `Unknown action '${action}'. Use 'stats', 'releases' or 'all'.` };
  }

  const [statsResult, releasesResult] = await Promise.all([getRepoStats(repo), getReleases(repo, limit)]);

  // A repo with no releases is normal; only a stats failure is fatal.
  if (!statsResult.success) return statsResult;
  if (!releasesResult.success) return releasesResult;

  return {
    success: true,
    data: { ...statsResult.data, ...releasesResult.data }
  };
}

export { getRepoStats, getReleases, runTool };
export type { RepoStats, ReleaseInfo, ToolResult };

// Manual test run: `npm start`. Guarded so importing the module never fires network calls.
if (require.main === module) {
  (async () => {
    const target = process.argv[2] || "tarunjandra/agent-tools-mcp-hub";
    console.log(`Fetching stats and releases for ${target}...\n`);
    const result = await runTool(target, "all", 3);
    console.log(JSON.stringify(result, null, 2));
  })();
}
