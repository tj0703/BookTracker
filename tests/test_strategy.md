# E2E Test Strategy — BookTracker CLI

Prepared by the `software-tester` role. This document scopes end-to-end
testing for the whole codebase; it does not touch implementation code.

## Current coverage — what's already covered vs. missing

The existing 19 tests (`tests/test_*.py`) are **component-level, not e2e**:
they run everything in-process via Click's `CliRunner`, with Finna HTTP
calls mocked at the `finna.requests.get` level. That's the right layer for
unit/integration coverage, but it never exercises:

- The actual installed `app-cli` console-script entry point (packaging
  correctness).
- **Cross-process persistence** — every existing test runs in a single
  Python process, so `storage.py`'s read-then-write-JSON-file cycle across
  separate CLI invocations (the real usage pattern: `app-cli book add` now,
  `app-cli book recommend` next week) is never actually verified.
- The real Finna API contract (mocks encode our *assumption* of the
  response shape — if Finna's API drifts, unit tests won't catch it).

## Proposed e2e layer (additive — does not replace existing tests)

### Step 1: Subprocess-driven CLI tests (`tests/e2e/test_cli_e2e.py`)

Invoke the installed `app-cli` binary via `subprocess.run`, not
`CliRunner`, with `APP_CLI_DATA_DIR` pointed at a fresh temp dir per test:

- `book add` -> `book list` -> `book recommend` as **three separate
  subprocess calls**, asserting the JSON file on disk persists and is read
  correctly across invocations.
- Full command help output (`app-cli --help`, `app-cli book --help`)
  doesn't error — catches Click wiring mistakes that in-process tests can
  mask.
- Bad input (`--rating 9`, malformed `--completed` date) exits non-zero
  with a clean error, not a traceback, when run as a real subprocess
  (validates Click's actual error-output path, not just exit code).
- The 10-rated-book gate end-to-end: add 9 rated books across 9 separate
  subprocess calls, confirm `recommend` still reports "9/10", add a 10th,
  confirm it unlocks — this is the scenario most likely to break if
  storage state handling has any in-process-only assumption baked in.

### Step 2: Real-network Finna smoke test (`tests/e2e/test_finna_live.py`)

One narrow test hitting the actual `api.finna.fi` endpoint (e.g., resolve
a well-known title like "Harry Potter", assert it returns *some* subjects
and doesn't error) — guards against Finna changing its response schema out
from under `_community_rating`/subject-parsing logic. Marked
`@pytest.mark.e2e_live` and excluded from the default `pytest` run
(`-m "not e2e_live"`) so normal test runs stay fast and non-flaky; run
manually or on a scheduled job, not per-commit.

### Step 3: Fresh-install packaging check

`pip install .` (not `-e`) into a throwaway venv, run `app-cli hello` —
catches `pyproject.toml`/entry-point mistakes that editable installs
silently paper over. Better as a CI script step than a pytest test, since
it manages its own venv lifecycle.

## Out of scope

- Testing Finna's own data quality/coverage (that's their system, not ours).
- Load/performance testing — this is a single-user local CLI, not a service.
- Fixing any issues this strategy surfaces — those get reported back to
  `software-developer`, not patched here.

## Status

- [x] Step 1: subprocess-driven CLI e2e tests — `tests/e2e/test_cli_e2e.py`
- [x] Step 2: real-network Finna smoke test — `tests/e2e/test_finna_live.py`
      (marker `e2e_live`, excluded from default run via `addopts` in
      `pyproject.toml`). Found a real bug on first run — see bug report below.
- [x] Step 3: fresh-install packaging check — `tests/e2e/check_fresh_install.py`
      (standalone script, not pytest-collected — run manually or as a CI
      step: `python tests/e2e/check_fresh_install.py`). Ran it: creates a
      throwaway venv, does a real non-editable `pip install .`, and runs
      the installed `app-cli` console-script entry point end to end.
      Result: PASS — packaging and entry-point wiring are correct.

## Bug found by Step 2 (reported, not fixed — outside tester scope)

**What was tested**: `finna.search_by_subjects()` against the real Finna
API (`tests/e2e/test_finna_live.py::test_search_by_subjects_against_real_finna_api`),
run via `pytest -m e2e_live`.

**Expected**: candidates list built successfully for any real subject facet
value returned by Finna.

**Actual**: crashes with `AttributeError: 'list' object has no attribute
'keys'` in `finna.py`, `search_by_subjects()`, at:
`primary_authors = list((record.get("authors") or {}).get("primary", {}).keys())`

**Root cause (confirmed via direct API query)**: Finna's `authors.primary`
field is not consistently a dict — for records with no primary author
(e.g. the record titled "Chuggington : Klik-klok" under subject
`(fiktiivinen hahmo)`), Finna returns `"primary": []` (an empty **list**),
not `{}` (empty dict). `.get("primary", {})` only supplies the `{}`
default when the key is *missing*, not when it's present but holds a list,
so `.keys()` is called on a list and raises.

**Severity**: high for the `recommend` feature specifically — any subject
query that happens to surface an authorless record will currently crash
the whole `book recommend` command (the per-subject `try/except` added
earlier only guards the HTTP request itself, not this parsing step
afterward).

**Status: fixed** by `software-developer` — added `_primary_authors()` in
`finna.py`, handling `authors.primary` as either a dict (name -> role) or a
list (Finna's shape when there's no primary author). Regression test added
(`test_search_by_subjects_handles_authors_primary_as_empty_list`), and the
live `e2e_live` tests were re-run against the real API and pass, including
a direct re-run of the exact query that originally crashed
(`(fiktiivinen hahmo)`, which contains the "Chuggington : Klik-klok"
record with no primary author).

Executed one step at a time; this file is updated as each step lands.

## Coverage added for `book search title/author`

- **Zero-network wiring checks** (`tests/e2e/test_cli_e2e.py`): `--help`
  output for `book search`, `book search title`, `book search author`, plus
  missing-argument exit behavior for both subcommands — all via real
  subprocess, no network required, so these stay in the fast default suite.
- **Live-network coverage** (`tests/e2e/test_finna_live.py`,
  `e2e_live`-marked): `search_by_title`/`search_by_author` against the real
  API, asserting the full result shape (`title, author, year, format,
  community_rating, locations`), the `locations` cap (`MAX_LOCATIONS`), and
  a no-match query returning `[]`. Ran against the real API: 5/5 pass.
- **Not added**: a subprocess-level (real console-script) live test for
  `book search`. It would need real network like the `finna.py`-level live
  tests above, but adds no coverage beyond what the zero-network wiring
  checks (Click plumbing) and the `finna.py`-level live tests (API
  contract) already cover separately — would only be testing that those
  two already-verified layers compose, which is a low-value, network-flaky
  addition. Flagging the omission explicitly rather than silently skipping it.
