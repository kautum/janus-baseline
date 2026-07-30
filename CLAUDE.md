# Janus — context for AI coding assistants

This file is read automatically by Claude Code and similar tools. It exists so that
any assistant (or any new developer) starts with the same accurate picture of this
repository instead of re-deriving it. Human-readable documentation lives in `docs/`.

## What this project is

Janus analyses **how an Android app's backend connectivity changes over time**.

It takes a package name (e.g. `kz.kaspi.mobile`), pulls a chronological series of
that app's historical releases from the [AndroZoo](https://androzoo.uni.lu) research
dataset, decompiles each one, extracts every domain and URL embedded in the code, and
plots how that set of endpoints shifts release by release.

The point is **not** security scanning. It is a research instrument: embedded URLs act
as a historical record of which services an app depended on, so changes over time
reveal shifting corporate partnerships, infrastructure migrations, and geopolitical
realignment. Janus was built by [DIGISILK](https://www.digisilk.eu/), an ERC-funded
project (Horizon 2020, grant 850891) in the Department of Digital Humanities at King's
College London, studying China's digital expansion in borderland regions.

**The users are social scientists, not engineers.** Optimise for a researcher who wants
to run an analysis without touching a terminal. See `docs/01-project.md`.

## Repository map

```
index.py                  Entry point. URL routing + auth gate. Run this, not app.py.
app.py                    Dash/Flask app object, Flask-Login setup, session secret key.
config.py                 Tunables (timeouts, retry counts) + optional UI overrides.

layouts/                  Dash UI trees. Pure presentation, no analysis logic.
callbacks/                Dash callbacks. Wire UI events -> logic/. Where requests land.
logic/                    The three analysis pipelines (see below).
utils/                    Shared machinery: APK download/parse, DEX parsing, DB pool,
                          session concurrency limits, UI log streaming.
docs/                     Human documentation. Start at docs/README.md.
```

`plotter.py` and the root-level `*.html` / `templates/` are **legacy leftovers** from an
earlier Flask version of this app. Nothing imports them. Do not extend them.

## The three analysis modes

Each has a `layouts/` + `callbacks/` + `logic/` triple. They do similar things and
share a lot of near-duplicated code — that duplication is known technical debt, not a
deliberate design.

| Mode | Route | What it does |
|---|---|---|
| Historical (real-time) | `/historical-connectivity` | Downloads APKs live from AndroZoo and analyses them. Slow (hours), needs an API key. |
| Pre-computed | `/precomputed-connectivity` | Browses results computed earlier, from `precomputed_data/`. Fast, no API key. |
| Upload | `/user-apk-analysis` | User uploads their own APK files through the browser. |

## How an analysis actually runs

1. A callback in `callbacks/` receives the form input and registers a session with
   `utils/concurrency_manager.py`, which caps concurrent analyses based on available
   CPU and RAM (these runs are heavy).
2. `logic/*_logic.py` resolves package names to specific APK hashes via the local
   `androzoo.db` SQLite index, then downloads each APK from AndroZoo.
3. Each APK is decompiled and its strings scanned for URLs/domains. Two parsers are
   available: **Androguard** (thorough, slow) or the project's own **DEXParser** in
   `utils/dex_parser.py` (faster, reads the DEX string table directly).
4. Extracted endpoints are cached in SQLite, then rendered as Plotly heatmaps/bar
   charts showing presence of each endpoint across versions.
5. Progress is streamed back to the browser via `utils/ui_logger.py`.

Long runs are bounded by `PROCESSING_TIMEOUT` in `config.py` and return partial results
rather than failing outright — deliberate, because researchers would rather have some
data than none after an hour.

## Conventions to follow

- **Error handling:** log with context (`logger.error(f"...: {e}")`) and continue where a
  single APK failing shouldn't kill a whole run. Never add a bare `except:` — silently
  swallowed failures show up as unexplained missing data in someone's research.
- **British spelling** in user-facing strings and comments ("analyse", "visualise",
  "initialise") — matches the existing codebase and the institution.
- **Licence headers:** every source file carries the Apache-2.0 header. Keep it.
- **Don't rewrite working analysis code to make it prettier.** The numbers it produces
  are going into published research. Behaviour-preserving changes only, unless the
  change is fixing a stated bug.

## Getting it running

See `docs/03-setup.md`. Note that the app requires two data files (`androzoo.db` and
`filtered_package_ids_with_counts10_ver.json`) that are **not in the repository** and
must be obtained separately — this is currently the single biggest barrier to new
contributors.

## Known issues

`docs/05-known-issues.md` tracks verified defects with file:line references. Check it
before reporting something as new.
