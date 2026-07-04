import os

from compressor import huffman


def round_trip(data: bytes) -> bytes:
    return huffman.decode(huffman.encode(data))


def test_empty_input():
    assert huffman.encode(b"") == (0).to_bytes(2, "big")
    assert round_trip(b"") == b""


def test_single_byte_repeated():
    data = b"a" * 500
    assert round_trip(data) == data


def test_single_occurrence_single_byte():
    data = b"x"
    assert round_trip(data) == data


def test_two_symbol_alphabet():
    data = b"ababababababab"
    assert round_trip(data) == data


def test_typical_text():
    data = b"the quick brown fox jumps over the lazy dog " * 20
    assert round_trip(data) == data


def test_all_256_byte_values_present():
    data = bytes(range(256)) * 4
    assert round_trip(data) == data


def test_random_binary_data():
    data = os.urandom(4096)
    assert round_trip(data) == data


def test_skewed_distribution_actually_shrinks():
    # Highly skewed frequency distribution should compress well below the
    # raw 8 bits/byte baseline once the header overhead is amortized.
    data = (b"a" * 900) + (b"b" * 90) + (b"c" * 10)
    encoded = huffman.encode(data)
    assert len(encoded) < len(data)
    assert huffman.decode(encoded) == data


def test_codes_are_prefix_free():
    freqs = {65: 5, 66: 2, 67: 1, 68: 1}
    root = huffman.build_tree(freqs)
    codes = huffman.build_codes(root)
    values = list(codes.values())
    for i, a in enumerate(values):
        for j, b in enumerate(values):
            if i == j:
                continue
            assert not b.startswith(a), f"{a!r} is a prefix of {b!r}"
