"""Bit level I/O helpers.

Huffman codes are variable length bit strings that do not fall on byte
boundaries, so we need a way to pack individual bits into bytes on the way
out and unpack them again on the way in. BitWriter and BitReader do exactly
that and nothing more.
"""

from __future__ import annotations

from typing import Tuple


class BitWriter:
    """Accumulates single bits and packs them into a bytes object."""

    def __init__(self) -> None:
        self._bytes = bytearray()
        self._current = 0
        self._nbits = 0

    def write_bit(self, bit: int) -> None:
        self._current = (self._current << 1) | (bit & 1)
        self._nbits += 1
        if self._nbits == 8:
            self._bytes.append(self._current)
            self._current = 0
            self._nbits = 0

    def write_bits(self, bitstring: str) -> None:
        for ch in bitstring:
            self.write_bit(1 if ch == "1" else 0)

    def write_uint(self, value: int, nbits: int) -> None:
        for i in range(nbits - 1, -1, -1):
            self.write_bit((value >> i) & 1)

    def getvalue(self) -> Tuple[bytes, int]:
        """Flush any partial byte and return (packed_bytes, padding_bits).

        padding_bits is how many zero bits were appended to the final byte
        so the reader knows where the real data stops.
        """
        pad = 0
        if self._nbits:
            pad = 8 - self._nbits
            self._bytes.append(self._current << pad)
            self._current = 0
            self._nbits = 0
        return bytes(self._bytes), pad


class BitReader:
    """Reads individual bits back out of a bytes object produced by BitWriter."""

    def __init__(self, data: bytes, pad: int = 0) -> None:
        self._data = data
        self._byte_pos = 0
        self._bit_pos = 0
        self._total_bits = len(data) * 8 - pad

    def read_bit(self) -> int:
        if self._byte_pos * 8 + self._bit_pos >= self._total_bits:
            raise EOFError("read_bit: no more bits in stream")
        byte = self._data[self._byte_pos]
        bit = (byte >> (7 - self._bit_pos)) & 1
        self._bit_pos += 1
        if self._bit_pos == 8:
            self._bit_pos = 0
            self._byte_pos += 1
        return bit

    def read_uint(self, nbits: int) -> int:
        value = 0
        for _ in range(nbits):
            value = (value << 1) | self.read_bit()
        return value

    def has_more(self) -> bool:
        return self._byte_pos * 8 + self._bit_pos < self._total_bits
