"""
Telegram Channel Alert Dispatcher

Sends formatted alerts -- text and photo -- to a Telegram group or channel
through the Telegram Bot API.

Named for the channel case on purpose: a channel post is what this is for, and
the two things that break there are the same two that break everywhere -- the
message length limit and the parse-mode escaping. Both are handled here rather
than left to the caller.

Requires a bot token from @BotFather, and the bot must be a member of the target
group (or an administrator of the channel). The token can be passed via the
`bot_token` parameter or the TELEGRAM_BOT_TOKEN environment variable.
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

API_URL = "https://api.telegram.org"

# Telegram's own limits. A caption limit ten times smaller than the message
# limit is the one that catches people out: a 2000-character alert posts fine as
# a message and is rejected outright as a photo caption.
MAX_MESSAGE_LENGTH = 4096
MAX_CAPTION_LENGTH = 1024

# Characters MarkdownV2 reserves. Telegram rejects the WHOLE message with a 400
# if any of these is unescaped, so a stray "!" or "." breaks an alert that looks
# perfectly fine in the terminal.
MARKDOWN_V2_RESERVED = r"_*[]()~`>#+-=|{}.!"

SEVERITY_BADGES = {
    "info": "\u2139\ufe0f",       # ℹ️
    "warning": "\u26a0\ufe0f",    # ⚠️
    "critical": "\U0001f6a8",     # 🚨
}


def escape_markdown_v2(text: str) -> str:
    """Escape every character MarkdownV2 reserves, so caller text cannot break the message."""
    return "".join("\\" + ch if ch in MARKDOWN_V2_RESERVED else ch for ch in str(text))


def escape_html(text: str) -> str:
    """Escape the three characters HTML parse mode treats as markup."""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def format_alert(message: str, severity: Optional[str] = None,
                 parse_mode: Optional[str] = "HTML") -> str:
    """
    Prefix the message with a severity badge, escaped for the chosen parse mode.

    The caller's own text is left exactly as written: they may have deliberately
    formatted it, and rewriting their markup would be worse than the badge is
    worth. Only the badge this function adds is escaped.
    """
    body = str(message or "")
    key = str(severity or "").strip().lower()
    badge = SEVERITY_BADGES.get(key)
    if not badge:
        return body
    if parse_mode == "MarkdownV2":
        return "%s \\*%s\\* %s" % (badge, escape_markdown_v2(key.upper()), body)
    if parse_mode == "HTML":
        return "%s <b>%s</b> %s" % (badge, escape_html(key.upper()), body)
    return "%s %s %s" % (badge, key.upper(), body)


def split_message(text: str, limit: int = MAX_MESSAGE_LENGTH) -> List[str]:
    """
    Split text into chunks no longer than `limit`.

    Splits on a line break when one is available near the limit and only falls
    back to a hard cut when a single line is longer than the limit itself -- a
    mid-word break is ugly, but Telegram rejects an over-long message outright,
    so a hard cut is the lesser failure. Never returns an empty chunk.
    """
    body = str(text or "")
    if limit <= 0:
        return [body] if body else []
    if len(body) <= limit:
        return [body] if body else []

    chunks: List[str] = []
    remaining = body
    while len(remaining) > limit:
        window = remaining[:limit + 1]
        cut = window.rfind("\n")
        if cut <= 0:
            cut = window.rfind(" ")
        if cut <= 0:
            cut = limit
        chunk = remaining[:cut].rstrip()
        # A window that is pure whitespace would produce an empty chunk and loop
        # forever; fall back to the hard cut.
        if not chunk:
            chunk = remaining[:limit]
            cut = limit
        chunks.append(chunk)
        remaining = remaining[cut:].lstrip("\n")
    if remaining:
        chunks.append(remaining)
    return chunks


def _call(method: str, payload: Dict[str, Any], token: str, timeout: int = 20) -> Dict[str, Any]:
    """
    Call one Bot API method.

    The bot token is part of the request URL, so it is never put in a message
    this module raises -- an error string that carried the URL would leak the
    token into logs and transcripts.
    """
    url = "%s/bot%s/%s" % (API_URL, token, method)
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (AgentToolsHub/1.0)",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = ""
        try:
            body = json.loads(error.read().decode("utf-8"))
            detail = body.get("description") or ""
        except Exception:
            detail = ""
        raise RuntimeError("Telegram %s returned HTTP %s%s"
                           % (method, error.code, ": " + detail if detail else ""))
    except Exception as error:  # noqa: BLE001
        raise RuntimeError("Telegram %s failed: %s" % (method, error))


def _chat_id(value: Any) -> str:
    """
    Accept the three shapes a channel or group id arrives in: the numeric id
    (often negative, and for a channel usually starting -100), the @username
    form, and a bare username. A bare one is prefixed, because Telegram rejects
    it otherwise and the failure is a bare "chat not found".
    """
    text = str(value or "").strip()
    if not text:
        return ""
    if text.startswith("@") or text.startswith("-") or text.lstrip("-").isdigit():
        return text
    return "@" + text


def run_tool(
    chat_id: str,
    message: str = "",
    photo_url: Optional[str] = None,
    photo_caption: Optional[str] = None,
    severity: Optional[str] = None,
    parse_mode: Optional[str] = "HTML",
    bot_token: Optional[str] = None,
    disable_notification: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Send an alert to a Telegram group or channel.

    Args:
        chat_id: Channel or group, as @username, a bare username, or the numeric
            id (channels usually look like -100XXXXXXXXXX).
        message: Alert text. Split automatically if it exceeds Telegram's 4096
            character limit.
        photo_url: Optional image URL. When set, the alert is posted as a photo
            with the caption instead of a plain message.
        photo_caption: Caption for the photo; falls back to `message`.
        severity: "info", "warning" or "critical" -- prefixes a badge.
        parse_mode: "HTML" (default), "MarkdownV2", "Markdown", or None.
        bot_token: Bot token; falls back to the TELEGRAM_BOT_TOKEN env var.
        disable_notification: Send silently (useful for off-hours alerts).

    Returns:
        Dict with the message ids Telegram accepted, and any chunk that failed.
    """
    token = (bot_token or os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    if not token:
        return {
            "success": False,
            "error": (
                "A Telegram bot token is required. Pass bot_token or set the "
                "TELEGRAM_BOT_TOKEN environment variable (get one from @BotFather)."
            ),
        }

    target = _chat_id(chat_id)
    if not target:
        return {"success": False, "error": "chat_id is required (a @username or numeric channel id)."}

    if parse_mode not in (None, "", "HTML", "MarkdownV2", "Markdown"):
        return {
            "success": False,
            "error": 'parse_mode must be "HTML", "MarkdownV2", "Markdown" or omitted; got "%s".' % parse_mode,
        }

    badge_text = format_alert(message, severity, parse_mode or None)
    raw_caption = photo_caption if photo_caption else message
    caption = format_alert(raw_caption, severity, parse_mode or None)

    if not badge_text.strip() and not photo_url:
        return {"success": False, "error": "message must not be empty (or pass photo_url)."}

    base: Dict[str, Any] = {"chat_id": target}
    if parse_mode:
        base["parse_mode"] = parse_mode
    if disable_notification:
        base["disable_notification"] = True

    sent: List[Dict[str, Any]] = []
    errors: List[str] = []
    try:
        if photo_url:
            photo_payload = dict(base)
            photo_payload["photo"] = photo_url
            # A caption limit ten times smaller than the message limit: an
            # over-long caption is rejected, so the photo goes out with what
            # fits and the remainder follows as its own message.
            photo_payload["caption"] = caption[:MAX_CAPTION_LENGTH]
            response = _call("sendPhoto", photo_payload, token)
            if response.get("ok"):
                result = response.get("result") or {}
                sent.append({"kind": "photo", "message_id": result.get("message_id")})
            else:
                errors.append("sendPhoto: %s" % response.get("description", "unknown error"))

            overflow = caption[MAX_CAPTION_LENGTH:].strip()
            if overflow:
                for chunk in split_message(overflow):
                    response = _call("sendMessage", dict(base, text=chunk), token)
                    if response.get("ok"):
                        sent.append({"kind": "text", "message_id": (response.get("result") or {}).get("message_id")})
                    else:
                        errors.append("sendMessage: %s" % response.get("description", "unknown error"))

        for chunk in split_message(badge_text):
            response = _call("sendMessage", dict(base, text=chunk), token)
            if response.get("ok"):
                sent.append({"kind": "text", "message_id": (response.get("result") or {}).get("message_id")})
            else:
                errors.append("sendMessage: %s" % response.get("description", "unknown error"))
    except RuntimeError as error:
        return {"success": False, "error": str(error), "sent": sent}

    # A partial send is NOT a success: some chunk did not arrive, so the alert is
    # incomplete and the caller must know. `sent` still lists what did land, so a
    # retry can be aimed at the rest rather than re-posting everything.
    if errors:
        return {
            "success": False,
            "error": "; ".join(errors),
            "chat_id": target,
            "sent_count": len(sent),
            "sent": sent,
        }
    return {
        "success": True,
        "chat_id": target,
        "sent_count": len(sent),
        "sent": sent,
        "errors": [],
    }


if __name__ == "__main__":
    print(json.dumps(
        run_tool(
            chat_id="@my_channel",
            message="Deploy finished.",
            severity="info",
        ),
        indent=2,
    ))
