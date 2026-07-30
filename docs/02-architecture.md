# Architecture

## Framework

Janus is a [Dash](https://dash.plotly.com/) application. Dash is a Python framework that
builds web UIs without you writing JavaScript: you describe the page as a tree of Python
objects, and Dash renders it as React in the browser. Underneath, Dash runs on Flask, so
anything true of Flask (sessions, routes, WSGI deployment) is true here.

Two consequences worth knowing:

- **Callbacks are HTTP endpoints.** A Dash "callback" looks like a decorated Python
  function, but it is reached by the browser POSTing to `/_dash-update-component`.
  Anything a callback trusts is client-supplied and must be validated.
- **Callbacks block.** Dash has no built-in job queue. A callback that spends two hours
  downloading APKs holds a worker thread for two hours. This is why
  `utils/concurrency_manager.py` exists.

The older `README.md`, `plotter.py`, `templates/` and root-level `*.html` files describe
a **previous, simpler Flask version** of this app. They are no longer used. Nothing in
the running application imports them.

## Layout

```
index.py         Entry point — run this. Routing, navbar, auth gate, /admin/status.
app.py           Creates the Dash app + Flask server, configures Flask-Login.
config.py        Timeouts, retry policy, optional UI feature toggles.

layouts/         What the page looks like. No analysis logic.
  login_layout.py, home_layout.py,
  historical_connectivity_layout.py,
  precomputed_connectivity_layout.py,
  user_apk_analysis_layout.py

callbacks/       What happens when the user clicks. Validates input, calls logic/.
  login_callbacks.py, and one per analysis mode.

logic/           The analysis pipelines. Download, parse, aggregate, plot.
  historical_connectivity_logic.py
  precomputed_connectivity_logic.py
  user_apk_analysis_logic.py

utils/
  apk_analysis_core.py   Shared APK download + feature extraction.
  dex_parser.py          Custom lightweight DEX string-table parser.
  db_connection.py       SQLite connection pool.
  concurrency_manager.py Caps simultaneous analyses by CPU/RAM.
  ui_logger.py           Streams progress messages to the browser; cancellation.
```

The `layouts` / `callbacks` / `logic` split is the organising idea: **presentation,
wiring, and computation stay separate.** When adding a feature, put each part in the
matching folder rather than growing one file.

## Request flow

```
Browser
  │  user submits the analysis form
  ▼
callbacks/<mode>_callbacks.py
  │  validate input; ask concurrency_manager for a slot
  ▼
utils/concurrency_manager.py ──► rejects if the server is already at capacity
  │
  ▼
logic/<mode>_logic.py
  │  1. resolve package name -> APK hashes        (androzoo.db)
  │  2. download each APK                          (AndroZoo API)
  │  3. extract endpoints from each APK            (utils/apk_analysis_core.py)
  │  4. cache results                              (SQLite)
  │  5. build the figure                           (Plotly)
  ▼
utils/ui_logger.py ──► progress text streamed back to the page while this runs
```

## The three modes

All three end in the same place — a chart of endpoints across versions — but they differ
in where the APKs come from.

**Historical (real-time)** — `/historical-connectivity`
The full pipeline. Give it package names and a date range; it queries `androzoo.db` for
matching releases, downloads them from AndroZoo (API key required), and analyses them.
Slow: hours for a handful of apps. Bounded by `PROCESSING_TIMEOUT`.

**Pre-computed** — `/precomputed-connectivity`
Reads analyses that were run earlier and saved under `precomputed_data/`. Fast, needs no
API key. This is the mode a researcher who just wants to look at results should use, and
the one most worth making friendlier.

**Upload** — `/user-apk-analysis`
The user supplies APK files directly from their own machine through the browser. Useful
for apps not in AndroZoo, or versions a researcher obtained themselves.

The three `logic/` modules **duplicate a lot of each other** — `initialize_database`,
`generate_download_link`, plotting and download helpers appear in near-identical form in
two or three places. Consolidating them into `utils/` is worthwhile, but do it
incrementally and verify output is unchanged at each step: these functions produce
figures that end up in published papers.

## Parsers

Endpoint extraction can use either of two engines, selectable in the UI:

- **Androguard** (`androguard==3.3.5`) — a full Android reverse-engineering library.
  Thorough, well-tested, slow, memory-hungry.
- **DEXParser** (`utils/dex_parser.py`) — written for this project. Reads the DEX file's
  string table directly instead of fully decompiling. Much faster, but hand-rolled
  binary parsing with correspondingly less tolerance for malformed input.

The Androguard pin is old and ties the project to older Python versions in places.
Treat any change to the parser layer as high-risk: it determines the numbers.

## Concurrency and safety rails

- `utils/concurrency_manager.py` computes a maximum number of simultaneous analyses from
  CPU count and free RAM, and refuses new runs beyond it. Sessions older than 30 minutes
  are treated as stale and cleared.
- `utils/ui_logger.py` gives each session its own log stream and a cancellation flag, so
  a user can stop a long run.
- `PROCESSING_TIMEOUT` in `config.py` caps a run's total wall-clock time; on expiry the
  run returns whatever it has rather than erroring.

## Authentication

`app.py` configures Flask-Login with a single shared account, and `index.py` decides
which page to render based on `current_user.is_authenticated`. This is appropriate to a
small internal research tool, but note the guard is applied when rendering pages — see
[05-known-issues.md](05-known-issues.md) regarding direct callback access.
