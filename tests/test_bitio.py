from compressor.bitio import BitReader, BitWriter


def test_write_read_single_bits():
    writer = BitWriter()
    bits = [1, 0, 1, 1, 0, 0, 0, 1, 1, 1]
    for bit in bits:
        writer.write_bit(bit)
    data, pad = writer.getvalue()

    reader = BitReader(data, pad)
    read_back = [reader.read_bit() for _ in bits]
    assert read_back == bits


def test_write_bits_string():
    writer = BitWriter()
    writer.write_bits("1011000111")
    data, pad = writer.getvalue()
    assert pad == 6  # 10 bits used, 2 bytes allocated -> 6 padding bits

    reader = BitReader(data, pad)
    out = "".join(str(reader.read_bit()) for _ in range(10))
    assert out == "1011000111"


def test_write_uint_round_trip():
    writer = BitWriter()
    values = [(5, 3), (200, 8), (0, 4), (1, 1)]
    for value, nbits in values:
        writer.write_uint(value, nbits)
    data, pad = writer.getvalue()

    reader = BitReader(data, pad)
    for value, nbits in values:
        assert reader.read_uint(nbits) == value


def test_has_more_and_eof():
    writer = BitWriter()
    writer.write_bits("101")
    data, pad = writer.getvalue()
    reader = BitReader(data, pad)

    assert reader.has_more()
    reader.read_bit()
    reader.read_bit()
    reader.read_bit()
    assert not reader.has_more()

    try:
        reader.read_bit()
        assert False, "expected EOFError"
    except EOFError:
        pass


def test_empty_writer_produces_empty_bytes():
    writer = BitWriter()
    data, pad = writer.getvalue()
    assert data == b""
    assert pad == 0
