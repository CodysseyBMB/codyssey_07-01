import os
import re
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault(
    "SESSION_SECRET",
    "test-session-secret-that-is-at-least-32-characters",
)

from fastapi.testclient import TestClient

from app.main import create_app
from app.services.auth import register_user


class AuthRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "test.db"
        self.app = create_app(
            database_path=self.database_path,
            session_secret="test-session-secret-that-is-at-least-32-characters",
            session_https_only=False,
        )
        self.client = TestClient(self.app)
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        self.temp_dir.cleanup()

    def _csrf_token(self, path: str) -> str:
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        match = re.search(
            r'name="csrf_token" value="([^"]+)"',
            response.text,
        )
        self.assertIsNotNone(match)
        return match.group(1)

    def _signup(self, username: str = "alice_01") -> None:
        csrf_token = self._csrf_token("/signup")
        response = self.client.post(
            "/signup",
            data={
                "username": username,
                "password": "password123",
                "password_confirmation": "password123",
                "csrf_token": csrf_token,
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/login?registered=1")

    def _login(self, username: str = "alice_01"):
        csrf_token = self._csrf_token("/login")
        response = self.client.post(
            "/login",
            data={
                "username": username,
                "password": "password123",
                "csrf_token": csrf_token,
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/")
        return response

    def test_signup_login_and_logout_flow(self) -> None:
        self._signup()

        login_page = self.client.get("/login?registered=1")
        self.assertEqual(login_page.status_code, 200)
        self.assertIn("회원가입이 완료되었습니다", login_page.text)

        login_response = self._login()
        self.assertIn("codyssey_session", self.client.cookies)
        session_cookie = login_response.headers["set-cookie"].lower()
        self.assertIn("httponly", session_cookie)
        self.assertIn("samesite=lax", session_cookie)
        self.assertIn("max-age=28800", session_cookie)

        home_page = self.client.get("/")
        self.assertEqual(home_page.status_code, 200)
        self.assertIn("alice_01님, 반갑습니다", home_page.text)
        csrf_token = re.search(
            r'name="csrf_token" value="([^"]+)"',
            home_page.text,
        ).group(1)

        logout_response = self.client.post(
            "/logout",
            data={"csrf_token": csrf_token},
            follow_redirects=False,
        )
        self.assertEqual(logout_response.status_code, 303)
        self.assertEqual(logout_response.headers["location"], "/")

        logged_out_home = self.client.get("/")
        self.assertNotIn("alice_01님, 반갑습니다", logged_out_home.text)
        self.assertIn('href="/login"', logged_out_home.text)

    def test_signup_validation_and_duplicate_responses_do_not_echo_password(self) -> None:
        csrf_token = self._csrf_token("/signup")
        invalid_response = self.client.post(
            "/signup",
            data={
                "username": "invalid.name",
                "password": "password123",
                "password_confirmation": "password123",
                "csrf_token": csrf_token,
            },
        )
        self.assertEqual(invalid_response.status_code, 400)
        self.assertIn("아이디는 영문 소문자", invalid_response.text)
        self.assertNotIn('value="password123"', invalid_response.text)

        self._signup("Alice_01")
        duplicate_response = self.client.post(
            "/signup",
            data={
                "username": "alice_01",
                "password": "another-password",
                "password_confirmation": "another-password",
                "csrf_token": csrf_token,
            },
        )
        self.assertEqual(duplicate_response.status_code, 409)
        self.assertIn("이미 사용 중인 아이디입니다", duplicate_response.text)

    def test_invalid_login_uses_same_error_message(self) -> None:
        csrf_token = self._csrf_token("/login")
        unknown_response = self.client.post(
            "/login",
            data={
                "username": "unknown",
                "password": "password123",
                "csrf_token": csrf_token,
            },
        )

        register_user(
            "alice_01",
            "password123",
            "password123",
            self.database_path,
        )
        wrong_password_response = self.client.post(
            "/login",
            data={
                "username": "alice_01",
                "password": "wrong-password",
                "csrf_token": csrf_token,
            },
        )

        expected_message = "아이디 또는 비밀번호가 올바르지 않습니다."
        self.assertEqual(unknown_response.status_code, 401)
        self.assertEqual(wrong_password_response.status_code, 401)
        self.assertIn(expected_message, unknown_response.text)
        self.assertIn(expected_message, wrong_password_response.text)

    def test_post_routes_reject_missing_or_invalid_csrf_token(self) -> None:
        missing_token_response = self.client.post(
            "/signup",
            data={
                "username": "alice_01",
                "password": "password123",
                "password_confirmation": "password123",
            },
        )
        self.assertEqual(missing_token_response.status_code, 403)

        self._signup()
        login_response = self.client.post(
            "/login",
            data={
                "username": "alice_01",
                "password": "password123",
                "csrf_token": "invalid-token",
            },
        )
        logout_response = self.client.post(
            "/logout",
            data={"csrf_token": "invalid-token"},
        )
        self.assertEqual(login_response.status_code, 403)
        self.assertEqual(logout_response.status_code, 403)

    def test_authenticated_user_is_redirected_from_auth_pages(self) -> None:
        self._signup()
        self._login()

        for path in ("/signup", "/login"):
            with self.subTest(path=path):
                response = self.client.get(path, follow_redirects=False)
                self.assertEqual(response.status_code, 303)
                self.assertEqual(response.headers["location"], "/")

    def test_create_app_rejects_short_session_secret(self) -> None:
        with self.assertRaises(RuntimeError):
            create_app(
                database_path=self.database_path,
                session_secret="too-short",
            )


if __name__ == "__main__":
    unittest.main()
