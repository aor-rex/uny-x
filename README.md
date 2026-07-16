# uny-x — unofficial x client

talks to x's internal api directly. no twikit, no tweety, no official keys. just httpx and a cookies file.

zero api fees. burner account friendly.

## setup

```bash
pip install -r requirements.txt
```

export cookies from a logged-in x session (firefox json format) and save as `cookies.json` in the project root. that's auth — no login command needed.

> cookies.json is gitignored. don't commit it.

## usage

tweet ids or full urls both work.

```
reads:
  uny-x user @handle           user profile
  uny-x read TWEET_ID          tweet details
  uny-x tweets @handle         user's tweets
  uny-x search "query"         search tweets
  uny-x timeline               home feed (following)
  uny-x bookmarks              your bookmarks
  uny-x followers @handle      who follows them
  uny-x following @handle      who they follow

writes:
  uny-x post "text"            post a tweet
  uny-x reply TWEET_ID "text"  reply
  uny-x like TWEET_ID          like
  uny-x unlike TWEET_ID        unlike
  uny-x retweet TWEET_ID       retweet
  uny-x delete TWEET_ID        delete your tweet
  uny-x follow @handle         follow
  uny-x unfollow @handle       unfollow

options:
  -n N    result count (default 20)
```

## how it works

talks to x's internal graphql api — same endpoints x.com uses. no developer portal, no rate limit cards.

reads are GET with json params. writes are POST with json body. follow/unfollow uses x's legacy v1.1 api.

query ids come from twikit's source but verified manually. some endpoints that used to be get now need post (x changes stuff). handled.

## why not xurl

xurl uses the official x api v2. that costs money. uny-x uses the same internal api x.com itself uses. free, but fragile — query ids go stale, endpoints change, no guarantees.
