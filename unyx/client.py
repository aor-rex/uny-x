"""uny-x client — twikit wrapper with cookie persistence & human-like behaviour."""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

from twikit import Client as TwikitClient
from twikit.errors import TooManyRequests, TwitterException

from .utils import RateLimitHandler, extract_tweet_id, random_delay

COOKIES_PATH = Path(__file__).resolve().parent.parent / "cookies.json"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


class UnyxClient:
    """Human-like X client wrapping twikit."""

    def __init__(self, language: str = "en-US"):
        self._tw = TwikitClient(language)
        self._rlh = RateLimitHandler()
        self._user_id: Optional[str] = None
        self._user_screen_name: Optional[str] = None

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    async def _run(self, coro):
        """Run an async coroutine, handling rate limits."""
        while True:
            try:
                return await coro
            except TooManyRequests:
                print("  [uny-x] rate limited — backing off...", file=sys.stderr)
                self._rlh.wait()
            except TwitterException as exc:
                raise RuntimeError(f"X API error: {exc}") from exc

    async def login(
        self,
        username: str,
        email: str,
        password: str,
    ) -> dict:
        """Authenticate and persist cookies."""
        print(f"  [uny-x] logging in as @{username}...", file=sys.stderr)

        # set a desktop-like UA
        self._tw.set_user_agent(USER_AGENT)
        await self._tw.login(
            auth_info_1=username,
            auth_info_2=email,
            password=password,
            cookies_file=str(COOKIES_PATH),
        )
        info = await self._run(self._tw.user())
        self._user_id = info.id
        self._user_screen_name = info.screen_name
        print(f"  [uny-x] logged in — id={self._user_id}", file=sys.stderr)
        return {"id": self._user_id, "screen_name": self._user_screen_name}

    async def login_from_cookies(self) -> bool:
        """Restore session from saved cookies.  Returns True on success."""
        if not COOKIES_PATH.exists():
            return False
        try:
            self._tw.set_user_agent(USER_AGENT)
            self._tw.load_cookies(str(COOKIES_PATH))
            info = await self._run(self._tw.user())
            self._user_id = info.id
            self._user_screen_name = info.screen_name
            print(f"  [uny-x] cookie session restored — @{info.screen_name}", file=sys.stderr)
            return True
        except Exception as exc:
            print(f"  [uny-x] cookie restore failed: {exc}", file=sys.stderr)
            return False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _ensure_authed(self):
        """Check session is alive; try cookies if not yet authed."""
        if self._user_id is not None:
            return
        ok = await self.login_from_cookies()
        if not ok:
            raise RuntimeError(
                "Not logged in. Run `uny-x login` first, or pass credentials."
            )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    async def post(self, text: str, media_paths: Optional[list[str]] = None):
        await self._ensure_authed()
        media_ids = []
        if media_paths:
            for p in media_paths:
                mid = await self._run(self._tw.upload_media(p))
                media_ids.append(mid)
        random_delay(0.1, 0.5)
        tweet = await self._run(
            self._tw.create_tweet(text, media_ids=media_ids or None)
        )
        return {"id": tweet.id, "text": tweet.text}

    async def reply(self, tweet_id: str, text: str, media_paths: Optional[list[str]] = None):
        await self._ensure_authed()
        media_ids = []
        if media_paths:
            for p in media_paths:
                mid = await self._run(self._tw.upload_media(p))
                media_ids.append(mid)
        random_delay(0.5, 1.5)
        tweet = await self._run(
            self._tw.create_tweet(text, reply_to=tweet_id, media_ids=media_ids or None)
        )
        return {"id": tweet.id, "text": tweet.text, "reply_to": tweet_id}

    async def quote(self, tweet_id: str, text: str):
        await self._ensure_authed()
        random_delay(0.5, 1.5)
        tweet = await self._run(self._tw.create_tweet(text, attachment_url=tweet_id))
        return {"id": tweet.id, "text": tweet.text, "quoted": tweet_id}

    async def retweet(self, tweet_id: str):
        await self._ensure_authed()
        random_delay(0.3, 1.0)
        result = await self._run(self._tw.retweet(tweet_id))
        return {"retweeted": tweet_id, "result": str(result)[:200]}

    async def delete(self, tweet_id: str):
        await self._ensure_authed()
        random_delay(0.3, 1.0)
        await self._run(self._tw.delete_tweet(tweet_id))
        return {"deleted": tweet_id}

    async def like(self, tweet_id: str):
        await self._ensure_authed()
        random_delay(0.3, 1.0)
        await self._run(self._tw.favorite_tweet(tweet_id))
        return {"liked": tweet_id}

    async def unlike(self, tweet_id: str):
        await self._ensure_authed()
        random_delay(0.3, 1.0)
        await self._run(self._tw.unfavorite_tweet(tweet_id))
        return {"unliked": tweet_id}

    async def follow(self, username: str):
        await self._ensure_authed()
        random_delay(0.5, 2.0)
        user = await self._run(self._tw.get_user_by_screen_name(username))
        await self._run(self._tw.follow_user(user.id))
        return {"followed": username, "user_id": user.id}

    async def unfollow(self, username: str):
        await self._ensure_authed()
        random_delay(0.5, 2.0)
        user = await self._run(self._tw.get_user_by_screen_name(username))
        await self._run(self._tw.unfollow_user(user.id))
        return {"unfollowed": username, "user_id": user.id}

    async def dm(self, username: str, text: str):
        await self._ensure_authed()
        random_delay(0.5, 1.5)
        user = await self._run(self._tw.get_user_by_screen_name(username))
        msg = await self._run(self._tw.send_dm(user.id, text))
        return {"to": username, "text": text, "dm_id": msg.id if hasattr(msg, "id") else None}

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    async def read(self, tweet_id: str):
        await self._ensure_authed()
        tweet = await self._run(self._tw.get_tweet_by_id(tweet_id))
        return _tweet_dict(tweet)

    async def user(self, username: str) -> dict:
        await self._ensure_authed()
        user = await self._run(self._tw.get_user_by_screen_name(username))
        tweets = await self._run(self._tw.get_user_tweets(user.id, count=5))
        return {
            "id": user.id,
            "screen_name": user.screen_name,
            "name": user.name or "",
            "description": user.description or "",
            "followers_count": getattr(user, "followers_count", 0),
            "following_count": getattr(user, "following_count", 0),
            "tweets_count": getattr(user, "statuses_count", 0),
            "is_verified": getattr(user, "verified", False) or getattr(user, "is_blue_verified", False),
            "recent_tweets": [_tweet_dict(t) for t in (tweets or [])[:5]],
        }

    async def timeline(self, count: int = 20):
        await self._ensure_authed()
        items = await self._run(self._tw.get_timeline(count=count))
        return {"tweets": [_tweet_dict(t) for t in (items or [])]}

    async def search(self, query: str, count: int = 20):
        await self._ensure_authed()
        results = await self._run(self._tw.search_tweet(query, count=count))
        return {"query": query, "tweets": [_tweet_dict(t) for t in (results or [])]}

    async def tweets(self, username: str, keyword: Optional[str] = None, count: int = 20):
        await self._ensure_authed()
        user = await self._run(self._tw.get_user_by_screen_name(username))
        tweets = await self._run(self._tw.get_user_tweets(user.id, count=count))
        items = [_tweet_dict(t) for t in (tweets or [])]
        if keyword:
            items = [t for t in items if keyword.lower() in t["text"].lower()]
        return {"username": username, "tweets": items}

    async def mentions(self, count: int = 20):
        await self._ensure_authed()
        items = await self._run(self._tw.get_tweet_notifications(count=count))
        return {"mentions": [_tweet_dict(t) for t in (items or [])]}

    async def followers(self, username: str, count: int = 20):
        await self._ensure_authed()
        user = await self._run(self._tw.get_user_by_screen_name(username))
        items = await self._run(self._tw.get_user_followers(user.id, count=count))
        return {"username": username, "followers": [_user_brief(u) for u in (items or [])]}

    async def following(self, username: str, count: int = 20):
        await self._ensure_authed()
        user = await self._run(self._tw.get_user_by_screen_name(username))
        items = await self._run(self._tw.get_user_following(user.id, count=count))
        return {"username": username, "following": [_user_brief(u) for u in (items or [])]}

    async def bookmarks(self, count: int = 20):
        await self._ensure_authed()
        items = await self._run(self._tw.get_bookmarks(count=count))
        return {"bookmarks": [_tweet_dict(t) for t in (items or [])]}


# ------------------------------------------------------------------
# Serialisation helpers
# ------------------------------------------------------------------


def _tweet_dict(t):
    if t is None:
        return None
    return {
        "id": t.id,
        "text": t.text or "",
        "created_at": str(getattr(t, "created_at", "")),
        "user": getattr(t, "user", None).screen_name if hasattr(t, "user") and t.user else None,
        "user_name": getattr(t, "user", None).name if hasattr(t, "user") and t.user else None,
        "retweet_count": getattr(t, "retweet_count", 0) or getattr(t, "favorite_count", 0),
        "like_count": getattr(t, "favorite_count", 0),
        "reply_count": getattr(t, "reply_count", 0),
        "is_reply": bool(getattr(t, "in_reply_to", None)),
        "in_reply_to": getattr(t, "in_reply_to", None),
        "url": f"https://x.com/i/status/{t.id}",
    }


def _user_brief(u):
    if u is None:
        return None
    return {
        "id": u.id,
        "screen_name": u.screen_name,
        "name": u.name or "",
    }
