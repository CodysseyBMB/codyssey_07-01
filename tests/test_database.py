import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from app.database import get_connection, init_db


class DatabaseInitializationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "nested" / "test.db"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_init_db_creates_users_table_with_expected_schema(self) -> None:
        init_db(self.database_path)

        self.assertTrue(self.database_path.exists())
        with closing(get_connection(self.database_path)) as connection:
            columns = {
                row["name"]: row
                for row in connection.execute("PRAGMA table_info(users)").fetchall()
            }

            self.assertEqual(
                list(columns),
                ["id", "username", "password_hash", "created_at"],
            )
            self.assertEqual(columns["id"]["type"], "INTEGER")
            self.assertEqual(columns["id"]["pk"], 1)
            self.assertEqual(columns["username"]["notnull"], 1)
            self.assertEqual(columns["password_hash"]["notnull"], 1)
            self.assertEqual(columns["created_at"]["notnull"], 1)
            self.assertEqual(columns["created_at"]["dflt_value"], "CURRENT_TIMESTAMP")

            unique_indexes = [
                row
                for row in connection.execute("PRAGMA index_list(users)").fetchall()
                if row["unique"] == 1
            ]
            self.assertEqual(len(unique_indexes), 1)
            index_name = unique_indexes[0]["name"]
            indexed_columns = [
                row["name"]
                for row in connection.execute(
                    f'PRAGMA index_info("{index_name}")'
                ).fetchall()
            ]
            self.assertEqual(indexed_columns, ["username"])

    def test_required_and_unique_constraints_are_enforced(self) -> None:
        init_db(self.database_path)

        with closing(get_connection(self.database_path)) as connection:
            connection.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                ("Alice_01", "hashed-password"),
            )
            connection.commit()

            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    ("alice_01", "another-hash"),
                )
            connection.rollback()

            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    (None, "hashed-password"),
                )
            connection.rollback()

            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    ("bob_02", None),
                )

    def test_repeated_initialization_preserves_existing_users(self) -> None:
        init_db(self.database_path)
        with closing(get_connection(self.database_path)) as connection:
            connection.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                ("alice_01", "hashed-password"),
            )
            connection.commit()

        init_db(self.database_path)

        with closing(get_connection(self.database_path)) as connection:
            user = connection.execute(
                "SELECT username, password_hash, created_at FROM users"
            ).fetchone()
            foreign_keys_enabled = connection.execute(
                "PRAGMA foreign_keys"
            ).fetchone()[0]

            self.assertIsNotNone(user)
            self.assertEqual(user["username"], "alice_01")
            self.assertEqual(user["password_hash"], "hashed-password")
            self.assertTrue(user["created_at"])
            self.assertEqual(foreign_keys_enabled, 1)


if __name__ == "__main__":
    unittest.main()
