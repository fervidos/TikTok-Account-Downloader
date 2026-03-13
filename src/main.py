# Deprecated standalone script. Use the package entry point instead.
# This file remains for backwards compatibility and simply proxies to
# ``tiktok_account_downloader.cli``.

from __future__ import annotations

import sys

from tiktok_account_downloader.cli import main

if __name__ == "__main__":
    sys.exit(main())

def parse_netscape_cookies(file_path):
    """Parses a Netscape HTTP Cookie File."""
    cookies = []
    try:
        with open(file_path, 'r') as f:
            for line in f:
                if line.startswith('#') or not line.strip():
                    continue
                
                parts = line.strip().split('\t')
                if len(parts) >= 7:
                    domain = parts[0]
                    # Filter cookies to only TikTok related domains to massively speed up loading
                    if 'tiktok' not in domain.lower() and 'byteoversea' not in domain.lower():
                        continue
                    
                    cookie = {
                        'domain': domain,
                        'path': parts[2],
                        'secure': parts[3].upper() == 'TRUE',
                        'expires': float(parts[4]) if parts[4] else -1,
                        'name': parts[5],
                        'value': parts[6]
                    }
                    cookies.append(cookie)
    except Exception as e:
        console.print(f"[red]Error parsing cookies file: {e}[/red]")
        return []
    return cookies

