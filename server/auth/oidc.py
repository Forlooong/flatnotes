import json
import secrets
import threading
import time
from dataclasses import dataclass
from hashlib import sha256
from http.client import HTTPException as HttpClientException
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from fastapi import HTTPException, Request as FastAPIRequest
from jose import JWTError, jwt

from helpers import get_env

from .base import BaseAuth
from .models import Login, Token


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_opener = build_opener(_NoRedirect)


@dataclass
class _LoginState:
    nonce: str
    code_verifier: str
    redirect: str
    expires_at: float


@dataclass
class _Session:
    subject: str
    username: str
    site_cookie_hash: str
    expires_at: float


class OIDCAuth(BaseAuth):
    """Small OIDC relying party for the single Flatnotes application.

    The app deliberately keeps only opaque, in-memory sessions. OIDC is the
    source of identity; the shared Flatnotes directory remains one common
    workspace for every authorized website account.
    """

    SESSION_COOKIE = "flatnotes_session"
    STATE_COOKIE = "flatnotes_oidc_state"
    STATE_TTL_SECONDS = 300

    def __init__(self, path_prefix: str) -> None:
        self.issuer = get_env("FLATNOTES_OIDC_ISSUER", mandatory=True).rstrip("/")
        self.client_id = get_env("FLATNOTES_OIDC_CLIENT_ID", mandatory=True)
        self.redirect_uri = get_env(
            "FLATNOTES_OIDC_REDIRECT_URI", mandatory=True
        )
        self.path_prefix = path_prefix or ""
        self.session_expiry_seconds = get_env(
            "FLATNOTES_SESSION_EXPIRY_SECONDS", default=28800, cast_int=True
        )
        self._validate_url(self.issuer, "FLATNOTES_OIDC_ISSUER")
        self._validate_url(self.redirect_uri, "FLATNOTES_OIDC_REDIRECT_URI")
        redirect = urlsplit(self.redirect_uri)
        self.origin = f"{redirect.scheme}://{redirect.netloc}"
        if self.redirect_uri != self.origin + self.path_prefix + "/api/oidc/callback":
            raise RuntimeError("OIDC redirect URI must target the callback route")
        self._states: dict[str, _LoginState] = {}
        self._sessions: dict[str, _Session] = {}
        self._lock = threading.Lock()
        self._discovery: dict[str, Any] | None = None
        self._jwks: dict[str, Any] | None = None

    @staticmethod
    def _validate_url(value: str, key: str) -> None:
        parsed = urlsplit(value)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password or parsed.fragment:
            raise RuntimeError(f"{key} must be an absolute HTTPS URL")

    def login(self, data: Login) -> Token:
        raise ValueError("Flatnotes OIDC login does not accept local credentials")

    def authenticate(self, request: FastAPIRequest):
        if request is None:
            raise HTTPException(status_code=401, detail="Authentication required")
        token = request.cookies.get(self.SESSION_COOKIE)
        if not token:
            raise HTTPException(status_code=401, detail="Authentication required")
        with self._lock:
            session = self._sessions.get(token)
            if session is None or session.expires_at <= time.time():
                self._sessions.pop(token, None)
                raise HTTPException(status_code=401, detail="Authentication required")
        site_cookie = request.cookies.get("site_session", "")
        if not secrets.compare_digest(session.site_cookie_hash, sha256(site_cookie.encode()).hexdigest()):
            self.logout(token)
            raise HTTPException(status_code=401, detail="Website session changed")
        try:
            username = self._site_identity(site_cookie)
        except HTTPException as error:
            if error.status_code in (401, 403):
                self.logout(token)
            raise
        if username != session.username:
            self.logout(token)
            raise HTTPException(status_code=401, detail="Website identity changed")
        return session.username

    def check_origin(self, request: FastAPIRequest) -> None:
        if request.method not in ("GET", "HEAD", "OPTIONS") and request.headers.get("origin") != self.origin:
            raise HTTPException(status_code=403, detail="Invalid request Origin")

    def _site_identity(self, site_cookie: str) -> str:
        if not site_cookie:
            raise HTTPException(status_code=401, detail="Website authentication required")
        request = Request(
            "http://127.0.0.1:19091/auth/api/authz/auth-request",
            headers={
                "Cookie": "site_session=" + site_cookie,
                "X-Original-Method": "GET",
                "X-Original-URL": self.origin + self.path_prefix + "/",
                "X-Forwarded-Proto": "https",
                "X-Forwarded-Host": urlsplit(self.origin).netloc,
            },
        )
        try:
            with _opener.open(request, timeout=5) as response:
                username = response.headers.get("Remote-User")
                groups = response.headers.get("Remote-Groups", "").split(",")
                if response.status != 200 or not username or "site-users" not in [g.strip() for g in groups]:
                    raise HTTPException(status_code=403, detail="Application membership required")
                return username
        except HTTPError as error:
            status = error.code if error.code in (401, 403) else 502
            raise HTTPException(status_code=status, detail="Website authorization failed") from error
        except (URLError, TimeoutError, HttpClientException) as error:
            raise HTTPException(status_code=502, detail="Website identity unavailable") from error

    def begin_login(self, redirect: str | None) -> tuple[str, str]:
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        code_verifier = secrets.token_urlsafe(48)
        redirect_path = self._safe_redirect(redirect)
        with self._lock:
            self._purge_states()
            self._states[state] = _LoginState(
                nonce=nonce,
                code_verifier=code_verifier,
                redirect=redirect_path,
                expires_at=time.time() + self.STATE_TTL_SECONDS,
            )
        discovery = self._get_discovery()
        challenge = self._code_challenge(code_verifier)
        query = urlencode(
            {
                "client_id": self.client_id,
                "redirect_uri": self.redirect_uri,
                "response_type": "code",
                "scope": "openid profile",
                "state": state,
                "nonce": nonce,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            }
        )
        return f"{discovery['authorization_endpoint']}?{query}", state

    def complete_login(self, state: str, code: str, site_cookie: str) -> tuple[str, str]:
        with self._lock:
            login_state = self._states.pop(state, None)
        if login_state is None or login_state.expires_at <= time.time():
            raise HTTPException(status_code=400, detail="Invalid OIDC state")
        tokens = self._request_token(code, login_state.code_verifier)
        id_token = tokens.get("id_token")
        if not isinstance(id_token, str):
            raise HTTPException(status_code=502, detail="OIDC response missing id_token")
        access_token = tokens.get("access_token")
        if not isinstance(access_token, str) or not access_token or tokens.get("token_type", "").lower() != "bearer":
            raise HTTPException(status_code=502, detail="OIDC response missing bearer token")
        claims = self._validate_id_token(id_token, login_state.nonce, access_token)
        userinfo = self._get_json(self._get_discovery()["userinfo_endpoint"], headers={"Authorization": "Bearer " + access_token})
        if userinfo.get("sub") != claims["sub"]:
            raise HTTPException(status_code=401, detail="OIDC subject mismatch")
        username = userinfo.get("preferred_username")
        if not isinstance(username, str) or not username.strip():
            raise HTTPException(status_code=502, detail="OIDC identity has no username")
        if self._site_identity(site_cookie) != username:
            raise HTTPException(status_code=403, detail="OIDC website identity mismatch")
        session_id = secrets.token_urlsafe(32)
        with self._lock:
            self._sessions = {k: v for k, v in self._sessions.items() if v.expires_at > time.time()}
            self._sessions[session_id] = _Session(
                subject=claims["sub"],
                username=username,
                site_cookie_hash=sha256(site_cookie.encode()).hexdigest(),
                expires_at=time.time() + self.session_expiry_seconds,
            )
        return session_id, login_state.redirect

    def logout(self, session_id: str | None) -> None:
        if session_id:
            with self._lock:
                self._sessions.pop(session_id, None)

    def provider_logout_url(self) -> str:
        return f"{self.issuer}/logout?rd={quote(self.redirect_uri.rsplit('/api/oidc/callback', 1)[0] + '/', safe='')}"

    def _get_discovery(self) -> dict[str, Any]:
        if self._discovery is None:
            discovery = self._get_json(
                f"{self.issuer}/.well-known/openid-configuration"
            )
            if discovery.get("issuer") != self.issuer:
                raise HTTPException(status_code=502, detail="OIDC discovery issuer mismatch")
            for key in ("authorization_endpoint", "token_endpoint", "jwks_uri", "userinfo_endpoint"):
                endpoint = discovery.get(key)
                if not isinstance(endpoint, str):
                    raise RuntimeError(f"OIDC discovery missing {key}")
                self._validate_url(endpoint, f"OIDC discovery {key}")
                if urlsplit(endpoint).netloc != urlsplit(self.issuer).netloc:
                    raise RuntimeError("OIDC endpoints must belong to the configured issuer host")
            self._discovery = discovery
        return self._discovery

    def _get_jwks(self) -> dict[str, Any]:
        if self._jwks is None:
            self._jwks = self._get_json(self._get_discovery()["jwks_uri"])
        return self._jwks

    def _request_token(self, code: str, code_verifier: str) -> dict[str, Any]:
        discovery = self._get_discovery()
        return self._get_json(
            discovery["token_endpoint"],
            method="POST",
            form={
                "grant_type": "authorization_code",
                "client_id": self.client_id,
                "code": code,
                "redirect_uri": self.redirect_uri,
                "code_verifier": code_verifier,
            },
        )

    def _validate_id_token(self, id_token: str, nonce: str, access_token: str | None = None) -> dict[str, Any]:
        try:
            header = jwt.get_unverified_header(id_token)
            if header.get("alg") != "RS256" or not header.get("kid"):
                raise JWTError("Unexpected OIDC signing algorithm")
            keys = self._get_jwks().get("keys", [])
            key = next((item for item in keys if item.get("kid") == header["kid"]), None)
            if key is None:
                self._jwks = None
                keys = self._get_jwks().get("keys", [])
                key = next((item for item in keys if item.get("kid") == header["kid"]), None)
            if key is None:
                raise JWTError("OIDC signing key not found")
            claims = jwt.decode(
                id_token,
                key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=self.issuer,
                access_token=access_token,
                options={"require_sub": True, "require_exp": True, "require_iat": True, "require_iss": True, "require_aud": True},
            )
            now = time.time()
            if not isinstance(claims["sub"], str) or not claims["sub"] or type(claims["iat"]) not in (int, float) or type(claims["exp"]) not in (int, float):
                raise JWTError("Invalid OIDC required claims")
            if claims["iat"] > now + 30 or claims["exp"] <= claims["iat"]:
                raise JWTError("Invalid OIDC token times")
            audiences = claims["aud"]
            if (isinstance(audiences, list) and len(audiences) > 1 and claims.get("azp") != self.client_id) or ("azp" in claims and claims["azp"] != self.client_id):
                raise JWTError("OIDC authorized party mismatch")
            if not secrets.compare_digest(claims.get("nonce", ""), nonce):
                raise JWTError("OIDC nonce mismatch")
            return claims
        except (JWTError, ValueError, TypeError) as error:
            raise HTTPException(status_code=401, detail="Invalid OIDC identity") from error

    @staticmethod
    def _code_challenge(verifier: str) -> str:
        import base64

        digest = sha256(verifier.encode("ascii")).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")

    def _safe_redirect(self, redirect: str | None) -> str:
        default = f"{self.path_prefix}/" if self.path_prefix else "/"
        if not redirect:
            return default
        parsed = urlsplit(redirect)
        if parsed.scheme or parsed.netloc or not parsed.path.startswith("/") or "\\" in redirect or any(ord(c) < 32 for c in redirect):
            return default
        path = parsed.path or "/"
        decoded_path = unquote(path)
        if "\\" in decoded_path or any(part in (".", "..") for part in decoded_path.split("/")):
            return default
        prefix = self.path_prefix or "/"
        if prefix != "/" and not (path == prefix or path.startswith(prefix + "/")):
            return default
        return path + (("?" + parsed.query) if parsed.query else "") + (("#" + parsed.fragment) if parsed.fragment else "")

    def _purge_states(self) -> None:
        now = time.time()
        self._states = {
            key: value
            for key, value in self._states.items()
            if value.expires_at > now
        }

    @staticmethod
    def _get_json(
        url: str, method: str = "GET", form: dict[str, str] | None = None, headers: dict[str, str] | None = None
    ) -> dict[str, Any]:
        data = None
        headers = {"Accept": "application/json", **(headers or {})}
        if form is not None:
            data = urlencode(form).encode("ascii")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        request = Request(url, data=data, headers=headers, method=method)
        try:
            with _opener.open(request, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, ValueError, HttpClientException) as error:
            raise HTTPException(status_code=502, detail="OIDC provider unavailable") from error
        if not isinstance(payload, dict):
            raise HTTPException(status_code=502, detail="Invalid OIDC provider response")
        if "error" in payload:
            raise HTTPException(status_code=401, detail="OIDC authorization failed")
        return payload
