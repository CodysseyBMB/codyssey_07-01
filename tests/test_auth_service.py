import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from app.database import get_connection, init_db
from app.services.auth import (
    AuthValidationError,
    DuplicateUsernameError,
    authenticate_user,
    get_user_by_id,
    register_user,
)


class AuthServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "test.db"
        init_db(self.database_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_register_normalizes_username_and_stores_only_password_hash(self) -> None:
        valid_password = "Pass-word_123!"
        user = register_user(
            "  Alice_01  ",
            valid_password,
            valid_password,
            self.database_path,
        )

        self.assertEqual(user.username, "alice_01")
        self.assertEqual(get_user_by_id(user.id, self.database_path), user)

        with closing(get_connection(self.database_path)) as connection:
            stored_password = connection.execute(
                "SELECT password_hash FROM users WHERE id = ?",
                (user.id,),
            ).fetchone()["password_hash"]

        self.assertNotEqual(stored_password, valid_password)
        self.assertTrue(stored_password.startswith("$argon2id$"))
        self.assertEqual(
            authenticate_user(
                "ALICE_01",
                valid_password,
                self.database_path,
            ),
            user,
        )
        self.assertIsNone(
            authenticate_user(
                "alice_01",
                valid_password.lower(),
                self.database_path,
            )
        )

    def test_username_policy_rejects_invalid_values(self) -> None:
        invalid_usernames = (
            "abcd",
            "a" * 21,
            "alice.01",
            "앨리스",
        )

        for username in invalid_usernames:
            with self.subTest(username=username):
                with self.assertRaises(AuthValidationError) as error:
                    register_user(
                        username,
                        "password123",
                        "password123",
                        self.database_path,
                    )
                self.assertEqual(error.exception.field, "username")

            with closing(get_connection(self.database_path)) as connection:
                count = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            self.assertEqual(count, 0)

    def test_username_policy_accepts_boundaries_hyphen_and_underscore(self) -> None:
        minimum_user = register_user(
            "a-1_b",
            "password123",
            "password123",
            self.database_path,
        )
        maximum_user = register_user(
            "a" * 20,
            "password123",
            "password123",
            self.database_path,
        )

        self.assertEqual(minimum_user.username, "a-1_b")
        self.assertEqual(maximum_user.username, "a" * 20)

    def test_password_policy_enforces_length_boundaries_and_confirmation(self) -> None:
        password_8 = "a" * 8
        password_16 = "Abcdefgh1234!@#$"

        register_user(
            "min_user",
            password_8,
            password_8,
            self.database_path,
        )
        register_user(
            "max_user",
            password_16,
            password_16,
            self.database_path,
        )

        for username, password in (
            ("short_user", "abc123!"),
            ("long_user", "a" * 17),
            ("space_user", "pass word1"),
            ("unicode_user", "비밀번호12345"),
            ("number_user", "12345678"),
        ):
            with self.subTest(password_length=len(password)):
                with self.assertRaises(AuthValidationError) as error:
                    register_user(
                        username,
                        password,
                        password,
                        self.database_path,
                    )
                self.assertEqual(error.exception.field, "password")

        with self.assertRaises(AuthValidationError) as error:
            register_user(
                "mismatch_user",
                "password123",
                "password456",
                self.database_path,
            )
        self.assertEqual(error.exception.field, "password_confirmation")

    def test_duplicate_username_is_case_insensitive(self) -> None:
        register_user(
            "Alice_01",
            "password123",
            "password123",
            self.database_path,
        )

        with self.assertRaises(DuplicateUsernameError):
            register_user(
                " alice_01 ",
                "another-password",
                "another-password",
                self.database_path,
            )

    def test_authentication_returns_none_for_unknown_user_or_wrong_password(self) -> None:
        register_user(
            "alice_01",
            "password123",
            "password123",
            self.database_path,
        )

        self.assertIsNone(
            authenticate_user("unknown", "password123", self.database_path)
        )
        self.assertIsNone(
            authenticate_user("alice_01", "wrong-password", self.database_path)
        )
        self.assertIsNone(
            authenticate_user("alice_01", "a" * 17, self.database_path)
        )
        self.assertIsNone(get_user_by_id("1", self.database_path))


if __name__ == "__main__":
    unittest.main()
