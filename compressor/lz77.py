"""LZ77 sliding window compression.

Every position in the input is described as either:
  * a back reference (distance, length) into the already seen window plus
    the literal byte that follows it, or
  * a bare literal byte, when no useful match was found (distance = 0,
    length = 0).

Encoded as a tuple: (distance, length, literal, has_literal)
  - has_literal is 0 only for the rare case where a match runs all the way
    to the end of the input and there is no trailing literal byte.

A naive implementation scans the whole window for every position, which is
O(n * window_size) and too slow for anything but tiny inputs. This module
instead keeps a hash table that maps every 3 byte prefix seen so far to the
list of positions it occurred at, so matches are found in roughly O(n) time
on typical data.
"""

from __future__ import annotations

from typing import List, Tuple

Token = Tuple[int, int, int, int]  # (distance, length, literal, has_literal)

_DEFAULT_WINDOW = 4096
_MIN_MATCH = 3
_MAX_MATCH = 255
_MAX_CHAIN = 32  # how many candidate positions we check per hash bucket


def compress(
    data: bytes,
    window_size: int = _DEFAULT_WINDOW,
    min_match: int = _MIN_MATCH,
    max_match: int = _MAX_MATCH,
) -> List[Token]:
    n = len(data)
    tokens: List[Token] = []
    table: dict = {}

    def remember(pos: int) -> None:
        if pos + min_match > n:
            return
        key = data[pos : pos + min_match]
        bucket = table.setdefault(key, [])
        bucket.append(pos)
        if len(bucket) > _MAX_CHAIN:
            del bucket[0]

    i = 0
    while i < n:
        best_len = 0
        best_dist = 0

        if i + min_match <= n:
            key = data[i : i + min_match]
            candidates = table.get(key)
            if candidates:
                max_len = min(max_match, n - i)
                for pos in reversed(candidates):
                    if i - pos > window_size:
                        continue
                    length = 0
                    while length < max_len and data[pos + length] == data[i + length]:
                        length += 1
                    if length > best_len:
                        best_len = length
                        best_dist = i - pos
                        if best_len == max_len:
                            break

        if best_len >= min_match:
            match_end = i + best_len
            has_literal = 1 if match_end < n else 0
            literal = data[match_end] if has_literal else 0
            tokens.append((best_dist, best_len, literal, has_literal))

            stop = match_end + (1 if has_literal else 0)
            for pos in range(i, stop):
                remember(pos)
            i = stop
        else:
            literal = data[i]
            tokens.append((0, 0, literal, 1))
            remember(i)
            i += 1

    return tokens


def decompress(tokens: List[Token]) -> bytes:
    out = bytearray()
    for distance, length, literal, has_literal in tokens:
        if length > 0:
            start = len(out) - distance
            for k in range(length):
                out.append(out[start + k])
        if has_literal:
            out.append(literal)
    return bytes(out)


def serialize_tokens(tokens: List[Token]) -> bytes:
    """Pack tokens into a flat byte stream: 2 bytes distance, 1 byte length,
    1 byte has_literal flag, 1 byte literal (5 bytes per token).

    This is deliberately simple rather than bit packed, because the whole
    point is that the following Huffman stage squeezes the redundancy back
    out of this stream (lots of repeated small values compress well).
    """
    buf = bytearray()
    for distance, length, literal, has_literal in tokens:
        buf += distance.to_bytes(2, "big")
        buf.append(length)
        buf.append(1 if has_literal else 0)
        buf.append(literal)
    return bytes(buf)


def deserialize_tokens(data: bytes) -> List[Token]:
    tokens = []
    for i in range(0, len(data), 5):
        distance = int.from_bytes(data[i : i + 2], "big")
        length = data[i + 2]
        has_literal = data[i + 3]
        literal = data[i + 4]
        tokens.append((distance, length, literal, has_literal))
    return tokens
