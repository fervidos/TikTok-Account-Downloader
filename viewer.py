from pathlib import Path
from typing import List
import os
import random
from fastapi import FastAPI
from fastapi import Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="TikTok Account Downloader Viewer")

APP_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = APP_DIR / "templates"
DEFAULT_KEPT_DIR = APP_DIR / "downloads" / "_kept"

# allow overriding via environment variable (new name + legacy name)
_kept_override = os.getenv("TIKTOK_ACCOUNT_DOWNLOADER_KEPT_DIR") or os.getenv("TIKTOK_SCANNER_KEPT_DIR") or os.getenv("TIKTOKSCANNER_KEPT_DIR")
KEPT_DIR = Path(_kept_override) if _kept_override else DEFAULT_KEPT_DIR
KEPT_DIR = KEPT_DIR.expanduser().resolve()

KEPT_DIR.mkdir(parents=True, exist_ok=True)

# mount directories for static serving
app.mount("/videos", StaticFiles(directory=str(KEPT_DIR)), name="videos")
app.mount("/static", StaticFiles(directory=str(TEMPLATES_DIR)), name="static")


class VideoResponse(BaseModel):
    videos: List[str]


class CreatorsResponse(BaseModel):
    creators: List[str]


def _collect_media_files() -> List[str]:
    """Return all relative media file paths under KEPT_DIR."""
    media_files: List[str] = []
    media_extensions = (".mp4", ".webm", ".mkv", ".jpg", ".jpeg", ".png", ".gif")

    for root, _, files in os.walk(str(KEPT_DIR)):
        for fname in files:
            if fname.lower().endswith(media_extensions):
                rel = Path(root).relative_to(KEPT_DIR) / fname
                media_files.append(str(rel).replace("\\", "/"))

    try:
        random.shuffle(media_files)
    except Exception:
        pass

    return media_files


@app.get("/", response_class=HTMLResponse)
async def get_viewer() -> HTMLResponse:
    """Return the HTML entry point for the vertical viewer."""
    template_path = TEMPLATES_DIR / "index.html"
    if not template_path.exists():
        return HTMLResponse(content="<h1>Error: templates/index.html not found.</h1>", status_code=404)
    return HTMLResponse(content=template_path.read_text(encoding="utf-8"))


@app.get("/api/videos", response_model=VideoResponse)
async def list_videos(
    creator: str = Query(default="", description="Filter by creator folder"),
    q: str = Query(default="", description="Case-insensitive filename/path search"),
) -> VideoResponse:
    """Return a list of relative paths for all supported video files under ``KEPT_DIR``."""
    video_files = _collect_media_files()

    normalized_creator = creator.strip().lower()
    if normalized_creator:
        video_files = [
            p for p in video_files
            if p.split("/", 1)[0].lower() == normalized_creator
        ]

    normalized_query = q.strip().lower()
    if normalized_query:
        video_files = [p for p in video_files if normalized_query in p.lower()]

    return VideoResponse(videos=video_files)


@app.get("/api/creators", response_model=CreatorsResponse)
async def list_creators() -> CreatorsResponse:
    """Return unique creator folders inferred from media relative paths."""
    creators = sorted({p.split("/", 1)[0] for p in _collect_media_files() if "/" in p})
    return CreatorsResponse(creators=creators)


if __name__ == "__main__":
    # Run as a standalone server for local viewing.
    # Requires: fastapi, uvicorn
    import uvicorn

    uvicorn.run("viewer:app", host="127.0.0.1", port=54321, reload=True)
