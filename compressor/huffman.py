"""Canonical byte oriented Huffman coding.

This builds a standard Huffman tree over the 256 possible byte values,
assigns each value a variable length bit code (frequent bytes get shorter
codes), and packs the result into a small self describing blob:

    [num_symbols: 2 bytes][ (symbol: 1 byte, count: 4 bytes) * num_symbols ]
    [padding_bits: 1 byte][ huffman coded bit stream ]

The frequency table has to travel with the data because without it a
decoder cannot rebuild the same tree, and the tree is what defines what
each bit sequence means.
"""

from __future__ import annotations

import heapq
from collections import Counter
from typing import Dict, Optional

from .bitio import BitReader, BitWriter


class _Node:
    __slots__ = ("freq", "symbol", "left", "right")

    def __init__(self, freq, symbol=None, left=None, right=None):
        self.freq = freq
        self.symbol = symbol
        self.left = left
        self.right = right

    def is_leaf(self) -> bool:
        return self.left is None and self.right is None

    def __lt__(self, other: "_Node") -> bool:
        # Only used as a heapq tie breaker fallback; the (freq, order) tuple
        # pushed onto the heap already makes ties deterministic.
        return self.freq < other.freq


def build_tree(freqs: Dict[int, int]) -> Optional[_Node]:
    """Build a Huffman tree from a {byte_value: count} table."""
    if not freqs:
        return None

    if len(freqs) == 1:
        (symbol,) = freqs.keys()
        leaf = _Node(freqs[symbol], symbol=symbol)
        # A tree with a single symbol still needs one bit per occurrence,
        # so we wrap the lone leaf under a root that always walks "left".
        return _Node(leaf.freq, left=leaf, right=None)

    heap = []
    order = 0
    for symbol, count in freqs.items():
        heapq.heappush(heap, (count, order, _Node(count, symbol=symbol)))
        order += 1

    while len(heap) > 1:
        freq_a, _, node_a = heapq.heappop(heap)
        freq_b, _, node_b = heapq.heappop(heap)
        merged = _Node(freq_a + freq_b, left=node_a, right=node_b)
        heapq.heappush(heap, (merged.freq, order, merged))
        order += 1

    return heap[0][2]


def build_codes(root: Optional[_Node]) -> Dict[int, str]:
    """Walk the tree and return {byte_value: '0101...' bit string}."""
    codes: Dict[int, str] = {}
    if root is None:
        return codes

    if root.is_leaf():
        codes[root.symbol] = "0"
        return codes

    stack = [(root, "")]
    while stack:
        node, prefix = stack.pop()
        if node is None:
            continue
        if node.is_leaf():
            codes[node.symbol] = prefix or "0"
            continue
        stack.append((node.left, prefix + "0"))
        stack.append((node.right, prefix + "1"))
    return codes


def encode(data: bytes) -> bytes:
    """Encode arbitrary bytes into a self describing Huffman coded blob."""
    if not data:
        return (0).to_bytes(2, "big")

    freqs = Counter(data)
    root = build_tree(freqs)
    codes = build_codes(root)

    writer = BitWriter()
    for byte in data:
        writer.write_bits(codes[byte])
    bitstream, pad = writer.getvalue()

    header = bytearray()
    header += len(freqs).to_bytes(2, "big")
    for symbol, count in freqs.items():
        header.append(symbol)
        header += count.to_bytes(4, "big")
    header.append(pad)

    return bytes(header) + bitstream


def decode(blob: bytes) -> bytes:
    """Invert encode(): rebuild the tree from the header and decode the bits."""
    num_symbols = int.from_bytes(blob[0:2], "big")
    if num_symbols == 0:
        return b""

    pos = 2
    freqs: Dict[int, int] = {}
    for _ in range(num_symbols):
        symbol = blob[pos]
        count = int.from_bytes(blob[pos + 1 : pos + 5], "big")
        freqs[symbol] = count
        pos += 5

    pad = blob[pos]
    pos += 1
    bitstream = blob[pos:]

    root = build_tree(freqs)
    total_symbols = sum(freqs.values())
    out = bytearray()

    # Single symbol trees never got a real bit stream written per-symbol in
    # a way that needs tree walking; short circuit for speed and clarity.
    if root.right is None and root.left is not None:
        out.extend(bytes([root.left.symbol]) * total_symbols)
        return bytes(out)

    reader = BitReader(bitstream, pad)
    node = root
    while len(out) < total_symbols:
        bit = reader.read_bit()
        node = node.left if bit == 0 else node.right
        if node.is_leaf():
            out.append(node.symbol)
            node = root

    return bytes(out)
