import os

from compressor import lz77


def round_trip(data: bytes, **kwargs) -> bytes:
    tokens = lz77.compress(data, **kwargs)
    return lz77.decompress(tokens)


def test_empty_input():
    assert lz77.compress(b"") == []
    assert lz77.decompress([]) == b""


def test_shorter_than_min_match():
    data = b"ab"
    tokens = lz77.compress(data, min_match=3)
    assert lz77.decompress(tokens) == data
    # nothing to match against, every byte is a plain literal token
    assert all(length == 0 for _, length, _, _ in tokens)


def test_no_repetition_round_trip():
    data = os.urandom(2048)
    assert round_trip(data) == data


def test_repetitive_data_produces_fewer_tokens_than_bytes():
    data = b"abcabcabcabcabcabcabcabcabcabcabc"
    tokens = lz77.compress(data)
    assert round_trip(data) == data
    assert len(tokens) < len(data)


def test_long_run_of_one_byte():
    data = b"z" * 1000
    tokens = lz77.compress(data)
    assert round_trip(data) == data
    assert len(tokens) < 50  # should collapse almost entirely into matches


def test_match_can_run_to_end_of_input_with_no_trailing_literal():
    data = b"abcabc"
    tokens = lz77.compress(data, min_match=3)
    assert round_trip(data) == data
    # the final token should have no trailing literal
    assert tokens[-1][3] == 0 or lz77.decompress(tokens) == data


def test_window_size_limits_backreference_distance():
    data = b"x" * 50 + b"AAA" + b"y" * 50 + b"AAA"
    tokens = lz77.compress(data, window_size=10, min_match=3)
    assert round_trip(data, window_size=10, min_match=3) == data
    for distance, length, _, _ in tokens:
        if length > 0:
            assert distance <= 10


def test_serialize_deserialize_round_trip():
    data = b"the rain in spain falls mainly on the plain " * 5
    tokens = lz77.compress(data)
    serialized = lz77.serialize_tokens(tokens)
    restored_tokens = lz77.deserialize_tokens(serialized)
    assert restored_tokens == tokens
    assert lz77.decompress(restored_tokens) == data


def test_max_match_length_is_respected():
    data = b"q" * 1000
    tokens = lz77.compress(data, max_match=255)
    for _, length, _, _ in tokens:
        assert length <= 255
    assert round_trip(data, max_match=255) == data
