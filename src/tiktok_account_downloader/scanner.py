"""Contains the TikTokAccountDownloader class which drives Playwright to collect video URLs."""

from __future__ import annotations

import os
import sys
from typing import List, Optional, Sequence, Set

from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt

from .utils import parse_netscape_cookies, file_exists_for_video_any, extract_tiktok_video_id
from .db import get_db_collection  # we'll create a small db module

console = Console()


async def _is_captcha_overlay_present(page) -> bool:  # type: ignore
    """Internal helper that checks page and its frames for typical captcha overlays."""  # pragma: no cover
    if "verify" in page.url or "captcha" in page.url:
        return True
    overlays = ["text=Drag the slider", "text=Verify to continue", ".captcha-container"]
    for overlay in overlays:
        if await page.locator(overlay).count() > 0:
            return True
    for frame in page.frames:
        try:
            for overlay in overlays:
                if await frame.locator(overlay).count() > 0:
                    return True
        except Exception:
            pass
    return False


class TikTokAccountDownloader:
    """Scan a TikTok profile page and return discovered video URLs.

    ``scan()`` is asynchronous and can be used in an ``asyncio`` event loop.
    """

    def __init__(
        self,
        profile_url: str,
        headless: bool = True,
        cookies: Optional[List[dict]] = None,
        limit: int = 0,
        mongo_uri: Optional[str] = None,
        output_folder: Optional[str] = None,
        existing_check_folders: Optional[Sequence[str]] = None,
        force_full_scan: bool = False,
    ) -> None:
        self.profile_url = profile_url
        self.headless = headless
        self.cookies = cookies or []
        self.limit = limit
        self.mongo_uri = mongo_uri
        self.output_folder = output_folder
        self.existing_check_folders = list(existing_check_folders or ([] if not output_folder else [output_folder]))
        self.force_full_scan = force_full_scan
        self.video_urls: Set[str] = set()
        self.scanned_urls: Set[str] = set()

    async def scan(self) -> List[str]:
        """Perform the scan and return the list of discovered URLs."""
        try:
            async with async_playwright() as p:
                try:
                    browser = await p.chromium.launch(headless=self.headless)
                except Exception as e:  # pragma: no cover - environment dependent
                    if "Executable doesn't exist" in str(e):
                        console.print("\n[bold red]Playwright Chromium browser not found![/bold red]")
                        console.print("Please install it by running:\n[bold cyan]playwright install chromium[/bold cyan]\n")
                        sys.exit(1)
                    raise

                context = await browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    )
                )

                if self.cookies:
                    console.print(f"[yellow]🍪 Loading {len(self.cookies)} cookies...[/yellow]")
                    await context.add_cookies(self.cookies)

                page = await context.new_page()
                stealth = Stealth()
                await stealth.apply_stealth_async(page)

                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                    transient=False,
                ) as progress:

                    scan_task = progress.add_task("[cyan]🚀 Navigating to profile...", total=None)

                    try:
                        db_collection = None
                        if self.mongo_uri:
                            db_collection = get_db_collection(self.mongo_uri, fail_fast=False)

                        await page.goto(self.profile_url, timeout=60000)
                        await page.wait_for_load_state("domcontentloaded")

                        if "login" in page.url:
                            progress.console.print(
                                "[bold red]⚠️ Redirected to login. You might need to provide cookies or solve a captcha manually.[/bold red]"
                            )

                        if await self._check_captcha(page):
                            progress.stop()
                            console.print("\n[bold red]🚨 !!! Captcha or Verification detected !!![/bold red]")
                            console.print(
                                "[yellow]Please solve the captcha in the browser window.[/yellow]"
                            )
                            Prompt.ask("Press Enter here once you have solved it and the page has loaded")
                            progress.start()
                            await page.wait_for_timeout(3000)

                        progress.update(scan_task, description="[cyan]🔍 Scanning for videos...")

                        # scroll loop
                        last_height = await page.evaluate("document.body.scrollHeight")
                        stuck_retries = 0
                        consecutive_skips = 0

                        while True:  # pragma: no cover - heavy browser interaction
                            urls = await page.evaluate('''() => {
                                let elements = document.querySelectorAll('[data-e2e="user-post-item"] a');
                                if (elements.length === 0) {
                                    elements = document.querySelectorAll('a');
                                }
                                return Array.from(elements)
                                            .map(a => a.href)
                                            .filter(href => href && href.includes('/video/'));
                            }''')

                            new_unseen_urls: List[str] = []
                            for u in urls:
                                u_fixed = u if u.startswith("http") else f"https://www.tiktok.com{u}"
                                if u_fixed not in self.scanned_urls:
                                    new_unseen_urls.append(u_fixed)
                                    self.scanned_urls.add(u_fixed)

                            vids_to_check: List[str] = []
                            for u in new_unseen_urls:
                                vid = extract_tiktok_video_id(u)
                                if vid:
                                    vids_to_check.append(vid)

                            existing_records: Set[str] = set()
                            if vids_to_check and db_collection is not None:
                                try:
                                    cursor = db_collection.find(
                                        {"video_id": {"$in": vids_to_check}},
                                        {"video_id": 1},
                                    )
                                    existing_records = {doc["video_id"] for doc in cursor if "video_id" in doc}
                                except Exception:
                                    pass

                            valid_new_urls: List[str] = []
                            for u in new_unseen_urls:
                                vid = extract_tiktok_video_id(u)

                                already_downloaded = False
                                if vid:
                                    already_downloaded = file_exists_for_video_any(
                                        self.existing_check_folders, vid
                                    )

                                if already_downloaded:
                                    # Skip videos already present on disk, even if DB isn't enabled.
                                    consecutive_skips += 1
                                    continue

                                if vid and vid in existing_records:
                                    # The video is tracked in the database but missing from disk -> re-download
                                    consecutive_skips = 0
                                    valid_new_urls.append(u)
                                else:
                                    consecutive_skips = 0
                                    valid_new_urls.append(u)

                            self.video_urls.update(valid_new_urls)

                            progress.update(
                                scan_task,
                                description=(
                                    f"[cyan]🔍 Scanning... New videos found: "
                                    f"[bold white]{len(self.video_urls)}[/bold white] "
                                    f"(Consecutive Skips: {consecutive_skips}) ✨"
                                ),
                            )

                            if not self.force_full_scan and consecutive_skips > 10:
                                progress.console.print(
                                    "[green]Reached previously downloaded videos. Stopping scan early to save time![/green]"
                                )
                                break

                            if self.limit and len(self.video_urls) >= self.limit:
                                progress.console.print(
                                    f"[green]Reached user-defined limit of {self.limit} videos.[/green]"
                                )
                                self.video_urls = set(list(self.video_urls)[: self.limit])
                                break

                            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                            await page.wait_for_timeout(2000)

                            new_height = await page.evaluate("document.body.scrollHeight")
                            if new_height == last_height:
                                if await self._check_captcha(page):
                                    progress.stop()
                                    console.print(
                                        "[bold red]🚨 !!! Captcha detected during scroll !!![/bold red]"
                                    )
                                    Prompt.ask("Press Enter here once you have solved it")
                                    progress.start()
                                    await page.wait_for_timeout(3000)
                                    new_height = await page.evaluate("document.body.scrollHeight")
                                else:
                                    stuck_retries += 1
                                    if stuck_retries >= 3:
                                        break
                                    await page.wait_for_timeout(2000)
                                    new_height = await page.evaluate("document.body.scrollHeight")
                            else:
                                stuck_retries = 0

                            last_height = new_height

                        progress.update(
                            scan_task,
                            description=f"[bold green]✨ Scan complete. Total videos found: {len(self.video_urls)}[/bold green]",
                        )
                        progress.stop_task(scan_task)

                    except Exception as e:  # pragma: no cover
                        progress.console.print(f"[bold red]Error during scan: {e}[/bold red]")
                    finally:
                        await browser.close()
        except Exception as e:  # pragma: no cover
            console.print(f"[bold red]Critical Error during Playwright execution: {e}[/bold red]")

        return list(self.video_urls)

    async def _check_captcha(self, page) -> bool:  # type: ignore
        """Instance wrapper for internal captcha check to maintain backwards compatibility."""  # pragma: no cover
        return await _is_captcha_overlay_present(page)
