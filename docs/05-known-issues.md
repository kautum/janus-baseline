# Known issues

Verified by reading the code and reproducing the behaviour, with file references so you
can check any of it yourself. Split into what has been fixed on this branch and what is
still outstanding.

---

## Fixed on this branch

### The app did not start from a clean clone
`index.py` and every callback/logic module imported `layouts.*`, `callbacks.*`,
`logic.*` and `utils.*` as packages, but all files sat flat at the repository root, so
a fresh clone failed immediately with `ModuleNotFoundError: No module named 'layouts'`.
Two modules the code still imported, `config.py` and `callbacks/login_callbacks.py`,
had also been deleted. **Fixed:** files moved into the packages the code already
expected, and minimal versions of both deleted modules restored.

### Analysis callbacks ran without authentication
`display_page()` in `index.py` chooses which layout to render, which looks like access
control but isn't. Dash callbacks are ordinary POSTs to `/_dash-update-component` and
every analysis callback is registered globally at import time, so an unauthenticated
caller could invoke them directly using component IDs read from the client bundle:
starting AndroZoo downloads, writing uploaded files, reading pre-computed data.
**Fixed:** a `before_request` guard on the callback endpoint, allowing only the router
and the login callback through while logged out. Guarding at the single point every
callback passes through means new callbacks are protected by default.
Covered by `test_auth_required.py`.

### Path traversal in APK upload
`save_uploaded_file_to_server()` built a server path from the browser-supplied filename
with no sanitisation, so a name like `../../../app.py` escaped `uploaded_apks/`. Worse
on removal: the stored path is later passed to `os.remove()`, making it arbitrary file
*deletion*. **Fixed:** filenames passed through `os.path.basename()`.
Covered by `test_upload_safety.py`.

### Uploads were never validated
No size cap and no check that an "APK" was actually an APK: the request body was
buffered and base64-decoded in full, then written to disk as-is. **Fixed:**
`MAX_CONTENT_LENGTH` (default 500 MB, `JANUS_MAX_UPLOAD_MB`) and a ZIP magic-byte check
before anything reaches disk.

### Session secret key regenerated on every restart
`app.py` fell back to a fresh random key each start, silently logging everyone out.
**Fixed:** persisted to `.flask_secret_key` (gitignored) when `SECRET_KEY` is unset.

### Race condition in session tracking
`active_sessions` was mutated with no lock while `clean_stale_sessions()` iterated it on
*every request*, so a session registering during that iteration could raise
`dictionary changed size during iteration` inside the page-routing callback, breaking
the site for all users, not only the one running an analysis. **Fixed:** a
`threading.Lock` around all four accessors in `utils/concurrency_manager.py`.

### Worker processes leaked on failure
`utils/apk_analysis_core.py` called `pool.close()`/`pool.join()` after `starmap()` with
no `try`/`finally`, so any exception, a malformed APK crashing a worker or a pickling
error, orphaned the pool and leaked its processes. Over long unattended runs these
accumulate. **Fixed:** the pool is now a context manager.

### `/logout` returned 404
The navbar has always linked to `/logout`, but no such route existed: clicking Logout
gave a 404 and left the session active. **Fixed:** route added.

### `/admin/status` was unauthenticated, and absent under WSGI
It disclosed session counts and truncated session IDs to anyone. It was also defined
inside `if __name__ == "__main__":`, so under `gunicorn index:server` it did not exist
at all, precisely the deployment where an operator would want it. **Fixed:** moved to
module level and given `@login_required`.

### Miscellaneous
- `re.split('(\d+)', s)` in two logic modules used an invalid escape sequence
  (`SyntaxWarning` now, `SyntaxError` on newer Python). Now raw strings.
- Two bare `except:` blocks replaced with specific exceptions, and the one that hid an
  unreadable index file now logs why.
- `requirements.txt` was missing `dash`, `dash-bootstrap-components`, `Flask-Login` and
  `psutil`, all imported by the app. Now added.

---

## Outstanding

