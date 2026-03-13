# TikTok Account Downloader

A **TikTok profile scraper + downloader** written in Python.

This tool uses **Playwright** to scan TikTok accounts for video post URLs and **yt-dlp** to download the media in the best available quality. It includes:

- A CLI scanner/downloader (`tiktok-account-downloader`)
- Optional cookie support for private/age-gated profiles
- Optional MongoDB caching to skip already-downloaded videos
- A local FastAPI viewer to browse downloaded videos

---

## ✅ Quick Start (Windows / macOS / Linux)

### 1) Clone the repo

```bash
git clone https://github.com/fervidos/TikTok-Account-Downloader.git
cd TikTok-Account-Downloader
```

### 2) Create a virtual environment & install dependencies

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 3) Install Playwright browser runtime (required)

```bash
python -m playwright install chromium
```

> **Tip:** If you want to use a different browser engine (Firefox / WebKit), run `python -m playwright install firefox` or `python -m playwright install webkit`.

---

## 🛠️ How to Use

### 1) Download videos from a TikTok profile

```bash
python -m tiktok_account_downloader.cli https://www.tiktok.com/@username
```

**Example**

```bash
python -m tiktok_account_downloader.cli https://www.tiktok.com/@kylek9
```

#### Common flags

- `--dry-run` — scan only (no downloads)
- `--limit N` — stop after finding N videos
- `--output <path>` — output directory (defaults to `downloads/`)
- `--cookies-file <path>` — use a Netscape-format cookie file
- `--browser <name>` — load cookies from a local browser (chrome/firefox/edge/brave/opera)
- `--mongo-uri <uri>` — enable MongoDB caching (stores downloaded video IDs)

---

## 🍪 Cookie Support (Recommended)

TikTok often requires login/cookies for age-gated or private content. Two ways to provide cookies:

### Option A) Use a cookies file

1. Export cookies in **Netscape `cookies.txt`** format (e.g. via a browser extension).
2. Place it at `src/cookies.txt` (default) or pass `--cookies-file /path/to/cookies.txt`.

> Example template: `src/cookies.example.txt`

### Option B) Load cookies from a local browser profile

```bash
python -m tiktok_account_downloader.cli --browser chrome https://www.tiktok.com/@username
```

Supported browser names: `chrome`, `firefox`, `edge`, `brave`, `opera`.

---

## 🧠 Caching with MongoDB (Optional)

If you run the scraper frequently, enabling caching avoids re-downloading the same videos.

1) Run a MongoDB instance (local or cloud).
2) Set `MONGO_URI` via env var or `.env`.

```bash
set MONGO_URI="mongodb+srv://<user>:<pw>@<cluster>/tiktok_account_downloader"
# or on macOS/Linux
export MONGO_URI="mongodb+srv://<user>:<pw>@<cluster>/tiktok_account_downloader"
```

Then run the scanner normally; it will store downloaded video IDs and skip duplicates.

---

## 🖥️ Viewer: Browse Downloaded Videos

Run the built-in FastAPI viewer:

```bash
python viewer.py
```

Then open in your browser:

```
http://127.0.0.1:8000
```

Default directory served is `downloads/_kept/`. To change it:

```bash
set TIKTOK_SCANNER_KEPT_DIR=path\to\videos     # Windows
export TIKTOK_SCANNER_KEPT_DIR=path/to/videos      # macOS/Linux
python viewer.py
```

---

## 🧪 Development

Install and develop in editable mode:

```bash
pip install -e .
```

Then run the CLI command directly:

```bash
tiktok-account-downloader https://www.tiktok.com/@username
```

---

## 🚀 Tips & Troubleshooting

- **Playwright errors**: Ensure the browser runtime is installed (`python -m playwright install chromium`).
- **Login required / missing videos**: Provide valid cookies or use `--browser` to load local browser cookies.
- **Slow scraping**: TikTok may throttle requests; use a higher `--limit` carefully and avoid rapid repeated runs.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
