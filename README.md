# TikTok Account Downloader

A **TikTok account downloader** written in Python.

This project uses **Playwright** to scrape TikTok profiles for video URLs and **yt-dlp** to download the videos with a polished progress UI (Rich). It also includes an optional **FastAPI viewer** for locally browsing downloaded videos.

---

## 🚀 Key Features

- Scan a TikTok profile for video URLs (no API required)
- Download TikTok videos using `yt-dlp` (best audio + video)
- Optional MongoDB caching to avoid re-downloading videos
- Cookie support (Netscape cookies file or browser cookies) to handle age-restricted/private profiles
- Local vertical web viewer (FastAPI + StaticFiles) for quick review

---

## ✅ Quick Start

### 1) Clone the repo

```bash
git clone https://github.com/fervidos/TikTok-Account-Downloader.git
cd TikTok-Account-Downloader
```

### 2) Create a virtual environment & install dependencies

```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate    # Windows

pip install -r requirements.txt
```

> ⚠️ **Playwright requires a browser runtime**

```bash
python -m playwright install chromium
```

### 3) Provide cookies (optional but recommended)

- If you have a `cookies.txt` (Netscape format), place it at:

  - `src/cookies.txt` (recommended)

- Or use a local browser to extract cookies with the `--browser` flag (Chrome/Firefox/Edge/Brave/Opera/Safari).

> 📌 Example cookies template: `src/cookies.example.txt`

### 4) Run the scanner

```bash
python -m tiktok_account_downloader.cli https://www.tiktok.com/@username
```

#### Useful flags

- `--dry-run` — scan but do not download
- `--limit N` — stop after finding N videos
- `--output path` — choose output directory
- `--browser chrome` — pull cookies from a local browser profile
- `--cookies-file path` — specify a custom cookies file
- `--mongo-uri <uri>` — use MongoDB for caching downloaded video IDs

---

## 🖥 Viewer (optional)

A simple local web app to browse downloaded media.

```bash
python viewer.py
```

Then open: http://127.0.0.1:8000

By default this serves files from `downloads/_kept/`, but you can override the directory via:

```bash
set TIKTOK_SCANNER_KEPT_DIR=path\\to\\videos     # Windows
export TIKTOK_SCANNER_KEPT_DIR=path/to/videos      # macOS/Linux
python viewer.py
```

---

## 🧩 Configuration

### Environment variables

Create a `.env` file (not committed) with values such as:

```ini
MONGO_URI="mongodb+srv://<user>:<pw>@<cluster>/tiktok_account_downloader"
```

> Use `.env.example` as a template.

---

## 🧪 Development

Install the package in editable mode:

```bash
pip install -e .
```

Then you can run the CLI as:

```bash
tiktok-account-downloader https://www.tiktok.com/@username
```

---

## 🧾 License

This project is licensed under the [MIT License](LICENSE).
