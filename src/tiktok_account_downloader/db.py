"""Database helper utilities."""

import sys
from typing import Optional

from pymongo import MongoClient
from rich.console import Console

console = Console()


def get_db_collection(mongo_uri: str):
    """Return a :class:`pymongo.collection.Collection` for downloaded videos.

    The function will exit the program if it cannot connect, since the calling
    code generally relies on having a valid collection.
    """
    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        db = client['tiktok_account_downloader']
        collection = db['downloaded_videos']
        return collection
    except Exception as e:
        console.print(f"[bold red]Failed to connect to MongoDB: {e}[/bold red]")
        sys.exit(1)
