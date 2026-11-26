#!/usr/bin/env python3
"""Read explicit client paths from YML and emit GitHub Actions outputs.

Usage:
    python3 .github/scripts/pipeline_config.py <CLIENT> <step>

Steps:
    fetch_linkedin | generate_content | generate_media |
    update_feedback | update_tree_mermaid

Outputs are written to $GITHUB_OUTPUT (or printed to stdout if not set).
All explicit file paths and the repositories required by the selected step are emitted.
"""

import json
import os
import sys
from pathlib import Path
from pathlib import PurePosixPath

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


def required(cfg: dict, section: str, key: str):
    value = cfg.get(section, {}).get(key)
    if value in (None, ""):
        raise ValueError(f"config.{section}.{key} is required")
    return value


def validate_path(value: str, prefix: str, client: str, label: str) -> str:
    path = PurePosixPath(value)
    expected = PurePosixPath(prefix) / client
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{label} must be a relative path without '..': {value}")
    if path.parts[:len(expected.parts)] != expected.parts:
        raise ValueError(f"{label} must be under {expected}: {value}")
    return value


def required_repositories_str(cfg: dict, step: str) -> str:
    repositories = cfg.get("repositories", {})
    keys = cfg.get("workflows", {}).get(step)
    if not keys:
        raise ValueError(f"config.workflows.{step} is required")
    unknown = [key for key in keys if key not in repositories]
    if unknown:
        raise ValueError(f"Unknown repositories in {step}: {', '.join(unknown)}")
    return " ".join(keys)


def validate_repository(key: str, repository: dict) -> tuple[str, str]:
    name = repository.get("name", "")
    checkout_path = repository.get("checkout_path", "")
    path = PurePosixPath(checkout_path)
    if name.count("/") != 1:
        raise ValueError(f"config.repositories.{key}.name must be owner/repository")
    if path.is_absolute() or len(path.parts) != 1 or ".." in path.parts:
        raise ValueError(
            f"config.repositories.{key}.checkout_path must be one relative directory"
        )
    return name, checkout_path


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
    repositories = {
        key: validate_repository(key, repository)
        for key, repository in cfg.get("repositories", {}).items()
    }
    missing_repositories = sorted({"yml", "xls", "json", "jsonl", "img", "pdf"} - repositories.keys())
    if missing_repositories:
        raise ValueError(
            f"Missing config.repositories entries: {', '.join(missing_repositories)}"
        )

    posts_path = validate_path(
        required(cfg, "files", "posts"), repositories["xls"][1], client, "posts"
    )
    tree_path = validate_path(
        required(cfg, "files", "tree"), repositories["json"][1], client, "tree"
    )
    linkedin_cache_path = validate_path(
        required(cfg, "files", "linkedin_cache"),
        repositories["jsonl"][1], client, "linkedin_cache"
    )
    pipeline_path = validate_path(
        required(cfg, "files", "pipeline"), repositories["yml"][1], client, "pipeline"
    )
    asset_log_path = validate_path(required(cfg, "files", "asset_log"), client, "", "asset_log")

    out: dict[str, str] = {
        # always present
        "quarter":  cfg.get("quarter", ""),
        "posts_path": posts_path,
        "tree_path": tree_path,
        "linkedin_cache_path": linkedin_cache_path,
        "pipeline_path": pipeline_path,
        "asset_log_path": asset_log_path,
        "required_repositories": required_repositories_str(cfg, step),
        # secret names (resolved dynamically in GHA with secrets[name])
        "secret_linkedin_fetch_url":     secs.get("linkedin_fetch_url", ""),
        "secret_generate_content_url":   secs.get("generate_content_url", ""),
        "secret_listener_shared_secret": secs.get("listener_shared_secret", ""),
    }
    for key, (name, checkout_path) in repositories.items():
        out[f"{key}_repository"] = name
        out[f"{key}_checkout_path"] = checkout_path

    if step in ("generate_content", "generate_media"):
        out["generate_post_skill_path"] = required(cfg, "files", "generate_post_skill")
        out["generate_media_skill_path"] = required(cfg, "files", "generate_media_skill")
        out["logo_path"]            = required(cfg, "files", "logo")
        out["logo_mime"]            = files.get("logo_mime", "image/jpeg")
        out["slug_order"]           = json.dumps(cfg.get("slug_order", []))

    if step == "generate_media":
        if media.get("mode") != "shared_repositories":
            raise ValueError("config.media.mode must be shared_repositories")
        images = required(cfg, "media", "images")
        documents = required(cfg, "media", "documents")
        out["media_mode"] = "shared_repositories"
        out["image_dir"] = validate_path(
            images["directory"], repositories["img"][1], client, "media.images.directory"
        )
        out["image_base_url"] = images["base_url"]
        out["document_dir"] = validate_path(
            documents["directory"], repositories["pdf"][1], client, "media.documents.directory"
        )
        out["document_base_url"] = documents["base_url"]

    emit(out)
    print(f"[pipeline_config] {client}/{step} → {len(out)} outputs", file=sys.stderr)


if __name__ == "__main__":
    main()