### High: download retries can block for hours, and the timeout is inconsistent
`utils/apk_analysis_core.py` retries a failed download up to
`DOWNLOAD_RETRY_CYCLES` (4) × `MAX_DOWNLOAD_RETRIES` (20) times with a flat
`time.sleep(200)` between attempts, with no backoff, jitter, or deadline. The worst case is
roughly four hours *for a single APK*, inside a blocking Dash callback.

Worse, `PROCESSING_TIMEOUT` is only checked in `logic/historical_connectivity_logic.py`.
The pre-computed and upload paths have no equivalent check, because the download loop
was copy-pasted and the timeout fix only ever landed in one copy, a good illustration
of why the duplication below matters.

*Suggested fix:* pass a deadline into the download function and check it inside the
sleep loop; use exponential backoff with jitter; apply it in one shared place.

### High: the three analysis modes are largely copy-paste
`initialize_database` is byte-identical across all three `logic/` modules (plus a fourth
unused variant in `utils/apk_analysis_core.py`). `generate_download_link`, `plot_data`,
`process_package` and `download_apks` differ by only a few lines between copies.
Roughly two-thirds of `logic/` is duplicated.

*Suggested fix:* extract into shared modules (`db`, `download`, `plotting`) **one module
at a time**, verifying output is unchanged at each step, because these functions produce
figures that end up in published papers, so behaviour must be preserved exactly.

### Medium: uploaded files are never cleaned up
Files in `uploaded_apks/` are deleted only when the user explicitly removes them in the
UI. Closing the tab or letting the session expire leaves them behind for good;
`clean_stale_sessions()` only clears the in-memory dict. The directory grows without
bound over months of use.

*Suggested fix:* sweep files older than `SESSION_TIMEOUT` on startup and during stale
session cleanup.

### Medium: connection pool silently ignores later configuration
`SQLiteConnectionPool.__init__` returns early once initialised, so the **first** caller's
`db_path` wins for the process lifetime. Harmless today because every caller passes
`'androzoo.db'`, but it will silently use the wrong database the moment anyone
parametrises the path per mode.

*Suggested fix:* warn (or keep a pool per path) if called again with a different path.

### Medium: `requirements.txt` pins are unusable on modern Python
Exact 2023 pins (`numpy==1.25.1`, `pandas==2.0.3`, …) have no wheels for Python 3.12+
and fail to build. New contributors hit this immediately.

*Suggested fix:* relax to minimum versions, or publish a tested `constraints.txt`
alongside a documented Python version.

### Low: dead code from the pre-Dash version
`plotter.py` (~22 KB), `templates/`, and the root `index.html`, `confirmation.html` and
`result.html` are left over from an earlier Flask implementation. Nothing imports or
renders them (verified by grep). They are deliberately **not** deleted on this branch,
since removing files is a maintainer's call rather than a contributor's, but they
mislead anyone
reading the repository for the first time.

### Low: missing `assets/` breaks the logos
Layouts reference `assets/digisilk_countries.png` and `assets/sponsors.png`; there is no
`assets/` directory. `sponsors.png` exists at the repository root instead. Cosmetic, but
visible on the login and home pages.

### Low: the DEX parser has no bounds checking
`utils/dex_parser.py` reads offsets out of the file and indexes into raw bytes without
validating them, so a truncated or malformed APK raises `IndexError`/`struct.error`.
That is caught by a broad handler upstream, which logs a line and drops **all** data for
that APK, a plausible cause of unexplained gaps in results.

*Suggested fix:* validate offsets against the buffer length and raise a specific error
so the failure is distinguishable from an APK that genuinely contains no URLs.

---

## Deliberately checked and found safe

Worth recording so nobody re-investigates:

- **Zip-slip during extraction.** `extract_apk_dex_files` only calls `z.read(name)` and
  keeps bytes in memory; no `extractall()` exists anywhere in the codebase, so crafted
  archive entry names cannot write outside a directory.
- **SQL injection.** All queries use `?` placeholders via `cursor.execute(query, params)`.
  No string-built SQL anywhere.
- **SSRF via the download path.** The AndroZoo host is hardcoded and the SHA-256 comes
  from the local catalogue, never directly from user input.
- **API keys in logs.** The AndroZoo key is never interpolated into a log message.
