# Step 12: Real Dataset Ingestion

## Scope implemented

- Added `scripts/import_data.py` for Yelp Open Dataset JSONL files:
  `business.json`, `user.json`, and `review.json`.
- Added support for the downloaded `yelp_academic_dataset_*.json` filenames.
- Added scoped city/category/business/review limits so the multi-GB dataset is not
  imported wholesale.
- Added two-pass user selection so only users referenced by retained reviews enter
  the tourism database.
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
- MBTI input is reserved for `data/raw/mbti/`; this step provides only a leakage-safe split utility and does not mix MBTI data with tourism interactions.
- Imports are streaming JSONL rather than loading complete files into memory.
- Existing records are updated by stable Yelp IDs; interactions are deduplicated by user, venue, and review text.
- Malformed or orphaned records are counted and skipped, while missing source files fail explicitly.

## Validation

- `.venv/bin/python -m pytest tests/test_import_data.py -q` — `3 passed`.
- `.venv/bin/python -m pytest tests/test_import_data.py -q` — `4 passed`.
- `.venv/bin/python -m pytest -q` — `67 passed`.
- `.venv/bin/python -m scripts.import_data --help` — confirmed scoped CLI options.

## Remaining risks and follow-up

- The real Yelp files are present under `data/raw/yelp/`, but no import was run without an explicit city scope.
- Yelp business opening-hour strings with overnight or multiple intervals require additional normalization.
- MBTI classifier training remains deferred by the agreed scope.
