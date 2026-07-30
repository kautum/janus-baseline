# Data: where it comes from and what it means

## AndroZoo

[AndroZoo](https://androzoo.uni.lu) is a research archive at the University of
Luxembourg holding millions of Android APKs collected from Google Play and other
stores, including **historical versions**: which is the part Janus depends on. Access
is free for academic use but requires an API key.

Janus uses two things from AndroZoo:

1. **The catalogue**, as a local SQLite database (`androzoo.db`), to answer "which
   versions of `kz.kaspi.mobile` exist, and what are their hashes?" without hitting the
   network.
2. **The APKs themselves**, downloaded on demand by SHA-256 hash.

Each catalogue entry carries a `vercode` (the app's own version number) and a
`vtscandate` (when the file was first scanned, used as a proxy for release date). Janus
orders versions chronologically by these.

### Required local files

| File | Contents | In Git? |
|---|---|---|
| `androzoo.db` | SQLite index of the AndroZoo catalogue | No, too large |
| `filtered_package_ids_with_counts10_ver.json` | Packages having ≥10 available versions | No |
| `precomputed_data/` | Previously computed analyses + `metadata.json` | No |

None of these are in the repository, and the bootstrap script `index.py` points you at
does not exist yet. Obtain them from the DIGISILK team. See
[03-setup.md](03-setup.md#3-get-the-data-files).

## What gets extracted from an APK

An APK is a ZIP archive. Inside it are one or more `.dex` files, the compiled Android
bytecode. Every DEX file contains a **string table**: all the string literals used by
the program, including hardcoded URLs and hostnames.

Janus reads that string table and keeps anything that looks like a web address, then
splits each one into three levels using
[`tldextract`](https://github.com/john-kurkowski/tldextract):

| Level | Example | Use |
|---|---|---|
| **URL** | `https://api.example.com/v2/pay` | Most specific; shows which endpoint. |
| **Subdomain** | `api.example.com` | Usually the right granularity for analysis. |
| **Domain** | `example.com` | Coarsest; groups all of an organisation's services. |

Two extraction engines are available (selectable in the UI):

- **Androguard**: full reverse-engineering library. Thorough, slow, memory-hungry.
- **DEXParser** (`utils/dex_parser.py`): reads the string table directly. Much faster,
  written specifically for this project.

They do not always return identical results. **Keep the parser consistent within a
single comparison**, or version-to-version differences may reflect the parser rather
than the app.

## Caching

Extracted results are cached in SQLite keyed by APK hash, so re-running an analysis on
packages you've already processed is fast. Downloaded APKs are also cached on disk.
Deleting `androzoo.db` therefore throws away cached *analysis results*, not just the
catalogue.

## How to read the output

The charts show **which endpoints appear in which versions**: typically a heatmap with
endpoints down one axis and versions across the other.

What you are looking for:

- **An endpoint that appears and then stops**: a service the app dropped.
- **An endpoint that appears partway through**: a new dependency, often after an
  acquisition, funding round, or regulatory change.
- **A cluster changing together**: usually a whole SDK being added or removed.

### Interpretation caveats

These matter, because it is easy to over-read this data:

1. **Presence in code is not proof of contact.** A URL in the string table means the
   code *can* reach that address, not that it did. Dead code and unused SDK defaults are
   common.
2. **Absence is not proof of absence.** Addresses built at runtime by joining strings
   together, or fetched from a server, will not appear. Obfuscated and packed apps hide
   much more.
3. **Version coverage is uneven.** AndroZoo has what it has. A gap in the timeline is
   usually a gap in the archive, not a period when the app stopped changing.
4. **The parser affects the result.** See above.

Janus is strongest as a way to *generate questions*, such as "why did this app start talking to
that host in 2019?", which are then answered with other evidence. The DIGISILK paper on
Kaspi (*Big Data & Society*, 2025) uses it this way, alongside interviews and document
analysis, rather than treating the endpoint list as a standalone finding.

## Uploaded APKs

In upload mode, files are written to `uploaded_apks/` and validated as real ZIP archives
before anything else touches them. They are removed when you remove them from the list
in the UI; note that files from an abandoned session are currently left behind. See
[05-known-issues.md](05-known-issues.md).
