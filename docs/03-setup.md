# Getting Janus running

Written for someone who does not consider themselves a programmer. If you are
comfortable with Python, skim — the only non-obvious part is [the data files](#3-get-the-data-files).

## What you need first

- **Python 3.9 or newer.** Check by opening a terminal and running `python3 --version`.
- **Git**, to download the code.
- **An AndroZoo API key**, but only for the live-download mode. Request one free at
  [androzoo.uni.lu](https://androzoo.uni.lu/access) — it is granted to people at
  academic institutions. You do *not* need one to browse pre-computed results.

## 1. Download the code

```bash
git clone https://github.com/digisilk/janus-baseline.git
cd janus-baseline
```

## 2. Create an isolated environment and install dependencies

A "virtual environment" keeps Janus's libraries separate from the rest of your machine,
so installing it can't break anything else.

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

You should see `(.venv)` at the start of your terminal prompt afterwards. You need to
run the `source` line again each time you open a new terminal.

> **If installation fails on a recent Python version:** `requirements.txt` pins exact
> versions from 2023, some of which have no pre-built package for Python 3.12+. The
> quickest workaround is to install without the strict pins:
> `pip install dash dash-bootstrap-components flask-login psutil pandas plotly requests tldextract tqdm androguard==3.3.5`.
> See [05-known-issues.md](05-known-issues.md).

## 3. Get the data files

**This is the step that stops most people.** Janus refuses to start without two files
that are not in the repository because they are too large for Git:

| File | What it is |
|---|---|
| `androzoo.db` | A SQLite index of AndroZoo's catalogue: which APK versions exist for which package, and their hashes. Janus queries this to decide what to download. |
| `filtered_package_ids_with_counts10_ver.json` | The list of packages that have at least 10 versions available — i.e. the apps worth analysing over time. |

`index.py` currently tells you to run `python bootstrap_database.py`, **but that script
is not in the repository.** Until it is, ask the DIGISILK team for both files directly
and place them in the project folder next to `index.py`.

To browse pre-computed results as well, you also need a `precomputed_data/` folder
containing `metadata.json` and the saved analyses. Also obtained from the team.

## 4. Set a password

Janus has one shared login. Choose the username and password by setting these before
starting it:

```bash
export JANUS_USERNAME=yourname          # optional, defaults to "admin"
export JANUS_PASSWORD=choose-something  # Windows: set JANUS_PASSWORD=...
```

If you skip this, Janus generates a random password and prints it to the terminal on
startup — fine for a quick local look, but it changes every restart.

## 5. Start it

```bash
python index.py
```

Then open **http://127.0.0.1:8050** in your browser and log in.

Useful environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | `8050` | Port to serve on. |
| `HOST` | `127.0.0.1` | Set to `0.0.0.0` to allow access from other machines. |
| `DEBUG` | `True` | Set to `False` for anything other than local development. |
| `SECRET_KEY` | generated | Session signing key. Set it in any real deployment. |
| `JANUS_MAX_UPLOAD_MB` | `500` | Maximum size of an uploaded APK. |

## Which mode should I use?

- **Just looking at results?** Use **Connectivity (Pre-computed)**. Fast, no API key.
- **Analysing a specific app's history?** Use **Connectivity (Real-time)**. Needs an
  API key, and can take hours — start with two or three packages, not twenty.
- **Have APK files already?** Use **Connectivity (Upload APKs)**.

## Deploying it for other people

`python index.py` runs Flask's development server, which is single-process and not meant
for real use. For a shared deployment use a production WSGI server:

```bash
pip install gunicorn
gunicorn --workers 2 --timeout 3600 --bind 0.0.0.0:8050 index:server
```

The long `--timeout` matters: analyses legitimately run for a long time, and the default
30-second worker timeout would kill them. Because analysis runs in the web worker
itself, give it at least two workers so one long analysis doesn't block the whole site.

## Common problems

**`ModuleNotFoundError: No module named 'layouts'`**
You are running a version of the code from before the package structure was fixed, or
you are running it from a different directory. Run `python index.py` from inside the
project folder.

**"Required database files are missing"**
See [step 3](#3-get-the-data-files).

**The page loads but the logos are missing**
The layouts reference `assets/digisilk_countries.png` and `assets/sponsors.png`, but the
repository has no `assets/` folder. Cosmetic only — see
[05-known-issues.md](05-known-issues.md).

**An analysis appears to hang**
Downloads retry for a long time when AndroZoo is unreachable. Check the Analysis Log
panel, and see the retry-behaviour entry in
[05-known-issues.md](05-known-issues.md).