class TikTokAccountDownloader:
    def __init__(self, profile_url, headless=True, cookies=None, limit=0, mongo_uri=None, output_folder=None, force_full_scan=False):
        self.profile_url = profile_url
        self.headless = headless
        self.cookies = cookies or []
        self.limit = limit
        self.mongo_uri = mongo_uri
        self.output_folder = output_folder or DOWNLOAD_DIR
        self.force_full_scan = force_full_scan
        self.video_urls = set()
        self.scanned_urls = set()

    async def _check_captcha(self, page):
        """Checks if a captcha or verification wall is present to allow centralized handling."""
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
            except:
                pass

        return False

    async def scan(self):
        """Scans the profile for video URLs."""
        try:
            async with async_playwright() as p:
                # Check for browser installation
                try:
                    browser = await p.chromium.launch(headless=self.headless)
                except Exception as e:
                    if "Executable doesn't exist" in str(e):
                        console.print("\n[bold red]Playwright Chromium browser not found![/bold red]")
                        console.print("Please install it by running the following command:")
                        console.print("[bold cyan]playwright install chromium[/bold cyan]\n")
                        sys.exit(1)
                    else:
                        raise e

                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                
                if self.cookies:
                    console.print(f"[yellow]🍪 Loading {len(self.cookies)} cookies...[/yellow]")
                    await context.add_cookies(self.cookies)

                page = await context.new_page()
                # Apply stealth techniques
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
                            db_collection = get_db_collection(self.mongo_uri)
                            
                        # Go to profile
                        await page.goto(self.profile_url, timeout=60000)
                        # Avoid 'networkidle' on dynamic sites like TikTok because background polling (analytics, websockets) never truly stops
                        await page.wait_for_load_state("domcontentloaded")
                        
                        # Check for errors or login walls
                        if "login" in page.url:
                            progress.console.print("[bold red]⚠️ Redirected to login. You might need to handle captcha manually or provide cookies.[/bold red]")

                        if await self._check_captcha(page):
                            progress.stop()
                            console.print("\n[bold red]🚨 !!! Captcha or Verification detected !!![/bold red]")
                            console.print("[yellow]Please solve the captcha in the browser window.[/yellow]")
                            Prompt.ask("Press Enter here once you have solved it and the page has loaded")
                            progress.start()
                            await page.wait_for_timeout(3000)
                        
                        progress.update(scan_task, description="[cyan]🔍 Scanning for videos...")
                        # Scroll and collect
                        last_height = await page.evaluate("document.body.scrollHeight")
                        stuck_retries = 0
                        consecutive_skips = 0

                        while True:
                            # Collect links natively in JS for massive performance gain
                            urls = await page.evaluate('''() => {
                                let elements = document.querySelectorAll('[data-e2e="user-post-item"] a');
                                if (elements.length === 0) {
                                    elements = document.querySelectorAll('a');
                                }
                                return Array.from(elements)
                                            .map(a => a.href)
                                            .filter(href => href && href.includes('/video/'));
                            }''')
                            
                            new_unseen_urls = []
                            for u in urls:
                                u_fixed = u if u.startswith("http") else f"https://www.tiktok.com{u}"
                                if u_fixed not in self.scanned_urls:
                                    new_unseen_urls.append(u_fixed)
                                    self.scanned_urls.add(u_fixed)

                            vids_to_check = []
                            for u in new_unseen_urls:
                                try:
                                    vid = u.split('/')[-1].split('?')[0]
                                    if vid:
                                        vids_to_check.append(vid)
                                except:
                                    pass

                            existing_records = set()
                            if vids_to_check and db_collection is not None:
                                try:
                                    cursor = db_collection.find({"video_id": {"$in": vids_to_check}}, {"video_id": 1})
                                    existing_records = {doc.get("video_id") for doc in cursor if "video_id" in doc}
                                except Exception as e:
                                    pass

                            valid_new_urls = []
                            for u in new_unseen_urls:
                                try:
                                    vid = u.split('/')[-1].split('?')[0]
                                except:
                                    vid = None
                                
                                # if its in the database and in the files, skip it entirely
                                if vid and vid in existing_records:
                                    file_exists = file_exists_for_video(self.output_folder, vid)
                                    
                                    if file_exists:
                                        consecutive_skips += 1
                                    else:
                                        consecutive_skips = 0
                                        valid_new_urls.append(u)
                                else:
                                    # Reset skip counter if we find a new video (or one that needs redownloading)
                                    consecutive_skips = 0
                                    valid_new_urls.append(u)
                            
                            self.video_urls.update(valid_new_urls)
                            
                            progress.update(scan_task, description=f"[cyan]🔍 Scanning... New videos found: [bold white]{len(self.video_urls)}[/bold white] (Consecutive Skips: {consecutive_skips}) ✨")

                            if not self.force_full_scan and consecutive_skips > 10:
                                # We only hit >10 consecutive skips if we pass the pinned videos and hit a solid chunk of already genuinely downloaded videos
                                progress.console.print("[green]Reached previously downloaded videos. Stopping scan early to save time![/green]")
                                break

                            if self.limit and len(self.video_urls) >= self.limit:
                                progress.console.print(f"[green]Reached user-defined limit of {self.limit} videos.[/green]")
                                # Trim to exact limit
                                self.video_urls = set(list(self.video_urls)[:self.limit])
                                break

                            # Scroll down
                            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                            
                            # Random wait to mimic human behavior slightly
                            await page.wait_for_timeout(2000)
                            
                            # Check if reached bottom
                            new_height = await page.evaluate("document.body.scrollHeight")
                            if new_height == last_height:
                                if await self._check_captcha(page):
                                    progress.stop()
                                    console.print("[bold red]🚨 !!! Captcha detected during scroll !!![/bold red]")
                                    Prompt.ask("Press Enter here once you have solved it")
                                    progress.start()
                                    await page.wait_for_timeout(3000)
                                    new_height = await page.evaluate("document.body.scrollHeight") # Re-read height
                                else:
                                    stuck_retries += 1
                                    if stuck_retries >= 3:
                                        break
                                    await page.wait_for_timeout(2000)
                                    new_height = await page.evaluate("document.body.scrollHeight")
                            else:
                                stuck_retries = 0
                            
                            last_height = new_height
                        
                        progress.update(scan_task, description=f"[bold green]✨ Scan complete. Total videos found: {len(self.video_urls)}[/bold green]")
                        progress.stop_task(scan_task)

                    except Exception as e:
                        progress.console.print(f"[bold red]Error during scan: {e}[/bold red]")
                    finally:
                        await browser.close()
        except Exception as e:
             console.print(f"[bold red]Critical Error during Playwright execution: {e}[/bold red]")
        
        return list(self.video_urls)

# Removed old logging classes

class RichYtDlpLogger:
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): 
        # Only print actual errors, not warnings yt-dlp classifies as errors sometimes
        if "ERROR:" in msg:
            if "list index out of range" in msg.lower():
                return
            if "does not look like a netscape format cookies file" in msg.lower():
                return
            if "invalid netscape format cookies file" in msg.lower():
                return
            console.print(f"[red]{msg}[/red]")
    def info(self, msg): pass

def get_db_collection(mongo_uri):
    """Connects to MongoDB and returns the downloaded_videos collection."""
    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        db = client['tiktok_scanner']
        collection = db['downloaded_videos']
        return collection
    except Exception as e:
        console.print(f"[bold red]Failed to connect to MongoDB: {e}[/bold red]")
        sys.exit(1)

