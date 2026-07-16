# uny-x — unofficial x client

talks to x's internal api directly. no twikit, no tweety, no official keys. just httpx and a cookies file.

zero api fees. burner account friendly.

## setup

```bash
# python deps
pip install -r requirements.txt

# auth — export cookies from a logged-in x session (firefox json format)
# and save as cookies.json in the project root
```

that's it. no login command. the cookies *are* your auth.

> **safety:** cookies.json is gitignored. don't commit it.

## usage

all commands accept tweet urls or numeric ids.

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
  uny-x reply TWEET_ID "text"  reply to a tweet
  uny-x like TWEET_ID          like
  uny-x unlike TWEET_ID        unlike
  uny-x retweet TWEET_ID       retweet
  uny-x delete TWEET_ID        delete your tweet
  uny-x follow @handle         follow
  uny-x unfollow @handle       unfollow

options:
  -n N    result count (default 20)
```

## example session

```bash
uny-x user @x
uny-x search "build in public" -n 5
uny-x post "testing testing"
uny-x like 2077762710213664814
uny-x reply 2077762710213664814 "nice"
```

## how it works

uses **x's internal graphql api** — same endpoints the web app uses. no developer portal, no rate limit cards, no oauth dance.

- reads → GET with json params
- writes → POST with json body
- follow/unfollow → x's legacy v1.1 api (form post)
- query ids from twikit's source, manually verified

some endpoints that used to be get now need post (x changes stuff). handled.

## dev

```
venv at /opt/data/.venv-x/
query ids live in unyx/client.py → GQL_EP dict
features in FEATURES / USER_FEATURES dicts
```

when x rotates query ids (404 on a working endpoint), pull fresh ones from twikit's gql.py:
```
/opt/data/.venv-x/lib/python3.13/site-packages/twikit/client/gql.py
```

## git

```bash
git remote -v
# gitlab → git@gitlab.com:aor-rex/uny-x.git
# codeberg → git@codeberg.org:aor-rex/uny-x.git
```

## why not xurl

xurl uses the official x api v2. that costs money. uny-x uses the same internal api x.com itself uses. free, but fragile — query ids go stale, endpoints change, and there's no guarantee.
