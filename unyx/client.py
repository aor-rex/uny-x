"""uny-x client — direct httpx against X internal API.

Uses cookies from a logged-in X browser session.
GraphQL for most ops, v1.1 for friendships (follow/unfollow).
No twikit / tweety dependency.
"""

import json
import random
import re
import sys
import time
from pathlib import Path
from typing import Optional

import httpx

# ---------------------------------------------------------------------------
# Constants  (from twikit — see .venv-x/lib/python3.13/site-packages/twikit/constants.py)
# ---------------------------------------------------------------------------

TOKEN = (
    "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs"
    "%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
)
DOMAIN = "x.com"

FEATURES: dict = {
    "creator_subscriptions_tweet_preview_api_enabled": True,
    "c9s_tweet_anatomy_moderator_badge_enabled": True,
    "tweetypie_unmention_optimization_enabled": True,
    "responsive_web_edit_tweet_api_enabled": True,
    "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
    "view_counts_everywhere_api_enabled": True,
    "longform_notetweets_consumption_enabled": True,
    "responsive_web_twitter_article_tweet_consumption_enabled": True,
    "tweet_awards_web_tipping_enabled": False,
    "longform_notetweets_rich_text_read_enabled": True,
    "longform_notetweets_inline_media_enabled": True,
    "rweb_video_timestamps_enabled": True,
    "responsive_web_graphql_exclude_directive_enabled": True,
    "verified_phone_label_enabled": False,
    "freedom_of_speech_not_reach_fetch_enabled": True,
    "standardized_nudges_misinfo": True,
    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
    "responsive_web_media_download_video_enabled": False,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    "responsive_web_graphql_timeline_navigation_enabled": True,
    "responsive_web_enhance_cards_enabled": False,
}

USER_FEATURES: dict = {
    "hidden_profile_likes_enabled": True,
    "hidden_profile_subscriptions_enabled": True,
    "responsive_web_graphql_exclude_directive_enabled": True,
    "verified_phone_label_enabled": False,
    "subscriptions_verification_info_is_identity_verified_enabled": True,
    "subscriptions_verification_info_verified_since_enabled": True,
    "highlights_tweets_tab_ui_enabled": True,
    "responsive_web_twitter_article_notes_tab_enabled": False,
    "creator_subscriptions_tweet_preview_api_enabled": True,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    "responsive_web_graphql_timeline_navigation_enabled": True,
}

HEADERS_BASE = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
    "X-Twitter-Auth-Type": "OAuth2Session",
    "X-Twitter-Active-User": "yes",
    "Origin": f"https://{DOMAIN}",
    "Referer": f"https://{DOMAIN}/",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
}

# ---------------------------------------------------------------------------
# GraphQL endpoint IDs (from twikit gql.py)
# ---------------------------------------------------------------------------

