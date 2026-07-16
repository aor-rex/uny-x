"""uny-x client — direct httpx against X internal GraphQL API.

Uses cookies from a logged-in X browser session.  No twikit / tweety.
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
# GraphQL query IDs  (extracted from main.bcd2a32a.js)
# ---------------------------------------------------------------------------

QUERIES = {
    "CreateTweet":            ("hIL9XdleMYEtVXOZVbr8Bg", "CreateTweet"),
    "DeleteTweet":            ("nxpZCY2K-I6QoFHAHeojFQ", "DeleteTweet"),
    "FavoriteTweet":          ("lI07N6Otwv1PhnEgXILM7A", "FavoriteTweet"),
    "UnfavoriteTweet":        ("ZYKSe-w7KEslx3JhSIk5LA", "UnfavoriteTweet"),
    "CreateRetweet":          ("mbRO74GrOvSfRcJnlMapnQ", "CreateRetweet"),
    "DeleteRetweet":          ("ZyZigVsNiFO6v1dEks1eWg", "DeleteRetweet"),
    "UserByScreenName":       ("2qvSHpkWTMS9i0zJAwDNiA", "UserByScreenName"),
    "UserByRestId":           ("DaeC_2LfMgwCujE03HSZtw", "UserByRestId"),
    "TweetDetail":            ("rZA6K31W4E90vZKBmxXV3g", "TweetDetail"),
    "TweetResultByRestId":    ("4hhGRbehkcUVTKf8n0f0xw", "TweetResultByRestId"),
    "SearchTimeline":         ("hz_94eVAtrtQo_vO3my7Rw", "SearchTimeline"),
    "CreateBookmark":         ("aoDbu3RHznuiSkQ9aNM67Q", "CreateBookmark"),
    "DeleteBookmark":         ("Wlmlj2-xzyS1GN3a6cj-mQ", "DeleteBookmark"),
    "UserTweets":             ("6r5OLCC_wFH4CpRyXKuAmQ", "UserTweets"),
    "UserTweetsAndReplies":   ("klja8a2iJX_3to5RdfVlgw", "UserTweetsAndReplies"),
    "Followers":              ("18SNsfvwgu2CYIweeUVHAw", "Followers"),
    "Following":              ("PEIBUtChvR2i_NZCxbK3fA", "Following"),
    "Likes":                  ("4X8QeWbeJ0jwGHaXSxExRw", "Likes"),
    "Viewer":                 ("u4ni7JqpqdAQxWQfkLsdUQ", "Viewer"),
    "ConnectTabTimeline":     ("5fKmzgJzgNxisAdyoJTPdg", "ConnectTabTimeline"),
    "BookmarkSearchTimeline": ("SpDsqmz6FfYESd1e7TPcAw", "BookmarkSearchTimeline"),
}

FEATURES = {
    "creator_subscriptions_tweet_preview_api_enabled": True,
    "communities_web_enable_tweet_actions": True,
    "c9s_tweet_anatomy_moderator_badge_enabled": True,
    "articles_preview_enabled": True,
    "tweetypie_unmention_optimization_enabled": True,
    "responsive_web_edit_tweet_api_enabled": True,
    "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
    "view_counts_everywhere_api_enabled": True,
    "longform_notetweets_consumption_enabled": True,
    "tweet_awards_web_tipping_enabled": False,
    "freedom_of_speech_not_reach_fetch_enabled": False,
    "standardized_nudges_misinfo": True,
    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": False,
    "responsive_web_graphql_exclude_directive_enabled": True,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    "responsive_web_graphql_timeline_navigation_enabled": True,
    "responsive_web_enhance_cards_enabled": False,
}

FIELD_TOGGLES = [
    "withArticleRichContentState",
    "withArticlePlainText",
    "withArticleSummaryText",
    "withArticleVoiceOver",
    "withGrokAnalyze",
    "withDisallowedReplyControls",
    "withPayments",
    "withAuxiliaryUserLabels",
]

HEADERS_BASE = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Authorization": (
        "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs"
        "%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
    ),
    "Content-Type": "application/json",
    "Origin": "https://x.com",
    "Referer": "https://x.com/",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
}

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

MIN_DELAY = 0.2
MAX_DELAY = 3.0


def random_delay(min_s: float = MIN_DELAY, max_s: float = MAX_DELAY) -> None:
    time.sleep(random.uniform(min_s, max_s))


_TWEET_URL_RE = re.compile(
    r'(?:https?://)?(?:www\.)?(?:x\.com|twitter\.com)/\w+/status/(\d+)'
)


def extract_tweet_id(value: str) -> str:
    m = _TWEET_URL_RE.search(value)
    if m:
        return m.group(1)
    if value.isdigit():
        return value
    raise ValueError(f"Can't extract tweet ID from: {value}")


_USERNAME_RE = re.compile(r'^@?(\w{1,15})$')


def extract_username(value: str) -> str:
    m = _USERNAME_RE.match(value)
    if m:
        return m.group(1)
    raise ValueError(f"Invalid username: {value}")


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

COOKIES_PATH = Path(__file__).resolve().parent.parent / "cookies.json"


class UnyxClient:
    """Direct X internal API client."""

    def __init__(self):
        self._cookies: dict = {}
        self._ct0: str = ""
        self._user_id: Optional[str] = None
        self._screen_name: Optional[str] = None

    # -- auth ----------------------------------------------------------------

    def load_cookies(self, path: str = str(COOKIES_PATH)) -> bool:
        """Load cookies from a Firefox JSON-format file."""
        p = Path(path)
        if not p.exists():
            return False
        with open(p) as f:
            raw = json.load(f)
        self._cookies = {}
        for c in raw:
            self._cookies[c["name"]] = c["value"]
        self._ct0 = self._cookies.get("ct0", "")
        return True

    def _headers(self) -> dict:
        h = dict(HEADERS_BASE)
        if self._ct0:
            h["X-CSRF-Token"] = self._ct0
        return h

    def _gql(self, name: str, variables: dict) -> dict:
        """Execute a GraphQL operation via POST."""
        qid, op_name = QUERIES[name]
        url = f"https://x.com/i/api/graphql/{qid}/{op_name}"
        payload = {
            "variables": variables,
            "features": FEATURES,
            "fieldToggles": FIELD_TOGGLES,
        }
        return self._request("POST", url, json=payload)

    def _request(self, method: str, url: str, **kwargs) -> dict:
        """Make an HTTP request with cookie auth."""
        with httpx.Client() as client:
            resp = client.request(
                method,
                url,
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
        if "errors" in data:
            # Non-fatal errors may still have data
            pass
        return data

    # -- public API ----------------------------------------------------------

    def login_from_cookies(self) -> bool:
        """Verify cookies are valid by fetching current user."""
        if not self.load_cookies():
            return False
        try:
            result = self._gql("Viewer", {})
            viewer = result.get("data", {}).get("viewer", {})
            user_results = viewer.get("user_results", {}).get("result", {})
            self._user_id = user_results.get("rest_id")
            core = user_results.get("core", {})
            self._screen_name = core.get("screen_name")
            print(f"  [uny-x] session restored — @{self._screen_name}", file=sys.stderr)
            return True
        except Exception as exc:
            print(f"  [uny-x] cookie restore failed: {exc}", file=sys.stderr)
            return False

    def _ensure_authed(self):
        if self._user_id is not None:
            return
        if not self.login_from_cookies():
            raise RuntimeError("Not logged in. Run `uny-x login` first, or pass credentials.")

    def post(self, text: str):
        self._ensure_authed()
        random_delay()
        # For CreateTweet variables, these are the required fields
        vars_ = {
            "tweet_text": text,
            "media": [],
            "semantic_annotation_ids": [],
            "dark_request": False,
            "disallowed_reply_options": None,
        }
        result = self._gql("CreateTweet", vars_)
        tweet = result.get("data", {}).get("create_tweet", {}).get("tweet_results", {}).get("result", {})
        return {"id": tweet.get("rest_id", ""), "text": text}

    def reply(self, tweet_id: str, text: str):
        self._ensure_authed()
        random_delay(0.5, 1.5)
        vars_ = {
            "tweet_text": text,
            "reply": {"in_reply_to_tweet_id": tweet_id, "exclude_reply_user_ids": []},
            "media": [],
            "semantic_annotation_ids": [],
            "dark_request": False,
            "disallowed_reply_options": None,
        }
        result = self._gql("CreateTweet", vars_)
        tweet = result.get("data", {}).get("create_tweet", {}).get("tweet_results", {}).get("result", {})
        return {"id": tweet.get("rest_id", ""), "text": text, "reply_to": tweet_id}

    def like(self, tweet_id: str):
        self._ensure_authed()
        random_delay(0.3, 1.0)
        self._gql("FavoriteTweet", {"tweet_id": tweet_id})
        return {"liked": tweet_id}

    def unlike(self, tweet_id: str):
        self._ensure_authed()
        random_delay(0.3, 1.0)
        self._gql("UnfavoriteTweet", {"tweet_id": tweet_id})
        return {"unliked": tweet_id}

    def retweet(self, tweet_id: str):
        self._ensure_authed()
        random_delay(0.3, 1.0)
        self._gql("CreateRetweet", {"tweet_id": tweet_id})
        return {"retweeted": tweet_id}

    def delete(self, tweet_id: str):
        self._ensure_authed()
        random_delay(0.3, 1.0)
        self._gql("DeleteTweet", {"tweet_id": tweet_id})
        return {"deleted": tweet_id}

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
        vars_ = {"screen_name": username, "withSafetyModeUserFields": True}
        result = self._gql("UserByScreenName", vars_)
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
        result = self._gql("SearchTimeline", vars_)
        return {"query": query, "raw": result}

    def timeline(self, count: int = 20):
        self._ensure_authed()
        result = self._gql("ConnectTabTimeline", {})
        return {"raw": result}

    def bookmarks(self, count: int = 20):
        self._ensure_authed()
        vars_ = {"count": count, "includePromotedContent": False}
        result = self._gql("BookmarkSearchTimeline", vars_)
        return {"raw": result}

    def tweets(self, username: str, keyword: Optional[str] = None, count: int = 20):
        self._ensure_authed()
        # First get user id
        user_info = self.user(username)
        uid = user_info["id"]
        vars_ = {
            "userId": uid,
            "count": count,
            "includePromotedContent": False,
            "withQuickPromote": False,
            "withVoice": True,
            "withV2Timeline": True,
        }
        result = self._gql("UserTweets", vars_)
        return {"username": username, "raw": result}

    def followers(self, username: str, count: int = 20):
        self._ensure_authed()
        user_info = self.user(username)
        uid = user_info["id"]
        vars_ = {"userId": uid, "count": count, "includePromotedContent": False}
        result = self._gql("Followers", vars_)
        return {"username": username, "raw": result}

    def following(self, username: str, count: int = 20):
        self._ensure_authed()
        user_info = self.user(username)
        uid = user_info["id"]
        vars_ = {"userId": uid, "count": count, "includePromotedContent": False}
        result = self._gql("Following", vars_)
        return {"username": username, "raw": result}

    def login(self, username: str, password: str) -> dict:
        """Not supported — use cookies instead."""
        raise RuntimeError(
            "Username/password login is not available. "
            "Export cookies from a browser session and save to cookies.json, "
            "then run any command and I'll use them automatically."
        )
