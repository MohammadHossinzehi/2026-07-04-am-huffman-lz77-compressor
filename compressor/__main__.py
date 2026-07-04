"""Allows `python -m compressor <command>` as a shortcut for
`python -m compressor.cli <command>`.
"""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