GQL_EP = {
    # Mutations (POST)
    "CreateTweet":       "SiM_cAu83R0wnrpmKQQSEw/CreateTweet",
    "DeleteTweet":       "VaenaVgh5q5ih7kvyVjgtg/DeleteTweet",
    "FavoriteTweet":     "lI07N6Otwv1PhnEgXILM7A/FavoriteTweet",
    "UnfavoriteTweet":   "ZYKSe-w7KEslx3JhSIk5LA/UnfavoriteTweet",
    "CreateRetweet":     "ojPdsZsimiJrUGLR1sjUtA/CreateRetweet",
    "DeleteRetweet":     "iQtK4dl5hBmXewYZuEOKVw/DeleteRetweet",
    "CreateBookmark":    "aoDbu3RHznuiSkQ9aNM67Q/CreateBookmark",
    "DeleteBookmark":    "Wlmlj2-xzyS1GN3a6cj-mQ/DeleteBookmark",
    "HomeTimeline":      "-X_hcgQzmHGl29-UXxz4sw/HomeTimeline",
    "HomeLatestTimeline":"U0cdisy7QFIoTfu3-Okw0A/HomeLatestTimeline",
    # Reads (GET)
    "UserByScreenName":  "NimuplG1OB7Fd2btCLdBOw/UserByScreenName",
    "UserByRestId":      "tD8zKvQzwY3kdx5yz6YmOw/UserByRestId",
    "TweetDetail":       "U0HTv-bAWTBYylwEMT7x5A/TweetDetail",
    "TweetResultByRestId":"Xl5pC_lBk_gcO2ItU39DQw/TweetResultByRestId",
    "SearchTimeline":    "flaR-PUMshxFWZWPNpq4zA/SearchTimeline",
    "UserTweets":        "QWF3SzpHmykQHsQMixG0cg/UserTweets",
    "UserTweetsAndReplies":"vMkJyzx1wdmvOeeNG0n6Wg/UserTweetsAndReplies",
    "UserMedia":         "2tLOJWwGuCTytDrGBg8VwQ/UserMedia",
    "Likes":             "IohM3gxQHfvWePH5E3KuNA/Likes",
    "Followers":         "gC_lyAxZOptAMLCJX5UhWw/Followers",
    "Following":         "2vUj-_Ek-UmBVDNtd8OnQA/Following",
    "Bookmarks":         "qToeLeMs43Q8cr7tRYXmaQ/Bookmarks",
    # Custom-mapped (not in twikit — may need refresh)
    "ConnectTabTimeline":"5fKmzgJzgNxisAdyoJTPdg/ConnectTabTimeline",
    "BookmarkSearchTimeline":"SpDsqmz6FfYESd1e7TPcAw/BookmarkSearchTimeline",
}

# Operations that use GET instead of POST
_GQL_GET = frozenset({
    "UserByScreenName", "UserByRestId",
    "TweetDetail", "TweetResultByRestId",
    "UserTweets", "UserTweetsAndReplies", "UserMedia", "Likes",
    "Following",
    "Bookmarks",
})

# v1.1 endpoint URLs
V11_FRIENDSHIPS_CREATE = f"https://{DOMAIN}/i/api/1.1/friendships/create.json"
V11_FRIENDSHIPS_DESTROY = f"https://{DOMAIN}/i/api/1.1/friendships/destroy.json"

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

MIN_DELAY = 0.2
MAX_DELAY = 3.0


def random_delay(min_s: float = MIN_DELAY, max_s: float = MAX_DELAY) -> None:
    time.sleep(random.uniform(min_s, max_s))


_TWEET_URL_RE = re.compile(
    r"(?:https?://)?(?:www\.)?(?:x\.com|twitter\.com)/\w+/status/(\d+)"
)


def extract_tweet_id(value: str) -> str:
    m = _TWEET_URL_RE.search(value)
    if m:
        return m.group(1)
    if value.isdigit():
        return value
    raise ValueError(f"Can't extract tweet ID from: {value}")


_USERNAME_RE = re.compile(r"^@?(\w{1,15})$")


def extract_username(value: str) -> str:
    m = _USERNAME_RE.match(value)
    if m:
        return m.group(1)
    raise ValueError(f"Invalid username: {value}")


def _flatten_params(params: dict) -> dict:
    """Convert dict/list values to JSON strings (httpx handles URL encoding)."""
    flat = {}
    for key, value in params.items():
        if isinstance(value, (list, dict)):
            value = json.dumps(value, separators=(",", ":"))
        flat[key] = value
    return flat


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

COOKIES_PATH = Path(__file__).resolve().parent.parent / "cookies.json"


