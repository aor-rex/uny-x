import math
import random
import hashlib
import re
import time
from functools import reduce
from typing import Optional, List

import base64
import httpx

from .cubic_curve import Cubic
from .interpolate import interpolate
from .rotation import convert_rotation_to_matrix
from .utils import float_to_hex, is_odd, base64_encode, fetch_home_page, parse_home_page

ON_DEMAND_FILE_REGEX = re.compile(
    r""",(\d+):["']ondemand\.s["']""", re.VERBOSE | re.MULTILINE)
INDICES_REGEX = re.compile(
    r"""\(\w{1}\[(\d{1,2})\],\s*16\)""", re.VERBOSE | re.MULTILINE)


class ClientTransaction:
    ADDITIONAL_RANDOM_NUMBER = 3
    DEFAULT_KEYWORD = "obfiowerehiring"
    DEFAULT_ROW_INDEX = None
    DEFAULT_KEY_BYTES_INDICES = None

    def __init__(self):
        self.home_page_soup = None
        self.key: Optional[str] = None
        self.key_bytes: Optional[List[int]] = None
        self.animation_key: Optional[str] = None
        self._initialized = False
        self._user_agent: str = ""

    def init(self, user_agent: str = "", cookies: dict | None = None) -> None:
        """Initialize by fetching X.com homepage and extracting keys."""
        self._user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        html = fetch_home_page(self._user_agent, cookie_dict=cookies)
        self.home_page_soup = parse_home_page(html)

        self.DEFAULT_ROW_INDEX, self.DEFAULT_KEY_BYTES_INDICES = self._get_indices(html)
        self.key = self._get_key(self.home_page_soup)
        self.key_bytes = self._get_key_bytes(self.key)
        self.animation_key = self._get_animation_key(self.key_bytes, self.home_page_soup)
        self._initialized = True

    def _get_indices(self, raw_body: str) -> tuple:
        key_byte_indices = []

        idx_match = ON_DEMAND_FILE_REGEX.search(raw_body)
        if idx_match:
            chunk_idx = idx_match.group(1)
            hash_pattern = r',{}:"([0-9a-f]+)"'.format(chunk_idx)
            hash_regex = re.compile(hash_pattern)
            hash_match = hash_regex.search(raw_body)
            if hash_match:
                on_demand_url = (
                    "https://abs.twimg.com/responsive-web/client-web/"
                    f"ondemand.s.{hash_match.group(1)}a.js"
                )
                try:
                    resp = httpx.get(on_demand_url, headers={
                        "User-Agent": self._user_agent,
                    }, follow_redirects=True, timeout=15)
                    indices_match = INDICES_REGEX.finditer(resp.text)
                    for item in indices_match:
                        key_byte_indices.append(item.group(1))
                except Exception:
                    pass

        if not key_byte_indices:
            raise RuntimeError("Couldn't get KEY_BYTE indices")

        key_byte_indices = list(map(int, key_byte_indices))
        return key_byte_indices[0], key_byte_indices[1:]

    def _get_key(self, soup) -> str:
        element = soup.select_one("[name='twitter-site-verification']")
        if not element:
            raise RuntimeError("Couldn't find twitter-site-verification meta tag")
        content = element.get("content", "")
        if not content:
            raise RuntimeError("Empty twitter-site-verification content")
        return content

    def _get_key_bytes(self, key: str) -> List[int]:
        return list(base64.b64decode(key.encode("utf-8")))

    def _get_frames(self, soup):
        return soup.select("[id^='loading-x-anim']")

    def _get_2d_array(self, key_bytes, soup, frames=None):
        if frames is None:
            frames = self._get_frames(soup)
        children = list(list(frames[key_bytes[5] % 4].children)[0].children)
        svg_d = list(children)[1].get("d", "")[9:].split("C")
        result = []
        for item in svg_d:
            nums = [int(x) for x in re.sub(r"[^\d]+", " ", item).strip().split()]
            if nums:
                result.append(nums)
        return result

    @staticmethod
    def _solve(value, min_val, max_val, rounding: bool):
        result = value * (max_val - min_val) / 255 + min_val
        return math.floor(result) if rounding else round(result, 2)

    def _animate(self, frames, target_time):
        from_color = [float(item) for item in [*frames[:3], 1]]
        to_color = [float(item) for item in [*frames[3:6], 1]]
        to_rotation = [self._solve(float(frames[6]), 60.0, 360.0, True)]
        curves = [self._solve(float(item), is_odd(counter), 1.0, False)
                  for counter, item in enumerate(frames[7:])]
        cubic = Cubic(curves)
        val = cubic.get_value(target_time)
        color = interpolate(from_color, to_color, val)
        color = [max(0, v) for v in color]
        rotation = interpolate([0.0], to_rotation, val)
        matrix = convert_rotation_to_matrix(rotation[0])
        str_arr = [format(round(v), 'x') for v in color[:-1]]
        for value in matrix:
            rounded = round(value, 2)
            if rounded < 0:
                rounded = -rounded
            hex_value = float_to_hex(rounded)
            str_arr.append(f"0{hex_value}".lower() if hex_value.startswith(".") else hex_value if hex_value else '0')
        str_arr.extend(["0", "0"])
        return re.sub(r"[.-]", "", "".join(str_arr))

    def _get_animation_key(self, key_bytes, soup) -> str:
        total_time = 4096
        row_index = key_bytes[self.DEFAULT_ROW_INDEX] % 16
        frame_time = reduce(lambda n1, n2: n1 * n2,
                            [key_bytes[idx] % 16 for idx in self.DEFAULT_KEY_BYTES_INDICES])
        arr = self._get_2d_array(key_bytes, soup)
        frame_row = arr[row_index]
        target_time = float(frame_time) / total_time
        return self._animate(frame_row, target_time)

    def generate_transaction_id(self, method: str, path: str, time_now: Optional[int] = None) -> str:
        if not self._initialized:
            raise RuntimeError("ClientTransaction not initialized. Call init() first.")

        time_now = time_now or math.floor(
            (time.time() * 1000 - 1682924400 * 1000) / 1000)
        time_now_bytes = [(time_now >> (i * 8)) & 0xFF for i in range(4)]

        hash_input = f"{method}!{path}!{time_now}{self.DEFAULT_KEYWORD}{self.animation_key}"
        hash_val = hashlib.sha256(hash_input.encode()).digest()
        hash_bytes = list(hash_val)

        random_num = random.randint(0, 255)
        bytes_arr = [*self.key_bytes, *time_now_bytes, *hash_bytes[:16], self.ADDITIONAL_RANDOM_NUMBER]
        out = bytearray([random_num, *[item ^ random_num for item in bytes_arr]])
        return base64_encode(out).strip("=")
