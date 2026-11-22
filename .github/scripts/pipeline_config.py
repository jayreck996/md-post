#!/usr/bin/env python3
"""Read YML/{CLIENT}/YML-*.yml and emit GitHub Actions outputs for the given step.

Usage:
    python3 .github/scripts/pipeline_config.py <CLIENT> <step>

Steps:
    fetch_linkedin | generate_content | generate_media |
    update_feedback | update_tree_mermaid

Outputs are written to $GITHUB_OUTPUT (or printed to stdout if not set).
All step-specific keys plus common keys (quarter, xls, json) are always emitted.
"""

import json
import os
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyyaml", "-q"])
    import yaml


STEPS = {
    "fetch_linkedin",
    "generate_content",
    "generate_media",
    "update_feedback",
    "update_tree_mermaid",
}


def find_yml(client: str) -> Path:
    base = Path(f"YML/{client}")
    candidates = sorted(base.glob("YML-*.yml"), reverse=True)
    if not candidates:
        raise FileNotFoundError(f"No YML file found in YML/{client}/")
    return candidates[0]


def load_config(client: str) -> dict:
    path = find_yml(client)
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    cfg = data.get("config")
    if not cfg:
        raise ValueError(f"{path} has no 'config:' block — add one before using pipeline_config.py")
    return cfg


def emit(outputs: dict[str, str]) -> None:
    gha_output = os.environ.get("GITHUB_OUTPUT")
    if gha_output:
        with open(gha_output, "a", encoding="utf-8") as f:
            for k, v in outputs.items():
                # multi-line values use heredoc syntax
                if "\n" in str(v):
                    f.write(f"{k}<<_EOF_\n{v}\n_EOF_\n")
                else:
                    f.write(f"{k}={v}\n")
    else:
        for k, v in outputs.items():
            print(f"{k}={v}")


def submodules_str(cfg: dict, step: str) -> str:
    subs = cfg.get("submodules", {}).get(step, [])
    return " ".join(subs)


def main() -> None:
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <CLIENT> <step>", file=sys.stderr)
        print(f"Steps: {', '.join(sorted(STEPS))}", file=sys.stderr)
        sys.exit(1)

    client = sys.argv[1].upper()
    step   = sys.argv[2].lower()

    if step not in STEPS:
        print(f"Unknown step {step!r}. Valid: {', '.join(sorted(STEPS))}", file=sys.stderr)
        sys.exit(1)

    cfg   = load_config(client)
    files = cfg.get("files", {})
    media = cfg.get("media", {})
    secs  = cfg.get("secrets", {})

    out: dict[str, str] = {
        # always present
        "quarter":  cfg.get("quarter", ""),
        "xls":      files.get("xls", ""),
        "json":     files.get("json", ""),
        "jsonl_dir": files.get("jsonl_dir", ""),
        "submodules": submodules_str(cfg, step),
        # secret names (resolved dynamically in GHA with secrets[name])
        "secret_linkedin_fetch_url":     secs.get("linkedin_fetch_url", ""),
        "secret_generate_content_url":   secs.get("generate_content_url", ""),
        "secret_listener_shared_secret": secs.get("listener_shared_secret", ""),
    }

    if step in ("generate_content", "generate_media"):
        out["skill_generate_post"]  = files.get("skill_generate_post", "")
        out["skill_generate_media"] = files.get("skill_generate_media", "")
        out["logo"]                 = files.get("logo", "")
        out["logo_mime"]            = files.get("logo_mime", "image/jpeg")
        out["slug_order"]           = json.dumps(cfg.get("slug_order", []))

    if step == "generate_media":
        out["media_mode"] = media.get("mode", "submodule")
        if media.get("mode") == "repo_local":
            out["media_dir"]  = media.get("media_dir", "")
            out["pages_base"] = media.get("pages_base", "")
        else:
            out["img_dir"]  = media.get("img_dir", "")
            out["pdf_dir"]  = media.get("pdf_dir", "")
            out["img_base"] = media.get("img_base", "")
            out["pdf_base"] = media.get("pdf_base", "")

    emit(out)
    print(f"[pipeline_config] {client}/{step} → {len(out)} outputs", file=sys.stderr)


if __name__ == "__main__":
    main()
