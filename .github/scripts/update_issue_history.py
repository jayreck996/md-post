#!/usr/bin/env python3
"""Prepends a timestamped entry to the <!-- HISTORY-START --> section of the client's open issue."""

import json
import os
import subprocess
from datetime import datetime, timezone

CLIENT = os.environ["CLIENT"]
EVENT  = os.environ["EVENT"]
DETAIL = os.environ.get("DETAIL", "")

now   = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
entry = f"- `{now}` **{EVENT}**" + (f" · {DETAIL}" if DETAIL else "")

MARKER_START     = "<!-- HISTORY-START -->"
MARKER_END       = "<!-- HISTORY-END -->"
HISTORY_SECTION  = f"\n## Change History\n\n{MARKER_START}\n{MARKER_END}\n"

result = subprocess.run(
    ["gh", "issue", "list", "--state", "open", "--json", "number,body"],
    capture_output=True, text=True, check=True,
)
issues = json.loads(result.stdout)

for issue in issues:
    body = issue.get("body") or ""
    if f"YML/{CLIENT}/" not in body:
        continue

    number = issue["number"]

    if MARKER_START not in body:
        body = body + HISTORY_SECTION

    body = body.replace(MARKER_START, f"{MARKER_START}\n{entry}", 1)

    subprocess.run(["gh", "issue", "edit", str(number), "--body", body], check=True)
    print(f"[{CLIENT}] issue #{number} history updated: {entry}")
    break
