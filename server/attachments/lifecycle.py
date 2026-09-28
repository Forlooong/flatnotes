"""Shared attachment references; draft bodies remain in the browser."""
import hashlib
import html
import json
import os
import threading
import logging
from pathlib import Path
from urllib.parse import unquote
from uuid import UUID


class AttachmentLifecycle:
    def __init__(self, storage):
        self.storage = storage
        self.root = Path(storage.base_path)
        self.directory = Path(storage.storage_path)
        self.path = self.root / ".attachment-drafts.json"
        self.lock = threading.RLock()
        self.state = json.loads(self.path.read_text("utf-8")) if self.path.exists() else {"managed": [], "drafts": {}}

    def persist(self):
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.state, ensure_ascii=False), encoding="utf-8")
        os.replace(temporary, self.path)

    @staticmethod
    def validate_id(draft_id):
        if draft_id:
            UUID(draft_id)

    def references(self, content):
        # Conservative matching also protects Markdown reference links, HTML,
        # encoded Chinese names and URLs with spaces/parentheses.
        text = unquote(html.unescape(content or ""))
        return {p.name for p in self.directory.iterdir()
                if p.is_file() and not p.is_symlink() and "attachments/" + p.name in text}

    def upload(self, file, draft_id=None):
        self.validate_id(draft_id)
        from helpers import is_valid_filename
        is_valid_filename(file.filename)
        with self.lock:
            digest = hashlib.file_digest(file.file, "sha256").digest()
            file.file.seek(0)
            existing = None
            for path in self.directory.iterdir():
                if path.is_file() and not path.is_symlink():
                    with path.open("rb") as source:
                        if hashlib.file_digest(source, "sha256").digest() == digest:
                            existing = path.name
                            break
            if existing:
                from attachments.models import AttachmentCreateResponse
                result = AttachmentCreateResponse(filename=existing, url=self.storage._url_for_filename(existing))
            else:
                result = self.storage.create(file)
                if draft_id:
                    self.state["managed"].append(result.filename)
            if draft_id:
                draft = self.state["drafts"].setdefault(draft_id, {"refs": [], "pending": []})
                draft["pending"] = sorted(set(draft["pending"]) | {result.filename})
            self.persist()
            return result

    def sync(self, draft_id, content, settled, discard=False):
        self.validate_id(draft_id)
        with self.lock:
            if discard:
                self.state["drafts"].pop(draft_id, None)
            else:
                draft = self.state["drafts"].setdefault(draft_id, {"refs": [], "pending": []})
                draft["refs"] = sorted(self.references(content))
                draft["pending"] = sorted(set(draft["pending"]) - set(settled))
                if not draft["refs"] and not draft["pending"]:
                    self.state["drafts"].pop(draft_id, None)
            return self.collect()

    def release(self, draft_id):
        if draft_id:
            self.state["drafts"].pop(draft_id, None)
        return self.collect()

    def collect(self):
        # Caller holds the same lock as note mutations and uploads. Never use
        # the search index: it may lag actual files on disk.
        referenced = set()
        try:
            for note in self.root.glob("*.md"):
                # Match the note store's text encoding on each platform.
                referenced.update(self.references(note.read_text()))
        except (OSError, UnicodeError):
            # A failed scan cannot prove an attachment is unreferenced. Keep
            # the completed note save valid and defer all deletion.
            logging.getLogger(__name__).warning("Attachment cleanup deferred: a note could not be read")
            self.persist()
            return {"removed": 0, "deferred": True}
        for draft in self.state["drafts"].values():
            referenced.update(draft["refs"])
            referenced.update(draft["pending"])
        removed = []
        for filename in list(self.state["managed"]):
            if filename not in referenced:
                path = self.directory / filename
                if path.is_file() and not path.is_symlink():
                    path.unlink()
                    removed.append(filename)
                self.state["managed"].remove(filename)
        self.persist()
        return {"removed": len(removed)}