def file_exists_for_video(output_folder, video_id):
    """Checks if any valid final media file matching the video ID exists in the output folder."""
    if not output_folder:
        return False
    if not os.path.exists(output_folder):
        return False
        
    # Build a more specific pattern that ignores temp downloads
    # It must have the ID and must end in a typical media format, not .part or .ytdl
    extensions = ['.mp4', '.mkv', '.webm', '.ts', '.jpg', '.png']
    
    for filename in os.listdir(output_folder):
        if video_id in filename:
            # Check if it's a completed file by looking at the extension
            if any(filename.lower().endswith(ext) for ext in extensions):
                return True
                
    return False

def clean_tiktok_url(raw_url):
    if not raw_url:
        return ""
    url = str(raw_url).strip()
    url = url.strip("`\"'")
    url = url.rstrip(" .,:;")
    url = url.strip("`\"'")
    return url

def is_probably_tiktok_video_url(url):
    if not url:
        return False
    try:
        parts = urlsplit(url)
    except Exception:
        return False
    host = (parts.netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if host != "tiktok.com":
        return False
    path = parts.path or ""
    return bool(re.search(r"^/@[a-zA-Z0-9_.-]+/video/\d+$", path))

def with_tiktok_query_params(url, extra_params):
    parts = urlsplit(url)
    existing = dict(parse_qsl(parts.query, keep_blank_values=True))
    existing.update(extra_params)
    query = urlencode(existing)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))

def write_netscape_cookie_file(cookies):
    if not cookies:
        return None
    handle = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", delete=False, suffix=".cookies.txt")
    try:
        handle.write("# Netscape HTTP Cookie File\n")
        handle.write("# This file was generated by TikTok Account Downloader for yt-dlp.\n")
        for c in cookies:
            domain = str(c.get("domain") or "").strip()
            if not domain:
                continue
            include_subdomains = "TRUE" if domain.startswith(".") else "FALSE"
            path = str(c.get("path") or "/")
            secure = "TRUE" if c.get("secure") else "FALSE"
            expires = c.get("expires")
            try:
                expires_f = float(expires) if expires is not None else 0.0
                expires_int = str(int(expires_f)) if expires_f > 0 else "0"
            except Exception:
                expires_int = "0"
            name = str(c.get("name") or "")
            value = str(c.get("value") or "")
            handle.write(f"{domain}\t{include_subdomains}\t{path}\t{secure}\t{expires_int}\t{name}\t{value}\n")
        return handle.name
    finally:
        handle.close()

