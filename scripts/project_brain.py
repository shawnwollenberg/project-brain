#!/usr/bin/env python3
"""Source-tree compatibility launcher."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from project_brain.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
