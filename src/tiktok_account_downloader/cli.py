"""Command line entry point for the TikTok Account Downloader package."""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys
from typing import List
from urllib.parse import urlsplit

from . import TikTokAccountDownloader, download_videos, clean_tiktok_url, parse_netscape_cookies
from .db import get_db_collection
from rich.console import Console

console = Console()


def _is_tiktok_profile_input(value: str) -> bool:
    """Return True when the value looks like @username or a TikTok profile URL."""
    if not value:
        return False
    if value.startswith("@"):
        return True
    if re.fullmatch(r"[a-zA-Z0-9_.-]+", value):
        return True
    try:
        parts = urlsplit(value)
    except Exception:
        return False
    host = (parts.netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = parts.path or ""
    return host == "tiktok.com" and bool(re.search(r"^/@[a-zA-Z0-9_.-]+/?$", path))


def _run_doctor(cookies_path: str, output_dir: str, mongo_uri: str | None) -> int:
    """Run lightweight local checks and print actionable output."""
    console.print("[bold cyan]Running diagnostics...[/bold cyan]")

    issues = 0
    major, minor = sys.version_info.major, sys.version_info.minor
    if major == 3 and minor >= 10:
        console.print(f"[green]OK[/green] Python {major}.{minor}")
    else:
        issues += 1
        console.print("[red]FAIL[/red] Python 3.10+ is required")

    try:
        os.makedirs(output_dir, exist_ok=True)
        test_path = os.path.join(output_dir, ".write_test")
        with open(test_path, "w", encoding="utf-8") as handle:
            handle.write("ok")
        os.remove(test_path)
        console.print(f"[green]OK[/green] Output directory writable: {output_dir}")
    except Exception as exc:
        issues += 1
        console.print(f"[red]FAIL[/red] Cannot write to output directory '{output_dir}': {exc}")

    if os.path.exists(cookies_path):
        cookies = parse_netscape_cookies(cookies_path)
        if cookies:
            console.print(f"[green]OK[/green] Cookies parsed: {len(cookies)} from '{cookies_path}'")
        else:
            issues += 1
            console.print(
                f"[red]FAIL[/red] Cookies file found at '{cookies_path}' but no valid TikTok cookies were parsed"
            )
    else:
        console.print(f"[yellow]WARN[/yellow] No cookies file at '{cookies_path}' (public profiles may still work)")

    if mongo_uri:
        collection = get_db_collection(mongo_uri, fail_fast=False)
        if collection is None:
            issues += 1
            console.print("[yellow]WARN[/yellow] MongoDB cache check failed; runs can still continue without cache")
        else:
            console.print("[green]OK[/green] MongoDB connection verified")

    console.print("[bold green]Diagnostics complete.[/bold green]" if issues == 0 else "[bold yellow]Diagnostics complete with warnings.[/bold yellow]")
    return 0 if issues == 0 else 1


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TikTok Account Downloader")
    parser.add_argument("url", nargs="?", help="TikTok Profile URL (e.g., https://www.tiktok.com/@username)")
    parser.add_argument("--headless", dest="headless", action="store_true", help="Run browser in headless mode (default: True)")
    parser.add_argument("--no-headless", dest="headless", action="store_false", help="Run browser with visible window")
    parser.set_defaults(headless=True)
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
    parser.add_argument("--debug", action="store_true", help="Enable debug logging for yt-dlp and extractor fallbacks")
    parser.add_argument("--doctor", action="store_true", help="Run local diagnostics and exit")

    args = parser.parse_args(argv)

    cookies_path = args.cookies_file or os.path.join("src", "cookies.txt")
    if args.doctor:
        return _run_doctor(cookies_path=cookies_path, output_dir=args.output, mongo_uri=args.mongo_uri)

    if not args.url:
        console.print("[bold red]Missing required profile URL.[/bold red]")
        parser.print_help()
        return 2

    if args.concurrent < 1:
        console.print("[bold red]--concurrent must be >= 1[/bold red]")
        return 2

    is_headless = args.headless
    if sys.platform == "linux" and not os.environ.get("DISPLAY") and not is_headless:
        console.print("No DISPLAY detected. Forcing headless mode.")
        is_headless = True

    cookies = []
    if os.path.exists(cookies_path):
        console.print(f"Found cookies file at '{cookies_path}'. Loading...")
        cookies = parse_netscape_cookies(cookies_path)
        if not cookies:
            console.print(
                "[yellow]Cookies file loaded but no valid TikTok cookies were found. "
                "Private or age-restricted videos may not be accessible.[/yellow]"
            )
    else:
        console.print(f"No cookies file found at '{cookies_path}'. Continuing without cookies.")

    if not _is_tiktok_profile_input(args.url):
        console.print(
            "[bold red]Invalid TikTok profile input.[/bold red] Use a full profile URL, @username, or username."
        )
        return 2

    profile_url = clean_tiktok_url(args.url)
    if not profile_url.startswith("http"):
        profile_url = f"https://www.tiktok.com/{profile_url}" if profile_url.startswith("@") else f"https://www.tiktok.com/@{profile_url}"

    console.print(f"Target Profile URL: {profile_url}")

    username = "unknown_user"
    match = re.search(r'@([a-zA-Z0-9_.-]+)', profile_url)
    if match:
        username = match.group(1)
    user_output_dir = os.path.join(args.output, username)
    existing_check_dirs = [
        user_output_dir,
        os.path.join(args.output, "_trash", username),
        os.path.join(args.output, "_kept", username),
        os.path.join(args.output, "-trash", username),
        os.path.join(args.output, "-kept", username),
    ]

    downloader = TikTokAccountDownloader(
        profile_url,
        headless=is_headless,
        cookies=cookies,
        limit=args.limit,
        mongo_uri=args.mongo_uri,
        output_folder=user_output_dir,
        existing_check_folders=existing_check_dirs,
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
                debug=args.debug,
                existing_check_folders=existing_check_dirs,
            )
    else:
        console.print("[yellow]No videos found to download.[/yellow]")

    return 0


if __name__ == "__main__":
    sys.exit(main())
