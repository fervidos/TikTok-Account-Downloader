<p align="center">
  <img src="https://github.com/fervidos/TikTok-Account-Downloader/raw/main/assets/banner.png" alt="TikTok Account Downloader Banner" width="800"/>
</p>

# TikTok Account Downloader

Archive TikTok profiles with Playwright for scanning and yt-dlp for downloads. The tool supports public profiles, authenticated access through cookies or browser extraction, optional MongoDB tracking, and a small local viewer for browsing saved files.

## What it does

- Scans a full TikTok profile and collects video URLs
- Downloads media with yt-dlp in the best available format
- Supports cookies for private, friends-only, or age-restricted content
- Can skip repeat work with MongoDB-backed tracking
- Includes a FastAPI viewer for local browsing

## Quick start

```bash
git clone https://github.com/fervidos/TikTok-Account-Downloader.git
cd TikTok-Account-Downloader
pip install -r requirements.txt
python -m playwright install chromium
```

Run a first scan:

```bash
python -m tiktok_account_downloader.cli https://www.tiktok.com/@username
```

If installed as a package, you can also use:

```bash
tiktok-account-downloader https://www.tiktok.com/@username
```

## Common usage

Show help:

```bash
tiktok-account-downloader --help
```

Dry run without downloading:

```bash
tiktok-account-downloader @username --dry-run
```

Limit the run size:

```bash
tiktok-account-downloader @username --limit 50
```

Use a custom output folder:

```bash
tiktok-account-downloader @username --output downloads
```

Run with browser cookies:

```bash
tiktok-account-downloader @username --browser chrome
```

Enable MongoDB tracking and two concurrent downloads:

```bash
tiktok-account-downloader @username --mongo-uri mongodb://localhost:27017/tiktok -c 2
```

Run local diagnostics:

```bash
tiktok-account-downloader --doctor
```

By default, downloads are stored under `downloads/<username>`.

## Authenticated access

TikTok often requires authentication for restricted profiles.

Use a Netscape-format cookies file:

```bash
tiktok-account-downloader @username --cookies-file src/cookies.txt
```

The repository includes a sample at `src/cookies.example.txt`.

You can also import cookies directly from an installed browser with `--browser`. Supported values are `chrome`, `firefox`, `edge`, `opera`, `safari`, `vivaldi`, and `brave`.

## Local viewer

Start the bundled viewer:

```bash
python viewer.py
```

Then open `http://127.0.0.1:54321`.

To point the viewer at a different library, set one of these environment variables before starting it:

Windows:

```bash
set TIKTOK_ACCOUNT_DOWNLOADER_KEPT_DIR=C:\Videos
```

Linux or macOS:

```bash
export TIKTOK_ACCOUNT_DOWNLOADER_KEPT_DIR=/path/to/videos
```

The viewer also accepts the legacy `TIKTOK_SCANNER_KEPT_DIR` name.

## Troubleshooting

Missing videos usually means TikTok throttled the session. Try smaller runs, authenticated access, or rerunning later.

If yt-dlp fails, update it:

```bash
pip install -U yt-dlp
```

If Playwright has browser issues, reinstall Chromium:

```bash
python -m playwright install chromium
```

## Legal

Use this tool only where you have the right to access and archive the content. Respect TikTok's terms, copyright, and the content owner's rights.

## Contributing

Pull requests are welcome. Keep changes focused, and include tests where practical.

## License

MIT