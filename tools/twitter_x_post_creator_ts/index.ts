/**
 * Twitter / X Post Creator Tool
 *
 * Creates a text post using the X API v2.
 */

interface XPostParams {
  text: string;
}

interface XPostResult {
  success: boolean;
  post_id?: string;
  text?: string;
  error?: string;
  status?: number;
}

interface XApiResponse {
  data?: {
    id: string;
    text: string;
  };
  title?: string;
  detail?: string;
  errors?: Array<{
    message?: string;
    detail?: string;
  }>;
}

async function createPost(text: string): Promise<XPostResult> {
  if (!text || !text.trim()) {
    return {
      success: false,
      error: "Post text is required."
    };
  }

  const accessToken = process.env.X_USER_ACCESS_TOKEN;

  if (!accessToken) {
    return {
      success: false,
      error:
        "X_USER_ACCESS_TOKEN environment variable is required."
    };
  }

  try {
    const response = await fetch(
      "https://api.x.com/2/tweets",
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json",
          "User-Agent": "AgentToolsHub/1.0"
        },
        body: JSON.stringify({
          text: text.trim()
        })
      }
    );

    const data = (await response.json()) as XApiResponse;

    if (!response.ok) {
      const apiError =
        data.detail ||
        data.title ||
        data.errors?.[0]?.detail ||
        data.errors?.[0]?.message ||
        `X API request failed with HTTP ${response.status}.`;

      return {
        success: false,
        status: response.status,
        error: apiError
      };
    }

    if (!data.data?.id) {
      return {
        success: false,
        status: response.status,
        error: "X API returned no post ID."
      };
    }

    return {
      success: true,
      status: response.status,
      post_id: data.data.id,
      text: data.data.text
    };
  } catch (error) {
    return {
      success: false,
      error:
        error instanceof Error
          ? `X API request failed: ${error.message}`
          : `X API request failed: ${String(error)}`
    };
  }
}

async function runTool(
  params: XPostParams
): Promise<XPostResult> {
  return createPost(params.text);
}

export { createPost, runTool };
export type { XPostParams, XPostResult };


// Optional local smoke test.
// This will only post when X_USER_ACCESS_TOKEN is configured.
if (require.main === module) {
  (async () => {
    if (!process.env.X_USER_ACCESS_TOKEN) {
      console.log(
        "Set X_USER_ACCESS_TOKEN to run the live X API smoke test."
      );
      return;
    }

    console.log(
      "Token detected. Import runTool() to perform a controlled live test."
    );
  })();
}