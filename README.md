# huffman-lz77-compressor

A file compressor built entirely from scratch in pure Python: no `zlib`, no
`gzip`, no third party libraries. It combines two classic ideas the same way
`DEFLATE` (the algorithm behind gzip and zip) does, just without the decades
of bit-packing optimization:

1. **LZ77** finds repeated substrings and replaces them with short back
   references into a sliding window of recently seen bytes.
2. **Huffman coding** then re-encodes the resulting token stream so that
   common byte values use fewer bits than rare ones.

Neither stage alone gets particularly close to a file's true entropy, but
stacking them (first remove repetition, then squeeze the leftover
distribution) is a real, well tested strategy, and building it by hand is a
good way to actually understand why gzip works instead of just knowing that
it does.

## Why this is useful

Beyond being a working compressor, this is a small, readable reference
implementation of two algorithms that are usually hidden behind a C
extension. Every piece is short enough to read in one sitting:

| File | What it does |
|---|---|
| `compressor/bitio.py` | Packs/unpacks individual bits into bytes (Huffman codes aren't byte aligned) |
| `compressor/huffman.py` | Builds a Huffman tree from byte frequencies, encodes/decodes with a self describing header |
| `compressor/lz77.py` | Hash table accelerated LZ77 sliding window match finder |
| `compressor/pipeline.py` | Wires LZ77 output into the Huffman stage and defines the on disk container format |
| `compressor/cli.py` | `compress` / `decompress` command line commands |

## How to run it

Requires nothing but Python 3.8+, no `pip install` needed.

```bash
# compress a file (writes input.cmp) and verify the round trip immediately
python -m compressor compress path/to/file.txt --verify

# decompress it back
python -m compressor decompress path/to/file.txt.cmp -o restored.txt

# run the benchmark over the bundled sample_data/ files
python benchmark.py

# run the test suite (needs pytest: `pip install pytest`)
python -m pytest -v
```

Example, compressing the bundled sample prose file:

```
$ python -m compressor compress sample_data/english_prose.txt --verify
sample_data/english_prose.txt -> sample_data/english_prose.txt.cmp
  original:   3,912 bytes
  compressed: 2,149 bytes
  ratio:      0.549 (45.1% smaller)
  time:       6.3 ms
  round trip: OK
```

## Design decisions

**Two stage pipeline, not a single clever algorithm.** LZ77 alone leaves a
byte stream (distance, length, literal, flag values) that still has an
uneven distribution and is worth entropy coding. Huffman coding alone
ignores repetition across the message entirely. Chaining them, LZ77 output
serialized to bytes, then Huffman encoded, is what actually makes this
useful rather than a toy of either algorithm in isolation.

**Tokens are simple and fixed width (5 bytes: 2 byte distance, 1 byte
length, 1 byte flag, 1 byte literal) rather than bit packed.** A
production compressor (DEFLATE included) bit packs match/literal tokens
directly for maximum density. This implementation deliberately keeps the
LZ77 stage's output format dead simple and lets the Huffman stage recover
the redundancy in that fixed layout instead (lots of repeated small
distance/length/flag values compress well). It costs some ratio compared to
a fully bit packed format, but it keeps `lz77.py` decoupled from the entropy
coder and easy to test in isolation.

**Hash chain match finding, not a naive O(n \* window) scan.** The match
finder keeps a dictionary from 3 byte prefixes to a bounded list of recent
positions, so typical inputs compress in close to linear time instead of
quadratic. `sample_data/repetitive.txt` (19,260 bytes) compresses in about
30ms on a single core.

**Random/incompressible data is expected to grow, not shrink, and the
benchmark says so honestly.** `benchmark.py` also runs against freshly
generated random bytes (not committed to the repo, generated at run time so
there is no reason to version a binary blob) and it reliably comes out
*larger* after compression, since Huffman + container header overhead has
nothing to amortize against when every byte is close to equally likely and
there are no repeats for LZ77 to find. This is not a bug, it's the same
reason `gzip` skips already-compressed files: no algorithm can shrink
genuinely high-entropy data, and pretending otherwise would be misleading.
The benchmark output in [Testing](#testing) below shows all three cases
side by side on purpose.

**Self describing container format.** Every `.cmp` file starts with a
`CMP1` magic and carries its own Huffman frequency table, so decompression
never depends on external state, and feeding it a non-`.cmp` file fails
with a clear `ValueError` instead of a confusing crash deep in the bit
reader.

## Testing

`tests/` has 33 unit tests across all four modules:

- `test_bitio.py`: bit level read/write round trips, including uint packing and EOF behavior.
- `test_huffman.py`: encode/decode round trips for empty input, single byte alphabets, all 256 byte values, random binary data, and a check that generated codes are prefix free (a Huffman tree invariant).
- `test_lz77.py`: match finding correctness, window size enforcement, max match length enforcement, and serialize/deserialize round trips.
- `test_pipeline.py`: end to end round trips on generated data and on the files in `sample_data/`, plus a check that the container format rejects bad magic bytes.

Every test asserts on an actual round trip (`decompress(compress(data)) ==
data`) rather than just on internal shape, since for a compressor a
byte-for-byte restore is the only correctness property that actually
matters.

Benchmark results on the bundled sample data (your numbers will vary
slightly by machine):

```
english_prose.txt          3,912 ->  2,149 bytes  (45.1% smaller)
repetitive.txt             19,260 ->    303 bytes  (98.4% smaller)
random_data (generated)    4,096 ->  8,920 bytes  (-117.8%, expected — see Design decisions)
```

## Possible extensions

- Bit pack LZ77 tokens directly instead of the fixed 5 byte layout, for a real DEFLATE-level ratio.
- Adaptive/streaming Huffman coding to avoid shipping a frequency table for very small inputs.
- Larger match windows with a proper suffix automaton instead of a bounded hash chain.
