"""Ties LZ77 and Huffman coding together into one compressor, similar in
spirit to how DEFLATE layers an entropy coder on top of LZ77 matches.

Stream format:
    b"CMP1" + huffman.encode(lz77.serialize_tokens(lz77.compress(data)))

The magic bytes exist purely so decompress() can fail fast with a clear
error on a file that is not actually one of ours, rather than crashing
deep inside the Huffman decoder.
"""

from __future__ import annotations

from . import huffman, lz77

MAGIC = b"CMP1"
MAX_WINDOW_FOR_FORMAT = 0xFFFF  # distances are stored in 2 bytes, see lz77.serialize_tokens


def compress(data: bytes, window_size: int = 4096) -> bytes:
    if window_size > MAX_WINDOW_FOR_FORMAT:
        raise ValueError(
            f"window_size must be <= {MAX_WINDOW_FOR_FORMAT} for this container format"
        )
    tokens = lz77.compress(data, window_size=window_size)
    token_bytes = lz77.serialize_tokens(tokens)
    huff_blob = huffman.encode(token_bytes)
    return MAGIC + huff_blob


def decompress(blob: bytes) -> bytes:
    if blob[:4] != MAGIC:
        raise ValueError("not a valid .cmp stream (missing/incorrect magic bytes)")
    token_bytes = huffman.decode(blob[4:])
    tokens = lz77.deserialize_tokens(token_bytes)
    return lz77.decompress(tokens)
