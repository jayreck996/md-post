ASSET LOG — md-post monorepo
INSTRUCTION FOR AI MODEL:

ALWAYS ADD NEW ASSET ENTRIES AT THE TOP, DIRECTLY BELOW THIS HEADER.

NEVER DELETE OR EDIT PREVIOUS ASSET ENTRIES.

REQUIRED FORMAT FOR EACH ASSET ENTRY:

## ASSET:{REDWOLF|ASIS|md-post} {YYYY-MM-DD HH:MM} → {CONTENT}

Use REDWOLF or ASIS for client-specific changes, md-post for changes that affect both clients or the shared repo infrastructure.

Per-client history is also maintained in REDWOLF/ASSET-2026Q4.md and ASIS/ASSET-2026Q4.md.

####### <!-- ANCHOR MARKER - ADD ALL NEW ASSET ENTRIES DIRECTLY BELOW THIS LINE, NEVER DELETE OR EDIT PREVIOUS ASSET ENTRIES-->
## ASSET:ASIS 2026-11-24 → fetch-linkedin 404 on Mac mini; new partners missing SLUG_MAP

**fetch-linkedin run 45350028803 — 0 written, 5 skipped (all HTTP 404).**
Mac mini LinkedIn fetch endpoint returning HTTP 404 for all slugs (ASISNZ, NZSA, ASIS, NZPOLICE). Root cause not yet investigated — the `/fetch-linkedin` route on the Mac mini listener may be down or the URL has changed.

Additionally, the 10 new ASIS partners added to `JSON/ASIS/JSON-2026Q4.json` this session have no entries in `fetch_linkedin_cache.py`'s `SLUG_MAP`: Risk NZ, BDO Risk Report, World Economic Forum Risk Report, New Zealand Network for Women in Security, New Zealand Internet Task Force (NZITF), National Cyber Security Centre (NCSC), ISACA, NZSIS, IFSEC, SIA. These will be skipped with warnings until slug entries are added and corresponding JSONL seed files are created.

Week 48 content was generated without fresh LinkedIn context (JSONL snapshots dated 2026-11-16; all recentPosts fall outside the 7-day window for a Nov 24 run). Pending: fix Mac mini endpoint, add SLUG_MAP entries, re-run fetch-linkedin, then re-run week 48 with `replace=true`.

## ASSET:ASIS 2026-11-24 → JSON connections schema fix; week 48 re-run succeeded

**Root cause: `update_tree_values.py` requires single-line inline connection entries.**
Previous session wrote `JSON/ASIS/JSON-2026Q4.json` using `json.dumps(..., indent=2)` which produced multi-line connection entries. `update_tree_values.py` processes connections with line-by-line regex (`CONN_RE`): it skips lines ending with `{` (the outer `"Name": {` line) but then matches the inner `"url": "..."` and `"value": 0` lines as if they were top-level connection names, rewriting them as `{ "url": "...", "value": 0 }` nested objects — corrupting the structure on every workflow run.

Fix: rebuilt `JSON/ASIS/JSON-2026Q4.json` with single-line inline entries matching REDWOLF format: `"Name": { "url": "https://...", "value": 0 }` on one line. Pushed via GitHub API (commit `186d523b`).

Previous two re-run attempts (runs 45341299561 and 45342134865) both failed at "Generate issue body" with `TypeError: '>' not supported between instances of 'dict' and 'int'` in `gen_pr_body.py:156` — `meta.get("value", 0) > 0` received a dict because the connections structure was corrupted.

Run 45343063282 (`replace=true`, `week=48`) passed all 12 steps after the fix. Week 48 ASIS content replaced successfully.


## ASSET:md-post 2026-11-23 → py-rss scheduled cron fired (5h late); 3 new Coinbase articles

Scheduled run 45079164791 fired at 22:41 UTC (cron `30 17 * * *` — first ever `schedule` event, delayed ~5h, likely GitHub inactive-repo suppression). XML commit `d3b40297` at 22:45 UTC.

Diff vs manual trigger (21:43 UTC, commit `4d9cdff6`):

ANTHROPIC — no new articles (+1/-1 metadata only)

COINBASE — 3 new articles added, 3 old dropped (sliding window):
  + "Coinbase Powers the First Crypto-Backed, Conforming Mortgages by Better"
  + "Coinbase and PNC expand partnership to bring stablecoin payment acceptance"
  + "Building enterprise AI agents at Coinbase: engineering for trust, scale, and speed"
  - "No Compromises: The case for Coinbase as the best place for institutions"
  - "Create your own stablecoin with Coinbase"
  - "Coinbase Australia Receives AFSL Licence: A New Chapter for Crypto in Australia"

NINTENDO — no new articles (+1/-1 metadata only)

OPENAI — no new articles (+1/-1 metadata only)

## ASSET:md-post 2026-11-23 → py-rss XML feed state after manual trigger (run 45073354311)

Feed totals and new articles detected vs morning baseline (06:33 UTC commit 15de02d6):

ANTHROPIC — 1 article total; no new today. Last: "Linked billing on the Claude Platform" (17 Nov 2026)

COINBASE — 26 articles total; no new since morning. All items normalised to 22 Nov 2026 date. Latest 3: "Coinbase for Agents introduces new Agent Controls", "An Evolution of Leadership at the Coinbase Global Advisory Council", "Beyond the bot: Mapping the agentic trading stack"

NINTENDO — 24 articles total; no new since morning. All items dated 22 Nov 2026. Latest 4: "Ask the Developer Vol. 24, The Legend of Zelda: Ocarina of Time" (Chapters 1–4), "Call of Duty: Modern Warfare 4 is out now for Nintendo Switch 2", "Congrats to The Game Awards 2026 nominees"

OPENAI — 25 articles total; 1 new this evening: "Perplexity and Intelligence" (22 Nov 2026). Previous latest was "Advancing chip design with OpenAI models" (18 Nov 2026)

## ASSET:md-post 2026-11-23 → py-rss scheduled run did not trigger; manually dispatched

`jayreck996/py-rss` daily cron (`30 17 * * *` UTC = 6:30 AM NZDT) did not fire on 2026-11-23 — all prior runs were `workflow_dispatch`, not `schedule`. GitHub may suppress schedule triggers on repos with no recent cron history. Run 45073354311 triggered manually via `gh workflow run daily.yml` at ~21:40 UTC; completed successfully in 3m47s. No errors.

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
