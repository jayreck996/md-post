#!/usr/bin/env python3
"""Step 2D: generate weekly media via Mac mini.

Reads all config from environment variables set by the generate-media workflow,
which loads them from the client's pipeline YML via pipeline_config.py.

Supports two output modes:
  submodule  — writes to IMG/{CLIENT}/ and PDF/{CLIENT}/ submodule dirs
  repo_local — writes to MAY/media/2026Q3/ (repo-local, served via Pages)
"""

import base64
import csv
import io
import os
import time
import requests
from datetime import date, datetime
from pathlib import Path

MEDIA_MODE = os.environ.get("MEDIA_MODE", "submodule")
TABLE_PATH = os.environ.get("XLS_PATH", "")
LOGO_PATH  = Path(os.environ.get("LOGO_PATH", ""))
LOGO_MIME  = os.environ.get("LOGO_MIME", "image/jpeg")
SKILL_PATH = Path(os.environ.get("SKILL_PATH", ""))

# submodule mode
IMG_DIR  = Path(os.environ.get("IMG_DIR", ""))
PDF_DIR  = Path(os.environ.get("PDF_DIR", ""))
IMG_BASE = os.environ.get("IMG_BASE", "")
PDF_BASE = os.environ.get("PDF_BASE", "")

# repo_local mode
MEDIA_DIR  = Path(os.environ.get("MEDIA_DIR", ""))
PAGES_BASE = os.environ.get("PAGES_BASE", "")

GENERATABLE = {"png", "gif", "pdf"}


def week_num() -> int:
    env = os.environ.get("CONTENT_WEEK", "")
    return int(env) if env else date.today().isocalendar()[1]


def load_csv() -> tuple[list[str], list[dict]]:
    with open(TABLE_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = [h.strip() for h in reader.fieldnames]
        rows = [{(k or "").strip(): v for k, v in r.items()} for r in reader]
    return fieldnames, rows


def load_system_prompt() -> str:
    text = SKILL_PATH.read_text(encoding="utf-8")
    if text.startswith("---"):
        text = text.split("---", 2)[2]
    return text.strip()


def _cf_headers() -> dict:
    return {
        "CF-Access-Client-Id":     os.environ.get("CF_ACCESS_CLIENT_ID", ""),
        "CF-Access-Client-Secret": os.environ.get("CF_ACCESS_CLIENT_SECRET", ""),
        "X-Listener-Secret":       os.environ["LISTENER_SHARED_SECRET"],
    }


def call_mac_mini_one(post: dict, system_prompt: str, logob64: str,
                      week: int, logomime: str) -> list[dict]:
    base_url = os.environ["GENERATE_CONTENT_URL"].rstrip("/")
    headers  = {**_cf_headers(), "Content-Type": "application/json"}
    payload  = {
        "systemPrompt": system_prompt,
        "logob64":      logob64,
        "logomime":     logomime,
        "week":         week,
        "posts":        [post],
    }
    print(f"  {post['item']} → {base_url}/generate-media …")
    resp = requests.post(base_url + "/generate-media", headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        print(f"  {post['item']} error: {data['error']}")
        return []

    job_id     = data["job_id"]
    status_url = f"{base_url}/generate-media-status/{job_id}"
    poll_hdrs  = _cf_headers()
    mtype      = post.get("media-type", "png").lower()
    max_calls  = 5 if mtype == "pdf" else (3 if mtype == "gif" else 1)
    deadline   = time.time() + (max_calls * 450) + 300

    print(f"  {post['item']} job {job_id} — polling (deadline {max_calls*450+300}s) …")
    while time.time() < deadline:
        time.sleep(15)
        r = requests.get(status_url, headers=poll_hdrs, timeout=30)
        if r.status_code == 404:
            print(f"  {post['item']} job lost (listener restarted?) — skipping")
            return []
        r.raise_for_status()
        state = r.json()
        if state["status"] == "done":
            files = state.get("files", [])
            print(f"  {post['item']} done ({len(files)} file(s))")
            return files
        if state["status"] == "error":
            print(f"  {post['item']} Mac mini error: {state.get('error', 'unknown')}")
            return []
        print(f"  {post['item']} pending …")

    print(f"  {post['item']} timed out")
    return []


def output_path(suffix: str) -> tuple[Path, str]:
    ts   = datetime.now()
    name = f"{ts.strftime('%Y%m%d%H%M%S')}{ts.strftime('%f')[:3]}{suffix}"
    if MEDIA_MODE == "repo_local":
        return MEDIA_DIR / name, f"{PAGES_BASE}/{name}"
    if suffix == ".pdf":
        return PDF_DIR / name, f"{PDF_BASE}/{name}"
    return IMG_DIR / name, f"{IMG_BASE}/{name}"


def main() -> None:
    week = week_num()
    fieldnames, rows = load_csv()

    targets = [
        r for r in rows
        if r.get("week") == str(week)
        and not r.get("media URL", "").strip()
        and r.get("media-type", "").strip().lower() in GENERATABLE
    ]
    skipped = [
        r for r in rows
        if r.get("week") == str(week)
        and not r.get("media URL", "").strip()
        and r.get("media-type", "").strip().lower() not in GENERATABLE
    ]

    for r in skipped:
        print(f"  skip {r['item']} ({r['media-type']}) — requires real asset")

    if not targets:
        print(f"No generatable posts with empty media URL for week {week}.")
        return

    client = os.environ.get("CLIENT", "?")
    print(f"[{client}] Generating media for {len(targets)} post(s) (week {week}, mode={MEDIA_MODE}):")
    for t in targets:
        print(f"  {t['item']} | {t['media-type']} | {t['media'][:60]}")

    system_prompt = load_system_prompt()
    logob64       = base64.b64encode(LOGO_PATH.read_bytes()).decode()

    if MEDIA_MODE == "repo_local":
        MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    else:
        IMG_DIR.mkdir(parents=True, exist_ok=True)
        PDF_DIR.mkdir(parents=True, exist_ok=True)

    all_files: list[dict] = []
    for post in targets:
        all_files.extend(call_mac_mini_one(post, system_prompt, logob64, week, LOGO_MIME))

    if not all_files:
        print("No files returned from Mac mini.")
        return

    url_map: dict[str, str] = {}
    for f in all_files:
        suffix = Path(f["path"]).suffix.lower()
        out, url = output_path(suffix)
        out.write_bytes(base64.b64decode(f["content_b64"]))
        print(f"  wrote {out} ({out.stat().st_size // 1024} KB)")
        item = f["item"]
        if item not in url_map or suffix in (".pdf", ".gif"):
            url_map[item] = url

    for row in rows:
        if row.get("item") in url_map:
            row["media URL"] = url_map[row["item"]]

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
    writer.writeheader()
    writer.writerows(rows)
    with open(TABLE_PATH, "w", newline="", encoding="utf-8") as f:
        f.write(buf.getvalue())

    print(f"[{client}] Updated {len(url_map)} media URL(s) in {TABLE_PATH}.")


if __name__ == "__main__":
    main()
