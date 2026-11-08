import sqlite3

from core.database import initialize_database


def test_initialize_database_creates_expected_schema_and_seed_data(tmp_path):
    database_path = tmp_path / "user_state.db"

    initialize_database(database_path, seed=True)

    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        assert tables == {"users", "venues", "interactions"}

        user_count = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        venue_count = connection.execute("SELECT COUNT(*) FROM venues").fetchone()[0]
        interaction_count = connection.execute(
            "SELECT COUNT(*) FROM interactions"
        ).fetchone()[0]

        assert user_count > 0
        assert venue_count > 0
        assert interaction_count > 0


def test_seeded_interactions_reference_existing_users_and_venues(tmp_path):
    database_path = tmp_path / "user_state.db"

    initialize_database(database_path, seed=True)

    with sqlite3.connect(database_path) as connection:
        orphaned_interactions = connection.execute(
            """
            SELECT COUNT(*)
            FROM interactions AS interactions
            LEFT JOIN users ON users.user_id = interactions.user_id
            LEFT JOIN venues ON venues.venue_id = interactions.venue_id
            WHERE users.user_id IS NULL OR venues.venue_id IS NULL
            """
        ).fetchone()[0]

    assert orphaned_interactions == 0
