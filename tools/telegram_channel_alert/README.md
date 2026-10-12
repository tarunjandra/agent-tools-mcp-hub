# Telegram Channel Alert Dispatcher

A Python tool that posts formatted text and photo alerts to a Telegram group or channel through the Telegram Bot API.

It exists for the **channel** case, where two things break and both are handled here instead of being left to the caller: Telegram's message-length limit and its parse-mode escaping.

> Related: [`tools/telegram_notifier/`](../telegram_notifier/) sends plain text and Markdown/HTML notifications. This tool adds **photo alerts**, severity badges, and automatic splitting — reach for it when the alert is long, visual, or going to a channel.

## Prerequisites

A bot token from [@BotFather](https://t.me/BotFather). The bot must be a **member** of the target group, or an **administrator** of the channel — a bot cannot post to a channel it does not administer, and Telegram's refusal is a bare "chat not found".

Then either:

- Set it as the `TELEGRAM_BOT_TOKEN` environment variable, or
- Pass it as the `bot_token` parameter.

## Parameters

| Parameter | Type | Required | Description | Default |
| :--- | :--- | :--- | :--- | :--- |
| `chat_id` | `string` | Yes | `@username`, a bare username, or the numeric id (channels usually look like `-100XXXXXXXXXX`) | — |
| `message` | `string` | No | Alert text; split automatically past 4096 characters | `""` |
| `photo_url` | `string` | No | Image URL; when set the alert posts as a photo with the caption | — |
| `photo_caption` | `string` | No | Caption for the photo; falls back to `message` | — |
| `severity` | `string` | No | `info`, `warning` or `critical` — prefixed as a badge | — |
| `parse_mode` | `string` | No | `HTML` (default), `MarkdownV2`, `Markdown`, or omit for plain text | `HTML` |
| `bot_token` | `string` | No | Bot token; falls back to `TELEGRAM_BOT_TOKEN` | — |
| `disable_notification` | `boolean` | No | Send silently, for off-hours alerts | `False` |

## Usage

```python
import os
from tool import run_tool

os.environ["TELEGRAM_BOT_TOKEN"] = "123456:ABC..."

# A text alert with a severity badge
result = run_tool(
    chat_id="@ops_channel",
    message="Nightly build failed on the release branch.",
    severity="critical",
)
print(result["sent_count"], "message(s) sent")

# A photo alert; a long caption spills into a follow-up message
run_tool(
    chat_id="-1001234567890",
    photo_url="https://example.com/graph.png",
    photo_caption="Latency p99 over the last 24h.",
    severity="warning",
    disable_notification=True,
)
```

### CLI test

```bash
TELEGRAM_BOT_TOKEN=123456:ABC... python tool.py
```

## Notes

- **Long messages are split, not rejected.** Telegram's limit is 4096 characters and an over-long message fails outright. Text is split on a line break near the limit, falling back to a space and only then to a hard cut — a mid-word break is ugly, but a rejected alert is worse. Chunks are never empty.
- **The caption limit is ten times smaller.** Photo captions cap at **1024** characters, which is the trap: a 2000-character alert posts fine as a message and is refused as a caption. When the caption is too long, the photo goes out with what fits and the remainder follows as its own message, so nothing is silently dropped.
- **`MarkdownV2` reserves a long list of characters** (`_ * [ ] ( ) ~ ` > # + - = | { } . !`) and Telegram rejects the **entire** message if one is unescaped — a stray `!` breaks an alert that looks fine in the terminal. `escape_markdown_v2()` and `escape_html()` are exported, and the severity badge is escaped for the chosen mode. The caller's own text is left exactly as written, because they may have formatted it deliberately.
- **The bot token never reaches an error message.** It is part of the request URL, so errors name the method (`Telegram sendMessage returned HTTP 400: chat not found`) rather than the URL. A tool that echoed the URL would leak the token into logs and transcripts.
- **A partial failure is reported as partial.** If the first chunk sends and a later one fails, `success` is `False` but `sent` lists what did land, so a retry does not silently double-post.