class UnyxClient:
    """Direct X internal API client."""

    def __init__(self):
        self._cookies: dict[str, str] = {}
        self._ct0: str = ""
        self._user_id: Optional[str] = None
        self._screen_name: Optional[str] = None

    # -- auth ----------------------------------------------------------------

    def load_cookies(self, path: str | Path = "") -> bool:
        """Load cookies from a Firefox JSON-format file."""
        p = Path(path) if path else COOKIES_PATH
        if not p.exists():
            return False
        with open(p) as f:
            raw = json.load(f)
        self._cookies = {c["name"]: c["value"] for c in raw}
        self._ct0 = self._cookies.get("ct0", "")
        return True

    def _headers(self) -> dict:
        h = dict(HEADERS_BASE)
        if self._ct0:
            h["X-Csrf-Token"] = self._ct0
        return h

    # -- low-level request helpers -------------------------------------------

    def _gql(self, name: str, variables: dict,
              features: dict | None = None,
              extra_params: dict | None = None) -> dict:
        """Execute a GraphQL operation — GET for reads, POST for writes."""
        if name in _GQL_GET:
            return self._gql_get(name, variables, features, extra_params)
        else:
            return self._gql_post(name, variables, features, extra_params)

    def _gql_get(self, name: str, variables: dict,
                  features: dict | None = None,
                  extra_params: dict | None = None) -> dict:
        """GraphQL query via GET (read operations)."""
        ep = GQL_EP[name]
        url = f"https://{DOMAIN}/i/api/graphql/{ep}"
        params: dict = {"variables": variables}
        if features is not None:
            params["features"] = features
        if extra_params is not None:
            params.update(extra_params)
        return self._request("GET", url, params=_flatten_params(params))

    def _gql_post(self, name: str, variables: dict,
                   features: dict | None = None,
                   extra_data: dict | None = None) -> dict:
        """GraphQL mutation via POST."""
        ep = GQL_EP[name]
        url = f"https://{DOMAIN}/i/api/graphql/{ep}"
        body: dict = {"variables": variables}
        # twikit includes queryId in the POST body
        qid = ep.split("/")[0]
        body["queryId"] = qid
        if features is not None:
            body["features"] = features
        if extra_data is not None:
            body.update(extra_data)
        return self._request("POST", url, json=body)

    def _v11_post(self, url: str, data: dict) -> dict:
        """v1.1 API POST (form-encoded)."""
        h = self._headers()
        h["Content-Type"] = "application/x-www-form-urlencoded"
        with httpx.Client() as client:
            resp = client.request(
                "POST", url,
                headers=h,
                cookies=self._cookies,
                data=data,
                follow_redirects=True,
                timeout=30,
            )
        if resp.status_code != 200:
            raise RuntimeError(
                f"X v1.1 error {resp.status_code}: {resp.text[:300]}"
            )
        return resp.json()

    def _request(self, method: str, url: str, **kwargs) -> dict:
        """Raw HTTP request with cookie auth."""
        with httpx.Client() as client:
            resp = client.request(
                method, url,
                headers=self._headers(),
                cookies=self._cookies,
                follow_redirects=True,
                timeout=30,
                **kwargs,
            )
        if resp.status_code != 200:
            raise RuntimeError(
                f"X API error {resp.status_code}: {resp.text[:300]}"
            )
        data = resp.json()
        # GraphQL may return partial data + errors (e.g. already-liked)
        if "errors" in data and data.get("data") is None:
            raise RuntimeError(
                f"X API error in response: "
                f"{json.dumps(data['errors'][:3], indent=2)}"
            )
        return data

    # -- auth ----------------------------------------------------------------

    def login_from_cookies(self) -> bool:
        """Verify cookies by fetching the authenticated user's profile."""
        if not self.load_cookies():
            return False
        try:
            # extract user id from twid cookie (format: u=1234567890, URL-encoded)
            from urllib.parse import unquote
            twid = unquote(self._cookies.get("twid", ""))
            user_id = twid.replace("u=", "") if twid.startswith("u=") else ""
            if not user_id:
                raise RuntimeError("no twid cookie — cookies might be invalid")

            # verify session by fetching own profile
            result = self._gql_get(
                "UserByRestId",
                {"userId": user_id,
                 "withSafetyModeUserFields": True},
                USER_FEATURES,
                {"fieldToggles": {"withAuxiliaryUserLabels": False}},
            )
            u = result.get("data", {}).get("user", {}).get("result", {})
            self._user_id = u.get("rest_id", "")
            core = u.get("core", {})
            self._screen_name = core.get("screen_name", "ryu_ngmi")
            print(f"  [uny-x] session restored — @{self._screen_name}",
                  file=sys.stderr)
            return True
        except Exception as exc:
            print(f"  [uny-x] cookie restore failed: {exc}", file=sys.stderr)
            return False

    def _ensure_authed(self):
        if self._user_id is not None:
            return
        if not self.login_from_cookies():
            raise RuntimeError(
                "Not logged in. Place a cookies.json (Firefox JSON export) "
                "in the project root."
            )

    # -- public API ----------------------------------------------------------

    # ----- writes (POST mutations) -----------------------------------------

    def post(self, text: str):
        self._ensure_authed()
        random_delay()
        vars_ = {
            "tweet_text": text,
            "dark_request": False,
            "media": {"media_entities": [], "possibly_sensitive": False},
            "semantic_annotation_ids": [],
        }
        result = self._gql("CreateTweet", vars_, FEATURES)
        tweet = (
            result.get("data", {})
            .get("create_tweet", {})
            .get("tweet_results", {})
            .get("result", {})
        )
        return {"id": tweet.get("rest_id", ""), "text": text}

    def reply(self, tweet_id: str, text: str):
        self._ensure_authed()
        random_delay(0.5, 1.5)
        vars_ = {
            "tweet_text": text,
            "dark_request": False,
            "media": {"media_entities": [], "possibly_sensitive": False},
            "semantic_annotation_ids": [],
            "reply": {
                "in_reply_to_tweet_id": tweet_id,
                "exclude_reply_user_ids": [],
            },
        }
        result = self._gql("CreateTweet", vars_, FEATURES)
        tweet = (
            result.get("data", {})
            .get("create_tweet", {})
            .get("tweet_results", {})
            .get("result", {})
        )
        return {"id": tweet.get("rest_id", ""), "text": text,
                "reply_to": tweet_id}

    def like(self, tweet_id: str):
        self._ensure_authed()
        random_delay(0.3, 1.0)
        vars_ = {"tweet_id": tweet_id}
        self._gql("FavoriteTweet", vars_)
        return {"liked": tweet_id}

    def unlike(self, tweet_id: str):
        self._ensure_authed()
        random_delay(0.3, 1.0)
        vars_ = {"tweet_id": tweet_id}
        self._gql("UnfavoriteTweet", vars_)
        return {"unliked": tweet_id}

    def retweet(self, tweet_id: str):
        self._ensure_authed()
        random_delay(0.3, 1.0)
        vars_ = {"tweet_id": tweet_id, "dark_request": False}
        self._gql("CreateRetweet", vars_)
        return {"retweeted": tweet_id}

    def delete(self, tweet_id: str):
        self._ensure_authed()
        random_delay(0.3, 1.0)
        vars_ = {"tweet_id": tweet_id, "dark_request": False}
        self._gql("DeleteTweet", vars_)
        return {"deleted": tweet_id}

    def follow(self, username: str):
        """Follow a user by screen_name."""
        self._ensure_authed()
        random_delay(0.5, 1.5)
        user_info = self.user(username)
        uid = user_info["id"]
        random_delay()
        data = {
            "include_profile_interstitial_type": "1",
            "include_blocking": "1",
            "include_blocked_by": "1",
            "include_followed_by": "1",
            "include_want_retweets": "1",
            "include_mute_edge": "1",
            "include_can_dm": "1",
            "include_can_media_tag": "1",
            "include_ext_is_blue_verified": "1",
            "include_ext_verified_type": "1",
            "include_ext_profile_image_shape": "1",
            "skip_status": "1",
            "user_id": uid,
        }
        resp = self._v11_post(V11_FRIENDSHIPS_CREATE, data)
        return {"followed": username, "user_id": uid}

    def unfollow(self, username: str):
        """Unfollow a user by screen_name."""
        self._ensure_authed()
        random_delay(0.5, 1.5)
        user_info = self.user(username)
        uid = user_info["id"]
        random_delay()
        data = {
            "include_profile_interstitial_type": "1",
            "include_blocking": "1",
            "include_blocked_by": "1",
            "include_followed_by": "1",
            "include_want_retweets": "1",
            "include_mute_edge": "1",
            "include_can_dm": "1",
            "include_can_media_tag": "1",
            "include_ext_is_blue_verified": "1",
            "include_ext_verified_type": "1",
            "include_ext_profile_image_shape": "1",
            "skip_status": "1",
            "user_id": uid,
        }
        resp = self._v11_post(V11_FRIENDSHIPS_DESTROY, data)
        return {"unfollowed": username, "user_id": uid}

    # ----- reads (GET queries) ---------------------------------------------

    def read(self, tweet_id: str):
        self._ensure_authed()
        vars_ = {
            "tweetId": tweet_id,
            "includePromotedContent": False,
            "withVoice": False,
            "withSafetyModeUserFields": True,
            "withCommunity": False,
            "withQuickPromote": False,
            "withBirdwatchNotes": False,
            "with_rux_injections": False,
        }
        result = self._gql("TweetResultByRestId", vars_)
        return {"tweet_id": tweet_id, "raw": result}

    def user(self, username: str):
        self._ensure_authed()
        vars_ = {
            "screen_name": username,
            "withSafetyModeUserFields": True,
        }
        result = self._gql(
            "UserByScreenName", vars_,
            USER_FEATURES,
            {"fieldToggles": {"withAuxiliaryUserLabels": False}},
        )
        u = result.get("data", {}).get("user", {}).get("result", {})
        core = u.get("core", {})
        legacy = u.get("legacy", {})
        return {
            "id": u.get("rest_id", ""),
            "screen_name": core.get("screen_name", username),
            "name": core.get("name", ""),
            "description": legacy.get("description", ""),
            "followers_count": legacy.get("followers_count", 0),
            "following_count": legacy.get("friends_count", 0),
            "tweets_count": legacy.get("statuses_count", 0),
            "is_verified": bool(u.get("is_blue_verified", False)),
        }

    def search(self, query: str, count: int = 20):
        self._ensure_authed()
        vars_ = {
            "rawQuery": query,
            "count": count,
            "querySource": "typed_query",
            "product": "Top",
        }
        result = self._gql("SearchTimeline", vars_, FEATURES)
        return {"query": query, "raw": result}

    def timeline(self, count: int = 20):
        """Home timeline (Following feed)."""
        self._ensure_authed()
        vars_ = {
            "count": count,
            "includePromotedContent": True,
            "latestControlAvailable": True,
            "requestContext": "launch",
            "withCommunity": True,
            "seenTweetIds": [],
        }
        result = self._gql("HomeTimeline", vars_, FEATURES)
        return {"raw": result}

    def bookmarks(self, count: int = 20):
        self._ensure_authed()
        vars_ = {"count": count, "includePromotedContent": True}
        features = dict(FEATURES)
        features["graphql_timeline_v2_bookmark_timeline"] = True
        result = self._gql("Bookmarks", vars_, features)
        return {"raw": result}

    def tweets(self, username: str, keyword: Optional[str] = None,
               count: int = 20):
        self._ensure_authed()
        user_info = self.user(username)
        uid = user_info["id"]
        vars_ = {
            "userId": uid,
            "count": count,
            "includePromotedContent": True,
            "withQuickPromoteEligibilityTweetFields": True,
            "withVoice": True,
            "withV2Timeline": True,
        }
        result = self._gql("UserTweets", vars_, FEATURES)
        return {"username": username, "raw": result}

    def followers(self, username: str, count: int = 20):
        self._ensure_authed()
        user_info = self.user(username)
        uid = user_info["id"]
        vars_ = {
            "userId": uid,
            "count": count,
            "includePromotedContent": False,
        }
        result = self._gql("Followers", vars_, FEATURES)
        return {"username": username, "raw": result}

    def following(self, username: str, count: int = 20):
        self._ensure_authed()
        user_info = self.user(username)
        uid = user_info["id"]
        vars_ = {
            "userId": uid,
            "count": count,
            "includePromotedContent": False,
        }
        result = self._gql("Following", vars_, FEATURES)
        return {"username": username, "raw": result}

    # -- login stub ----------------------------------------------------------

    def login(self, username: str, password: str) -> dict:
        raise RuntimeError(
            "Username/password login is not available. "
            "Export cookies from a browser session and save to cookies.json, "
            "then run any command and I'll use them automatically."
        )
