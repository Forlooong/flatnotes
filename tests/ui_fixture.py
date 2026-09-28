"""Isolated local browser fixture; never used in production or Docker build."""
import os
import sys
import time
from pathlib import Path
from hashlib import sha256

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server"))
data = Path(os.environ.get("FLATNOTES_UI_DATA", "work/tests/ui-data")).resolve()
data.mkdir(parents=True, exist_ok=True)
os.environ.update({"FLATNOTES_AUTH_TYPE": "oidc", "FLATNOTES_PATH_PREFIX": "/apps/notes", "FLATNOTES_PATH": str(data), "FLATNOTES_OIDC_ISSUER": "https://www.040323.xyz/auth", "FLATNOTES_OIDC_CLIENT_ID": "flatnotes", "FLATNOTES_OIDC_REDIRECT_URI": "https://www.040323.xyz/apps/notes/api/oidc/callback"})
import main
from auth.oidc import _Session
from notes.models import NoteCreate
main.auth._site_identity = lambda cookie: "fixture-user"
main.auth.origin = "http://127.0.0.1:18081"
main.auth._sessions["fixture-session"] = _Session("fixture-sub", "fixture-user", sha256(b"fixture-site").hexdigest(), time.time() + 3600)
if not (data / "欢迎使用.md").exists():
    main.note_storage.create(NoteCreate(title="欢迎使用", content="共享笔记测试 #shared"))
import uvicorn
uvicorn.run(main.app, host="127.0.0.1", port=18081, access_log=False)
