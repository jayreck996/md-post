#!/usr/bin/env python3
"""
Called by .github/workflows/fetch-linkedin.yml (weekly cron).

Reads the configured strategy tree's connections{}, maps each to its fixed
slug, and calls the client listener once per connection, appending each
successful response to the configured LinkedIn cache directory.

CLIENT env var selects REDWOLF or ASIS.
"""

import json
import os
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path

CLIENT    = os.environ.get("CLIENT", "REDWOLF").upper()
TREE_FILE = Path(os.environ["TREE_PATH"])
JSONL_DIR = Path(os.environ["LINKEDIN_CACHE_PATH"])

SECONDS_BETWEEN_CALLS = 30
REQUEST_TIMEOUT = 90

CLIENT_UA = {
    "REDWOLF": "redwolf-linkedin-fetch/1.0 (+https://github.com/jayreck996/py-post)",
    "ASIS":    "asis-linkedin-fetch/1.0 (+https://github.com/jayreck996/py-post)",
}

SLUG_MAP = {
    "Red Wolf High Level Security Ltd": "REDWOLF",
    "ASIS New Zealand": "ASISNZ",
    "New Zealand Security Association (NZSA)": "NZSA",
    "ASIS International": "ASIS",
    "NZ Police": "NZPOLICE",
    "Johnson Controls": "JOHNSON",
    "Gallagher Security": "GALLAGHER",
    "Inner Range ANZ": "INNERRANGE",
    "Bosch Security and Safety Systems": "BOSCH",
    "Integrated Control Technology (ICT)": "ICT",
    "Jacques Technologies": "JACQUES",
    "Risk NZ": "RISKNZ",
    "BDO Risk Report": "BDORISK",
    "New Zealand Network for Women in Security": "NZNWS",
    "New Zealand Internet Task Force (NZITF)": "NZITF",
    "National Cyber Security Centre (NCSC)": "NCSCNZ",
    "ISACA": "ISACA",
    "SIA": "SIA",
    "WorkSafe New Zealand": "WORKSAFE",
    "ASIAL": "ASIAL",
}


def load_connections() -> list[tuple[str, str, str]]:
    data = json.loads(TREE_FILE.read_text())
    connections = data.get("connections", {})
    out = []
    for group in ("own", "associations", "partners"):
        for name, entry in connections.get(group, {}).items():
            url = entry["url"] if isinstance(entry, dict) else entry
            slug = SLUG_MAP.get(name)
            if not slug:
                print(f"WARNING: no slug mapping for connection {name!r} — "
                      f"skipping. Add it to SLUG_MAP.", file=sys.stderr)
                continue
            out.append((slug, name, url))
    return out


def fetch_one(base_url: str, slug: str, company_name: str, url: str,
              cf_client_id: str, cf_client_secret: str, shared_secret: str) -> bytes | None:
    qs = urllib.parse.urlencode({"slug": slug, "companyName": company_name, "url": url})
    full_url = f"{base_url}?{qs}"
    headers = {"User-Agent": CLIENT_UA.get(CLIENT, "linkedin-fetch/1.0")}
    if cf_client_id and cf_client_secret:
        headers["CF-Access-Client-Id"] = cf_client_id
        headers["CF-Access-Client-Secret"] = cf_client_secret
    if shared_secret:
        headers["X-Listener-Secret"] = shared_secret

    req = urllib.request.Request(full_url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            if resp.status != 200:
                print(f"slug={slug}: HTTP {resp.status} — skipping", file=sys.stderr)
                return None
            return resp.read()
    except urllib.error.HTTPError as exc:
        print(f"slug={slug}: HTTP {exc.code} — skipping", file=sys.stderr)
        return None
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"slug={slug}: request failed ({exc}) — skipping", file=sys.stderr)
        return None


def append_entry(slug: str, data: dict) -> None:
    JSONL_DIR.mkdir(parents=True, exist_ok=True)
    path = JSONL_DIR / f"{slug}.jsonl"
    compact = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    with open(path, "a", encoding="utf-8") as f:
        f.write(compact + "\n")


def main() -> int:
    base_url = os.environ.get("LINKEDIN_FETCH_URL", "")
    if not base_url:
        print("LINKEDIN_FETCH_URL is not set — nothing to do", file=sys.stderr)
        return 1

    cf_client_id     = os.environ.get("CF_ACCESS_CLIENT_ID", "")
    cf_client_secret = os.environ.get("CF_ACCESS_CLIENT_SECRET", "")
    shared_secret    = os.environ.get("LISTENER_SHARED_SECRET", "")

    connections = load_connections()
    print(f"[{CLIENT}] Fetching {len(connections)} connections, {SECONDS_BETWEEN_CALLS}s apart...")

    fetched, skipped = 0, 0
    for i, (slug, company_name, url) in enumerate(connections):
        body = fetch_one(base_url, slug, company_name, url,
                         cf_client_id, cf_client_secret, shared_secret)
        if body is None:
            skipped += 1
        else:
            try:
                parsed = json.loads(body)
            except json.JSONDecodeError:
                print(f"slug={slug}: non-JSON response — skipping", file=sys.stderr)
                skipped += 1
                continue
            append_entry(slug, parsed)
            fetched += 1
            print(f"slug={slug}: appended entry to {JSONL_DIR / f'{slug}.jsonl'}")

        if i < len(connections) - 1:
            time.sleep(SECONDS_BETWEEN_CALLS)

    print(f"Done: {fetched} written, {skipped} skipped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

