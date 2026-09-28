import os
import sys
import time
import unittest
from jose import jwt, jwk
from unittest.mock import patch
from fastapi import HTTPException
from starlette.requests import Request
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))

from auth.oidc import OIDCAuth  # noqa: E402


class OIDCAuthTest(unittest.TestCase):
    def setUp(self):
        self.previous = os.environ.copy()
        os.environ.update(
            {
                "FLATNOTES_OIDC_ISSUER": "https://identity.example.test/auth",
                "FLATNOTES_OIDC_CLIENT_ID": "flatnotes",
                "FLATNOTES_OIDC_REDIRECT_URI": "https://www.040323.xyz/apps/notes/api/oidc/callback",
            }
        )
        self.auth = OIDCAuth("/apps/notes")
        self.auth._get_discovery = lambda: {
            "authorization_endpoint": self.auth.issuer + "/api/oidc/authorization",
            "token_endpoint": self.auth.issuer + "/api/oidc/token",
            "userinfo_endpoint": self.auth.issuer + "/api/oidc/userinfo",
            "jwks_uri": self.auth.issuer + "/jwks.json",
        }
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.private = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
        public = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        self.auth._get_jwks = lambda: {"keys": [dict(jwk.construct(public, algorithm="RS256").to_dict(), kid="test")]}
        self.auth._get_json = lambda *a, **k: {"sub": "subject-1", "preferred_username": "zhuqing"}
        self.auth._site_identity = lambda cookie: "zhuqing" if cookie == "site-test" else self.reject(401)

    @staticmethod
    def reject(status):
        raise HTTPException(status_code=status)

    def issue(self, state, changes=None):
        claims = {"iss": self.auth.issuer, "aud": "flatnotes", "sub": "subject-1", "nonce": self.auth._states[state].nonce, "iat": int(time.time()), "exp": int(time.time()) + 300}
        claims.update(changes or {})
        return jwt.encode(claims, self.private, algorithm="RS256", headers={"kid": "test"})

    def complete(self, redirect="/apps/notes/note/demo?x=1", changes=None):
        location, state = self.auth.begin_login(redirect)
        signed = self.issue(state, changes)
        self.auth._request_token = lambda code, verifier: {"id_token": signed, "access_token": "test-access", "token_type": "Bearer"}
        return self.auth.complete_login(state, "code", "site-test"), state, location

    def test_pkce_deep_return_and_state_replay(self):
        (session, redirect), state, location = self.complete()
        query = parse_qs(urlsplit(location).query)
        self.assertEqual(query["code_challenge_method"], ["S256"])
        self.assertEqual(redirect, "/apps/notes/note/demo?x=1")
        self.assertEqual(self.auth._sessions[session].subject, "subject-1")
        with self.assertRaises(HTTPException):
            self.auth.complete_login(state, "code", "site-test")

    def test_invalid_claims_are_rejected(self):
        for changes in ({"nonce": "wrong"}, {"iss": "https://evil.test"}, {"aud": "other"}, {"iat": int(time.time()) + 100}, {"exp": 1}, {"sub": ""}, {"aud": ["flatnotes", "other"]}, {"azp": "other"}, {"at_hash": "invalid"}):
            with self.subTest(changes=changes), self.assertRaises(HTTPException):
                self.complete(changes=changes)

    def test_subject_and_membership_required(self):
        self.auth._get_json = lambda *a, **k: {"sub": "different", "preferred_username": "zhuqing"}
        with self.assertRaises(HTTPException):
            self.complete()
        self.auth._get_json = lambda *a, **k: {"sub": "subject-1", "preferred_username": "zhuqing"}
        self.auth._site_identity = lambda c: self.reject(403)
        with self.assertRaises(HTTPException):
            self.complete()

    def test_logout_expiry_and_changed_website_session(self):
        for mode in ("logout", "expired", "changed"):
            self.auth._site_identity = lambda c: "zhuqing"
            (session, _), _, _ = self.complete()
            cookie = "site-test"
            if mode == "logout":
                self.auth._site_identity = lambda c: self.reject(401)
            elif mode == "expired":
                self.auth._sessions[session].expires_at = 0
            else:
                cookie = "new-site-session"
            request = Request({"type": "http", "method": "GET", "headers": [(b"cookie", f"flatnotes_session={session}; site_session={cookie}".encode())]})
            with self.assertRaises(HTTPException):
                self.auth.authenticate(request)
            self.assertNotIn(session, self.auth._sessions)

    def test_origin_and_redirect_boundaries(self):
        for origin in ("", "https://evil.test", self.auth.origin + "/"):
            request = Request({"type": "http", "method": "POST", "headers": [(b"origin", origin.encode())]})
            with self.assertRaises(HTTPException):
                self.auth.check_origin(request)
        for value in ("https://evil.test", "//evil.test", "/apps/notes-evil/", "/apps/notes/\\evil", "/member/", "/apps/notes/%2e%2e/%2e%2e/member/"):
            self.assertEqual(self.auth._safe_redirect(value), "/apps/notes/")

    def test_discovery_issuer_is_checked(self):
        auth = OIDCAuth("/apps/notes")
        auth._get_json = lambda *a, **k: {"issuer": "https://wrong.test"}
        with self.assertRaises(HTTPException):
            auth._get_discovery()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.previous)


if __name__ == "__main__":
    unittest.main()
