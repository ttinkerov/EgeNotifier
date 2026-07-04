from __future__ import annotations

import asyncio
import sys
import warnings
from pathlib import Path


if sys.platform == "win32":
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from egebot.app import main

if __name__ == "__main__":
    main()
