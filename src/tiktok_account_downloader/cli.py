"""Command line entry point for the TikTok Account Downloader package."""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys
from typing import List

from . import TikTokAccountDownloader, download_videos, clean_tiktok_url, parse_netscape_cookies
from rich.console import Console

console = Console()


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TikTok Account Downloader")
    parser.add_argument("url", help="TikTok Profile URL (e.g., https://www.tiktok.com/@username)")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode (default: False)", default=False)
    parser.add_argument("--dry-run", action="store_true", help="Only scan and list videos without downloading")
    parser.add_argument("--force-full-scan", action="store_true", help="Do not stop scanning early even if previously downloaded videos are found", default=False)
    parser.add_argument("--output", default="downloads", help="Output directory for downloads")
    parser.add_argument("--limit", type=int, help="Maximum number of videos to scan and download", default=0)
    parser.add_argument(
        "--browser",
        choices=["chrome", "firefox", "edge", "opera", "safari", "vivaldi", "brave"],
        help="Extract cookies from an installed browser instead of using cookies.txt",
    )
    parser.add_argument("--cookies-file", default=None, help="Path to a Netscape-format cookies.txt file for scanning/downloading")
    parser.add_argument("--mongo-uri", default=os.getenv("MONGO_URI"), help="MongoDB Connection String for tracking downloaded videos")
    parser.add_argument("-c", "--concurrent", type=int, default=1, help="Number of concurrent downloads (default: 1)")

    args = parser.parse_args(argv)
    if args.concurrent < 1:
        console.print("[bold red]--concurrent must be >= 1[/bold red]")
        return 2

    is_headless = args.headless
    if sys.platform == "linux" and not os.environ.get("DISPLAY") and not is_headless:
        console.print("No DISPLAY detected. Forcing headless mode.")
        is_headless = True

    cookies_path = args.cookies_file or os.path.join("src", "cookies.txt")
    cookies = []
    if os.path.exists(cookies_path):
        console.print(f"Found cookies file at '{cookies_path}'. Loading...")
        cookies = parse_netscape_cookies(cookies_path)
    else:
        console.print(f"No cookies file found at '{cookies_path}'. Continuing without cookies.")

    profile_url = clean_tiktok_url(args.url)
    if not profile_url.startswith("http"):
        profile_url = f"https://www.tiktok.com/{profile_url}" if profile_url.startswith("@") else f"https://www.tiktok.com/@{profile_url}"

    console.print(f"Target Profile URL: {profile_url}")

    username = "unknown_user"
    match = re.search(r'@([a-zA-Z0-9_.-]+)', profile_url)
    if match:
        username = match.group(1)
    user_output_dir = os.path.join(args.output, username)

    downloader = TikTokAccountDownloader(
        profile_url,
        headless=is_headless,
        cookies=cookies,
        limit=args.limit,
        mongo_uri=args.mongo_uri,
        output_folder=user_output_dir,
        force_full_scan=args.force_full_scan,
    )

    video_urls: List[str] = asyncio.run(downloader.scan())
    if video_urls:
        console.print(f"[bold green]Found {len(video_urls)} videos to process.[/bold green]")
        if args.dry_run:
            console.print(f"[yellow]Dry run enabled. Skipping download to '{user_output_dir}'.[/yellow]")
            for url in video_urls:
                console.print(url)
        else:
            download_videos(
                video_urls,
                user_output_dir,
                cookie_file=cookies_path if os.path.exists(cookies_path) else None,
                browser=args.browser,
                mongo_uri=args.mongo_uri,
                concurrent_downloads=args.concurrent,
            )
    else:
        console.print("[yellow]No videos found to download.[/yellow]")

    return 0


if __name__ == "__main__":
    sys.exit(main())
