"""HTTP boundary and shared storage; provider cryptography tested in test_oidc."""
import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from hashlib import sha256
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server"))
from auth.oidc import _Session


class BoundaryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Path("work/tests").mkdir(parents=True, exist_ok=True)
        cls.data = tempfile.TemporaryDirectory(dir="work/tests")
        os.environ.update({"FLATNOTES_AUTH_TYPE": "oidc", "FLATNOTES_PATH_PREFIX": "/apps/notes", "FLATNOTES_PATH": str(Path(cls.data.name).resolve()), "FLATNOTES_OIDC_ISSUER": "https://www.040323.xyz/auth", "FLATNOTES_OIDC_CLIENT_ID": "flatnotes", "FLATNOTES_OIDC_REDIRECT_URI": "https://www.040323.xyz/apps/notes/api/oidc/callback"})
        cls.main = importlib.import_module("main")
        cls.auth = cls.main.auth
        cls.auth._site_identity = lambda cookie: {"site-a": "zhuqing", "site-b": "yaojia"}[cookie]
        import time
        for sid, site, user in (("a", "site-a", "zhuqing"), ("b", "site-b", "yaojia")):
            cls.auth._sessions[sid] = _Session(user, user, sha256(site.encode()).hexdigest(), time.time() + 60)
        cls.client = TestClient(cls.main.app, base_url="https://www.040323.xyz")

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        cls.data.cleanup()

    def headers(self, sid="a", origin=True):
        result = {"Cookie": f"flatnotes_session={sid}; site_session=site-{sid}"}
        if origin:
            result["Origin"] = "https://www.040323.xyz"
        return result

    def test_cookie_write_csrf_and_shared_notes_attachments(self):
        endpoint = "/apps/notes/api/notes"
        note = {"title": "shared-check", "content": "First #shared"}
        self.assertEqual(self.client.post(endpoint, headers=self.headers(origin=False), json=note).status_code, 403)
        self.assertEqual(self.client.post(endpoint, headers={**self.headers(), "Origin": "https://evil.test"}, json=note).status_code, 403)
        self.assertEqual(self.client.post(endpoint, headers=self.headers(), json=note).status_code, 200)
        self.assertEqual(self.client.get(endpoint + "/shared-check", headers=self.headers("b")).json()["content"], note["content"])
        self.assertEqual(self.client.patch(endpoint + "/shared-check", headers=self.headers("b"), json={"newContent": "Second #shared"}).status_code, 200)
        self.assertEqual(self.client.get(endpoint + "/shared-check", headers=self.headers()).json()["content"], "Second #shared")
        upload = self.client.post("/apps/notes/api/attachments", headers=self.headers(), files={"file": ("shared.txt", b"attachment evidence", "text/plain")})
        self.assertEqual(upload.status_code, 200)
        self.assertEqual(self.client.get("/apps/notes/" + upload.json()["url"], headers=self.headers("b")).content, b"attachment evidence")
        self.assertEqual(self.client.get("/apps/notes/attachments/shared.txt").status_code, 401)
        self.assertEqual(self.client.delete(endpoint + "/shared-check", headers=self.headers("b")).status_code, 200)

    def test_anonymous_ui_deep_link_and_api_header_forgery(self):
        response = self.client.get("/apps/notes/note/demo?edit=1", headers={"Accept": "text/html"}, follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn("redirect=%2Fapps%2Fnotes%2Fnote%2Fdemo%3Fedit%3D1", response.headers["location"])
        self.assertEqual(self.client.get("/apps/notes/api/search?term=*", headers={"Remote-User": "zhuqing", "Remote-Groups": "site-users"}).status_code, 401)
        self.assertEqual(self.client.get("/apps/notes/health").json(), "OK")
        self.assertEqual(self.client.post("/apps/notes/api/token", headers=self.headers(), json={"username": "x", "password": "x"}).status_code, 405)

    def test_callback_cookie_state_binding(self):
        self.assertEqual(self.client.get("/apps/notes/api/oidc/callback?code=x&state=bad").status_code, 400)


if __name__ == "__main__":
    unittest.main()
