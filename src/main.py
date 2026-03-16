"""Deprecated standalone entrypoint.

Use `python -m tiktok_account_downloader.cli` (or the installed
`tiktok-account-downloader` command) for normal usage.
"""

from __future__ import annotations

import sys

from tiktok_account_downloader.cli import main


if __name__ == "__main__":
    sys.exit(main())
