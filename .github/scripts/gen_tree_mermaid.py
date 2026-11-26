#!/usr/bin/env python3
"""Generate a Mermaid graph LR from the configured strategy tree.

CLIENT env var selects REDWOLF or ASIS.
"""

import json
import os
import re
import sys

CLIENT    = os.environ.get("CLIENT", "REDWOLF").upper()
TREE_FILE = os.environ["TREE_PATH"]


def safe_id(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "_", text)


def gen_mermaid(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    quarter    = data["meta"]["quarter"]
    client_lbl = data["meta"].get("name", CLIENT)
    lines = [
        "```mermaid",
        "graph LR",
        f'  ROOT(["🔴 {client_lbl} · {quarter}"])',
    ]

    classed = {"win": [], "lost": []}

    conns = data.get("connections", {})
    if conns:
        lines.append('  ROOT --> CONNECTIONS["connections"]')
        for group, label in (("own", "own"), ("associations", "associations"), ("partners", "partners")):
            members = conns.get(group, {})
            if not members:
                continue
            grp_id = f'CONN_{group}'
            lines.append(f'  CONNECTIONS --> {grp_id}["{label}"]')
            for name, entry in members.items():
                mem_id = f'{grp_id}_{safe_id(name)}'
                value  = entry.get("value", 0) if isinstance(entry, dict) else 0
                shown  = f"{name} · {value:+d}" if value else name
                if value:
                    classed["win" if value > 0 else "lost"].append(mem_id)
                lines.append(f'  {grp_id} --> {mem_id}("{shown}")')

    lines.append('  ROOT --> TREE["tree"]')
    for cat in data["tree"]:
        cat_id = safe_id(cat["category"])
        lines.append(f'  TREE --> {cat_id}["{cat["category"]}"]')
        for t in cat["types"]:
            type_id = f'{cat_id}_{safe_id(t["type"])}'
            lines.append(f'  {cat_id} --> {type_id}["{t["type"]}"]')
            for s in t["subtypes"]:
                sub_id = f'{type_id}_{safe_id(s["name"])}'
                label  = s["name"]
                value  = s.get("value", 0)
                if value:
                    label += f" · {value:+d}"
                    classed["win" if value > 0 else "lost"].append(sub_id)
                lines.append(f'  {type_id} --> {sub_id}("{label}")')

    lines.append("  classDef win fill:#d4edda,stroke:#2e7d32,color:#1b5e20")
    lines.append("  classDef lost fill:#f8d7da,stroke:#c62828,color:#7f0000")
    for outcome, ids in classed.items():
        if ids:
            lines.append(f'  class {",".join(ids)} {outcome}')

    lines.append("```")
    return "\n".join(lines)


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else TREE_FILE
    print(gen_mermaid(path))
