"""uny-x CLI — argparse frontend for the X client."""

import argparse
import json
import sys
from typing import Optional

from .client import UnyxClient, extract_tweet_id, extract_username


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        prog="uny-x",
        description="Unofficial X client — direct httpx against X internal API",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # --- auth ---
    p_login = sub.add_parser("login", help="Show cookie-auth instructions")

    # --- actions ---
    p_post = sub.add_parser("post", help="Post a tweet")
    p_post.add_argument("text", nargs="+")

    p_reply = sub.add_parser("reply", help="Reply to a tweet")
    p_reply.add_argument("tweet_id", help="Tweet ID or URL")
    p_reply.add_argument("text", nargs="+")

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

    p_dm = sub.add_parser("dm", help="Send a DM (NYI)")
    p_dm.add_argument("username")
    p_dm.add_argument("text", nargs="+")

    # --- reads ---
    p_read = sub.add_parser("read", help="Get tweet details")
    p_read.add_argument("tweet_id", help="Tweet ID or URL")

    p_user = sub.add_parser("user", help="Get user profile")
    p_user.add_argument("username")

    p_timeline = sub.add_parser("timeline", help="Home timeline")
    p_timeline.add_argument("-n", type=int, default=20)

    p_search = sub.add_parser("search", help="Search tweets")
    p_search.add_argument("query", nargs="+")
    p_search.add_argument("-n", type=int, default=20)

    p_tweets = sub.add_parser("tweets", help="Get user's tweets")
    p_tweets.add_argument("username")
    p_tweets.add_argument("keyword", nargs="?", default=None)

    p_bookmarks = sub.add_parser("bookmarks", help="Get your bookmarks")
    p_bookmarks.add_argument("-n", type=int, default=20)

    p_mentions = sub.add_parser("mentions", help="Get tweets mentioning you")
    p_mentions.add_argument("-n", type=int, default=20)

    p_dms = sub.add_parser("dms", help="Get DM inbox")
    p_dms.add_argument("-n", type=int, default=20)

    args = parser.parse_args(argv)
    result = _run(args)
    print(json.dumps(result, indent=2, default=str))


def _run(args) -> dict:
    cl = UnyxClient()

    try:
        if args.command == "login":
            return {
                "instructions": "Export cookies from a logged-in browser session "
                "as Firefox JSON, save to cookies.json in the project root, "
                "then run any command."
            }

        if args.command == "post":
            return cl.post(" ".join(args.text))

        if args.command == "reply":
            return cl.reply(extract_tweet_id(args.tweet_id), " ".join(args.text))

        if args.command == "retweet":
            return cl.retweet(extract_tweet_id(args.tweet_id))

        if args.command == "delete":
            return cl.delete(extract_tweet_id(args.tweet_id))

        if args.command == "like":
            return cl.like(extract_tweet_id(args.tweet_id))

        if args.command == "unlike":
            return cl.unlike(extract_tweet_id(args.tweet_id))

        if args.command == "dm":
            return cl.send_dm(extract_username(args.username), " ".join(args.text))

        if args.command == "follow":
            return cl.follow(extract_username(args.username))

        if args.command == "unfollow":
            return cl.unfollow(extract_username(args.username))

        if args.command == "read":
            return cl.read(extract_tweet_id(args.tweet_id))

        if args.command == "user":
            return cl.user(extract_username(args.username))

        if args.command == "timeline":
            return cl.timeline(count=args.n)

        if args.command == "search":
            return cl.search(" ".join(args.query), count=args.n)

        if args.command == "tweets":
            return cl.tweets(extract_username(args.username), keyword=args.keyword)

        if args.command == "bookmarks":
            return cl.bookmarks(count=args.n)

        if args.command == "mentions":
            return cl.mentions(count=args.n)

        if args.command == "dms":
            return cl.dms(count=args.n)

        return {"error": f"Unknown command: {args.command}"}

    except Exception as exc:
        return {"error": str(exc)}


if __name__ == "__main__":
    main(sys.argv[1:])
