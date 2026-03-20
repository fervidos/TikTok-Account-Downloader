import contextlib
import io
import yt_dlp
import sys
import os
from src.tiktok_account_downloader.utils import parse_netscape_cookies, write_netscape_cookie_file

url = "https://www.tiktok.com/@fckanyoneexceptyou/video/7616202319578877205"

class _RichYtDlpLogger:
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg):
        print("LOGGER ERROR:", msg)
    def info(self, msg): pass

def test():
    cookie_file = "src/cookies.txt"
    effective_cookiefile = None
    if os.path.exists(cookie_file):
        parsed = parse_netscape_cookies(cookie_file)
        if parsed:
            effective_cookiefile = write_netscape_cookie_file(parsed)

    ydl_opts = {
        'outtmpl': os.path.join("downloads", '%(uploader)s_%(upload_date)s_%(id)s_%(title).50s.%(ext)s'),
        'ignoreerrors': True,
        'format': 'bestvideo+bestaudio/best',
        'quiet': False,
        'no_warnings': False,
        'logger': _RichYtDlpLogger(),
        'retries': 3,
        'fragment_retries': 3,
        'extractor_retries': 3,
        'socket_timeout': 30,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36',
            'Referer': 'https://www.tiktok.com/',
        },
        'noplaylist': True,
        'extractor_args': {
            'tiktok': {
                'app_info': ['musical_ly/35.1.3/2023501030/0'],
            }
        },
    }
    
    if effective_cookiefile:
        ydl_opts['cookiefile'] = effective_cookiefile
        print(f"Using cookie file: {effective_cookiefile}")

    stderr_buffer = io.StringIO()
    try:
        with contextlib.redirect_stderr(stderr_buffer):
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
            if info:
                print("SUCCESS")
                return
            print("INFO WAS FALSY")
    except Exception as e:
        print("CAUGHT EXCEPTION:", str(e))
        print("STDERR BUFFER:", stderr_buffer.getvalue())

    if effective_cookiefile:
        try:
            os.remove(effective_cookiefile)
        except:
            pass

test()
