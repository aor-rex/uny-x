# uny-x

Unofficial X client using direct httpx against X's internal GraphQL and v1.1 APIs. No official API keys needed — uses browser cookies for auth.

## Install

```bash
pip install "uny-x @ git+https://github.com/aor-rex/uny-x@v2.0.0"
# CLI included:
uny-x user @handle
```

Cookies: export from a logged-in X browser session (cookie-editor JSON),
point at it with `UNYX_COOKIES=/path/to/cookies.json` or pass it explicitly.
`cookies.json` in cwd is the fallback.

## Use as a library

```python
from unyx import UnyxClient

with UnyxClient() as c:                       # UNYX_COOKIES env, or:
    c.login_from_cookies("/path/to/cookies.json")  # explicit file wins
    me = c.user("ryu_ngmi")                   # profile
    box = c.mentions(20)                      # tweets mentioning you
    for m in box["mentions"]:
        print(m["id"], m["user"]["screen_name"], m["text"][:80])
    post = c.post("hello world")              # {"id", "text"}
    rep = c.reply(post["id"], "a reply")      # {"id", "text", "reply_to"}
```

Return shapes are plain dicts (see `_parse_tweet_entry` in `client.py`
for the full tweet shape). Writes raise `RuntimeError` when X silently
drops them — never fails quiet.

## Setup (CLI)

1. Export cookies from a logged-in X browser session (Firefox JSON format)
2. Save as `cookies.json` or `x.com_cookies.json` in the project root
3. Run any command — it auto-loads cookies and restores the session

```bash
python3 -m unyx.cli user @handle
python3 -m unyx.cli timeline -n 10
python3 -m unyx.cli post "hello world"
```

## Commands

| Command | Description |
|---------|-------------|
| `login` | Auth from cookies (auto-detected) |
| `post` | Post a tweet |
| `reply` | Reply to a tweet |
| `retweet` | Retweet |
| `delete` | Delete your tweet |
| `like` / `unlike` | Like/unlike |
| `follow` / `unfollow` | Follow/unfollow |
| `name` | Change profile display name (not @handle) |
| `avatar` | Change profile image from a local file |
| `dm` | Send a DM |
| `dms` | Read DM inbox |
| `mentions` | Search for tweets mentioning you |
| `read` | Get tweet details |
| `user` | Get user profile |
| `timeline` | Home timeline |
| `search` | Search tweets |
| `tweets` | Get user's tweets |
| `bookmarks` | Get your bookmarks |
| `following` / `followers` | Get following/followers |

## Limitations

**DM inbox reading is unreliable** with cookie auth. Incoming DMs from accounts you don't follow may not appear in the inbox due to X's request filter and cookie session staleness. DM sending works fine.

For reliable DM inbox access, use the official X API (OAuth 2.0) via tools like `xurl`.
