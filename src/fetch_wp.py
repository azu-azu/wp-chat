import os, json, time, math, html, hashlib
import requests
from urllib.parse import urljoin
from dotenv import load_dotenv

load_dotenv()
BASE = os.getenv("WP_BASE_URL").rstrip("/")
OUT  = "data/raw/posts.jsonl"
STATE_DIR = ".state"
PER_PAGE = 100
UA = {"User-Agent": "wp-chatbot/0.1 (+local)"}

def _retry_get(url, headers, timeout=30, max_attempts=3):
    for i in range(max_attempts):
        r = requests.get(url, headers=headers, timeout=timeout)
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(0.5 * (2 ** i))
            continue
        return r
    r.raise_for_status()
    return r

if __name__ == "__main__":
    os.makedirs("data/raw", exist_ok=True)
    os.makedirs(STATE_DIR, exist_ok=True)

    cond = {}
    lm_path = os.path.join(STATE_DIR, "last_modified.txt")
    et_path = os.path.join(STATE_DIR, "etag.txt")
    if os.path.exists(lm_path):
        cond["If-Modified-Since"] = open(lm_path).read().strip()
    if os.path.exists(et_path):
        cond["If-None-Match"] = open(et_path).read().strip()

    page = 1
    wrote = 0
    with open(OUT, "w", encoding="utf-8") as f:
        while True:
            url = urljoin(BASE, f"/wp-json/wp/v2/posts?per_page={PER_PAGE}&page={page}")
            r = _retry_get(url, {**UA, **cond})
            if r.status_code == 304:
                break
            if r.status_code in (400, 404):
                break
            r.raise_for_status()
            items = r.json()
            if not items:
                break
            for it in items:
                f.write(json.dumps(it, ensure_ascii=False) + "\n")
                wrote += 1

            total_pages = int(r.headers.get("X-WP-TotalPages", page))
            if lm := r.headers.get("Last-Modified"):
                open(lm_path, "w").write(lm)
            if et := r.headers.get("ETag"):
                open(et_path, "w").write(et)

            if page >= total_pages:
                break
            page += 1
            time.sleep(0.2)

    print(f"✅ fetched posts: {wrote}, saved -> {OUT}")
