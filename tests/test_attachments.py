"""Attachment ownership, deduplication and shared reference protection."""
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server"))
from fastapi import UploadFile
from attachments.file_system.file_system import FileSystemAttachments
from attachments.lifecycle import AttachmentLifecycle


class AttachmentTest(unittest.TestCase):
    def setUp(self):
        Path("work/tests").mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir="work/tests")
        self.root = Path(self.tmp.name)
        with patch.dict(os.environ, FLATNOTES_PATH=str(self.root)):
            self.storage = FileSystemAttachments()
        self.life = AttachmentLifecycle(self.storage)
        self.a, self.b = str(uuid4()), str(uuid4())

    def tearDown(self):
        self.tmp.cleanup()

    def upload(self, name="图片 (1).png", content=b"same image", draft=None):
        return self.life.upload(UploadFile(filename=name, file=io.BytesIO(content)), draft or self.a)

    def exists(self, filename):
        return (self.root / "attachments" / filename).exists()

    def test_duplicate_drafts_and_restart(self):
        first = self.upload()
        second = self.upload("another.png", draft=self.b)
        self.assertEqual(first.url, second.url)
        self.assertEqual(len(list((self.root / "attachments").iterdir())), 1)
        self.life.sync(self.a, "", [], discard=True)
        self.assertTrue(self.exists(first.filename))  # Other editor still uploading.
        content = f"![image]({first.url})"
        self.life.sync(self.b, content, [first.filename])
        self.life = AttachmentLifecycle(self.storage)
        self.life.collect()
        self.assertTrue(self.exists(first.filename))  # Persisted browser draft.
        self.life.sync(self.b, "", [], discard=True)
        self.assertFalse(self.exists(first.filename))

    def test_save_shared_notes_remove_reference_and_pending(self):
        image = self.upload()
        self.life.sync(self.a, f'<img src="/apps/notes/{image.url}">', [image.filename])
        for name in ("one.md", "two.md"):
            (self.root / name).write_text(f"![image]({image.url})", encoding="utf-8")
        with self.life.lock:
            self.life.release(self.a)
        self.assertTrue(self.exists(image.filename))
        (self.root / "one.md").unlink()
        self.life.collect()
        self.assertTrue(self.exists(image.filename))
        (self.root / "two.md").write_text("removed", encoding="utf-8")
        self.life.collect()
        self.assertFalse(self.exists(image.filename))
        pending = self.upload("unused.png", b"unused")
        self.life.sync(self.a, "", [])  # A sync before upload callback cannot delete it.
        self.assertTrue(self.exists(pending.filename))
        self.life.sync(self.a, "", [pending.filename])
        self.assertFalse(self.exists(pending.filename))

    def test_legacy_upload_and_unknown_files_are_not_deleted(self):
        legacy = self.life.upload(UploadFile(filename="legacy.txt", file=io.BytesIO(b"legacy")))
        self.life.collect()
        self.assertTrue(self.exists(legacy.filename))
        with self.assertRaises(ValueError):
            self.life.sync("../bad", "", [])

    def test_unreadable_note_defers_deletion(self):
        image = self.upload()
        (self.root / "unreadable.md").write_bytes(b"\xff")
        result = self.life.sync(self.a, "", [], discard=True)
        self.assertTrue(result["deferred"])
        self.assertTrue(self.exists(image.filename))


if __name__ == "__main__":
    unittest.main()
