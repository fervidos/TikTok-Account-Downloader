<p align="center">
  <img src="https://github.com/fervidos/TikTok-Account-Downloader/raw/main/assets/banner.png" alt="TikTok Account Downloader Banner" width="800"/>
</p>

<p align="center">
  <a href="https://github.com/fervidos/TikTok-Account-Downloader/stargazers">
    <img src="https://img.shields.io/github/stars/fervidos/TikTok-Account-Downloader?style=for-the-badge&color=ff0050"/>
  </a>
  <a href="https://github.com/fervidos/TikTok-Account-Downloader/forks">
    <img src="https://img.shields.io/github/forks/fervidos/TikTok-Account-Downloader?style=for-the-badge&color=ff7300"/>
  </a>
  <a href="https://github.com/fervidos/TikTok-Account-Downloader/issues">
    <img src="https://img.shields.io/github/issues/fervidos/TikTok-Account-Downloader?style=for-the-badge&color=00aaff"/>
  </a>
</p>

<p align="center">
  <img src="https://github.com/fervidos/TikTok-Account-Downloader/actions/workflows/python-package.yml/badge.svg"/>
  <img src="https://img.shields.io/badge/python-3.10+-blue?style=for-the-badge&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge"/>
</p>

---

# TikTok Account Downloader

> **Archive entire TikTok profiles — including private, age-restricted, and locked content.**

A powerful archiving tool built with **Playwright + yt-dlp** that automatically scrolls profiles, collects every video, and downloads them in the **highest available quality**.

Perfect for researchers, archivists, or anyone who wants to keep backups of TikTok accounts.

---

# Table of Contents

- Features
- Quick Start
- Usage
- Cookies (Private Content)
- Local Video Browser
- FAQ
- Contributing
- License

---

# Features

**Full Profile Archiving**
- Automatically scrolls TikTok profiles
- Collects every video on the account

**Best Quality Downloads**
- Uses `yt-dlp`
- Downloads **bestvideo + bestaudio**

**Private / Restricted Content**
- Supports cookies from browsers
- Works with:
  - private accounts
  - friends-only videos
  - age-restricted content

**Smart Caching (Optional)**
- MongoDB support
- Skips already-downloaded videos

**Built-in Video Viewer**
- Local web interface for browsing downloaded videos

**Safe Testing**
- `--dry-run` preview mode
- Download limits

**Actively Maintained**
- Uses Playwright to adapt to TikTok layout changes

---

# Quick Start (3 minutes)

## 1. Clone the repository

```bash
git clone https://github.com/fervidos/TikTok-Account-Downloader.git
cd TikTok-Account-Downloader
```

## 2. Create virtual environment

```bash
python -m venv .venv
```

Activate it:

**Windows**

```bash
.venv\Scripts\activate
```

**Linux / macOS**

```bash
source .venv/bin/activate
```

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

## 4. Install Playwright browser

```bash
python -m playwright install chromium
```

## 5. Run the downloader

```bash
python -m tiktok_account_downloader.cli https://www.tiktok.com/@username
```

Or if installed as a package:

```bash
tiktok-account-downloader https://www.tiktok.com/@username
```

Videos will appear in:

```
downloads/_kept/
```

Test without downloading:

```bash
--dry-run
```

---

# Usage

View all options:

```bash
tiktok-account-downloader --help
```

## Popular Flags

| Flag | Description |
|-----|-------------|
| `--dry-run` | Scan profile without downloading |
| `--limit N` | Stop after N videos |
| `--output DIR` | Custom download directory |
| `--cookies-file FILE` | Use Netscape cookies file |
| `--browser chrome` | Load cookies from browser |
| `--mongo-uri URI` | Enable MongoDB caching |
| `--headless false` | Show browser window |
| `--slow-mo 300` | Delay actions (helps avoid rate limits) |

Example:

```bash
tiktok-account-downloader https://www.tiktok.com/@privateacc \
  --cookies-file cookies.txt \
  --limit 200 \
  --mongo-uri mongodb://localhost:27017/tiktok \
  --output backups/privateacc
```

---

# Cookies (Private / Restricted Videos)

TikTok requires authentication for many accounts.

## Option 1 — cookies.txt (recommended)

1. Install a browser extension such as:
   - Cookie Editor
   - EditThisCookie

2. Export cookies from:

```
https://www.tiktok.com
```

3. Save them as:

```
cookies.txt
```

4. Run:

```bash
tiktok-account-downloader --cookies-file cookies.txt https://www.tiktok.com/@username
```

Example template:

```
cookies.example.txt
```

---

## Option 2 — Load directly from browser

```bash
tiktok-account-downloader --browser chrome https://www.tiktok.com/@username
```

Supported browsers:

- Chrome
- Firefox
- Edge
- Brave
- Opera

---

# Local Video Browser

After downloading videos you can launch a **simple web viewer**.

```bash
python viewer.py
```

Open in browser:

```
http://127.0.0.1:8000
```

Change the video directory:

Linux / macOS:

```bash
export TIKTOK_SCANNER_KEPT_DIR=/path/to/videos
```

Windows:

```bash
set TIKTOK_SCANNER_KEPT_DIR=C:\Videos
```

Then run again:

```bash
python viewer.py
```

---

# FAQ

### Videos are missing

TikTok rate limits aggressive scrolling.

Try:

```bash
--slow-mo 500 --headless false
```

Or split downloads into multiple runs.

---

### yt-dlp fails or quality is low

Update yt-dlp:

```bash
pip install -U yt-dlp
```

---

### Playwright crashes

Reinstall browsers:

```bash
python -m playwright install --with-deps chromium
```

---

### MongoDB caching not working

Check that your `MONGO_URI` contains the correct credentials and database name.

---

# Legal Notice

This tool is intended for **personal archiving and research purposes**.

Always respect:

- TikTok Terms of Service
- Copyright laws
- Content ownership

---

# Contributing

Pull requests are welcome.

1. Fork the repo  
2. Clone your fork  
3. Install dev dependencies  

```bash
pip install -e ".[dev]"
```

4. Make changes  
5. Add tests if possible (`pytest`)  
6. Submit a pull request  

### Suggested Improvements

- Resume interrupted downloads
- Support photo/slideshow posts
- Better progress statistics
- Docker support
- Single-file executable

---

# License

MIT License © 2026 fervidos

---

<p align="center">
Made with ❤️ for archivists, researchers, and data hoarders.
</p>

<p align="center">
⭐ Star the project if it saved you time.
</p>