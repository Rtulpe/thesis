import json
import sqlite3

from core.database import initialize_database
from scripts.import_data import import_yelp, split_mbti_users


def write_json_lines(path, records):
    path.write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )


def test_import_yelp_maps_business_users_and_reviews(tmp_path):
    raw = tmp_path / "yelp"
    raw.mkdir()
    write_json_lines(
        raw / "business.json",
        [
            {
                "business_id": "b1",
                "name": "Museum",
                "city": "Amsterdam",
                "latitude": 52.37,
                "longitude": 4.89,
                "categories": "Museums, Culture",
                "stars": 4.5,
                "hours": {"Monday": "09:00-17:00"},
            }
        ],
    )
    write_json_lines(
        raw / "user.json",
        [{"user_id": "u1", "name": "Traveller", "review_count": 3}],
    )
    write_json_lines(
        raw / "review.json",
        [
            {
                "review_id": "r1",
                "user_id": "u1",
                "business_id": "b1",
                "stars": 5,
                "text": "Thoughtful history exhibits.",
                "date": "2025-01-02",
            }
        ],
    )

    database = tmp_path / "user_state.db"
    initialize_database(database)
    report = import_yelp(raw, database)

    assert report == {"businesses": 1, "users": 1, "reviews": 1, "skipped": 0}
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM venues").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM interactions").fetchone()[0] == 1


def test_import_yelp_is_idempotent_and_skips_malformed_records(tmp_path):
    raw = tmp_path / "yelp"
    raw.mkdir()
    write_json_lines(
        raw / "business.json",
        [{"business_id": "b1", "name": "Museum", "city": "Amsterdam"}],
    )
    write_json_lines(raw / "user.json", [])
    write_json_lines(
        raw / "review.json",
        [{"review_id": "bad", "business_id": "missing", "user_id": "u1"}],
    )

    database = tmp_path / "user_state.db"
    initialize_database(database)
    first = import_yelp(raw, database)
    second = import_yelp(raw, database)

    assert first["skipped"] == 1
    assert second["skipped"] == 1
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM venues").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM interactions").fetchone()[0] == 0


def test_split_mbti_users_is_disjoint_and_reproducible():
    records = [{"user_id": f"u{i}", "type": "INTJ"} for i in range(10)]

    first = split_mbti_users(records, test_fraction=0.2, seed=7)
    second = split_mbti_users(records, test_fraction=0.2, seed=7)

    assert first == second
    train_ids = {record["user_id"] for record in first["train"]}
    test_ids = {record["user_id"] for record in first["test"]}
    assert train_ids.isdisjoint(test_ids)
    assert len(first["test"]) == 2
