"""uny-x client — direct httpx against X internal API.

Uses cookies from a logged-in X browser session.
GraphQL for most ops, v1.1 for friendships (follow/unfollow).
No twikit / tweety dependency.
"""

import base64
import json
import os
import random
import re
import sys
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import httpx

from .x_client_transaction import ClientTransaction

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
    "Accept-Encoding": "gzip, deflate, br",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
    "Sec-Ch-Ua": (
        '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"'
    ),
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
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
V11_UPDATE_PROFILE = f"https://{DOMAIN}/i/api/1.1/account/update_profile.json"
V11_UPDATE_PROFILE_IMAGE = f"https://{DOMAIN}/i/api/1.1/account/update_profile_image.json"

# ---------------------------------------------------------------------------
# helpers — single source in .utils (no duplicates)
# ---------------------------------------------------------------------------

from .utils import (
    MIN_DELAY,
    MAX_DELAY,
    SHORT_MIN,
    SHORT_MAX,
    random_delay,
    extract_tweet_id,
    extract_username,
    RateLimitHandler,
)


def _flatten_params(params: dict) -> dict:
    """Convert dict/list values to JSON strings (httpx handles URL encoding)."""
    flat = {}
    for key, value in params.items():
        if isinstance(value, (list, dict)):
            value = json.dumps(value, separators=(",", ":"))
        flat[key] = value
    return flat


def _extract_timeline_entries(result: dict) -> list:
    """Extract tweet entry dicts from a timeline GraphQL response."""
    try:
        instructions = (
            result.get("data", {})
            .get("search_by_raw_query", {})
            .get("search_timeline", {})
            .get("timeline", {})
            .get("instructions", [])
        )
    except AttributeError:
        return []
    for instr in instructions:
        if instr.get("type") == "TimelineAddEntries":
            return instr.get("entries", [])
    return []


