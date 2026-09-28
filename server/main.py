from typing import List, Literal
import secrets
from urllib.parse import quote
from starlette.concurrency import run_in_threadpool

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, UploadFile, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

import api_messages
from attachments.base import BaseAttachments
from attachments.lifecycle import AttachmentLifecycle
from attachments.models import DraftAttachments
from attachments.models import AttachmentCreateResponse
from auth.base import BaseAuth
from auth.models import Login, Token
from global_config import AuthType, GlobalConfig, GlobalConfigResponseModel
from helpers import replace_base_href
from notes.base import BaseNotes
from notes.models import Note, NoteCreate, NoteUpdate, SearchResult

global_config = GlobalConfig()
auth: BaseAuth = global_config.load_auth()
note_storage: BaseNotes = global_config.load_note_storage()
attachment_storage: BaseAttachments = global_config.load_attachment_storage()
attachment_lifecycle = AttachmentLifecycle(attachment_storage)
auth_deps = [Depends(auth.authenticate)] if auth else []
router = APIRouter()
app = FastAPI(
    docs_url=global_config.path_prefix + "/docs",
    openapi_url=global_config.path_prefix + "/openapi.json",
)
replace_base_href("client/dist/index.html", global_config.path_prefix)


if global_config.auth_type == AuthType.OIDC:
    # Protect UI, static assets and APIs. Authentication runs once per request;
    # the router dependency reuses the established request identity.
    auth_deps = []

    @app.middleware("http")
    async def oidc_boundary(request: Request, call_next):
        public = {
            global_config.path_prefix + "/health",
            global_config.path_prefix + "/api/oidc/login",
            global_config.path_prefix + "/api/oidc/callback",
        }
        try:
            auth.check_origin(request)
            if request.url.path not in public:
                request.state.username = await run_in_threadpool(auth.authenticate, request)
        except HTTPException as error:
            if error.status_code == 401 and request.method == "GET" and "text/html" in request.headers.get("accept", ""):
                destination = request.url.path + (("?" + request.url.query) if request.url.query else "")
                response = RedirectResponse(global_config.path_prefix + "/api/oidc/login?redirect=" + quote(destination, safe=""), status_code=302)
            else:
                response = JSONResponse({"detail": error.detail}, status_code=error.status_code)
            response.headers["Cache-Control"] = "no-store"
            return response
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response


# region UI
@router.get("/", include_in_schema=False)
@router.get("/login", include_in_schema=False)
@router.get("/search", include_in_schema=False)
@router.get("/new", include_in_schema=False)
@router.get("/note/{title}", include_in_schema=False)
def root(title: str = ""):
    with open("client/dist/index.html", "r", encoding="utf-8") as f:
        html = f.read()
    return HTMLResponse(content=html)


# endregion


# region Auth
if global_config.auth_type not in [AuthType.NONE, AuthType.READ_ONLY]:

    if global_config.auth_type in [AuthType.PASSWORD, AuthType.TOTP]:

        @router.post("/api/token", response_model=Token)
        def token(data: Login):
            try:
                return auth.login(data)
            except ValueError:
                raise HTTPException(
                    status_code=401, detail=api_messages.login_failed
                )

    if global_config.auth_type == AuthType.OIDC:

        @router.get("/api/oidc/login", include_in_schema=False)
        def oidc_login(redirect: str | None = None):
            location, state = auth.begin_login(redirect)
            response = RedirectResponse(url=location, status_code=302)
            response.set_cookie(
                auth.STATE_COOKIE,
                state,
                max_age=auth.STATE_TTL_SECONDS,
                secure=True,
                httponly=True,
                samesite="lax",
                path=global_config.path_prefix + "/",
            )
            response.headers["Cache-Control"] = "no-store"
            return response

        @router.get("/api/oidc/callback", include_in_schema=False)
        def oidc_callback(
            request: Request, code: str | None = None, state: str | None = None
        ):
            request_state = request.cookies.get(auth.STATE_COOKIE)
            if not code or not state or not request_state or not secrets.compare_digest(request_state, state):
                raise HTTPException(status_code=400, detail="Invalid OIDC callback")
            session_id, redirect = auth.complete_login(state, code, request.cookies.get("site_session", ""))
            response = RedirectResponse(url=redirect, status_code=302)
            response.set_cookie(
                auth.SESSION_COOKIE,
                session_id,
                max_age=auth.session_expiry_seconds,
                secure=True,
                httponly=True,
                samesite="lax",
                path=global_config.path_prefix + "/",
            )
            response.delete_cookie(
                auth.STATE_COOKIE, path=global_config.path_prefix + "/"
            )
            response.headers["Cache-Control"] = "no-store"
            return response

        @router.post("/api/oidc/logout", include_in_schema=False)
        def oidc_logout(request: Request):
            auth.logout(request.cookies.get(auth.SESSION_COOKIE))
            response = JSONResponse({"redirect": auth.provider_logout_url()})
            response.delete_cookie(
                auth.SESSION_COOKIE, path=global_config.path_prefix + "/"
            )
            response.headers["Cache-Control"] = "no-store"
            return response


