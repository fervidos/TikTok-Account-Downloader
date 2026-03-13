# TikTok Account Downloader

[![Build](https://github.com/fervidos/TikTok-Account-Downloader/actions/workflows/python-package.yml/badge.svg)](https://github.com/fervidos/TikTok-Account-Downloader/actions)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

A simple tool that **scrapes a TikTok profile** and **downloads all videos** found on that profile.

- Downloads the best-quality video + audio using **yt-dlp**
- Uses **Playwright** to scan the profile page for TikTok post URLs
- Supports **cookies** so it can download private / age-locked content
- Optional **MongoDB caching** to avoid re-downloading the same videos
- Includes a small **local web viewer** to browse downloaded videos

---

## ✅ What this project does (in plain English)

1. You tell it a TikTok profile URL (e.g. `https://www.tiktok.com/@username`).
2. It visits the profile page in a browser (Playwright) and finds all video post links.
3. It hands those links to `yt-dlp` to download the video files.
4. It saves videos into `downloads/_kept/` by default.

---

## 🧩 How to run it (step-by-step)

### 1) Download the code

```bash
git clone https://github.com/fervidos/TikTok-Account-Downloader.git
cd TikTok-Account-Downloader
```

### 2) Install Python dependencies

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 3) Install the browser runtime Playwright needs

```bash
python -m playwright install chromium
```

> ✅ If you want Firefox or WebKit instead, run:
> - `python -m playwright install firefox`
> - `python -m playwright install webkit`

---

## ▶️ Run the downloader (the simplest way)

```bash
python -m tiktok_account_downloader.cli https://www.tiktok.com/@username
```

### What is `-m tiktok_account_downloader.cli`?

`python -m <module>` tells Python to run a module as a script.

- `tiktok_account_downloader.cli` is the file `src/tiktok_account_downloader/cli.py`.
- The `cli.py` file contains the command-line interface (the part that reads flags and starts the download).

> ✅ If you installed the package (`pip install -e .`), you can also run:
> ```bash
tiktok-account-downloader https://www.tiktok.com/@username
> ```

---

## 🔧 Common options (flags)

| Flag | What it does |
|------|--------------|
| `--dry-run` | Scan the profile but don’t download anything |
| `--limit N` | Stop after finding N videos |
| `--output <path>` | Save downloads to a custom folder |
| `--cookies-file <path>` | Load cookies from a cookies.txt file |
| `--browser <name>` | Load cookies from a local browser (chrome/firefox/edge/brave/opera) |
| `--mongo-uri <uri>` | Enable MongoDB caching (skips already-downloaded videos) |

---

## 🍪 Cookies (needed for private / restricted content)

TikTok will block access to some videos unless you are logged in. This tool can use your browser cookies to make it look like you’re logged in.

### Option A) Use a cookies file (recommended)

1. Export cookies in **Netscape `cookies.txt`** format (browser extension or tool).
2. Put the file at:
   - `src/cookies.txt` (default)
   - or use `--cookies-file path/to/cookies.txt`

> Example template: `src/cookies.example.txt`

### Option B) Load cookies from a browser you already use

```bash
python -m tiktok_account_downloader.cli --browser chrome https://www.tiktok.com/@username
```

Supported browser names: `chrome`, `firefox`, `edge`, `brave`, `opera`.

---

## 🧠 Optional: Cache downloaded videos with MongoDB

If you run this tool repeatedly, MongoDB can keep track of what’s already downloaded so it doesn’t download the same video twice.

1) Run MongoDB (local or cloud).
2) Set `MONGO_URI` in your environment (or `.env` file):

```bash
set MONGO_URI="mongodb+srv://<user>:<pw>@<cluster>/tiktok_account_downloader"  # Windows
export MONGO_URI="mongodb+srv://<user>:<pw>@<cluster>/tiktok_account_downloader"  # macOS/Linux
```

Then run the downloader as normal.

---

## 🖥️ Browse downloaded videos (viewer)

Use the built-in viewer to open a web page and play the downloaded files.

```bash
python viewer.py
```

Open in your browser:

```
http://127.0.0.1:8000
```

Default folder: `downloads/_kept/`

To change the folder:

```bash
set TIKTOK_SCANNER_KEPT_DIR=path\to\videos     # Windows
export TIKTOK_SCANNER_KEPT_DIR=path/to/videos      # macOS/Linux
python viewer.py
```

---

## 🧪 Development (edit the code)

Install the package in editable mode:

```bash
pip install -e .
```

Then run the command:

```bash
tiktok-account-downloader https://www.tiktok.com/@username
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
