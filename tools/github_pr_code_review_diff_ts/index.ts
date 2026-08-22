/**
 * GitHub Pull Request Code Review Diff Tool - TypeScript
 *
 * Fetches changed files and patch details for an open GitHub pull request.
 */

interface PullRequestFile {
  filename: string;
  status: string;
  additions: number;
  deletions: number;
  changes: number;
  patch?: string;
  blob_url?: string;
  raw_url?: string;
}

interface PullRequestDiffResult {
  success: boolean;
  repository?: string;
  pull_request?: number;
  title?: string;
  state?: string;
  changed_files?: number;
  files?: PullRequestFile[];
  error?: string;
}

interface GitHubPullRequest {
  number: number;
  title: string;
  state: string;
  head: { sha: string };
  base: { sha: string };
}

function buildHeaders(token?: string): Record<string, string> {
  const headers: Record<string, string> = {
    Accept: "application/vnd.github+json",
    "User-Agent": "AgentToolsHub/1.0",
    "X-GitHub-Api-Version": "2022-11-28",
  };

  if (token?.trim()) {
    headers.Authorization = `Bearer ${token.trim()}`;
  }

  return headers;
}

function parsePullRequestUrl(url: string): {
  owner: string;
  repo: string;
  pullNumber: number;
} | null {
  try {
    const parsed = new URL(url.trim());
    if (parsed.hostname !== "github.com") {
      return null;
    }

    const parts = parsed.pathname.split("/").filter(Boolean);
    if (parts.length < 4 || parts[2] !== "pull") {
      return null;
    }

    const pullNumber = Number(parts[3]);
    if (!Number.isInteger(pullNumber) || pullNumber <= 0) {
      return null;
    }

    return {
      owner: parts[0],
      repo: parts[1],
      pullNumber,
    };
  } catch {
    return null;
  }
}

/**
 * Fetches changed files and patch details for a GitHub pull request.
 *
 * Provide either a GitHub pull request URL or owner/repo/pull_number.
 * GITHUB_TOKEN is used automatically when token is not provided.
 */
async function getPullRequestDiff(
  pullRequestUrl?: string,
  owner?: string,
  repo?: string,
  pullNumber?: number,
  token?: string,
): Promise<PullRequestDiffResult> {
  let resolvedOwner = owner?.trim();
  let resolvedRepo = repo?.trim();
  let resolvedPullNumber = pullNumber;

  if (pullRequestUrl) {
    const parsed = parsePullRequestUrl(pullRequestUrl);
    if (!parsed) {
      return {
        success: false,
        error: "Invalid GitHub pull request URL. Expected https://github.com/{owner}/{repo}/pull/{number}.",
      };
    }

    resolvedOwner = parsed.owner;
    resolvedRepo = parsed.repo;
    resolvedPullNumber = parsed.pullNumber;
  }

  if (!resolvedOwner || !resolvedRepo || !resolvedPullNumber) {
    return {
      success: false,
      error: "Provide a pull_request_url or owner, repo, and pull_number.",
    };
  }

  if (!Number.isInteger(resolvedPullNumber) || resolvedPullNumber <= 0) {
    return {
      success: false,
      error: "pull_number must be a positive integer.",
    };
  }

  const envToken = (globalThis as { process?: { env?: Record<string, string | undefined> } })
    .process?.env?.GITHUB_TOKEN;
  const authToken = token?.trim() || envToken;
  const headers = buildHeaders(authToken);
  const apiBase = `https://api.github.com/repos/${encodeURIComponent(resolvedOwner)}/${encodeURIComponent(resolvedRepo)}/pulls/${resolvedPullNumber}`;

  try {
    const pullResponse = await fetch(apiBase, { headers });

    if (!pullResponse.ok) {
      return {
        success: false,
        error: `GitHub API error: HTTP ${pullResponse.status} ${pullResponse.statusText}`,
      };
    }

    const pull = (await pullResponse.json()) as GitHubPullRequest;

    if (pull.state !== "open") {
      return {
        success: false,
        error: `Pull request #${resolvedPullNumber} is not open (state: ${pull.state}).`,
      };
    }

    const filesResponse = await fetch(`${apiBase}/files?per_page=100`, { headers });

    if (!filesResponse.ok) {
      return {
        success: false,
        error: `GitHub API error while fetching files: HTTP ${filesResponse.status} ${filesResponse.statusText}`,
      };
    }

    const files = (await filesResponse.json()) as PullRequestFile[];

    return {
      success: true,
      repository: `${resolvedOwner}/${resolvedRepo}`,
      pull_request: pull.number,
      title: pull.title,
      state: pull.state,
      changed_files: files.length,
      files: files.map((file) => ({
        filename: file.filename,
        status: file.status,
        additions: file.additions,
        deletions: file.deletions,
        changes: file.changes,
        patch: file.patch,
        blob_url: file.blob_url,
        raw_url: file.raw_url,
      })),
    };
  } catch (error) {
    return {
      success: false,
      error: `GitHub request failed: ${error instanceof Error ? error.message : String(error)}`,
    };
  }
}

export { getPullRequestDiff, parsePullRequestUrl };

