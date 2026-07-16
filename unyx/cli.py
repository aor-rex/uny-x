"""uny-x CLI — argparse frontend for the X client."""

import argparse
import asyncio
import json
import sys
from typing import Optional

from .client import UnyxClient
from .utils import extract_tweet_id, extract_username


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        prog="uny-x",
        description="Unofficial X client — human-like interaction via twikit",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # --- auth ---
    p_login = sub.add_parser("login", help="Authenticate with username/email/password")
    p_login.add_argument("username")
    p_login.add_argument("email")
    p_login.add_argument("password")

    # --- actions ---
    p_post = sub.add_parser("post", help="Post a tweet")
    p_post.add_argument("text", nargs="+")

    p_reply = sub.add_parser("reply", help="Reply to a tweet")
    p_reply.add_argument("tweet_id", help="Tweet ID or URL")
    p_reply.add_argument("text", nargs="+")

    p_quote = sub.add_parser("quote", help="Quote a tweet")
    p_quote.add_argument("tweet_id", help="Tweet ID or URL")
    p_quote.add_argument("text", nargs="+")

    p_rt = sub.add_parser("retweet", help="Retweet")
    p_rt.add_argument("tweet_id", help="Tweet ID or URL")

    p_del = sub.add_parser("delete", help="Delete your tweet")
    p_del.add_argument("tweet_id", help="Tweet ID or URL")

    p_like = sub.add_parser("like", help="Like a tweet")
    p_like.add_argument("tweet_id", help="Tweet ID or URL")

    p_unlike = sub.add_parser("unlike", help="Unlike a tweet")
    p_unlike.add_argument("tweet_id", help="Tweet ID or URL")

    p_follow = sub.add_parser("follow", help="Follow a user")
    p_follow.add_argument("username")

    p_unfollow = sub.add_parser("unfollow", help="Unfollow a user")
    p_unfollow.add_argument("username")

    p_dm = sub.add_parser("dm", help="Send a direct message")
    p_dm.add_argument("username")
    p_dm.add_argument("text", nargs="+")

    # --- reads ---
    p_read = sub.add_parser("read", help="Get tweet details")
    p_read.add_argument("tweet_id", help="Tweet ID or URL")

    p_user = sub.add_parser("user", help="Get user profile + recent tweets")
    p_user.add_argument("username")

    p_timeline = sub.add_parser("timeline", help="Home timeline")
    p_timeline.add_argument("-n", type=int, default=20)

    p_search = sub.add_parser("search", help="Search tweets")
    p_search.add_argument("query", nargs="+")
    p_search.add_argument("-n", type=int, default=20)

    p_tweets = sub.add_parser("tweets", help="Get user's tweets (optional keyword)")
    p_tweets.add_argument("username")
    p_tweets.add_argument("keyword", nargs="?", default=None)

    p_mentions = sub.add_parser("mentions", help="Get mentions / replies to you")
    p_mentions.add_argument("-n", type=int, default=20)

    p_followers = sub.add_parser("followers", help="Get user's followers")
    p_followers.add_argument("username")
    p_followers.add_argument("-n", type=int, default=20)

    p_following = sub.add_parser("following", help="Get who a user follows")
    p_following.add_argument("username")
    p_following.add_argument("-n", type=int, default=20)

    p_bm = sub.add_parser("bookmarks", help="Get your bookmarks")
    p_bm.add_argument("-n", type=int, default=20)

    args = parser.parse_args(argv)
    result = _run(args)
    print(json.dumps(result, indent=2, default=str))


def _run(args) -> dict:
    """Dispatch subcommand and return JSON-serialisable dict."""
    cl = UnyxClient()

    async def _a() -> dict:
        # login
        if args.command == "login":
            return await cl.login(args.username, args.email, args.password)

        # actions
        if args.command == "post":
            text = " ".join(args.text)
            return await cl.post(text)

        if args.command == "reply":
            tid = extract_tweet_id(args.tweet_id)
            text = " ".join(args.text)
            return await cl.reply(tid, text)

        if args.command == "quote":
            tid = extract_tweet_id(args.tweet_id)
            text = " ".join(args.text)
            return await cl.quote(tid, text)

        if args.command == "retweet":
            tid = extract_tweet_id(args.tweet_id)
            return await cl.retweet(tid)

        if args.command == "delete":
            tid = extract_tweet_id(args.tweet_id)
            return await cl.delete(tid)

        if args.command == "like":
            tid = extract_tweet_id(args.tweet_id)
            return await cl.like(tid)

        if args.command == "unlike":
            tid = extract_tweet_id(args.tweet_id)
            return await cl.unlike(tid)

        if args.command == "follow":
            username = extract_username(args.username)
            return await cl.follow(username)

        if args.command == "unfollow":
            username = extract_username(args.username)
            return await cl.unfollow(username)

        if args.command == "dm":
            username = extract_username(args.username)
            text = " ".join(args.text)
            return await cl.dm(username, text)

        # reads
        if args.command == "read":
            tid = extract_tweet_id(args.tweet_id)
            return await cl.read(tid)

        if args.command == "user":
            username = extract_username(args.username)
            return await cl.user(username)

        if args.command == "timeline":
            return await cl.timeline(count=args.n)

        if args.command == "search":
            query = " ".join(args.query)
            return await cl.search(query, count=args.n)

        if args.command == "tweets":
            username = extract_username(args.username)
            return await cl.tweets(username, keyword=args.keyword)

        if args.command == "mentions":
            return await cl.mentions(count=args.n)

        if args.command == "followers":
            username = extract_username(args.username)
            return await cl.followers(username, count=args.n)

        if args.command == "following":
            username = extract_username(args.username)
            return await cl.following(username, count=args.n)

        if args.command == "bookmarks":
            return await cl.bookmarks(count=args.n)

        return {"error": f"Unknown command: {args.command}"}

    try:
        return asyncio.run(_a())
    except Exception as exc:
        return {"error": str(exc)}
