#!/usr/bin/env python3
"""Compression benchmark over the files in sample_data/.

Run from the repo root:

    python benchmark.py

For each sample file this prints the original size, the compressed size,
the resulting ratio, and how long compression + decompression took, and
verifies every result round trips back to the original bytes exactly.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from compressor import pipeline

SAMPLE_DIR = Path(__file__).resolve().parent / "sample_data"


def bench_bytes(name: str, data: bytes) -> None:
    start = time.perf_counter()
    compressed = pipeline.compress(data)
    compress_time = time.perf_counter() - start

    start = time.perf_counter()
    restored = pipeline.decompress(compressed)
    decompress_time = time.perf_counter() - start

    ok = restored == data
    ratio = (len(compressed) / len(data)) if data else 0.0

    print(f"{name}")
    print(f"  original:    {len(data):>8,} bytes")
    print(f"  compressed:  {len(compressed):>8,} bytes")
    print(f"  ratio:       {ratio:.3f}  ({(1 - ratio) * 100:5.1f}% smaller)")
    print(f"  compress:    {compress_time * 1000:6.1f} ms")
    print(f"  decompress:  {decompress_time * 1000:6.1f} ms")
    print(f"  round trip:  {'OK' if ok else 'MISMATCH!'}")
    print()


def bench_file(path: Path) -> None:
    data = path.read_bytes()

    start = time.perf_counter()
    compressed = pipeline.compress(data)
    compress_time = time.perf_counter() - start

    start = time.perf_counter()
    restored = pipeline.decompress(compressed)
    decompress_time = time.perf_counter() - start

    ok = restored == data
    ratio = (len(compressed) / len(data)) if data else 0.0

    print(f"{path.name}")
    print(f"  original:    {len(data):>8,} bytes")
    print(f"  compressed:  {len(compressed):>8,} bytes")
    print(f"  ratio:       {ratio:.3f}  ({(1 - ratio) * 100:5.1f}% smaller)")
    print(f"  compress:    {compress_time * 1000:6.1f} ms")
    print(f"  decompress:  {decompress_time * 1000:6.1f} ms")
    print(f"  round trip:  {'OK' if ok else 'MISMATCH!'}")
    print()


def main() -> None:
    files = sorted(SAMPLE_DIR.glob("*"))
    if not files:
        print(f"No sample files found in {SAMPLE_DIR}")
        return
    for path in files:
        bench_file(path)

    # High entropy data is generated rather than committed to the repo (a
    # binary blob in source control brings little value), but it is the
    # most important comparison point: it shows the pipeline being honest
    # about data it cannot shrink instead of silently doing nothing useful.
    bench_bytes("random_data (generated, 4096 bytes)", os.urandom(4096))


if __name__ == "__main__":
    main()
