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


class ChatsTableTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "nested" / "test.db"
        init_db(self.database_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _insert_user(self, connection: sqlite3.Connection, username: str) -> int:
        cursor = connection.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, "hashed-password"),
        )
        connection.commit()
        return cursor.lastrowid

    def _insert_chat(
        self,
        connection: sqlite3.Connection,
        user_id: int,
        question: str,
        answer: str,
    ) -> int:
        cursor = connection.execute(
            "INSERT INTO chats (user_id, question, answer) VALUES (?, ?, ?)",
            (user_id, question, answer),
        )
        connection.commit()
        return cursor.lastrowid

    def test_init_db_creates_chats_table_with_expected_schema(self) -> None:
        with closing(get_connection(self.database_path)) as connection:
            columns = {
                row["name"]: row
                for row in connection.execute("PRAGMA table_info(chats)").fetchall()
            }

            self.assertEqual(
                list(columns),
                ["id", "user_id", "question", "answer", "created_at"],
            )
            self.assertEqual(columns["id"]["type"], "INTEGER")
            self.assertEqual(columns["id"]["pk"], 1)
            self.assertEqual(columns["user_id"]["notnull"], 1)
            self.assertEqual(columns["question"]["notnull"], 1)
            self.assertEqual(columns["answer"]["notnull"], 1)
            self.assertEqual(columns["created_at"]["notnull"], 1)
            self.assertEqual(columns["created_at"]["dflt_value"], "CURRENT_TIMESTAMP")

    def test_chats_reference_users_with_cascade_delete(self) -> None:
        with closing(get_connection(self.database_path)) as connection:
            foreign_keys = connection.execute(
                "PRAGMA foreign_key_list(chats)"
            ).fetchall()

            self.assertEqual(len(foreign_keys), 1)
            self.assertEqual(foreign_keys[0]["from"], "user_id")
            self.assertEqual(foreign_keys[0]["table"], "users")
            self.assertEqual(foreign_keys[0]["to"], "id")
            self.assertEqual(foreign_keys[0]["on_delete"], "CASCADE")

    def test_chats_index_supports_lookup_by_user_and_time(self) -> None:
        with closing(get_connection(self.database_path)) as connection:
            indexes = connection.execute("PRAGMA index_list(chats)").fetchall()

            self.assertEqual(len(indexes), 1)
            index_name = indexes[0]["name"]
            indexed_columns = [
                row["name"]
                for row in connection.execute(
                    f'PRAGMA index_info("{index_name}")'
                ).fetchall()
            ]
            self.assertEqual(indexed_columns, ["user_id", "created_at"])

    def test_chats_are_stored_and_retrieved_for_each_user(self) -> None:
        with closing(get_connection(self.database_path)) as connection:
            alice_id = self._insert_user(connection, "alice_01")
            bob_id = self._insert_user(connection, "bob_02")

            self._insert_chat(connection, alice_id, "배포 방법 알려줘", "이렇게 합니다")
            self._insert_chat(connection, alice_id, "배포 방법 알려줘", "다시 설명하면")
            self._insert_chat(connection, bob_id, "배포 방법 알려줘", "안녕하세요")

            alice_chats = connection.execute(
                "SELECT user_id, question, answer, created_at FROM chats "
                "WHERE user_id = ? ORDER BY created_at DESC, id DESC",
                (alice_id,),
            ).fetchall()

            self.assertEqual(len(alice_chats), 2)
            self.assertEqual(
                [row["answer"] for row in alice_chats],
                ["다시 설명하면", "이렇게 합니다"],
            )
            for row in alice_chats:
                self.assertEqual(row["user_id"], alice_id)
                self.assertTrue(row["created_at"])

    def test_foreign_key_and_check_constraints_are_enforced(self) -> None:
        with closing(get_connection(self.database_path)) as connection:
            user_id = self._insert_user(connection, "alice_01")

            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO chats (user_id, question, answer) VALUES (?, ?, ?)",
                    (user_id + 1000, "질문", "응답"),
                )
            connection.rollback()

            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO chats (user_id, question, answer) VALUES (?, ?, ?)",
                    (None, "질문", "응답"),
                )
            connection.rollback()

            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO chats (user_id, question, answer) VALUES (?, ?, ?)",
                    (user_id, "", "응답"),
                )
            connection.rollback()

            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO chats (user_id, question, answer) VALUES (?, ?, ?)",
                    (user_id, "질문", ""),
                )

    def test_deleting_user_removes_only_their_chats(self) -> None:
        with closing(get_connection(self.database_path)) as connection:
            alice_id = self._insert_user(connection, "alice_01")
            bob_id = self._insert_user(connection, "bob_02")
            self._insert_chat(connection, alice_id, "질문", "응답")
            self._insert_chat(connection, bob_id, "질문", "응답")

            connection.execute("DELETE FROM users WHERE id = ?", (alice_id,))
            connection.commit()

            remaining = connection.execute("SELECT user_id FROM chats").fetchall()

            self.assertEqual([row["user_id"] for row in remaining], [bob_id])

    def test_repeated_initialization_preserves_existing_chats(self) -> None:
        with closing(get_connection(self.database_path)) as connection:
            user_id = self._insert_user(connection, "alice_01")
            self._insert_chat(connection, user_id, "질문", "응답")

        init_db(self.database_path)

        with closing(get_connection(self.database_path)) as connection:
            chat = connection.execute(
                "SELECT user_id, question, answer, created_at FROM chats"
            ).fetchone()

            self.assertIsNotNone(chat)
            self.assertEqual(chat["question"], "질문")
            self.assertEqual(chat["answer"], "응답")
            self.assertTrue(chat["created_at"])

if __name__ == "__main__":
    unittest.main()
