# uny-x — unofficial X client

Human-like X/Twitter client using the unofficial internal API (twikit). No API keys, no fees — just a burner account.

## Setup

```bash
# install deps
cd uny-x
pip install -r requirements.txt

# login once
uny-x login username email@example.com password
```

Session saved to `cookies.json` — subsequent commands auto-restore.

## Usage

```
Actions:
  uny-x post "text"
  uny-x reply TWEET_ID "text"
  uny-x quote TWEET_ID "text"
  uny-x retweet TWEET_ID
  uny-x like TWEET_ID
  uny-x unlike TWEET_ID
  uny-x follow @handle
  uny-x unfollow @handle
  uny-x dm @handle "message"
  uny-x delete TWEET_ID

Reads:
  uny-x read TWEET_ID
  uny-x user @handle
  uny-x timeline [-n 20]
  uny-x search "query" [-n 20]
  uny-x tweets @handle [keyword]
  uny-x mentions [-n 20]
  uny-x followers @handle [-n 20]
  uny-x following @handle [-n 20]
  uny-x bookmarks [-n 20]
```

TWEET_ID accepts either numeric IDs or full URLs (e.g. `https://x.com/user/status/123`).
