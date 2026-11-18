import asyncio
import copy
import json
import os
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import urlencode

from src.app import activities, app


STUDENT_TOKEN = "student-" + "a" * 40
ADMIN_TOKEN = "admin-" + "b" * 40
ACCOUNTS = [
    {"email": "michael@mergington.edu", "role": "student", "token": STUDENT_TOKEN},
    {"email": "admin@mergington.edu", "role": "admin", "token": ADMIN_TOKEN},
]


class AuthenticationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.original_activities = copy.deepcopy(activities)
        self.accounts_file = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8")
        json.dump(ACCOUNTS, self.accounts_file)
        self.accounts_file.flush()
        self.environment = patch.dict(os.environ, {"AUTH_ACCOUNTS_FILE": self.accounts_file.name})
        self.environment.start()

    def tearDown(self):
        self.environment.stop()
        self.accounts_file.close()
        activities.clear()
        activities.update(self.original_activities)

    async def request(self, method, path, email=None, token=None):
        query = urlencode({"email": email}) if email is not None else ""
        headers = [(b"authorization", f"Bearer {token}".encode())] if token else []
        scope = {
            "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
            "method": method, "scheme": "http", "path": path,
            "raw_path": path.encode(), "query_string": query.encode(),
            "headers": headers, "server": ("test", 80), "client": ("test", 1234),
            "root_path": "",
        }
        messages = []
        received = False

        async def receive():
            nonlocal received
            if not received:
                received = True
                return {"type": "http.request", "body": b"", "more_body": False}
            await asyncio.Event().wait()

        async def send(message):
            messages.append(message)

        await app(scope, receive, send)
        status = next(message["status"] for message in messages
                      if message["type"] == "http.response.start")
        body = b"".join(message.get("body", b"") for message in messages
                        if message["type"] == "http.response.body")
        return status, json.loads(body)

    async def test_writes_require_valid_credentials(self):
        for method, action in [("POST", "signup"), ("DELETE", "unregister")]:
            path = f"/activities/Chess Club/{action}"
            for token in (None, "invalid"):
                status, _ = await self.request(method, path, "michael@mergington.edu", token)
                self.assertEqual(status, 401)
        self.assertEqual((await self.request("GET", "/activities"))[0], 200)

    async def test_student_cannot_manage_another_student(self):
        before = copy.deepcopy(activities)
        for method, action in [("POST", "signup"), ("DELETE", "unregister")]:
            status, _ = await self.request(
                method, f"/activities/Chess Club/{action}", "daniel@mergington.edu", STUDENT_TOKEN
            )
            self.assertEqual(status, 403)
        self.assertEqual(activities, before)

    async def test_student_can_manage_own_registration_case_insensitively(self):
        email = "MICHAEL@mergington.edu"
        self.assertEqual((await self.request(
            "DELETE", "/activities/Chess Club/unregister", email, STUDENT_TOKEN
        ))[0], 200)
        self.assertNotIn("michael@mergington.edu", activities["Chess Club"]["participants"])
        self.assertEqual((await self.request(
            "POST", "/activities/Chess Club/signup", email, STUDENT_TOKEN
        ))[0], 200)
        self.assertIn("michael@mergington.edu", activities["Chess Club"]["participants"])

    async def test_admin_can_manage_another_student(self):
        email = "new@mergington.edu"
        for method, action in [("POST", "signup"), ("DELETE", "unregister")]:
            status, _ = await self.request(method, f"/activities/Chess Club/{action}", email, ADMIN_TOKEN)
            self.assertEqual(status, 200)
        self.assertNotIn(email, activities["Chess Club"]["participants"])

    async def test_account_endpoint_does_not_expose_token(self):
        status, body = await self.request("GET", "/auth/me", token=STUDENT_TOKEN)
        self.assertEqual(status, 200)
        self.assertEqual(body, {"email": "michael@mergington.edu", "role": "student"})

    async def test_misconfigured_accounts_fail_closed(self):
        for contents in ("not json", "[]", json.dumps([*ACCOUNTS, ACCOUNTS[0]])):
            self.accounts_file.seek(0)
            self.accounts_file.truncate()
            self.accounts_file.write(contents)
            self.accounts_file.flush()
            status, _ = await self.request(
                "DELETE", "/activities/Chess Club/unregister", "michael@mergington.edu", STUDENT_TOKEN
            )
            self.assertEqual(status, 503)
        self.assertIn("michael@mergington.edu", activities["Chess Club"]["participants"])
        with patch.dict(os.environ, {}, clear=True):
            status, _ = await self.request("GET", "/auth/me", token=STUDENT_TOKEN)
            self.assertEqual(status, 503)


if __name__ == "__main__":
    unittest.main()