def download_videos(video_urls, output_folder=DOWNLOAD_DIR, cookie_file=None, browser=None, mongo_uri=None, concurrent_downloads=1):
    """Downloads videos using yt-dlp with a rich UI and MongoDB caching."""
    if not video_urls:
        console.print("[yellow]No videos to download.[/yellow]")
        return
    
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # MongoDB Setup
    db_collection = None
    if mongo_uri:
        console.print("[dim]Connecting to MongoDB...[/dim]")
        db_collection = get_db_collection(mongo_uri)
        
        # Pre-filter videos
        filtered_urls = []
        console.print("[dim]Checking database for existing videos...[/dim]")
        
        skipped_count = 0
        url_map = []
        video_ids_to_check = []
        
        for url in video_urls:
            try:
                 # Standard TikTok URL format is .../video/ID
                video_id = url.split('/')[-1].split('?')[0] 
                if video_id:
                    video_ids_to_check.append(video_id)
                    url_map.append((url, video_id))
                else:
                    filtered_urls.append(url)
            except IndexError:
                # If URL parsing fails, just try to download it
                filtered_urls.append(url)
                continue
                
        # Bulk query MongoDB
        existing_records = set()
        if video_ids_to_check:
            try:
                cursor = db_collection.find({"video_id": {"$in": video_ids_to_check}}, {"video_id": 1})
                existing_records = {doc.get("video_id") for doc in cursor if "video_id" in doc}
            except Exception as e:
                console.print(f"[red]Error querying MongoDB: {e}[/red]")
                
        for url, video_id in url_map:
            if video_id in existing_records:
                # Video is in DB. Does the file exist?
                if file_exists_for_video(output_folder, video_id):
                    # In DB and exists on disk. Skip.
                    skipped_count += 1
                    continue
            
            filtered_urls.append(url)
            
        if skipped_count > 0:
            console.print(f"[bold green]Skipped {skipped_count} videos already downloaded and present on disk.[/bold green]")
            
        video_urls = filtered_urls

    if not video_urls:
        console.print("[bold yellow]All videos are already downloaded and present on disk. Nothing to do![/bold yellow]")
        return

    console.print(f"[bold cyan]Starting download of {len(video_urls)} videos to '{output_folder}'...[/bold cyan]")

    effective_cookiefile = None
    if cookie_file and os.path.exists(cookie_file):
        parsed = parse_netscape_cookies(cookie_file)
        if parsed:
            effective_cookiefile = write_netscape_cookie_file(parsed)

    # Setup yt-dlp options
    ydl_opts = {
        'outtmpl': os.path.join(output_folder, '%(uploader)s_%(upload_date)s_%(id)s_%(title).50s.%(ext)s'),
        'ignoreerrors': True,
        'format': 'bestvideo+bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'logger': RichYtDlpLogger(),
        'retries': 3,
        'fragment_retries': 3,
        'extractor_retries': 3,
        'socket_timeout': 30,
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

    # Create the overall progress bar
    with Progress(
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
    ) as progress:
        
        overall_task = progress.add_task("Total Progress", total=len(video_urls))
        active_downloads = {} # Track active download tasks
        progress_lock = threading.Lock()

        def progress_hook(d):
            video_id = d.get('info_dict', {}).get('id', 'unknown')
            
            with progress_lock:
                if d['status'] == 'downloading':
                    # Add task if it doesn't exist
                    if video_id not in active_downloads:
                        title = d.get('info_dict', {}).get('title', 'Unknown')
                        # Truncate title for display
                        display_title = title[:30] + '...' if len(title) > 30 else title
                        task_id = progress.add_task(f"[cyan]{display_title}", total=d.get('total_bytes') or d.get('total_bytes_estimate', 0))
                        active_downloads[video_id] = task_id
                    
                    # Update task
                    task_id = active_downloads[video_id]
                    progress.update(task_id, completed=d.get('downloaded_bytes', 0), total=d.get('total_bytes') or d.get('total_bytes_estimate', 0))

                elif d['status'] == 'finished':
                    # Only update task if we were actually tracking its download bytes
                    if video_id in active_downloads:
                        task_id = active_downloads[video_id]
                        progress.update(task_id, completed=d.get('total_bytes', 100), description=f"[green]✓ {progress.tasks[task_id].description.replace('[cyan]', '')}")
                        try:
                            progress.remove_task(task_id)
                        except Exception:
                            pass
                        active_downloads.pop(video_id, None)
                        
                        # Store successful download in DB
                        if db_collection is not None and video_id != 'unknown':
                            try:
                                # Use upsert to avoid duplicate key errors if it somehow already exists
                                db_collection.update_one(
                                    {"video_id": video_id},
                                    {"$set": {"video_id": video_id, "status": "downloaded"}},
                                    upsert=True
                                )
                            except Exception as e:
                                # Don't let a DB error stop the progress UI
                                pass

        ydl_opts['progress_hooks'] = [progress_hook]

        def process_url(url):
            cleaned = clean_tiktok_url(url)
            if not cleaned:
                return (url, False, "SKIP: Empty URL")
            if not cleaned.startswith("http"):
                return (cleaned, False, "SKIP: Invalid URL")
            if not is_probably_tiktok_video_url(cleaned):
                return (cleaned, False, "SKIP: Not a TikTok video URL")
            try:
                # Use a fresh YoutubeDL instance per thread to avoid state conflicts
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(cleaned, download=True)
                    if info:
                        return (cleaned, True, None)
            except Exception as e:
                msg = str(e) if e is not None else "Unknown error"
                lower = msg.lower()
                if "your ip address is blocked" in lower or "page not available" in lower:
                    return (cleaned, False, f"SKIP: {msg}")
                if isinstance(e, IndexError) or "list index out of range" in lower:
                    fallback = with_tiktok_query_params(cleaned, {"is_copy_url": "1", "is_from_webapp": "v1", "lang": "en"})
                    try:
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            info = ydl.extract_info(fallback, download=True)
                            if info:
                                return (fallback, True, None)
                    except Exception as e2:
                        msg2 = str(e2) if e2 is not None else "Unknown error"
                        return (cleaned, False, f"SKIP: {msg2}")
                return (cleaned, False, msg)
            return (cleaned, False, "SKIP: Unavailable/blocked (no info)")

        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_downloads) as executor:
            futures = [executor.submit(process_url, url) for url in video_urls]
            for future in concurrent.futures.as_completed(futures):
                url, success, error_msg = future.result()
                if success:
                    success_count += 1
                else:
                    if error_msg and str(error_msg).startswith("SKIP:"):
                        skipped_count += 1
                        with progress_lock:
                            console.print(f"[dim]{error_msg} -> {url}[/dim]")
                    else:
                        error_count += 1
                        if error_msg and "already been downloaded" not in error_msg.lower() and "abort" not in error_msg.lower():
                            with progress_lock:
                                console.print(f"[red]Error downloading {url}: {error_msg}[/red]")
                
                with progress_lock:
                    # Update overall progress
                    progress.update(overall_task, advance=1)

    console.print()
    
    # Final Summary Table
    table = Table(title="Scan & Download Summary", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Total Scanned URLs", str(len(video_urls)))
    table.add_row("Successfully Processed", str(success_count))
    if skipped_count > 0:
        table.add_row("Skipped", f"[yellow]{skipped_count}[/yellow]")
    if error_count > 0:
        table.add_row("Errors", f"[red]{error_count}[/red]")
    
    console.print(table)
    if effective_cookiefile:
        try:
            os.remove(effective_cookiefile)
        except Exception:
            pass

async def main():
    parser = argparse.ArgumentParser(description="TikTok Profile Scanner & Downloader")
    parser.add_argument("url", help="TikTok Profile URL (e.g., https://www.tiktok.com/@username)")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode (default: False)", default=False)
    parser.add_argument("--dry-run", action="store_true", help="Only scan and list videos without downloading")
    parser.add_argument("--force-full-scan", action="store_true", help="Do not stop scanning early even if previously downloaded videos are found", default=False)
    parser.add_argument("--output", default="downloads", help="Output directory for downloads")
    parser.add_argument("--limit", type=int, help="Maximum number of videos to scan and download", default=0)
    parser.add_argument("--browser", choices=["chrome", "firefox", "edge", "opera", "safari", "vivaldi", "brave"], help="Extract cookies from an installed browser instead of using cookies.txt")
    parser.add_argument("--cookies-file", default=None, help="Path to a Netscape-format cookies.txt file for scanning/downloading")
    parser.add_argument("--mongo-uri", default=os.getenv("MONGO_URI"), help="MongoDB Connection String for tracking downloaded videos")
    parser.add_argument("-c", "--concurrent", type=int, default=1, help="Number of concurrent downloads (default: 1)")

    args = parser.parse_args()
    if args.concurrent < 1:
        console.print("[bold red]--concurrent must be >= 1[/bold red]")
        sys.exit(2)

    # Auto-detect headless mode for Linux/Codespaces without DISPLAY
    is_headless = args.headless
    if sys.platform == "linux" and not os.environ.get("DISPLAY") and not is_headless:
        print("No DISPLAY detected. Forcing headless mode.")
        is_headless = True

    cookies_path = args.cookies_file or os.path.join("src", "cookies.txt")
    cookies = []
    
    if os.path.exists(cookies_path):
        print(f"Found cookies file at '{cookies_path}'. Loading...")
        cookies = parse_netscape_cookies(cookies_path)
    else:
        print(f"No cookies file found at '{cookies_path}'. Continuing without cookies.")

    # Normalize input to URL
    profile_url = clean_tiktok_url(args.url)
    if not profile_url.startswith("http"):
        profile_url = f"https://www.tiktok.com/{profile_url}" if profile_url.startswith("@") else f"https://www.tiktok.com/@{profile_url}"
    
    print(f"Target Profile URL: {profile_url}")

    # Extract username for folder creation early
    username = "unknown_user"
    match = re.search(r'@([a-zA-Z0-9_.-]+)', profile_url)
    if match:
        username = match.group(1)
    
    user_output_dir = os.path.join(args.output, username)

    downloader = TikTokAccountDownloader(profile_url, headless=is_headless, cookies=cookies, limit=args.limit, mongo_uri=args.mongo_uri, output_folder=user_output_dir, force_full_scan=args.force_full_scan)
    video_urls = await downloader.scan()
    
    if video_urls:
        full_urls = list(video_urls)
        
        console.print(f"[bold green]Found {len(full_urls)} videos to process.[/bold green]")

        if args.dry_run:
            console.print(f"[yellow]Dry run enabled. Skipping download to '{user_output_dir}'.[/yellow]")
            for url in full_urls:
                print(url)
        else:
            download_videos(
                full_urls, 
                user_output_dir, 
                cookie_file=cookies_path if os.path.exists(cookies_path) else None,
                browser=args.browser,
                mongo_uri=args.mongo_uri,
                concurrent_downloads=args.concurrent
            )
    else:
        console.print("[yellow]No videos found to download.[/yellow]")

if __name__ == "__main__":
    asyncio.run(main())
