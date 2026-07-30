# Janus

A fork of [digisilk/janus-baseline](https://github.com/digisilk/janus-baseline), the app
analysis tool built by the [DIGISILK](https://www.digisilk.eu/) project in the Department
of Digital Humanities at King's College London. Janus is their work, funded by the
European Research Council and led by Dr Elisa Oreglia. Everything here stays under
Apache 2.0, the same licence as upstream.

I put this together while applying for the junior software developer role on Janus. I
don't know what the team already has planned, so I haven't tried to guess at a roadmap.
What I could do was read the code properly, get it running, fix what was broken, and
write down what I learned so that the next person doesn't have to work it out from
scratch.

You are looking at the `fix/bootable-and-secure-baseline` branch, which is where all of
this lives. The [`main`](../../tree/main) branch is left exactly as upstream has it, so
you can diff the two to see precisely what changed.

## The documentation is the main thing here

Janus has been built by a rotating cast of students and researchers rather than a
standing engineering team. That shows. The code is undocumented in places, the README
described a version of the app that no longer exists, and anyone joining has to
reconstruct the reasoning from the source. The upstream README says as much, promising
"additional guidance" for people who aren't familiar with git or Python.

So I wrote that guidance. It's in [`docs/`](docs/):

- [What Janus is and why it exists](docs/01-project.md), including the research it
  supports and what its output can and cannot be used to claim
- [Architecture](docs/02-architecture.md): how the code is laid out, how a request moves
  through it, and why it's shaped the way it is
- [Setup](docs/03-setup.md), written for someone who doesn't consider themselves a
  programmer, with a section on deploying it properly
- [The data](docs/04-data.md): where the APKs come from, what gets extracted, and how to
  read the charts without over-reading them
- [Known issues](docs/05-known-issues.md): every defect I found, with file references,
  plus the things I checked that turned out to be fine

There's also a [`CLAUDE.md`](CLAUDE.md) at the root. Coding assistants read that file
automatically, so anyone using one on this repository starts from an accurate picture of
the system rather than inferring it from whichever file they happened to open first. It
covers the same ground as `docs/` in condensed form, plus the conventions the codebase
already follows.

I spent more time on this than on the code changes, on purpose. Fixing a bug helps once.
Writing down how the system works helps every time someone new arrives, and for a project
staffed by students on short placements that happens a lot.

## What I fixed

The app didn't run from a clean clone. Every module imported `layouts`, `callbacks`,
`logic` and `utils` as packages, but all the files sat flat at the repository root, so a
fresh checkout died on the first import. Two modules the code still referenced,
`config.py` and `login_callbacks.py`, had been deleted. Four libraries the app imports
were missing from `requirements.txt`. I moved the files into the structure the code
already expected, restored minimal versions of the two deleted modules, and added the
missing dependencies. It boots to the login screen now.

The more serious problem was authentication. `display_page()` in `index.py` picks which
layout to render based on whether the user is logged in, which looks like access control
but isn't. Dash callbacks are ordinary HTTP POSTs to `/_dash-update-component`, and every
callback is registered globally when its module is imported. Anyone who knew the
component IDs, which Dash's own `/_dash-dependencies` endpoint lists, could run the
analysis pipeline, the file upload handler and the pre-computed data access without ever
logging in. I put a guard on the single endpoint every callback passes through, so a
callback added next year is covered without anyone needing to remember.

Alongside that:

- **Path traversal in APK upload.** The uploaded filename went into a server path with no
  sanitisation, so a crafted name could write outside the upload directory. Since that
  stored path is later passed to `os.remove()`, it meant arbitrary file deletion too.
- **No upload validation.** No size cap, and no check that an APK was even a ZIP archive.
  One large request could exhaust memory and disk.
- **A race in session tracking.** `active_sessions` was mutated without a lock while the
  stale session cleaner iterated over it on every request. When those collide it raises
  `dictionary changed size during iteration` inside the page routing callback, which
  breaks the site for everyone rather than only the person running an analysis.
- **Leaked worker processes.** `close()` and `join()` sat after `starmap()` with no
  `try`/`finally`, so one malformed APK crashing a worker orphaned the entire pool. Those
  accumulate over the long unattended runs this tool is built for.
- **`/logout` returned 404.** The navigation bar has always linked to it, but the route
  didn't exist, so logging out quietly left you logged in.
- **`/admin/status` was unauthenticated**, and because it was defined inside
  `if __name__ == "__main__":` it didn't exist at all under a production WSGI server.

The full detail, including issues I found and chose not to fix, is in
[docs/05-known-issues.md](docs/05-known-issues.md).

## Checking it

```bash
python run_tests.py
```

Three suites, with no test framework to install first:

| Suite | Covers |
|---|---|
| `test_auth_required.py` | All 37 registered callbacks refuse an unauthenticated request, the login page stays reachable, and the guard fails closed on malformed input |
| `test_upload_safety.py` | Path traversal, non-APK payloads, malformed uploads |
| `test_concurrency.py` | Eight threads running against a concurrent session cleaner, plus stale cleanup and the capacity gate |

The auth suite reads Dash's live callback registry instead of a list I typed out, so a
newly added callback is covered automatically. That came out of reviewing my own work:
the first version named three callbacks by hand and two of those names didn't exist, so
the test was passing through the fail-closed path without ever touching a real callback.

I also checked that the tests fail when they should. Breaking each fix in turn, first the
auth guard, then the lock, then the filename sanitisation, makes exactly one suite fail
each time and leaves the other two passing. A test that never fails is decoration.

Past the automated checks, I ran the app and used it: logged in, opened the analysis
pages, watched the capacity indicator update, logged out again.

## What I left alone on purpose

`plotter.py`, `templates/` and the three HTML files at the repository root are dead code,
left over from the Flask version of this app that the old README describes. Nothing
imports or renders them. I haven't deleted them. Removing files is a maintainer's call,
and someone on the team may know a reason to keep them that I don't. They're listed in
the known issues instead.

I've also left the duplication between the three analysis modes alone. Roughly two thirds
of `logic/` is copy-pasted between them and consolidating it is worth doing, but those
functions produce the figures that end up in published papers. That's a change to make
carefully, one module at a time, checking the output is identical at each step. It isn't
a change to make in a first pull request by someone who hasn't met the team yet.

Same reasoning for the download retry loop. It can block for hours on one unreachable
APK, and the timeout that would stop it was only ever added to one of the three copies. I
described the fix in the known issues rather than attempting it, because getting it wrong
means an analysis quietly returns incomplete results, and for a researcher that's worse
than an obvious failure.

## A note on proportions

The code changes are deliberately small: 323 lines added and 81 removed across 24 files,
against 444 lines of tests and 725 of documentation. Research software produces numbers
that end up in published work, so I kept the behavioural changes narrow and evidenced,
and put the effort into making the system legible instead.

Two files Janus needs at startup, `androzoo.db` and
`filtered_package_ids_with_counts10_ver.json`, aren't in the repository and are too large
for git. `index.py` tells you to run `bootstrap_database.py`, which isn't here either. I
documented what both files hold and what they're for, but actually getting them means
asking the DIGISILK team. Writing a real bootstrap script looks like an obvious early
task.