def _parse_tweet_entry(entry: dict) -> dict | None:
    """Parse a timeline entry into a readable tweet dict."""
    try:
        content = entry.get("content", {})
        item = content.get("itemContent", {})
        tweet_result = item.get("tweet_results", {}).get("result", {})
        if not tweet_result:
            return None
        # Handle visibility wrapper
        tweet = tweet_result.get("tweet", {}) if tweet_result.get("__typename") == "TweetWithVisibilityResults" else tweet_result
        legacy = tweet.get("legacy", {})
        user = (
            tweet.get("core", {})
            .get("user_results", {})
            .get("result", {})
        )
        user_legacy = user.get("legacy", {})

        return {
            "id": legacy.get("id_str", tweet.get("rest_id", "")),
            "text": legacy.get("full_text", ""),
            "user": {
                "id": user.get("rest_id", ""),
                "screen_name": user_legacy.get("screen_name", ""),
                "name": user_legacy.get("name", ""),
                "avatar": user_legacy.get("profile_image_url_https", ""),
            },
            "created_at": legacy.get("created_at", ""),
            "reply_count": legacy.get("reply_count", 0),
            "retweet_count": legacy.get("retweet_count", 0),
            "like_count": legacy.get("favorite_count", 0),
            "quote_count": legacy.get("quote_count", 0),
            "view_count": int((legacy.get("views") or {}).get("count") or 0),
            "is_quote": bool(legacy.get("is_quote_status")),
            "quote_url": legacy.get("quoted_status_permalink", {}).get("expanded", ""),
            "media": [
                m.get("media_url_https", "") for m in legacy.get("entities", {}).get("media", [])
                if m.get("type") == "photo"
            ],
        }
    except (KeyError, TypeError, AttributeError):
        return None


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
        self._http: Optional[httpx.Client] = None
        self._transaction = ClientTransaction()
        self._tx_inited = False
        self._tx_failed_at: float = 0.0
        self._rate = RateLimitHandler()

    def close(self):
        """Close the persistent httpx client."""
        if self._http is not None:
            try:
                self._http.close()
            except Exception:
                pass
            self._http = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False

    def _ensure_tx(self):
        """Initialize the X-Client-Transaction-Id provider if not already done.
        If init fails (webpack chunk changed, etc.), back off 10 min before
        retrying so we don't hammer X on every request."""
        import time as _time
        if self._tx_inited:
            return
        if _time.time() - self._tx_failed_at < 600:
            return
        try:
            ua = HEADERS_BASE.get("User-Agent", "")
            self._transaction.init(user_agent=ua, cookies=self._cookies)
            self._tx_inited = True
        except Exception:
            # Transaction init is non-critical — continue without it
            self._tx_failed_at = _time.time()

    def _get_tx_header(self, method: str, path: str) -> str | None:
        """Generate X-Client-Transaction-Id if initialized, else None."""
        if not self._tx_inited:
            return None
        try:
            return self._transaction.generate_transaction_id(method=method, path=path)
        except Exception:
            return None

    def _get_http(self) -> httpx.Client:
        """Return a persistent httpx client with cookie jar for ct0 rotation."""
        if self._http is None:
            self._http = httpx.Client(
                cookies=self._cookies,
                follow_redirects=True,
                timeout=30,
            )
        return self._http

    def _update_ct0_from_response(self, resp: httpx.Response):
        """Sync ct0 from the persistent client's cookie jar (X rotates it)."""
        try:
            jar_ct0 = self._get_http().cookies.get("ct0", "")
        except Exception:
            jar_ct0 = ""
        if jar_ct0 and jar_ct0 != self._ct0:
            self._ct0 = jar_ct0

    # -- auth ----------------------------------------------------------------

    def load_cookies(self, path: str | Path = "") -> bool:
        """Load cookies from a Firefox JSON-format file.

        Order: explicit path > UNYX_COOKIES env > ./cookies.json.
        """
        p = Path(path) if path else Path(os.environ.get("UNYX_COOKIES", "") or COOKIES_PATH)
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
        client = self._get_http()
        resp: httpx.Response = client.request(
            "POST", url,
            headers=h,
            data=data,
        )
        self._update_ct0_from_response(resp)
        if resp.status_code == 429:
            self._rate.wait()
            resp = client.request(
                "POST", url,
                headers=h,
                data=data,
            )
            self._update_ct0_from_response(resp)
        if resp.status_code != 200:
            raise RuntimeError(
                f"X v1.1 error {resp.status_code}: {resp.text[:300]}"
            )
        return resp.json()

    def _request(self, method: str, url: str, **kwargs) -> dict:
        """Raw HTTP request with cookie auth."""
        client = self._get_http()
        headers = self._headers()

        # add X-Client-Transaction-Id header (non-critical)
        self._ensure_tx()
        path = urlparse(url).path
        tid = self._get_tx_header(method=method, path=path)
        if tid:
            headers["X-Client-Transaction-Id"] = tid

        for attempt in (1, 2):
            resp: httpx.Response = client.request(
                method, url,
                headers=headers,
                **kwargs,
            )
            self._update_ct0_from_response(resp)
            if resp.status_code == 429 and attempt == 1:
                self._rate.wait()
                continue
            break
        if resp.status_code == 429:
            self._rate.reset()
        else:
            # success or other error — reset backoff counter on any non-429
            try:
                self._rate.reset()
            except Exception:
                pass
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

    def login_from_cookies(self, path: str | Path = "") -> bool:
        """Verify cookies by fetching the authenticated user's profile."""
        if not self.load_cookies(path):
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
            legacy = u.get("legacy", {})
            self._screen_name = (
                legacy.get("screen_name")
                or core.get("screen_name")
                or ""
            )
            if not self._user_id or not self._screen_name:
                raise RuntimeError(
                    f"cookie session valid but profile parse failed: {json.dumps(u)[:300]}"
                )
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
        rest_id = tweet.get("rest_id", "")
        if not rest_id:
            raise RuntimeError(
                "X silently dropped write (empty tweet_results). "
                f"likely stale query id or missing tx header: {json.dumps(result)[:500]}"
            )
        return {"id": rest_id, "text": text}

    def reply(self, tweet_id: str, text: str):
        self._ensure_authed()
        random_delay()
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
        rest_id = tweet.get("rest_id", "")
        if not rest_id:
            raise RuntimeError(
                "X silently dropped write (empty tweet_results). "
                f"likely stale query id or missing tx header: {json.dumps(result)[:500]}"
            )
        return {"id": rest_id, "text": text,
                "reply_to": tweet_id}

    def like(self, tweet_id: str):
        self._ensure_authed()
        random_delay()
        vars_ = {"tweet_id": tweet_id}
        self._gql("FavoriteTweet", vars_)
        return {"liked": tweet_id}

    def unlike(self, tweet_id: str):
        self._ensure_authed()
        random_delay()
        vars_ = {"tweet_id": tweet_id}
        self._gql("UnfavoriteTweet", vars_)
        return {"unliked": tweet_id}

    def retweet(self, tweet_id: str):
        self._ensure_authed()
        random_delay()
        vars_ = {"tweet_id": tweet_id, "dark_request": False}
        self._gql("CreateRetweet", vars_)
        return {"retweeted": tweet_id}

    def delete(self, tweet_id: str):
        self._ensure_authed()
        random_delay()
        vars_ = {"tweet_id": tweet_id, "dark_request": False}
        self._gql("DeleteTweet", vars_)
        return {"deleted": tweet_id}

    def follow(self, username: str):
        """Follow a user by screen_name."""
        self._ensure_authed()
        random_delay()
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
        random_delay()
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

    def set_name(self, name: str):
        """Change profile display name (not @handle). Max 50 chars."""
        name = name.strip()
        if not name or len(name) > 50:
            raise ValueError("Display name must be 1-50 characters.")
        self._ensure_authed()
        random_delay()
        resp = self._v11_post(V11_UPDATE_PROFILE, {"name": name})
        return {"name": resp.get("name", name)}

    def set_avatar(self, path: str | Path):
        """Change profile image from a local file.

        The file is read in-memory and uploaded straight to X —
        nothing is copied into the repo.
        """
        p = Path(path).expanduser()
        if not p.is_file():
            raise FileNotFoundError(f"No such image file: {p}")
        if p.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
            raise ValueError("Avatar must be a jpg, png, webp or gif file.")
        self._ensure_authed()
        random_delay()
        b64 = base64.b64encode(p.read_bytes()).decode()
        resp = self._v11_post(V11_UPDATE_PROFILE_IMAGE, {"image": b64})
        return {
            "avatar": resp.get("profile_image_url_https", ""),
            "screen_name": resp.get("screen_name", ""),
        }

    # ----- reads (GET queries) ---------------------------------------------

    def read(self, tweet_id: str):
        self._ensure_authed()
        random_delay(SHORT_MIN, SHORT_MAX)
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
        random_delay(SHORT_MIN, SHORT_MAX)
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
        screen_name = legacy.get("screen_name") or core.get("screen_name", username)
        name = legacy.get("name") or core.get("name", "")
        return {
            "id": u.get("rest_id", ""),
            "screen_name": screen_name,
            "name": name,
            "avatar": legacy.get("profile_image_url_https", ""),
            "description": legacy.get("description", ""),
            "followers_count": legacy.get("followers_count", 0),
            "following_count": legacy.get("friends_count", 0),
            "tweets_count": legacy.get("statuses_count", 0),
            "is_verified": bool(u.get("is_blue_verified", False)),
        }

    def search(self, query: str, count: int = 20):
        self._ensure_authed()
        random_delay(SHORT_MIN, SHORT_MAX)
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
        random_delay(SHORT_MIN, SHORT_MAX)
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
        random_delay(SHORT_MIN, SHORT_MAX)
        vars_ = {"count": count, "includePromotedContent": True}
        features = dict(FEATURES)
        features["graphql_timeline_v2_bookmark_timeline"] = True
        result = self._gql("Bookmarks", vars_, features)
        return {"raw": result}

    def tweets(self, username: str, keyword: Optional[str] = None,
               count: int = 20):
        self._ensure_authed()
        random_delay(SHORT_MIN, SHORT_MAX)
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
        random_delay(SHORT_MIN, SHORT_MAX)
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
        random_delay(SHORT_MIN, SHORT_MAX)
        user_info = self.user(username)
        uid = user_info["id"]
        vars_ = {
            "userId": uid,
            "count": count,
            "includePromotedContent": False,
        }
        result = self._gql("Following", vars_, FEATURES)
        return {"username": username, "raw": result}

    def mentions(self, count: int = 20):
        """Get tweets mentioning own handle via search."""
        self._ensure_authed()
        screen_name = self._screen_name
        if not screen_name:
            raise RuntimeError("could not resolve own handle for mentions")
        random_delay(SHORT_MIN, SHORT_MAX)
        vars_ = {
            "rawQuery": f"@{screen_name}",
            "count": count,
            "querySource": "typed_query",
            "product": "Latest",
        }
        result = self._gql("SearchTimeline", vars_, FEATURES)
        # Extract readable mention entries from timeline
        entries = _extract_timeline_entries(result)
        mentions = []
        for e in entries:
            tweet = _parse_tweet_entry(e)
            if tweet:
                mentions.append(tweet)
        return {"count": len(mentions), "mentions": mentions, "raw": result}

    def dms(self, count: int = 20):
        """Get DM inbox conversations."""
        self._ensure_authed()
        random_delay(SHORT_MIN, SHORT_MAX)
        url = "https://x.com/i/api/1.1/dm/inbox_initial_state.json"
        params = {
            "include_mention_in_reply_to": "true",
            "include_welcome_tweet": "false",
            "include_trusted_friends": "false",
            "include_conversation_info": "true",
            "include_pinned_conversation_ids": "false",
            "include_pinned_dm_info": "false",
            "include_dm_alt_text": "false",
            "dm_secret_conversations_enabled": "false",
            "include_tombstone_state": "false",
            "include_voice_dm": "false",
        }
        result = self._request("GET", url, params=params)
        inbox = result.get("inbox_initial_state", {})
        entries = inbox.get("entries", [])
        # Build per-conversation view
        conversations: dict[str, list] = {}
        for entry in entries:
            msg_data = entry.get("message", {}).get("message_data", {})
            conv_id = entry.get("message", {}).get("conversation_id", "")
            if not conv_id:
                continue
            sender_id = msg_data.get("sender_id", "")
            text = msg_data.get("text", "")
            created = msg_data.get("time", 0)
            conversations.setdefault(conv_id, []).append({
                "sender_id": sender_id,
                "text": text,
                "created_at": created,
                "media": bool(msg_data.get("attachment")),
            })
        # Sort conversations by most recent message
        sorted_convs = sorted(
            conversations.items(),
            key=lambda x: max(m["created_at"] for m in x[1]) if x[1] else 0,
            reverse=True,
        )
        result_list = []
        for conv_id, msgs in sorted_convs[:count]:
            msgs_sorted = sorted(msgs, key=lambda m: m["created_at"], reverse=True)
            result_list.append({
                "conversation_id": conv_id,
                "messages": msgs_sorted[:5],  # most recent 5 per conversation
            })
        return {"count": len(result_list), "conversations": result_list,
                "raw": result}

    def send_dm(self, username: str, text: str) -> dict:
        """Send a DM to a user by screen_name."""
        self._ensure_authed()
        random_delay(SHORT_MIN, SHORT_MAX)
        user_info = self.user(username)
        recipient_id = user_info["id"]
        if not recipient_id:
            return {"error": f"Could not resolve user: {username}"}
        # reuse existing conversation if we have one, else sender-recipient order
        conversation_id = f"{self._user_id}-{recipient_id}"
        try:
            inbox = self.dms(count=50)
            for conv in inbox.get("conversations", []):
                cid = conv.get("conversation_id", "")
                if self._user_id in cid and recipient_id in cid:
                    conversation_id = cid
                    break
        except Exception:
            pass
        url = "https://x.com/i/api/1.1/dm/new.json"
        data = {
            "text": text,
            "conversation_id": conversation_id,
            "recipient_id": recipient_id,
        }
        result = self._v11_post(url, data)
        # Extract dm id from response
        entries = result.get("entries", [])
        dm_id = entries[0].get("message", {}).get("id", "") if entries else ""
        return {
            "dm_id": dm_id,
            "text": text,
            "recipient": username,
        }

    def login(self, username: str, password: str) -> dict:
        raise RuntimeError(
            "Username/password login is not available. "
            "Export cookies from a browser session and save to cookies.json, "
            "then run any command and I'll use them automatically."
        )
