"""Command line interface for the compressor package.

Usage:
    python -m compressor compress <input> [-o output.cmp]
    python -m compressor decompress <input.cmp> [-o output]
    python -m compressor compress <input> --verify
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from . import pipeline


def _default_output(input_path: Path, mode: str) -> Path:
    if mode == "compress":
        return input_path.with_suffix(input_path.suffix + ".cmp")
    if input_path.suffix == ".cmp":
        return input_path.with_suffix("")
    return input_path.with_suffix(input_path.suffix + ".out")


def _cmd_compress(args: argparse.Namespace) -> int:
    input_path = Path(args.input)
    data = input_path.read_bytes()

    start = time.perf_counter()
    blob = pipeline.compress(data, window_size=args.window)
    elapsed = time.perf_counter() - start

    output_path = Path(args.output) if args.output else _default_output(input_path, "compress")
    output_path.write_bytes(blob)

    ratio = (len(blob) / len(data)) if data else 0.0
    print(f"{input_path} -> {output_path}")
    print(f"  original:   {len(data):,} bytes")
    print(f"  compressed: {len(blob):,} bytes")
    print(f"  ratio:      {ratio:.3f} ({(1 - ratio) * 100:.1f}% smaller)")
    print(f"  time:       {elapsed * 1000:.1f} ms")

    if args.verify:
        restored = pipeline.decompress(blob)
        ok = restored == data
        print(f"  round trip: {'OK' if ok else 'MISMATCH'}")
        if not ok:
            return 1
    return 0


def _cmd_decompress(args: argparse.Namespace) -> int:
    input_path = Path(args.input)
    blob = input_path.read_bytes()

    start = time.perf_counter()
    data = pipeline.decompress(blob)
    elapsed = time.perf_counter() - start

    output_path = Path(args.output) if args.output else _default_output(input_path, "decompress")
    output_path.write_bytes(data)

    print(f"{input_path} -> {output_path}")
    print(f"  restored: {len(data):,} bytes")
    print(f"  time:     {elapsed * 1000:.1f} ms")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="compressor", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_compress = sub.add_parser("compress", help="compress a file")
    p_compress.add_argument("input", help="path to the file to compress")
    p_compress.add_argument("-o", "--output", help="output path (default: <input>.cmp)")
    p_compress.add_argument(
        "--window", type=int, default=4096, help="LZ77 sliding window size (default: 4096)"
    )
    p_compress.add_argument(
        "--verify", action="store_true", help="decompress immediately and confirm a byte for byte match"
    )
    p_compress.set_defaults(func=_cmd_compress)

    p_decompress = sub.add_parser("decompress", help="decompress a .cmp file")
    p_decompress.add_argument("input", help="path to the .cmp file")
    p_decompress.add_argument("-o", "--output", help="output path (default: <input> without .cmp)")
    p_decompress.set_defaults(func=_cmd_decompress)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
