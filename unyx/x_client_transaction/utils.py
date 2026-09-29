import base64
import httpx
from typing import Union


def fetch_home_page(user_agent: str, cookie_dict: dict | None = None) -> str:
    """Fetch X.com homepage and return raw HTML text.

    Must use auth cookies so X returns the logged-in page with webpack chunk data.
    """
    resp = httpx.get(
        "https://x.com",
        headers={
            "User-Agent": user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
        },
        cookies=cookie_dict,
        follow_redirects=True,
        timeout=15,
    )
    return resp.text


def parse_home_page(html: str):
    """Parse X.com HTML into BeautifulSoup using html.parser."""
    from bs4 import BeautifulSoup
    return BeautifulSoup(html, "html.parser")


def float_to_hex(x: float) -> str:
    result = []
    quotient = int(x)
    fraction = x - quotient

    while quotient > 0:
        quotient = int(x / 16)
        remainder = int(x - (float(quotient) * 16))
        if remainder > 9:
            result.insert(0, chr(remainder + 55))
        else:
            result.insert(0, str(remainder))
        x = float(quotient)

    if fraction == 0:
        return ''.join(result)

    result.append('.')
    while fraction > 0:
        fraction *= 16
        integer = int(fraction)
        fraction -= float(integer)
        if integer > 9:
            result.append(chr(integer + 55))
        else:
            result.append(str(integer))
    return ''.join(result)


def is_odd(num: Union[int, float]) -> float:
    return -1.0 if num % 2 else 0.0


def base64_encode(data) -> str:
    if isinstance(data, str):
        data = data.encode()
    return base64.b64encode(data).decode()
