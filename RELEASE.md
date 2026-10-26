# Final local release

Create a clean Python 3.12 environment and install the pinned local dependencies as described in
[SETUP.md](SETUP.md). Place the authorized data bundle in `data/`, or set `MTAH_DATA_DIR` to its
location. From the repository root, regenerate the proposed release with:

```bash
.venv/bin/python scripts/package_submission.py --team polyamal --no-cache
```

`--no-cache` makes this a clean regeneration from the supplied tactical inputs. The command runs
the unchanged C0 method, writes `data/predictions/release/polyamal.csv`, validates that exact file
with the unchanged organizer validator, copies `TECHNICAL_REPORT.md` to
`data/predictions/release/polyamal.md`, and writes a local
`data/predictions/release/polyamal.manifest.json` containing source/config/runtime identifiers
and file digests. It prints only a fixed pass/fail result and does not score against labels.

All three generated files remain under ignored `data/`; do not add them to Git or publish the
manifest. The CSV and Markdown report are the intended upload artifacts. The registered name is confirmed as `polyamal` (five members). The emailed submission form has not been received, and the exact
deadline cutoff time/timezone is not stated in the repository. Uploading/publishing is a separate
manual step.

Each file is written atomically, but the three files are not a transactional bundle. A failure
may leave a CSV or report from that attempt beside an older manifest. Only use a bundle after
the command reports PASS; rerun the command after any failure. Keep the manifest private and
compare its CSV and report digests when checking that a bundle belongs together.

## Local verification completed

On 2026-10-26, the existing environment and a newly installed isolated Python 3.12.1
environment regenerated the package independently with `--no-cache`. The CSV and report
bytes matched between environments; the CSV also matched the selected T08 C0 output.
Both exact generated CSVs passed the unchanged official validator. All 99 asset-free tests
passed in the clean environment, and pinned dependencies passed `pip check`.

Private checksums and source identifiers are recorded in the local manifest and
`data/predictions/release/polyamal.verification.json`; neither belongs in Git. This check
establishes reproduction on the tested platform, not performance on unseen match labels.

The user authorized fork publication for teammate sharing on 2026-10-26. The source and
technical document are the submission candidate described in [HANDOFF.md](HANDOFF.md);
publication state is recorded in PLAN.md. Generated private files stay local. The emailed
form and exact cutoff are pending, and no form submission has been performed.
