import unittest
import requests
import time
import subprocess
import os
import signal
import sys

# Ensure server is running before tests (managed by the test runner or manually)
# For this script, we will assume the server is running on localhost:8000
# However, to be robust, we can start it in setUpClass.

class TestGateway(unittest.TestCase):
    SERVER_PROCESS = None
    BASE_URL = "http://localhost:8000"

    @classmethod
    def setUpClass(cls):
        # Start the server
        print("Starting server...")
        cls.SERVER_PROCESS = subprocess.Popen(
            [sys.executable, "main.py"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        time.sleep(3) # Wait for startup

    @classmethod
    def tearDownClass(cls):
        if cls.SERVER_PROCESS:
            print("Stopping server...")
            cls.SERVER_PROCESS.terminate()
            cls.SERVER_PROCESS.wait()

    def test_missing_api_key(self):
        response = requests.get(f"{self.BASE_URL}/posts/1")
        self.assertEqual(response.status_code, 403)
        self.assertIn("Missing API Key", response.text)

    def test_invalid_api_key(self):
        headers = {"X-API-Key": "invalid_key_123"}
        response = requests.get(f"{self.BASE_URL}/posts/1", headers=headers)
        self.assertEqual(response.status_code, 403)
        self.assertIn("Invalid API Key", response.text)

    def test_valid_proxy_request(self):
        # Partner A has plenty of limit
        headers = {"X-API-Key": "key_a"}
        response = requests.get(f"{self.BASE_URL}/posts/1", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], 1)

    def test_rate_limit_exceeded(self):
        # Partner B has limit 5
        # Note: Depending on previous tests or persistent process, state might be retained.
        # Since we restart server per class, state is fresh.
        # But wait, request_counts is in-memory global.
        # We need to be careful.

        headers = {"X-API-Key": "key_b"}

        # Consume the 5 allowed requests
        for _ in range(5):
            # Partner B has access to /users, not /posts
            response = requests.get(f"{self.BASE_URL}/users/1", headers=headers)
            if response.status_code == 429:
                self.fail("Rate limit triggered too early")
            self.assertEqual(response.status_code, 200)

        # The 6th should fail
        response = requests.get(f"{self.BASE_URL}/users/1", headers=headers)
        self.assertEqual(response.status_code, 429)
        self.assertIn("Rate limit exceeded", response.text)

    def test_post_request(self):
        # Test a POST request forwarding
        headers = {"X-API-Key": "key_a"}
        payload = {"title": "foo", "body": "bar", "userId": 1}
        response = requests.post(f"{self.BASE_URL}/posts", headers=headers, json=payload)
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["title"], "foo")

    def test_permission_allowed(self):
        # Partner A has access to /posts
        headers = {"X-API-Key": "key_a"}
        response = requests.get(f"{self.BASE_URL}/posts/1", headers=headers)
        self.assertEqual(response.status_code, 200)

    def test_permission_denied(self):
        # Partner A does NOT have access to /users
        headers = {"X-API-Key": "key_a"}
        response = requests.get(f"{self.BASE_URL}/users/1", headers=headers)
        self.assertEqual(response.status_code, 403)
        self.assertIn("Access denied", response.text)

    def test_usage_tracking(self):
        # Make a request and verify it appears in the DB
        import sqlite3
        conn = sqlite3.connect("gateway.db")
        cursor = conn.execute("SELECT COUNT(*) FROM api_usage")
        initial_count = cursor.fetchone()[0]

        headers = {"X-API-Key": "god_mode"}
        requests.get(f"{self.BASE_URL}/todos/1", headers=headers)

        cursor = conn.execute("SELECT COUNT(*) FROM api_usage")
        final_count = cursor.fetchone()[0]
        conn.close()

        self.assertEqual(final_count, initial_count + 1)

if __name__ == "__main__":
    unittest.main()
