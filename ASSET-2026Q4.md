ASSET LOG — md-post monorepo
INSTRUCTION FOR AI MODEL:

ALWAYS ADD NEW ASSET ENTRIES AT THE TOP, DIRECTLY BELOW THIS HEADER.

NEVER DELETE OR EDIT PREVIOUS ASSET ENTRIES.

REQUIRED FORMAT FOR EACH ASSET ENTRY:

## ASSET:{REDWOLF|ASIS|md-post} {YYYY-MM-DD HH:MM} → {CONTENT}

Use REDWOLF or ASIS for client-specific changes, md-post for changes that affect both clients or the shared repo infrastructure.

Per-client history is also maintained in REDWOLF/ASSET-2026Q4.md and ASIS/ASSET-2026Q4.md.

####### <!-- ANCHOR MARKER - ADD ALL NEW ASSET ENTRIES DIRECTLY BELOW THIS LINE, NEVER DELETE OR EDIT PREVIOUS ASSET ENTRIES-->

## ASSET:md-post 2026-11-22 → monorepo migration: md-redwolf + md-asis unified into jayreck996/md-post

**New repo `jayreck996/md-post` created:**
- Shared `index.html`, `app.js`, `app.css` — URL hash selects client (`#REDWOLF` / `#ASIS`).
- `window.__MD_CFG__` object injected per-client at Pages deploy time (`{title, tokenVar, csvPath, logo}`).
- Both clients served from `jayreck996.github.io/md-post`.
- GitHub Pages enabled via API (workflow-driven build type).

**All 5 GitHub Actions workflows migrated and unified (CLIENT matrix):**
- `fetch-linkedin.yml`, `generate-content.yml`, `generate-media.yml`, `update-feedback.yml`, `update-tree-mermaid.yml` — each accepts `client` input and runs a matrix of `[REDWOLF, ASIS]` by default.
- `deploy-pages.yml` — injects per-client `config.js` files (`REDWOLF/config.js`, `ASIS/config.js`) with `window.__MD_REDWOLF__` and `window.__MD_ASIS__` tokens at Pages build time.

**All 7 scripts migrated as CLIENT-parameterised versions:**
- `fetch_linkedin_cache.py`, `gen_posts.py`, `gen_pr_body.py`, `gen_tree_mermaid.py`, `gen_media.py`, `replace_tree_section.py`, `update_tree_values.py`.
- `gen_media.py` unified from two client-specific scripts — `MEDIA_MODE=submodule` for REDWOLF (IMG/PDF repos), `MEDIA_MODE=repo_local` for ASIS (`MAY/media/2026Q3/` served via Pages).

**`pipeline_config.py` added (new):**
- Reads `YML/{CLIENT}/YML-*.yml` `config:` block and emits GitHub Actions outputs for dynamic secret and path resolution.
- Outputs: `quarter`, `xls`, `json`, `jsonl_dir`, `submodules`, `secret_linkedin_fetch_url`, `secret_generate_content_url`, `secret_listener_shared_secret`, `skill_generate_post`, `skill_generate_media`, `logo`, `logo_mime`, `slug_order`, `media_mode`, and mode-specific media paths.
- YML bootstrap pattern in every workflow: init YML submodule first → run `pipeline_config.py` → init remaining submodules from output. Removes all hardcoded quarter strings from workflows.

**YML `config:` blocks added to both `YML/REDWOLF/YML-2026Q4.yml` and `YML/ASIS/YML-2026Q4.yml`:**
- Covers `quarter`, `files` (xls, json, jsonl_dir, skill paths, logo), `media` (mode + paths), `secrets` (per-client secret names), `schedule`, `submodules` (per-step list), `slug_order`.
- REDWOLF: `media.mode: submodule`, secrets `REDWOLF_GENERATE_CONTENT_URL` / `REDWOLF_LISTENER_SHARED_SECRET`.
- ASIS: `media.mode: repo_local`, `media.media_dir: MAY/media/2026Q3`, secrets `ASIS_GENERATE_CONTENT_URL` / `ASIS_LISTENER_SHARED_SECRET`.

