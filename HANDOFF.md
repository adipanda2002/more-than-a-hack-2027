# Polyamal teammate and submission handoff

Team **polyamal**, five members. This is the current reproducible submission candidate,
using unchanged C0. The code, pinned runtime and technical report belong in the public
repository; match assets, generated labels and private verification manifests stay local.

## Start here

```bash
git clone https://github.com/adipanda2002/more-than-a-hack-2027.git
cd more-than-a-hack-2027
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-local.txt
.venv/bin/python -m unittest discover -s tests -q
```

Use Python 3.12; the verified environment is 3.12.1. On Windows use
`.venv\Scripts\python.exe`. Obtain the authorized competition bundle separately and extract
it according to [data/README.md](data/README.md). Do not put a private download link in Git.
If the bundle is elsewhere, set `MTAH_DATA_DIR` or supply `--data-dir /path/to/bundle`.

From the repository root, generate the same candidate and validate its exact CSV:

```bash
.venv/bin/python scripts/package_submission.py --team polyamal --no-cache
```

| Local file | Purpose |
|---|---|
| `data/predictions/release/polyamal.csv` | Possession file for the organizer form |
| `data/predictions/release/polyamal.md` | Team-named technical document for the form |
| `data/predictions/release/polyamal.manifest.json` | Private config/runtime/source/file digests; do not upload to Git |
| `data/predictions/release/polyamal.verification.json` | Private audit of the original two-environment verification; not created by the normal package command |

The Markdown upload is copied from [TECHNICAL_REPORT.md](TECHNICAL_REPORT.md). It describes
the actual algorithm and limitations. [RELEASE.md](RELEASE.md) covers bundle handling and
verification; [SETUP.md](SETUP.md) covers setup and additional checks. Only use generated
files after the package command reports PASS. Never edit possession labels by hand.

## Current evidence and limits

The initial package passed 99 asset-free tests and exact official CSV validation. Independent
no-cache generation in two Python environments produced identical CSV/report bytes. C0 passed
23 synthetic contracts and 97 invariance checks; the two frozen ablations were rejected.
These are engineering results, not measured real-match accuracy or evidence of qualification.
In-pitch and unavailable-ball stoppages remain a known weakness. No independent real-match
benchmark was validated, and public labels were not used to select or tune this candidate.

Read [PLAN.md](PLAN.md) and [AGENTS.md](AGENTS.md) before further work. If teammates change
source or the report, regenerate and revalidate both team-named upload files together;
the old local manifest then no longer describes the changed source. Follow the bounded
evaluation protocol rather than tuning on the public five minutes.

## Resume when the submission form arrives

1. Read PLAN.md, check the working tree and published revision, and obtain the emailed
   form and exact cutoff time/timezone. The published deadline is November 17, 2026;
   the repository does not specify its hour/timezone.
2. Confirm whether teammates made changes since this candidate. Resolve and verify any
   intended changes before publication; otherwise retain unchanged C0.
3. Regenerate with the command above, confirm PASS, and verify the local manifest matches
   the exact CSV/report being uploaded. Do not reuse an old pair after changing the code.
4. Supply the public fork URL, team name **polyamal**, and the exact team-named CSV/Markdown
   through the organizer's approved form. Record the source commit used for reproduction.
5. Confirm the response was accepted and record the submission date/revision in PLAN.md.
   No form submission has been performed yet.

The local assets, environment, selected candidate and verification records are retained so
work can resume here. No scheduled background work or monitoring is configured.
