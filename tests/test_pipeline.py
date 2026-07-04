import os
from pathlib import Path

import pytest

from compressor import pipeline

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_data"


def round_trip(data: bytes) -> bytes:
    return pipeline.decompress(pipeline.compress(data))


def test_empty_input():
    assert round_trip(b"") == b""


def test_small_text():
    data = b"hello, hello, hello, world!"
    assert round_trip(data) == data


def test_binary_random_data_still_round_trips():
    data = os.urandom(8192)
    assert round_trip(data) == data


def test_bad_magic_raises():
    with pytest.raises(ValueError):
        pipeline.decompress(b"NOPE" + b"\x00\x00")


def test_highly_repetitive_text_compresses_well():
    data = (b"abcdefgh" * 2000)
    compressed = pipeline.compress(data)
    assert len(compressed) < len(data) // 4
    assert pipeline.decompress(compressed) == data


@pytest.mark.parametrize(
    "filename",
    ["english_prose.txt", "repetitive.txt"],
)
def test_sample_data_round_trips(filename):
    path = SAMPLE_DIR / filename
    data = path.read_bytes()
    compressed = pipeline.compress(data)
    assert pipeline.decompress(compressed) == data


def test_english_prose_compresses_smaller_than_original():
    data = (SAMPLE_DIR / "english_prose.txt").read_bytes()
    compressed = pipeline.compress(data)
    assert len(compressed) < len(data)


def test_repetitive_sample_compresses_dramatically():
    data = (SAMPLE_DIR / "repetitive.txt").read_bytes()
    compressed = pipeline.compress(data)
    assert len(compressed) < len(data) * 0.2


def test_custom_window_size():
    data = b"mississippi river " * 50
    compressed = pipeline.compress(data, window_size=64)
    assert pipeline.decompress(compressed) == data


def test_window_size_too_large_rejected():
    with pytest.raises(ValueError):
        pipeline.compress(b"hi", window_size=100000)