@router.get("/api/auth-check", dependencies=auth_deps)
def auth_check() -> str:
    """A lightweight endpoint that simply returns 'OK' if the user is
    authenticated."""
    return "OK"


# endregion


# region Notes
# Get Note
@router.get(
    "/api/notes/{title}",
    dependencies=auth_deps,
    response_model=Note,
)
def get_note(title: str):
    """Get a specific note."""
    try:
        return note_storage.get(title)
    except ValueError:
        raise HTTPException(
            status_code=400, detail=api_messages.invalid_note_title
        )
    except FileNotFoundError:
        raise HTTPException(404, api_messages.note_not_found)


if global_config.auth_type != AuthType.READ_ONLY:

    # Create Note
    @router.post(
        "/api/notes",
        dependencies=auth_deps,
        response_model=Note,
    )
    def post_note(note: NoteCreate):
        """Create a new note."""
        try:
            with attachment_lifecycle.lock:
                result = note_storage.create(note)
                attachment_lifecycle.release(note.draft_id)
                return result
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=api_messages.invalid_note_title,
            )
        except FileExistsError:
            raise HTTPException(
                status_code=409, detail=api_messages.note_exists
            )

    # Update Note
    @router.patch(
        "/api/notes/{title}",
        dependencies=auth_deps,
        response_model=Note,
    )
    def patch_note(title: str, data: NoteUpdate):
        try:
            with attachment_lifecycle.lock:
                result = note_storage.update(title, data)
                attachment_lifecycle.release(data.draft_id)
                return result
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=api_messages.invalid_note_title,
            )
        except FileExistsError:
            raise HTTPException(
                status_code=409, detail=api_messages.note_exists
            )
        except FileNotFoundError:
            raise HTTPException(404, api_messages.note_not_found)

    # Delete Note
    @router.delete(
        "/api/notes/{title}",
        dependencies=auth_deps,
        response_model=None,
    )
    def delete_note(title: str):
        try:
            with attachment_lifecycle.lock:
                note_storage.delete(title)
                attachment_lifecycle.collect()
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=api_messages.invalid_note_title,
            )
        except FileNotFoundError:
            raise HTTPException(404, api_messages.note_not_found)


# endregion


# region Search
@router.get(
    "/api/search",
    dependencies=auth_deps,
    response_model=List[SearchResult],
)
def search(
    term: str,
    sort: Literal["score", "title", "lastModified"] = "score",
    order: Literal["asc", "desc"] = "desc",
    limit: int = None,
):
    """Perform a full text search on all notes."""
    if sort == "lastModified":
        sort = "last_modified"
    return note_storage.search(term, sort=sort, order=order, limit=limit)


@router.get(
    "/api/tags",
    dependencies=auth_deps,
    response_model=List[str],
)
def get_tags():
    """Get a list of all indexed tags."""
    return note_storage.get_tags()


# endregion


# region Config
@router.get("/api/config", response_model=GlobalConfigResponseModel)
def get_config():
    """Retrieve server-side config required for the UI."""
    return GlobalConfigResponseModel(
        auth_type=global_config.auth_type,
        quick_access_hide=global_config.quick_access_hide,
        quick_access_title=global_config.quick_access_title,
        quick_access_term=global_config.quick_access_term,
        quick_access_sort=global_config.quick_access_sort,
        quick_access_limit=global_config.quick_access_limit,
    )


# endregion


# region Attachments
# Get Attachment
@router.get(
    "/api/attachments/{filename}",
    dependencies=auth_deps,
)
# Include a secondary route used to create relative URLs that can be used
# outside the context of flatnotes (e.g. "/attachments/image.jpg").
@router.get(
    "/attachments/{filename}",
    dependencies=auth_deps,
    include_in_schema=False,
)
def get_attachment(filename: str):
    """Download an attachment."""
    try:
        return attachment_storage.get(filename)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=api_messages.invalid_attachment_filename,
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=404, detail=api_messages.attachment_not_found
        )


if global_config.auth_type != AuthType.READ_ONLY:

    @router.post("/api/attachment-drafts/{draft_id}", dependencies=auth_deps)
    def sync_attachment_draft(draft_id: str, data: DraftAttachments):
        try:
            return attachment_lifecycle.sync(draft_id, data.content, data.settled, data.discard)
        except ValueError:
            raise HTTPException(400, "无效的草稿标识")

    # Create Attachment
    @router.post(
        "/api/attachments",
        dependencies=auth_deps,
        response_model=AttachmentCreateResponse,
    )
    def post_attachment(file: UploadFile, draft_id: str | None = Form(None, alias="draftId")):
        """Upload an attachment."""
        try:
            return attachment_lifecycle.upload(file, draft_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=api_messages.invalid_attachment_filename,
            )
        except FileExistsError:
            raise HTTPException(409, api_messages.attachment_exists)


# endregion


# region Healthcheck
@router.get("/health")
def healthcheck() -> str:
    """A lightweight endpoint that simply returns 'OK' to indicate the server
    is running."""
    return "OK"


# endregion

app.include_router(router, prefix=global_config.path_prefix)
app.mount(
    global_config.path_prefix,
    StaticFiles(directory="client/dist"),
    name="dist",
)
