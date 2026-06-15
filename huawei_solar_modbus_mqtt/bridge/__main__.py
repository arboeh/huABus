"""Package entry point for `python -m bridge`."""

import asyncio

from .main import _run

asyncio.run(_run())