**Client subdirectories populated:**
- `REDWOLF/logo.jpg`, `ASIS/logo.jpg`, `ASIS/logo.svg`.
- `REDWOLF/.claude/skills/{fetch-linkedin,generate-post,generate-media}/SKILL.md` — copied from `md-redwolf`.
- `ASIS/.claude/skills/{fetch-linkedin,generate-post,generate-media}/SKILL.md` — copied from `md-asis`.
- `REDWOLF/ASSET-2026Q3.md`, `REDWOLF/ASSET-2026Q4.md`, `REDWOLF/ISSUE-2026Q4.md` — copied from `md-redwolf`.
- `ASIS/ASSET-2026Q3.md`, `ASIS/ASSET-2026Q4.md`, `ASIS/ISSUE-2026Q4.md` — copied from `md-asis`.

**`gen_pr_body.py` path fix:**
- `ASSET = "ASSET-2026Q4.md"` → `ASSET = f"{CLIENT}/ASSET-2026Q4.md"` to prevent REDWOLF/ASIS collision at repo root.

**12 secrets set on `jayreck996/md-post`:**
- PAT secrets (all same token from `jayreck996.txt`): `JSON_PAT`, `XLS_PAT`, `YML_PAT`, `JSONL_PAT`, `IMG_PAT`, `PDF_PAT`.
- Mac mini secrets (retrieved via SSH through Cloudflare Tunnel): `REDWOLF_LINKEDIN_FETCH_URL`, `ASIS_LINKEDIN_FETCH_URL`, `REDWOLF_GENERATE_CONTENT_URL`, `ASIS_GENERATE_CONTENT_URL`, `REDWOLF_LISTENER_SHARED_SECRET`, `ASIS_LISTENER_SHARED_SECRET`.

**First test run passed:**
- `fetch-linkedin` triggered for REDWOLF (run 45002358900) — both jobs green.
- `fetch (REDWOLF)` 4m51s: YML bootstrapped, pipeline_config loaded, submodules init, LinkedIn snapshots fetched, JSONL committed.
- `refresh-values (REDWOLF)` 11s: subtype values recalculated, tree JSON committed.

## ASSET:REDWOLF 2026-11-22 → XLS rename, Pages fix, media extracted to IMG/PDF submodules

See REDWOLF/ASSET-2026Q4.md for full detail.

**`jayreck996/CSV` renamed to `jayreck996/XLS`:** files `REDWOLF/XLS-2026Q4.xls`, all 10 workflow files updated (`CSV_PAT` → `XLS_PAT`), all scripts updated.

**Pages review site fixed (`index.html`):** `OWNER` → `jayreck996`, `REPO` → `XLS`, `CSV_PATH` → `REDWOLF/XLS-2026Q4.xls`; stale Q3 path caused "Cannot read properties of undefined" crash. `deploy-pages.yml` now injects `XLS_PAT`.

**Media extracted to public submodules:** `jayreck996/IMG` (82 REDWOLF files, 62 ASIS files) and `jayreck996/PDF` (9 REDWOLF, 6 ASIS). `MAY/media/2026Q3/` removed from both org repos. Media URLs now `raw.githubusercontent.com/jayreck996/IMG|PDF/main/REDWOLF|ASIS/`.

## ASSET:REDWOLF 2026-11-22 → submodule refactor: shared data extracted into 4 private jayreck996 repos

See REDWOLF/ASSET-2026Q4.md for full detail.

**4 new submodule repos:** `jayreck996/JSON`, `jayreck996/CSV`, `jayreck996/YML`, `jayreck996/JSONL` (replaces `MAY/LOG-*.log`). Files retired from both org repos: `CAN/TREE-*.json`, `COULD/TABLE-*.csv`, `PIPE-*.yml`, `MAY/LOG-*.log`, `MIGHT/`. All 7 scripts and all 10 workflows updated to use submodule paths. 4 PAT secrets set on both org repos.
