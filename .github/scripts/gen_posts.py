#!/usr/bin/env python3
"""
Step 2: Generate weekly content batch.

CLIENT env var selects REDWOLF or ASIS.
"""

import csv
import io
import json
import os
import re
import requests
from datetime import date, timedelta
from pathlib import Path


CLIENT = os.environ.get("CLIENT", "REDWOLF").upper()

QUARTER    = os.environ.get("QUARTER", "2026Q4")
TABLE_PATH = f"XLS/{CLIENT}/XLS-2026Q4.xls"
TREE_PATH  = f"JSON/{CLIENT}/JSON-2026Q4.json"
JSONL_DIR  = Path(f"JSONL/{CLIENT}")
SKILL_PATH = Path(f"{CLIENT}/.claude/skills/generate-post/SKILL.md")

SLUG_ORDER = {
    "REDWOLF": ["REDWOLF", "NZSA", "ASIS", "NZPOLICE", "JOHNSON", "GALLAGHER", "INNERRANGE", "BOSCH", "ICT", "JACQUES"],
    "ASIS":    ["ASISNZ",  "NZSA", "ASIS", "NZPOLICE", "JOHNSON", "GALLAGHER", "INNERRANGE", "BOSCH", "ICT", "JACQUES"],
}[CLIENT]

PILLARS = ["SERVICES", "INDUSTRY", "AUTHORITY", "PEOPLE", "TRUST", "ENGAGEMENT"]


def week_num() -> int:
    env = os.environ.get("CONTENT_WEEK", "")
    return int(env) if env else date.today().isocalendar()[1]


def parse_latest_jsonl_entry(slug: str) -> dict | None:
    path = JSONL_DIR / f"{slug}.jsonl"
    if not path.exists():
        return None
    for line in reversed(path.read_text(encoding="utf-8").splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    return None


def load_connections(window_start: date, window_end: date) -> list[dict]:
    connections = []
    for slug in SLUG_ORDER:
        data = parse_latest_jsonl_entry(slug)
        if not data:
            continue
        recent = [
            p for p in data.get("recentPosts", [])
            if window_start <= date.fromisoformat(p["date"]) <= window_end
        ]
        connections.append({
            "slug": slug,
            "companyName": data.get("companyName", slug),
            "url": data.get("url", ""),
            "bio": data.get("bio", ""),
            "fetchedAt": data.get("fetchedAt", ""),
            "recentPosts": recent,
        })
    return connections


def load_csv() -> tuple[list[str], list[dict]]:
    with open(TABLE_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = [h.strip() for h in reader.fieldnames]
        rows = [{(k or "").strip(): v for k, v in r.items()} for r in reader]
    return fieldnames, rows


def used_subtypes(rows: list[dict]) -> list[dict]:
    return [
        {"topic": r["topic"], "type": r["type"], "subtopic": r["subtopic"]}
        for r in rows
        if r.get("topic") and r.get("type") and r.get("subtopic")
    ]


def next_item_num(rows: list[dict]) -> int:
    nums = [
        int(r["item"].replace("post-", ""))
        for r in rows
        if re.fullmatch(r"post-\d+", r.get("item", ""))
    ]
    return (max(nums) if nums else 0) + 1


def load_system_prompt() -> str:
    text = SKILL_PATH.read_text(encoding="utf-8")
    if text.startswith("---"):
        text = text.split("---", 2)[2]
    return text.strip()


def build_payload(week: int, rows: list[dict], tree: dict) -> dict:
    today = date.today()
    window_start = today - timedelta(days=7)
    return {
        "systemPrompt": load_system_prompt(),
        "quarter": QUARTER,
        "week": week,
        "today": str(today),
        "window": f"{window_start} to {today}",
        "nextItemStart": next_item_num(rows),
        "usedSubtypes": used_subtypes(rows),
        "tree": tree,
        "connections": load_connections(window_start, today),
    }


def call_mac_mini(payload: dict) -> list[dict]:
    url     = os.environ["GENERATE_CONTENT_URL"].rstrip("/") + "/generate-content"
    headers = {
        "CF-Access-Client-Id":     os.environ["CF_ACCESS_CLIENT_ID"],
        "CF-Access-Client-Secret": os.environ["CF_ACCESS_CLIENT_SECRET"],
        "X-Listener-Secret":       os.environ["LISTENER_SHARED_SECRET"],
        "Content-Type":            "application/json",
    }
    print(f"[{CLIENT}] Calling Mac mini at {url} …")
    resp = requests.post(url, headers=headers, json=payload, timeout=180)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "posts" in data:
        return data["posts"]
    raise ValueError(f"Unexpected response shape: {str(data)[:200]}")


DOUBLE_HYPHEN = re.compile(r"--")


def validate_posts(posts: list[dict]) -> None:
    if len(posts) != 6:
        raise ValueError(f"Expected 6 posts, got {len(posts)}")
    topics = sorted(p.get("topic", "") for p in posts)
    if topics != sorted(PILLARS):
        raise ValueError(f"Posts must cover all 6 pillars. Got: {topics}")
    for p in posts:
        for field in ("title", "description"):
            val = p.get(field, "")
            if DOUBLE_HYPHEN.search(val):
                raise ValueError(
                    f"Double hyphen in {p.get('topic')} / {field}: {val[:80]}"
                )


def serialize_csv(rows: list[dict], fieldnames: list[str]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def append_posts(posts: list[dict], existing_rows: list[dict],
                 fieldnames: list[str], week: int) -> list[dict]:
    today = str(date.today())
    item_num = next_item_num(existing_rows)
    new_rows = []
    for post in posts:
        row = {h: "" for h in fieldnames}
        row.update({
            "week": str(week),
            "item": f"post-{item_num:03d}",
            "topic": post.get("topic", ""),
            "type": post.get("type", ""),
            "subtopic": post.get("subtopic", ""),
            "title": post.get("title", ""),
            "description": post.get("description", ""),
            "media": post.get("media", ""),
            "media-type": post.get("media-type", ""),
            "media URL": "",
            "linkedin account tag": post.get("linkedin account tag", ""),
            "hashtag": post.get("hashtag", ""),
            "score": str(post.get("score", "")),
            "createdat": today,
            "updatedat": today,
            "feedback": "",
            "feedback-comment": "",
            "sources": post.get("sources", ""),
        })
        new_rows.append(row)
        item_num += 1
    return new_rows


def main() -> None:
    week = week_num()
    fieldnames, existing_rows = load_csv()
    if os.environ.get("CONTENT_REPLACE") == "true":
        kept = [r for r in existing_rows if r.get("week") != str(week)]
        print(f"[{CLIENT}] Replacing week {week}: dropping {len(existing_rows) - len(kept)} existing rows")
        existing_rows = kept
    tree = json.loads(Path(TREE_PATH).read_text(encoding="utf-8"))

    payload = build_payload(week, existing_rows, tree)
    posts   = call_mac_mini(payload)

    validate_posts(posts)

    new_rows = append_posts(posts, existing_rows, fieldnames, week)
    all_rows = existing_rows + new_rows

    with open(TABLE_PATH, "w", newline="", encoding="utf-8") as f:
        f.write(serialize_csv(all_rows, fieldnames))

    print(f"[{CLIENT}] Added {len(new_rows)} posts for week {week}:")
    for r in new_rows:
        print(f"  {r['item']} | {r['topic']} / {r['type']} / {r['subtopic']}")


if __name__ == "__main__":
    main()
