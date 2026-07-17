# uny-x

Unofficial X client using direct httpx against X's internal GraphQL and v1.1 APIs. No official API keys needed — uses browser cookies for auth.

## Setup

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
