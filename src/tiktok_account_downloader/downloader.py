"""Download logic using yt-dlp and a rich progress UI."""

from __future__ import annotations

import os
import threading
from typing import Any, Dict, Iterable, List, Optional, Tuple

import yt_dlp
from rich.console import Console
from rich.progress import (
    Progress,
    TextColumn,
    BarColumn,
    DownloadColumn,
    TransferSpeedColumn,
    TimeRemainingColumn,
)

from .utils import (
    clean_tiktok_url,
    extract_tiktok_video_id,
    file_exists_for_video,
    is_probably_tiktok_video_url,
    with_tiktok_query_params,
    parse_netscape_cookies,
    write_netscape_cookie_file,
)
from .db import get_db_collection

console = Console()


class _RichYtDlpLogger:
    # yt-dlp only requires a logger object with debug/warning/error methods.
    # This avoids depending on internal classes that may not exist in newer versions.
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        # filter out non-errors
        if "ERROR:" in msg:
            lower = msg.lower()
            if "list index out of range" in lower:
                return
            if "does not look like a netscape format cookies file" in lower:
                return
            if "invalid netscape format cookies file" in lower:
                return
            console.print(f"[red]{msg}[/red]")

    def info(self, msg):
        pass


def download_videos(
    video_urls: Iterable[str],
    output_folder: str = "downloads",
    cookie_file: Optional[str] = None,
    browser: Optional[str] = None,
    mongo_uri: Optional[str] = None,
    concurrent_downloads: int = 1,
    debug: bool = False,
    extra_http_headers: Optional[Dict[str, str]] = None,
) -> None:
    """Download each URL with ``yt-dlp`` and display progress using Rich.

    This function is synchronous and may be called from an async context by
    using ``run_in_executor`` if desired.
    """

    video_urls = list(video_urls)
    total_input_urls = len(video_urls)
    if not video_urls:
        console.print("[yellow]No videos to download.[/yellow]")
        return

    os.makedirs(output_folder, exist_ok=True)

    # Pre-filter by existing files on disk (even if MongoDB isn't used)
    url_map: List[Tuple[str, Optional[str]]] = []
    filtered: List[str] = []
    skipped = 0
    skipped_existing_on_disk = 0

    for url in video_urls:
        video_id = extract_tiktok_video_id(url)
        url_map.append((url, video_id))

    for url, vid in url_map:
        if vid and file_exists_for_video(output_folder, vid):
            skipped += 1
            continue
        filtered.append(url)

    if skipped:
        skipped_existing_on_disk += skipped
        console.print(f"[bold green]Skipped {skipped} videos already downloaded and present on disk.[/bold green]")

    video_urls = filtered

    db_collection = None
    if mongo_uri:
        console.print("[dim]Connecting to MongoDB...[/dim]")
        db_collection = get_db_collection(mongo_uri, fail_fast=False)

        # pre-filter against DB (only for videos that are not already on disk)
        url_map = [(url, vid) for url, vid in url_map if vid and not file_exists_for_video(output_folder, vid)]
        video_ids = [vid for _, vid in url_map if vid]

        existing: set = set()
        if video_ids:
            try:
                cursor = db_collection.find({"video_id": {"$in": video_ids}}, {"video_id": 1})
                existing = {doc.get("video_id") for doc in cursor if "video_id" in doc}
            except Exception as e:
                console.print(f"[red]Error querying MongoDB: {e}[/red]")

        filtered = []
        skipped = 0
        for url, vid in url_map:
            if vid and vid in existing and file_exists_for_video(output_folder, vid):
                skipped += 1
                continue
            filtered.append(url)

        if skipped:
            skipped_existing_on_disk += skipped
            console.print(f"[bold green]Skipped {skipped} videos already downloaded and present on disk (via DB).[/bold green]")

        video_urls = filtered

    if not video_urls:
        console.print("[bold yellow]All videos are already downloaded and present on disk. Nothing to do![/bold yellow]")
        return

    console.print(f"[bold cyan]Starting download of {len(video_urls)} videos to '{output_folder}'...[/bold cyan]")

    effective_cookiefile: Optional[str] = None
    if cookie_file and os.path.exists(cookie_file):
        parsed = parse_netscape_cookies(cookie_file)
        if parsed:
            effective_cookiefile = write_netscape_cookie_file(parsed)

    # conservative default headers to make TikTok extractor behave more like a browser
    default_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36',
        'Referer': 'https://www.tiktok.com/',
    }
    if extra_http_headers:
        default_headers.update(extra_http_headers)

    ydl_opts: Dict[str, Any] = {
        'outtmpl': os.path.join(output_folder, '%(uploader)s_%(upload_date)s_%(id)s_%(title).50s.%(ext)s'),
        'ignoreerrors': True,
        'format': 'bestvideo+bestaudio/best',
        'quiet': not debug,
        'no_warnings': not debug,
        'logger': _RichYtDlpLogger(),
        'retries': 3,
        'fragment_retries': 3,
        'extractor_retries': 3,
        'socket_timeout': 30,
        'http_headers': default_headers,
        'noplaylist': True,
    }

    if browser:
        ydl_opts['cookiesfrombrowser'] = [browser]
        console.print(f"[dim]Extracting cookies from local browser: {browser}[/dim]")
    elif effective_cookiefile:
        ydl_opts['cookiefile'] = effective_cookiefile
        console.print(f"[dim]Using cookies file: {cookie_file}[/dim]")

    success_count = 0
    error_count = 0
    skipped_count = 0

    progress = Progress(
        TextColumn("[bold blue]{task.description}", justify="right"),
        BarColumn(bar_width=40),
        "[progress.percentage]{task.percentage:>3.1f}%",
        "•",
        DownloadColumn(),
        "•",
        TransferSpeedColumn(),
        "•",
        TimeRemainingColumn(),
        console=console,
    )
    progress.__enter__()

    overall_task = progress.add_task("Total Progress", total=len(video_urls))
    active_downloads: Dict[str, int] = {}
    progress_lock = threading.Lock()

    def progress_hook(d: dict):
        video_id = d.get('info_dict', {}).get('id', 'unknown')
        with progress_lock:
            if d['status'] == 'downloading':
                if video_id not in active_downloads:
                    title = d.get('info_dict', {}).get('title', 'Unknown')
                    display_title = title[:30] + '...' if len(title) > 30 else title
                    task_id = progress.add_task(f"[cyan]{display_title}", total=d.get('total_bytes') or d.get('total_bytes_estimate', 0))
                    active_downloads[video_id] = task_id
                task_id = active_downloads[video_id]
                progress.update(task_id, completed=d.get('downloaded_bytes', 0), total=d.get('total_bytes') or d.get('total_bytes_estimate', 0))
            elif d['status'] == 'finished':
                if video_id in active_downloads:
                    task_id = active_downloads.pop(video_id)
                    progress.update(task_id, completed=d.get('total_bytes', 100), description=f"[green]✓ {progress.tasks[task_id].description.replace('[cyan]', '')}")
                    try:
                        progress.remove_task(task_id)
                    except Exception:
                        pass
                if db_collection is not None and video_id != 'unknown':
                    try:
                        db_collection.update_one(
                            {"video_id": video_id},
                            {"$set": {"video_id": video_id, "status": "downloaded"}},
                            upsert=True,
                        )
                    except Exception:
                        pass

    ydl_opts['progress_hooks'] = [progress_hook]

    def process_url(url: str) -> Tuple[str, bool, Optional[str]]:
        cleaned = clean_tiktok_url(url)
        video_id = extract_tiktok_video_id(cleaned)
        if not cleaned:
            return (url, False, "SKIP: Empty URL")
        if not cleaned.startswith("http"):
            return (cleaned, False, "SKIP: Invalid URL")
        if not is_probably_tiktok_video_url(cleaned):
            return (cleaned, False, "SKIP: Not a TikTok video URL")
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(cleaned, download=True)
                if info:
                    return (cleaned, True, None)
                if video_id and file_exists_for_video(output_folder, video_id):
                    return (cleaned, True, None)
        except Exception as e:
            msg = str(e) if e is not None else "Unknown error"
            lower = msg.lower()
            # Common blockers: IP blocked / page unavailable
            if "your ip address is blocked" in lower or "page not available" in lower:
                return (cleaned, False, f"SKIP: {msg}")

            # Try common TikTok extractor fallback when webpage extraction fails
            if "unable to extract webpage video data" in lower or "list index out of range" in lower:
                fallback = with_tiktok_query_params(cleaned, {"is_copy_url": "1", "is_from_webapp": "v1", "lang": "en"})
                # try again with same opts (headers enabled) and allow_unplayable_formats
                fallback_opts = dict(ydl_opts)
                fallback_opts['allow_unplayable_formats'] = True
                try:
                    with yt_dlp.YoutubeDL(fallback_opts) as ydl:
                        info = ydl.extract_info(fallback, download=True)
                        if info:
                            return (fallback, True, None)
                except Exception as e2:
                    if debug:
                        console.print(f"[red]Fallback extractor also failed: {e2}[/red]")
                    # continue to final SKIP below

            if debug:
                console.print(f"[red]Error downloading {cleaned}: {msg}[/red]")
            return (cleaned, False, msg)
        return (cleaned, False, "SKIP: Unavailable/blocked (no info)")

    from concurrent.futures import ThreadPoolExecutor, as_completed

    with ThreadPoolExecutor(max_workers=concurrent_downloads) as executor:
        futures = [executor.submit(process_url, url) for url in video_urls]
        for future in as_completed(futures):
            url, success, error_msg = future.result()
            if success:
                success_count += 1
            else:
                if error_msg and error_msg.startswith("SKIP:"):
                    skipped_count += 1
                    with progress_lock:
                        console.print(f"[dim]{error_msg} -> {url}[/dim]")
                else:
                    error_count += 1
                    if error_msg and "already been downloaded" not in error_msg.lower() and "abort" not in error_msg.lower():
                        with progress_lock:
                            console.print(f"[red]Error downloading {url}: {error_msg}[/red]")
            with progress_lock:
                progress.update(overall_task, advance=1)

    progress.__exit__(None, None, None)

    # summary table
    from rich.table import Table

    table = Table(title="Scan & Download Summary", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Total Scanned URLs", str(total_input_urls))
    table.add_row("Successfully Downloaded", str(success_count))
    if skipped_existing_on_disk > 0:
        table.add_row("Already On Disk", f"[green]{skipped_existing_on_disk}[/green]")
    if skipped_count > 0:
        table.add_row("Skipped During Download", f"[yellow]{skipped_count}[/yellow]")
    if error_count > 0:
        table.add_row("Errors", f"[red]{error_count}[/red]")
    console.print(table)

    if effective_cookiefile:
        try:
            os.remove(effective_cookiefile)
        except Exception:
            pass
