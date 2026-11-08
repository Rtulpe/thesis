# Step 12: Real Dataset Ingestion

## Scope implemented

- Added `scripts/import_data.py` for Yelp Open Dataset JSONL files:
  `business.json`, `user.json`, and `review.json`.
- Added support for the downloaded `yelp_academic_dataset_*.json` filenames.
- Added scoped city/category/business/review limits so the multi-GB dataset is not
  imported wholesale.
- Added two-pass user selection so only users referenced by retained reviews enter
  the tourism database.
- Reworked the scoped import to avoid the expensive preliminary review scan and
  full user-file scan by default.
- Added an early return for zero matching businesses, review-derived user rows,
  batched inserts, and opt-in `--enrich-user-metadata` for the multi-GB user file.
- Fixed a foreign-key batching defect where interaction rows could flush before
  their newly discovered users; pending users are now flushed before interactions.
- Added review-scan progress reporting to stderr via `--progress-every`.
- Mapped businesses to venues, users to user profiles, and reviews to interactions.
- Normalized coordinates, ratings, timestamps, categories, and opening hours.
- Added foreign-key-safe review handling, malformed-record skip counts, and idempotent upserts.
- Added a separate deterministic MBTI user split utility without importing MBTI records into tourism tables.
- Added importer fixtures and integration tests.

## Files changed

- `scripts/__init__.py`
- `scripts/import_data.py`
- `tests/test_import_data.py`

## Decisions

- Yelp input is expected under `data/raw/yelp/` by default, matching the agreed path.
- Both generic fixture names and Yelp's actual academic filenames are accepted.
- CLI imports require explicit `--cities`; optional categories and caps bound the import.
- Yelp reviews are streamed twice: once to identify retained user IDs, then to import
  bounded interactions without holding the dataset in memory.
- The default path streams reviews once and creates minimal users from retained
  review IDs; full Yelp names and source review counts require the optional metadata
  enrichment scan.
- MBTI input is reserved for `data/raw/mbti/`; this step provides only a leakage-safe split utility and does not mix MBTI data with tourism interactions.
- Imports are streaming JSONL rather than loading complete files into memory.
- Existing records are updated by stable Yelp IDs; interactions are deduplicated by user, venue, and review text.
- Malformed or orphaned records are counted and skipped, while missing source files fail explicitly.

## Validation

- `.venv/bin/python -m pytest tests/test_import_data.py -q` — `3 passed`.
- `.venv/bin/python -m pytest tests/test_import_data.py -q` — `4 passed`.
- `.venv/bin/python -m pytest -q` — `67 passed`.
- `.venv/bin/python -m scripts.import_data --input data/raw/yelp --database /tmp/yelp-las-vegas-check.db --cities "Las Vegas" --max-businesses 10000 --max-reviews-per-business 100` — completed with zero matches without scanning review/user data.
- `.venv/bin/python -m pytest -q` — `70 passed`.
- `.venv/bin/python -m pytest tests/test_import_data.py -q` — `7 passed`.
- `.venv/bin/python -m pytest -q` — `72 passed`.
- The real Philadelphia command reached the review scan but exceeded a five-minute
  bounded validation timeout; the database remained unchanged and consistent..
- `.venv/bin/python -m scripts.import_data --help` — confirmed scoped CLI options.

## Remaining risks and follow-up

- The real Yelp files are present under `data/raw/yelp/`, but no import was run without an explicit city scope.
- For matched cities, the full review file still must be streamed once because Yelp
  JSONL has no business index. A future index/preprocessing step could reduce that
  scan for repeated imports.
- The default batch size and progress output are designed for the large Philadelphia
  import; a failed or interrupted SQLite transaction leaves the prior database
  state intact.
- Yelp business opening-hour strings with overnight or multiple intervals require additional normalization.
- MBTI classifier training remains deferred by the agreed scope.
